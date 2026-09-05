"""
Standalone Model Host FastAPI app.

Started when SATQUERY_ROLE=model_host (or device.json role is model_host).
Exposes /node/* only — no frontend, no analyze pipeline.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.node.config_store import load_device_config, local_ip
from app.node.host_routes import router as host_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = load_device_config()
    if cfg:
        logger.info(
            f"SatQuery Model Host node_id={cfg.node_id} "
            f"lan={local_ip()}:{cfg.node_port} pairing_code={cfg.pairing_code}"
        )
    else:
        logger.warning("No .satquery/device.json — configure role before hosting")
    yield


app = FastAPI(
    title="SatQuery Model Host",
    description="LAN model node — Ollama-backed VQA/captioning",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(host_router)


@app.get("/")
def root():
    cfg = load_device_config()
    return {
        "service": "satquery-model-host",
        "node_id": cfg.node_id if cfg else None,
        "role": cfg.role if cfg else None,
        "docs": "/docs",
    }
