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

## Status

- **Routing / planning:** Shiven QueryPlanner (Ollama Qwen3 → rule fallback)
- **Specialist CV/VLM weights:** not required for the demo — responses return `Model not available` with honest Debug metadata (`model not loaded`)
- **UI:** map, chat, Debug Mode, synthetic location fallback kept for demo polish
