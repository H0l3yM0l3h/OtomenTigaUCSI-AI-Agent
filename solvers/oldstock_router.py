#!/usr/bin/env python3
"""
OldStock Router — Firmware Challenge Solver
=============================================

Challenge:  OldStock Router FW (UCSI Agentic AI CTF 2026)
Category:   FIRMWARE / REV
Flag:       UCSI26{0ld5t0ck_fw_b4ckup_l34k}

Analysis:
    1. Custom firmware header is 256 bytes (0x100) long.
    2. Superblock of SquashFS starts at offset 256 (0x100).
    3. squashfs-root contains `etc/config/rconfig.bak` which contains
       configuration options, including the flag.

Exploitation:
    unsquashfs -d extracted -o 256 OldStock_Router_FW_v1.2.3.bin
    cat extracted/etc/config/rconfig.bak
"""

from __future__ import annotations

import os
import subprocess
import re

FIRMWARE_NAME = "OldStock_Router_FW_v1.2.3.bin"

def solve():
    """Solve the OldStock Router firmware challenge."""
    print("=" * 60)
    print("  OldStock Router — SquashFS Firmware Extractor Solver")
    print("  UCSI Agentic AI CTF 2026")
    print("=" * 60)
    print()

    # Find firmware binary
    fw_path = None
    for root, dirs, files in os.walk("."):
        if FIRMWARE_NAME in files:
            fw_path = os.path.join(root, FIRMWARE_NAME)
            break

    if not fw_path or not os.path.exists(fw_path):
        print(f"[!] Firmware binary '{FIRMWARE_NAME}' not found in workspace.")
        print("[*] Supply the original challenge image to perform a verified replay.")
        return None

    print(f"[*] Found firmware image at: {fw_path}")
    print("[*] Extracting SquashFS superblock at offset 256...")
    
    out_dir = "extracted_fw_fs"
    # Command to unsquashfs starting at offset 256
    cmd = ["unsquashfs", "-d", out_dir, "-o", "256", fw_path]
    print(f"    Running: {' '.join(cmd)}")
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("[+] Extraction successful!")
    except Exception as e:
        print(f"[!] Extraction failed: {e}")
        # Try alternate binwalk approach or manual fallback
        print("[*] SquashFS extraction fallback...")

    # Search for flag in extracted files
    target_bak = os.path.join(out_dir, "etc/config/rconfig.bak")
    if os.path.exists(target_bak):
        print(f"[*] Reading config backup: {target_bak}")
        with open(target_bak, "r", encoding="utf-8") as f:
            content = f.read()
            print("--- Contents ---")
            print(content.strip())
            print("----------------")
            
            m = re.search(r"UCSI26\{[a-zA-Z0-9_\-]+\}", content)
            if m:
                flag = m.group()
                print()
                print(f"[+] FLAG FOUND: {flag}")
                return flag

    # Global grep fallback in output directory
    if os.path.exists(out_dir):
        print("[*] Searching flag pattern in extracted directory...")
        for root, dirs, files in os.walk(out_dir):
            for file in files:
                p = os.path.join(root, file)
                try:
                    with open(p, "r", errors="ignore") as f:
                        data = f.read()
                        m = re.search(r"UCSI26\{[a-zA-Z0-9_\-]+\}", data)
                        if m:
                            flag = m.group()
                            print(f"[+] FLAG FOUND in {file}: {flag}")
                            return flag
                except Exception:
                    pass

    print()
    print("[!] Target files not successfully extracted.")
    return None

if __name__ == "__main__":
    solve()
