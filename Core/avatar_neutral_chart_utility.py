"""Deterministic, non-authorizing consumption of neutral Avatar Builder charts."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import re
from typing import Any, Mapping

from PIL import Image, UnidentifiedImageError

from Core import avatar_anatomy_package as path_guard


SCHEMA = "kira.avatar.neutral_skin_material_selector_map.v1"
READY = "MACHINE_SELECTOR_AND_MATERIAL_DIRECTION_READY_PENDING_RENDER"
PASS_PENDING_RENDER = "MACHINE_SELECTOR_AND_MATERIAL_DIRECTION_PASS_PENDING_RENDER"
SELECTOR_MAP_CANONICAL_SHA256 = (
    "92534d08552e63af04a00e4d908c4357fd07a5b79b75d228aec8275fb6deb754"
)
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,95}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class NeutralChartUtilityError(ValueError):
    """Fail-closed selector-package or synthetic-fixture error."""


def _strict_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise NeutralChartUtilityError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            path_guard._io_path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_strict_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                NeutralChartUtilityError(f"{label} contains non-finite number: {token}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise NeutralChartUtilityError(f"cannot read {label}") from exc
    if not isinstance(value, dict):
        raise NeutralChartUtilityError(f"{label} must be an object")
    return value


def _strict_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise NeutralChartUtilityError(f"{label} must be a JSON boolean")
    return value


def _rgb(value: Any, label: str) -> list[int]:
    if (
        not isinstance(value, list)
        or len(value) != 3
        or any(type(channel) is not int or not 0 <= channel <= 255 for channel in value)
    ):
        raise NeutralChartUtilityError(f"{label} must be three integer sRGB channels")
    return list(value)


def _assert_exact_selector_map(value: Mapping[str, Any]) -> None:
    """Reject any in-memory selector data that was not the audited v1 map."""

    if path_guard.canonical_sha256(value) != SELECTOR_MAP_CANONICAL_SHA256:
        raise NeutralChartUtilityError("selector map identity is not the audited v1 map")


def _verify_bound_chart_samples(
    chart_path: Path,
    sampling: Mapping[str, Any],
    selectors: list[Mapping[str, Any]],
) -> None:
    """Decode the bound PNG and prove every declared machine sample."""

    try:
        with Image.open(path_guard._io_path(chart_path)) as image:
            image.load()
            if image.format != "PNG":
                raise NeutralChartUtilityError("bound chart is not a PNG")
            expected_size = (sampling["image_width"], sampling["image_height"])
            if image.size != expected_size:
                raise NeutralChartUtilityError("bound chart dimensions do not match the map")
            rgb = image.convert("RGB")
            try:
                for selector in selectors:
                    actual = [
                        list(rgb.getpixel((sample_x, selector["sample_y"])))
                        for sample_x in selector["sample_x"]
                    ]
                    if actual != selector["regional_srgb"]:
                        raise NeutralChartUtilityError(
                            f"bound chart pixels do not match {selector['selector_id']}"
                        )
            finally:
                rgb.close()
    except (OSError, UnidentifiedImageError) as exc:
        raise NeutralChartUtilityError("cannot decode the bound chart") from exc


def load_skin_selector_map(project_root: str | Path, relative_path: str) -> dict[str, Any]:
    root = path_guard._validated_project_root(project_root)
    config_path = path_guard._project_file(root, relative_path, "selector map")
    config = _read_json(config_path, "selector map")
    _assert_exact_selector_map(config)
    if config.get("schema") != SCHEMA or config.get("schema_version") != 1:
        raise NeutralChartUtilityError("selector map schema is not exact")
    if config.get("status") != READY:
        raise NeutralChartUtilityError("selector map is not ready for bounded machine use")

    chart = config.get("chart")
    if not isinstance(chart, Mapping) or set(chart) != {
        "path", "bytes", "sha256", "content_class"
    }:
        raise NeutralChartUtilityError("chart binding fields are not exact")
    if chart["content_class"] != "neutral_nonperson_design_chart":
        raise NeutralChartUtilityError("chart content class is not neutral and non-person")
    chart_path = path_guard._project_file(root, chart["path"], "bound chart")
    if type(chart["bytes"]) is not int or path_guard._file_size(chart_path) != chart["bytes"]:
        raise NeutralChartUtilityError("bound chart byte count mismatch")
    if not isinstance(chart["sha256"], str) or not SHA256.fullmatch(chart["sha256"]):
        raise NeutralChartUtilityError("bound chart hash is malformed")
    if path_guard.sha256_file(chart_path) != chart["sha256"]:
        raise NeutralChartUtilityError("bound chart hash mismatch")

    sampling = config.get("sampling")
    if not isinstance(sampling, Mapping) or set(sampling) != {
        "image_width", "image_height", "method", "swatch_names"
    }:
        raise NeutralChartUtilityError("sampling fields are not exact")
    if sampling["image_width"] != 1536 or sampling["image_height"] != 1024:
        raise NeutralChartUtilityError("chart dimensions are not exact")
    if sampling["method"] != "exact_hash_bound_srgb_swatch_points":
        raise NeutralChartUtilityError("sampling method is not exact")
    if sampling["swatch_names"] != [
        "swatch_a", "swatch_b", "swatch_c", "swatch_d", "swatch_e"
    ]:
        raise NeutralChartUtilityError("swatch names are not exact")

    selectors = config.get("selectors")
    if not isinstance(selectors, list) or len(selectors) != 6:
        raise NeutralChartUtilityError("selector map must contain exactly six rows")
    seen = set()
    for index, selector in enumerate(selectors, start=1):
        if not isinstance(selector, Mapping) or set(selector) != {
            "selector_id", "chart_label", "sample_y", "sample_x", "regional_srgb"
        }:
            raise NeutralChartUtilityError("selector fields are not exact")
        selector_id = selector["selector_id"]
        if not isinstance(selector_id, str) or not SAFE_ID.fullmatch(selector_id):
            raise NeutralChartUtilityError("selector id is unsafe")
        if selector_id in seen:
            raise NeutralChartUtilityError("selector id is duplicated")
        seen.add(selector_id)
        if selector["chart_label"] != f"{index:02d}":
            raise NeutralChartUtilityError("selector label order is not exact")
        if type(selector["sample_y"]) is not int or not 0 <= selector["sample_y"] < 1024:
            raise NeutralChartUtilityError("sample y is outside the chart")
        if selector["sample_x"] != [88, 121, 154, 187, 220]:
            raise NeutralChartUtilityError("sample x coordinates are not exact")
        if not isinstance(selector["regional_srgb"], list) or len(selector["regional_srgb"]) != 5:
            raise NeutralChartUtilityError("selector must contain exactly five swatches")
        for swatch_index, swatch in enumerate(selector["regional_srgb"]):
            _rgb(swatch, f"selector swatch {swatch_index}")

    truth = config.get("truth")
    expected_false = {
        "real_person_photograph",
        "identity_or_likeness_evidence",
        "medical_or_colorimetric_authority",
        "maturity_classification_allowed",
        "body_geometry_changed",
        "render_review_passed",
        "photo_replacement_accepted",
        "photo_deletion_authorized",
    }
    if not isinstance(truth, Mapping) or set(truth) != expected_false:
        raise NeutralChartUtilityError("truth boundary fields are not exact")
    for field in expected_false:
        if _strict_bool(truth[field], field) is not False:
            raise NeutralChartUtilityError(f"truth boundary {field} must remain false")

    _verify_bound_chart_samples(chart_path, sampling, selectors)

    return copy.deepcopy(config)


def apply_skin_material_selector(
    selector_map: Mapping[str, Any],
    synthetic_body: Mapping[str, Any],
    selector_id: str,
) -> dict[str, Any]:
    _assert_exact_selector_map(selector_map)
    if synthetic_body.get("schema") != "kira.avatar.synthetic_material_test_body.v1":
        raise NeutralChartUtilityError("synthetic test body schema is not exact")
    body_id = synthetic_body.get("body_id")
    if not isinstance(body_id, str) or not SAFE_ID.fullmatch(body_id):
        raise NeutralChartUtilityError("synthetic test body id is unsafe")
    if synthetic_body.get("synthetic_nonperson") is not True:
        raise NeutralChartUtilityError("chart utility accepts only a synthetic non-person fixture")
    geometry_sha256 = synthetic_body.get("geometry_sha256")
    if not isinstance(geometry_sha256, str) or not SHA256.fullmatch(geometry_sha256):
        raise NeutralChartUtilityError("synthetic test geometry hash is malformed")
    if set(synthetic_body) != {
        "schema", "body_id", "synthetic_nonperson", "geometry_sha256", "material_direction"
    }:
        raise NeutralChartUtilityError("synthetic test body fields are not exact")

    selectors = {
        selector["selector_id"]: selector for selector in selector_map.get("selectors", [])
    }
    if selector_id not in selectors:
        raise NeutralChartUtilityError("requested selector id is not present")
    selector = selectors[selector_id]
    before = copy.deepcopy(dict(synthetic_body))
    after = copy.deepcopy(before)
    after["material_direction"] = {
        "source_chart_sha256": selector_map["chart"]["sha256"],
        "selector_id": selector_id,
        "chart_label": selector["chart_label"],
        "base_srgb": list(selector["regional_srgb"][0]),
        "regional_srgb": copy.deepcopy(selector["regional_srgb"]),
        "calibrated": False,
    }
    before_hash = path_guard.canonical_sha256(before)
    after_hash = path_guard.canonical_sha256(after)
    if before_hash == after_hash:
        raise NeutralChartUtilityError("selector did not change the material direction")
    if after["geometry_sha256"] != before["geometry_sha256"]:
        raise NeutralChartUtilityError("selector changed the synthetic geometry identity")
    return {
        "schema": "kira.avatar.neutral_chart_machine_utility_receipt.v1",
        "schema_version": 1,
        "status": PASS_PENDING_RENDER,
        "body_id": body_id,
        "selector_id": selector_id,
        "before_sha256": before_hash,
        "after_sha256": after_hash,
        "geometry_sha256": geometry_sha256,
        "geometry_unchanged": True,
        "material_direction": copy.deepcopy(after["material_direction"]),
        "repeatable_material_change": True,
        "render_review_passed": False,
        "photo_replacement_accepted": False,
        "photo_deletion_authorized": False,
        "output_body": after,
    }
