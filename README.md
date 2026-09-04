# SatQuery AI

Agentic remote sensing analysis system for SIH 2026 / ISRO-SAC.

## Project Overview

SatQuery AI enables users to upload one or more satellite images and ask natural-language questions such as:

- "What changed between these two dates?"
- "Highlight the water body in this image."
- "Estimate the built-up increase in the eastern region."

The system routes each request to the correct model pipeline, executes the analysis, and returns an evidence-backed response with confidence and execution trace metadata.

## Current Status

The repository currently includes:

1. A deterministic, zero-VRAM routing layer that classifies requests into multiple task types without relying on a large LLM.
2. A pipeline execution framework that coordinates model loading, inference, and output aggregation.
3. Qwen2.5-VL integration for VQA and captioning workflows.
4. A working FastAPI backend and browser-based demo UI for end-to-end validation.
5. A fallback mode that keeps the app stable when model weights are unavailable or GPU resources are limited.
6. A real optical-SAR fusion model (`backend/app/models/optical_sar.py`) — BIFOLD BigEarthNet v2.0 ResNet-18-all-v0.2.0, producing real 19-class CORINE land-cover predictions from co-registered Sentinel-1/Sentinel-2 imagery, not a stub.

## Quick Start

### 1. Set up the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Download the VLM (optional)

```bash
pip install huggingface_hub
huggingface-cli download Qwen/Qwen2.5-VL-7B-Instruct-AWQ --local-dir backend/models/vqa/qwen25vl
```

### 3. Start the API

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 4. Run the frontend demo

```bash
cd frontend
python -m http.server 3000
```

Open http://localhost:3000 and upload an image to test the workflow.

## Optical-SAR Fusion Model — Runtime Notes

`backend/app/models/optical_sar.py` uses a pretrained model from
HuggingFace Hub (`BIFOLD-BigEarthNetv2-0/resnet18-all-v0.2.0`) via
`from_pretrained(...)`. A few things to know before running it:

- **The model weights are NOT stored in this repo.** They're downloaded
  from HuggingFace the first time the fusion pipeline actually runs (i.e.
  the first request that routes to `fuse_modalities`), then cached locally
  (typically under `~/.cache/huggingface/hub/`). Loading is lazy via
  `ModelRegistry` -- nothing downloads at server startup.
- **Requires internet access on first run only.** The weights are small
  (~45MB, an 11M-parameter ResNet-18), so this is fast. Every run after
  the first uses the local cache with no network call.
- **Input format:** this model expects `context["images"][0]` and
  `context["images"][1]` to be pre-stacked, co-registered, same-resolution
  multi-band GeoTIFFs -- optical: 10 bands (B02..B12, 20m bands
  nearest-upsampled to the 10m grid); SAR: 2 bands (VV, VH, gamma0 dB) --
  not arbitrary raw images. See the module docstring for details.
- **Output:** real 19-class BigEarthNet v2.0 / CORINE land-cover
  predictions per 1.2km tile (not the 5 placeholder classes from the
  original stub), returned as an `answer`, `confidence`, a `classes`
  percentage breakdown, and a rendered land-cover map evidence image.
- **Install with `pip<24.1`.** This pipeline depends on `configilm`, which
  pulls in `lightning-bolts`. That package has a malformed version
  constraint that fails pip's strict metadata validation starting in
  pip 24.1. Run `pip install "pip<24.1"` before `pip install -r
  requirements.txt` to avoid the failure. If you already ran the install
  and saw a metadata error mentioning `lightning-bolts` or `torchvision
  (>=0.10.*)`, this is why -- downgrade pip and re-run.

## Team Tasks and Next Steps

The project currently uses stub implementations in `backend/app/models/` as placeholders. The next phase is to replace these stubs with production-ready model logic and complete the user-facing interface.

Before making changes, review the team workflow in [CONTRIBUTING.md](CONTRIBUTING.md).

### M1 and M2: Web Platform

- **M1 (Backend):** Own `backend/app/api/routes.py`, add robust validation and error handling, and prepare deployment-ready storage patterns.
- **M2 (Frontend):** Replace the demo UI with a polished dashboard experience based on the current API contract and workflow documentation.

### M4: ML Pipelines

- `grounding.py`: implement Grounding DINO and SAM-based region extraction.
- `change_detection.py`: integrate change detection and measure changed areas.
- ~~`optical_sar.py`: implement the cross-modal fusion pipeline.~~ **Done** --
  real BIFOLD BigEarthNet v2.0 ResNet-18 model, see the Runtime Notes
  section above.
- `change_vqa.py`: build targeted prompting for change-focused reasoning.

### M5 and M6: Data, Deployment, and Presentation

- **M5 (Data):** centralize model weights and prepare fine-tuning data and adapter workflows.
- **M6 (Presentation):** build the final demo narrative around the routing layer and explainable execution trace.
