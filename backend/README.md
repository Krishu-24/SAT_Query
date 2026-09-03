# SatQuery AI — Backend

FastAPI backend for the agentic remote-sensing analysis pipeline. See the
project root [README](../README.md) for the overall system and
[CONTRIBUTING.md](../CONTRIBUTING.md) for the team workflow.

## Upload Storage

**Files:** [`app/utils/storage.py`](app/utils/storage.py)

`POST /api/analyze` accepts 1–2 uploaded images per request. Before this
module existed, the route called `tempfile.mkdtemp()` inside the per-image
save loop, so a 2-image (bi-temporal / cross-modal) request scattered its
files across two unrelated temp directories, and nothing ever cleaned them
up.

`storage.py` fixes both problems:

| Function | Purpose |
|---|---|
| `make_upload_dir(request_id)` | Creates (if needed) and returns `TEMP_DIR/{request_id}/` — one directory per request. |
| `save_uploads(images, request_id)` | Saves every uploaded file for a request into that single directory as `image_0.ext`, `image_1.ext`, etc., in upload order. Raises `ValueError` if an upload is empty. |
| `cleanup_upload_dir(request_id)` | Removes the request's temp directory. Safe to call even if it was never created. |

`TEMP_DIR` is configured in [`app/utils/config.py`](app/utils/config.py)
(defaults to `/tmp/satquery`, overridable via the `TEMP_DIR` env var).

In [`app/api/routes.py`](app/api/routes.py), `/api/analyze` calls
`save_uploads()` for step 1, and calls `cleanup_upload_dir()` in a `finally`
block once the pipeline has run — so temp uploads are removed after every
request regardless of outcome. Evidence images generated during inference
(overlays, change maps) are saved separately under `settings.RESULTS_DIR`
and are unaffected by this cleanup.

**Tests:** [`tests/test_storage.py`](tests/test_storage.py) covers the
shared-directory behavior, filename/order preservation, empty-upload
rejection, and cleanup (including the "already gone" case).

```bash
cd backend
python -m pytest tests/test_storage.py -v
```
