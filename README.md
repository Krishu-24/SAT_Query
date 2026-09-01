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

## Team Tasks and Next Steps

The project currently uses stub implementations in `backend/app/models/` as placeholders. The next phase is to replace these stubs with production-ready model logic and complete the user-facing interface.

Before making changes, review the team workflow in [CONTRIBUTING.md](CONTRIBUTING.md).

### M1 and M2: Web Platform

- **M1 (Backend):** Own `backend/app/api/routes.py`, add robust validation and error handling, and prepare deployment-ready storage patterns.
- **M2 (Frontend):** Replace the demo UI with a polished dashboard experience based on the current API contract and workflow documentation.

### M4: ML Pipelines

- `grounding.py`: implement Grounding DINO and SAM-based region extraction.
- `change_detection.py`: integrate change detection and measure changed areas.
- `optical_sar.py`: implement the cross-modal fusion pipeline.
- `change_vqa.py`: build targeted prompting for change-focused reasoning.

### M5 and M6: Data, Deployment, and Presentation

- **M5 (Data):** centralize model weights and prepare fine-tuning data and adapter workflows.
- **M6 (Presentation):** build the final demo narrative around the routing layer and explainable execution trace.
