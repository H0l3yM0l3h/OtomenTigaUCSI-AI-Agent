"""
LLM Provider Abstraction Layer.

Provides a unified interface to multiple LLM backends:
  - OpenAI (GPT-4o, GPT-4o-mini)
  - Anthropic (Claude 3.5 Sonnet, Claude Opus)
  - Ollama (Llama 3.1, DeepSeek Coder, Mistral — local inference)
  - Groq (Llama 3.1 70B — fast cloud inference for open-source models)

The provider is selected via the LLM_PROVIDER and LLM_MODEL env vars.
"""

from __future__ import annotations
from langchain_core.language_models.chat_models import BaseChatModel

from agent.config import config


def get_llm(
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    **kwargs,
) -> BaseChatModel:
    """
    Create and return an LLM instance based on the selected provider.

    Args:
        provider: LLM provider name. Defaults to config value.
        model: Model identifier. Defaults to config value.
        temperature: Sampling temperature (0 = deterministic).
        **kwargs: Additional provider-specific arguments.

    Returns:
        A LangChain-compatible chat model instance.

    Raises:
        ValueError: If the provider is unknown or API key is missing.
    """
    provider = (provider or config.llm_provider).lower()
    model = model or config.llm_model

    if provider == "openai":
        return _build_openai(model, temperature, **kwargs)
    elif provider == "anthropic":
        return _build_anthropic(model, temperature, **kwargs)
    elif provider == "ollama":
        return _build_ollama(model, temperature, **kwargs)
    elif provider == "groq":
        return _build_groq(model, temperature, **kwargs)
    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. "
            f"Supported: openai, anthropic, ollama, groq"
        )


# ─── Provider Builders ───────────────────────────────────────────────

def _build_openai(model: str, temperature: float, **kwargs) -> BaseChatModel:
    """Build an OpenAI chat model."""
    if not config.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is required for the OpenAI provider. "
            "Set it in your .env file."
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=config.openai_api_key,
        **kwargs,
    )


def _build_anthropic(model: str, temperature: float, **kwargs) -> BaseChatModel:
    """Build an Anthropic chat model."""
    if not config.anthropic_api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is required for the Anthropic provider. "
            "Set it in your .env file."
        )
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=model,
        temperature=temperature,
        api_key=config.anthropic_api_key,
        max_tokens=4096,
        **kwargs,
    )


def _build_ollama(model: str, temperature: float, **kwargs) -> BaseChatModel:
    """Build an Ollama (local) chat model."""
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=model,
        temperature=temperature,
        base_url=config.ollama_base_url,
        **kwargs,
    )


def _build_groq(model: str, temperature: float, **kwargs) -> BaseChatModel:
    """Build a Groq cloud inference chat model."""
    if not config.groq_api_key:
        raise ValueError(
            "GROQ_API_KEY is required for the Groq provider. "
            "Set it in your .env file."
        )
    from langchain_groq import ChatGroq

    return ChatGroq(
        model=model,
        temperature=temperature,
        groq_api_key=config.groq_api_key,
        **kwargs,
    )


# ─── Utility ─────────────────────────────────────────────────────────

def list_supported_providers() -> dict[str, list[str]]:
    """Return a dict of providers and their recommended models."""
    return {
        "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "anthropic": ["claude-sonnet-4-20250514", "claude-opus-4-20250514"],
        "ollama": ["llama3.1:70b", "deepseek-coder-v2", "mistral"],
        "groq": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant"],
    }
