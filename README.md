# SatQuery AI

Agentic remote-sensing query system: upload satellite imagery, ask a natural-language question, and get a routed analysis plan with an explainable debug trace.

```text
You  -->  Frontend (Next.js)  -->  Backend (FastAPI)  -->  Router (planner)
                                        |                      |
                                        v                      v
                                   Debug trace            Ollama Qwen3
                                   + model stubs          (or rule fallback)
```

## Quick start (one click)

| OS | Action |
|----|--------|
| **Windows** | Double-click `START_SATQUERY.bat` |
| **macOS** | Double-click `START_SATQUERY.command` (see [docs/SETUP.md](docs/SETUP.md) if Gatekeeper blocks it) |

The launcher checks requirements, installs missing dependencies, starts the API + UI, and opens:

**http://localhost:3000**

Full machine-specific notes: **[docs/SETUP.md](docs/SETUP.md)**  
How the system works (flowcharts): **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**  
Latest validation hardening notes: **[UPDATES.md](UPDATES.md)**

## Project layout

```text
SAT_Query/
├── START_SATQUERY.bat / .command   # one-click launchers
├── scripts/                        # shared setup + start logic
├── frontend/                       # Next.js UI + Debug Mode
├── backend/                        # FastAPI + Shiven adapter
├── router/                         # Query planner / agent core (Shiven)
├── contrib/                        # optional specialist model work-in-progress
├── data/                           # demo assets
├── docs/                           # ARCHITECTURE + SETUP
└── training/                       # fine-tune placeholders
```

## Manual run (if you prefer)

```bash
# Backend
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

Clone **the same repository** on every machine. Run the same startup script. Choose a role once (saved under `.satquery/`, gitignored).

| Role | What starts | Models |
|------|-------------|--------|
| **Controller** | Frontend + FastAPI + router + small planner Qwen (`qwen3:4b-instruct`) | Does **not** pull the large VLM |
| **Model Host** | Node API (`/node/*`) + Ollama | Hosts **`qwen2.5vl:7b`** (Qwen2.5-VL-7B Instruct) for VQA/captioning |
| **Full System** | Controller stack + optional local host | Pulls planner + host VLM when enabled |

**Pairing:** On Model Host, note LAN IP, port `8100`, and pairing code. On Controller (startup prompt or):

```bash
python scripts/pair_host.py <host-ip> 8100 <pairing-code>
```

Queries still go through the normal UI → `/api/analyze` → existing router → node registry → Model Host → Ollama VLM → answer + Debug trace (`Execution: REMOTE`).

**Change role:** close the launcher (`Ctrl+C`) and run it again — role is asked **every** launch and cleared on exit (no reuse).

Startup still **checks before installing**: existing venv, `node_modules`, and Ollama models are not re-downloaded if already present.

## Status

- **Routing / planning:** Shiven QueryPlanner (Ollama Qwen3 → rule fallback)
- **VQA / captioning (distributed):** Model Host Ollama tag `qwen2.5vl:7b` (Qwen2.5-VL-7B Instruct) via SatQuery `/node/inference` (not raw Ollama from the Controller)
- **Local specialist weights:** optional; default `SKIP_MODEL_INFERENCE=true` with honest Debug metadata when no remote host is paired
- **UI:** map, chat, Debug Mode, remote node status in the sidebar