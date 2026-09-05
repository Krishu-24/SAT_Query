# SatQuery — Local Update Log (merge handoff)

**Base remote:** [https://github.com/Krishu-24/SAT_Query](https://github.com/Krishu-24/SAT_Query)  
**Base tip this work started from:** `8bf5845` — *Restructure SatQuery into a pushable app with Shiven router integration and one-click launchers*  
**Current tip (this log):** `eb62b0d` — *Route multi-part analytical questions as a single VQA*  
**Purpose of this file:** Describe every intentional change made on top of that base so another contributor can merge their branch against ours without guessing intent.  
**Not a git log.** Prefer reading this + the file lists below over `git log`.

Related older notes (validator-only): `UPDATES.md`  
Specs that drove this work (do not treat as runtime code):

- `SatQuery_Validator_Hard_Debug_Spec.md`
- `SATQUERY_MULTIDEVICE_SPEC.md`

---

## How to use this when merging

1. Read **Workstreams** in order (A → B → C). C is follow-up hardening after the first multi-device ship.
2. Compare your change list against **Hotspots** — those files are most likely to conflict.
3. Prefer **ours** for new packages (`backend/app/node/`, hybrid executor, role scripts) unless you already reinvented the same layer.
4. Prefer **careful merge** on shared files (`routes.py`, `validator.py`, `router.py`, `start-satquery.ps1` / `.sh`, `README.md`, Debug UI).
5. Keep **API contracts** listed under each workstream — frontend and remote nodes depend on them.

---

## Workstream A — Validator hardening (pre-router)

### Goal

Reject impossible / inconsistent image+query combinations **before** routing or remote inference. Do not invent metadata. Do not run vision. Do not redesign the router or UI.

### Behavior

| Status | Meaning |
|--------|---------|
| `VALID` | Safe to route |
| `WARNING` | Route allowed; something incomplete/uncertain |
| `INVALID` | Stop (clear mismatch / bad file) |
| `NEEDS_CLARIFICATION` | Stop (e.g. ambiguous multi-image set) |
| `UNSUPPORTED` | Stop (needs non-imagery external data) |

Examples of new checks: bitemporal needs two dates that match the query; change-detection needs same-area GeoTIFF footprints when geo tags exist; SAR/optical modality must match wording; population-style questions → unsupported.

HTTP **422** still returns `detail.errors[]` (string list) for the existing frontend. Extra fields added for richer clients: `status`, `codes`, `issues`.

### Files

| Action | Path | Notes for merge |
|--------|------|-----------------|
| **Added** | `backend/app/agent/query_requirements.py` | Query → required inputs (not a router) |
| **Added** | `backend/app/agent/geo_checks.py` | Trusted GeoTIFF footprints only; coverage ≥ 0.25 = same-area |
| **Modified** | `backend/app/agent/validator.py` | Large: statuses, codes, sufficiency, geo/modality |
| **Modified** | `backend/app/api/routes.py` | Passes `query=` into validate; richer 422 |
| **Modified** | `backend/app/output/trace.py` | Can surface validation status/codes in debug |
| **Added** | `backend/tests/test_validator_hard_debug.py` | Hard matrix cases |
| **Added** | `SatQuery_Validator_Hard_Debug_Spec.md` | Spec document |
| **Added** | `UPDATES.md` | Short validator-only summary (superseded in scope by this log) |

### Intentionally not changed (A)

- Model weights / pipelines  
- Frontend layout for validation errors (still uses `errors[]`)  
- *(Router prompts/rules were left alone in A; see Workstream C for later routing fixes.)*

---

## Workstream B — Multi-device deployment layer (Controller / Model Host / Full System)

### Goal

Same repo on every machine. Startup chooses a **role**. Controller talks to Model Host over LAN for VQA/captioning. Preserve existing frontend, validator, and Qwen pipeline shape — this is a **deployment + node communication** layer, not a rewrite.

### Roles

| Role | Starts | Does not |
|------|--------|----------|
| **Controller** | Frontend + FastAPI + router + small planner Ollama (`qwen3:4b-instruct`) | Pull large VL; run Next.js is required |
| **Model Host** | Node API (`app.node.host_app:app` on port **8100**) + Ollama VL | Frontend / main analyze UI |
| **Full System** | Controller stack + optional local host endpoints | Assume every model fits every GPU |

### Host VLM (important merge note)

Team intent was GGUF **Qwen2.5-VL-7B-Instruct Q4_K_M**. That string is **not** an Ollama registry name (`ollama pull` → `file does not exist`).

**Runtime default used in code/scripts:** `qwen2.5vl:7b` (official Ollama vision package, same model family).  
Logical id toward the controller remains `qwen-vl`. Constant lives in `backend/app/node/config_store.py` as `DEFAULT_HOST_VLM_OLLAMA_TAG`.

### Communication

```text
Frontend → POST /api/analyze
  → Validator (must pass first)
  → Existing router (task plan, e.g. rs_vlm caption/VQA)
  → HybridPipelineExecutor
       → if paired host: POST http://host:8100/node/inference
            (images as base64 — never local filesystem paths)
            → Ollama on Model Host → answer
       → else: prior SKIP_MODEL_INFERENCE / local path
  → Integrator + execution_trace (REMOTE visible in Debug)
```

**Model Host API:** `GET /node/health|info|capabilities`, `POST /node/pair`, `POST /node/inference`  
**Controller pairing API:** `GET/POST /api/nodes/*` (status, pair, refresh, role, reset)

Auth: Bearer token from pairing. Errors use codes like `NODE_OFFLINE`, `OLLAMA_UNAVAILABLE`, `REMOTE_TIMEOUT`, etc. (see `backend/app/node/schemas.py`).

### Startup / shutdown UX (Windows + macOS scripts)

- **Always ask role every launch** — previous `.satquery/device.json` is cleared at start; not reused.
- Check-if-exists install logic preserved (venv, `node_modules`, Ollama models already present → skip re-download).
- Role-aware pulls: Controller does **not** pull host VL; Model Host does **not** start frontend.
- **On Ctrl+C / exit:** stop FE/BE/node trees, free ports 3000/8000/8100, `ollama stop` running models (free VRAM), delete role config again.

Helpers:

- `scripts/configure_role.py` — interactive role + hardware probe  
- `scripts/pair_host.py` — `python scripts/pair_host.py <ip> 8100 <code>`

Local secrets/state (gitignored): `.satquery/device.json`

### Files

| Action | Path | Notes for merge |
|--------|------|-----------------|
| **Added** | `backend/app/node/` entire package | config_store, auth, schemas, registry, client, bridge, hardware, ollama_runtime, host_routes, host_app |
| **Added** | `backend/app/agent/hybrid_executor.py` | Remote rs_vlm then fall back to unavailable/local |
| **Added** | `backend/app/api/node_controller.py` | Controller pairing/status |
| **Modified** | `backend/app/main.py` | Mount `/api/nodes` + `/node/*` |
| **Modified** | `backend/app/api/routes.py` | Uses `HybridPipelineExecutor`; health includes device summary |
| **Modified** | `backend/app/api/schemas.py` | Telemetry fields for REMOTE (`execution`, `node_id`, …) |
| **Modified** | `backend/app/output/trace.py` | Pass-through of those telemetry keys |
| **Modified** | `backend/app/utils/config.py` | Optional `SATQUERY_ROLE` / node port / remote timeout env |
| **Modified** | `scripts/start-satquery.ps1` | Role-aware; always re-ask; clean shutdown |
| **Modified** | `scripts/start-satquery.sh` | Same for macOS/Linux |
| **Added** | `scripts/configure_role.py`, `scripts/pair_host.py` | |
| **Added** | `frontend/src/components/NodeStatus.tsx` | Sidebar device/remote status |
| **Modified** | `frontend/src/components/Sidebar.tsx` | Mounts NodeStatus |
| **Modified** | `frontend/src/components/DebugPanel.tsx` | Shows REMOTE execution block |
| **Modified** | `frontend/src/types/api.ts` | Telemetry optional fields |
| **Modified** | `.gitignore` | `.satquery/` |
| **Modified** | `README.md` | Multi-device section |
| **Added** | `SATQUERY_MULTIDEVICE_SPEC.md` | Spec |
| **Added** | `backend/tests/test_multidevice_nodes.py` | Unit/API tests (mocked Ollama) |

### Intentionally not changed (B)

- Transformers local `QwenVLMWrapper` path (still for Full System when weights exist)  
- Synthetic map / location UX on the frontend  
- Creating a second repo or OS-specific forks  
- *(Initial B left Shiven/RuleBasedRouter task logic alone; Workstream C changed routing after live testing.)*

### Not claimed at end of B

- Real Mac ↔ Legion two-laptop E2E was **not** fully verified when B was first written. Pairing/inference/registry unit tests passed with mocks.

---

## Workstream C — Live fixes after multi-device + routing (append)

Shipped on `main` after B, while testing Controller (Mac) ↔ Model Host (Windows). Keep this section when merging — these are behavior fixes, not optional polish.

### C1 — Launcher / Python env (Windows + Mac)

| Problem | Fix |
|---------|-----|
| Python **3.14** breaks `pydantic-core` wheels | Scripts require **3.11–3.13** (prefer 3.12); recreate bad venvs |
| Loud pip / leftover `~*` packages on Windows | Pin direct deps in `backend/requirements-lite.txt`; quieter install |

**Files:** `scripts/start-satquery.ps1`, `scripts/start-satquery.sh`, `backend/requirements-lite.txt`

### C2 — Pairing looked connected but analyze said “model not loaded”

| Problem | Fix |
|---------|-----|
| CLI pairing wrote `.satquery/device.json` while uvicorn kept an empty in-memory registry | `get_registry(reload=True)` on status, bridge, hybrid |
| UI had no connection strip | Minimal `NodeStatus` in sidebar (connected / VLM ready) |

**Files:** `backend/app/node/registry.py`, `bridge.py`, `hybrid_executor.py`, `api/node_controller.py`, `frontend/.../NodeStatus.tsx`

### C3 — Model Host terminal silent; GeoTIFF queries failed

| Problem | Fix |
|---------|-----|
| Host uvicorn ran **Hidden** → logs only in `scripts/logs/node-host*.log` | Model Host runs uvicorn **in the foreground**; Controller tails `backend.log` for OUTGOING/INCOMING |
| Ollama rejected Sentinel-2 **GeoTIFF** (`Failed to load image`) | Host converts images → RGB **PNG** (downscale long edge) before Ollama |

**Files:** `scripts/start-satquery.ps1` / `.sh`, `backend/app/node/host_routes.py`, `ollama_runtime.py`, `hybrid_executor.py`, `api/routes.py`

### C4 — Router over-split a single analytical VQA

Example prompt that was mis-routed to VQA + captioning + grounding/SAM:

> Examine this satellite image carefully. What are the three most prominent visual features, where are they located relative to the image center, and what evidence in the image supports your identification?

| Cause | Fix |
|-------|-----|
| Substring `"locate"` matched inside **`located`** | Whole-word / phrase keyword matching |
| `"where are"` + split on `" and "` → grounding + second task | Compound analytical questions → **one** `rs_vlm` `answer_question` |
| LLM planner emitted VQA+CAPTION+GROUNDING | Tighter planner prompt + adapter coalesce (drop spurious grounding/caption) |

**Still correct:** `"Find the river and describe the image"` → GROUNDING + CAPTIONING.

**Files:**

| Action | Path |
|--------|------|
| **Modified** | `backend/app/agent/router.py` (`ROUTER_VERSION` → `rule_based_keyword/2`) |
| **Modified** | `backend/app/agent/shiven_adapter.py` (plan filter / coalesce) |
| **Modified** | `router/app/router/classifier.py` |
| **Modified** | `router/app/planner/prompt.py`, `planner.py` |
| **Modified** | `backend/tests/test_router.py` |

### Commits in C (for orientation)

| SHA | Summary |
|-----|---------|
| `de2b5ee` / `66ca70d` | Python pin + lite deps / Windows pip noise |
| `ce0162d` | Stale registry + remote traffic logging |
| `3f559e4` | Sidebar Model Host / VLM status |
| `2c2be9b` | Foreground host console + GeoTIFF→PNG |
| `eb62b0d` | Single-VQA routing for multi-part analytical questions |

### Proven in C (manual)

- Controller UI can show Model Host **connected** after pair  
- Host receives `/node/inference`; GeoTIFF path no longer fails solely on format  
- Analytical VQA no longer plans grounding_dino + sam for “located relative to…”

---

## Shared / small supporting edits

| Path | Why |
|------|-----|
| `backend/tests/conftest.py` | Test env pins for router/inference flags (may already exist; check diff) |
| `backend/tests/test_trace_builder.py` | Expectation set updated for expanded telemetry keys |

---

## Hotspots (merge carefully)

These files were touched across workstreams or are large shared surfaces:

1. `backend/app/api/routes.py` — validator wiring **and** hybrid executor  
2. `backend/app/agent/validator.py` — large validator rewrite  
3. `backend/app/agent/router.py` + `shiven_adapter.py` + `router/app/router/classifier.py` — routing behavior (C)  
4. `scripts/start-satquery.ps1` / `scripts/start-satquery.sh` — large launcher rewrite + foreground host  
5. `README.md` — docs from both streams  
6. `backend/app/output/trace.py` + `frontend/.../DebugPanel.tsx` — debug/telemetry  

Safer to take **their** feature commits into a branch, then re-apply our `node/` package and hybrid executor if their branch never had multi-device.

---

## Suggested merge checklist for the other contributor

- [ ] No accidental commit of `.satquery/`, `.env`, tokens, or model weights  
- [ ] `POST /api/analyze` still returns `answer`, `confidence`, `evidence`, `execution_trace`  
- [ ] 422 still has `detail.errors` as a string list  
- [ ] If they also added pairing/nodes: align on one package under `backend/app/node/`  
- [ ] If they use a different Ollama VL tag: set `hosted_models[].ollama_tag` / `DEFAULT_HOST_VLM_OLLAMA_TAG` once  
- [ ] Analytical multi-part VQA stays **one** `rs_vlm` step (no spurious DINO/SAM)  
- [ ] Run:  
  `cd backend && python -m pytest tests/test_validator_hard_debug.py tests/test_multidevice_nodes.py tests/test_router.py tests/test_api_analyze.py tests/test_trace_builder.py -q`  
- [ ] Manual: Controller + Model Host + pair + GeoTIFF VQA (host terminal shows INCOMING)

---

## One-paragraph summary for chat/PR

> On top of Krishu-24/SAT_Query `@8bf5845`, this tree adds (1) hard query↔input validation before routing, (2) a role-aware multi-device layer (Controller / Model Host / Full System) with LAN pairing, base64 transfer, Ollama `qwen2.5vl:7b`, hybrid executor, and always-reask role + clean shutdown, then (3) live fixes: registry reload after pair, sidebar node status, foreground Model Host logs, GeoTIFF→PNG for Ollama, and routing so multi-part analytical questions stay a single VQA instead of captioning + grounding/SAM.

---

*End of update log through `eb62b0d`. Append the next workstream below if you continue this handoff.*
