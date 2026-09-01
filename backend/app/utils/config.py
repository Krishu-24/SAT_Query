"""
Application settings and configuration.
"""

import os
from pathlib import Path


class Settings:
    """Central configuration for SatQuery AI backend."""

    # ── Paths ──
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent  # backend/
    RESULTS_DIR: Path = BASE_DIR / "results"
    MODELS_DIR: Path = BASE_DIR / "models"

    # ── Qwen2.5-VL ──
    QWEN_MODEL_PATH: str = os.environ.get(
        "QWEN_MODEL_PATH",
        str(MODELS_DIR / "vqa" / "qwen25vl"),
    )

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
    TEMP_DIR: str = os.environ.get("TEMP_DIR", "/tmp/satquery")


settings = Settings()

# Ensure dirs exist
settings.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
Path(settings.TEMP_DIR).mkdir(parents=True, exist_ok=True)
