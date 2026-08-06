# Agent Architecture — Design Document

> Technical documentation for the UCSI Agentic AI CTF 2026 agent harness.

---

## 1. Overview

The agent is designed as an autonomous CTF challenge solver. It accepts a challenge description, classifies the challenge type, and iteratively analyzes and exploits the target using a ReAct reasoning loop driven by a large language model (LLM).

### Design Goals

- **Autonomous operation** — Solve challenges with minimal human intervention
- **Provider agnostic** — Work with any LLM (GPT-4o, Claude, Llama 3.1, etc.)
- **Modular tools** — Easily extend with new analysis and exploitation capabilities
- **Category aware** — Specialized prompts and strategies for PWN, WEB, REV, CRYPTO
- **Safe execution** — Sandboxed code execution with timeouts

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      CLI (run.py)                         │
│   argparse-based interface with rich terminal output      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Agent Core (core.py)                  │  │
│  │                                                    │  │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐    │  │
│  │  │ REASON   │───▶│  TOOLS   │───▶│ REASON   │    │  │
│  │  │ (LLM)    │    │ (Execute)│    │ (LLM)    │    │  │
│  │  └──────────┘    └──────────┘    └──────────┘    │  │
│  │       │                               │          │  │
│  │       ▼                               ▼          │  │
│  │  ┌──────────┐                   ┌──────────┐    │  │
│  │  │ Flag?    │──── yes ─────────▶│   DONE   │    │  │
│  │  │ Max iter?│                   └──────────┘    │  │
│  │  └──────────┘                                   │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              LLM Provider (llm.py)                  │ │
│  │  OpenAI │ Anthropic │ Ollama │ Groq                 │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              Tool Suite (tools/)                    │ │
│  │                                                     │ │
│  │  ┌──────────────┐  ┌───────────────┐               │ │
│  │  │ Binary       │  │ Code          │               │ │
│  │  │ Analysis     │  │ Executor      │               │ │
│  │  │ (r2pipe)     │  │ (subprocess)  │               │ │
│  │  └──────────────┘  └───────────────┘               │ │
│  │  ┌──────────────┐  ┌───────────────┐               │ │
│  │  │ Network      │  │ Web           │               │ │
│  │  │ Client       │  │ Tools         │               │ │
│  │  │ (socket)     │  │ (aiohttp)     │               │ │
│  │  └──────────────┘  └───────────────┘               │ │
│  │  ┌──────────────┐                                  │ │
│  │  │ File         │                                  │ │
│  │  │ Tools        │                                  │ │
│  │  └──────────────┘                                  │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## 3. ReAct Loop

The agent follows the **ReAct (Reasoning + Acting)** paradigm, implemented as a LangGraph state machine:

### State

```python
class AgentState(TypedDict):
    messages: list[BaseMessage]   # Full conversation history
    challenge: str                # Challenge description
    category: str                 # pwn, web, rev, crypto, misc
    flags_found: list[str]        # Extracted flags
    iteration: int                # Current iteration count
    max_iterations: int           # Safety limit
    status: str                   # running, solved, failed
```

### Nodes

| Node | Function | Description |
|------|----------|-------------|
| `reason` | `_reason_node()` | Calls the LLM with full context and tool bindings |
| `tools` | `ToolNode(ALL_TOOLS)` | Executes tool calls returned by the LLM |

### Edges

```
reason ──[has tool calls]──▶ tools ──▶ reason
reason ──[flag found]──────▶ END
reason ──[max iterations]──▶ END
reason ──[no tool calls]───▶ END
```

### Termination Conditions

1. **Flag found** — Regex `UCSI26\{[a-zA-Z0-9_]+\}` detected in output
2. **Max iterations** — Configurable limit (default: 25)
3. **No action** — LLM produces a response without tool calls

---

## 4. Tool Design

Each tool is a `@langchain_core.tools.tool` decorated function. This provides:
- Automatic schema generation for the LLM
- Type validation on inputs
- Structured error handling

### Tool Categories

#### Binary Analysis (`binary_analysis.py`)
- **Primary**: radare2 via r2pipe (decompilation, disassembly, function listing)
- **Fallback**: objdump, nm, pwntools ELF
- **Features**: `analyze_binary`, `list_functions`, `get_strings`, `checksec`

#### Code Executor (`code_executor.py`)
- Runs Python code in isolated subprocess
- Timeout protection (default 60s)
- Output size limits (10KB)
- Supports running inline code or script files

#### Network Client (`network_client.py`)
- TCP connection with send/receive sequences
- Binary payload support (hex-encoded)
- Menu-driven service interaction

#### Web Tools (`web_tools.py`)
- Full HTTP request support (GET, POST, PUT, DELETE)
- Session and cookie management
- **Concurrent requests** via `aiohttp` for race condition exploits
- Automatic flag detection in responses

#### File Tools (`file_tools.py`)
- Read files in text, hex dump, or raw hex modes
- Write text or binary files
- Hex encode/decode utilities

---

## 5. LLM Integration

### Provider Abstraction

The `llm.py` module provides a factory function `get_llm()` that returns a LangChain-compatible chat model:

```python
from agent.llm import get_llm

llm = get_llm(provider="ollama", model="llama3.1:70b")
```

### Supported Providers

| Provider | Import | Env Var |
|----------|--------|---------|
| OpenAI | `langchain_openai.ChatOpenAI` | `OPENAI_API_KEY` |
| Anthropic | `langchain_anthropic.ChatAnthropic` | `ANTHROPIC_API_KEY` |
| Ollama | `langchain_community.ChatOllama` | `OLLAMA_BASE_URL` |
| Groq | `langchain_community.ChatGroq` | `GROQ_API_KEY` |

### Tool Calling

Tools are bound to the LLM using LangChain's `bind_tools()`:

```python
llm_with_tools = llm.bind_tools(ALL_TOOLS)
```

The LLM receives JSON schemas for all tools and can invoke them by returning structured tool call messages.

---

## 6. Prompt Engineering

### System Prompt Structure

```
[Base CTF Expert Prompt]
  ├── Capabilities list (PWN, WEB, REV, CRYPTO, MISC)
  ├── ReAct methodology (OBSERVE → ANALYZE → PLAN → EXPLOIT → VERIFY)
  ├── Rules (flag format, no fabrication, tool usage)
  └── Output format (FLAG FOUND: ...)

[Category-Specific Prompt]  (appended based on challenge category)
  ├── PWN: heap techniques, ROP, pwntools usage
  ├── WEB: injection types, race conditions, session handling
  ├── REV: static analysis, VM internals, algorithm recovery
  └── MISC: forensics, steganography, encoding puzzles
```

### Prompt Design Decisions

1. **Explicit methodology** — The ReAct steps are spelled out so the LLM follows a structured approach
2. **Tool-aware** — The prompt mentions specific tools (pwntools, requests) to guide the LLM
3. **Category specialization** — Different vulnerability classes are highlighted per category
4. **Guard rails** — Rules prevent flag fabrication and ensure systematic analysis
5. **Flag format** — Explicit `UCSI26{...}` format for auto-detection

---

## 7. Challenge-Specific Strategies

### PWN Strategy
1. `checksec` → understand binary protections
2. `analyze_binary` → decompile key functions
3. `get_strings` → find interesting strings/paths
4. Identify vulnerability class
5. Generate pwntools exploit via `execute_python_code`

### WEB Strategy
1. `http_request GET /` → understand the application
2. Probe API endpoints
3. Identify input handling flaws
4. Exploit via `http_request` or `concurrent_requests`

---

## 8. Safety Considerations

- **Sandboxed execution** — Code runs in subprocess with timeout
- **Output limits** — Tool outputs truncated to prevent context overflow
- **Iteration cap** — Agent cannot loop indefinitely
- **Scope control** — Agent operates only on specified targets
- **No persistence** — Agent does not install backdoors or persist access

---

## 9. Future Improvements

- **Docker isolation** — Run exploit code in containers
- **Memory management** — Summarize old context to handle long conversations
- **Multi-agent** — Parallel sub-agents for different analysis tracks
- **Learning** — Store successful exploit patterns for similar future challenges
- **GDB integration** — Dynamic analysis with breakpoints
- **Burp Suite integration** — Advanced web vulnerability scanning
