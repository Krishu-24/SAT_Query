# 04 — Backend Plan (POC)

> FastAPI backend — what to build, in what order, with code patterns.

---

## Owner: M1 (Backend Lead)

**Helpers:** M3 (schemas/contracts), M4 (model interface)

---

## Dependencies

```txt
# requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-multipart==0.0.12
pydantic==2.9.0
torch==2.4.0
torchvision==0.19.0
transformers==4.45.0
accelerate==0.34.0
Pillow==10.4.0
rasterio==1.4.0
opencv-python-headless==4.10.0
numpy==1.26.0
loguru==0.7.0
```

---

## Build Order (follow this exactly)

### Step 1: Scaffold (Day 1 Morning, 1 hour)

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from loguru import logger
from app.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SatQuery AI...")
    # Model registry init will go here
    yield
    logger.info("Shutting down...")

app = FastAPI(title="SatQuery AI", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/results", StaticFiles(directory="results"), name="results")
app.include_router(router, prefix="/api")
```

### Step 2: Schemas (Day 1 Morning, 30 min)

M1 + M3 agree on these schemas first thing:

```python
# app/api/schemas.py
from pydantic import BaseModel, Field
from typing import Optional

class EvidenceImage(BaseModel):
    type: str
    url: str
    caption: str

class BoundingRegion(BaseModel):
    bbox: list[float]
    label: str
    confidence: float

class Evidence(BaseModel):
    images: list[EvidenceImage] = []
    regions: list[BoundingRegion] = []

class PipelineStep(BaseModel):
    step: int
    model: str
    action: str
    status: str
    time_ms: float
    error: Optional[str] = None

class ValidationInfo(BaseModel):
    image_count: int
    format: list[str]
    modality: list[str]
    temporal: bool
    cross_modal: bool
    compatible: bool
    warnings: list[str] = []

class ExecutionTrace(BaseModel):
    input_validation: ValidationInfo
    detected_task: str
    task_confidence: float
    reasoning: str
    selected_models: list[dict]
    pipeline_steps: list[PipelineStep]
    total_time_ms: float

class AnalysisResponse(BaseModel):
    answer: str
    confidence: float
    evidence: Evidence
    execution_trace: ExecutionTrace

class HealthResponse(BaseModel):
    status: str
    models_loaded: list[str]
    gpu_available: bool
    gpu_memory_used: Optional[str] = None
```

### Step 3: Routes (Day 1 Afternoon)

```python
# app/api/routes.py
import uuid, tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException
from typing import Optional
from loguru import logger

router = APIRouter()

@router.post("/analyze")
async def analyze(
    request: Request,
    images: list[UploadFile] = File(...),
    query: str = Form(...),
    modalities: str = Form(default="optical"),
    dates: Optional[str] = Form(default=None),
):
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Query: '{query}' | Images: {len(images)}")

    # 1. Save uploaded images to temp
    image_paths = []
    for i, img in enumerate(images):
        suffix = Path(img.filename).suffix or ".tif"
        tmp = Path(tempfile.mkdtemp()) / f"image_{i}{suffix}"
        tmp.write_bytes(await img.read())
        image_paths.append(str(tmp))

    # 2. Parse metadata
    modality_list = [m.strip() for m in modalities.split(",")]
    metadata = {"modalities": modality_list}

    # 3. Validate → Route → Execute → Integrate
    # (Wire these in Day 1 Evening)
    from app.agent.validator import InputValidator
    from app.agent.router import RuleBasedRouter
    from app.agent.executor import PipelineExecutor
    from app.output.integrator import OutputIntegrator
    from app.output.trace import TraceBuilder

    validator = InputValidator()
    validation = validator.validate(image_paths, metadata)
    if not validation.is_valid:
        raise HTTPException(422, detail={"errors": validation.errors})

    input_info = {
        "num_images": validation.num_images,
        "modalities": validation.modalities,
        "is_temporal": validation.is_temporal,
        "is_cross_modal": validation.is_cross_modal,
    }
    router_inst = RuleBasedRouter()
    decision = router_inst.route(query, input_info)

    registry = request.app.state.model_registry
    executor = PipelineExecutor(registry)
    step_results = executor.execute(decision.pipeline, image_paths, query)

    trace = TraceBuilder().build(validation, decision, step_results)
    output = OutputIntegrator().integrate(step_results, decision.task_type, query, request_id)

    return {
        "answer": output["answer"],
        "confidence": output["confidence"],
        "evidence": output["evidence"],
        "execution_trace": trace,
    }

@router.get("/health")
async def health(request: Request):
    import torch
    registry = request.app.state.model_registry
    gpu_mem = None
    if torch.cuda.is_available():
        used = torch.cuda.memory_allocated() / 1e9
        total = torch.cuda.get_device_properties(0).total_mem / 1e9
        gpu_mem = f"{used:.1f} / {total:.1f} GB"
    return {
        "status": "healthy",
        "models_loaded": registry.list_loaded(),
        "gpu_available": torch.cuda.is_available(),
        "gpu_memory_used": gpu_mem,
    }
```

### Step 4: Model Registry (Day 1 Afternoon — with M4)

```python
# app/models/registry.py
import gc, torch
from loguru import logger

class ModelRegistry:
    def __init__(self):
        self._models = {}
        self._configs = {}  # M4 populates this

    def register(self, name, loader_fn, vram_gb):
        self._configs[name] = {"loader": loader_fn, "vram_gb": vram_gb}

    def get(self, name):
        if name not in self._models:
            self._load(name)
        return self._models[name]

    def _load(self, name):
        if name not in self._configs:
            raise ValueError(f"Unknown model: {name}")
        config = self._configs[name]
        self._ensure_vram(config["vram_gb"])
        logger.info(f"Loading {name} (~{config['vram_gb']} GB)")
        self._models[name] = config["loader"]()

    def _ensure_vram(self, needed_gb):
        if not torch.cuda.is_available():
            return
        free = (torch.cuda.get_device_properties(0).total_mem - torch.cuda.memory_allocated()) / 1e9
        while free < needed_gb and self._models:
            oldest = next(iter(self._models))
            self.unload(oldest)
            free = (torch.cuda.get_device_properties(0).total_mem - torch.cuda.memory_allocated()) / 1e9

    def unload(self, name):
        if name in self._models:
            del self._models[name]
            gc.collect()
            torch.cuda.empty_cache()
            logger.info(f"Unloaded {name}")

    def unload_all(self):
        for name in list(self._models):
            self.unload(name)

    def list_loaded(self):
        return list(self._models.keys())

    def list_all(self):
        return [{"name": n, "loaded": n in self._models, "vram_gb": c["vram_gb"]} for n, c in self._configs.items()]
```

### Step 5: Pipeline Executor (Day 1 Evening — with M3)

```python
# app/agent/executor.py
import time
from dataclasses import dataclass
from typing import Any
from loguru import logger

@dataclass
class StepResult:
    step_num: int
    model_name: str
    action: str
    output: Any
    time_ms: float
    success: bool
    error: str = None

class PipelineExecutor:
    def __init__(self, registry):
        self.registry = registry

    def execute(self, pipeline, image_paths, query):
        results = []
        context = {"images": image_paths, "query": query, "intermediate": {}}

        for step in pipeline:
            start = time.time()
            try:
                model = self.registry.get(step["model"])
                output = model.run(action=step["action"], context=context)
                elapsed = (time.time() - start) * 1000
                context["intermediate"][f"step_{step['step']}"] = output
                results.append(StepResult(step["step"], step["model"], step["action"], output, elapsed, True))
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                logger.error(f"Pipeline step {step['step']} failed: {e}")
                results.append(StepResult(step["step"], step["model"], step["action"], None, elapsed, False, str(e)))
                break
        return results
```

---

## Running

```bash
# From backend/
pip install -r requirements.txt
mkdir -p results
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## POC Simplifications

| Full Version | POC Version |
|-------------|-------------|
| Celery + Redis for async | Synchronous in request handler |
| Docker deployment | `uvicorn --reload` |
| Full GeoTIFF validation | Basic format + size check |
| Geographic overlap check | Skip for demo (assume co-registered) |
| Report generation | Raw JSON response |
| Multiple users | Single user demo |
