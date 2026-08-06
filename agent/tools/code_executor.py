"""
Code Executor Tool.

Provides sandboxed Python code execution for running exploit scripts.
Executes code in a subprocess with timeout protection.

Safety measures:
  - Subprocess isolation
  - Configurable timeout (default 30s)
  - Output size limits
  - Working directory isolation
"""

from __future__ import annotations

import subprocess
import tempfile
import os
from pathlib import Path
from langchain_core.tools import tool

from agent.config import config


@tool
def execute_python_code(code: str, timeout: int = 60) -> str:
    """
    Execute Python code in a sandboxed subprocess and return the output.

    The code is written to a temporary file and executed with the system
    Python interpreter. Both stdout and stderr are captured.

    Args:
        code: The Python source code to execute.
        timeout: Maximum execution time in seconds (default: 60).

    Returns:
        Combined stdout and stderr output from the execution,
        or an error message if execution failed.
    """
    # Create a temp file for the code
    work_dir = config.output_dir / "sandbox"
    work_dir.mkdir(parents=True, exist_ok=True)

    script_path = work_dir / "_agent_exploit.py"
    script_path.write_text(code, encoding="utf-8")

    try:
        result = subprocess.run(
            ["python", str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(work_dir),
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

        output_parts = []
        if result.stdout:
            output_parts.append(f"[STDOUT]\n{result.stdout}")
        if result.stderr:
            output_parts.append(f"[STDERR]\n{result.stderr}")

        output = "\n".join(output_parts) if output_parts else "[No output]"

        # Add return code info
        if result.returncode != 0:
            output += f"\n[EXIT CODE: {result.returncode}]"

        # Truncate very long output
        if len(output) > 10000:
            output = output[:10000] + "\n... [OUTPUT TRUNCATED]"

        return output

    except subprocess.TimeoutExpired:
        return (
            f"[ERROR] Execution timed out after {timeout} seconds. "
            f"The exploit may need optimization or the target may be unreachable."
        )
    except Exception as e:
        return f"[ERROR] Failed to execute code: {type(e).__name__}: {e}"
    finally:
        # Clean up temp script
        if script_path.exists():
            try:
                script_path.unlink()
            except OSError:
                pass


@tool
def execute_script_file(file_path: str, args: str = "", timeout: int = 60) -> str:
    """
    Execute an existing Python script file and return the output.

    Args:
        file_path: Path to the Python script to execute.
        args: Additional command-line arguments to pass to the script.
        timeout: Maximum execution time in seconds (default: 60).

    Returns:
        Combined stdout and stderr output from the execution.
    """
    path = Path(file_path)
    if not path.exists():
        return f"[ERROR] Script not found: {file_path}"

    cmd = ["python", str(path)]
    if args:
        cmd.extend(args.split())

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(path.parent),
        )

        output_parts = []
        if result.stdout:
            output_parts.append(f"[STDOUT]\n{result.stdout}")
        if result.stderr:
            output_parts.append(f"[STDERR]\n{result.stderr}")

        output = "\n".join(output_parts) if output_parts else "[No output]"

        if result.returncode != 0:
            output += f"\n[EXIT CODE: {result.returncode}]"

        if len(output) > 10000:
            output = output[:10000] + "\n... [OUTPUT TRUNCATED]"

        return output

    except subprocess.TimeoutExpired:
        return f"[ERROR] Script timed out after {timeout} seconds."
    except Exception as e:
        return f"[ERROR] Failed to execute script: {type(e).__name__}: {e}"
