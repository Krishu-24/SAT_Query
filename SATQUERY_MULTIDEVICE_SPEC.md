# SatQuery — Multi-Device Role System Implementation Spec

Repository: `https://github.com/Krishu-24/SAT_Query`

> **Implementation status (as of `UPDATE_LOG.md` Workstream B/C):** The multi-device layer is shipped in-tree (`backend/app/node/`, hybrid executor, role-aware launchers, sidebar `NodeStatus`). Notable deltas vs this original spec: role is asked **every** launch and cleared on exit (not persisted across sessions); host VLM runtime tag is **`qwen2.5vl:7b`** (not the non-registry GGUF string); Model Host uvicorn runs in the **foreground**; GeoTIFF is converted to PNG before Ollama; pairing registry reloads from disk after CLI pair. Treat this file as the design intent; treat `UPDATE_LOG.md` + `docs/SETUP.md` as “what runs today.”

This is **ONE project** and must remain **ONE repository and ONE codebase**. The goal is to extend the existing SatQuery application so the exact same repository can be cloned onto ANY laptop/PC, and the application determines at startup which role that particular machine should perform.

Do not create separate projects for Mac, Windows, model hosts, or controllers.

---

## 1. Core Requirement

When the user runs the existing one-click startup script for the first time, the terminal must ask:

```text
Select this device's SatQuery role:

1. Controller
2. Model Host
3. Full System
```

The selected role determines:
- which components start
- which dependencies are required
- which models/runtime are checked
- which services are exposed
- whether this machine acts as the main application or as a remote model server

Persist the selected configuration so the user does not have to choose every startup. Provide a way to change/reset the role later.

The role must **NOT** be tied to the operating system or machine name. Example:

```text
Mac              → Controller
Windows Legion    → Model Host
Another Windows PC → Full System
Another Mac       → Model Host
```

The same repository must work in all cases.

---

## 2. Do Not Install Everything on Every Machine

The startup/bootstrap system must be role-aware.

**Controller** — install/start only what is required for:
```text
Frontend
FastAPI/backend
existing deterministic router
small routing Qwen
local Ollama if required
communication/node client
```
Must NOT require the large VQA model.

**Model Host** — install/start only what is required for:
```text
SatQuery node/model-host service
Ollama
models assigned to this host
communication server
```
Must NOT require the frontend. Must NOT start the main router unless explicitly needed.

**Full System** — install/start the components supported by the machine:
```text
Frontend
Backend
Router
Ollama
available local models
Node service
```
Do not assume every Full System machine can run every model — hardware/model capability detection must determine what can actually be enabled.

---

## 3. First: Audit the Current Repository

Before changing code, inspect the actual repository. Specifically inspect:

```text
backend/
frontend/
training/
data/
docs/
README.md
CONTRIBUTING.md
```

Find:
- backend entrypoint
- FastAPI routes
- router implementation
- model registry
- Qwen integration
- current Ollama integration, if any
- pipeline execution framework
- frontend → backend API flow
- current startup scripts
- dependency files
- environment/configuration files
- fallback mode
- validation logic
- execution trace
- existing model stubs

Do not assume the architecture described in this spec is identical to the repository. Use the repository's actual implementation as the source of truth. **Before major modifications, produce a concise implementation plan based on the discovered code.**

---

## 4. Existing Architecture Must Be Preserved

The current repository already has:
- deterministic routing
- FastAPI backend
- frontend demo
- Qwen VLM integration
- pipeline execution framework
- fallback behavior

The README currently describes the routing layer as deterministic/zero-VRAM and the Qwen VLM as part of VQA/captioning. **Preserve this architecture.**

Do NOT:
- replace the router with an LLM
- redesign the router
- rewrite the frontend
- rewrite the existing validation system
- rewrite model pipelines
- remove fallback mode
- create another repository/application
- create separate codebases for different operating systems

This task is primarily a **deployment + node communication layer**.

---

## 5. Node Architecture

Introduce a generic SatQuery Node abstraction. Supported roles:

```text
CONTROLLER
MODEL_HOST
FULL_SYSTEM
```

A node should have:
```text
node_id
role
hostname
OS
address
port
status
capabilities
models
runtime
```

Example:
```json
{
  "node_id": "satquery-8F31A2",
  "role": "MODEL_HOST",
  "status": "ready",
  "runtime": "ollama",
  "models": [
    {
      "id": "qwen-vl",
      "tasks": ["vqa", "captioning"]
    }
  ]
}
```

Do not hard-code `Legion = Qwen`, `Mac = Controller`, `Windows = Model Host` — those are merely the current test setup.

---

## 6. Current Two-Laptop Test

The first working distributed configuration must support:

**MAC — Role: CONTROLLER**
```text
Frontend + FastAPI + existing router + small Qwen through Ollama
```

**LENOVO LEGION — Role: MODEL_HOST**
```text
SatQuery Node Service + Ollama + large Qwen VQA/captioning model
```

The Mac must send VQA/captioning inference requests to the Legion. The Legion must execute the model through its LOCAL Ollama instance. The result must return to the Mac and continue through the existing application flow.

---

## 7. No Code Copying Between Devices

Once the repository is cloned on both machines (`Mac: SAT_Query/`, `Legion: SAT_Query/`), the user should NOT need to:
- copy Python files
- copy model code
- manually edit IP addresses in source
- manually modify imports
- create special versions of files
- copy configuration code from one machine to another

The startup/bootstrap system handles role-specific configuration. The codebase remains identical — only local configuration/state differs.

---

## 8. Role Configuration

Create a **central** configuration mechanism rather than scattering settings throughout the repository. Conceptually support:

```text
SATQUERY_ROLE=controller
SATQUERY_NODE_ID=...
SATQUERY_PORT=...
SATQUERY_CONTROLLER_ADDRESS=...
SATQUERY_OLLAMA_URL=...
SATQUERY_MODEL_CONFIG=...
```

Use the project's existing configuration style if one exists. Do not invent multiple competing configuration systems. Persist local machine configuration somewhere appropriate and **ignored by Git**.

Never commit: pairing secrets, local IP addresses, machine-specific configuration, model weights, credentials.

---

## 9. Startup Flow

Modify the existing Windows `.bat` and macOS `.command`/shell startup mechanism rather than creating an unrelated startup system.

```text
Start SatQuery
       ↓
Is this machine configured?
       │
       ├── NO
       │    ↓
       │   Ask: 1. Controller  2. Model Host  3. Full System
       │    ↓
       │   Save role
       │
       └── YES
            ↓
       Load saved role
            ↓
       Check requirements
            ↓
       Install missing role-specific dependencies
            ↓
       Start role-specific services
```

Provide a reset/reconfigure option such as `Change device role`. Do not force the user to delete configuration files manually.

---

## 10. Dependency Installation

The bootstrapper must be role-aware.

```text
Controller
→ controller dependencies
→ frontend dependencies
→ backend dependencies
→ router dependencies
→ small Qwen/Ollama requirements

Model Host
→ model host dependencies
→ Ollama check
→ selected model check
→ node service dependencies

Full System
→ combined requirements based on available hardware
```

Do not blindly install heavyweight ML packages on a controller that cannot use them. Do not download large model weights automatically unless the user explicitly chooses/enables that model. Use the existing project's dependency files where possible. If the current `requirements.txt` contains packages unnecessary for a particular role, determine whether role-specific requirements files are appropriate rather than duplicating the entire environment blindly.

---

## 11. Model Selection on Model Host

When the user selects **MODEL HOST**, the startup system should eventually allow:

```text
Select models to host:

[✓] Qwen VQA / Captioning
[ ] Grounding
[ ] Change Detection
[ ] Optical-SAR
...
```

For the **FIRST implementation**, only expose `Qwen VQA / Captioning`. Other models should remain future capabilities — do not implement their actual inference yet, but the architecture must allow additional models later.

---

## 12. Hardware Awareness

Do not assume every machine can run the large Qwen model. When configuring a Model Host, check relevant local capabilities where practical: OS, CPU, RAM, GPU availability, GPU VRAM, Ollama availability, available disk space if relevant.

Then report:
```text
Hardware:
GPU: ...
VRAM: ...
RAM: ...

Qwen VQA:
Supported / Unsupported / Unknown
```

Do not prevent a user from manually configuring a model merely because detection is uncertain. Represent unknown hardware information as unknown rather than fabricating support.

---

## 13. Ollama

Use Ollama as the model runtime for this distributed prototype.

```text
SatQuery Controller
       ↓
SatQuery Node API
       ↓
Ollama on Model Host
       ↓
Qwen
```

Do NOT make the controller directly depend on the remote machine's Ollama API. The SatQuery Model Host is an abstraction layer around Ollama — this is critical for future model runtimes (later: vLLM, Transformers, TensorRT, etc.). The controller should not need to know those implementation details.

---

## 14. Model Host API

Implement a lightweight HTTP API for SatQuery Model Hosts. At minimum:

```text
GET  /node/health
GET  /node/info
GET  /node/capabilities
POST /node/inference
```

Use the project's existing FastAPI architecture if appropriate. Do not expose arbitrary Ollama endpoints directly.

---

## 15. Node Info

```json
{
  "node_id": "satquery-123",
  "role": "MODEL_HOST",
  "status": "ready",
  "runtime": "ollama",
  "capabilities": ["vqa", "captioning"],
  "models": ["qwen-vl"]
}
```

Use the actual existing schema conventions where possible.

---

## 16. Inference Request

The controller should send a structured request conceptually containing:

```text
request_id
task
model
query
images
metadata
timeout
```

The host: receive request → validate request → validate image → locate requested local model → invoke Ollama → return structured result.

The same `request_id` must be preserved from: `Frontend → Backend → Router → Node → Model → Node → Backend → Frontend`.

---

## 17. Image Transfer

Do **NOT** send local filesystem paths. This is WRONG:

```text
Mac: C:/something/image.tif
Legion: try opening C:/something/image.tif   ← path doesn't exist remotely
```

The controller must transmit the actual required image data using a safe request mechanism. Preserve: image order, filenames where useful, content type, relevant metadata.

The Model Host reconstructs/temporarily stores the image locally and passes it to the model. Clean temporary data afterward. Respect existing upload limits and validation.

---

## 18. Pairing

Implement a simple LAN pairing system. The Model Host startup should display something like:

```text
SatQuery Model Host
────────────────────
Node ID: SAT-LEGION-82F1
Address: 192.168.x.x
Port: 8xxx

Capabilities:
✓ Qwen VQA
✓ Qwen Captioning

Pairing Code:
482913

Waiting for Controller...
```

The Controller should discover available SatQuery nodes where practical. If automatic discovery is unreliable across operating systems/networks, provide a fallback: `Enter pairing code/address:`.

The user should perform this only once. Persist the pairing information securely enough for the LAN prototype.

After pairing:
```text
Controller
✓ SAT-LEGION-82F1
✓ Qwen VQA
✓ Qwen Captioning
```

No source-code modification should be required.

---

## 19. Multiple Model Hosts

Do NOT design this around exactly two laptops. The Controller should maintain a node registry:

```text
Controller
│
├── Node A → Qwen VQA
├── Node B → Grounding
├── Node C → Qwen VQA + Captioning
└── Node D → Change Detection
```

The router asks for a capability, e.g.:
```text
Task: VQA
Find: healthy node + VQA capability + compatible model
```
Then select an appropriate node. Do NOT select based on machine name, IP address, or operating system.

---

## 20. Routing

Do not change the existing deterministic router's responsibility.

- The **router** determines: *what task is required?*
- The **node manager** determines: *where can this task execute?*

```text
Query → Existing Router → VQA → Node Registry → Qwen-capable node → Model Host → Ollama → Qwen
```

The user should never need to manually select "Use Legion" for normal queries.

---

## 21. Local Fallback

```text
If a compatible model exists locally:
  Router → Local capable model   (per existing architecture)

If only a remote capable model exists:
  Router → Remote node

If no capable model exists:
  Existing fallback/error behavior
```

Do not break the existing fallback mode.

---

## 22. Frontend

Do not redesign the frontend. Only add the minimum required UI/status information.

Potential developer/system status panel:
```text
Device: Controller

Local:
Small Qwen ✓

Remote Nodes:
SAT-LEGION-82F1
✓ Qwen VQA
✓ Qwen Captioning
Status: Ready
```

For a query, the execution trace should make remote execution visible:
```text
Task: VQA
Execution: REMOTE

Node: SAT-LEGION-82F1
Runtime: Ollama
Model: Qwen VQA
Status: SUCCESS
```

Use the existing execution-trace mechanism if available.

---

## 23. Error Handling

Handle all distributed failures gracefully. At minimum:

```text
NODE_NOT_FOUND
NODE_OFFLINE
NODE_UNHEALTHY
NODE_PAIRING_FAILED
NODE_AUTH_FAILED
MODEL_NOT_AVAILABLE
OLLAMA_UNAVAILABLE
REMOTE_CONNECTION_FAILED
REMOTE_TIMEOUT
REMOTE_INFERENCE_FAILED
REMOTE_RESPONSE_INVALID
IMAGE_TRANSFER_FAILED
UNSUPPORTED_TASK
```

Never crash the main FastAPI application because a Model Host disappeared. Use structured errors compatible with the existing API/frontend contract.

---

## 24. Timeouts

Remote requests must have configurable timeouts. Do not allow infinite HTTP requests. Use bounded retries — no infinite retry loops.

If a host disappears during inference: mark unhealthy → return structured error → allow future health checks/reconnection.

---

## 25. Security

Even for LAN development:
- authenticate controller → model-host requests
- use pairing-generated secret/token
- do not expose arbitrary filesystem operations
- do not expose unrestricted Ollama access
- validate uploaded files
- enforce request/upload limits
- sanitize filenames
- do not execute arbitrary commands received remotely
- do not hard-code secrets

Full production TLS is not required for this first prototype.

---

## 26. Validator Integration

The existing validator must execute **BEFORE** remote model execution.

```text
Frontend → Backend → File/query validation → Existing router → Task requirements → Node selection → Remote/local inference
```

Invalid image/query combinations must NOT be forwarded to the Model Host. Do not weaken the validator while implementing networking.

---

## 27. Current End-to-End Test

After implementation, this exact scenario must be possible.

**Legion:** Clone the SAME repository → Run the SAME startup script → Select `2. Model Host`.
The script: checks Python/runtime → checks Ollama → checks Qwen → installs missing dependencies → starts node service → shows node ID/pairing information.

**Mac:** Clone the SAME repository → Run the SAME startup script → Select `1. Controller`.
The script: checks dependencies → starts frontend → starts backend → starts router → checks small Qwen/Ollama → discovers/pairs with Legion.

No code should be copied between machines.

---

## 28. End-to-End Query

Use a valid satellite image and ask: `Describe this image.`

Expected path:
```text
Mac Frontend → Mac FastAPI → Existing Router → Captioning/VQA → Node Registry
→ Legion → SatQuery Model Host → Local Ollama → Big Qwen
→ Model Host → Mac → Frontend
```

Then execute a second query without restarting either machine. Verify that both work.

---

## 29. Same Repository, Different Runtime

```text
              SAME SAT_QUERY REPOSITORY
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
      Controller    Model Host   Full System
          │            │            │
       frontend       Ollama      everything
       backend        models      supported
       router         node
```

The source code is shared. The runtime configuration differs.

---

## 30. Documentation

Update the README with a concise section: `Running SatQuery on multiple devices`, explaining:
1. Clone the same repository on every machine.
2. Run the startup script.
3. Select the device role.
4. Let the bootstrapper install role-specific dependencies.
5. Pair Model Hosts with the Controller.
6. Start using the normal frontend.

Also document: Controller responsibilities, Model Host responsibilities, Full System responsibilities, how pairing works, how to change device role, how to add future model capabilities.

Do not make the README excessively long.

---

## 31. Testing

Add tests for:

**Configuration** — first startup asks for role; role persists; role can be changed; invalid role handled.

**Node** — node health; node info; capabilities; registration/pairing; authentication.

**Remote inference** — request reaches host; image transfer works; request ID preserved; Ollama invocation works; response returned.

**Failure cases** — host offline; Ollama offline; model missing; timeout; malformed response; authentication failure; invalid image; oversized upload.

**Routing** — verify `VQA → Qwen-capable node` without hard-coding a specific machine.

---

## 32. Do Not Overengineer

For this phase, DO NOT add: Kubernetes, Docker orchestration, cloud infrastructure, distributed databases, complicated service discovery, load-balancing frameworks, production-grade distributed scheduling, TLS infrastructure, all future ML models.

We only need a clean LAN prototype that can later scale.

---

## 33. Implementation Order

1. Audit repository.
2. Identify existing startup/bootstrap architecture.
3. Identify existing router/model execution boundaries.
4. Introduce role configuration.
5. Implement Node abstraction.
6. Implement Model Host API.
7. Implement controller-side node registry.
8. Implement pairing/discovery.
9. Implement remote image transfer.
10. Connect Qwen VQA/captioning to remote Ollama.
11. Update startup scripts.
12. Add minimal frontend status/trace changes.
13. Add error handling.
14. Add tests.
15. Perform the two-laptop end-to-end test.
16. Update README.

Do not make unrelated refactors.

---

## 34. Final Report

At the end, report:

- **Architecture discovered** — what the repository actually contained before modification.
- **Files changed** — exact files.
- **Role system** — how Controller / Model Host / Full System work.
- **Dependency behavior** — what gets installed for each role.
- **Node communication** — how discovery/pairing/inference work.
- **Current Qwen flow** — exactly how Mac → Legion → Ollama → Qwen → Mac works.
- **Tests** — passed / failed.
- **Manual setup** — exact commands/steps for Mac Controller + Windows Legion Model Host.
- **Remaining limitations** — especially anything not actually tested.

**DO NOT claim that the two-machine system works unless it has actually been tested.**

---

**Most important requirement: Keep everything in the single existing SAT_Query repository and make the startup script determine what that particular machine runs.**
