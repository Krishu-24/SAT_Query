<div align="center">
  <h1>🛰️ SatQuery AI</h1>
  <p><strong>Agentic Remote Sensing Analysis System — SIH 2026 / ISRO-SAC</strong></p>
  <p>
    <a href="#-project-overview">Overview</a> •
    <a href="#-what-is-currently-working">Current Status</a> •
    <a href="#-quick-start-how-to-run">Quick Start</a> •
    <a href="#-team-tasks--next-steps">Team Tasks</a> •
    <a href="CONTRIBUTING.md">Git Workflow</a>
  </p>
</div>

---

## 🌍 Project Overview

SatQuery AI is a unified, agentic AI system for satellite imagery analysis. Instead of forcing users to navigate complex GIS software, users can upload satellite images (Optical or SAR) and simply type natural language queries like *"What changed?"* or *"Highlight the buildings"*. 

Our intelligent backend **automatically routes** the query to the correct machine learning pipeline (VQA, Grounding, Change Detection, or Optical-SAR Fusion), executes the models, and returns an evidence-backed answer.

---

## 🚀 What is Currently Working

**Member 3 (Agent & Router Lead)** has completed the core infrastructure and agentic routing layer. The repository currently features:

1. **🧠 Zero-VRAM Rule-Based Router**: Deterministically analyzes inputs and keywords to instantly classify queries into one of 6 task types without requiring a massive LLM.
2. **🏗️ Execution Pipeline**: A fully functional `PipelineExecutor` and `OutputIntegrator` that loads models, passes context between them, and generates an `ExecutionTrace` for explainable AI.
3. **🤖 Qwen2.5-VL Integration**: A fully integrated wrapper for `Qwen2.5-VL-7B-Instruct-AWQ` to handle standard VQA and captioning. 
4. **🔌 API & UI**: A working FastAPI backend (`/api/analyze`) and a sleek test UI (`frontend/index.html`) to demonstrate end-to-end connectivity.
5. **🛡️ Fallback Mode**: If you don't have a GPU or haven't downloaded the massive ML weights, the system gracefully falls back to returning `"Model output not available"`, preventing crashes and allowing frontend development to proceed unhindered.

---

## ⚡ Quick Start (How to Run)

To run the current codebase and test the routing logic and UI:

### 1. Setup the Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Download the VLM (Optional, ~5GB)
If you want to run real inference instead of seeing the "No Output" fallback, download the Qwen model:
```bash
pip install huggingface_hub
huggingface-cli download Qwen/Qwen2.5-VL-7B-Instruct-AWQ --local-dir backend/models/vqa/qwen25vl
```

### 3. Start the Server
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 4. Test the UI
Open a new terminal and serve the frontend:
```bash
cd frontend
python -m http.server 3000
```
Navigate to `http://localhost:3000` in your browser. Try uploading an image and asking different questions to watch the agent route your request!

---

## 🎯 Team Tasks & Next Steps

This repository uses **Stub Models** (`backend/app/models/`) as placeholders. The rest of the team must now replace these stubs with production code and build out the final UI. 

**Before writing code, please read our [🤝 Git Workflow & Contributing Guide](CONTRIBUTING.md) to learn how to branch, PR, and keep your code synced!**

### 👩‍💻 M1 & M2: Web Platform
- **M1 (Backend)**: Take ownership of `backend/app/api/routes.py`. Add production error handling, rate limiting, and migrate temp file storage to AWS S3 if required for deployment.
- **M2 (Frontend)**: The current `frontend/index.html` is just a dummy app to prove the API works. Rebuild this into a robust **React/Next.js** dashboard featuring glassmorphism, micro-animations, and a premium dark mode as specified in the original workflow docs. Use the current HTML file as your API reference.

### 🔬 M4: ML Pipelines (Replace the Stubs!)
Your task is to open the files in `backend/app/models/` and replace the stubs with real ML inference. Currently, they just return `"Model output not available"`.
- **`grounding.py`**: Implement real **Grounding DINO** (target extraction & bounding boxes) and **SAM 2.1** (segmentation masks).
- **`change_detection.py`**: Implement **TinyCD** to process bi-temporal images and return a change map and changed pixel percentage.
- **`optical_sar.py`**: Implement the **EfficientNet-B0** dual encoder for cross-modal fusion classification.
- **`change_vqa.py`**: Write the prompt engineering to feed 2 images + the TinyCD change map into Qwen2.5-VL to answer specific change questions.

### 💾 M5 & M6: Datasets, Deployment & Presentation
- **M5 (Data)**: Ensure all weights (Qwen, GDINO, SAM, TinyCD) are hosted centrally. Fine-tune the Qwen model using LoRA if time permits, and swap out the weights in `backend/models/`.
- **M6 (Presentation)**: Start building the SIH slides. Highlight our **Agentic Router** and **Execution Trace (Explainable AI)**, as these are major competitive advantages over standard ML dashboards. 
