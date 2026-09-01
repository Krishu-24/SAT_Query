# 03 — Work Division

> 5 members × 3 days. Everyone uses Claude/Antigravity. Ship a working POC.

---

## Team Roles

| Code | Role | Primary Focus | Key Deliverables |
|------|------|---------------|------------------|
| **M1** | **Backend Lead** | FastAPI server, API routes, model registry | Working `/api/analyze` endpoint |
| **M2** | **Frontend Lead** | Next.js app, UI components, UX | Working web interface |
| **M3** | **Agent/Router Lead** | Input validation, task routing, output integration | Agent that auto-detects task type |
| **M4** | **ML Pipelines Lead** | Model wrappers, inference code, evidence generation | All 5 model pipelines working |
| **M5** | **Data/Fine-Tuning Lead** | Demo data, fine-tuning scripts, model preparation | Fine-tuned adapter + demo dataset |

> [!IMPORTANT]
> Everyone is vibe-coding with Claude/Antigravity. This means each person can move FAST. The bottleneck is integration, not individual features. Communicate constantly.

---

## Day 1 — Scaffold + Core (Sept 1)

### Morning (9 AM – 1 PM)

| Member | Task | Details | Done When |
|--------|------|---------|-----------|
| **M1** | Scaffold backend | FastAPI project, CORS, lifespan, routes skeleton, Pydantic schemas | `GET /api/health` returns 200 |
| **M2** | Scaffold frontend | Next.js + Tailwind + shadcn/ui, ImageUpload component, QueryInput component | Can upload image + type query in browser |
| **M3** | Build RuleBasedRouter | Keyword dictionaries, input analysis, TaskType enum, RoutingDecision dataclass | Router correctly classifies 10 test queries |
| **M4** | Build ModelRegistry | Load/unload/get logic, VRAM management, config for all 6 model slots | Registry can load and unload a dummy model |
| **M5** | Prepare demo data | Download VRSBench samples, LEVIR-CD pairs, BigEarthNet-MM pairs, organize into `data/demo/` | 3+ test images per demo scenario |

### Afternoon (2 PM – 6 PM)

| Member | Task | Details | Done When |
|--------|------|---------|-----------|
| **M1** | `/api/analyze` endpoint | Accept images + query, save temps, call validator + router + executor, return JSON | Endpoint accepts upload + returns 'Model output not available' |
| **M2** | ResultPanel + ExecutionTrace | Result display component, execution trace component, confidence badge | Empty data renders beautifully |
| **M3** | InputValidator | Format check (GeoTIFF/TIFF/PNG), image count, modality detection, pair compatibility | Rejects 3+ images, wrong format. Accepts valid inputs |
| **M4** | VQA pipeline wrapper | Load VLM, preprocess image, run inference, return answer + confidence | `python -c "from app.models.vqa import ..."` works |
| **M5** | Download model weights | Download all model checkpoints (VLM AWQ, GDINO, SAM, CD model) | All weights in `backend/models/` |

### Evening (7 PM – 11 PM)

| Member | Task | Details | Done When |
|--------|------|---------|-----------|
| **M1** | Wire router → executor → models | PipelineExecutor runs steps, connects to ModelRegistry | Full pipeline: upload → router → model → response |
| **M2** | Connect frontend → backend | Axios POST to /api/analyze, display real response, error handling | Upload image + query → see real answer in browser |
| **M3** | TraceBuilder + OutputIntegrator | Build execution trace JSON, combine model outputs into final response | Trace JSON matches API schema |
| **M4** | Grounding pipeline wrapper | Grounding DINO + SAM, detect regions, generate overlay image | Grounding produces highlighted image |
| **M5** | Set up fine-tuning env | Install PEFT, prepare VRSBench data loader, test QLoRA config | Training script starts without errors |

### Day 1 Milestone
```
✅ Backend accepts image + query → returns VQA answer
✅ Frontend uploads image + displays result
✅ Router classifies queries correctly
✅ At least VQA pipeline working end-to-end
✅ Demo data organized
✅ All model weights downloaded
```

---

## Day 2 — All Pipelines + Integration (Sept 2)

### Morning (9 AM – 1 PM)

| Member | Task | Details | Done When |
|--------|------|---------|-----------|
| **M1** | Multi-image upload handling | Handle 2 images in /api/analyze, pass metadata (modality, dates) | 2-image upload works |
| **M2** | Evidence image display | Show evidence images from backend, before/after/change-map layout | Evidence images render in UI |
| **M3** | Refine router for all 5 tasks | Test all 5 demo queries route correctly, edge cases | 100% routing accuracy on demo queries |
| **M4** | Change Detection pipeline | Load CD model, generate change map, save as evidence image | Change map PNG generated from 2 images |
| **M5** | Start fine-tuning run | Launch QLoRA fine-tune on VRSBench (or BigEarthNet subset) | Training running, loss decreasing |

### Afternoon (2 PM – 6 PM)

| Member | Task | Details | Done When |
|--------|------|---------|-----------|
| **M1** | Optical-SAR handling | Detect cross-modal from modalities, route to fusion pipeline | Cross-modal detection works |
| **M2** | Execution trace UI polish | Icons, timing badges, step-by-step visualization, color coding | Trace looks professional |
| **M3** | Evidence generation helpers | Overlay bboxes on images, colorize change maps, save to results/ | evidence.py generates clean overlays |
| **M4** | Change VQA + Optical-SAR pipelines | Change VQA (CD + VLM), Optical-SAR fusion (fusion net + VLM) | Both pipelines return answers |
| **M5** | Fine-tuning monitoring + adapter export | Check training, export LoRA adapter when done | LoRA adapter saved to models/ |

### Evening (7 PM – 11 PM)

| Member | Task | Details | Done When |
|--------|------|---------|-----------|
| **M1** | Integration testing | Test all 5 demo scenarios through the API | All 5 return valid JSON |
| **M2** | Full integration with backend | All 5 demos work in the browser, loading states, error display | All 5 demos render in UI |
| **M3** | Confidence scoring | Heuristic confidence from model outputs, aggregate for multi-step | Every response has confidence |
| **M4** | Caption pipeline (reuse VQA) | Add caption prompt to VQA wrapper, test | Caption mode works |
| **M5** | Load fine-tuned adapter | Integrate LoRA adapter into VQA pipeline, A/B test vs base | Fine-tuned model loaded and working |

### Day 2 Milestone
```
✅ ALL 5 demo scenarios work end-to-end (browser → backend → model → response)
✅ Evidence images generated for grounding + change detection
✅ Execution trace displays for every request
✅ Fine-tuned adapter loaded into VQA pipeline
✅ Confidence scores in every response
```

---

## Day 3 — Polish + Demo (Sept 3)

### Morning (9 AM – 1 PM)

| Member | Task | Details | Done When |
|--------|------|---------|-----------|
| **M1** | Error handling + edge cases | Graceful errors for all failure modes, timeout handling | No crashes on any input |
| **M2** | UI polish | Loading spinner, example query badges, responsive layout, dark header | UI looks professional |
| **M3** | Validation edge cases | Test weird inputs: 3 images, .docx file, empty query, huge image | All rejected gracefully |
| **M4** | Pipeline robustness | Handle model OOM gracefully, fallback responses, retry logic | Models don't crash |
| **M5** | Benchmark numbers | Run fine-tuned model on 20-50 test samples, record accuracy | Accuracy table ready |

### Afternoon (2 PM – 6 PM)

| Member | Task | Details | Done When |
|--------|------|---------|-----------|
| **ALL** | Demo rehearsal round 1 | Run all 5 demos, identify failures, fix bugs | All 5 pass |
| **M1** | Fix backend bugs from rehearsal | Whatever broke | Fixed |
| **M2** | Fix frontend bugs from rehearsal | Whatever broke | Fixed |
| **M3** | Write README.md | Setup instructions, architecture, how to run | README complete |
| **M4** | Prepare backup responses | Pre-computed results for each demo scenario | Backup JSON files ready |
| **M5** | Prepare fine-tuning documentation | What was fine-tuned, on what data, results | Doc ready for judges |

### Evening (7 PM – 11 PM)

| Member | Task | Details | Done When |
|--------|------|---------|-----------|
| **ALL** | Demo rehearsal round 2-3 | Full demo run, timed (< 10 min), smooth transitions | Confident demo flow |
| **M1** | Record backup demo video | Screen record all 5 scenarios working | Video saved |
| **M2** | Screenshot all 5 demos | High-quality screenshots for presentation | Screenshots saved |
| **M5** | Final benchmark + comparison table | Base model vs fine-tuned comparison | Table in docs |

### Day 3 Milestone
```
✅ All 5 demos pass consistently (3+ successful runs)
✅ No crashes on valid or invalid inputs
✅ UI is polished and professional
✅ README with setup instructions
✅ Backup demo video recorded
✅ Fine-tuning documentation ready
✅ Team can present in < 10 minutes
```

---

## Git Workflow

```
main              ← only merged, tested code
  └── dev         ← integration branch
      ├── feat/backend     ← M1
      ├── feat/frontend    ← M2
      ├── feat/agent       ← M3
      ├── feat/pipelines   ← M4
      └── feat/data        ← M5
```

**Rules:**
- Push to your feature branch frequently
- Merge to `dev` at each day's milestone
- Only merge `dev → main` when all 5 demos pass
- Resolve conflicts immediately — don't let them pile up

---

## Integration Points (Where Things Break)

| Interface | Between | Contract |
|-----------|---------|----------|
| API Schema | M1 ↔ M2 | `schemas.py` — agree on this Day 1 morning |
| Model Interface | M1 ↔ M4 | `base.py` — every model has `.run(action, context) → dict` |
| Router Output | M3 → M1 | `RoutingDecision` dataclass — task type, models, pipeline |
| Evidence Files | M4 → M1 → M2 | Images saved to `results/`, URL in response JSON |
| Trace Format | M3 → M1 → M2 | `ExecutionTrace` schema — agreed Day 1 |

> [!WARNING]
> **Day 1 morning priority:** M1 + M2 + M3 must agree on the API schema and data contracts before anyone writes code. Spend 30 minutes on this. It prevents 3 hours of refactoring later.

---

## Communication Protocol

| When | What | How |
|------|------|-----|
| Day start | Standup | 10 min call — what you'll do today |
| Every 2 hours | Status ping | Message in group chat: "VQA pipeline working ✅" or "Blocked on X" |
| Integration time | Pair merge | M1 screenshares, others merge into dev together |
| End of day | Demo test | Everyone watches all 5 scenarios run |

---

## Contingency Plans

| If... | Then... |
|-------|---------|
| A model won't load | Return 'Model output not available' for that pipeline |
| Fine-tuning doesn't converge in time | Use base model + claim "adaptation in progress" |
| Frontend bugs last-minute | Demo from Swagger UI (`/docs`) as fallback |
| GPU runs out of memory | Reduce image resolution, use smaller model variant |
| Team member blocked | Another member pair-codes with them using Claude |
| Backend crashes on demo day | Pre-recorded demo video as backup |
