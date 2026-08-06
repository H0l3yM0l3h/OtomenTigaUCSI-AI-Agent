"""
Loop Detection for the CTF Agent.

Detects when the agent is stuck in a repetitive cycle of tool calls
and injects warnings to encourage trying different approaches.

Based on the Veria Labs ctf-agent pattern.
"""

from __future__ import annotations

import hashlib
from collections import deque
from typing import Literal

# Warning message injected when a loop is detected
LOOP_WARNING_MESSAGE = (
    "⚠️ LOOP DETECTED: You appear to be repeating the same actions. "
    "Stop and reconsider your approach. Try a completely different "
    "technique or tool. If your current exploit isn't working, "
    "analyze WHY and pivot to an alternative strategy."
)


class LoopDetector:
    """
    Detect repetitive tool call patterns.

    Maintains a sliding window of recent tool calls and checks for
    repeated sequences. Returns 'ok', 'warn', or 'break' status.
    """

    def __init__(self, window_size: int = 20, warn_threshold: int = 3, break_threshold: int = 5):
        """
        Args:
            window_size: Number of recent calls to track.
            warn_threshold: Consecutive repeats before warning.
            break_threshold: Consecutive repeats before breaking.
        """
        self.window_size = window_size
        self.warn_threshold = warn_threshold
        self.break_threshold = break_threshold
        self._history: deque[str] = deque(maxlen=window_size)
        self._consecutive_repeats = 0
        self._last_hash: str = ""

    def _hash_call(self, tool_name: str, tool_args: dict) -> str:
        """Create a hash of a tool call for comparison."""
        # Normalize args to a stable string representation
        key = f"{tool_name}:{sorted(tool_args.items())}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def check(self, tool_name: str, tool_args: dict) -> Literal["ok", "warn", "break"]:
        """
        Check if the current tool call is part of a repetitive loop.

        Returns:
            'ok' — No loop detected
            'warn' — Potential loop, warning injected
            'break' — Definite loop, should break
        """
        call_hash = self._hash_call(tool_name, tool_args)

        if call_hash == self._last_hash:
            self._consecutive_repeats += 1
        else:
            self._consecutive_repeats = 0

        self._last_hash = call_hash
        self._history.append(call_hash)

        if self._consecutive_repeats >= self.break_threshold:
            return "break"
        elif self._consecutive_repeats >= self.warn_threshold:
            return "warn"

        # Also check for cyclical patterns in the window
        if len(self._history) >= 6:
            recent = list(self._history)[-6:]
            if recent[:3] == recent[3:]:
                self._consecutive_repeats = self.warn_threshold
                return "warn"

        return "ok"

    def reset(self) -> None:
        """Reset the detector (e.g., when bumped with new insights)."""
        self._history.clear()
        self._consecutive_repeats = 0
        self._last_hash = ""
