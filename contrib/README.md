# Optional specialist-model work-in-progress (not required to run the app)

- `change-detection/` — change-detection model contribution
- `optical-sar/` — optical/SAR fusion contribution

The integrated app (`backend/` + `router/` + `frontend/`) runs without these.

**Distributed VQA/captioning** uses the Model Host path (`backend/app/node/` + Ollama `qwen2.5vl:7b`), not packages under `contrib/`. See [docs/SETUP.md](../docs/SETUP.md) and [UPDATE_LOG.md](../UPDATE_LOG.md).
