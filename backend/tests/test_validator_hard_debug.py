"""
Hard-debug validation cases from SatQuery_Validator_Hard_Debug_Spec.md.

Focus: query sufficiency, compatibility, geo overlap, dates, duplicates,
bad files — without claiming vision-model inference.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from app.agent.geo_checks import compare_footprints
from app.agent.query_requirements import derive_query_requirements
from app.agent.validator import InputValidator, ValidationStatus


def _png(size=(64, 64), color=(10, 20, 30), suffix=".png"):
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    Image.new("RGB", size, color=color).save(tmp.name)
    tmp.close()
    return tmp.name


def _empty_file(suffix=".tif"):
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.close()
    return tmp.name


def _corrupt_tif():
    tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    tmp.write(b"not-a-real-tiff-file")
    tmp.close()
    return tmp.name


def _gray_nodata():
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    Image.new("L", (64, 64), color=0).save(tmp.name)
    tmp.close()
    return tmp.name


@pytest.fixture
def validator():
    return InputValidator()


def test_valid_caption_single_optical(validator):
    p = _png()
    try:
        r = validator.validate(
            [p],
            {"modalities": ["optical"]},
            query="Describe this image.",
        )
        assert r.is_valid
        assert r.status in (ValidationStatus.VALID, ValidationStatus.WARNING)
    finally:
        os.unlink(p)


def test_missing_temporal_image(validator):
    p = _png()
    try:
        r = validator.validate(
            [p],
            {"modalities": ["optical"]},
            query="What changed between 2020 and 2025?",
        )
        assert not r.is_valid
        assert "MISSING_TEMPORAL_INPUT" in r.error_codes
        assert r.status == ValidationStatus.INVALID
    finally:
        os.unlink(p)


def test_wrong_explicit_dates(validator):
    p1, p2 = _png(), _png(color=(1, 2, 3))
    try:
        r = validator.validate(
            [p1, p2],
            {"modalities": ["optical", "optical"], "dates": ["2018-01", "2025-06"]},
            query="How much did the built-up area increase between 2020 and 2025?",
        )
        assert not r.is_valid
        assert "EXPLICIT_DATE_MISMATCH" in r.error_codes
    finally:
        os.unlink(p1)
        os.unlink(p2)


def test_same_date_pair(validator):
    p1, p2 = _png(), _png(color=(9, 9, 9))
    try:
        r = validator.validate(
            [p1, p2],
            {"modalities": ["optical", "optical"], "dates": ["2020-01", "2020-01"]},
            query="What changed between these two images?",
        )
        assert not r.is_valid
        assert "SAME_ACQUISITION_DATE" in r.error_codes
    finally:
        os.unlink(p1)
        os.unlink(p2)


def test_optical_sar_mismatch_sar_requested(validator):
    p = _png()
    try:
        r = validator.validate(
            [p],
            {"modalities": ["optical"]},
            query="Using the SAR image, identify flooded areas.",
        )
        assert not r.is_valid
        assert "MODALITY_MISMATCH_SAR_REQUIRED" in r.error_codes
    finally:
        os.unlink(p)


def test_optical_sar_requested_sar_missing(validator):
    p1, p2 = _png(), _png(color=(2, 2, 2))
    try:
        r = validator.validate(
            [p1, p2],
            {"modalities": ["optical", "optical"]},
            query="Compare optical and SAR imagery of this area.",
        )
        assert not r.is_valid
        assert "MISSING_CROSS_MODAL_INPUT" in r.error_codes
    finally:
        os.unlink(p1)
        os.unlink(p2)


def test_valid_same_location_bitemporal(validator):
    p1, p2 = _png(), _png(color=(3, 3, 3))
    bbox = {"north": 10.1, "south": 10.0, "east": 20.1, "west": 20.0}

    def fake_georef(_path):
        return {
            "location_known": True,
            "bbox": bbox,
            "crs": "EPSG:4326",
            "source": "geotiff-tags",
        }

    try:
        with patch("app.agent.validator.inspect_georef", side_effect=fake_georef):
            r = validator.validate(
                [p1, p2],
                {"modalities": ["optical", "optical"], "dates": ["2020-01", "2025-01"]},
                query="What changed between these two images?",
            )
        assert r.is_valid
        assert r.footprint_check["correspondence"] == "same"
        assert "TEMPORAL_PAIR_LOCATION_MISMATCH" not in r.error_codes
    finally:
        os.unlink(p1)
        os.unlink(p2)


def test_different_location_bitemporal(validator):
    p1, p2 = _png(), _png(color=(4, 4, 4))
    bboxes = [
        {"north": 29.0, "south": 28.0, "east": 78.0, "west": 77.0},  # Delhi-ish
        {"north": 19.5, "south": 18.5, "east": 73.5, "west": 72.5},  # Mumbai-ish
    ]
    calls = {"i": 0}

    def fake_georef(_path):
        b = bboxes[min(calls["i"], 1)]
        calls["i"] += 1
        return {
            "location_known": True,
            "bbox": b,
            "crs": "EPSG:4326",
            "source": "geotiff-tags",
        }

    try:
        with patch("app.agent.validator.inspect_georef", side_effect=fake_georef):
            r = validator.validate(
                [p1, p2],
                {"modalities": ["optical", "optical"], "dates": ["2020-01", "2025-01"]},
                query="What changed between these two images?",
            )
        assert not r.is_valid
        assert "TEMPORAL_PAIR_LOCATION_MISMATCH" in r.error_codes
        assert r.footprint_check["correspondence"] == "none"
    finally:
        os.unlink(p1)
        os.unlink(p2)


def test_partial_vs_zero_overlap():
    a = {"north": 10.5, "south": 10.0, "east": 20.5, "west": 20.0}
    # Small strip overlap only (~10% of smaller footprint) → partial
    b_partial = {"north": 10.05, "south": 9.5, "east": 21.0, "west": 20.0}
    b_none = {"north": 0.5, "south": 0.0, "east": 1.5, "west": 1.0}
    partial = compare_footprints(a, b_partial)
    none = compare_footprints(a, b_none)
    assert partial["correspondence"] == "partial"
    assert none["correspondence"] == "none"
    assert none["coverage"] == 0.0


def test_incompatible_optical_sar_locations(validator):
    p1, p2 = _png(), _png(color=(5, 5, 5))
    bboxes = [
        {"north": 10.1, "south": 10.0, "east": 20.1, "west": 20.0},
        {"north": 0.1, "south": 0.0, "east": 1.1, "west": 1.0},
    ]
    calls = {"i": 0}

    def fake_georef(_path):
        b = bboxes[min(calls["i"], 1)]
        calls["i"] += 1
        return {
            "location_known": True,
            "bbox": b,
            "crs": "EPSG:4326",
            "source": "geotiff-tags",
        }

    try:
        with patch("app.agent.validator.inspect_georef", side_effect=fake_georef):
            r = validator.validate(
                [p1, p2],
                {"modalities": ["optical", "sar"], "dates": ["2020-01", "2020-06"]},
                query="How did flooding change between the two dates using optical and SAR imagery?",
            )
        assert not r.is_valid
        assert (
            "CROSS_MODAL_LOCATION_MISMATCH" in r.error_codes
            or "TEMPORAL_PAIR_LOCATION_MISMATCH" in r.error_codes
        )
    finally:
        os.unlink(p1)
        os.unlink(p2)


def test_duplicate_images(validator):
    p1 = _png(color=(7, 7, 7))
    p2 = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
    Image.open(p1).save(p2)
    try:
        r = validator.validate(
            [p1, p2],
            {"modalities": ["optical", "optical"], "dates": ["2020-01", "2025-01"]},
            query="What changed between these two images?",
        )
        assert any(iss.code == "DUPLICATE_IMAGES" for iss in r.issues)
    finally:
        os.unlink(p1)
        os.unlink(p2)


def test_missing_metadata_location_unknown_warning(validator):
    p1, p2 = _png(), _png(color=(8, 8, 8))
    try:
        r = validator.validate(
            [p1, p2],
            {"modalities": ["optical", "optical"], "dates": ["2020-01", "2025-01"]},
            query="What changed between these two images?",
        )
        # PNG has no trusted geo — must warn, not invent correspondence
        assert r.footprint_check["correspondence"] == "unknown"
        assert any(iss.code == "LOCATION_METADATA_UNKNOWN" for iss in r.issues)
        # Still may be valid-with-warning (unknown ≠ false rejection)
        assert r.is_valid
    finally:
        os.unlink(p1)
        os.unlink(p2)


def test_ambiguous_three_images(validator):
    paths = [_png(color=(i, i, i)) for i in range(3)]
    try:
        r = validator.validate(
            paths,
            {"modalities": ["optical", "optical", "optical"]},
            query="What changed between these images?",
        )
        assert not r.is_valid
        assert "AMBIGUOUS_IMAGE_SET" in r.error_codes
        assert r.status == ValidationStatus.NEEDS_CLARIFICATION
    finally:
        for p in paths:
            os.unlink(p)


def test_malformed_and_empty_files(validator):
    empty = _empty_file()
    corrupt = _corrupt_tif()
    bad_ext = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    bad_ext.write(b"x")
    bad_ext.close()
    try:
        r1 = validator.validate([empty], query="Describe this image.")
        r2 = validator.validate([corrupt], query="Describe this image.")
        r3 = validator.validate([bad_ext.name], query="Describe this image.")
        assert "EMPTY_FILE" in r1.error_codes
        assert "CORRUPT_OR_UNREADABLE" in r2.error_codes
        assert "UNSUPPORTED_FORMAT" in r3.error_codes
    finally:
        os.unlink(empty)
        os.unlink(corrupt)
        os.unlink(bad_ext.name)


def test_nodata_heavy_invalid(validator):
    p = _gray_nodata()
    try:
        r = validator.validate([p], {"modalities": ["optical"]}, query="Describe this image.")
        assert not r.is_valid
        assert "NODATA_HEAVY" in r.error_codes
    finally:
        os.unlink(p)


def test_external_information_unsupported(validator):
    p = _png()
    try:
        r = validator.validate(
            [p],
            {"modalities": ["optical"]},
            query="What is the population density of this region?",
        )
        assert not r.is_valid
        assert r.status == ValidationStatus.UNSUPPORTED
        assert "EXTERNAL_INFORMATION_REQUIRED" in r.error_codes
    finally:
        os.unlink(p)


def test_compound_query_requirements_preserved():
    req = derive_query_requirements(
        "Identify the water bodies, determine whether they changed between "
        "the two dates, and calculate the percentage change in area."
    )
    assert req.needs_temporal_pair
    assert req.is_compound
    assert req.requires_same_location
    assert "water" in req.target_hints


def test_spatial_constraint_preserved():
    req = derive_query_requirements(
        "Where did change occur in the eastern region between the two dates?"
    )
    assert req.spatial_constraint == "east"
    assert req.needs_temporal_pair


def test_railway_presence_is_not_rejected(validator):
    """Semantic content is model inference — validator must not reject."""
    p = _png()
    try:
        r = validator.validate(
            [p],
            {"modalities": ["optical"]},
            query="Is there a railway?",
        )
        assert r.is_valid
        assert "EXTERNAL_INFORMATION_REQUIRED" not in r.error_codes
    finally:
        os.unlink(p)


def test_temporal_order_normalized_warning(validator):
    p1, p2 = _png(), _png(color=(11, 11, 11))
    try:
        r = validator.validate(
            [p1, p2],
            {"modalities": ["optical", "optical"], "dates": ["2025-01", "2020-01"]},
            query="What changed between these two images?",
        )
        assert r.is_valid
        assert any(iss.code == "TEMPORAL_ORDER_NORMALIZED" for iss in r.issues)
        assert r.footprint_check["temporal_order"] == [1, 0]
    finally:
        os.unlink(p1)
        os.unlink(p2)


def test_has_this_changed_one_image(validator):
    p = _png()
    try:
        r = validator.validate(
            [p],
            {"modalities": ["optical"]},
            query="Has this changed?",
        )
        assert not r.is_valid
        assert "MISSING_TEMPORAL_INPUT" in r.error_codes
    finally:
        os.unlink(p)
