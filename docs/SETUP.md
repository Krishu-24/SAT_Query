# Setup & run instructions

One-click launch on **Windows** and **macOS**, plus manual fallback and troubleshooting.

---

## Requirements

| Tool | Version | Required? | Notes |
|------|---------|-----------|-------|
| Python | **3.11–3.13** (3.12 recommended) | Yes | Backend API. **Not 3.14** — pydantic-core has no wheels / PyO3 build fails. Launcher creates `backend/.venv` with pinned `requirements-lite.txt`. |
| Node.js | 18+ LTS | Yes | Frontend |
| npm | comes with Node | Yes | |
| Ollama | latest | Optional | Powers the small Qwen3 planner; without it, rule-based fallback still works |
| Disk | ~2–5 GB free | Yes | More if pulling the Ollama model |
| GPU | — | No | Not needed for the current demo path |

---

## One-click (recommended)

### Windows

1. Open the repo folder `SAT_Query`.
2. Double-click **`START_SATQUERY.bat`**.
3. Wait for checks / installs (first run is longest: `pip` + `npm` + optional model pull).
4. Browser should open **http://localhost:3000**.
5. Leave the console open. Press **Ctrl+C** to stop.

If PowerShell blocks scripts, the `.bat` already uses `-ExecutionPolicy Bypass` for this file only.

### macOS

1. Open the repo folder in Finder.
2. First time only — allow the launcher:
   - Right-click **`START_SATQUERY.command`** → **Open** → confirm,  
     **or** in Terminal:
     ```bash
     chmod +x START_SATQUERY.command scripts/start-satquery.sh
     xattr -d com.apple.quarantine START_SATQUERY.command 2>/dev/null || true
     ```
3. Double-click **`START_SATQUERY.command`**.
4. Wait for setup; browser opens **http://localhost:3000**.
5. Leave the Terminal window open. **Ctrl+C** stops services.

Optional Homebrew helpers (used automatically when present):

```bash
brew install python@3.12 node
# Ensure python3.12 is on PATH (Homebrew may not replace default python3 if it is 3.14)
brew install --cask ollama
```

If setup fails on `pydantic-core` / Python 3.14:

```bash
brew install python@3.12
rm -rf backend/.venv
# re-run START_SATQUERY.command — it prefers python3.12 and recreates the venv
```

---

## What success looks like

Console should print something like:

```text
OPEN THE WEBSITE:
http://localhost:3000

Backend API:   http://127.0.0.1:8000
Swagger docs:  http://127.0.0.1:8000/docs
```

In the UI:

1. Turn on **Debug Mode** (sidebar bug icon).
2. Type e.g. `Locate the water bodies then describe the image.`
3. Expect answer **`Model not available`**.
4. In Debug: intent decomposition, selected models with **`model not loaded`**, and a **fallback** badge if Ollama is down.

---

## Manual run (developers)

### Backend

```bash
cd backend
python3 -m venv .venv          # Windows: python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-lite.txt

export USE_SHIVEN_ROUTER=true
export SKIP_MODEL_INFERENCE=true
export SHIVEN_ROUTER_ROOT="$(pwd)/../router"   # Windows: set SHIVEN_ROUTER_ROOT=...\router

uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" > .env.local
npm install
npm run dev
```

### Optional Ollama planner

```bash
ollama serve
ollama pull qwen3:4b-instruct
```

---

## Environment variables

| Name | Where | Default | Purpose |
|------|-------|---------|---------|
| `NEXT_PUBLIC_API_URL` | `frontend/.env.local` | `http://127.0.0.1:8000` | UI → API |
| `USE_SHIVEN_ROUTER` | backend env | `true` | Use `router/` planner |
| `SKIP_MODEL_INFERENCE` | backend env | `true` | Skip loading specialist weights |
| `SHIVEN_ROUTER_ROOT` | backend env | `<repo>/router` | Planner package path |
| `OLLAMA_BASE_URL` | backend env | `http://127.0.0.1:11434` | Planner LLM |
| `OLLAMA_PLANNER_MODEL` | backend env | `qwen3:4b-instruct` | Model tag |
| `SATQUERY_DEBUG` | backend env | off | Always attach payload snapshots |

To try real stub model execution later: `SKIP_MODEL_INFERENCE=false` (still not full satellite VLMs unless weights are installed).

---

## Things to look out for

| Issue | What you’ll see | Fix |
|-------|-----------------|-----|
| Port 3000 or 8000 busy | Launcher / bind error | Close other apps using those ports; re-run (launcher tries to free them on Windows) |
| Node not installed | Setup fails at npm | Install Node LTS from https://nodejs.org/ then re-run |
| Python too old / **3.14** | `pydantic-core` build fails / PyO3 max 3.13 | `brew install python@3.12` (Mac) or install 3.12 (Windows); `rm -rf backend/.venv`; re-run launcher |
| Ollama missing | Amber **fallback** in Debug | Optional — install Ollama or ignore; routing still works |
| macOS “cannot be opened” | Gatekeeper | `chmod +x` + right-click Open / remove quarantine (above) |
| Blank UI / network error | “Couldn’t reach the backend” | Confirm `:8000` health: http://127.0.0.1:8000/api/health |
| Two FastAPI apps | Confusing routes | Do **not** also `uvicorn` inside `router/` for the demo |
| Spaces in path | Rare tool issues | Prefer cloning to a path without spaces when possible |
| First `npm install` slow | Long wait | Normal; watch `scripts/logs/frontend*.log` |
| Windows execution policy | Script blocked | Use the `.bat` (Bypass is already set) |
| Antivirus locks `node_modules` | Install/delete fails | Pause real-time scan briefly or re-run as admin |

Logs live in **`scripts/logs/`** (`backend.log`, `frontend.log`, `last-run.json`).

---

## Project tree (after cleanup)

```text
SAT_Query/
├── START_SATQUERY.bat          Windows one-click
├── START_SATQUERY.command      macOS one-click
├── README.md
├── docs/
│   ├── ARCHITECTURE.md         how it works (flowcharts)
│   └── SETUP.md                this file
├── scripts/
│   ├── start-satquery.ps1
│   ├── start-satquery.sh
│   └── logs/                   runtime logs (gitignored)
├── frontend/                   Next.js UI
├── backend/                    FastAPI + adapter
├── router/                     planner / agent package
├── contrib/                    optional model WIP
├── data/
└── training/
```

---

## Stopping

- One-click window: **Ctrl+C**
- Manual: stop the two terminals running `uvicorn` and `npm run dev`
- Ollama can keep running in the background if you use it for other projects
