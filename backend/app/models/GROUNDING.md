# Grounding Pipeline

**Owner:** M4 (ML Pipelines Lead)
**File:** [`grounding.py`](grounding.py)

Handles queries like *"highlight the water body"* or *"locate the airport"* —
find exactly where something is in a satellite image, not just whether it's
present.

## What it does

Two models run back-to-back, matching the `GROUNDING` route in
[`app/agent/router.py`](../agent/router.py)
(`pipeline: [detect_regions → segment_regions]`):

```text
"Highlight the water body"
        ↓
GroundingModel   — Grounding DINO: text phrase → bounding boxes + scores
        ↓
SegmentationModel — SAM 2.1: each box → a precise pixel mask
        ↓
Overlay image + region list + answer text
```

1. **`GroundingModel`** (`grounding_dino` slot) — extracts the target phrase
   from the query (`_extract_target`, e.g. `"highlight the water body"` →
   `"water body"`), then runs Grounding DINO as an open-vocabulary detector:
   the model isn't limited to a fixed class list, it matches whatever text
   phrase it's given directly against the image.
2. **`SegmentationModel`** (`sam` slot) — reads the boxes from step 1 out of
   `context["intermediate"]["step_1"]`, runs SAM 2.1 once per box to get a
   precise mask, merges the masks into one overlay image via
   [`app/output/evidence.py`](../output/evidence.py), and builds the final
   `answer` / `confidence` / `evidence_images` / `regions` response.

## Fallback behavior (no GPU / no weights)

Both wrappers follow the same pattern as
[`app/models/vqa.py`](vqa.py): on `__init__`, each tries to load its real
model, and if that fails (weights not downloaded, no `torch`, no GPU), it
flips into `_mock_mode` and returns empty/placeholder output instead of
crashing. This means the backend runs and the pipeline wires up correctly
on any machine, even before the real weights are in place — you'll just get
"no region found" / "Model output not available" until they are.

Two failure modes are handled differently on purpose:

- **Zero detections** (target genuinely not in the image, or `GroundingModel`
  is in mock mode) → a normal, non-error response:
  `"No region matching '<target>' was found in the image."`, confidence
  `0.0`.
- **SAM itself unavailable while boxes exist** → `"Model output not
  available"`, matching the VQA wrapper's wording for consistency across the
  app.

## Setup

```bash
# Grounding DINO Tiny (detection)
pip install transformers torch
huggingface-cli download IDEA-Research/grounding-dino-tiny \
  --local-dir backend/models/grounding/gdino

# SAM 2.1 Hiera-Tiny (segmentation) — pulled directly from the Hub at
# runtime via SAM2ImagePredictor.from_pretrained(), no manual download needed
pip install sam2
```

Paths/model IDs are configured in
[`app/utils/config.py`](../utils/config.py):

| Setting | Default | Override env var |
|---|---|---|
| `GDINO_MODEL_PATH` | `backend/models/grounding/gdino` | `GDINO_MODEL_PATH` |
| `SAM_MODEL_ID` | `facebook/sam2.1-hiera-tiny` | `SAM_MODEL_ID` |

## Still open

- Not yet validated against a real satellite image + downloaded weights —
  only the mock-mode fallback path has been tested so far.
- Detection/text thresholds (`BOX_THRESHOLD = 0.30`, `TEXT_THRESHOLD = 0.25`
  in `GroundingModel`) are reasonable Grounding DINO defaults, not tuned for
  remote-sensing imagery specifically.
