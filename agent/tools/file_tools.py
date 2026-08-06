"""
File I/O Tools.

Provides file reading, writing, and encoding/decoding utilities
for CTF challenge work.

Capabilities:
  - Read text and binary files
  - Write exploit payloads and scripts
  - Hex encode/decode
  - Base64 encode/decode
"""

from __future__ import annotations

import base64
from pathlib import Path
from langchain_core.tools import tool

from agent.utils import hexdump


@tool
def read_file(file_path: str, mode: str = "text", max_bytes: int = 8000) -> str:
    """
    Read a file and return its contents.

    Args:
        file_path: Path to the file to read.
        mode: Reading mode - 'text' for UTF-8 text, 'hex' for hex dump,
              'raw' for raw bytes as hex string.
        max_bytes: Maximum bytes to read (default: 8000).

    Returns:
        File contents in the requested format.
    """
    path = Path(file_path)
    if not path.exists():
        return f"[ERROR] File not found: {file_path}"

    try:
        if mode == "text":
            content = path.read_text(encoding="utf-8", errors="replace")
            if len(content) > max_bytes:
                content = content[:max_bytes] + "\n... [TRUNCATED]"
            return content

        elif mode == "hex":
            data = path.read_bytes()[:max_bytes]
            return hexdump(data)

        elif mode == "raw":
            data = path.read_bytes()[:max_bytes]
            return data.hex()

        else:
            return f"[ERROR] Unknown mode: {mode}. Use 'text', 'hex', or 'raw'."

    except Exception as e:
        return f"[ERROR] Failed to read file: {type(e).__name__}: {e}"


@tool
def write_file(file_path: str, content: str, mode: str = "text") -> str:
    """
    Write content to a file.

    Args:
        file_path: Path to the file to write.
        content: The content to write.
        mode: Write mode - 'text' for UTF-8 text, 'hex' for hex-encoded bytes.

    Returns:
        Confirmation message with file path and size.
    """
    path = Path(file_path)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        if mode == "text":
            path.write_text(content, encoding="utf-8")
            size = path.stat().st_size
            return f"[OK] Written {size} bytes to {file_path}"

        elif mode == "hex":
            data = bytes.fromhex(content)
            path.write_bytes(data)
            return f"[OK] Written {len(data)} bytes (from hex) to {file_path}"

        else:
            return f"[ERROR] Unknown mode: {mode}. Use 'text' or 'hex'."

    except ValueError as e:
        return f"[ERROR] Invalid hex content: {e}"
    except Exception as e:
        return f"[ERROR] Failed to write file: {type(e).__name__}: {e}"


@tool
def hex_encode(data: str) -> str:
    """
    Encode a string to its hexadecimal representation.

    Args:
        data: The ASCII/UTF-8 string to encode.

    Returns:
        Hex-encoded string.
    """
    return data.encode("utf-8").hex()


@tool
def hex_decode(hex_string: str) -> str:
    """
    Decode a hexadecimal string back to ASCII/UTF-8.

    Args:
        hex_string: The hex string to decode (e.g., '48656c6c6f').

    Returns:
        Decoded text string, or error message if invalid hex.
    """
    # Clean the hex string
    cleaned = hex_string.strip().replace(" ", "").replace("\n", "")

    try:
        raw = bytes.fromhex(cleaned)
        decoded = raw.decode("utf-8", errors="replace")
        return decoded
    except ValueError as e:
        return f"[ERROR] Invalid hex string: {e}"
