"""Lightweight hardware / capability probe. Unknown stays unknown."""

from __future__ import annotations

from typing import Any, Optional


def probe_hardware() -> dict[str, Any]:
    info: dict[str, Any] = {
        "os": None,
        "cpu_count": None,
        "ram_gb": None,
        "gpu_available": False,
        "gpu_name": None,
        "vram_gb": None,
        "qwen_vl_support": "unknown",
    }
    try:
        import platform
        import os

        info["os"] = f"{platform.system()} {platform.release()}"
        info["cpu_count"] = os.cpu_count()
    except Exception:
        pass

    try:
        import psutil  # optional

        info["ram_gb"] = round(psutil.virtual_memory().total / (1024**3), 1)
    except Exception:
        pass

    try:
        import torch

        if torch.cuda.is_available():
            info["gpu_available"] = True
            info["gpu_name"] = torch.cuda.get_device_name(0)
            free_b, total_b = torch.cuda.mem_get_info(0)
            info["vram_gb"] = round(total_b / (1024**3), 1)
            # Soft guidance only — never block manual enable
            if info["vram_gb"] is not None and info["vram_gb"] >= 6:
                info["qwen_vl_support"] = "supported"
            elif info["vram_gb"] is not None:
                info["qwen_vl_support"] = "unsupported"
        else:
            info["qwen_vl_support"] = "unsupported"
    except Exception:
        info["qwen_vl_support"] = "unknown"

    return info
