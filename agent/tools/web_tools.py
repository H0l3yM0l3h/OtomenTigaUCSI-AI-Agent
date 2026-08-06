"""
Web Exploitation Tools.

Provides HTTP request tools and concurrent request capabilities
for exploiting web-based CTF challenges.

Features:
  - Standard HTTP requests with session/cookie management
  - Concurrent requests for race condition exploitation
  - JSON and form-encoded body support
  - Response parsing and flag extraction
"""

from __future__ import annotations

import json
import asyncio
import aiohttp
import requests
from typing import Any
from langchain_core.tools import tool

from agent.utils import extract_flags


@tool
def http_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: str | None = None,
    cookies: dict[str, str] | None = None,
    content_type: str = "application/json",
    timeout: int = 15,
    follow_redirects: bool = True,
) -> str:
    """
    Send an HTTP request and return the response details.

    Args:
        url: The full URL to request.
        method: HTTP method (GET, POST, PUT, DELETE, PATCH).
        headers: Optional HTTP headers as key-value pairs.
        body: Optional request body (JSON string for application/json).
        cookies: Optional cookies as key-value pairs.
        content_type: Content-Type header value.
        timeout: Request timeout in seconds.
        follow_redirects: Whether to follow HTTP redirects.

    Returns:
        A formatted string containing status code, headers, and body.
    """
    method = method.upper()
    req_headers = headers or {}

    kwargs: dict[str, Any] = {
        "timeout": timeout,
        "allow_redirects": follow_redirects,
    }

    if cookies:
        kwargs["cookies"] = cookies

    if req_headers:
        kwargs["headers"] = req_headers

    # Handle body
    if body and method in ("POST", "PUT", "PATCH"):
        if content_type == "application/json":
            try:
                kwargs["json"] = json.loads(body)
            except json.JSONDecodeError:
                kwargs["data"] = body
                req_headers["Content-Type"] = content_type
        else:
            kwargs["data"] = body
            req_headers["Content-Type"] = content_type

    try:
        response = requests.request(method, url, **kwargs)

        # Build response summary
        parts = [
            f"[{method} {url}]",
            f"Status: {response.status_code} {response.reason}",
            f"",
            f"[Response Headers]",
        ]

        for key, value in response.headers.items():
            parts.append(f"  {key}: {value}")

        parts.append("")
        parts.append("[Response Body]")

        # Try to pretty-print JSON
        try:
            body_json = response.json()
            parts.append(json.dumps(body_json, indent=2))
        except (json.JSONDecodeError, ValueError):
            body_text = response.text[:5000]
            parts.append(body_text)

        # Check for cookies
        if response.cookies:
            parts.append("")
            parts.append("[Cookies]")
            for name, value in response.cookies.items():
                parts.append(f"  {name}={value}")

        result = "\n".join(parts)

        # Auto-detect flags
        flags = extract_flags(result)
        if flags:
            result += f"\n\n🚩 [FLAG DETECTED] {', '.join(flags)}"

        return result

    except requests.ConnectionError:
        return f"[ERROR] Connection failed to {url}"
    except requests.Timeout:
        return f"[ERROR] Request timed out after {timeout}s"
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"


@tool
def concurrent_requests(
    url: str,
    method: str = "POST",
    body: str | None = None,
    count: int = 3,
    cookies: dict[str, str] | None = None,
    content_type: str = "application/json",
    timeout: int = 15,
) -> str:
    """
    Send multiple HTTP requests concurrently (for race condition exploits).

    All requests are fired simultaneously using asyncio to maximize
    the chance of triggering TOCTOU / race condition bugs.

    Args:
        url: The target URL.
        method: HTTP method for all requests.
        body: Request body (same for all requests).
        count: Number of concurrent requests to send.
        cookies: Optional cookies to include.
        content_type: Content-Type header.
        timeout: Per-request timeout in seconds.

    Returns:
        A summary of all responses received.
    """

    async def _send_all():
        """Fire all requests concurrently."""
        connector = aiohttp.TCPConnector(limit=0)
        jar = aiohttp.CookieJar()

        async with aiohttp.ClientSession(
            connector=connector, cookie_jar=jar
        ) as session:
            # Pre-set cookies
            if cookies:
                for name, value in cookies.items():
                    session.cookie_jar.update_cookies({name: value})

            tasks = []
            for i in range(count):
                tasks.append(_single_request(session, i, url, method, body, content_type, timeout))

            return await asyncio.gather(*tasks, return_exceptions=True)

    async def _single_request(session, index, url, method, body, content_type, timeout):
        """Send a single request."""
        kwargs: dict[str, Any] = {
            "timeout": aiohttp.ClientTimeout(total=timeout),
        }

        if body and method.upper() in ("POST", "PUT", "PATCH"):
            if content_type == "application/json":
                try:
                    kwargs["json"] = json.loads(body)
                except json.JSONDecodeError:
                    kwargs["data"] = body
                    kwargs["headers"] = {"Content-Type": content_type}
            else:
                kwargs["data"] = body
                kwargs["headers"] = {"Content-Type": content_type}

        async with session.request(method.upper(), url, **kwargs) as resp:
            text = await resp.text()
            return {
                "index": index,
                "status": resp.status,
                "body": text[:2000],
            }

    # Run the async requests
    try:
        loop = asyncio.new_event_loop()
        results = loop.run_until_complete(_send_all())
        loop.close()
    except Exception as e:
        return f"[ERROR] Concurrent requests failed: {type(e).__name__}: {e}"

    # Format results
    parts = [f"[Concurrent {method.upper()} x{count} to {url}]", ""]

    all_text = ""
    for r in results:
        if isinstance(r, Exception):
            parts.append(f"  Request: ERROR - {r}")
        else:
            parts.append(f"  Request {r['index'] + 1}: HTTP {r['status']}")
            parts.append(f"    Body: {r['body'][:500]}")
            all_text += r["body"]
        parts.append("")

    result = "\n".join(parts)

    # Auto-detect flags
    flags = extract_flags(all_text)
    if flags:
        result += f"\n🚩 [FLAG DETECTED] {', '.join(flags)}"

    return result
