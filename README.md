# 🛰️ SatQuery AI — Backend (POC)

This repository contains the backend and agent logic for the SatQuery AI POC, built for SIH 2026 / ISRO-SAC.

> **Note:** This repository specifically focuses on **Member 3 (Agent/Router Lead)** deliverables and the **Qwen2.5-VL integration**. Other pipelines (TinyCD, Grounding DINO, etc.) are stubbed for end-to-end testing.

## ✨ Member 3 (Agent/Router) Progress

I have successfully completed all M3 deliverables for this POC:
- **Project Structure**: Set up the full FastAPI backend architecture.
- **Agent Logic**: Built the `RuleBasedRouter` (Zero-VRAM), `InputValidator`, and `PipelineExecutor`.
- **Output Engine**: Built the `TraceBuilder`, `OutputIntegrator`, and `evidence.py` overlay generators.
- **VLM Integration**: Wrote the `QwenVLMWrapper` and successfully connected it to the local pipeline.
- **UI & API**: Built the FastAPI routes and a functional `frontend/index.html` to prove end-to-end connectivity.
- **Team Enablement**: Created model stubs for all M4 pipelines so other members can test their code without crashes.

> **Team Members (M1, M2, M4, M5):** Please read [docs/STUBS_DOCUMENTATION.md](docs/STUBS_DOCUMENTATION.md) for exact instructions on where to inject your code, replace my stubs, and build the final UI!

## 🌟 Features

- **Agentic Routing:** Automatically routes user queries and images to the correct task pipeline (VQA, Grounding, Change Detection, Change VQA, Optical-SAR Fusion).
- **Zero-VRAM Rule-Based Router:** Uses deterministic keyword and input analysis to select pipelines without needing an LLM.
- **Input Validation:** Strict checking for image counts, formats, dimensions, and cross-modal/temporal properties.
- **Execution Trace:** Full transparency into how the agent analyzed the input, routed the request, and executed the models.
- **Qwen2.5-VL Integration:** Real integration with `Qwen2.5-VL-7B-Instruct-AWQ` for VQA, captioning, and change descriptions.
- **No Output Fallback:** If the Qwen model weights are not available or there is no GPU, the system gracefully falls back to a 'Model output not available' response, allowing you to still test the UI and agent routing.

## 📂 Project Structure

```
SAT_Query/
├── backend/
│   ├── app/
│   │   ├── agent/         # Router, Validator, Executor (M3 Core)
│   │   ├── api/           # Routes and Schemas
│   │   ├── models/        # Model registry, Qwen wrapper, and stubs
│   │   ├── output/        # Trace builder, integrator, evidence generators
│   │   └── utils/         # Config and image utils
│   ├── results/           # Generated evidence images (temp)
│   └── tests/             # Tests for router and validator
├── frontend/              # Minimal single-page HTML test app
└── data/demo/             # Demo images (add your own)
```

## 🚀 Setup & Installation

### 1. Backend Environment

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Download Qwen Model (Optional)

To run the real VLM, you need to download `Qwen2.5-VL-7B-Instruct-AWQ`.

```bash
pip install huggingface_hub
huggingface-cli download Qwen/Qwen2.5-VL-7B-Instruct-AWQ --local-dir backend/models/vqa/qwen25vl
```

If you don't do this, the backend will automatically run in **NO OUTPUT MODE** (it will just return 'Model output not available', but the routing logic will still execute).

### 3. Run the Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 4. Run the Test UI

Just open `frontend/index.html` in your browser, or serve it:

```bash
cd frontend
python -m http.server 3000
```

Then visit `http://localhost:3000`.

## 🧪 Testing

Run the automated tests for the router and validator:

```bash
cd backend
pytest tests/ -v
```

## 🔄 Agentic Flow (How it works)

1. **User uploads image(s) & types a query**
2. **`InputValidator`** checks format, counts, and identifies modalities/temporal status.
3. **`RuleBasedRouter`** looks at the inputs + query keywords to decide the `TaskType` and which models to use.
4. **`PipelineExecutor`** asks the `ModelRegistry` to load the needed models. (The registry unloads old models if VRAM is tight).
5. **Models run** in sequence, passing context between them.
6. **`OutputIntegrator`** collects the final answer, confidence, and generated evidence.
7. **`TraceBuilder`** packages the exact reasoning into an `ExecutionTrace`.
