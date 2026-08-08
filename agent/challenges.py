"""Canonical challenge portfolio metadata used by the CLI and tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Challenge:
    """A captured competition challenge and its available evidence."""

    slug: str
    name: str
    category: str
    technique: str
    flag: str
    solver_module: str | None
    aliases: tuple[str, ...] = ()

    @property
    def evidence(self) -> str:
        """Return the strongest evidence artifact currently in the repository."""
        return "Replay solver" if self.solver_module else "Writeup"


CHALLENGES: tuple[Challenge, ...] = (
    Challenge(
        "grimoire-heap",
        "Grimoire Heap",
        "PWN",
        "UAF + tcache poisoning",
        "UCSI26{grimoire_uaf_tcache_win_6e7291e6}",
        "solvers.grimoire_heap",
        ("grimoire_heap",),
    ),
    Challenge(
        "sandworm-vm",
        "Sandworm VM",
        "PWN",
        "VM out-of-bounds escape",
        "UCSI26{sandworm_vm_oob_escape_025a2ef7}",
        "solvers.sandworm_vm",
        ("sandworm_vm",),
    ),
    Challenge(
        "saturn-exchange",
        "Saturn Exchange",
        "WEB",
        "Asynchronous settlement race",
        "UCSI26{4sync_settlement_r4c3_110cbe1e}",
        "solvers.saturn_exchange",
        ("saturn_exchange",),
    ),
    Challenge(
        "pony-express",
        "Pony Express 500",
        "WEB",
        "Handlebars AST injection",
        "UCSI26{cve-2026-33937_h4ndl3b4rs_4st_1nj3ct10n}",
        "solvers.pony_express",
        ("pony_express",),
    ),
    Challenge(
        "temporary",
        "Temporary",
        "WEB",
        "Path traversal + template injection",
        "UCSI26{cve-2026-44705_tmp_tr4v3rs4l_g4in_1s_f0r3v3r}",
        "solvers.temporary",
        ("temporary_vault",),
    ),
    Challenge(
        "oldstock-router",
        "OldStock Router",
        "FIRM",
        "SquashFS extraction + backup leak",
        "UCSI26{0ld5t0ck_fw_b4ckup_l34k}",
        "solvers.oldstock_router",
        ("oldstock_router",),
    ),
    Challenge(
        "staffdesk",
        "StaffDesk",
        "WEB",
        "GraphQL IDOR + account reset",
        "UCSI26{gr4phql_1d0r_2_admin_t4k30v3r}",
        "solvers.staffdesk",
        ("staff_desk",),
    ),
    Challenge(
        "cerberus",
        "Cerberus Reports",
        "WEB",
        "Java deserialization + SUID",
        "UCSI26{cerberus_gadget_privesc_8630453b}",
        "solvers.cerberus",
        ("cerberus_reports",),
    ),
    Challenge(
        "helios",
        "Helios Metadata Broker",
        "WEB",
        "Redirect SSRF + IMDS credential pivot",
        "UCSI26{helios_imds_creds_pivot_e611b736}",
        None,
        ("helios-metadata-broker", "helios_metadata_broker"),
    ),
)


def challenge_by_name(name: str) -> Challenge | None:
    """Resolve a challenge by its canonical slug or a documented alias."""
    normalized = name.strip().lower()
    for challenge in CHALLENGES:
        if normalized == challenge.slug or normalized in challenge.aliases:
            return challenge
    return None


def replayable_challenges() -> tuple[Challenge, ...]:
    """Return challenges that have a deterministic replay module."""
    return tuple(challenge for challenge in CHALLENGES if challenge.solver_module)
