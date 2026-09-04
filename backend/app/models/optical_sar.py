"""
Optical-SAR Fusion Model — Cross-modal land cover classification.

Owner: M4 (ML Pipelines Lead)
Status: REAL MODEL — BIFOLD BigEarthNet v2.0 ResNet-18-all-v0.2.0
(pretrained on BigEarthNet v2.0 S1+S2 fusion, MIT licensed:
https://huggingface.co/BIFOLD-BigEarthNetv2-0/resnet18-all-v0.2.0)

Verified against the actual installed configilm / reben_publication source
(not just their docs) for band order, per-band normalization stats, and
output label ordering — see backend/README or PR description for details.

Deviations from the original stub worth knowing about:

  - CLASS_NAMES/CLASS_COLORS are the real 19-class BigEarthNet v2.0 / CORINE
    label set (configilm.extra.BENv2_utils.NEW_LABELS), not the 5 placeholder
    classes the stub used — those were never meant to survive a real model.

  - This model classifies whole 120x120px (1200m) tiles, not individual
    pixels. To keep the documented 2-image API (images[0]=optical,
    images[1]=SAR) while still producing a real spatial land-cover map
    (not one flat color), this wrapper expects images[0]/images[1] to be
    pre-stacked, co-registered, same-resolution multi-band GeoTIFFs
    (optical: 10 bands B02..B12 in ESA order, 20m bands already
    nearest-upsampled to the 10m grid; SAR: 2 bands VV,VH, gamma0 dB) —
    then tiles that raster into 120x120 blocks and classifies each one.
    A separate data-prep script (not included in this PR) builds these
    stacked GeoTIFFs from raw Sentinel-1/2 downloads -- ask M4 if you need it.
"""

from pathlib import Path

import numpy as np
import rasterio
import torch
import torchvision.transforms as T

from configilm.extra.BENv2_utils import (
    NEW_LABELS,
    STANDARD_BANDS,
    band_combi_to_mean_std,
)
from reben_publication.BigEarthNetv2_0_ImageClassifier import BigEarthNetv2_0_ImageClassifier
from loguru import logger

from app.models.base import BaseModelWrapper
from app.output.evidence import generate_land_cover_map

TILE_PX = 120  # one BigEarthNet-style patch = 120x120 px @ ~10m/px = 1200m
THRESHOLD = 0.5

# Band order actually fed to the model (SAR first, then S2 10m/20m bands) --
# configilm's own verified order, not re-derived here.
BAND_ORDER = STANDARD_BANDS[12]  # ["VV","VH","B02",...,"B8A","B11","B12"]

# Order the *input files* are expected in.
OPTICAL_BAND_ORDER = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]
SAR_BAND_ORDER = ["VV", "VH"]

# Real 19-class BigEarthNet v2.0 / CORINE labels with CORINE-inspired colors
# (urban=red, agriculture=yellow/olive, forest=green, wetlands=teal, water=blue),
# keyed by name so index alignment with NEW_LABELS doesn't depend on
# remembering its sort order by hand.
_CLASS_COLORS_BY_NAME = {
    "Urban fabric": (230, 25, 75),
    "Industrial or commercial units": (170, 10, 10),
    "Arable land": (255, 225, 25),
    "Permanent crops": (245, 130, 48),
    "Pastures": (210, 245, 60),
    "Complex cultivation patterns": (128, 128, 0),
    "Land principally occupied by agriculture, with significant areas of natural vegetation": (170, 170, 50),
    "Agro-forestry areas": (100, 140, 40),
    "Broad-leaved forest": (60, 180, 75),
    "Coniferous forest": (0, 100, 0),
    "Mixed forest": (0, 146, 63),
    "Natural grassland and sparsely vegetated areas": (200, 255, 150),
    "Moors, heathland and sclerophyllous vegetation": (145, 110, 80),
    "Transitional woodland, shrub": (188, 200, 80),
    "Beaches, dunes, sands": (255, 215, 150),
    "Inland wetlands": (70, 180, 180),
    "Coastal wetlands": (140, 210, 210),
    "Inland waters": (0, 0, 255),
    "Marine waters": (0, 0, 140),
}


class OpticalSARFusionModel(BaseModelWrapper):
    """
    Real optical-SAR fusion network: BIFOLD BigEarthNet v2.0 ResNet-18-all-v0.2.0.

    Generates a spatial land cover classification from a co-registered
    optical + SAR multi-band GeoTIFF pair.
    """

    CLASS_NAMES = list(NEW_LABELS)  # model output index order
    CLASS_COLORS = [_CLASS_COLORS_BY_NAME[name] for name in CLASS_NAMES]

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading OpticalSARFusionModel (ResNet-18-all-v0.2.0) on {self.device}...")
        self.model = BigEarthNetv2_0_ImageClassifier.from_pretrained(
            "BIFOLD-BigEarthNetv2-0/resnet18-all-v0.2.0"
        ).to(self.device)
        self.model.eval()

        mean, std = band_combi_to_mean_std(12, interpolation="120_nearest")
        self.normalize = T.Normalize(mean=mean.tolist(), std=std.tolist())
        logger.info("OpticalSARFusionModel loaded")

    def run(self, action: str, context: dict) -> dict:
        if action != "fuse_modalities":
            raise ValueError(f"Unknown action for OpticalSARFusionModel: '{action}'")

        optical_path = context["images"][0]
        sar_path = context["images"][1] if len(context["images"]) > 1 else context["images"][0]
        request_id = context.get("request_id", "demo")

        class_map, tile_predictions, class_percentages, mean_confidence = self._fuse_and_classify(
            optical_path, sar_path
        )

        map_url = generate_land_cover_map(
            class_map, self.CLASS_NAMES, self.CLASS_COLORS, request_id
        )

        top_class = max(class_percentages, key=class_percentages.get) if class_percentages else "unknown"
        summary = ", ".join(f"{name} ({pct}%)" for name, pct in
                             sorted(class_percentages.items(), key=lambda kv: -kv[1]))

        return {
            "type": "fusion_result",
            "classes": class_percentages,
            "tile_grid_shape": list(class_map.shape),
            "tile_predictions": tile_predictions,
            "answer": f"Optical-SAR fusion classified the area as predominantly {top_class}. "
                      f"Tile breakdown: {summary}.",
            "confidence": round(mean_confidence, 3),
            "evidence_images": [
                {
                    "type": "land_cover_map",
                    "url": map_url,
                    "caption": "Land cover classification from optical+SAR fusion "
                               f"({class_map.shape[1]}x{class_map.shape[0]} tiles of ~1.2km each)",
                }
            ],
        }

    def _fuse_and_classify(self, optical_path, sar_path):
        with rasterio.open(optical_path) as src:
            optical = src.read().astype(np.float32)  # (10, H, W)
        with rasterio.open(sar_path) as src:
            sar = src.read().astype(np.float32)  # (2, H, W)

        h, w = optical.shape[1], optical.shape[2]
        if sar.shape[1:] != (h, w):
            raise ValueError(
                f"optical ({h}x{w}) and SAR ({sar.shape[1]}x{sar.shape[2]}) rasters "
                "must be the same size -- co-register/resample them before calling this model."
            )
        if h % TILE_PX or w % TILE_PX:
            raise ValueError(
                f"Raster size {h}x{w} is not a multiple of {TILE_PX}px -- "
                "crop or pad to a multiple of one BigEarthNet tile (120px) first."
            )

        band_arrays = {}
        for i, name in enumerate(OPTICAL_BAND_ORDER):
            band_arrays[name] = optical[i]
        for i, name in enumerate(SAR_BAND_ORDER):
            band_arrays[name] = sar[i]

        rows, cols = h // TILE_PX, w // TILE_PX
        class_map = np.zeros((rows, cols), dtype=np.int64)
        tile_predictions = {}
        class_tile_counts = {name: 0 for name in self.CLASS_NAMES}
        top_probs = []

        for r in range(rows):
            for c in range(cols):
                y0, y1 = r * TILE_PX, (r + 1) * TILE_PX
                x0, x1 = c * TILE_PX, (c + 1) * TILE_PX

                tile = torch.stack(
                    [torch.from_numpy(band_arrays[name][y0:y1, x0:x1]) for name in BAND_ORDER]
                ).float()
                tile = self.normalize(tile)
                x = tile.unsqueeze(0).to(self.device)

                with torch.no_grad():
                    probs = torch.sigmoid(self.model(x)).cpu().squeeze(0)

                probs_by_class = {
                    self.CLASS_NAMES[i]: round(probs[i].item(), 3) for i in range(len(self.CLASS_NAMES))
                }
                top_idx = int(torch.argmax(probs).item())
                class_map[r, c] = top_idx
                class_tile_counts[self.CLASS_NAMES[top_idx]] += 1
                top_probs.append(probs[top_idx].item())
                tile_predictions[f"tile_{r}_{c}"] = {
                    "top_class": self.CLASS_NAMES[top_idx],
                    "top_prob": round(probs[top_idx].item(), 3),
                    "all_probs_above_threshold": {
                        name: p for name, p in probs_by_class.items() if p > THRESHOLD
                    },
                }

        total_tiles = rows * cols
        class_percentages = {
            name: round(count / total_tiles * 100, 1)
            for name, count in class_tile_counts.items()
            if count > 0
        }
        mean_confidence = sum(top_probs) / len(top_probs) if top_probs else 0.0
        return class_map, tile_predictions, class_percentages, mean_confidence
