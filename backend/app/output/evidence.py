"""
Evidence generation helpers — Overlay bounding boxes, colorize change maps, save to results/.

Owner: M3 (Agent/Router Lead)

Provides utility functions for generating visual evidence:
  - Bounding box overlays on satellite images
  - Change map colorization
  - Segmentation mask overlays
  - Legend generation
"""

import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from loguru import logger


RESULTS_DIR = Path("results")


def ensure_results_dir(request_id: str = "") -> Path:
    """Ensure the results directory exists and return path for request."""
    out_dir = RESULTS_DIR / request_id if request_id else RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def overlay_bboxes(
    image_path: str,
    boxes: list[list[float]],
    labels: list[str],
    scores: list[float],
    request_id: str = "demo",
    color: tuple = (0, 120, 255),
    line_width: int = 3,
) -> str:
    """
    Draw bounding boxes on an image and save as evidence.

    Args:
        image_path: Path to the original image.
        boxes: List of [x1, y1, x2, y2] bounding boxes.
        labels: List of label strings.
        scores: List of confidence scores.
        request_id: For file naming.
        color: RGB tuple for box color.
        line_width: Box border width.

    Returns:
        URL path to the saved evidence image.
    """
    try:
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        for box, label, score in zip(boxes, labels, scores):
            x1, y1, x2, y2 = [int(c) for c in box]

            # Draw bounding box
            draw.rectangle([x1, y1, x2, y2], outline=color, width=line_width)

            # Draw label background
            text = f"{label} ({score:.2f})"
            text_bbox = draw.textbbox((x1, y1), text)
            text_h = text_bbox[3] - text_bbox[1]
            text_w = text_bbox[2] - text_bbox[0]
            draw.rectangle(
                [x1, y1 - text_h - 6, x1 + text_w + 6, y1],
                fill=color,
            )
            draw.text((x1 + 3, y1 - text_h - 3), text, fill="white")

        out_dir = ensure_results_dir(request_id)
        out_path = out_dir / "grounding_overlay.png"
        img.save(str(out_path))

        return f"/results/{request_id}/grounding_overlay.png"

    except Exception as e:
        logger.error(f"Failed to generate bbox overlay: {e}")
        return ""


def colorize_change_map(
    change_mask: np.ndarray,
    request_id: str = "demo",
    change_color: tuple = (255, 60, 60),
    no_change_color: tuple = (200, 200, 200),
) -> str:
    """
    Convert a binary change mask to a colored PNG.

    Args:
        change_mask: 2D numpy array (1=changed, 0=unchanged).
        request_id: For file naming.
        change_color: RGB for changed pixels.
        no_change_color: RGB for unchanged pixels.

    Returns:
        URL path to the saved change map image.
    """
    try:
        h, w = change_mask.shape[:2]
        colored = np.zeros((h, w, 3), dtype=np.uint8)
        colored[change_mask > 0] = change_color
        colored[change_mask == 0] = no_change_color

        out_dir = ensure_results_dir(request_id)
        out_path = out_dir / "change_map.png"
        Image.fromarray(colored).save(str(out_path))

        return f"/results/{request_id}/change_map.png"

    except Exception as e:
        logger.error(f"Failed to generate change map: {e}")
        return ""


def overlay_segmentation_mask(
    image_path: str,
    mask: np.ndarray,
    request_id: str = "demo",
    color: tuple = (0, 120, 255),
    alpha: float = 0.4,
) -> str:
    """
    Overlay a segmentation mask on the original image.

    Args:
        image_path: Path to the original image.
        mask: 2D numpy array (1=foreground, 0=background).
        request_id: For file naming.
        color: RGB tuple for mask overlay color.
        alpha: Transparency (0=invisible, 1=opaque).

    Returns:
        URL path to the saved overlay image.
    """
    try:
        img = np.array(Image.open(image_path).convert("RGB"))

        overlay = img.copy()
        overlay[mask > 0] = color
        blended = (img * (1 - alpha) + overlay * alpha).astype(np.uint8)

        out_dir = ensure_results_dir(request_id)
        out_path = out_dir / "segmentation_overlay.png"
        Image.fromarray(blended).save(str(out_path))

        return f"/results/{request_id}/segmentation_overlay.png"

    except Exception as e:
        logger.error(f"Failed to generate segmentation overlay: {e}")
        return ""


def generate_land_cover_map(
    class_map: np.ndarray,
    class_names: list[str],
    class_colors: list[tuple],
    request_id: str = "demo",
) -> str:
    """
    Convert a class map to a colored land cover visualization.

    Args:
        class_map: 2D numpy array of class indices.
        class_names: List of class name strings.
        class_colors: List of RGB tuples per class.
        request_id: For file naming.

    Returns:
        URL path to the saved land cover map.
    """
    try:
        h, w = class_map.shape[:2]
        colored = np.zeros((h, w, 3), dtype=np.uint8)
        for i, color in enumerate(class_colors):
            colored[class_map == i] = color

        out_dir = ensure_results_dir(request_id)
        out_path = out_dir / "landcover_map.png"
        Image.fromarray(colored).save(str(out_path))

        return f"/results/{request_id}/landcover_map.png"

    except Exception as e:
        logger.error(f"Failed to generate land cover map: {e}")
        return ""
