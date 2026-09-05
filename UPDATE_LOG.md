# SatQuery — Local Update Log (merge handoff)

**Base remote:** [https://github.com/Krishu-24/SAT_Query](https://github.com/Krishu-24/SAT_Query)  
**Base tip this work started from:** `8bf5845` — *Restructure SatQuery into a pushable app with Shiven router integration and one-click launchers*  
**Purpose of this file:** Describe every intentional change made on top of that base so another contributor can merge their branch against ours without guessing intent.  
**Not a git log.** Prefer reading this + the file lists below over `git log`.

Related older notes (validator-only): `UPDATES.md`  
Specs that drove this work (do not treat as runtime code):

- `SatQuery_Validator_Hard_Debug_Spec.md`
- `SATQUERY_MULTIDEVICE_SPEC.md`

---

## How to use this when merging

1. Read **Workstreams** to see what we built and what we deliberately left alone.
2. Compare your change list against **Hotspots** — those files are most likely to conflict.
3. Prefer **ours** for new packages (`backend/app/node/`, hybrid executor, role scripts) unless you already reinvented the same layer.
4. Prefer **careful merge** on shared files (`routes.py`, `validator.py`, `start-satquery.ps1` / `.sh`, `README.md`, Debug UI).
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

- RuleBasedRouter / Shiven planner prompts  
- Model weights / pipelines  
- Frontend layout for validation errors (still uses `errors[]`)

---

## Workstream B — Multi-device deployment layer (Controller / Model Host / Full System)

### Goal

Same repo on every machine. Startup chooses a **role**. Controller talks to Model Host over LAN for VQA/captioning. Preserve existing router, frontend, validator, and Qwen pipeline shape — this is a **deployment + node communication** layer, not a rewrite.

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

- Shiven router core / RuleBasedRouter task logic  
- Transformers local `QwenVLMWrapper` path (still for Full System when weights exist)  
- Synthetic map / location UX on the frontend  
- Creating a second repo or OS-specific forks  

### Not claimed / not fully proven

- Real Mac ↔ Legion two-laptop E2E was **not** fully verified in this environment. Unit tests for pairing/inference/registry passed with mocks.

---

## Shared / small supporting edits

| Path | Why |
|------|-----|
| `backend/tests/conftest.py` | Test env pins for router/inference flags (may already exist; check diff) |
| `backend/tests/test_trace_builder.py` | Expectation set updated for expanded telemetry keys |

---

## Hotspots (merge carefully)

These files were touched by **both** workstreams or are large shared surfaces:

1. `backend/app/api/routes.py` — validator wiring **and** hybrid executor  
2. `backend/app/agent/validator.py` — large validator rewrite  
3. `scripts/start-satquery.ps1` / `scripts/start-satquery.sh` — large launcher rewrite  
4. `README.md` — docs from both streams  
5. `backend/app/output/trace.py` + `frontend/.../DebugPanel.tsx` — debug/telemetry  

Safer to take **their** feature commits into a branch, then re-apply our `node/` package and hybrid executor if their branch never had multi-device.

---

## Suggested merge checklist for the other contributor

- [ ] No accidental commit of `.satquery/`, `.env`, tokens, or model weights  
- [ ] `POST /api/analyze` still returns `answer`, `confidence`, `evidence`, `execution_trace`  
- [ ] 422 still has `detail.errors` as a string list  
- [ ] If they also added pairing/nodes: align on one package under `backend/app/node/`  
- [ ] If they use a different Ollama VL tag: set `hosted_models[].ollama_tag` / `DEFAULT_HOST_VLM_OLLAMA_TAG` once  
- [ ] Run:  
  `cd backend && python -m pytest tests/test_validator_hard_debug.py tests/test_multidevice_nodes.py tests/test_router.py tests/test_api_analyze.py tests/test_trace_builder.py -q`  
- [ ] Manual: Controller role + Model Host role + pair + one caption query (when two machines available)

---

## One-paragraph summary for chat/PR

> On top of Krishu-24/SAT_Query `@8bf5845`, this tree adds (1) hard query↔input validation before routing, and (2) a role-aware multi-device layer (Controller / Model Host / Full System) with LAN pairing, base64 image transfer, Ollama-backed remote VQA via `qwen2.5vl:7b`, hybrid executor, always-reask role + clean shutdown in the one-click scripts, and minimal Debug/sidebar status — without rewriting the existing router or frontend.

---

*End of update log. Append your own workstream section below if you are the other merge partner.*
