"""
Agent Tool Suite.

Provides LangChain-compatible tools for CTF challenge solving:
  - binary_analysis: Decompile, disassemble, and analyze ELF binaries
  - code_executor: Run Python exploit scripts in a sandboxed subprocess
  - network_client: TCP/UDP interaction with challenge services
  - web_tools: HTTP requests, race condition exploitation
  - file_tools: File I/O, hex encoding/decoding
"""

from agent.tools.binary_analysis import (
    analyze_binary,
    list_functions,
    get_strings,
    checksec,
)
from agent.tools.code_executor import execute_python_code, execute_script_file
from agent.tools.network_client import tcp_connect_and_interact
from agent.tools.web_tools import http_request, concurrent_requests
from agent.tools.file_tools import read_file, write_file, hex_encode, hex_decode

# Collect all tools for registration with the agent
ALL_TOOLS = [
    analyze_binary,
    list_functions,
    get_strings,
    checksec,
    execute_python_code,
    execute_script_file,
    tcp_connect_and_interact,
    http_request,
    concurrent_requests,
    read_file,
    write_file,
    hex_encode,
    hex_decode,
]

__all__ = ["ALL_TOOLS"]
