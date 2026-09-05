# SatQuery AI — Validator Hard-Debug Specification

> **Implementation status:** Hardened validator is in `backend/app/agent/validator.py` (+ `query_requirements.py`, `geo_checks.py`) with tests in `tests/test_validator_hard_debug.py`. Statuses and 422 `detail.errors[]` match Workstream A in `UPDATE_LOG.md`. This file remains the case matrix / intent; code may use slightly different messaging.

## Purpose

This document defines the validation/red-team cases for the existing SatQuery AI query router.

**Scope:** validate the existing query → decomposition → input validation → routing flow.

**Do not:** replace the deterministic router with an LLM, load models, redesign the frontend, rewrite model pipelines, or make unrelated architectural changes.

---

## 1. Validation states

The validator should distinguish, using existing project conventions where possible:

- `VALID`
- `WARNING`
- `INVALID`
- `NEEDS_CLARIFICATION`
- `UNSUPPORTED`

Never silently convert invalid input into another task.

---

## 2. File/input validation

Check, where technically possible:

- file exists and is readable
- supported extension/content
- non-empty and non-corrupt raster
- valid dimensions/bands
- GeoTIFF metadata when available
- CRS/geotransform/bounds when available
- acquisition date when available
- modality when available
- NoData/NaN/invalid-pixel coverage
- unreasonable file dimensions/size
- duplicate files

Test:
- valid `.tif` / `.tiff`
- single-band raster
- multiband/multispectral raster
- optical raster
- SAR raster
- JPEG/PNG photograph
- corrupted/empty/renamed-invalid TIFF
- fully or heavily NoData raster

Do not assume every TIFF is multispectral or every multiband TIFF is optical.

---

## 3. Query → input sufficiency

The decomposed request should preserve, where applicable:

- task
- target
- operation
- spatial constraint
- temporal constraint
- required modality
- required image count
- image relationship
- required metadata
- expected output type

Examples:

### Single image
"Describe this image." + 1 valid optical image → valid VQA/captioning.

### Missing image
"What changed between 2020 and 2025?" + only one image → invalid/missing temporal input.

### Missing modality
"Compare optical and SAR imagery." + only optical → invalid/missing SAR.

### Modality mismatch
"Using the SAR image, identify flooded areas." + optical only → invalid.

### External-information mismatch
"What is the population density of this region?" + only satellite imagery → unsupported/insufficient; do not pretend the image alone provides demographic data.

---

## 4. Bitemporal validation

For queries such as:
- "What changed between these two images?"
- "How much did the built-up area increase between 2020 and 2025?"
- "Has vegetation decreased between the two dates?"

Validate, where metadata permits:

- two appropriate images exist
- same/sufficiently corresponding geographic area
- meaningful spatial overlap
- compatible/transformable CRS
- acquisition dates are known when required
- dates are temporally distinct when the query requires change
- temporal ordering is normalized independently of upload order
- modality compatibility
- footprint/resolution are suitable for the requested analysis

### Critical cases

**Valid**
- Area A / 2020 + Area A / 2025 → valid temporal pair.

**Invalid**
- Delhi / 2020 + Mumbai / 2025 → cannot perform same-location bitemporal change detection.
- Query explicitly requests 2020–2025 but files are 2018 + 2025 → invalid.
- One image only for a two-date query → invalid.
- Same acquisition date for a query requiring temporal change → warning/invalid according to existing conventions.
- Three unrelated images with "what changed between these images?" → clarification required, not automatic T1/T2/T3 assignment.

Do not rely solely on filenames to establish location or date. Prefer actual geospatial/acquisition metadata.

---

## 5. Spatial footprint validation

Distinguish:

- same/sufficiently corresponding footprint → valid
- partial overlap → warning or restrict analysis to overlap
- no meaningful overlap → invalid for same-location comparison

Different dimensions or CRS do not automatically mean different locations. Reprojection/resampling may be legitimate.

Do not introduce arbitrary thresholds without documenting them.

---

## 6. Optical/SAR multimodal validation

For optical + SAR requests, verify that the required modalities are actually present.

Where metadata permits, verify:

- geographic overlap
- CRS compatibility/transformability
- footprint compatibility
- resolution suitability
- acquisition timing where relevant

Examples:

- Optical Area A + SAR Area A → potentially valid.
- Optical Area A + SAR Area B → invalid for same-area fusion.
- Optical + SAR requested, only optical uploaded → invalid.
- Flood change across two dates using optical + SAR → decomposition should preserve multimodal + temporal requirements.

BigEarthNet-MM is a useful conceptual reference: Sentinel-1/Sentinel-2 pairs correspond to the same geographic area. Do not claim the project implements BigEarthNet rules verbatim.

---

## 7. Spatial/query decomposition

Preserve spatial constraints such as:

- north/south/east/west
- northeast/northwest/southeast/southwest
- center
- eastern/northern region
- left/right/upper/lower
- "near the river"
- "around the city center"

Examples:

"Where did change occur in the eastern region?" must preserve:
`change_detection + spatial_constraint=east`.

"Highlight the forest north of the settlement." should preserve grounding/referring-expression intent rather than collapsing to generic captioning.

---

## 8. Multi-label and grounding cases

Remote-sensing scenes may contain multiple land-cover types.

Test:
- "What land-cover types are present?"
- "Is there forest, agriculture, or water?"
- "Where is the agricultural field near the river?"
- "Highlight the forest north of the settlement."

Preserve multi-label understanding and grounding/referring-expression intent.

Do not force a single scene label when the query asks for multiple classes.

---

## 9. Image-quality validation

Where technically possible, detect:

- heavy clouds
- cloud shadows
- snow
- excessive NoData
- target fully obscured by invalid pixels

Expected behavior:
- usable but degraded → warning
- target unavailable/obscured → invalid or insufficient
- completely unusable raster → invalid

Do not claim semantic cloud/snow detection is available unless the current implementation actually supports it.

---

## 10. Metadata uncertainty

Missing metadata should be represented as `unknown`, not fabricated.

Examples:

- Missing acquisition date for bitemporal query → clarification/warning if temporal validity cannot be established.
- Missing CRS/location metadata → do not falsely assert same-location compatibility.
- Missing modality metadata → do not invent optical/SAR classification.

The validator should distinguish:
- definitely incompatible
- probably compatible
- compatible with warning
- unknown

Avoid unnecessary false rejection.

---

## 11. Duplicate/identity cases

Test:

- exact same file uploaded twice
- identical raster content with different filenames
- same area/date duplicated

For a change query, warn that no meaningful temporal change is established.

Do not use filenames as the sole identity mechanism.

---

## 12. Ambiguous queries

Examples:

- "What changed?" + two images → change intent, target unspecified.
- "Has this changed?" + one image → missing comparison input.
- "Is this area getting greener?" + one image → likely requires temporal evidence.
- "Find the difference." + two images → comparison intent, but target unspecified.

Preserve ambiguity or request clarification instead of inventing missing assumptions.

---

## 13. Compound queries

Test queries combining multiple requirements:

"Identify the water bodies, determine whether they changed between the two dates, and calculate the percentage change in area."

Expected decomposition conceptually:

1. water-body identification
2. segmentation/delineation
3. temporal comparison
4. area measurement
5. percentage change

The validator must ensure all required inputs are present before routing.

Another hard case:

"How did flooding change between the two dates using optical and SAR imagery?"

Expected requirements:
- flood target
- optical + SAR
- two temporal observations
- same/sufficient geographic correspondence
- change detection
- multimodal analysis

---

## 14. Contradictory/misleading inputs

Test:

- query says 2020–2025, files are 2019 + 2025
- query says SAR, file metadata says optical
- query requires optical + SAR, only optical exists
- query asks same-location change, files have different locations
- three images supplied but query describes a pair
- filenames claim one location/date while geospatial metadata says otherwise

Prefer trusted metadata over filenames.

Do not silently repair contradictions.

---

## 15. Important boundary: validation vs model inference

The validator should check whether the input is suitable for the requested task.

It should NOT reject a valid image merely because it cannot prove that the requested object exists.

Example:

"Is there a railway?" + valid satellite image

→ valid VQA/grounding request; actual railway presence is a model inference problem.

But:

"Using the SAR image..." + optical metadata

→ deterministic input mismatch; reject.

---

## 16. Robustness/security

Do not crash on:

- huge dimensions/files
- too many uploads
- empty filename
- very long/unusual filename
- duplicate names
- malformed multipart input
- unsupported compression/format
- misleading MIME type
- path-traversal-like filenames

Never trust client MIME type alone and never let uploaded filenames directly control filesystem paths.

---

## 17. Routing order

Preferred conceptual flow:

`parse request`
→ `inspect files`
→ `decompose query`
→ `derive required inputs`
→ `validate query ↔ inputs`
→ if invalid: stop
→ if clarification needed: stop/request clarification
→ if warning: preserve warning and continue only when safe
→ route

Do not route an obviously invalid request first and discover the mismatch afterward.

---

## 18. Minimum hard test matrix

Automate tests for:

### Single image
- caption
- VQA
- object identification
- grounding
- segmentation
- quantification
- multi-label land-cover query

### Two images
- valid bitemporal same location
- different locations
- same date
- wrong explicit dates
- partial overlap
- no overlap
- different CRS
- different resolution
- optical + SAR
- incompatible optical/SAR locations
- duplicate images
- missing metadata

### 3+ images
- three dates same location
- unrelated locations
- mixed locations
- mixed modalities
- ambiguous temporal ordering

### Query/input mismatch
- SAR requested / optical uploaded
- optical requested / SAR uploaded
- two dates requested / one image
- explicit dates do not match files
- optical + SAR requested / SAR missing
- same-location bitemporal requested / locations differ

### Bad files
- corrupted
- empty
- invalid raster
- JPEG/PNG
- unsupported extension
- NoData-heavy
- extreme dimensions

### Ambiguity
- "What changed?"
- "Has this changed?"
- "Find the difference."
- "Is this getting greener?"

### Compound
- spatial + temporal + target + quantitative
- optical/SAR + temporal + target
- grounding + spatial relation

---

## 19. Structured errors

Use the project's existing response contract if available.

Otherwise errors should conceptually expose:

- validity/status
- stable error code
- human-readable message
- affected image(s)
- relevant missing/contradictory requirement

Example:

`TEMPORAL_PAIR_LOCATION_MISMATCH`

Message:
"The uploaded images do not represent sufficiently corresponding geographic areas for the requested bitemporal comparison."

Do not break the frontend contract merely to improve error formatting.

---

## 20. Acceptance criteria

The validator hardening is successful when:

1. Invalid files do not crash the system.
2. Required image count is enforced.
3. Required modalities are checked.
4. Bitemporal requests require appropriate temporal evidence.
5. Same-location requirements are checked using trusted geospatial evidence where available.
6. Partial overlap is distinguished from zero overlap.
7. CRS/resolution differences are handled intelligently.
8. Upload order does not define temporal order.
9. Wrong explicit dates are caught.
10. Optical/SAR compatibility is checked.
11. Missing metadata is never fabricated.
12. Spatial constraints survive decomposition.
13. Compound tasks preserve all subtasks.
14. Ambiguous inputs are not silently guessed.
15. Semantic image content is left to model inference.
16. Validation errors are structured.
17. Existing router/frontend contracts remain intact.
18. No model weights/GPU dependencies are introduced.
19. Existing routing behavior is changed only when a demonstrated validation bug requires it.

## Final report required from Cursor

After implementation, report only:

- Files changed
- Validation rules added/fixed
- Tests added
- Tests passed
- Tests failed
- Known limitations
- Remaining risks

Do not claim geographic correspondence, co-registration, modality detection, cloud detection, or temporal validation works unless the implementation has sufficient data to establish it.
