# SatQuery AI

Agentic remote-sensing query system: upload satellite imagery, ask a natural-language question, and get a routed analysis plan with an explainable debug trace. The same repo can run as **Controller**, **Model Host**, or **Full System** across LAN machines.

```text
You  -->  Frontend (Next.js)  -->  Backend (FastAPI)  -->  Validator → Router
                                        |                      |
                                        v                      v
                              Hybrid executor            Ollama planner
                              (+ paired Model Host)      (or rule fallback)
```

## Quick start (one click)

| OS | Action |
|----|--------|
| **Windows** | Double-click `START_SATQUERY.bat` |
| **macOS** | Double-click `START_SATQUERY.command` (see [docs/SETUP.md](docs/SETUP.md) if Gatekeeper blocks it) |

The launcher asks for a **device role every launch**, checks requirements, installs missing dependencies, starts the right services, and (for Controller / Full System) opens:

**http://localhost:3000**

| Doc | What it covers |
|-----|----------------|
| **[docs/SETUP.md](docs/SETUP.md)** | Install, roles, pairing, troubleshooting |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | Request flow, modules, multi-device |
| **[UPDATE_LOG.md](UPDATE_LOG.md)** | Merge handoff (validator + multi-device + live fixes) |
| **[UPDATES.md](UPDATES.md)** | Short pointer to the update log |

## Project layout

```text
SAT_Query/
├── START_SATQUERY.bat / .command   # one-click launchers
├── scripts/                        # role-aware setup + start (+ pair_host.py)
├── frontend/                       # Next.js UI + Debug Mode + node status
├── backend/                        # FastAPI, validator, hybrid executor, node/
├── router/                         # Query planner / agent core (Shiven)
├── contrib/                        # optional specialist model work-in-progress
├── data/                           # demo assets
├── docs/                           # ARCHITECTURE + SETUP
├── UPDATE_LOG.md                   # merge handoff (A/B/C)
└── training/                       # fine-tune placeholders
```

Local role/pairing state (gitignored): `.satquery/device.json`

## Manual run (if you prefer)

```bash
# Backend (Python 3.11–3.13 only — not 3.14)
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |  macOS: source .venv/bin/activate
pip install -r requirements-lite.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend (other terminal)
cd frontend
cp .env.example .env.local   # or write NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm install
npm run dev
```

Optional planner LLM: install [Ollama](https://ollama.com) and `ollama pull qwen3:4b-instruct`.

## Running SatQuery on multiple devices

Clone **the same repository** on every machine. Run the same startup script. Choose a role **every** launch (cleared on exit — not reused).

| Role | What starts | Models |
|------|-------------|--------|
| **Controller** | Frontend + FastAPI + router + small planner Qwen (`qwen3:4b-instruct`) | Does **not** pull the large VLM |
| **Model Host** | Node API on **:8100** (foreground logs) + Ollama | Hosts **`qwen2.5vl:7b`** for VQA/captioning |
| **Full System** | Controller stack + optional local host | Pulls planner + host VLM when enabled |

**Pairing:** On Model Host, note LAN IP, port `8100`, and pairing code. On Controller (startup prompt or):

```bash
python scripts/pair_host.py <host-ip> 8100 <pairing-code>
```

Flow: UI → `/api/analyze` → validator → router → `HybridPipelineExecutor` → paired Model Host `/node/inference` (images as base64; GeoTIFF converted to PNG on the host) → Ollama VLM → answer + Debug (`Execution: REMOTE`). Sidebar shows Model Host connected / VLM ready.

**Change role:** close the launcher (`Ctrl+C`) and run it again — role is asked every time.

Startup still **checks before installing**: existing venv, `node_modules`, and Ollama models are not re-downloaded if already present.

## Status

- **Validation:** Pre-router hard checks (`VALID` / `WARNING` / `INVALID` / …) — see `SatQuery_Validator_Hard_Debug_Spec.md`
- **Routing / planning:** Shiven QueryPlanner (Ollama Qwen3 → rule fallback); multi-part analytical questions stay **one VQA** (not spurious captioning + grounding/SAM)
- **VQA / captioning (distributed):** Model Host Ollama tag `qwen2.5vl:7b` via `/node/inference`
- **Local specialist weights:** optional; default `SKIP_MODEL_INFERENCE=true` with honest Debug metadata when no remote host is paired
- **UI:** map, chat, Debug Mode, remote node status in the sidebar
