# 🧩 Model Stubs & Next Steps (Team Handoff)

This document is specifically for the other members of the SatQuery AI team (M1, M2, M4, M5, M6). Member 3 (Agent/Router Lead) has completed the core backend architecture, routing, and VLM integration. 

To ensure the system works end-to-end without crashing, M3 created **stubs** (dummy placeholders) for the models and endpoints that other members need to build. 

**This document outlines exactly which files you need to modify to replace the stubs with real implementations.**

---

## 🚀 M4: ML Pipelines Lead

Your task is to take the STUB model classes and implement the real model inference logic. All of these files are located in `backend/app/models/`.

Currently, these files simply return `"Model output not available"` so the frontend doesn't break. You will need to load your models in the `__init__` (or lazy load them) and perform the actual image inference in the `run()` method.

### 1. Grounding & Segmentation (`grounding.py`)
- **File:** `backend/app/models/grounding.py`
- **What to do:**
  - `GroundingModel`: Replace the stub with actual **Grounding DINO** inference. Extract the `target` from the query, run the model on `context["images"][0]`, and return real bounding boxes and confidence scores.
  - `SegmentationModel`: Replace the stub with actual **SAM 2.1 Hiera-Tiny** inference. Take the bounding boxes passed from `context["intermediate"]["step_1"]` and return the segmentation masks and the `evidence.py` overlay image.

### 2. Change Detection (`change_detection.py`)
- **File:** `backend/app/models/change_detection.py`
- **What to do:** Replace the stub with actual **TinyCD** inference. It will receive two images (bi-temporal). You need to run them through TinyCD, calculate the percentage of changed pixels, and use the `colorize_change_map` helper from `evidence.py` to generate the visual evidence.

### 3. Change VQA (`change_vqa.py`)
- **File:** `backend/app/models/change_vqa.py`
- **What to do:** This requires feeding 2 images + the change map (from TinyCD) into the VLM (Qwen2.5-VL) to answer specific questions about the change. Right now, it returns a stubbed string. You'll need to write the prompt engineering for Qwen to ingest the change map.

### 4. Optical-SAR Fusion (`optical_sar.py`)
- **File:** `backend/app/models/optical_sar.py`
- **What to do:** Replace the stub with the **EfficientNet-B0 dual encoder** model for cross-modal fusion. It will receive one optical and one SAR image. Return the land cover classification distribution.

---

## 🌐 M1 & M2: Frontend & Backend Leads

### 1. API Endpoints (M1)
- **File:** `backend/app/api/routes.py`
- **What's done:** The `/api/analyze` and `/api/health` endpoints are fully wired up to M3's agent routing pipeline. They correctly handle file uploads, validation, routing, and returning the structured JSON.
- **What to do:** Add production-ready error handling, rate limiting, logging (via ELK/Prometheus), and possibly migrate the temp file storage to a more robust cloud bucket (S3) if required.

### 2. Frontend UI (M2)
- **File:** `frontend/index.html`
- **What's done:** A fully functional, but basic (dummy) single-page HTML app. It successfully handles drag-and-drop uploads for up to 2 images (including `.geotiff`), sends the `FormData` to the backend, and renders the Answer, Confidence Bar, Evidence Images, and Execution Trace.
- **What to do:** This is just a POC frontend! You need to rebuild this into a proper **Next.js** or **React** dashboard using the design system (glassmorphism, animations, etc.). You can use `index.html` as the API reference for how to structure your fetch requests and parse the `execution_trace`.

---

## 🗄️ M5 & M6: Datasets & Presentation

### 1. Checkpoint Management (M5)
- Ensure all weights for Qwen, GDINO, SAM, and TinyCD are uploaded to the shared team drive.
- Create a script (or add to `requirements.txt`/`setup.py`) to automate downloading these models into the `backend/models/` directory so M4's pipelines can load them smoothly.

### 2. Demo & Slides (M6)
- Review the M3 walkthrough and the `index.html` UI to start taking screenshots of the routing logic in action.
- The "Execution Trace" feature (built by M3) is a huge selling point for our SIH presentation, as it provides "explainable AI". Make sure to highlight this!
