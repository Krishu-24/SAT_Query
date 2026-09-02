"""
Tests for upload storage helpers — request-scoped temp dirs and cleanup.
"""

import asyncio
import io
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from fastapi import UploadFile

from app.utils.storage import save_uploads, cleanup_upload_dir, make_upload_dir
from app.utils.config import settings


def _make_upload(filename: str, content: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content))


def test_save_uploads_creates_single_request_dir():
    """Multi-image uploads land in ONE shared directory, not one-per-image."""
    request_id = "test-single-dir"
    uploads = [_make_upload("a.png", b"fake-png-bytes"), _make_upload("b.tif", b"fake-tif-bytes")]

    try:
        paths = asyncio.run(save_uploads(uploads, request_id))

        assert len(paths) == 2
        parents = {Path(p).parent for p in paths}
        assert len(parents) == 1, "All images should be saved into one shared request directory"
        assert parents.pop() == Path(settings.TEMP_DIR) / request_id
    finally:
        cleanup_upload_dir(request_id)


def test_save_uploads_preserves_extension_and_order():
    request_id = "test-extensions"
    uploads = [_make_upload("first.tif", b"1"), _make_upload("second.jpg", b"2")]

    try:
        paths = asyncio.run(save_uploads(uploads, request_id))

        assert paths[0].endswith("image_0.tif")
        assert paths[1].endswith("image_1.jpg")
    finally:
        cleanup_upload_dir(request_id)


def test_save_uploads_rejects_empty_file():
    request_id = "test-empty"
    uploads = [_make_upload("empty.png", b"")]

    try:
        raised = False
        try:
            asyncio.run(save_uploads(uploads, request_id))
        except ValueError:
            raised = True
        assert raised, "Expected ValueError for an empty upload"
    finally:
        cleanup_upload_dir(request_id)


def test_cleanup_upload_dir_removes_directory():
    request_id = "test-cleanup"
    make_upload_dir(request_id)
    upload_dir = Path(settings.TEMP_DIR) / request_id
    assert upload_dir.exists()

    cleanup_upload_dir(request_id)

    assert not upload_dir.exists()


def test_cleanup_upload_dir_is_safe_when_missing():
    # Should not raise even if the directory was never created.
    cleanup_upload_dir("nonexistent-request-id")
