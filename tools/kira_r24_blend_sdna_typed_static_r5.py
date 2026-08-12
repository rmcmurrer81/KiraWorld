from __future__ import annotations

"""R24 R5 typed Blend preflight.

This is an append-only successor to the sealed R4 parser.  It retains R4's
structural/SDNA checks and additionally exposes the typed inline ``ID.us``
value.  R5 uses that value to prove the one allowed Material-user transition
instead of normalizing every possible signed value without a separate check.
"""

import hashlib
from pathlib import Path
import struct
from typing import Iterable

from tools import kira_r24_blend_sdna_typed_static_r4 as r4


TypedBlendError = r4.TypedBlendError
BlendBlock = r4.BlendBlock
SDNASchema = r4.SDNASchema
CODE_TO_STRUCTURE = r4.CODE_TO_STRUCTURE


def _id_user_count(
    schema: SDNASchema,
    block: BlendBlock,
    pointer_size: int,
    endian: str,
) -> int | None:
    if block.payload is None:
        raise TypedBlendError("semantic block payload was not retained")
    top_layout, _ = r4.structure_layout(schema, block.sdna_index, pointer_size)
    id_fields = [
        (field, offset)
        for field, offset, _ in top_layout
        if schema.types[field.type_index] == "ID"
        and schema.names[field.name_index].split("[")[0] == "id"
        and not r4._is_pointer_declaration(schema.names[field.name_index])
    ]
    if len(id_fields) != 1:
        raise TypedBlendError("semantic structure lacks one inline typed ID field")
    _, id_offset = id_fields[0]
    id_index = schema.structure_index("ID")
    id_layout, _ = r4.structure_layout(schema, id_index, pointer_size)
    fields = [
        (offset, size)
        for field, offset, size in id_layout
        if schema.names[field.name_index].split("[")[0].lstrip("*") == "us"
        and not r4._is_pointer_declaration(schema.names[field.name_index])
        and r4._array_multiplier(schema.names[field.name_index]) == 1
    ]
    if not fields:
        return None
    if len(fields) != 1:
        raise TypedBlendError("ID has an ambiguous typed user-count field")
    user_offset, user_size = fields[0]
    start = id_offset + user_offset
    end = start + user_size
    if start < 0 or end > len(block.payload) or user_size not in {1, 2, 4, 8}:
        raise TypedBlendError("typed ID.us lies outside block payload")
    return int.from_bytes(
        block.payload[start:end],
        byteorder="little" if endian == "<" else "big",
        signed=True,
    )


def parse_typed_blend(path: Path) -> dict[str, object]:
    """Parse a Blend using the R4 structural rules and retain typed ID.us."""
    stream, compressed = r4._open_blend_stream(path)
    retained: list[BlendBlock] = []
    all_meta: list[BlendBlock] = []
    dna_payload: bytes | None = None
    ended = False
    with stream:
        header, endian, pointer_size, read_header = r4._header_and_reader(stream)
        for block_number in range(2_000_001):
            parsed = read_header()
            if parsed is None:
                break
            if block_number == 2_000_000:
                raise TypedBlendError("unreasonable Blender block count")
            code_raw, length, old_address, sdna, count = parsed
            try:
                code = code_raw.rstrip(b"\x00").decode("ascii", "strict")
            except UnicodeDecodeError as exc:
                raise TypedBlendError("non-ASCII block code") from exc
            if not code or length < 0 or length > 2**40 or count < 0 or count > 2**40:
                raise TypedBlendError("invalid Blender block dimensions")
            payload = stream.read(length)
            if len(payload) != length:
                raise TypedBlendError("truncated Blender block payload")
            keep = payload if code in CODE_TO_STRUCTURE or code == "DNA1" else None
            block = BlendBlock(code, length, old_address, sdna, count, keep)
            all_meta.append(block)
            if code in CODE_TO_STRUCTURE:
                retained.append(block)
            if code == "DNA1":
                if dna_payload is not None:
                    raise TypedBlendError("duplicate DNA1 block")
                dna_payload = payload
            if code == "ENDB":
                if length != 0 or count != 0:
                    raise TypedBlendError("malformed ENDB block")
                ended = True
                break
        if not ended or stream.read(1):
            raise TypedBlendError("Blend does not terminate exactly at ENDB")
    if dna_payload is None:
        raise TypedBlendError("Blend lacks DNA1")
    schema = r4.parse_sdna(dna_payload, endian)
    semantic: dict[str, list[dict[str, object]]] = {code: [] for code in CODE_TO_STRUCTURE}
    addresses: set[int] = set()
    for block in retained:
        if block.old_address <= 0 or block.old_address in addresses:
            raise TypedBlendError("semantic datablock has a null or duplicate old-address pointer")
        addresses.add(block.old_address)
        semantic[block.code].append(
            {
                "name": r4.typed_id_name(schema, block, pointer_size),
                "sdna_index": block.sdna_index,
                "sdna_type": schema.structure_type(block.sdna_index),
                "count": block.count,
                "bytes": block.length,
                "direct_block_sha256": hashlib.sha256(block.payload or b"").hexdigest(),
                "id_user_count": _id_user_count(schema, block, pointer_size, endian),
                "id_user_count_normalized_block_sha256": r4.id_user_count_normalized_block_sha256(
                    schema, block, pointer_size
                ),
            }
        )
    for code, records in semantic.items():
        if not records:
            raise TypedBlendError(f"Blend lacks typed {code} datablock")
        records.sort(key=lambda row: str(row["name"]))
    counts: dict[str, int] = {}
    for block in all_meta:
        counts[block.code] = counts.get(block.code, 0) + 1
    return {
        "schema": "kira.avatar.r24.typed_blend_preflight.v5",
        "compressed_zstd": compressed,
        "header": header.decode("ascii"),
        "pointer_size": pointer_size,
        "endian": "little" if endian == "<" else "big",
        "block_count": len(all_meta),
        "block_counts": {key: counts[key] for key in sorted(counts)},
        "dna": {
            "name_count": len(schema.names),
            "type_count": len(schema.types),
            "structure_count": len(schema.structures),
        },
        "semantic_ids": semantic,
    }


def semantic_names(summary: dict[str, object], code: str) -> set[str]:
    return r4.semantic_names(summary, code)


def iter_semantic_blocks(path: Path) -> Iterable[dict[str, object]]:
    summary = parse_typed_blend(path)
    semantic = summary["semantic_ids"]
    for code in sorted(semantic):
        yield from semantic[code]

