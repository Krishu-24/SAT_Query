"""
Upload storage helpers — request-scoped temp directories with cleanup.

Owner: M1 (Backend Lead)

Each request gets ONE directory (settings.TEMP_DIR/{request_id}) instead of a
separate tempdir per image, so multi-image requests are easy to reason about
and to clean up in one shot after the pipeline finishes.
"""

import shutil
from pathlib import Path

from fastapi import UploadFile
from loguru import logger

from app.utils.config import settings


def make_upload_dir(request_id: str) -> Path:
    """Create (if needed) and return the temp upload directory for a request."""
    upload_dir = Path(settings.TEMP_DIR) / request_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


async def save_uploads(images: list[UploadFile], request_id: str) -> list[str]:
    """
    Save uploaded images into one request-scoped temp directory.

    Args:
        images: Uploaded files from the request.
        request_id: Unique request identifier, used as the directory name.

    Returns:
        List of saved file paths, in the same order as `images`.

    Raises:
        ValueError: If any uploaded file is empty.
    """
    upload_dir = make_upload_dir(request_id)
    image_paths: list[str] = []

    for i, img_file in enumerate(images):
        suffix = Path(img_file.filename or "").suffix or ".png"
        dest = upload_dir / f"image_{i}{suffix}"

        content = await img_file.read()
        if not content:
            raise ValueError(
                f"Image {i + 1} ('{img_file.filename}') is empty or failed to upload."
            )

        dest.write_bytes(content)
        image_paths.append(str(dest))
        logger.debug(f"[{request_id}] Saved upload: {dest} ({len(content)} bytes)")

    return image_paths


def cleanup_upload_dir(request_id: str) -> None:
    """Remove a request's temp upload directory, if present. Safe to call if missing."""
    upload_dir = Path(settings.TEMP_DIR) / request_id
    if upload_dir.exists():
        shutil.rmtree(upload_dir, ignore_errors=True)
        logger.debug(f"[{request_id}] Cleaned up temp uploads: {upload_dir}")
