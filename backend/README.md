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

## Error Handling

**Files:** [`app/api/routes.py`](app/api/routes.py),
[`app/main.py`](app/main.py)

Previously `/api/analyze` only handled the *expected* failure cases it
checked for explicitly (bad query, invalid image format/count). Anything
unexpected further down the pipeline — a model failing to load, an OOM
during inference, a bug in a pipeline step — propagated as an unhandled
exception, which FastAPI turns into a bare `500` with no useful body, and
which could take the whole process down mid-demo.

Two layers now catch this:

1. **Route-level (`routes.py`)** — `save_uploads()` errors are translated
   explicitly: `ValueError` (empty upload) → `422`, `OSError` (disk write
   failure) → `500`. The rest of the pipeline
   (validate → route → execute → integrate) is wrapped in
   `try/except HTTPException: raise / except Exception: → 500`, so any
   unexpected failure returns a structured body instead of crashing:

   ```json
   {
     "errors": ["Internal error while processing the request."],
     "request_id": "a1b2c3d4",
     "message": "<exception str, for debugging>"
   }
   ```

   The existing `finally: cleanup_upload_dir(request_id)` (see Upload
   Storage above) still runs whether the request succeeded, failed
   validation, or hit this new catch-all.

2. **App-level (`main.py`)** — a global
   `@app.exception_handler(Exception)` catches anything outside
   `/api/analyze` (e.g. `/api/health`, middleware) as a last resort, so no
   single unhandled exception can crash the server during the demo.

Both layers only translate failures into HTTP responses — they don't
change what the validator, router, or model pipeline actually do.
