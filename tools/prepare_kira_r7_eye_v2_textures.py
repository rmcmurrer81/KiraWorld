"""Derive bounded brown-eye review textures from Robert's supplied Folder 91 asset.

The source archive is user-supplied local reference material.  This tool reads
only the three eye textures required for Kira's inactive R7 v2 review and
writes deterministic, source-derived PNGs into the requested candidate folder.
It does not touch Avatar Builder bindings, Home World, or any live person state.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ARCHIVE = Path(r"C:\Users\robmc\Desktop\91\sci-fi-girl-v02-walkcycle-test.zip")
EXPECTED_ARCHIVE_SHA256 = "ed9d90f09cc5a17881e14738bc102a704ee331add9442bad1e4d970fc9d4bfb1"
MEMBERS = {
    "diffuse": "textures/eyes_diff03.jpg",
    "normal_full": "textures/eyes_norm_01.jpeg",
    "normal_sclera": "textures/eyes_norm_02.jpeg",
}
EXPECTED_MEMBER_SHA256 = {
    "diffuse": "846de9cb189a86a29bcf3145b2df68b0087632d2c64f0560cd10604d02485ddd",
    "normal_full": "47c817d805e09635dd9420126d82f19d6271cac6df68f0a2e77f34de571af4d1",
    "normal_sclera": "9f2b735dc008eb29cbab746f6a2e07d07563403a0e21a12ec72685fc5b7d6984",
}
DEFAULT_OUTPUT = (
    ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_r7_socket_eye_fit"
    / "review_20260722_v2/derived_textures"
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_authorized_members() -> tuple[dict[str, Image.Image], dict[str, str]]:
    archive_hash = sha256_file(SOURCE_ARCHIVE)
    if archive_hash != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeError(
            f"Folder 91 source archive changed: {archive_hash} != {EXPECTED_ARCHIVE_SHA256}"
        )
    images: dict[str, Image.Image] = {}
    hashes: dict[str, str] = {}
    with zipfile.ZipFile(SOURCE_ARCHIVE) as archive:
        for key, member in MEMBERS.items():
            payload = archive.read(member)
            member_hash = sha256_bytes(payload)
            if member_hash != EXPECTED_MEMBER_SHA256[key]:
                raise RuntimeError(
                    f"Folder 91 eye member {member!r} changed: "
                    f"{member_hash} != {EXPECTED_MEMBER_SHA256[key]}"
                )
            hashes[key] = member_hash
            images[key] = Image.open(io.BytesIO(payload)).convert("RGB")
    return images, {"archive": archive_hash, **hashes}


def derive_brown_iris(source: Image.Image) -> Image.Image:
    # The supplied diffuse stores the iris at the exact texture centre.  Crop
    # just outside its natural limbal boundary so the source's radial fibres,
    # crypts, pupil falloff, and irregularity remain intact.
    crop = source.crop((378, 378, 646, 646)).resize((1024, 1024), Image.Resampling.LANCZOS)
    rgb = np.asarray(crop, dtype=np.float32) / 255.0
    luminance = (
        0.2126 * rgb[:, :, 0]
        + 0.7152 * rgb[:, :, 1]
        + 0.0722 * rgb[:, :, 2]
    )
    luminance = np.clip((luminance - 0.035) * 1.18, 0.0, 1.0)

    yy, xx = np.mgrid[0:1024, 0:1024]
    radius = np.sqrt(((xx - 511.5) / 511.5) ** 2 + ((yy - 511.5) / 511.5) ** 2)

    # A subdued, heterogeneous medium brown.  Luminance comes from the real
    # supplied iris, not from procedural rings.  Subtle golden modulation is
    # strongest mid-iris and deliberately asymmetric so it does not read as a
    # button or target.
    warm = np.zeros_like(rgb)
    warm[:, :, 0] = 0.018 + 0.53 * luminance
    warm[:, :, 1] = 0.007 + 0.255 * np.power(luminance, 1.08)
    warm[:, :, 2] = 0.003 + 0.090 * np.power(luminance, 1.16)
    asymmetric = np.clip(1.0 - radius, 0.0, 1.0) * (0.5 + 0.5 * (xx / 1023.0))
    warm[:, :, 0] += 0.024 * asymmetric
    warm[:, :, 1] += 0.010 * asymmetric

    # Preserve a natural dark pupil and limbal falloff already present in the
    # photograph, reinforcing them only enough to survive the 2.9 mm render.
    pupil = np.clip((radius - 0.105) / 0.105, 0.0, 1.0)
    limbus = 1.0 - 0.48 * np.clip((radius - 0.78) / 0.22, 0.0, 1.0)
    warm *= pupil[:, :, None] * limbus[:, :, None]
    warm[radius < 0.105] *= 0.10

    alpha = np.clip((1.0 - radius) / 0.025, 0.0, 1.0)
    rgba = np.dstack((np.clip(warm, 0.0, 1.0), alpha))
    return Image.fromarray(np.uint8(np.round(rgba * 255.0)), mode="RGBA")


def derive_sclera(source: Image.Image) -> Image.Image:
    # Crop the central living-tissue band before the supplied globe reaches
    # its very red rear/peripheral area.  This retains fine vessels without
    # making Kira look inflamed.
    crop = source.crop((150, 292, 874, 732)).resize((1024, 512), Image.Resampling.LANCZOS)
    crop = ImageEnhance.Color(crop).enhance(0.56)
    crop = ImageEnhance.Contrast(crop).enhance(0.86)
    rgb = np.asarray(crop, dtype=np.float32) / 255.0
    target = np.array([0.86, 0.79, 0.75], dtype=np.float32)
    rgb = np.clip(0.64 * rgb + 0.36 * target, 0.0, 1.0)

    # The moving iris is a separate mesh.  Remove the source's fixed blue iris
    # beneath it so a gaze cannot expose a second pupil.  A broad feathered
    # warm scleral fill is used only under the iris and its travel envelope.
    yy, xx = np.mgrid[0:512, 0:1024]
    radial = np.sqrt(((xx - 511.5) / 216.0) ** 2 + ((yy - 255.5) / 236.0) ** 2)
    centre_fill = np.array([0.83, 0.77, 0.73], dtype=np.float32)
    fill_weight = np.clip((1.15 - radial) / 0.34, 0.0, 1.0)[:, :, None]
    rgb = rgb * (1.0 - fill_weight) + centre_fill * fill_weight
    return Image.fromarray(np.uint8(np.round(np.clip(rgb, 0.0, 1.0) * 255.0)), mode="RGB")


def derive_iris_normal(source: Image.Image) -> Image.Image:
    crop = source.crop((178, 178, 334, 334)).resize((1024, 1024), Image.Resampling.LANCZOS)
    return ImageEnhance.Contrast(crop).enhance(0.82)


def derive_sclera_normal(source: Image.Image) -> Image.Image:
    crop = source.crop((74, 146, 438, 366)).resize((1024, 512), Image.Resampling.LANCZOS)
    return ImageEnhance.Contrast(crop).enhance(0.68).filter(ImageFilter.GaussianBlur(0.28))


def main() -> None:
    args = parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    source_images, source_hashes = load_authorized_members()

    generated = {
        "brown_iris_base_color": (
            output / "kira_r7_v2_brown_iris_base_color.png",
            derive_brown_iris(source_images["diffuse"]),
        ),
        "sclera_base_color": (
            output / "kira_r7_v2_sclera_base_color.png",
            derive_sclera(source_images["diffuse"]),
        ),
        "iris_normal": (
            output / "kira_r7_v2_iris_normal.png",
            derive_iris_normal(source_images["normal_full"]),
        ),
        "sclera_normal": (
            output / "kira_r7_v2_sclera_normal.png",
            derive_sclera_normal(source_images["normal_sclera"]),
        ),
    }
    records: dict[str, dict[str, object]] = {}
    for key, (path, image) in generated.items():
        image.save(path, format="PNG", optimize=True)
        records[key] = {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "size": list(image.size),
        }

    manifest = {
        "schema_version": 1,
        "kind": "bounded_source_derived_eye_textures_no_live_write",
        "source": {
            "path": str(SOURCE_ARCHIVE),
            "authorization_context": (
                "Robert explicitly supplied Desktop Folder 91 to improve the avatar, world, "
                "and movement builders. Archive has no bundled license metadata. Local inactive "
                "review use only; no redistribution claim is made."
            ),
            "members": MEMBERS,
            "hashes": source_hashes,
        },
        "generated": records,
        "limits": [
            "This output is only an inactive R7 v2 review input.",
            "It does not bind, promote, activate, or modify Kira or Home World.",
            "The brown iris is a deterministic color derivation of the supplied photographic eye texture.",
        ],
    }
    manifest_path = output / "texture_derivation_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "generated": records}, indent=2))


if __name__ == "__main__":
    main()
