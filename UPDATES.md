# Updates

Canonical merge handoff: **[UPDATE_LOG.md](./UPDATE_LOG.md)** (workstreams **A → B → C**, tip through `6ccd39a` / code `eb62b0d`).

| Area | Where to read |
|------|----------------|
| Validator hardening | Workstream A in UPDATE_LOG; short note below; spec `SatQuery_Validator_Hard_Debug_Spec.md` |
| Multi-device roles / pairing | Workstream B; `SATQUERY_MULTIDEVICE_SPEC.md`; [docs/SETUP.md](docs/SETUP.md) |
| Live fixes (registry, host console, GeoTIFF→PNG, single-VQA routing) | Workstream C |
| How it works | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Getting started | [README.md](README.md) |

---

## Validator hardening (short)

Before routing, SatQuery checks whether uploads/metadata support the query (temporal pair, modality, same-area GeoTIFF when tags exist, unsupported external-data asks, etc.).

Statuses: `VALID` / `WARNING` / `INVALID` / `NEEDS_CLARIFICATION` / `UNSUPPORTED`.  
422 keeps `detail.errors[]` for the UI.

Key files: `query_requirements.py`, `geo_checks.py`, hardened `validator.py`, `tests/test_validator_hard_debug.py`.
