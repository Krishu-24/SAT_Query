"""
Geospatial helpers for input validation.

Only trusted GeoTIFF tags are used for correspondence checks.
Synthetic / filename-derived locations are never treated as evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image

from app.output.raster_stub import _geotiff_bbox


# Documented thresholds (WGS84 axis-aligned bbox IoU / coverage).
# Correspondence: intersection / min(area_a, area_b) >= FULL_COVERAGE
# Partial: 0 < coverage < FULL_COVERAGE
# None: coverage == 0
FULL_COVERAGE = 0.25
PARTIAL_COVERAGE = 1e-12


def inspect_georef(image_path: str) -> dict:
    """Return trusted georef facts or explicit unknowns.

    Never invents CRS/bbox. PNG/JPEG and untagged TIFF → location unknown.
    """
    info = {
        "location_known": False,
        "bbox": None,
        "crs": None,
        "source": "unknown",
    }
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            if img.format != "TIFF":
                return info
            real = _geotiff_bbox(img, width, height)
            if not real or real.get("source") != "geotiff-tags":
                return info
            info["location_known"] = True
            info["bbox"] = real["bbox"]
            info["source"] = "geotiff-tags"
            info["crs"] = "EPSG:4326"  # after reprojection when needed
            return info
    except Exception:
        return info


def _bbox_area(b: dict) -> float:
    return max(0.0, (b["east"] - b["west"])) * max(0.0, (b["north"] - b["south"]))


def _intersection(a: dict, b: dict) -> Optional[dict]:
    west = max(a["west"], b["west"])
    east = min(a["east"], b["east"])
    south = max(a["south"], b["south"])
    north = min(a["north"], b["north"])
    if east <= west or north <= south:
        return None
    return {"west": west, "east": east, "south": south, "north": north}


def compare_footprints(bbox_a: Optional[dict], bbox_b: Optional[dict]) -> dict:
    """Compare two WGS84 bboxes.

    Returns correspondence in {same, partial, none, unknown}.
    """
    if not bbox_a or not bbox_b:
        return {
            "correspondence": "unknown",
            "coverage": None,
            "iou": None,
            "reason": "One or both images lack trusted geospatial bounds.",
        }

    inter = _intersection(bbox_a, bbox_b)
    area_a = _bbox_area(bbox_a)
    area_b = _bbox_area(bbox_b)
    if area_a <= 0 or area_b <= 0:
        return {
            "correspondence": "unknown",
            "coverage": None,
            "iou": None,
            "reason": "Degenerate bounding box.",
        }

    if inter is None:
        return {
            "correspondence": "none",
            "coverage": 0.0,
            "iou": 0.0,
            "reason": "No geographic overlap between trusted footprints.",
        }

    inter_area = _bbox_area(inter)
    coverage = inter_area / min(area_a, area_b)
    union = area_a + area_b - inter_area
    iou = inter_area / union if union > 0 else 0.0

    if coverage >= FULL_COVERAGE:
        correspondence = "same"
        reason = (
            f"Trusted footprints overlap strongly "
            f"(coverage={coverage:.3f}, threshold={FULL_COVERAGE})."
        )
    elif coverage > PARTIAL_COVERAGE:
        correspondence = "partial"
        reason = (
            f"Trusted footprints overlap only partially "
            f"(coverage={coverage:.3f}, full threshold={FULL_COVERAGE})."
        )
    else:
        correspondence = "none"
        reason = "No meaningful geographic overlap."

    return {
        "correspondence": correspondence,
        "coverage": round(coverage, 6),
        "iou": round(iou, 6),
        "reason": reason,
    }


def content_fingerprint(path: str, max_bytes: int = 8 * 1024 * 1024) -> str:
    """SHA-256 of file bytes (capped) for duplicate detection — not filename."""
    import hashlib

    h = hashlib.sha256()
    p = Path(path)
    with p.open("rb") as fh:
        remaining = max_bytes
        while remaining > 0:
            chunk = fh.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            h.update(chunk)
            remaining -= len(chunk)
        # Include size so truncated large equals don't collide casually
        h.update(str(p.stat().st_size).encode())
    return h.hexdigest()
