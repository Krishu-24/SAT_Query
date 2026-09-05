# Updates

**Start here:** [README.md](./README.md) (how to run + documentation hub).

Canonical merge handoff: **[UPDATE_LOG.md](./UPDATE_LOG.md)** (workstreams **A → D**).

| Area | Where to read |
|------|----------------|
| How to run / product overview | [README.md](./README.md) |
| Setup & pairing | [docs/SETUP.md](docs/SETUP.md) |
| Architecture | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Validator hardening | Workstream A · [SatQuery_Validator_Hard_Debug_Spec.md](SatQuery_Validator_Hard_Debug_Spec.md) |
| Multi-device | Workstream B · [SATQUERY_MULTIDEVICE_SPEC.md](SATQUERY_MULTIDEVICE_SPEC.md) |
| Live fixes (registry, GeoTIFF, VQA routing) | Workstream C |
| API hardening + land-cover + UI polish | Workstream D · [CHANGELOG.md](CHANGELOG.md) |

---

## Validator hardening (short)

Before routing, SatQuery checks whether uploads/metadata support the query (temporal pair, modality, same-area GeoTIFF when tags exist, unsupported external-data asks, etc.).

Statuses: `VALID` / `WARNING` / `INVALID` / `NEEDS_CLARIFICATION` / `UNSUPPORTED`.  
422 keeps `detail.errors[]` for the UI (unified error envelope after Workstream D).

Key files: `query_requirements.py`, `geo_checks.py`, hardened `validator.py`, `tests/test_validator_hard_debug.py`.
