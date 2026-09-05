# SatQuery AI

**Proof-of-concept · Agentic remote-sensing query platform**

Upload satellite imagery. Ask in natural language. SatQuery validates the request, plans a model pipeline, runs inference locally or on a paired **Model Host**, and returns an answer with a full execution trace.

Built as a deployable PoC: one repository, one-click launch, role-aware multi-device execution, and production-minded API hardening.

```text
  Operator  →  Web UI (:3000)  →  API (:8000)
                                    │
                     ┌──────────────┼──────────────┐
                     ▼              ▼              ▼
                Validator      Planner        Hybrid executor
              (pre-router)   (Shiven/Qwen3)   (local stubs or
                                               remote VLM :8100)
```

---

## How to run

| OS | Action |
|----|--------|
| **Windows** | Double-click [`START_SATQUERY.bat`](START_SATQUERY.bat) |
| **macOS** | Double-click [`START_SATQUERY.command`](START_SATQUERY.command) · see [docs/SETUP.md](docs/SETUP.md) if Gatekeeper blocks it |

The launcher asks for this machine’s **role**, installs anything missing, starts the right services, and (Controller / Full System) opens:

### → http://localhost:3000

Leave the console open. **Ctrl+C** stops everything, frees ports, and clears the local role.

<details>
<summary><strong>Manual run</strong> (developers)</summary>

```bash
# Backend — Python 3.11–3.13 only (not 3.14)
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate  |  macOS: source .venv/bin/activate
pip install -r requirements-lite.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend — other terminal
cd frontend
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm install && npm run dev
```

Optional planner: [Ollama](https://ollama.com) + `ollama pull qwen3:4b-instruct`.  
Model Host VLM: `ollama pull qwen2.5vl:7b`.

</details>

---

## Documentation hub

Everything starts here. Deep dives live one click away.

| Document | Use it for |
|----------|------------|
| **[docs/SETUP.md](docs/SETUP.md)** | Requirements, roles, pairing, troubleshooting |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | Request path, modules, ports, Debug Mode |
| **[UPDATE_LOG.md](UPDATE_LOG.md)** | Merge handoff — workstreams A→D (validator, multi-device, live fixes, hardening) |
| **[CHANGELOG.md](CHANGELOG.md)** | Backend Phase 1/2 hardening + land-cover notes |
| **[UPDATES.md](UPDATES.md)** | Short index into the handoff log |
| [SATQUERY_MULTIDEVICE_SPEC.md](SATQUERY_MULTIDEVICE_SPEC.md) | Multi-device design intent |
| [SatQuery_Validator_Hard_Debug_Spec.md](SatQuery_Validator_Hard_Debug_Spec.md) | Validator case matrix |

Specs describe intent; **SETUP + ARCHITECTURE + UPDATE_LOG** describe what runs today.

---

## What you get

| Capability | Detail |
|------------|--------|
| **Natural-language RS queries** | VQA, captioning, grounding, change, optical–SAR plans |
| **Pre-router validation** | Rejects impossible image/query combos before planning |
| **Smart routing** | Multi-part analytical questions stay one VQA; explicit “find + describe” still splits |
| **Distributed VLM** | Controller UI + Model Host `qwen2.5vl:7b` over LAN |
| **Land-cover pre-check** | Fast parallel gate; can short-circuit remote VLM when land signal is too weak |
| **Hardened API** | Upload budgets, unified error envelope, CORS tighten, pipeline resilience |
| **Explainability** | Debug Mode + sidebar node status (`Execution: REMOTE` when hosted) |

---

## Multi-device (same repo)

Clone once. Run the same launcher on every machine. Pick a role **every** launch (cleared on exit).

| Role | Starts | Models |
|------|--------|--------|
| **Controller** | UI + API + planner (`qwen3:4b-instruct`) | No large VLM pull |
| **Model Host** | Node API **:8100** (live console) + Ollama | **`qwen2.5vl:7b`** |
| **Full System** | Controller stack (+ host pieces as configured) | Planner + VLM when enabled |

```bash
# On Controller, after Model Host shows its pairing code:
python scripts/pair_host.py <host-ip> 8100 <pairing-code>
```

GeoTIFF → PNG conversion happens on the Model Host before Ollama. Re-pair after each Controller restart.

Full walkthrough: **[docs/SETUP.md § Multi-device](docs/SETUP.md#multi-device-controller--model-host)**.

---

## Architecture at a glance

```text
POST /api/analyze
  → Upload gate + InputValidator
  → Land-cover check ∥ QueryPlanner (LLM → rule fallback)
  → HybridPipelineExecutor
       ├─ paired host → POST /node/inference → Ollama VL
       └─ else → unavailable / local stubs
  → Integrator + execution_trace → UI
```

| Port | Service |
|------|---------|
| `3000` | Next.js frontend |
| `8000` | FastAPI controller API |
| `8100` | Model Host node API |
| `11434` | Ollama |

Diagrams and module map: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

---

## Repository layout

```text
SAT_Query/
├── START_SATQUERY.bat / .command     One-click entry
├── README.md                         You are here
├── docs/                             SETUP · ARCHITECTURE
├── scripts/                          Launchers · pair_host · configure_role
├── frontend/                         Next.js UI · Debug · NodeStatus
├── backend/                          FastAPI · validator · hybrid · node/
├── router/                           Shiven QueryPlanner
├── UPDATE_LOG.md · CHANGELOG.md      Handoff & hardening history
├── contrib/ · data/ · training/      Optional / demo assets
└── *.md (specs)                      Design matrices (linked above)
```

Local role state (gitignored): `.satquery/device.json`

---

## Status

| Layer | State |
|-------|--------|
| PoC demo path | **Runnable** via one-click (Controller or Full System) |
| Multi-device VQA | **Runnable** with paired Model Host + `qwen2.5vl:7b` |
| Specialist CV weights | Optional; default `SKIP_MODEL_INFERENCE=true` with honest traces |
| API hardening | Phase 1 + 2 landed (see [CHANGELOG.md](CHANGELOG.md)) |
| Production weights / auth / k8s | **Out of scope** for this PoC |

---

## Team handoff

If you are merging another branch, start with **[UPDATE_LOG.md](UPDATE_LOG.md)** (workstreams A–D), then run:

```bash
cd backend && python -m pytest -q
```

Smoke: Controller + Model Host pair → one GeoTIFF VQA → host console shows `INCOMING` → UI shows a remote answer.
