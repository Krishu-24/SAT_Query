# 01 — POC Overview

> What the project is building in three days, including the scope boundaries and delivery targets.

## Goal

Build a working web application in which a user uploads satellite imagery and asks a natural-language question. An agent identifies the task, routes the request to the appropriate model pipeline, executes the analysis, and returns a structured result with confidence and execution trace details.

## In Scope

| # | Feature | Priority |
|---|---|---|
| 1 | Single-image VQA | Critical |
| 2 | Text-guided grounding with detection + segmentation | Critical |
| 3 | Bi-temporal change detection and description | Critical |
| 4 | Change VQA for specific change questions | Critical |
| 5 | Optical + SAR joint analysis | Critical |
| 6 | Rule-based agent/router for task detection | Critical |
| 7 | Input validation for format, count, and modality | Critical |
| 8 | Execution trace display | Critical |
| 9 | Evidence images such as overlays and change maps | Critical |
| 10 | Confidence scores | Important |
| 11 | At least one remote-sensing-adapted model | Important |

## Out of Scope

| Feature | Why It Is Deferred | Planned Later |
|---|---|---|
| LLM-based router | Deterministic, low-cost rule-based routing is sufficient for the demo | Week 2 |
| Celery / Redis task queue | Synchronous execution is adequate for a POC | Production |
| Docker deployment | Local execution is enough for the demo | Pre-submission |
| Full benchmark suite | Use a curated set of strong demo images instead | Week 2 |
| PDF report generation | JSON results are sufficient for the current milestone | Week 2 |
| Geographic overlap checks | Assume demo inputs are pre-aligned | Week 2 |
| Multi-GPU parallelism | Sequential loading is adequate on a single GPU | Not required |
| User auth / sessions | Single-user demo only | Production |

## Success Criteria

By end of Day 3, the system should satisfy the following:

- all five demo scenarios work end-to-end through the web UI
- the agent detects the task type without manual selection
- every response includes answer, evidence, confidence, and trace metadata
- invalid input is rejected cleanly with clear feedback
- at least one model demonstrates remote-sensing adaptation
- the system runs on a single RTX 4060 with 8 GB VRAM
- the full demonstration can be completed in under 10 minutes

## Architecture Summary

```text
User → Frontend → Backend → Agent Router
                             ↓
                       Input Validator
                             ↓
                       Task Classifier
               ┌─────────────┼─────────────┐
               ↓             ↓             ↓
        Single-Image   Bi-Temporal   Cross-Modal
        (VQA / Caption /   (Change       (Optical-SAR
         Grounding)      Detection)     Fusion)
               └─────────────┼─────────────┘
                             ↓
                     Output Integrator
                     (answer + evidence +
                      confidence + trace)
                             ↓
                          Frontend
```

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Router type | Rule-based keyword + input analysis | Deterministic, zero VRAM, strong demo fit |
| Model loading | Sequential load → infer → unload | Fits 8 GB VRAM constraints |
| Frontend framework | Next.js + Tailwind + shadcn/ui | Fast to scaffold and visually consistent |
| Backend framework | FastAPI | Python ML ecosystem and quick API iteration |
| Image format | GeoTIFF/TIFF first, PNG/JPEG for demo | Aligns with remote-sensing requirements |
| Fine-tuning | QLoRA on VLM with RS data | Satisfies the adaptation requirement |

## What Makes It Agentic

The user never selects a model directly. The system:

1. analyzes the inputs and modality
2. interprets the user intent
3. selects the appropriate model or model chain
4. executes the pipeline and records timing
5. combines evidence into a single response

This is the layer that distinguishes the project from a simple collection of inference models.
