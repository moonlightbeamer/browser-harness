# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (editable, so code changes are picked up immediately)
uv tool install -e .

# Run all tests
pytest tests/

# Run a single test
pytest tests/unit/test_helpers.py::test_wait_for_network_idle_filters_events_to_active_session

# Run integration tests (requires a live browser + daemon)
pytest tests/integration/

# Diagnose install, daemon, and browser state
browser-harness --doctor

# Update to latest and restart daemon
browser-harness --update -y

# Reload the daemon (picks up code changes in agent-workspace/agent_helpers.py)
browser-harness --reload
```

## Architecture

The system has three layers that communicate at runtime:

```
Chrome (CDP WS) ──► daemon.py (long-lived process) ──► helpers.py (-c scripts)
                       holds single WS connection          IPC: one JSON line each way
```

**`_ipc.py`** — Transport layer. Unix socket at `/tmp/bu-<NAME>.sock` on POSIX, TCP loopback + port file on Windows. All IPC is one JSON line per request, one per response. Windows uses a random port + a 64-char hex token in every request to guard the loopback boundary; POSIX relies on `chmod 600` on the socket.

**`daemon.py`** — The only process that holds the CDP WebSocket. Maintains a single `(session_id, target_id)` pair — the "currently attached tab". Handles both CDP pass-through (`{method, params, session_id}`) and meta-commands (`{meta: "ping"|"set_session"|"session"|"drain_events"|"shutdown"|...}`). `Target.*` calls are always browser-level (no session), all others default to the attached session. Stale session errors auto-recover via `attach_first_page()`.

**`helpers.py`** — CDP wrapper functions imported into every `-c` script. Each function calls `_send()` which opens a fresh IPC connection, sends one request, reads one response, and closes. Auto-loads `agent-workspace/agent_helpers.py` at import time, merging any public names into its own namespace.

**`admin.py`** — Daemon lifecycle: `ensure_daemon()` (idempotent, self-healing), `restart_daemon()` (stop-only, despite the name), `start_remote_daemon()` (provisions a Browser Use cloud browser and wires up BU_CDP_WS), `run_doctor()`, `run_update()`, version check/cache.

**`run.py`** — The `browser-harness` CLI. Parses flags (`--doctor`, `--update`, `--reload`, `--debug-clicks`, `-c`), calls `ensure_daemon()`, then `exec()`s the `-c` script with the entire `helpers` namespace pre-imported including everything from `agent_helpers.py`.

## Key invariants

- **One daemon per `BU_NAME`** (env var, default `"default"`). Multiple daemons can coexist with different names, each with its own IPC socket, pid file, and log file.
- **One CDP session at a time**. `switch_tab()` and `new_tab()` update the daemon via `meta: set_session` — they also enable Page/DOM/Runtime/Network on the new session and disable Network on the old one.
- **Environment is loaded from `.env`** at repo root and `agent-workspace/.env`. Both files are loaded by `_load_env()` in `daemon.py` and `helpers.py` using `setdefault` (never overwrites already-set vars).
- **`BU_CDP_WS`** overrides local Chrome discovery with an explicit WebSocket URL. **`BU_CDP_URL`** points to a DevTools HTTP endpoint (resolves WS via `/json/version`). Either blocks cloud auto-bootstrap.
- **Cloud auto-bootstrap** (`BU_AUTOSPAWN=1`) only fires when no daemon is alive, no local Chrome is listening, no explicit CDP var is set, and `BROWSER_USE_API_KEY` is present.
- **The 🐴 horse marker** is prepended to the controlled tab's title so users can see which tab the agent owns. It is `\U0001F434` — a surrogate pair in JS UTF-16, so `slice(3)` removes it cleanly.

## What belongs where

| Location | Purpose |
|---|---|
| `src/browser_harness/` | Core package — do not add task-specific logic here |
| `agent-workspace/agent_helpers.py` | Task-specific helpers the agent adds during a run |
| `agent-workspace/domain-skills/` | Per-site playbooks (agent-generated, not hand-authored) |
| `interaction-skills/` | Reusable mechanics: tabs, iframes, uploads, dialogs, etc. |

## Environment variables

| Variable | Effect |
|---|---|
| `BU_NAME` | Daemon namespace (default: `"default"`) |
| `BU_CDP_WS` | Explicit CDP WebSocket URL (skips local Chrome discovery) |
| `BU_CDP_URL` | DevTools HTTP endpoint; harness resolves WS via `/json/version` |
| `BROWSER_USE_API_KEY` | Browser Use cloud API key (remote browsers, profile sync) |
| `BU_AUTOSPAWN` | Set to `1` to auto-provision a cloud browser when no local Chrome is found |
| `BH_DOMAIN_SKILLS` | Set to `1` to enable per-site skill file surfacing in `goto_url()` |
| `BH_AGENT_WORKSPACE` | Override default `agent-workspace/` path |
| `BH_RUNTIME_DIR` | Override socket/port/pid location (must be short path on macOS for AF_UNIX) |
| `BH_TMP_DIR` | Override screenshot and log location |
| `BH_DEBUG_CLICKS` | Set to `1` to save annotated screenshots of every click |

## Code conventions (from AGENTS.md)

Priorities: **clarity, precision, low verbosity, versatility.** Prefer the smallest diff that fixes the bug. Do not add a retries framework, session manager, daemon supervisor, config system, or logging framework. `run.py` stays tiny — no argparse, subcommands, or extra control layer. Task-specific additions go in `agent-workspace/agent_helpers.py`, not in the core package.
