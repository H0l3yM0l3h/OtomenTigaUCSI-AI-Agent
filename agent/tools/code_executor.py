"""Bounded local Python execution tools for authorized CTF workloads.

The default path is a subprocess boundary, not a hardened security sandbox.
It provides unique work files, time limits, and output limits. Use the optional
Docker sandbox for stronger isolation when running untrusted challenge code.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from langchain_core.tools import tool

from agent.config import config


MAX_TIMEOUT_SECONDS = 300
MAX_OUTPUT_CHARS = 10_000


def _validated_timeout(timeout: int) -> int:
    """Return a safe timeout or raise a clear tool-facing error."""
    if not isinstance(timeout, int) or not 1 <= timeout <= MAX_TIMEOUT_SECONDS:
        raise ValueError(f"timeout must be between 1 and {MAX_TIMEOUT_SECONDS} seconds")
    return timeout


def _format_result(result: subprocess.CompletedProcess[str]) -> str:
    """Format subprocess evidence consistently and cap it for the agent context."""
    output_parts: list[str] = []
    if result.stdout:
        output_parts.append(f"[STDOUT]\n{result.stdout}")
    if result.stderr:
        output_parts.append(f"[STDERR]\n{result.stderr}")

    output = "\n".join(output_parts) if output_parts else "[No output]"
    if result.returncode != 0:
        output += f"\n[EXIT CODE: {result.returncode}]"
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n... [OUTPUT TRUNCATED]"
    return output


def _subprocess_env() -> dict[str, str]:
    """Build a predictable child environment without altering the parent."""
    return {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"}


@tool
def execute_python_code(code: str, timeout: int = 60) -> str:
    """
    Execute Python code in a bounded subprocess and return the output.

    The code is written to a temporary file and executed with the system
    Python interpreter. Both stdout and stderr are captured.

    Args:
        code: The Python source code to execute.
        timeout: Maximum execution time in seconds (default: 60).

    Returns:
        Combined stdout and stderr output from the execution,
        or an error message if execution failed.
    """
    work_dir = config.output_dir / "sandbox"
    work_dir.mkdir(parents=True, exist_ok=True)
    script_path: Path | None = None

    try:
        safe_timeout = _validated_timeout(timeout)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".py",
            prefix="agent-exploit-",
            dir=work_dir,
            delete=False,
        ) as script:
            script.write(code)
            script_path = Path(script.name)

        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=safe_timeout,
            cwd=str(work_dir),
            env=_subprocess_env(),
            check=False,
        )
        return _format_result(result)

    except subprocess.TimeoutExpired:
        return (
            f"[ERROR] Execution timed out after {timeout} seconds. "
            f"The exploit may need optimization or the target may be unreachable."
        )
    except Exception as e:
        return f"[ERROR] Failed to execute code: {type(e).__name__}: {e}"
    finally:
        # Clean up temp script
        if script_path and script_path.exists():
            try:
                script_path.unlink()
            except OSError:
                pass


@tool
def execute_script_file(file_path: str, arguments: str = "", timeout: int = 60) -> str:
    """
    Execute an existing Python script file and return the output.

    Args:
        file_path: Path to the Python script to execute.
        arguments: Additional command-line arguments to pass to the script.
        timeout: Maximum execution time in seconds (default: 60).

    Returns:
        Combined stdout and stderr output from the execution.
    """
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        return f"[ERROR] Script not found: {file_path}"
    if path.suffix.lower() != ".py":
        return f"[ERROR] Only Python script files are supported: {file_path}"

    try:
        safe_timeout = _validated_timeout(timeout)
        cmd = [sys.executable, str(path)]
        if arguments:
            cmd.extend(shlex.split(arguments))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=safe_timeout,
            cwd=str(path.parent),
            env=_subprocess_env(),
            check=False,
        )
        return _format_result(result)

    except subprocess.TimeoutExpired:
        return f"[ERROR] Script timed out after {timeout} seconds."
    except Exception as e:
        return f"[ERROR] Failed to execute script: {type(e).__name__}: {e}"
