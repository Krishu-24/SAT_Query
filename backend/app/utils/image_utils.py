"""
Image utility functions — loading, resizing, preprocessing.
"""

from pathlib import Path
from PIL import Image
from loguru import logger


def load_image(path: str, max_size: int = 1024) -> Image.Image:
    """
    Load and optionally resize an image.

    Args:
        path: Path to image file.
        max_size: Maximum dimension (width or height). Resize if larger.

    Returns:
        PIL Image in RGB mode.
    """
    img = Image.open(path)

    # Convert to RGB if needed
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Resize if too large
    w, h = img.size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        logger.debug(f"Resized {Path(path).name}: {w}x{h} → {new_w}x{new_h}")

    return img


def get_image_info(path: str) -> dict:
    """Get basic image metadata."""
    try:
        img = Image.open(path)
        return {
            "filename": Path(path).name,
            "size": list(img.size),
            "bands": len(img.getbands()),
            "mode": img.mode,
            "format": img.format or Path(path).suffix,
        }
    except Exception as e:
        return {"filename": Path(path).name, "error": str(e)}
