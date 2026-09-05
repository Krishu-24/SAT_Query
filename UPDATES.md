# Updates

For the full merge handoff (validator + multi-device + live fixes A→B→C), see **[UPDATE_LOG.md](./UPDATE_LOG.md)** (current tip `eb62b0d`).

The section below is the earlier short note for validator hardening only.

---

## Validator hardening (short)

Before routing, SatQuery checks whether uploads/metadata support the query (temporal pair, modality, same-area GeoTIFF when tags exist, unsupported external-data asks, etc.).

Statuses: `VALID` / `WARNING` / `INVALID` / `NEEDS_CLARIFICATION` / `UNSUPPORTED`.  
422 keeps `detail.errors[]` for the UI.

Key files: `query_requirements.py`, `geo_checks.py`, hardened `validator.py`, `tests/test_validator_hard_debug.py`.  
Spec: `SatQuery_Validator_Hard_Debug_Spec.md`.
