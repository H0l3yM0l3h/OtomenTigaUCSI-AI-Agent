"""
Utility functions for the CTF Agent.

Includes flag extraction, hex formatting, logging helpers,
and other shared utilities used across the agent.
"""

from __future__ import annotations

import re
import logging
from datetime import datetime
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.text import Text


# ─── Flag Pattern ─────────────────────────────────────────────────────

FLAG_PATTERN = re.compile(r"UCSI26\{[a-zA-Z0-9_\-]+\}")


def extract_flags(text: str) -> list[str]:
    """
    Extract all CTF flags from a text string.

    Args:
        text: The text to search for flags.

    Returns:
        A list of found flag strings.
    """
    return FLAG_PATTERN.findall(text)


def contains_flag(text: str) -> bool:
    """Check if the text contains a valid CTF flag."""
    return bool(FLAG_PATTERN.search(text))


# ─── Hex Utilities ────────────────────────────────────────────────────

def hex_to_ascii(hex_string: str) -> str:
    """Convert a hex string to ASCII, ignoring non-printable characters."""
    try:
        raw = bytes.fromhex(hex_string)
        return raw.decode("ascii", errors="ignore")
    except ValueError:
        return ""


def hexdump(data: bytes, width: int = 16) -> str:
    """
    Generate a readable hex dump of binary data.

    Args:
        data: Raw bytes to dump.
        width: Number of bytes per line.

    Returns:
        Formatted hex dump string.
    """
    lines = []
    for offset in range(0, len(data), width):
        chunk = data[offset : offset + width]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{offset:08x}  {hex_part:<{width * 3}}  |{ascii_part}|")
    return "\n".join(lines)


# ─── Logging ──────────────────────────────────────────────────────────

console = Console()


def setup_logging(verbose: bool = True) -> logging.Logger:
    """Configure rich logging for the agent."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )
    return logging.getLogger("ctf-agent")


def print_banner():
    """Display the agent startup banner."""
    banner_text = Text()
    banner_text.append("  ╔═══════════════════════════════════════════╗\n", style="bold cyan")
    banner_text.append("  ║                                           ║\n", style="bold cyan")
    banner_text.append("  ║   ", style="bold cyan")
    banner_text.append("OtomenTiga CTF Agent v2.0", style="bold white")
    banner_text.append("        ║\n", style="bold cyan")
    banner_text.append("  ║   ", style="bold cyan")
    banner_text.append("Autonomous CTF Challenge Solver", style="dim white")
    banner_text.append("       ║\n", style="bold cyan")
    banner_text.append("  ║                                           ║\n", style="bold cyan")
    banner_text.append("  ╚═══════════════════════════════════════════╝", style="bold cyan")
    console.print(banner_text)


def print_flag_found(flag: str):
    """Display a prominent flag-found notification."""
    console.print(
        Panel(
            f"[bold green]🚩 FLAG FOUND: {flag}[/]",
            title="[bold yellow]✨ SUCCESS ✨[/]",
            border_style="green",
            padding=(1, 2),
        )
    )


def print_step(step_num: int, action: str, detail: str = ""):
    """Display an agent step."""
    console.print(
        f"  [bold cyan]Step {step_num}[/] │ "
        f"[bold]{action}[/]"
        f"{' │ ' + detail if detail else ''}"
    )


def print_tool_call(tool_name: str, args_summary: str = ""):
    """Display a tool invocation."""
    console.print(
        f"  [dim]  ├─ 🔧 [bold magenta]{tool_name}[/][/]"
        f"{' ' + args_summary if args_summary else ''}"
    )


def print_thinking(thought: str):
    """Display the agent's reasoning."""
    # Truncate very long thoughts for display
    if len(thought) > 500:
        thought = thought[:497] + "..."
    console.print(f"  [dim]  ├─ 💭 {thought}[/]")


def get_timestamp() -> str:
    """Get current timestamp as a string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
