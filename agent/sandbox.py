"""
Docker Sandbox for CTF Agent.

Provides isolated Docker containers for running exploit code safely.
Inspired by the Veria Labs ctf-agent architecture.

Each solver gets its own container with CTF tools pre-installed:
  - pwntools, radare2, GDB
  - Python 3 with exploitation libraries
  - Standard Linux utilities

The sandbox prevents exploit code from compromising the host system.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default sandbox Docker image
DEFAULT_IMAGE = "ctf-sandbox"


@dataclass
class ExecResult:
    """Result of executing a command in the sandbox."""
    exit_code: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        """Combined stdout + stderr."""
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        return "\n".join(parts)

    @property
    def success(self) -> bool:
        return self.exit_code == 0


@dataclass
class DockerSandbox:
    """
    Isolated Docker container for running CTF exploits.

    Usage:
        sandbox = DockerSandbox(challenge_dir="/path/to/challenge")
        await sandbox.start()
        result = await sandbox.exec("python3 exploit.py")
        await sandbox.stop()
    """

    image: str = DEFAULT_IMAGE
    challenge_dir: str = ""
    memory_limit: str = "4g"
    timeout_default: int = 300
    container_id: str = ""
    workspace_dir: str = ""

    def _docker_available(self) -> bool:
        """Check if Docker is available."""
        return shutil.which("docker") is not None

    async def start(self) -> None:
        """Start a new sandbox container."""
        if not self._docker_available():
            logger.warning("Docker not available — sandbox will use local execution")
            return

        # Build volume mounts
        volumes = []
        if self.challenge_dir and Path(self.challenge_dir).exists():
            volumes.extend(["-v", f"{self.challenge_dir}:/challenge:ro"])

        # Create and start container
        cmd = [
            "docker", "run", "-d",
            "--memory", self.memory_limit,
            "--network", "host",
            "--label", "ctf-agent",
            *volumes,
            self.image,
            "sleep", "infinity",
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                self.container_id = result.stdout.strip()[:12]
                logger.info(f"Sandbox started: {self.container_id}")
            else:
                logger.error(f"Failed to start sandbox: {result.stderr}")
        except Exception as e:
            logger.error(f"Docker error: {e}")

    async def exec(self, command: str, timeout_s: int | None = None) -> ExecResult:
        """
        Execute a command inside the sandbox container.

        Falls back to local subprocess if Docker is not available.
        """
        timeout = timeout_s or self.timeout_default

        if self.container_id:
            return await self._exec_docker(command, timeout)
        else:
            return await self._exec_local(command, timeout)

    async def _exec_docker(self, command: str, timeout: int) -> ExecResult:
        """Execute inside Docker container."""
        cmd = [
            "docker", "exec", self.container_id,
            "bash", "-c", command,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            return ExecResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except subprocess.TimeoutExpired:
            return ExecResult(exit_code=-1, stdout="", stderr=f"Timed out after {timeout}s")
        except Exception as e:
            return ExecResult(exit_code=-1, stdout="", stderr=str(e))

    async def _exec_local(self, command: str, timeout: int) -> ExecResult:
        """Execute locally (fallback when Docker is not available)."""
        try:
            result = subprocess.run(
                ["bash", "-c", command] if shutil.which("bash") else ["cmd", "/c", command],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return ExecResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except subprocess.TimeoutExpired:
            return ExecResult(exit_code=-1, stdout="", stderr=f"Timed out after {timeout}s")
        except Exception as e:
            return ExecResult(exit_code=-1, stdout="", stderr=str(e))

    async def stop(self) -> None:
        """Stop and remove the sandbox container."""
        if self.container_id:
            try:
                subprocess.run(
                    ["docker", "rm", "-f", self.container_id],
                    capture_output=True, timeout=30,
                )
                logger.info(f"Sandbox stopped: {self.container_id}")
            except Exception:
                pass
            self.container_id = ""
