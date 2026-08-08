"""
CTF Agent Core — ReAct Loop with LangGraph.

Implements the main agent orchestration using a state graph:

    ┌──────────┐     ┌──────────┐     ┌──────────┐
    │ ANALYZE  │────▶│  PLAN    │────▶│ EXPLOIT  │
    └──────────┘     └──────────┘     └──────────┘
         ▲                                  │
         │           ┌──────────┐           │
         └───────────│  VERIFY  │◀──────────┘
                     └──────────┘
                          │
                     ┌──────────┐
                     │   DONE   │
                     └──────────┘

The agent loops through analyze → plan → exploit → verify until
a flag is found or the maximum iteration count is reached.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated, TypedDict, Sequence, Literal
from uuid import uuid4

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from agent.llm import get_llm
from agent.prompts import SYSTEM_PROMPT, get_prompt_for_category
from agent.tools import ALL_TOOLS
from agent.utils import (
    extract_flags,
    print_banner,
    print_flag_found,
    print_step,
    print_tool_call,
    print_thinking,
    console,
    setup_logging,
)
from agent.config import config


# ─── State Definition ─────────────────────────────────────────────────

class AgentState(TypedDict):
    """State maintained across the agent's reasoning loop."""
    messages: Annotated[Sequence[BaseMessage], lambda a, b: list(a) + list(b)]
    challenge: str
    category: str
    flags_found: list[str]
    iteration: int
    max_iterations: int
    status: str  # "running", "solved", "failed"


def _tool_observed_flags(messages: Sequence[BaseMessage]) -> list[str]:
    """Extract unique flags only from executed tool observations."""
    observed: list[str] = []
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        content = message.content if isinstance(message.content, str) else str(message.content)
        for flag in extract_flags(content):
            if flag not in observed:
                observed.append(flag)
    return observed


# ─── CTF Agent Class ──────────────────────────────────────────────────

class CTFAgent:
    """
    AI-powered CTF challenge solver using a ReAct reasoning loop.

    The agent uses an LLM (configurable provider) with a suite of
    security tools to autonomously analyze and exploit CTF challenges.

    Usage:
        agent = CTFAgent()
        result = agent.solve(
            challenge="A banished spell is supposed to be gone...",
            category="pwn",
            target_host="52.76.96.108",
            target_port=9005
        )
        print(result)
    """

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        verbose: bool | None = None,
    ):
        """
        Initialize the CTF Agent.

        Args:
            provider: LLM provider override (default: from config).
            model: Model name override (default: from config).
            verbose: Enable verbose output (default: from config).
        """
        self.verbose = verbose if verbose is not None else config.verbose
        self.logger = setup_logging(self.verbose)
        self.provider = (provider or config.llm_provider).lower()
        self.model = model or config.llm_model

        # Build the LLM with tool-calling support
        self.llm = get_llm(provider=self.provider, model=self.model)
        self.llm_with_tools = self.llm.bind_tools(ALL_TOOLS)

        # Build the agent graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Construct the LangGraph state machine for the agent."""
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("reason", self._reason_node)
        graph.add_node("tools", ToolNode(ALL_TOOLS))

        # Set entry point
        graph.set_entry_point("reason")

        # Add conditional edges
        graph.add_conditional_edges(
            "reason",
            self._should_continue,
            {
                "tools": "tools",
                "end": END,
            },
        )

        # Tools always route back to reasoning
        graph.add_edge("tools", "reason")

        return graph.compile()

    def _reason_node(self, state: AgentState) -> dict:
        """
        The reasoning node — calls the LLM to think and decide next action.

        This is the core of the ReAct loop. The LLM receives the full
        conversation history and decides whether to call a tool or
        provide a final answer.
        """
        messages = list(state["messages"])
        observed_flags = _tool_observed_flags(messages)
        if observed_flags:
            if self.verbose:
                for flag in observed_flags:
                    console.print(f"  [bold green]✓ Tool evidence verified:[/] {flag}")
            return {
                "messages": [],
                "flags_found": observed_flags,
                "status": "solved",
            }

        iteration = state.get("iteration", 0) + 1

        if self.verbose:
            print_step(iteration, "Reasoning", "LLM is analyzing...")

        # Call the LLM
        response = self.llm_with_tools.invoke(messages)

        if self.verbose:
            # Show thinking
            if hasattr(response, "content") and response.content:
                content = response.content if isinstance(response.content, str) else str(response.content)
                print_thinking(content[:300])

            # Show tool calls
            if hasattr(response, "tool_calls") and response.tool_calls:
                for tc in response.tool_calls:
                    args_str = ", ".join(
                        f"{k}={repr(v)[:50]}" for k, v in tc.get("args", {}).items()
                    )
                    print_tool_call(tc["name"], args_str)

        # A model response is not evidence. Flag-shaped text is accepted only
        # after it has appeared in a ToolMessage from an executed action.
        model_flags = []
        if hasattr(response, "content") and response.content:
            content = response.content if isinstance(response.content, str) else str(response.content)
            model_flags = extract_flags(content)
        if model_flags and self.verbose:
            console.print("  [yellow]Flag-shaped model text ignored until a tool observation verifies it.[/]")

        return {
            "messages": [response],
            "iteration": iteration,
            "flags_found": state.get("flags_found", []),
            "status": state.get("status", "running"),
        }

    def _should_continue(self, state: AgentState) -> Literal["tools", "end"]:
        """Decide whether to continue tool-calling or stop."""
        # Check if we found a flag
        if state.get("flags_found"):
            return "end"

        # Check iteration limit
        if state.get("iteration", 0) >= state.get("max_iterations", config.max_iterations):
            return "end"

        # Check if the last message has tool calls
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"

        return "end"

    def solve(
        self,
        challenge: str,
        category: str = "misc",
        target_host: str | None = None,
        target_port: int | None = None,
        files: list[str] | None = None,
        max_iterations: int | None = None,
    ) -> dict:
        """
        Solve a CTF challenge.

        Args:
            challenge: Challenge description or prompt.
            category: Challenge category (pwn, web, rev, crypto, misc).
            target_host: Remote host for the challenge service.
            target_port: Remote port for the challenge service.
            files: List of file paths associated with the challenge.
            max_iterations: Override max iterations for this solve.

        Returns:
            A structured dict with the run ID, status, tool-verified flags,
            iteration count, category, provider, model, and elapsed time.
        """
        challenge = challenge.strip()
        category = category.lower().strip()
        if not challenge:
            raise ValueError("challenge description cannot be empty")
        if category not in {"pwn", "web", "rev", "crypto", "misc"}:
            raise ValueError(f"unsupported challenge category: {category}")
        if bool(target_host) != bool(target_port):
            raise ValueError("target_host and target_port must be provided together")
        if target_port is not None and not 1 <= target_port <= 65_535:
            raise ValueError("target_port must be between 1 and 65535")

        iteration_limit = max_iterations if max_iterations is not None else config.max_iterations
        if not isinstance(iteration_limit, int) or iteration_limit < 1:
            raise ValueError("max_iterations must be a positive integer")

        normalized_files: list[str] = []
        for file_path in files or []:
            path = Path(file_path).expanduser().resolve()
            if not path.is_file():
                raise ValueError(f"challenge file not found: {file_path}")
            normalized_files.append(str(path))
        files = normalized_files or None

        run_id = uuid4().hex[:12]
        started_at = time.perf_counter()

        if self.verbose:
            print_banner()
            console.print()
            console.print(f"  [bold]Challenge:[/] {challenge[:100]}...")
            console.print(f"  [bold]Category:[/]  {category.upper()}")
            if target_host:
                console.print(f"  [bold]Target:[/]    {target_host}:{target_port}")
            if files:
                console.print(f"  [bold]Files:[/]     {', '.join(files)}")
            console.print()
            console.rule("[bold cyan]Agent Starting[/]")
            console.print()

        # Build the initial prompt
        system_msg = SYSTEM_PROMPT + "\n\n" + get_prompt_for_category(category)

        user_prompt = f"## CTF Challenge\n\n"
        user_prompt += f"**Category:** {category.upper()}\n"
        user_prompt += f"**Description:** {challenge}\n\n"

        if target_host and target_port:
            user_prompt += f"**Target:** {target_host}:{target_port}\n\n"

        if files:
            user_prompt += f"**Provided Files:** {', '.join(files)}\n\n"
            user_prompt += (
                "Start by analyzing the provided files to understand the challenge. "
                "Then formulate and execute an exploit to capture the flag.\n"
            )
        else:
            user_prompt += (
                "Analyze the challenge description and use the available tools to "
                "explore the target, identify vulnerabilities, and capture the flag.\n"
            )

        # Initialize state
        initial_state: AgentState = {
            "messages": [
                SystemMessage(content=system_msg),
                HumanMessage(content=user_prompt),
            ],
            "challenge": challenge,
            "category": category,
            "flags_found": [],
            "iteration": 0,
            "max_iterations": iteration_limit,
            "status": "running",
        }

        # Run the agent graph
        try:
            final_state = self.graph.invoke(initial_state)
        except Exception as e:
            self.logger.error(f"Agent error: {e}")
            final_state = {
                **initial_state,
                "status": "error",
                "flags_found": [],
            }

        # Extract results
        flags = final_state.get("flags_found", [])
        status = "solved" if flags else final_state.get("status", "failed")
        if status == "running":
            status = "failed"
        iterations = final_state.get("iteration", 0)

        if self.verbose:
            console.print()
            console.rule("[bold cyan]Agent Complete[/]")
            console.print()
            console.print(f"  [bold]Status:[/]     {status.upper()}")
            console.print(f"  [bold]Iterations:[/] {iterations}")

            if flags:
                for flag in flags:
                    print_flag_found(flag)
            else:
                console.print("  [bold red]No flag found.[/]")

            console.print()

        return {
            "run_id": run_id,
            "flags": flags,
            "status": status,
            "iterations": iterations,
            "category": category,
            "provider": self.provider,
            "model": self.model,
            "evidence_source": "tool_observation" if flags else None,
            "duration_seconds": round(time.perf_counter() - started_at, 3),
        }

    def solve_with_script(
        self,
        challenge: str,
        category: str,
        script_path: str,
    ) -> dict:
        """
        Ask the agent to analyze a challenge, then run a pre-written solver.

        Useful for challenges where the exploit is already known and the
        agent just needs to execute and verify it.

        Args:
            challenge: Challenge description.
            category: Challenge category.
            script_path: Path to the solver script.

        Returns:
            Same dict as solve().
        """
        enhanced_challenge = (
            f"{challenge}\n\n"
            f"A solver script has been prepared at: {script_path}\n"
            f"Execute this script using the execute_script_file tool "
            f"and extract the flag from the output."
        )
        return self.solve(
            challenge=enhanced_challenge,
            category=category,
            files=[script_path],
        )
