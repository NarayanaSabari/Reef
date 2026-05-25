# Reef

A macOS-native, voice-first personal agent for a founder/builder — *"Siri, but it actually knows your work."* You talk to it, it remembers you, and it answers across your scattered tools through [Coral](https://withcoral.com) (locally), then nudges you when something needs you.

Reef **remembers everything and answers anything** — it does not act on your behalf (no sending/drafting). The only thing it writes is its own memory of you, locally.

> Hackathon build. The deliverable is a 3-minute demo video. See `docs/` for the full PRD, architecture, and plans.

## What it is

- **Voice-first** (Google ADK + Gemini Live, interruptible) — a single all-Python process.
- **Cross-source answers** via Coral over MCP — GitHub today; Email + Calendar via Microsoft Graph **or** Google (Gmail/Calendar).
- **Durable memory** + persistent chat thread in local SQLite.
- **Proactive** morning brief → notification → deep-link back into voice.
- **Local-first** — credentials and query execution stay on your machine.

The slide-winning beat: *"Who am I meeting today that I still owe a reply to?"* answered from a single cross-source SQL JOIN (`calendar ⋈ email`).

## Status

All 7 build phases are code-complete with tests (**52+ unit, integration suite covering the real Coral MCP connection + the showpiece JOIN**). What remains needs credentials or your Mac to verify — see **`docs/reef-credentials-and-verification.md`** (the single checklist of every secret + exactly what to test with it).

## Prerequisites

- macOS (Apple Silicon), a microphone + speaker.
- [`uv`](https://docs.astral.sh/uv/): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [Coral CLI](https://withcoral.com): `brew install withcoral/tap/coral`
- [`gh`](https://cli.github.com) authenticated (`gh auth login`) — for the GitHub source.

## Setup

```bash
# 1. Python deps + venv
uv sync

# 2. Connect data sources to Coral (local, read-only)
GITHUB_TOKEN="$(gh auth token)" coral source add github
#   Email/Calendar are added during the live pass — see docs/reef-credentials-and-verification.md §2.3 (Microsoft) / §2.4 (Google)

# 3. Secrets (never committed)
cp .env.example .env   # then fill GOOGLE_API_KEY (Gemini Live); GRAPH_TOKEN or GOOGLE_TOKEN for email/calendar
```

## Run the tests

```bash
uv run pytest                 # unit suite (no credentials/network needed)
uv run pytest -m integration  # integration (needs coral installed; Gemini test skips without GOOGLE_API_KEY)
```

## Run the app

```bash
# Requires GOOGLE_API_KEY in the environment and `coral` on PATH.
export $(grep -v '^#' .env | xargs)
uv run python -m reef.app.main
```
Then talk: *"What time is it?"*, *"Any PRs waiting on my review?"*, *"Remember I prefer brief mornings."*

For deterministic/offline demo recording, snapshot live sources to JSONL first:
```bash
uv run python scripts/snapshot.py
```

## Project layout

```
src/reef/
  config.py            Settings + paths
  audio/               PCM formats, ports, sounddevice mic/speaker adapters
  voice/               VoiceSession port, VoiceLoop, Gemini Live adapter, instructions
  agent/               clock/timer tools, Coral MCP toolset
  memory/              SQLite store + memory function tools
  shell/               deep-link, schedule, brief, notify, daily scheduler, menubar/hotkey
  onboarding/          profile + app config
  snapshot/            JSONL read/write + coral->JSONL snapshot runner
  app/main.py          entrypoint (wires everything)
coral/sources/         custom Coral specs: email/calendar (MS Graph), gcal/gmail (Google)
tests/                 unit + integration (incl. the real Coral JOIN proof)
docs/                  PRD, tech-stack, architecture, per-phase plans, credentials checklist
scripts/snapshot.py    snapshot live sources -> JSONL (offline-demo fallback)
```

## Docs

- `docs/reef-prd.md` — product requirements
- `docs/reef-architecture.md` — system design + data flow
- `docs/reef-tech-stack.md` — technology choices
- `docs/reef-credentials-and-verification.md` — **every credential + what to test with it**
- `docs/reef-implementation-plan.md` + `docs/reef-plan-phase*.md` — the build plans
