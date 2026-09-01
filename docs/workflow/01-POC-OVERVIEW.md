# 01 — POC Overview

> What we're building in 3 days, what's in scope, what's cut.

---

## One-Sentence Goal

Build a **working web app** where a user uploads satellite image(s) + types a question, and an **AI agent** automatically routes to the right model pipeline, runs inference, and returns an **evidence-backed answer** with confidence and execution trace.

---

## In Scope (MUST HAVE for POC)

| # | Feature | Priority |
|---|---------|----------|
| 1 | Single-image VQA | 🔴 Critical |
| 2 | Text-guided grounding (DINO + SAM) | 🔴 Critical |
| 3 | Bi-temporal change detection + description | 🔴 Critical |
| 4 | Change VQA (specific questions about changes) | 🔴 Critical |
| 5 | Optical + SAR joint analysis | 🔴 Critical |
| 6 | Rule-based agent/router (auto task detection) | 🔴 Critical |
| 7 | Input validation (format, count, modality) | 🔴 Critical |
| 8 | Execution trace display | 🔴 Critical |
| 9 | Evidence images (change maps, overlays, bboxes) | 🔴 Critical |
| 10 | Confidence scores | 🟡 Important |
| 11 | At least 1 model fine-tuned on RS data | 🟡 Important |

## Out of Scope (Cut for POC)

| Feature | Why Cut | Add Later |
|---------|---------|----------|
| LLM-based router | Rule-based is deterministic + zero VRAM | Week 2 |
| Celery/Redis task queue | Synchronous is fine for demo | Production |
| Docker deployment | `python main.py` + `npm run dev` is fine | Pre-submission |
| Full benchmark suite | Cherry-pick best demo images instead | Week 2 |
| PDF report generation | JSON response is enough | Week 2 |
| Geographic overlap check | Assume demo images are co-registered | Week 2 |
| Multi-GPU / model parallelism | Sequential loading on single GPU | Never needed |
| User auth / sessions | Single-user demo | Production |

---

## Success Criteria (Day 3 EOD)

```
✅ All 5 demo scenarios work end-to-end through the web UI
✅ Agent automatically detects task type (no manual model selection)
✅ Each response includes: answer + evidence + confidence + trace
✅ Input validation rejects bad inputs gracefully
✅ At least 1 model shows RS adaptation (LoRA adapter or fine-tuned weights)
✅ System runs on a single RTX 4060 (8GB VRAM)
✅ Demo takes < 10 minutes to present all 5 scenarios
```

---

## Architecture Summary (POC)

```
User → Frontend (Next.js) → Backend (FastAPI) → Agent Router
                                                     ↓
                                              Input Validator
                                                     ↓
                                              Task Classifier
                                                     ↓
                                    ┌────────────────┼────────────────┐
                                    ↓                ↓                ↓
                              Single-Image     Bi-Temporal      Cross-Modal
                              (VQA/Caption/    (Change Det +    (Optical-SAR
                               Grounding)       Change VQA)      Fusion)
                                    ↓                ↓                ↓
                                    └────────────────┼────────────────┘
                                                     ↓
                                              Output Integrator
                                              (answer + evidence +
                                               confidence + trace)
                                                     ↓
                                                  Frontend
```

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Router type | Rule-based (keyword + input analysis) | Deterministic, zero VRAM, perfect for demo |
| Model loading | Sequential (load → run → unload) | Only 8GB VRAM, can't keep all models loaded |
| Frontend framework | Next.js + shadcn/ui + Tailwind | Fast to scaffold with AI, professional look |
| Backend framework | FastAPI | Fast, async, auto-docs, Python ML ecosystem |
| Image format | GeoTIFF/TIFF primary, PNG/JPEG for demo | Matches ISRO requirement |
| Fine-tuning | QLoRA on VLM with RS data | Satisfies mandatory RS adaptation req |
| Vibe coding | All 5 members use Claude/Antigravity | Max velocity, consistent code style |

---

## What Makes This "Agentic"

The user **never** selects a model. The system:

1. **Analyzes inputs** — How many images? What modality? What format?
2. **Parses intent** — Is this VQA? Grounding? Change detection?
3. **Selects models** — Picks the right specialist(s)
4. **Builds pipeline** — Chains multiple models if needed
5. **Executes & tracks** — Runs pipeline, records timing
6. **Assembles output** — Combines results, generates evidence, computes confidence

This is Layer 2 (The Brain) that makes it SatQuery AI, not just "a collection of models."
