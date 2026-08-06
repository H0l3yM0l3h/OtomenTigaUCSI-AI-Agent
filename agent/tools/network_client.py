"""
Network Client Tool.

Provides TCP/UDP socket interaction for communicating with
CTF challenge services (e.g., PWN challenges on remote servers).

Supports:
  - TCP connect with send/receive
  - Binary protocol handling
  - Interactive multi-step conversations
  - Connection timeout management
"""

from __future__ import annotations

import socket
import struct
from langchain_core.tools import tool


@tool
def tcp_connect_and_interact(
    host: str,
    port: int,
    commands: list[str],
    timeout: int = 10,
    recv_size: int = 4096,
) -> str:
    """
    Connect to a TCP service and send a sequence of commands, capturing responses.

    Each command is sent one at a time, with a receive between each send.
    Useful for interacting with menu-driven CTF challenge services.

    Args:
        host: Target hostname or IP address.
        port: Target port number.
        commands: List of strings to send (each followed by a newline).
        timeout: Socket timeout in seconds (default: 10).
        recv_size: Maximum bytes to receive per read (default: 4096).

    Returns:
        A transcript of the interaction showing sends and receives.
    """
    transcript = []

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)

            # Read initial banner
            try:
                banner = sock.recv(recv_size).decode("utf-8", errors="replace")
                transcript.append(f"[RECV banner]\n{banner}")
            except socket.timeout:
                transcript.append("[No initial banner received]")

            # Send each command and capture response
            for i, cmd in enumerate(commands):
                # Send
                sock.sendall((cmd + "\n").encode("utf-8"))
                transcript.append(f"[SEND {i + 1}] {cmd}")

                # Receive response
                try:
                    response = sock.recv(recv_size).decode("utf-8", errors="replace")
                    transcript.append(f"[RECV {i + 1}]\n{response}")
                except socket.timeout:
                    transcript.append(f"[RECV {i + 1}] (timeout)")

    except ConnectionRefusedError:
        transcript.append(f"[ERROR] Connection refused to {host}:{port}")
    except socket.timeout:
        transcript.append(f"[ERROR] Connection timed out to {host}:{port}")
    except Exception as e:
        transcript.append(f"[ERROR] {type(e).__name__}: {e}")

    # Truncate if too long
    result = "\n".join(transcript)
    if len(result) > 8000:
        result = result[:8000] + "\n... [TRUNCATED]"

    return result


@tool
def tcp_send_binary(
    host: str,
    port: int,
    hex_payload: str,
    timeout: int = 10,
    recv_size: int = 4096,
) -> str:
    """
    Send a raw binary payload (as hex string) to a TCP service.

    Useful for binary protocol exploitation where raw bytes need to
    be sent (e.g., VM bytecode, struct-packed data).

    Args:
        host: Target hostname or IP address.
        port: Target port number.
        hex_payload: Hex-encoded payload string (e.g., "deadbeef01020304").
        timeout: Socket timeout in seconds.
        recv_size: Maximum bytes to receive.

    Returns:
        The response from the server (hex + ASCII).
    """
    try:
        payload = bytes.fromhex(hex_payload)
    except ValueError as e:
        return f"[ERROR] Invalid hex payload: {e}"

    transcript = []

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)

            # Send binary payload
            sock.sendall(payload)
            sock.shutdown(socket.SHUT_WR)
            transcript.append(f"[SENT] {len(payload)} bytes")

            # Receive all response data
            chunks = []
            while True:
                try:
                    data = sock.recv(recv_size)
                    if not data:
                        break
                    chunks.append(data)
                except socket.timeout:
                    break

            response = b"".join(chunks)
            transcript.append(f"[RECV] {len(response)} bytes")

            # Show as hex + ASCII
            hex_resp = response.hex()
            ascii_resp = response.decode("utf-8", errors="replace")
            transcript.append(f"[HEX] {hex_resp[:2000]}")
            transcript.append(f"[ASCII] {ascii_resp[:2000]}")

    except ConnectionRefusedError:
        transcript.append(f"[ERROR] Connection refused to {host}:{port}")
    except socket.timeout:
        transcript.append(f"[ERROR] Connection timed out")
    except Exception as e:
        transcript.append(f"[ERROR] {type(e).__name__}: {e}")

    return "\n".join(transcript)
