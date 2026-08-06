"""
UCSI Agentic AI CTF 2026 — Agent Harness
=========================================

An AI-powered agent that autonomously analyzes and solves
Capture The Flag (CTF) challenges across PWN, WEB, and other categories.

Architecture:
    - ReAct (Reasoning + Acting) loop via LangGraph
    - Provider-agnostic LLM backend (OpenAI, Anthropic, Ollama, Groq)
    - Modular tool suite for binary analysis, code execution,
      network interaction, and web exploitation

Usage:
    from agent import CTFAgent
    agent = CTFAgent()
    result = agent.solve(challenge_description="...", category="pwn")
"""

from agent.core import CTFAgent

__version__ = "1.0.0"
__all__ = ["CTFAgent"]
