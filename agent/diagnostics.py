"""Local installation diagnostics for the competition harness."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from dataclasses import dataclass

from agent.challenges import CHALLENGES, replayable_challenges
from agent.config import config


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One actionable environment check."""

    name: str
    status: str
    detail: str
    required: bool = True


def run_diagnostics() -> list[Diagnostic]:
    """Inspect the runtime without making network calls or exposing secrets."""
    checks: list[Diagnostic] = []

    python_ok = sys.version_info >= (3, 11)
    checks.append(
        Diagnostic(
            "Python",
            "pass" if python_ok else "fail",
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )
    )

    required_packages = {
        "langchain": "langchain",
        "langgraph": "langgraph",
        "rich": "rich",
        "requests": "requests",
        "aiohttp": "aiohttp",
    }
    missing = [label for label, module in required_packages.items() if importlib.util.find_spec(module) is None]
    checks.append(
        Diagnostic(
            "Core packages",
            "fail" if missing else "pass",
            f"missing: {', '.join(missing)}" if missing else "all required imports available",
        )
    )

    provider_modules = {
        "openai": "langchain_openai",
        "anthropic": "langchain_anthropic",
        "ollama": "langchain_ollama",
        "groq": "langchain_groq",
    }
    provider_module = provider_modules.get(config.llm_provider.lower())
    provider_installed = bool(provider_module and importlib.util.find_spec(provider_module))
    provider_issues = config.validate()
    credential_issues = [issue for issue in provider_issues if "API_KEY" in issue]
    provider_supported = provider_module is not None
    provider_detail = f"{config.llm_provider} / {config.llm_model}"
    if not provider_supported:
        provider_detail += " — unsupported provider"
    elif not provider_installed:
        provider_detail += " — integration package missing"
    elif credential_issues:
        provider_detail += " — credentials not configured"
    if not provider_supported or not provider_installed:
        provider_status = "fail"
        provider_required = True
    elif credential_issues:
        provider_status = "warn"
        provider_required = False
    else:
        provider_status = "pass"
        provider_required = True
    checks.append(Diagnostic("Configured provider", provider_status, provider_detail, required=provider_required))

    local_model = config.llm_model.lower()
    small_local_model = config.llm_provider.lower() == "ollama" and any(
        size in local_model for size in (":1b", ":2b", ":3b")
    )
    if small_local_model:
        checks.append(
            Diagnostic(
                "Model suitability",
                "warn",
                "small local model detected; use qwen3 or a stronger tool-calling model for autonomous solves",
                required=False,
            )
        )

    settings_issues = [issue for issue in provider_issues if "API_KEY" not in issue and "LLM_PROVIDER" not in issue]
    checks.append(
        Diagnostic(
            "Agent settings",
            "fail" if settings_issues else "pass",
            "; ".join(settings_issues) if settings_issues else f"iteration limit: {config.max_iterations}",
        )
    )

    missing_solvers = [
        challenge.slug
        for challenge in replayable_challenges()
        if challenge.solver_module and importlib.util.find_spec(challenge.solver_module) is None
    ]
    checks.append(
        Diagnostic(
            "Replay modules",
            "fail" if missing_solvers else "pass",
            f"missing: {', '.join(missing_solvers)}"
            if missing_solvers
            else f"{len(replayable_challenges())}/{len(CHALLENGES)} captures have importable solvers",
        )
    )

    native_tools = ("radare2", "r2", "gdb", "objdump", "strings", "unsquashfs", "docker")
    available = [tool for tool in native_tools if shutil.which(tool)]
    checks.append(
        Diagnostic(
            "Optional native tools",
            "pass" if available else "warn",
            ", ".join(available) if available else "none detected; web and core agent flows still work",
            required=False,
        )
    )

    challenge_assets = tuple(config.project_root.joinpath("Challenge").glob("*"))
    checks.append(
        Diagnostic(
            "Bundled challenge assets",
            "pass" if challenge_assets else "warn",
            f"{len(challenge_assets)} local artifact(s) found",
            required=False,
        )
    )

    return checks


def diagnostics_pass(checks: list[Diagnostic], strict: bool = False) -> bool:
    """Return whether diagnostics satisfy the selected strictness level."""
    blocking = {"fail", "warn"} if strict else {"fail"}
    return not any(check.status in blocking and (strict or check.required) for check in checks)
