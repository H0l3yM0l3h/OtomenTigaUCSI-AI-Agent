# UCSI Agentic AI CTF 2026 — Agent Harness

> **Autonomous AI agent that analyzes and solves Capture The Flag (CTF) challenges**  
> Built for the UCSI Agentic AI Hackathon 2026

---

## 🏆 Results

| # | Challenge | Category | Technique | Flag |
|---|-----------|----------|-----------|------|
| 1 | Grimoire Heap | PWN | UAF + tcache poisoning | `UCSI26{grimoire_uaf_tcache_win_6e7291e6}` |
| 2 | Sandworm VM | PWN | VM OOB escape | `UCSI26{sandworm_vm_oob_escape_025a2ef7}` |
| 3 | Saturn Exchange | WEB | Async race condition | `UCSI26{4sync_settlement_r4c3_110cbe1e}` |
| 4 | Pony Express 500 | WEB | Handlebars AST injection (CVE-2026-33937) | `UCSI26{cve-2026-33937_h4ndl3b4rs_4st_1nj3ct10n}` |
| 5 | Temporary | WEB | Path traversal + templates | `UCSI26{cve-2026-44705_tmp_tr4v3rs4l_g4in_1s_f0r3v3r}` |
| 6 | OldStock Router | FIRM | Firmware SquashFS extract | `UCSI26{0ld5t0ck_fw_b4ckup_l34k}` |
| 7 | StaffDesk | WEB | GraphQL IDOR + Account Reset | `UCSI26{gr4phql_1d0r_2_admin_t4k30v3r}` |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   CLI (run.py)                   │
├─────────────────────────────────────────────────┤
│              Agent Core (ReAct Loop)             │
│         analyze → plan → exploit → verify        │
├──────────┬──────────┬───────────┬───────────────┤
│ Binary   │ Code     │ Network   │ Web           │
│ Analysis │ Executor │ Client    │ Tools         │
│ (r2pipe) │ (subproc)│ (socket)  │ (requests)    │
├──────────┴──────────┴───────────┴───────────────┤
│            LLM Provider (Pluggable)              │
│   OpenAI  │  Anthropic  │  Ollama  │  Groq      │
└─────────────────────────────────────────────────┘
```

The agent uses a **ReAct (Reasoning + Acting)** loop built with **LangGraph**:

1. **Observe** — Read challenge description, examine files, probe services
2. **Analyze** — Identify vulnerability class and attack surface
3. **Plan** — Formulate exploitation strategy
4. **Exploit** — Execute attack using available tools
5. **Verify** — Extract and validate the flag (`UCSI26{...}`)

### 🔁 Detailed Agent Execution Flow

The harness orchestrates the solver loop through a state transition model:
```
           ┌──────────────────────┐
           │     1. Observe       │ ◄─── (Check challenge descriptions & distfiles)
           └──────────┬───────────┘
                      ▼
           ┌──────────────────────┐
           │     2. Analyze       │ ◄─── (Categorize & run checksec / r2 analysis)
           └──────────┬───────────┘
                      ▼
           ┌──────────────────────┐
           │      3. Plan         │ ◄─── (Formulate binary or HTTP exploit payload)
           └──────────┬───────────┘
                      ▼
           ┌──────────────────────┐
 ┌────────►│     4. Exploit       ├────────┐
 │         └──────────────────────┘        │
 │                    │                    │
 │ (No flag           ▼ (Tool Call)        │ (Flag found
 │  & iterations <   ┌──────────────────────┐      │  or max iterations)
 │  MAX_ITERATIONS)  │   Execute Tool &     │      │
 └───────────────────┤   Check for Loop     │      ▼
                     └──────────┬───────────┘ ┌──────────────┐
                                ▼             │   5. Verify  │
                     [ Anti-Loop Check ] ────►│   & Extract  │
                                              └──────────────┘
```

### 🐳 Isolation & Sandboxed Execution
To safely run generated exploit scripts (which may contain arbitrary commands, shellcode, or unsafe networking logic), the harness uses a **Docker Sandbox** isolation model:
- **Workspace Bindings:** Mounts the solver workspace (Read/Write) and challenge binaries/distfiles (Read-Only).
- **Execution Controls:** Configures custom limits (default: 4GB memory, 2 CPUs) and executes commands via the sandbox API.
- **Degradation Fallback:** Automatically falls back to local execution with custom timeout protections if Docker is not available in the host environment.

### ⚠️ Loop Detection & Prevention
To prevent LLMs from entering infinite execution loops (e.g. calling `read_file` repeatedly when a file is missing or a tool fails), the harness implements a **hash-based loop detector**:
1. Keeps a sliding window of recent tool names and argument hashes.
2. Injects a warning prompt (`⚠️ LOOP DETECTED...`) after 3 consecutive identical operations, instructing the LLM to change its approach.
3. Aborts and cleans up the run if identical calls repeat 5 times to prevent token waste.

---

## 📋 Project Structure

```
├── run.py                        # CLI entry point
├── agent/
│   ├── core.py                   # ReAct agent loop (LangGraph)
│   ├── llm.py                    # LLM provider abstraction
│   ├── prompts.py                # CTF-specialized system prompts
│   ├── config.py                 # Configuration management
│   ├── utils.py                  # Flag extraction, hex utilities
│   └── tools/
│       ├── binary_analysis.py    # r2pipe / objdump / pwntools
│       ├── code_executor.py      # Sandboxed Python execution
│       ├── network_client.py     # TCP/UDP interaction
│       ├── web_tools.py          # HTTP + race conditions
│       └── file_tools.py         # File I/O + encoding
├── solvers/
│   ├── grimoire_heap.py          # PWN: UAF + tcache poisoning
│   ├── sandworm_vm.py            # PWN: VM OOB escape
│   ├── saturn_exchange.py        # WEB: Async race condition
│   └── pony_express.py           # WEB: Handlebars AST injection
├── docs/
│   ├── writeup.md                # Full challenge writeups
│   └── architecture.md           # Agent design documentation
├── presentation/
│   └── index.html                # Reveal.js slide deck
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- An LLM API key (OpenAI, Anthropic, Groq) or local Ollama instance

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/ucsi-ctf-agent-2026.git
cd ucsi-ctf-agent-2026

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
# or: venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure your LLM provider
cp .env.example .env
# Edit .env with your API key
```

### Usage

```bash
# Solve a challenge with the AI agent
python run.py solve \
  --challenge "A banished spell is supposed to be gone. Is it really?" \
  --category pwn \
  --host 52.76.96.108 \
  --port 9005

# Use a specific LLM provider
python run.py solve \
  --challenge "..." \
  --category web \
  --provider ollama \
  --model llama3.1:70b

# Run a pre-built solver
python run.py solver grimoire-heap
python run.py solver sandworm-vm
python run.py solver saturn-exchange
python run.py solver pony-express
python run.py solver temporary
python run.py solver oldstock-router
python run.py solver staffdesk

# List all solved challenges
python run.py challenges

# Show supported LLM providers
python run.py providers
```

---

## 📌 Hackathon Submission Checklist

Use the exact fields below in your final submission package. Replace the bracketed values with the real team details before exporting the PDF or uploading the repository.

1. Team Name — OtomenTiga
2. GitHub Repository Link — https://github.com/H0l3yM0l3h
3. Team Leader Account — Uploaded from the registered team leader's GitHub account
4. Presentation Slides / Documentation / Writeup — [PDF or PowerPoint slide deck plus writeup]
5. Technology Stack — Python, LangGraph, LangChain, OpenAI, Anthropic, Ollama, Groq, radare2, r2pipe, pwntools, requests, aiohttp, Rich, Click, python-dotenv

For a fast final pass, fill these placeholders, export the slide deck, and verify the repository is public.

---

## 🤖 Technology Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Language** | Python 3.11+ | Core implementation |
| **Agent Framework** | LangGraph + LangChain | ReAct reasoning loop & tool orchestration |
| **LLM (Cloud)** | OpenAI GPT-4o | Primary reasoning engine |
| **LLM (Cloud)** | Anthropic Claude | Alternative reasoning engine |
| **LLM (Open Source)** | Llama 3.1 via Ollama | Local open-source inference |
| **LLM (Fast OSS)** | Groq (Llama 3.1 70B) | Fast cloud inference for open-source models |
| **Binary Analysis** | radare2 + r2pipe | Disassembly, decompilation, binary inspection |
| **Exploit Dev** | pwntools | Binary exploitation & payload construction |
| **Web Exploitation** | requests + aiohttp | HTTP requests & concurrent race conditions |
| **CLI Interface** | Rich + Click | Terminal UI, logging, colored output |
| **Configuration** | python-dotenv | Environment variable management |
| **Data Validation** | Pydantic | Structured data handling |

---

## 🔧 LLM Provider Support

The agent is provider-agnostic. Switch LLMs via `.env` or CLI flags:

| Provider | Models | Setup |
|----------|--------|-------|
| **OpenAI** | `gpt-4o`, `gpt-4o-mini` | Set `OPENAI_API_KEY` in `.env` |
| **Anthropic** | `claude-sonnet-4-20250514`, `claude-opus-4-20250514` | Set `ANTHROPIC_API_KEY` in `.env` |
| **Ollama** | `llama3.1:70b`, `deepseek-coder-v2`, `mistral` | Install [Ollama](https://ollama.com), pull model |
| **Groq** | `llama-3.1-70b-versatile` | Set `GROQ_API_KEY` in `.env` |

### Using Ollama (Open Source, Free, Local)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.1:70b

# Configure the agent
echo 'LLM_PROVIDER=ollama' >> .env
echo 'LLM_MODEL=llama3.1:70b' >> .env

# Run
python run.py solve --challenge "..." --category pwn
```

---

## 📖 Documentation

- [**Challenge Writeups**](docs/writeup.md) — Detailed analysis and solutions for each challenge
- [**Architecture Guide**](docs/architecture.md) — Agent design, tool integration, prompt engineering
- [**Presentation Slides**](presentation/index.html) — Open in browser for the slide deck

---

## 📄 License

This project was created for the UCSI Agentic AI CTF Hackathon 2026.  
For educational and authorized security testing purposes only.
