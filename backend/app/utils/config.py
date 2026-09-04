"""
Application settings and configuration.
"""

import os
import tempfile
from pathlib import Path


def _default_shiven_root() -> Path:
    # backend/app/utils/config.py -> parents[3] == repo root
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "router"


def _default_temp_dir() -> str:
    # Prefer a writable OS temp dir (Windows-safe) over hardcoded /tmp.
    return os.environ.get("TEMP_DIR") or str(Path(tempfile.gettempdir()) / "satquery")


class Settings:
    """Central configuration for SatQuery AI backend."""

    # ── Paths ──
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent  # backend/
    RESULTS_DIR: Path = BASE_DIR / "results"
    MODELS_DIR: Path = BASE_DIR / "models"

    # Shiven QueryPlanner package root (contains the `app` package).
    SHIVEN_ROUTER_ROOT: str = os.environ.get(
        "SHIVEN_ROUTER_ROOT",
        str(_default_shiven_root()),
    )

    # ── Qwen2.5-VL (specialist inference — separate from Ollama planner) ──
    QWEN_MODEL_PATH: str = os.environ.get(
        "QWEN_MODEL_PATH",
        str(MODELS_DIR / "vqa" / "qwen25vl"),
    )

    # ── Shiven LLM planner (Ollama / Qwen3 4B) ──
    OLLAMA_BASE_URL: str = os.environ.get(
        "OLLAMA_BASE_URL", "http://localhost:11434"
    )
    OLLAMA_PLANNER_MODEL: str = os.environ.get(
        "OLLAMA_PLANNER_MODEL", "qwen3:4b-instruct"
    )
    # Use Shiven QueryPlanner instead of in-repo RuleBasedRouter.
    USE_SHIVEN_ROUTER: bool = os.environ.get(
        "USE_SHIVEN_ROUTER", "true"
    ).lower() in ("1", "true", "yes")
    # When True, do not load stub/real specialist weights — emit honest
    # "Model not available" / "Model not loaded" steps for Debug Mode.
    SKIP_MODEL_INFERENCE: bool = os.environ.get(
        "SKIP_MODEL_INFERENCE", "true"
    ).lower() in ("1", "true", "yes")

    # ── Server ──
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "8000"))
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5500",   # VS Code Live Server
        "null",                      # file:// protocol
    ]

    # ── GPU ──
    MAX_VRAM_GB: float = float(os.environ.get("MAX_VRAM_GB", "8.0"))

    # ── Uploads ──
    MAX_UPLOAD_SIZE_MB: int = 50
    TEMP_DIR: str = _default_temp_dir()

    # ── Debug ──
    # Default for the execution trace's per-step payload snapshots when a
    # request doesn't pass ?debug explicitly. Snapshotting costs real CPU on
    # large model outputs, so it stays off unless asked for; every other
    # telemetry field in the trace is always on.
    DEBUG_TRACE: bool = os.environ.get("SATQUERY_DEBUG", "").lower() in (
        "1", "true", "yes",
    )


settings = Settings()

# Ensure dirs exist
settings.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
Path(settings.TEMP_DIR).mkdir(parents=True, exist_ok=True)
