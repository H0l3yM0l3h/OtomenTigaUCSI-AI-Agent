#!/usr/bin/env python3
"""Command-line interface for the OtomenTiga CTF agent harness."""

from __future__ import annotations

import argparse
import importlib
import json
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent.challenges import CHALLENGES, challenge_by_name, replayable_challenges
from agent.utils import contains_flag


console = Console()


def cmd_solve(args: argparse.Namespace) -> int:
    """Run the autonomous agent on a challenge."""
    from agent import CTFAgent

    try:
        agent = CTFAgent(provider=args.provider, model=args.model, verbose=not (args.quiet or args.json))
        result = agent.solve(
            challenge=args.challenge,
            category=args.category,
            target_host=args.host,
            target_port=args.port,
            files=args.files,
            max_iterations=args.max_iterations,
        )
    except (ImportError, ValueError) as exc:
        if args.json:
            print(json.dumps({"status": "configuration_error", "error": str(exc)}))
        else:
            console.print(f"[bold red]Configuration error:[/] {exc}")
            console.print("[dim]Run `python run.py doctor` for an environment report.[/]")
        return 2
    except Exception as exc:
        if args.json:
            print(json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"}))
        else:
            console.print(f"[bold red]Agent startup failed:[/] {type(exc).__name__}: {exc}")
        return 1

    if args.json:
        print(json.dumps(result, sort_keys=True))
        return 0 if result["flags"] else 1

    if result["flags"]:
        for flag in result["flags"]:
            console.print(f"\n[bold green]🚩 {flag}[/]")
        return 0

    console.print("\n[bold red]No tool-observed flag found.[/]")
    return 1


def cmd_solver(args: argparse.Namespace) -> int:
    """Run a captured deterministic replay solver."""
    challenge = challenge_by_name(args.name)
    if challenge is None:
        available = ", ".join(item.slug for item in replayable_challenges())
        console.print(f"[bold red]Unknown solver:[/] {args.name}")
        console.print(f"[dim]Available: {available}[/]")
        return 2

    if not challenge.solver_module:
        console.print(f"[bold yellow]{challenge.name} is a documented capture, not a replay module yet.[/]")
        console.print("[dim]See docs/writeup.md for the verified exploit chain.[/]")
        return 2

    console.print(f"[bold cyan]Running solver: {challenge.name}[/]\n")
    try:
        module = importlib.import_module(challenge.solver_module)
        solve = getattr(module, "solve", None) or getattr(module, "solve_remote", None)
        if solve is None:
            console.print("[bold red]Solver module has no callable solve function.[/]")
            return 2
        result = solve()
    except Exception as exc:
        console.print(f"[bold red]Solver failed:[/] {type(exc).__name__}: {exc}")
        return 1

    if isinstance(result, str) and contains_flag(result):
        console.print(f"\n[bold green]Verified replay result: {result}[/]")
        return 0

    console.print("\n[bold red]Replay finished without a verified flag.[/]")
    console.print("[dim]Expired targets and missing challenge files are reported as failures, never as captures.[/]")
    return 1


def cmd_providers(_args: argparse.Namespace) -> int:
    """List supported LLM providers and recommended model families."""
    from agent.llm import list_supported_providers

    table = Table(title="Supported LLM Providers", header_style="bold magenta")
    table.add_column("Provider", style="cyan", width=15)
    table.add_column("Recommended models", style="white")
    table.add_column("Type", style="dim")
    types = {
        "openai": "Cloud API",
        "anthropic": "Cloud API",
        "ollama": "Local / self-hosted",
        "groq": "Cloud API",
    }
    for provider, models in list_supported_providers().items():
        table.add_row(provider, ", ".join(models), types.get(provider, ""))
    console.print(table)
    console.print("\n[dim]Set LLM_PROVIDER and LLM_MODEL in your .env file.[/]")
    return 0


def cmd_challenges(args: argparse.Namespace) -> int:
    """Display the canonical nine-capture portfolio."""
    if args.json:
        payload = [
            {
                "slug": challenge.slug,
                "name": challenge.name,
                "category": challenge.category,
                "technique": challenge.technique,
                "evidence": challenge.evidence,
            }
            for challenge in CHALLENGES
        ]
        print(json.dumps(payload, sort_keys=True))
        return 0

    table = Table(title="UCSI Agentic AI CTF 2026 — Capture Portfolio", header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Challenge", style="cyan", width=23)
    table.add_column("Domain", style="yellow", width=8)
    table.add_column("Technique", style="white", width=36)
    table.add_column("Evidence", style="green", width=13)
    for index, challenge in enumerate(CHALLENGES, 1):
        table.add_row(
            str(index),
            challenge.name,
            challenge.category,
            challenge.technique,
            challenge.evidence,
        )
    console.print(table)
    console.print(
        f"\n[bold green]{len(CHALLENGES)} captures[/] · "
        f"[bold cyan]{len(replayable_challenges())} replay modules[/] · "
        "[bold magenta]13 agent tools[/]"
    )
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Run a no-network installation and capability audit."""
    from agent.diagnostics import diagnostics_pass, run_diagnostics

    checks = run_diagnostics()
    passed = diagnostics_pass(checks, strict=args.strict)
    if args.json:
        payload = {
            "passed": passed,
            "strict": args.strict,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status,
                    "detail": check.detail,
                    "required": check.required,
                }
                for check in checks
            ],
        }
        print(json.dumps(payload, sort_keys=True))
        return 0 if passed else 1

    symbols = {"pass": "✓", "warn": "!", "fail": "✗"}
    styles = {"pass": "green", "warn": "yellow", "fail": "red"}
    table = Table(title="OtomenTiga Environment Doctor", header_style="bold magenta")
    table.add_column("", width=2)
    table.add_column("Check", style="cyan", width=24)
    table.add_column("Result", width=9)
    table.add_column("Details")
    for check in checks:
        style = styles[check.status]
        table.add_row(symbols[check.status], check.name, f"[{style}]{check.status.upper()}[/]", check.detail)
    console.print(table)

    if passed:
        console.print("\n[bold green]Core harness checks passed.[/]")
        return 0
    console.print("\n[bold red]One or more required checks failed.[/]")
    return 1


def build_parser() -> argparse.ArgumentParser:
    """Build the command parser independently for tests and integrations."""
    parser = argparse.ArgumentParser(
        prog="ctf-agent",
        description="OtomenTiga — evidence-driven agentic CTF harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python run.py doctor
  python run.py challenges
  python run.py solver saturn-exchange
  python run.py solve --challenge "A service may contain an IDOR" --category web --host TARGET_HOST --port TARGET_PORT
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    solve_parser = subparsers.add_parser("solve", help="Solve an authorized CTF challenge with AI")
    solve_parser.add_argument("--challenge", "-c", required=True, help="Challenge description")
    solve_parser.add_argument(
        "--category",
        "-t",
        default="misc",
        choices=["pwn", "web", "rev", "crypto", "misc"],
        help="Challenge category",
    )
    solve_parser.add_argument("--host", "-H", help="Authorized target host")
    solve_parser.add_argument("--port", "-P", type=int, help="Authorized target port")
    solve_parser.add_argument("--files", "-f", nargs="+", help="Challenge files")
    solve_parser.add_argument("--provider", help="LLM provider override")
    solve_parser.add_argument("--model", help="Model override")
    solve_parser.add_argument("--max-iterations", type=int, help="Maximum reasoning passes")
    solve_parser.add_argument("--quiet", "-q", action="store_true", help="Suppress verbose output")
    solve_parser.add_argument("--json", action="store_true", help="Emit a machine-readable run result")

    solver_parser = subparsers.add_parser("solver", help="Replay a captured challenge technique")
    solver_parser.add_argument("name", help="Challenge slug, for example saturn-exchange")

    subparsers.add_parser("providers", help="List supported LLM providers")
    challenges_parser = subparsers.add_parser("challenges", help="Show the nine-capture portfolio")
    challenges_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    doctor_parser = subparsers.add_parser("doctor", help="Audit the local installation without network calls")
    doctor_parser.add_argument("--strict", action="store_true", help="Treat optional warnings as failures")
    doctor_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Dispatch one CLI command and return its process status."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        console.print(
            Panel(
                "[bold cyan]OTOMENTIGA // CHAMPION BUILD[/]\n"
                "[dim]Reason. Act. Prove. Replay.[/]\n\n"
                "Run [bold]python run.py doctor[/] to verify the environment\n"
                "Run [bold]python run.py challenges[/] to inspect the capture portfolio",
                title="🚩 Agentic CTF Harness",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        parser.print_help()
        return 0

    commands = {
        "solve": cmd_solve,
        "solver": cmd_solver,
        "providers": cmd_providers,
        "challenges": cmd_challenges,
        "doctor": cmd_doctor,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
