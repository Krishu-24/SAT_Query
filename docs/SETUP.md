# Setup & run instructions

One-click launch on **Windows** and **macOS**, role-aware multi-device setup, manual fallback, and troubleshooting.

---

## Requirements

| Tool | Version | Required? | Notes |
|------|---------|-----------|-------|
| Python | **3.11–3.13** (3.12 recommended) | Yes | Backend / Model Host API. **Not 3.14** — pydantic-core has no wheels. Launcher creates `backend/.venv` with pinned `requirements-lite.txt`. |
| Node.js | 18+ LTS | Controller / Full System | Frontend |
| npm | comes with Node | Controller / Full System | |
| Ollama | latest | Strongly recommended | Planner on Controller (`qwen3:4b-instruct`); VLM on Model Host (`qwen2.5vl:7b`) |
| Disk | ~2–5 GB+ | Yes | More when pulling the host VLM (~6 GB) |
| GPU | — | Optional | Helps Model Host VLM; not required for Controller-only demo |

---

## One-click (recommended)

Every launch asks for this machine’s role (**Controller** / **Model Host** / **Full System**). Previous `.satquery/device.json` is cleared at start and on exit — re-pair after each Controller restart.

### Windows

1. Open the repo folder `SAT_Query`.
2. Double-click **`START_SATQUERY.bat`**.
3. Pick a role when prompted.
4. Wait for checks / installs (first run is longest: `pip` + `npm` + optional model pull).
5. **Controller / Full System:** browser opens **http://localhost:3000**.  
   **Model Host:** this window stays in the foreground and prints pairing / INCOMING query logs — leave it open.
6. Press **Ctrl+C** to stop (frees ports, stops Ollama models, clears role).

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
3. Double-click **`START_SATQUERY.command`** and pick a role.
4. Same role behavior as Windows above.

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

## Multi-device (Controller + Model Host)

Typical split: Mac = Controller, Windows GPU PC = Model Host (any OS can be either role).

1. Start **Model Host** first. Note **LAN IP**, port **8100**, and **pairing code**.
2. Start **Controller**. At the pairing prompt (or later):

   ```bash
   python scripts/pair_host.py <host-ip> 8100 <pairing-code>
   ```

3. Sidebar should show **Model Host: connected** and **VLM: ready**.
4. Ask a VQA/caption question with an image. Host terminal should print `INCOMING QUERY` → Ollama → answer. Controller console mirrors OUTGOING/INCOMING from `backend.log`.

GeoTIFF uploads are converted to PNG on the Model Host before Ollama (raw TIFF is often rejected).

Full merge notes: **[UPDATE_LOG.md](../UPDATE_LOG.md)**. Spec: **[SATQUERY_MULTIDEVICE_SPEC.md](../SATQUERY_MULTIDEVICE_SPEC.md)** (implementation may differ slightly — role is asked every launch).

---

## What success looks like

### Controller / Full System

```text
OPEN THE WEBSITE:
http://localhost:3000

Backend API:   http://127.0.0.1:8000
```

In the UI:

1. Turn on **Debug Mode** (sidebar bug icon).
2. With a **paired** Model Host: ask a VQA question → expect a real answer and Debug `Execution: REMOTE`.
3. **Without** a host: expect answer **`Model not available`** / pairing hint, and Debug steps with **`model not loaded`** for specialists.
4. Multi-part analytical VQA (features + relative location + evidence) should show **one** `rs_vlm` / `answer_question` step — not grounding_dino + sam.

### Model Host

```text
SatQuery Model Host is running
  Port:          8100
  Pairing code:  ......
  Live pairing / query / answer logs will print below.
```

---

## Manual run (developers)

### Backend (Controller path)

```bash
cd backend
python3.12 -m venv .venv       # Windows: py -3.12 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-lite.txt

export USE_SHIVEN_ROUTER=true
export SKIP_MODEL_INFERENCE=true
export SHIVEN_ROUTER_ROOT="$(pwd)/../router"   # Windows: set SHIVEN_ROUTER_ROOT=...\router

uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Model Host only

```bash
cd backend
# same venv + deps
uvicorn app.node.host_app:app --host 0.0.0.0 --port 8100
```

### Frontend

```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" > .env.local
npm install
npm run dev
```

### Ollama

```bash
ollama serve
ollama pull qwen3:4b-instruct   # Controller planner
ollama pull qwen2.5vl:7b        # Model Host VLM
```

---

## Environment variables

| Name | Where | Default | Purpose |
|------|-------|---------|---------|
| `NEXT_PUBLIC_API_URL` | `frontend/.env.local` | `http://127.0.0.1:8000` | UI → API |
| `USE_SHIVEN_ROUTER` | backend env | `true` | Use `router/` planner |
| `SKIP_MODEL_INFERENCE` | backend env | `true` | Skip loading specialist weights locally |
| `SHIVEN_ROUTER_ROOT` | backend env | `<repo>/router` | Planner package path |
| `OLLAMA_BASE_URL` | backend env | `http://127.0.0.1:11434` | Local Ollama |
| `OLLAMA_PLANNER_MODEL` | backend env | `qwen3:4b-instruct` | Planner tag |
| `SATQUERY_ROLE` | optional | from `.satquery/` | `controller` / `model_host` / `full_system` |
| `SATQUERY_NODE_PORT` | optional | `8100` | Model Host bind port |
| `SATQUERY_DEBUG` | backend env | off | Always attach payload snapshots |

---

## Things to look out for

| Issue | What you’ll see | Fix |
|-------|-----------------|-----|
| Port 3000 / 8000 / **8100** busy | Launcher / bind error | Close other apps; re-run (launcher frees ports) |
| Node not installed | Setup fails at npm | Install Node LTS; re-run |
| Python **3.14** | `pydantic-core` / PyO3 fail | Install 3.12; `rm -rf backend/.venv`; re-run |
| UI connected but “model not loaded” | Analyze never hits host | Re-pair after Controller restart; check sidebar refresh |
| Host terminal idle | Old Hidden uvicorn | Pull latest; Model Host must run in **foreground** |
| Ollama `Failed to load image` on TIFF | Remote error | Pull latest (host converts GeoTIFF→PNG) |
| Spurious grounding/SAM on a VQA ask | Debug shows DINO+SAM | Pull latest routing fix (Workstream C) |
| Ollama missing on Controller | Amber **fallback** in Debug | Optional for planning; install or ignore |
| Blank UI / network error | “Couldn’t reach the backend” | http://127.0.0.1:8000/api/health |
| Two FastAPI apps | Confusing routes | Do **not** also `uvicorn` inside `router/` |
| macOS “cannot be opened” | Gatekeeper | `chmod +x` + right-click Open (above) |
| Windows execution policy | Script blocked | Use the `.bat` |
| Antivirus locks `node_modules` | Install fails | Pause scan briefly / re-run |

Logs: **`scripts/logs/`** (`backend.log`, `frontend.log`, `last-run.json`). Model Host live traffic is in the **host console** (not only log files).

---

## Project tree

```text
SAT_Query/
├── START_SATQUERY.bat / .command
├── README.md
├── UPDATE_LOG.md / UPDATES.md
├── docs/SETUP.md / ARCHITECTURE.md
├── scripts/start-satquery.ps1 / .sh
├── scripts/configure_role.py / pair_host.py
├── scripts/logs/
├── frontend/
├── backend/          # includes app/node/ (Model Host API)
├── router/
├── contrib/
├── data/
└── training/
```

---

## Stopping

- One-click window: **Ctrl+C** (clears role, frees ports, `ollama stop` on models the launcher managed)
- Manual: stop `uvicorn` / `npm run dev` terminals
- Ollama can keep running in the background if you use it for other projects
