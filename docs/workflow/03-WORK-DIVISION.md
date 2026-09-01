# 03 — Work Division

> 5 members × 3 days. The delivery target is a working proof of concept, not a perfect production deployment.

## Team Roles

| Code | Role | Focus | Deliverables |
|---|---|---|---|
| M1 | Backend Lead | FastAPI server, routes, model registry | Working `/api/analyze` endpoint |
| M2 | Frontend Lead | UI build, interaction design, API integration | Functional web interface |
| M3 | Agent / Router Lead | Validation and routing logic | Auto-detection of task type |
| M4 | ML Pipelines Lead | Model wrappers and evidence generation | Five model pipelines in place |
| M5 | Data / Fine-Tuning Lead | Demo assets and model preparation | Dataset organization and training setup |

## Day 1 — Scaffold and Core Integration

### Morning

| Member | Task | Done When |
|---|---|---|
| M1 | Scaffold backend | Health endpoint responds successfully |
| M2 | Scaffold frontend | Browser can upload an image and accept a query |
| M3 | Implement router | Ten test queries route correctly |
| M4 | Build model registry | Registry can load and unload a dummy model |
| M5 | Prepare demo data | At least three reference assets per scenario |

### Afternoon

| Member | Task | Done When |
|---|---|---|
| M1 | Implement `/api/analyze` endpoint | Upload request returns a valid JSON response |
| M2 | Build result and trace panels | Empty data renders cleanly |
| M3 | Implement input validation | Invalid counts and unsupported formats are rejected |
| M4 | Build VQA wrapper | A test invocation returns answer and confidence |
| M5 | Download model weights | Required checkpoints are available locally |

### Evening

| Member | Task | Done When |
|---|---|---|
| M1 | Connect router to executor and model registry | Full request pipeline returns a response |
| M2 | Connect frontend to backend | Browser shows live API results |
| M3 | Build trace and output integration | Structured trace matches the API schema |
| M4 | Implement grounding wrapper | Region overlays are generated |
| M5 | Set up fine-tuning environment | Training script starts without error |

### Day 1 milestone

- backend accepts image + query and returns a response
- frontend uploads and displays results
- router classifies queries correctly
- at least one VQA pipeline runs end-to-end
- demo data is organized
- model weights are downloaded

## Day 2 — Pipeline Completion and Integration

### Morning

| Member | Task | Done When |
|---|---|---|
| M1 | Handle multi-image uploads | Two-image requests are processed correctly |
| M2 | Display evidence images | Change-map and overlays render in the UI |
| M3 | Refine router | All five task types pass demo routing checks |
| M4 | Implement change detection | Change map is produced from paired images |
| M5 | Start fine-tuning | Training loss is decreasing |

### Afternoon

| Member | Task | Done When |
|---|---|---|
| M1 | Support optical-SAR routing | Cross-modal input is identified correctly |
| M2 | Polish trace UI | Timing and stage outputs are readable |
| M3 | Build evidence helpers | Overlay generation works cleanly |
| M4 | Complete change VQA and optical-SAR pipelines | Both pipelines return answers |
| M5 | Monitor and export adapter | LoRA checkpoint is saved |

### Evening

| Member | Task | Done When |
|---|---|---|
| M1 | Run API-level integration tests | All five scenarios return valid JSON |
| M2 | Validate browser flow | All five demos render in the web app |
| M3 | Compute confidence scores | Every response includes confidence metadata |
| M4 | Add caption mode | Caption pipeline works for single-image requests |
| M5 | Load fine-tuned adapter | The adapted model is active in the pipeline |

### Day 2 milestone

- all five scenarios work end-to-end
- evidence images are generated
- execution trace is visible for each request
- confidence scores are present in responses

## Day 3 — Polish and Demo Readiness

### Morning

| Member | Task | Done When |
|---|---|---|
| M1 | Improve error handling | Failure modes are handled without crashing |
| M2 | Polish UI | Layout feels professional and responsive |
| M3 | Test validation edge cases | Unusual inputs are rejected gracefully |
| M4 | Harden model execution | OOM and fallback behavior are stable |
| M5 | Record benchmark numbers | Model quality metrics are documented |

### Afternoon

| Member | Task | Done When |
|---|---|---|
| All | Rehearsal round 1 | All five demos run and issues are identified |
| M1 | Fix backend issues | Bugs are resolved |
| M2 | Fix frontend issues | Bugs are resolved |
| M3 | Finalize README | Setup and usage instructions are complete |
| M4 | Prepare backup outputs | Sample JSON responses are saved |
| M5 | Prepare training documentation | Model adaptation details are documented |

### Evening

| Member | Task | Done When |
|---|---|---|
| All | Rehearsal round 2 and 3 | Demo flow is stable and under the time limit |
| M1 | Record backup demo video | Backup is available |
| M2 | Capture presentation screenshots | Visuals are prepared |
| M5 | Complete benchmark comparison | Final table is ready |

### Day 3 milestone

- all five demos run consistently
- no crashes on valid or invalid inputs
- UI is polished and presentation-ready
- setup instructions are documented
- backup demo assets are available

## Git Workflow

```text
main                ← verified, merged code
  └── dev           ← integration branch
      ├── feat/backend
      ├── feat/frontend
      ├── feat/agent
      ├── feat/pipelines
      └── feat/data
```

Rules:

- push to feature branches frequently
- merge to `dev` at each milestone
- only merge `dev` into `main` when all demo scenarios pass
- resolve conflicts early

## Integration Points

| Interface | Between | Contract |
|---|---|---|
| API schema | M1 ↔ M2 | shared response and request definition |
| Model interface | M1 ↔ M4 | consistent `.run(action, context)` structure |
| Router output | M3 → M1 | task type, models, and pipeline selection |
| Evidence files | M4 → M1 → M2 | images saved in `results/` and referenced in JSON |
| Trace format | M3 → M1 → M2 | execution trace schema |

> API schema and data contracts should be agreed early in Day 1. This prevents downstream rework.

## Communication Protocol

| Timing | Action | Standard |
|---|---|---|
| Start of day | Stand-up | brief review of priorities |
| Every two hours | Status update | shared progress or blocking issue |
| Integration stage | Pair merge | coordinated review and merge |
| End of day | Demo rehearsal | run all scenarios and log issues |

## Contingency Plans

| Situation | Response |
|---|---|
| Model fails to load | return a graceful fallback response |
| Fine-tuning is delayed | use base model and document adaptation progress |
| Frontend breaks late | use Swagger UI as fallback |
| GPU memory is insufficient | reduce image resolution or switch to a smaller model |
| A team member is blocked | pair-programming and shared review |
| Backend fails during demo | use the recorded backup video |
