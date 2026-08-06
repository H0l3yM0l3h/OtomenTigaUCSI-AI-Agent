"""
Configuration management for the CTF Agent.

Loads settings from .env file and environment variables.
Provides a singleton Config object used throughout the agent.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv


# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


@dataclass
class Config:
    """Central configuration for the CTF agent."""

    # ── LLM Provider ──
    llm_provider: str = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "openai")
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o")
    )

    # ── API Keys ──
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )
    anthropic_api_key: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )
    groq_api_key: str = field(
        default_factory=lambda: os.getenv("GROQ_API_KEY", "")
    )

    # ── Ollama ──
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )

    # ── Agent Behavior ──
    max_iterations: int = field(
        default_factory=lambda: int(os.getenv("MAX_ITERATIONS", "25"))
    )
    verbose: bool = field(
        default_factory=lambda: os.getenv("VERBOSE", "true").lower() == "true"
    )

    # ── Paths ──
    project_root: Path = field(default_factory=lambda: _project_root)
    solvers_dir: Path = field(default_factory=lambda: _project_root / "solvers")
    output_dir: Path = field(default_factory=lambda: _project_root / "output")

    def __post_init__(self):
        """Ensure output directory exists."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> list[str]:
        """Return a list of configuration warnings/errors."""
        issues = []
        if self.llm_provider == "openai" and not self.openai_api_key:
            issues.append("OPENAI_API_KEY is not set")
        elif self.llm_provider == "anthropic" and not self.anthropic_api_key:
            issues.append("ANTHROPIC_API_KEY is not set")
        elif self.llm_provider == "groq" and not self.groq_api_key:
            issues.append("GROQ_API_KEY is not set")
        return issues


# ── Singleton ──
config = Config()
