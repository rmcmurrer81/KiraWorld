from __future__ import annotations

"""Read-only, typed Blender block/SDNA preflight for the R24 R4 gate.

This module deliberately does not decode geometry.  Its narrow job is to
prove that semantic Blender datablocks are genuine blocks whose BHead SDNA
index, count, byte length, structure type, and typed ``ID.name`` field agree.
Geometry acceptance belongs to the separately sealed Blender extractor.
"""

from dataclasses import dataclass
from functools import lru_cache
import hashlib
from pathlib import Path
import struct
from typing import BinaryIO, Iterable


class TypedBlendError(ValueError):
    """The file is not a structurally and type-consistent Blender artifact."""


@dataclass(frozen=True)
class SDNAField:
    type_index: int
    name_index: int


@dataclass(frozen=True)
class SDNAStruct:
    type_index: int
    fields: tuple[SDNAField, ...]


@dataclass(frozen=True)
class SDNASchema:
    names: tuple[str, ...]
    types: tuple[str, ...]
    type_lengths: tuple[int, ...]
    structures: tuple[SDNAStruct, ...]

    def structure_type(self, index: int) -> str:
        if index < 0 or index >= len(self.structures):
            raise TypedBlendError("block SDNA index is outside DNA1 STRC")
        return self.types[self.structures[index].type_index]

    def structure_index(self, type_name: str) -> int:
        matches = [
            index
            for index, item in enumerate(self.structures)
            if self.types[item.type_index] == type_name
        ]
        if len(matches) != 1:
            raise TypedBlendError(f"DNA1 has {len(matches)} structures named {type_name!r}")
        return matches[0]


@dataclass(frozen=True)
class BlendBlock:
    code: str
    length: int
    old_address: int
    sdna_index: int
    count: int
    payload: bytes | None


CODE_TO_STRUCTURE = {
    "OB": "Object",
    "ME": "Mesh",
    "AR": "bArmature",
    "AC": "bAction",
    "MA": "Material",
}


def _align(offset: int, alignment: int) -> int:
    if alignment <= 1:
        return offset
    return (offset + alignment - 1) // alignment * alignment


def _array_multiplier(name: str) -> int:
    multiplier = 1
    start = 0
    while True:
        left = name.find("[", start)
        if left < 0:
            return multiplier
        right = name.find("]", left + 1)
        if right < 0:
            raise TypedBlendError("unterminated SDNA array declarator")
        raw = name[left + 1 : right]
        if not raw.isdigit() or int(raw) <= 0:
            raise TypedBlendError("invalid SDNA array extent")
        multiplier *= int(raw)
        if multiplier > 2**31:
            raise TypedBlendError("unreasonable SDNA array extent")
        start = right + 1


def _is_pointer_declaration(name: str) -> bool:
    # DNA names retain C declarators.  Any asterisk denotes a serialized
    # pointer-sized field, including function-pointer spellings.
    return "*" in name


def _open_blend_stream(path: Path) -> tuple[BinaryIO, bool]:
    raw = path.open("rb")
    magic = raw.read(4)
    raw.seek(0)
    if magic != b"\x28\xb5\x2f\xfd":
        return raw, False
    raw.close()
    try:
        from compression import zstd
    except ImportError as exc:  # pragma: no cover - depends on Python build
        raise TypedBlendError("zstd-compressed Blend cannot be inspected") from exc
    return zstd.open(path, "rb"), True


def parse_sdna(payload: bytes, endian: str) -> SDNASchema:
    offset = 0

    def take(size: int) -> bytes:
        nonlocal offset
        value = payload[offset : offset + size]
        if len(value) != size:
            raise TypedBlendError("truncated DNA1 payload")
        offset += size
        return value

    def tag(expected: bytes) -> None:
        if take(4) != expected:
            raise TypedBlendError(f"DNA1 lacks {expected.decode('ascii')} section")

    def u32() -> int:
        return struct.unpack(endian + "I", take(4))[0]

    def u16() -> int:
        return struct.unpack(endian + "H", take(2))[0]

    def strings(count: int) -> tuple[str, ...]:
        nonlocal offset
        values: list[str] = []
        for _ in range(count):
            end = payload.find(b"\x00", offset)
            if end < 0:
                raise TypedBlendError("unterminated DNA1 string")
            try:
                values.append(payload[offset:end].decode("utf-8", "strict"))
            except UnicodeDecodeError as exc:
                raise TypedBlendError("DNA1 string is not UTF-8") from exc
            offset = end + 1
        offset = _align(offset, 4)
        if offset > len(payload):
            raise TypedBlendError("DNA1 string padding overrun")
        return tuple(values)

    tag(b"SDNA")
    tag(b"NAME")
    name_count = u32()
    if name_count <= 0 or name_count > 1_000_000:
        raise TypedBlendError("invalid DNA1 NAME count")
    names = strings(name_count)
    tag(b"TYPE")
    type_count = u32()
    if type_count <= 0 or type_count > 1_000_000:
        raise TypedBlendError("invalid DNA1 TYPE count")
    types = strings(type_count)
    tag(b"TLEN")
    type_lengths = tuple(u16() for _ in range(type_count))
    offset = _align(offset, 4)
    tag(b"STRC")
    structure_count = u32()
    if structure_count <= 0 or structure_count > 1_000_000:
        raise TypedBlendError("invalid DNA1 STRC count")
    structures: list[SDNAStruct] = []
    seen_types: set[int] = set()
    for _ in range(structure_count):
        type_index = u16()
        field_count = u16()
        if type_index >= type_count or type_index in seen_types:
            raise TypedBlendError("invalid or duplicate DNA1 structure type")
        seen_types.add(type_index)
        fields: list[SDNAField] = []
        for _ in range(field_count):
            field_type = u16()
            field_name = u16()
            if field_type >= type_count or field_name >= name_count:
                raise TypedBlendError("invalid DNA1 field index")
            fields.append(SDNAField(field_type, field_name))
        structures.append(SDNAStruct(type_index, tuple(fields)))
    if any(payload[offset:]):
        raise TypedBlendError("unexpected nonzero DNA1 trailing data")
    schema = SDNASchema(names, types, type_lengths, tuple(structures))
    # These types are needed to resolve typed semantic IDs.  A copied but
    # unrelated/incomplete DNA table is not sufficient.
    schema.structure_index("ID")
    for type_name in CODE_TO_STRUCTURE.values():
        schema.structure_index(type_name)
    return schema


def _field_size(schema: SDNASchema, field: SDNAField, pointer_size: int) -> int:
    name = schema.names[field.name_index]
    element = pointer_size if _is_pointer_declaration(name) else schema.type_lengths[field.type_index]
    return element * _array_multiplier(name)


@lru_cache(maxsize=4096)
def _structure_alignment_cached(
    names: tuple[str, ...],
    type_lengths: tuple[int, ...],
    structures_key: tuple[tuple[int, tuple[tuple[int, int], ...]], ...],
    types: tuple[str, ...],
    structure_index: int,
    pointer_size: int,
) -> int:
    del names, type_lengths, structures_key, types, structure_index, pointer_size
    # The real work lives in _structure_alignment.  This cache placeholder is
    # intentionally not called directly; keeping the public implementation
    # simple avoids recursive-cache key construction in hot paths.
    raise AssertionError("internal cache placeholder")


def _structure_alignment(
    schema: SDNASchema,
    structure_index: int,
    pointer_size: int,
    active: set[int] | None = None,
) -> int:
    active = set() if active is None else set(active)
    if structure_index in active:
        raise TypedBlendError("recursive inline SDNA structure")
    active.add(structure_index)
    structure = schema.structures[structure_index]
    by_type = {item.type_index: index for index, item in enumerate(schema.structures)}
    result = 1
    for field in structure.fields:
        name = schema.names[field.name_index]
        if _is_pointer_declaration(name):
            alignment = pointer_size
        elif field.type_index in by_type:
            alignment = _structure_alignment(schema, by_type[field.type_index], pointer_size, active)
        else:
            size = schema.type_lengths[field.type_index]
            alignment = max(1, min(size, pointer_size))
        result = max(result, alignment)
    return min(result, pointer_size)


def structure_layout(
    schema: SDNASchema, structure_index: int, pointer_size: int
) -> tuple[list[tuple[SDNAField, int, int]], int]:
    structure = schema.structures[structure_index]
    by_type = {item.type_index: index for index, item in enumerate(schema.structures)}
    offset = 0
    rows: list[tuple[SDNAField, int, int]] = []
    for field in structure.fields:
        name = schema.names[field.name_index]
        size = _field_size(schema, field, pointer_size)
        if _is_pointer_declaration(name):
            alignment = pointer_size
        elif field.type_index in by_type:
            alignment = _structure_alignment(schema, by_type[field.type_index], pointer_size)
        else:
            alignment = max(1, min(schema.type_lengths[field.type_index], pointer_size))
        offset = _align(offset, alignment)
        rows.append((field, offset, size))
        offset += size
    total = _align(offset, _structure_alignment(schema, structure_index, pointer_size))
    declared = schema.type_lengths[structure.type_index]
    if total > declared:
        raise TypedBlendError("computed SDNA layout exceeds declared TLEN")
    return rows, declared


def typed_id_name(
    schema: SDNASchema,
    block: BlendBlock,
    pointer_size: int,
) -> str:
    if block.payload is None:
        raise TypedBlendError("semantic block payload was not retained")
    expected_type = CODE_TO_STRUCTURE.get(block.code)
    if expected_type is None or schema.structure_type(block.sdna_index) != expected_type:
        raise TypedBlendError("semantic block code and SDNA type disagree")
    top_layout, top_size = structure_layout(schema, block.sdna_index, pointer_size)
    if block.count != 1 or block.length != top_size:
        raise TypedBlendError("semantic block count/length does not equal one typed structure")
    id_fields = [
        (field, offset)
        for field, offset, _ in top_layout
        if schema.types[field.type_index] == "ID"
        and schema.names[field.name_index].split("[")[0] == "id"
        and not _is_pointer_declaration(schema.names[field.name_index])
    ]
    if len(id_fields) != 1:
        raise TypedBlendError("semantic structure lacks one inline typed ID field")
    _, id_offset = id_fields[0]
    id_index = schema.structure_index("ID")
    id_layout, _ = structure_layout(schema, id_index, pointer_size)
    name_fields = [
        (field, offset, size)
        for field, offset, size in id_layout
        if schema.names[field.name_index].startswith("name[")
        and schema.types[field.type_index] == "char"
        and not _is_pointer_declaration(schema.names[field.name_index])
    ]
    if len(name_fields) != 1:
        raise TypedBlendError("ID structure lacks one typed char name array")
    _, name_offset, name_size = name_fields[0]
    raw = block.payload[id_offset + name_offset : id_offset + name_offset + name_size]
    if len(raw) != name_size:
        raise TypedBlendError("typed ID.name lies outside block payload")
    value = raw.split(b"\x00", 1)[0]
    try:
        full_name = value.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise TypedBlendError("typed ID.name is not UTF-8") from exc
    if not full_name.startswith(block.code) or len(full_name) <= len(block.code):
        raise TypedBlendError("typed ID.name prefix does not match block code")
    return full_name[len(block.code) :]


def id_user_count_normalized_block_sha256(
    schema: SDNASchema,
    block: BlendBlock,
    pointer_size: int,
) -> str:
    """Hash a semantic block after zeroing only its typed inline ``ID.us``.

    Adding the detached R24 proof object creates one additional legitimate
    Material user.  No other Material payload byte is normalized, and AR/AC
    gates continue to use the raw direct-block digest.
    """
    if block.payload is None:
        raise TypedBlendError("semantic block payload was not retained")
    top_layout, _ = structure_layout(schema, block.sdna_index, pointer_size)
    id_fields = [
        (field, offset)
        for field, offset, _ in top_layout
        if schema.types[field.type_index] == "ID"
        and schema.names[field.name_index].split("[")[0] == "id"
        and not _is_pointer_declaration(schema.names[field.name_index])
    ]
    if len(id_fields) != 1:
        raise TypedBlendError("semantic structure lacks one inline typed ID field")
    _, id_offset = id_fields[0]
    id_index = schema.structure_index("ID")
    id_layout, _ = structure_layout(schema, id_index, pointer_size)
    user_fields = [
        (offset, size)
        for field, offset, size in id_layout
        if schema.names[field.name_index].split("[")[0].lstrip("*") == "us"
        and not _is_pointer_declaration(schema.names[field.name_index])
        and _array_multiplier(schema.names[field.name_index]) == 1
    ]
    # Minimal typed fixtures intentionally model only ID.name.  They remain
    # structurally useful negative tests; a real bound Material must expose us
    # and its normalized digest will therefore differ from a schema that does
    # not contain that typed field.
    if not user_fields:
        return hashlib.sha256(block.payload).hexdigest()
    if len(user_fields) != 1:
        raise TypedBlendError("ID has an ambiguous typed user-count field")
    user_offset, user_size = user_fields[0]
    start = id_offset + user_offset
    end = start + user_size
    if start < 0 or end > len(block.payload) or user_size not in {1, 2, 4, 8}:
        raise TypedBlendError("typed ID.us lies outside block payload")
    normalized = bytearray(block.payload)
    normalized[start:end] = b"\x00" * user_size
    return hashlib.sha256(normalized).hexdigest()


def _header_and_reader(stream: BinaryIO):
    header17 = stream.read(17)
    if header17.startswith(b"BLENDER17-"):
        if len(header17) != 17 or header17[10:12] != b"01" or header17[12:13] not in (b"v", b"V"):
            raise TypedBlendError("invalid extended Blender header")
        if not header17[13:17].isdigit():
            raise TypedBlendError("invalid extended Blender version")
        endian = "<" if header17[12:13] == b"v" else ">"
        pointer_size = 8

        def read_header() -> tuple[bytes, int, int, int, int] | None:
            raw = stream.read(32)
            if not raw:
                return None
            if len(raw) != 32:
                raise TypedBlendError("truncated extended block header")
            code, sdna, old_address, length, count = struct.unpack(endian + "4sIQQQ", raw)
            return code, length, old_address, sdna, count

        return header17, endian, pointer_size, read_header

    header = header17[:12]
    if (
        len(header) != 12
        or header[:7] != b"BLENDER"
        or header[7:8] not in (b"-", b"_")
        or header[8:9] not in (b"v", b"V")
        or not header[9:12].isdigit()
    ):
        raise TypedBlendError("invalid classic Blender header")
    stream.seek(12)
    endian = "<" if header[8:9] == b"v" else ">"
    pointer_size = 8 if header[7:8] == b"-" else 4
    fmt = endian + ("4sIQII" if pointer_size == 8 else "4sIIII")
    size = struct.calcsize(fmt)

    def read_header() -> tuple[bytes, int, int, int, int] | None:
        raw = stream.read(size)
        if not raw:
            return None
        if len(raw) != size:
            raise TypedBlendError("truncated classic block header")
        code, length, old_address, sdna, count = struct.unpack(fmt, raw)
        return code, length, old_address, sdna, count

    return header, endian, pointer_size, read_header


def parse_typed_blend(path: Path) -> dict[str, object]:
    """Parse and type-check semantic blocks without using Blender."""
    stream, compressed = _open_blend_stream(path)
    retained: list[BlendBlock] = []
    all_meta: list[BlendBlock] = []
    dna_payload: bytes | None = None
    ended = False
    with stream:
        header, endian, pointer_size, read_header = _header_and_reader(stream)
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
    schema = parse_sdna(dna_payload, endian)
    semantic: dict[str, list[dict[str, object]]] = {code: [] for code in CODE_TO_STRUCTURE}
    semantic_addresses: set[int] = set()
    for block in retained:
        if block.old_address <= 0 or block.old_address in semantic_addresses:
            raise TypedBlendError("semantic datablock has a null or duplicate old-address pointer")
        semantic_addresses.add(block.old_address)
        name = typed_id_name(schema, block, pointer_size)
        semantic[block.code].append(
            {
                "name": name,
                "sdna_index": block.sdna_index,
                "sdna_type": schema.structure_type(block.sdna_index),
                "count": block.count,
                "bytes": block.length,
                "direct_block_sha256": hashlib.sha256(block.payload or b"").hexdigest(),
                "id_user_count_normalized_block_sha256": id_user_count_normalized_block_sha256(
                    schema, block, pointer_size
                ),
            }
        )
    for code, records in semantic.items():
        if not records:
            raise TypedBlendError(f"Blend lacks typed {code} datablock")
        records.sort(key=lambda row: str(row["name"]))
    block_counts: dict[str, int] = {}
    for block in all_meta:
        block_counts[block.code] = block_counts.get(block.code, 0) + 1
    return {
        "schema": "kira.avatar.r24.typed_blend_preflight.v4",
        "compressed_zstd": compressed,
        "header": header.decode("ascii"),
        "pointer_size": pointer_size,
        "endian": "little" if endian == "<" else "big",
        "block_count": len(all_meta),
        "block_counts": {key: block_counts[key] for key in sorted(block_counts)},
        "dna": {
            "name_count": len(schema.names),
            "type_count": len(schema.types),
            "structure_count": len(schema.structures),
        },
        "semantic_ids": semantic,
    }


def semantic_names(summary: dict[str, object], code: str) -> set[str]:
    raw = summary.get("semantic_ids")
    if not isinstance(raw, dict) or not isinstance(raw.get(code), list):
        return set()
    return {
        str(row.get("name"))
        for row in raw[code]
        if isinstance(row, dict) and isinstance(row.get("name"), str)
    }


def iter_semantic_blocks(path: Path) -> Iterable[dict[str, object]]:
    summary = parse_typed_blend(path)
    semantic = summary["semantic_ids"]
    for code in sorted(semantic):
        yield from semantic[code]
