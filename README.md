# OtomenTiga CTF Agent

> One challenge prompt in. Tool-driven investigation, exploit execution, and a reproducible flag path out.

Built by **Team OtomenTiga** for the **UCSI Agentic AI CTF Hackathon 2026**.

**8 captured flags** · **13 callable tools** · **4 LLM providers** · **2 execution modes** · **1 reusable agent workflow**

[Results](#captured-flags) · [Judge demo](#judge-demo) · [How it works](#how-it-works) · [Setup](#setup) · [Usage](#usage) · [Writeups](docs/writeup.md) · [Slides](presentation/index.html)

---

## Why this project stands out

This is not a chat wrapper around an LLM. It is a working CTF harness that lets a model inspect evidence, choose security tools, execute actions, observe results, and iterate through a LangGraph ReAct loop.

| Capability | What the project delivers |
|---|---|
| **Agentic execution** | The LLM selects and invokes 13 file, web, network, binary-analysis, encoding, and code-execution tools. |
| **Broad CTF coverage** | Recorded solutions span web exploitation, binary exploitation, firmware analysis, race conditions, GraphQL authorization, template injection, and Java deserialization. |
| **Two execution modes** | Use the autonomous agent for discovery, then replay a captured technique with a deterministic challenge solver. |
| **Provider freedom** | Switch between OpenAI, Anthropic, Ollama, and Groq without changing the agent workflow. |
| **Reproducible proof** | Eight captured flags are registered in the CLI and backed by challenge-specific solver modules. |
| **Local-first option** | Ollama can run the reasoning model locally, which is useful for privacy, cost control, and offline experimentation. |

The result is a practical loop from **reasoning** to **real tool use** to **repeatable exploitation**, rather than a one-off answer that cannot be demonstrated again.

---

## Judge demo

> **The 20-second pitch:** Most AI security demos stop at advice. OtomenTiga CTF Agent closes the loop: the model reasons, calls real security tools, adapts to their output, captures the exploit path, and turns the win into a solver that judges can replay.

From a configured environment, these commands show the complete story:

```bash
# 1. Show the captured challenge portfolio
python run.py challenges

# 2. Show the pluggable reasoning backends
python run.py providers

# 3. Replay a real exploit against an authorized, live CTF target
python run.py solver saturn-exchange

# 4. Launch the autonomous agent on a new challenge
python run.py solve --challenge "Describe the challenge here" --category web --host TARGET_HOST --port TARGET_PORT
```

### Showcase: Saturn Exchange

We independently re-ran the Saturn solver against the live challenge service and reproduced the full exploit:

```text
POST /api/reset
        ↓
balance = 1 BTC, pending = 0
        ↓
queue multiple 0.6 BTC withdrawals before batch settlement
        ↓
pending withdrawals are accepted without reserving the balance
        ↓
settlement subtracts more than the account owns
        ↓
balance = -0.8 BTC, pending = 0
        ↓
UCSI26{4sync_settlement_r4c3_110cbe1e}
```

This is a strong demo of the platform because it combines API discovery, session handling, concurrent HTTP requests, timing-sensitive settlement, state polling, and flag extraction. Two rapid `0.6 BTC` requests are enough to make the balance negative; the replay solver sends three requests to trigger the condition reliably.

```bash
python run.py solver saturn-exchange
```

Expected success evidence:

```text
Initial balance: 1 BTC
Total withdrawal: 1.8 BTC
Balance: -0.8, Pending: 0
FLAG FOUND: UCSI26{4sync_settlement_r4c3_110cbe1e}
```

> Remote replay requires the competition target to remain online. Only run the harness against systems you are authorized to test.

---

## Captured flags

The repository currently records **eight challenge captures** across three major CTF domains.

| # | Challenge | Domain | Exploit technique | Reproducible solver |
|---:|---|---|---|---|
| 1 | Grimoire Heap | PWN | Use-after-free and tcache poisoning | [`grimoire_heap.py`](solvers/grimoire_heap.py) |
| 2 | Sandworm VM | PWN | Virtual-machine out-of-bounds escape | [`sandworm_vm.py`](solvers/sandworm_vm.py) |
| 3 | Saturn Exchange | WEB | Asynchronous settlement race | [`saturn_exchange.py`](solvers/saturn_exchange.py) |
| 4 | Pony Express 500 | WEB | Handlebars AST injection | [`pony_express.py`](solvers/pony_express.py) |
| 5 | Temporary | WEB | Path traversal and template abuse | [`temporary.py`](solvers/temporary.py) |
| 6 | OldStock Router | FIRMWARE | SquashFS extraction and backup-secret discovery | [`oldstock_router.py`](solvers/oldstock_router.py) |
| 7 | StaffDesk | WEB | GraphQL IDOR and account reset | [`staffdesk.py`](solvers/staffdesk.py) |
| 8 | Cerberus Reports | WEB | Java deserialization and SUID privilege escalation | [`cerberus.py`](solvers/cerberus.py) |

Run `python run.py challenges` to display the recorded flags in the terminal. Full explanations are available in the [challenge writeups](docs/writeup.md).

---

## Two ways to solve

### 1. Autonomous discovery

Use `solve` when the vulnerability or exploit is not yet known. The model receives the challenge description and target context, selects tools, evaluates their output, and continues until it finds a flag or reaches the iteration limit.

```bash
python run.py solve \
  --challenge "Saturn Exchange batches withdrawals for settlement. Can you scam the exchange?" \
  --category web \
  --host 52.76.96.108 \
  --port 3000 \
  --max-iterations 25
```

For a file-based challenge, give the agent the relevant artifacts:

```bash
python run.py solve \
  --challenge "Analyze this binary and capture the flag" \
  --category pwn \
  --files ./challenge/vuln ./challenge/libc.so.6
```

### 2. Deterministic replay

Use `solver` after a technique has been captured. Solver mode does not require an LLM: it reruns the challenge-specific exploit and provides a fast, repeatable demonstration.

```bash
python run.py solver grimoire-heap
python run.py solver sandworm-vm
python run.py solver saturn-exchange
python run.py solver pony-express
python run.py solver temporary
python run.py solver oldstock-router
python run.py solver staffdesk
python run.py solver cerberus
```

This dual-mode design is deliberate: the agent explores, while the solver preserves the successful path as executable evidence.

---

## How it works

```text
Challenge description + files + target
                  │
                  ▼
        ┌───────────────────┐
        │  LangGraph agent  │
        │ reason and decide │
        └─────────┬─────────┘
                  │ tool call
                  ▼
┌─────────────────────────────────────────────┐
│ 13 callable tools                           │
│ files · binaries · code · TCP · HTTP · race │
└──────────────────────┬──────────────────────┘
                       │ observation
                       ▼
            continue reasoning or finish
                       │
                       ▼
             flag extraction + CLI result
```

The core graph has two cooperating nodes:

1. **Reason** — the selected chat model analyzes the accumulated messages and either requests tools or returns an answer.
2. **Tools** — LangGraph executes the requested functions and sends their observations back to the model.

The loop is bounded by `MAX_ITERATIONS`. A successful path can then be preserved in `solvers/` for deterministic replay.

### Tool arsenal

| Area | Agent tools |
|---|---|
| Binary analysis | `analyze_binary`, `list_functions`, `get_strings`, `checksec` |
| Exploit execution | `execute_python_code`, `execute_script_file` |
| Network | `tcp_connect_and_interact` |
| Web | `http_request`, `concurrent_requests` |
| Files and transforms | `read_file`, `write_file`, `hex_encode`, `hex_decode` |

### Agent lifecycle

```text
observe → analyze → choose a tool → act → inspect evidence → adapt → verify
```

That feedback loop lets the same harness pivot between very different tasks: disassembling an ELF, racing an API, unpacking firmware, probing GraphQL, or constructing an exploit script.

---

## Setup

### Prerequisites

- Python 3.11 or newer
- One LLM backend for autonomous mode:
  - an OpenAI, Anthropic, or Groq API key; or
  - a running local Ollama instance
- Optional native tools for PWN challenges: radare2, GDB, `objdump`, and a compiler
- Live, authorized challenge targets for remote solver replays

Deterministic solver mode does not require an LLM unless that individual solver says otherwise.

### 1. Clone the repository

```bash
git clone https://github.com/H0l3yM0l3h/OtomenTigaUCSI-AI-Agent.git
cd OtomenTigaUCSI-AI-Agent
```

### 2. Create the environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Linux or macOS:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

### 3. Configure one provider

Edit `.env` and choose one configuration.

OpenAI:

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=your-key
```

Anthropic:

```dotenv
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=your-key
```

Groq:

```dotenv
LLM_PROVIDER=groq
LLM_MODEL=llama-3.1-70b-versatile
GROQ_API_KEY=your-key
```

Local Ollama:

```bash
ollama pull llama3.2:3b
```

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:3b
OLLAMA_BASE_URL=http://localhost:11434
```

`llama3.2:3b` is suitable for a local smoke test. For difficult autonomous exploitation, use a stronger tool-calling model; small local models can choose poor tools or return unverified answers.

### 4. Verify the installation

```bash
python -m pip check
python run.py providers
python run.py challenges
```

For Ollama, also verify that the configured model is available:

```bash
ollama list
```

---

## Usage

```text
python run.py solve --challenge TEXT [options]
python run.py solver NAME
python run.py providers
python run.py challenges
```

Useful `solve` options:

| Option | Purpose |
|---|---|
| `--category web` | Choose `pwn`, `web`, `rev`, `crypto`, or `misc`. |
| `--host HOST` / `--port PORT` | Supply a remote challenge endpoint. |
| `--files FILE [FILE ...]` | Give the agent binaries, archives, source, or other artifacts. |
| `--provider NAME` | Override the provider configured in `.env`. |
| `--model NAME` | Override the configured model. |
| `--max-iterations N` | Bound the number of reasoning passes. |
| `--quiet` | Suppress verbose reasoning and tool output. |

Show the full CLI reference at any time:

```bash
python run.py --help
python run.py solve --help
```

---

## Execution and verification notes

- Run this project only against CTF infrastructure or systems where you have explicit authorization.
- The default generated-code tool runs Python in a local subprocess with a timeout, isolated working directory, and output limit. It is **not** a hardened security boundary.
- `agent/sandbox.py` and `agent/loop_detect.py` contain experimental Docker-sandbox and loop-detection components; they are not connected to the default LangGraph execution path yet.
- Autonomous mode currently recognizes strings matching `UCSI26{...}`. For competition evidence, confirm that a flag came from target output or replay it through the deterministic solver instead of trusting a model-generated string alone.
- Binary-analysis features require their native executables in addition to the Python wrappers.

These boundaries keep the demo honest and make the next engineering improvements clear.

---

## Project structure

```text
├── run.py                    # Rich CLI: solve, replay, providers, results
├── agent/
│   ├── core.py               # LangGraph reason ↔ tool loop
│   ├── llm.py                # OpenAI, Anthropic, Ollama, Groq adapters
│   ├── prompts.py            # Category-aware CTF instructions
│   ├── config.py             # .env and runtime configuration
│   ├── tools/                # 13 LangChain-callable security tools
│   ├── sandbox.py            # Experimental Docker execution component
│   └── loop_detect.py        # Experimental repetition detector
├── solvers/                  # Eight replayable challenge techniques
├── docs/
│   ├── writeup.md            # Challenge analysis and exploitation details
│   └── architecture.md       # Deeper system design
├── presentation/index.html  # Competition presentation
├── requirements.txt
└── .env.example
```

---

## Troubleshooting

| Symptom | Check |
|---|---|
| `ModuleNotFoundError` | Activate the virtual environment and rerun `pip install -r requirements.txt`. |
| Ollama connection error | Run `ollama serve`, then confirm the model appears in `ollama list`. |
| Model not found | Make `LLM_MODEL` exactly match an installed or provider-supported model ID. |
| Binary tool unavailable | Install the native radare2, GDB, or binutils executable and ensure it is on `PATH`. |
| Agent stops without a flag | Add relevant files/target details, increase the iteration cap, or use a stronger tool-calling model. |
| Replay cannot connect | Confirm the competition service is still online and the target in the solver is current. |

---

## Competition submission

- **Team:** OtomenTiga
- **Repository:** [H0l3yM0l3h/OtomenTigaUCSI-AI-Agent](https://github.com/H0l3yM0l3h/OtomenTigaUCSI-AI-Agent)
- **Writeups:** [`docs/writeup.md`](docs/writeup.md)
- **Architecture:** [`docs/architecture.md`](docs/architecture.md)
- **Presentation:** [`presentation/index.html`](presentation/index.html)
- **Stack:** Python, LangGraph, LangChain, OpenAI, Anthropic, Ollama, Groq, pwntools, radare2/r2pipe, requests, aiohttp, Rich, Click, and Pydantic

Before final submission, confirm that the repository is public and export the presentation/writeup to the format required by the organizers.

---

## Responsible use

This project was created for educational CTF work and authorized security testing. Do not use it against systems without explicit permission.
