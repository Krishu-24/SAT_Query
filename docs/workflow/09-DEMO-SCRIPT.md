# 09 — Demo Script

> 5 demo scenarios, test data sources, fallback plans.

---

## Demo Flow (10 minutes total)

```
1. [1 min]  System overview — what SatQuery AI does
2. [1.5 min] Demo 1: VQA — single image question
3. [1.5 min] Demo 2: Grounding — highlight a region
4. [2 min]   Demo 3: Change Detection — bi-temporal
5. [1.5 min] Demo 4: Change VQA — specific question
6. [2 min]   Demo 5: Optical + SAR fusion
7. [0.5 min] Wrap-up + questions
```

---

## Demo 1 — Single-Image VQA

| Field | Value |
|-------|-------|
| Input | 1 optical satellite image |
| Query | "What objects are present in this image?" |
| Expected Task | VQA |
| Expected Model | RS-VLM |

**What to show:**
- Upload image
- Type question
- Click Analyze
- Point out: agent auto-detected VQA
- Show answer + confidence
- Show execution trace (1 step, ~1-2s)

**Judge looks for:** Accurate land cover / object identification, RS-specific vocabulary

---

## Demo 2 — Text-Guided Grounding

| Field | Value |
|-------|-------|
| Input | 1 satellite image (with visible water body) |
| Query | "Highlight the water body in this image." |
| Expected Task | GROUNDING |
| Expected Models | Grounding DINO → SAM |

**What to show:**
- Same upload flow
- Agent detects "highlight" keyword → GROUNDING
- Evidence image: water body highlighted in blue overlay
- Bounding box coordinates + confidence
- 2-step pipeline in trace (detect → segment)

**Judge looks for:** Accurate region highlighting, visual evidence quality

---

## Demo 3 — Change Detection

| Field | Value |
|-------|-------|
| Input | 2 optical images (same area, different dates) |
| Query | "What changed between these two dates?" |
| Expected Task | CHANGE_DETECTION |
| Expected Models | Change Detection → RS-VLM |

**What to show:**
- Upload TWO images (set dates)
- Agent detects bi-temporal + general query → CHANGE_DETECTION
- Before / After / Change Map side by side
- Change ratio percentage
- Description of changes from VLM

**Judge looks for:** Accurate change map, meaningful description, agent distinguishes from Change VQA

---

## Demo 4 — Change VQA

| Field | Value |
|-------|-------|
| Input | Same 2 images as Demo 3 |
| Query | "Has the built-up area increased, decreased, or remained unchanged?" |
| Expected Task | CHANGE_VQA |
| Expected Models | Change Detection → Change VQA |

**What to show:**
- Same images, DIFFERENT question type
- Agent detects specific question → CHANGE_VQA (not CHANGE_DETECTION)
- Direct answer: "increased/decreased/unchanged"
- Point out the agent distinguished Demo 3 (general) from Demo 4 (specific)

**Judge looks for:** Correct specific answer, agent intelligence in task routing

---

## Demo 5 — Optical + SAR Analysis

| Field | Value |
|-------|-------|
| Input | 1 optical + 1 SAR image (same area) |
| Query | "Use both images to identify built-up and water-covered regions." |
| Expected Task | OPTICAL_SAR |
| Expected Models | Fusion Network → RS-VLM |

**What to show:**
- Upload optical (set modality: Optical) + SAR (set modality: SAR)
- Agent detects cross-modal → OPTICAL_SAR fusion
- Land cover map with color coding
- Natural language explanation
- Both input images shown for comparison

**Judge looks for:** Actual fusion (not two separate answers), land cover accuracy, cross-modal reasoning

---

## Test Data Sources

| Source | Type | Use For | Download |
|--------|------|---------|---------|
| VRSBench test | High-res optical | Demo 1, 2 | `github.com/lx709/VRSBench` |
| RSVQA-HR test | Aerial optical | Demo 1 | `rsvqa.sylvainlobry.com` |
| LEVIR-CD test | Bi-temporal pairs | Demo 3, 4 | `justchenhao.github.io/LEVIR` |
| CDVQA test | Bi-temporal + QA | Demo 4 | `github.com/YZHJessica/CDVQA` |
| BigEarthNet-MM | Optical + SAR pairs | Demo 5 | `bigearth.net` |

---

## Backup Plans

| Failure | Backup |
|---------|--------|
| Model won't load | Pre-computed JSON responses for each demo |
| Inference too slow | Pre-load the VLM before demo, skip unloading |
| Wrong answer | Have 3 backup images per demo, use the one that works best |
| Frontend crash | Demo from Swagger UI at `localhost:8000/docs` |
| GPU OOM | Restart backend, use Florence-2 (smaller) instead of Qwen |
| Total system failure | Play pre-recorded demo video |

---

## Pre-Demo Checklist

### Night Before
- [ ] All 5 demos pass 3+ times
- [ ] Backup images selected and tested
- [ ] Pre-computed backup responses saved
- [ ] Demo video recorded as last resort
- [ ] All team members know speaking parts

### 1 Hour Before
- [ ] `GET /api/health` returns healthy
- [ ] Frontend at localhost:3000 loads
- [ ] Demo images in a ready-to-upload folder
- [ ] Screen sharing / projector tested

### During Demo
- [ ] Start with Demo 1 (simplest, builds confidence)
- [ ] Show execution trace for EVERY demo
- [ ] Point out agent decisions explicitly
- [ ] End with Demo 5 (most complex, strong finish)
- [ ] Don't apologize for load times — explain the model is loading

---

## Talking Points

### When explaining the system:
> "The user never selects a model. They just upload images and ask a question. Our agent analyzes the input, determines the task type, selects the right specialist models, runs the pipeline, and returns an evidence-backed answer."

### When showing the execution trace:
> "Every response includes a transparent execution trace — what the agent detected, which models it chose, and how long each step took. This is observable agentic behavior."

### When showing fine-tuning:
> "We fine-tuned our VLM using QLoRA on remote sensing datasets like BigEarthNet and VRSBench. This domain adaptation is what allows the model to understand satellite-specific concepts like land cover classification and spectral signatures."

### When showing optical-SAR:
> "This is actual cross-modal fusion, not just running two separate models. The optical image provides spectral information while SAR provides structural and moisture data. Our fusion network combines these at the feature level."
