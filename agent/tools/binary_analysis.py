"""
Binary Analysis Tool.

Provides tools for analyzing ELF binaries using radare2 (via r2pipe)
and standard command-line utilities as a fallback.

Capabilities:
  - Decompile / disassemble specific functions
  - List all functions in a binary
  - Extract printable strings
  - Check security mitigations (checksec equivalent)
"""

from __future__ import annotations

import subprocess
import shutil
from pathlib import Path
from langchain_core.tools import tool


def _r2pipe_available() -> bool:
    """Check if r2pipe and radare2 are available."""
    try:
        import r2pipe  # noqa: F401
        return shutil.which("radare2") is not None or shutil.which("r2") is not None
    except ImportError:
        return False


def _run_command(cmd: list[str], timeout: int = 30) -> str:
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "[ERROR] Command timed out"
    except FileNotFoundError:
        return f"[ERROR] Command not found: {cmd[0]}"


@tool
def analyze_binary(file_path: str, function_name: str = "main") -> str:
    """
    Analyze a binary and decompile/disassemble a specific function.

    Args:
        file_path: Path to the ELF binary.
        function_name: Name of the function to analyze (default: main).

    Returns:
        Decompiled or disassembled output of the function.
    """
    path = Path(file_path)
    if not path.exists():
        return f"[ERROR] File not found: {file_path}"

    if _r2pipe_available():
        import r2pipe

        r2 = r2pipe.open(str(path), flags=["-2"])
        r2.cmd("aaa")  # Full analysis

        # Try decompilation first (if r2ghidra is available)
        decompiled = r2.cmd(f"s sym.{function_name}; pdg")
        if decompiled and "Cannot" not in decompiled:
            r2.quit()
            return f"[Decompiled {function_name}]\n{decompiled}"

        # Fall back to disassembly
        disasm = r2.cmd(f"s sym.{function_name}; pdf")
        r2.quit()
        return f"[Disassembly of {function_name}]\n{disasm}"

    # Fallback: use objdump
    if shutil.which("objdump"):
        output = _run_command(["objdump", "-d", "-M", "intel", str(path)])
        return f"[objdump disassembly]\n{output[:8000]}"

    return (
        "[ERROR] No binary analysis tools available. "
        "Install radare2 or ensure objdump is in PATH."
    )


@tool
def list_functions(file_path: str) -> str:
    """
    List all functions found in a binary.

    Args:
        file_path: Path to the ELF binary.

    Returns:
        A list of function names, addresses, and sizes.
    """
    path = Path(file_path)
    if not path.exists():
        return f"[ERROR] File not found: {file_path}"

    if _r2pipe_available():
        import r2pipe

        r2 = r2pipe.open(str(path), flags=["-2"])
        r2.cmd("aaa")
        functions = r2.cmd("afl")
        r2.quit()
        return f"[Functions in {path.name}]\n{functions}"

    # Fallback: nm
    if shutil.which("nm"):
        output = _run_command(["nm", "-C", str(path)])
        return f"[Symbols via nm]\n{output[:5000]}"

    return "[ERROR] No analysis tools available."


@tool
def get_strings(file_path: str, min_length: int = 4) -> str:
    """
    Extract printable strings from a binary file.

    Args:
        file_path: Path to the binary file.
        min_length: Minimum string length to extract.

    Returns:
        Extracted strings, one per line.
    """
    path = Path(file_path)
    if not path.exists():
        return f"[ERROR] File not found: {file_path}"

    if _r2pipe_available():
        import r2pipe

        r2 = r2pipe.open(str(path), flags=["-2"])
        strings = r2.cmd(f"iz~[3:]")
        r2.quit()
        return f"[Strings in {path.name}]\n{strings[:5000]}"

    # Fallback: strings command
    if shutil.which("strings"):
        output = _run_command(["strings", f"-n{min_length}", str(path)])
        return f"[Strings (len >= {min_length})]\n{output[:5000]}"

    # Python fallback
    import re

    data = path.read_bytes()
    pattern = re.compile(rb"[\x20-\x7e]{%d,}" % min_length)
    found = [m.group().decode("ascii") for m in pattern.finditer(data)]
    return f"[Strings extracted]\n" + "\n".join(found[:200])


@tool
def checksec(file_path: str) -> str:
    """
    Check the security mitigations of a binary (ASLR, PIE, NX, canary, RELRO).

    Args:
        file_path: Path to the ELF binary.

    Returns:
        Security analysis results.
    """
    path = Path(file_path)
    if not path.exists():
        return f"[ERROR] File not found: {file_path}"

    # Try checksec command
    if shutil.which("checksec"):
        output = _run_command(["checksec", "--file", str(path)])
        return output

    # Try pwn checksec via pwntools
    try:
        from pwn import ELF

        elf = ELF(str(path), checksec=False)
        results = []
        results.append(f"File:    {path.name}")
        results.append(f"Arch:    {elf.arch}")
        results.append(f"RELRO:   {'Full' if elf.full_relro else 'Partial' if elf.relro else 'No'}")
        results.append(f"Stack:   {'Canary found' if elf.canary else 'No canary'}")
        results.append(f"NX:      {'Enabled' if elf.nx else 'Disabled'}")
        results.append(f"PIE:     {'Enabled' if elf.pie else 'Disabled'}")
        return "\n".join(results)
    except Exception:
        pass

    if _r2pipe_available():
        import r2pipe

        r2 = r2pipe.open(str(path), flags=["-2"])
        info = r2.cmd("iI")
        r2.quit()
        return f"[Binary info]\n{info}"

    return "[ERROR] No security analysis tools available."
