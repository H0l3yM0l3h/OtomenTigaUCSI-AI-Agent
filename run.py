#!/usr/bin/env python3
"""
UCSI Agentic AI CTF 2026 — Agent CLI
======================================

Command-line interface for the CTF Agent.
Supports solving challenges interactively or running pre-built solvers.

Usage:
    # Solve a challenge with the AI agent
    python run.py solve --challenge "Description..." --category pwn

    # Run a specific pre-built solver
    python run.py solver grimoire-heap
    python run.py solver sandworm-vm
    python run.py solver saturn-exchange
    python run.py solver pony-express

    # List supported LLM providers
    python run.py providers

    # Show help
    python run.py --help
"""

from __future__ import annotations

import sys
import argparse
import importlib

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def cmd_solve(args):
    """Run the AI agent to solve a challenge."""
    from agent import CTFAgent

    agent = CTFAgent(
        provider=args.provider,
        model=args.model,
        verbose=not args.quiet,
    )

    result = agent.solve(
        challenge=args.challenge,
        category=args.category,
        target_host=args.host,
        target_port=args.port,
        files=args.files,
        max_iterations=args.max_iterations,
    )

    if result["flags"]:
        for flag in result["flags"]:
            console.print(f"\n[bold green]🚩 {flag}[/]")
        sys.exit(0)
    else:
        console.print("\n[bold red]No flag found.[/]")
        sys.exit(1)


def cmd_solver(args):
    """Run a pre-built challenge solver."""
    solvers = {
        "grimoire-heap": "solvers.grimoire_heap",
        "grimoire_heap": "solvers.grimoire_heap",
        "sandworm-vm": "solvers.sandworm_vm",
        "sandworm_vm": "solvers.sandworm_vm",
        "saturn-exchange": "solvers.saturn_exchange",
        "saturn_exchange": "solvers.saturn_exchange",
        "pony-express": "solvers.pony_express",
        "pony_express": "solvers.pony_express",
        "temporary": "solvers.temporary",
        "temporary_vault": "solvers.temporary",
        "oldstock-router": "solvers.oldstock_router",
        "oldstock_router": "solvers.oldstock_router",
        "staffdesk": "solvers.staffdesk",
        "staff_desk": "solvers.staffdesk",
        "cerberus": "solvers.cerberus",
        "cerberus_reports": "solvers.cerberus",
    }

    name = args.name.lower()
    if name not in solvers:
        console.print(f"[red]Unknown solver: {name}[/]")
        console.print(f"[dim]Available: {', '.join(set(solvers.values()))}[/]")
        sys.exit(1)

    module_name = solvers[name]
    console.print(f"[bold cyan]Running solver: {module_name}[/]\n")

    try:
        module = importlib.import_module(module_name)
        if hasattr(module, "solve"):
            module.solve()
        elif hasattr(module, "solve_remote"):
            module.solve_remote()
        else:
            console.print(f"[red]Solver module has no solve() function[/]")
    except Exception as e:
        console.print(f"[red]Solver failed: {e}[/]")
        sys.exit(1)


def cmd_providers(args):
    """List supported LLM providers and models."""
    from agent.llm import list_supported_providers

    table = Table(
        title="Supported LLM Providers",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Provider", style="cyan", width=15)
    table.add_column("Recommended Models", style="white")
    table.add_column("Type", style="dim")

    providers = list_supported_providers()
    types = {
        "openai": "Cloud API",
        "anthropic": "Cloud API",
        "ollama": "Local (self-hosted)",
        "groq": "Cloud (open-source models)",
    }

    for provider, models in providers.items():
        table.add_row(provider, ", ".join(models), types.get(provider, ""))

    console.print(table)
    console.print()
    console.print("[dim]Set LLM_PROVIDER and LLM_MODEL in your .env file[/]")


def cmd_challenges(args):
    """List solved challenges and their flags."""
    table = Table(
        title="UCSI Agentic AI CTF 2026 — Solved Challenges",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Challenge", style="cyan", width=20)
    table.add_column("Category", style="yellow", width=8)
    table.add_column("Technique", style="white", width=30)
    table.add_column("Flag", style="green")

    challenges = [
        ("1", "Grimoire Heap", "PWN", "UAF + tcache poisoning",
         "UCSI26{grimoire_uaf_tcache_win_6e7291e6}"),
        ("2", "Sandworm VM", "PWN", "VM OOB escape",
         "UCSI26{sandworm_vm_oob_escape_025a2ef7}"),
        ("3", "Saturn Exchange", "WEB", "Async race condition",
         "UCSI26{4sync_settlement_r4c3_110cbe1e}"),
        ("4", "Pony Express 500", "WEB", "Handlebars AST injection (CVE-2026-33937)",
         "UCSI26{cve-2026-33937_h4ndl3b4rs_4st_1nj3ct10n}"),
        ("5", "Temporary", "WEB", "Path traversal + templates",
         "UCSI26{cve-2026-44705_tmp_tr4v3rs4l_g4in_1s_f0r3v3r}"),
        ("6", "OldStock Router", "FIRM", "Firmware SquashFS extract",
         "UCSI26{0ld5t0ck_fw_b4ckup_l34k}"),
        ("7", "StaffDesk", "WEB", "GraphQL IDOR + Account Reset",
         "UCSI26{gr4phql_1d0r_2_admin_t4k30v3r}"),
        ("8", "Cerberus Reports", "WEB", "Java Deserialization + SUID",
         "UCSI26{cerberus_gadget_privesc_8630453b}"),
    ]

    for c in challenges:
        table.add_row(*c)

    console.print(table)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="ctf-agent",
        description="UCSI Agentic AI CTF 2026 — Autonomous Challenge Solver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python run.py solve --challenge "A banished spell..." --category pwn --host 52.76.96.108 --port 9005
  python run.py solver grimoire-heap
  python run.py solver pony-express
  python run.py providers
  python run.py challenges
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── solve command ──
    solve_parser = subparsers.add_parser("solve", help="Solve a CTF challenge with AI")
    solve_parser.add_argument("--challenge", "-c", required=True, help="Challenge description")
    solve_parser.add_argument("--category", "-t", default="misc",
                              choices=["pwn", "web", "rev", "crypto", "misc"],
                              help="Challenge category")
    solve_parser.add_argument("--host", "-H", help="Target host")
    solve_parser.add_argument("--port", "-P", type=int, help="Target port")
    solve_parser.add_argument("--files", "-f", nargs="+", help="Challenge files")
    solve_parser.add_argument("--provider", default=None, help="LLM provider override")
    solve_parser.add_argument("--model", default=None, help="LLM model override")
    solve_parser.add_argument("--max-iterations", type=int, default=None, help="Max agent iterations")
    solve_parser.add_argument("--quiet", "-q", action="store_true", help="Suppress verbose output")

    # ── solver command ──
    solver_parser = subparsers.add_parser("solver", help="Run a pre-built challenge solver")
    solver_parser.add_argument("name", help="Solver name (e.g., grimoire-heap, sandworm-vm, saturn-exchange, pony-express)")

    # ── providers command ──
    subparsers.add_parser("providers", help="List supported LLM providers")

    # ── challenges command ──
    subparsers.add_parser("challenges", help="List solved challenges")

    args = parser.parse_args()

    if not args.command:
        # Show banner and help
        console.print(Panel(
            "[bold cyan]UCSI Agentic AI CTF 2026[/]\n"
            "[dim]Autonomous CTF Challenge Solver[/]\n\n"
            "Run [bold]python run.py --help[/] for usage information\n"
            "Run [bold]python run.py challenges[/] to see solved challenges",
            title="🚩 CTF Agent",
            border_style="cyan",
            padding=(1, 2),
        ))
        parser.print_help()
        return

    commands = {
        "solve": cmd_solve,
        "solver": cmd_solver,
        "providers": cmd_providers,
        "challenges": cmd_challenges,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
