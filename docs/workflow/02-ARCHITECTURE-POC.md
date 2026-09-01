# 02 — Architecture (POC)

> Simplified architecture for the 3-day build.

---

## High-Level Flow

```
┌─────────────────────────┐
│     FRONTEND (Next.js)  │
│  • Image upload (1-2)   │
│  • Modality selector    │
│  • Query text input     │
│  • Result + Evidence    │
│  • Execution Trace      │
│  localhost:3000         │
└───────────┬─────────────┘
            │ POST /api/analyze (multipart)
            ↓
┌─────────────────────────┐
│   BACKEND (FastAPI)     │
│  • Input Validator      │
│  • Rule-Based Router    │
│  • Pipeline Executor    │
│  • Model Registry       │
│  • Output Integrator    │
│  localhost:8000         │
└───────────┬─────────────┘
            │
    ┌───────┼───────┐
    ↓       ↓       ↓
┌───────┐┌───────┐┌───────┐
│Single ││BiTemp ││Cross  │
│Image  ││oral   ││Modal  │
│       ││       ││       │
│• VQA  ││• CD   ││• Fuse │
│• Cap  ││• CVQA ││• VLM  │
│• Grnd ││       ││       │
└───┬───┘└───┬───┘└───┬───┘
    └────────┼────────┘
             ↓
    Output Integrator
    (answer + evidence
     + confidence + trace)
```

---

## Directory Structure (POC)

```
sih26/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry + CORS + lifespan
│   │   ├── api/
│   │   │   ├── routes.py           # POST /api/analyze, GET /api/health
│   │   │   └── schemas.py          # Pydantic request/response models
│   │   ├── agent/
│   │   │   ├── router.py           # RuleBasedRouter (keyword + input analysis)
│   │   │   ├── executor.py         # PipelineExecutor (runs model steps)
│   │   │   └── validator.py        # InputValidator (format, count, modality)
│   │   ├── models/
│   │   │   ├── registry.py         # ModelRegistry (load/unload/get)
│   │   │   ├── base.py             # BaseModel interface
│   │   │   ├── vqa.py              # VQA pipeline wrapper
│   │   │   ├── caption.py          # Caption pipeline wrapper (may reuse VQA)
│   │   │   ├── grounding.py        # Grounding DINO + SAM wrapper
│   │   │   ├── change_detection.py # Change detection model wrapper
│   │   │   ├── change_vqa.py       # Change VQA wrapper
│   │   │   └── optical_sar.py      # Optical-SAR fusion wrapper
│   │   ├── output/
│   │   │   ├── integrator.py       # Combine model outputs into response
│   │   │   ├── evidence.py         # Generate overlay images, change maps
│   │   │   └── trace.py            # Build execution trace JSON
│   │   └── utils/
│   │       ├── image_utils.py      # Image loading, resize, preprocessing
│   │       └── config.py           # Settings (model paths, VRAM limits)
│   ├── models/                     # Model weights directory
│   │   ├── vqa/
│   │   ├── grounding/
│   │   ├── change/
│   │   └── fusion/
│   ├── results/                    # Generated evidence images
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx            # Main page
│   │   │   └── layout.tsx          # Root layout
│   │   ├── components/
│   │   │   ├── ImageUpload.tsx      # Drag-drop image upload
│   │   │   ├── QueryInput.tsx       # Text input + example queries
│   │   │   ├── ResultPanel.tsx      # Answer + evidence display
│   │   │   ├── ExecutionTrace.tsx   # Trace visualization
│   │   │   └── ConfidenceBadge.tsx  # Confidence score badge
│   │   └── hooks/
│   │       └── useAnalysis.ts       # API call hook
│   └── package.json
│
├── data/
│   └── demo/                       # Pre-selected demo images
│       ├── vqa/
│       ├── grounding/
│       ├── change/
│       └── optical_sar/
│
├── training/                       # Fine-tuning scripts
│   ├── finetune_vlm.py
│   └── configs/
│
├── mds/                            # Original planning docs
├── mds2/                           # This POC sprint docs
└── README.md
```

---

## API Contract (POC — Single Endpoint)

### `POST /api/analyze`

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `images` | File[] | Yes | 1 or 2 satellite images |
| `query` | string | Yes | Natural language question |
| `modalities` | string | No | Comma-separated: "optical", "sar", "optical,sar" |
| `dates` | string | No | Comma-separated dates: "2024-01,2024-08" |

**Response:** `application/json`

```json
{
  "answer": "Built-up area increased in the eastern portion.",
  "confidence": 0.87,
  "evidence": {
    "images": [
      { "type": "change_map", "url": "/results/abc/change.png", "caption": "Changes in red" }
    ],
    "regions": [
      { "bbox": [120, 80, 300, 250], "label": "New built-up", "confidence": 0.91 }
    ]
  },
  "execution_trace": {
    "input_validation": {
      "image_count": 2,
      "format": ["GeoTIFF", "GeoTIFF"],
      "modality": ["optical", "optical"],
      "temporal": true,
      "cross_modal": false,
      "compatible": true,
      "warnings": []
    },
    "detected_task": "CHANGE_ANALYSIS",
    "task_confidence": 0.90,
    "reasoning": "Bi-temporal input + change keywords detected",
    "selected_models": [
      { "name": "Change Detection", "version": "1.0" },
      { "name": "RS-VLM", "version": "1.0" }
    ],
    "pipeline_steps": [
      { "step": 1, "model": "change_detection", "action": "generate_change_map", "status": "success", "time_ms": 1240 },
      { "step": 2, "model": "rs_vlm", "action": "describe_changes", "status": "success", "time_ms": 890 }
    ],
    "total_time_ms": 2130
  }
}
```

### `GET /api/health`

```json
{
  "status": "healthy",
  "models_loaded": ["rs_vlm"],
  "gpu_available": true,
  "gpu_memory_used": "5.5 / 8.0 GB"
}
```

---

## Tech Stack (POC — Minimal)

| Layer | Choice | Why (POC context) |
|-------|--------|-------------------|
| Frontend | Next.js 14 + Tailwind + shadcn/ui | AI can scaffold in < 1 hour |
| Backend | FastAPI + Python 3.11 | ML ecosystem, fast, auto-docs |
| ML | PyTorch 2.x + Transformers | Standard, all models support it |
| Image IO | Pillow + rasterio | GeoTIFF support |
| Model loading | Sequential on-demand | 8GB VRAM constraint |
| State mgmt | React useState (no Zustand needed for POC) | Simplicity |
| Deployment | `uvicorn` + `npm run dev` | No Docker needed for demo |

---

## GPU Memory Strategy

```
RTX 4060 — 8 GB VRAM

Rule: ONE major model at a time
Strategy: Load → Infer → Unload → Next

Pipeline VRAM Timeline:
──────────────────────────────────────────
VQA request:
  Load VLM (5.5 GB) → Answer → Unload
  Peak: 5.5 GB ✅

Grounding request:
  Load GDINO (0.7 GB) + SAM (0.35 GB) → Detect + Segment → Unload
  Peak: 1.1 GB ✅

Change request:
  Load CD model (0.15 GB) → Change map → Unload
  Load VLM (5.5 GB) → Describe → Unload
  Peak: 5.5 GB ✅

Optical-SAR request:
  Load Fusion net (0.5 GB) → Fuse → Unload
  Load VLM (5.5 GB) → Analyze → Unload
  Peak: 5.5 GB ✅
──────────────────────────────────────────
```

> [!TIP]
> The ModelRegistry handles all load/unload logic. Pipeline wrappers just call `registry.get("model_name")` and the registry handles VRAM management.
