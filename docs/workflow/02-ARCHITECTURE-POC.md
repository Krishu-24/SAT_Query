# 02 — Architecture (POC)

> Simplified architecture for the three-day build.

## High-Level Flow

```text
Frontend (Next.js)
  └── POST /api/analyze
        ↓
Backend (FastAPI)
  ├── Input Validator
  ├── Rule-Based Router
  ├── Pipeline Executor
  ├── Model Registry
  └── Output Integrator
        ↓
    ┌──────────────┬──────────────┬──────────────┐
    ↓              ↓              ↓
Single-image    Bi-temporal    Cross-modal
(VQA / Caption /   (Change       (Optical-SAR
 Grounding)      Detection /    Fusion)
                 Change VQA)
    └──────────────┴──────────────┘
                     ↓
             Output Integrator
             (answer + evidence +
              confidence + trace)
```

## Directory Structure

```text
sih26/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── routes.py
│   │   │   └── schemas.py
│   │   ├── agent/
│   │   │   ├── router.py
│   │   │   ├── executor.py
│   │   │   └── validator.py
│   │   ├── models/
│   │   │   ├── registry.py
│   │   │   ├── base.py
│   │   │   ├── vqa.py
│   │   │   ├── grounding.py
│   │   │   ├── change_detection.py
│   │   │   ├── change_vqa.py
│   │   │   └── optical_sar.py
│   │   ├── output/
│   │   │   ├── integrator.py
│   │   │   ├── evidence.py
│   │   │   └── trace.py
│   │   └── utils/
│   │       ├── image_utils.py
│   │       └── config.py
│   ├── models/
│   ├── results/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   └── package.json
│
├── data/
│   └── demo/
│
├── training/
├── README.md
└── docs/
```

## API Contract

### `POST /api/analyze`

Request: `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `images` | `File[]` | Yes | One or two satellite images |
| `query` | `string` | Yes | Natural-language question |
| `modalities` | `string` | No | `optical`, `sar`, or `optical,sar` |
| `dates` | `string` | No | Comma-separated dates such as `2024-01,2024-08` |

Response payload example:

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

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 14 + Tailwind + shadcn/ui | Fast UI iteration and consistent UX |
| Backend | FastAPI + Python 3.11 | Strong ML ecosystem and quick deployment |
| ML | PyTorch + Transformers | Standard stack for remote-sensing models |
| Image IO | Pillow + Rasterio | GeoTIFF support |
| Model loading | Sequential on-demand | Fits the VRAM budget |
| Deployment | `uvicorn` + `npm run dev` | Simple local demo path |

## GPU Memory Strategy

A single RTX 4060 has 8 GB VRAM, so the system should avoid loading all large models simultaneously. The registry layer manages this by loading, inferring, and unloading on demand.

**Rule:** one major model at a time.

**Examples:**

- VQA: ~5.5 GB peak
- Grounding: ~1.1 GB peak
- Change detection + VLM: ~5.5 GB peak
- Optical-SAR + VLM: ~6.0 GB peak

> The model registry is responsible for handling load/unload behavior so that the wrapper implementations stay focused on inference logic.
