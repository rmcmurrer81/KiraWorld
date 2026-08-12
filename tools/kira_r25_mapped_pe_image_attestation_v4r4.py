#!/usr/bin/env python3
from __future__ import annotations

"""Pure PE64 parsing and relocation-aware mapped-image attestation for R25 04r4.

This module does not open processes, read project inputs, import Blender, or
write evidence.  Its caller supplies the exact held executable bytes, the
loader-observed module facts, and a function that reads the live module by
RVA.  Only immutable headers, executable sections, and non-discardable
read-only sections are authority-bearing.  Declared base relocations are the
only byte transformation allowed in those regions.
"""

import hashlib
import json
import struct


ATTESTATION_SCHEMA = "kira.avatar.r25.mapped_pe_image_attestation.v4r4"
ATTESTATION_STATUS = "LIVE_MAPPED_PE_AUTHORITY_REGIONS_EQUAL_EXACT_HELD_IMAGE"
PE_MACHINE_AMD64 = 0x8664
PE32_PLUS_MAGIC = 0x20B
IMAGE_FILE_EXECUTABLE_IMAGE = 0x0002
IMAGE_FILE_DLL = 0x2000
IMAGE_SCN_MEM_DISCARDABLE = 0x02000000
IMAGE_SCN_MEM_EXECUTE = 0x20000000
IMAGE_SCN_MEM_READ = 0x40000000
IMAGE_SCN_MEM_WRITE = 0x80000000
IMAGE_DIRECTORY_ENTRY_IMPORT = 1
IMAGE_DIRECTORY_ENTRY_SECURITY = 4
IMAGE_DIRECTORY_ENTRY_BASERELOC = 5
IMAGE_DIRECTORY_ENTRY_TLS = 9
IMAGE_DIRECTORY_ENTRY_IAT = 12
IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT = 13
IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR = 14
IMAGE_REL_BASED_ABSOLUTE = 0
IMAGE_REL_BASED_DIR64 = 10
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_IMAGE_BYTES = 512 * 1024 * 1024
MAX_SECTIONS = 64


class MappedPeAttestationV4R4Error(RuntimeError):
    pass


def _fail(reason):
    raise MappedPeAttestationV4R4Error(reason)


def _sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical_json_bytes(value):
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _hex64(value):
    return type(value) is str and len(value) == 64 and all(
        "0" <= character <= "9" or "a" <= character <= "f"
        for character in value
    )


def _power_of_two(value):
    return type(value) is int and value > 0 and value & (value - 1) == 0


def _align_up(value, alignment):
    if not _power_of_two(alignment) or type(value) is not int or value < 0:
        _fail("pe_alignment_arithmetic_invalid")
    return (value + alignment - 1) & ~(alignment - 1)


def _take(raw, offset, count, label):
    if (
        type(raw) is not bytes or type(offset) is not int or type(count) is not int
        or offset < 0 or count < 0 or offset + count > len(raw)
    ):
        _fail("pe_truncated:" + label)
    return raw[offset:offset + count]


def _unpack(raw, offset, format_text, label):
    size = struct.calcsize(format_text)
    return struct.unpack(format_text, _take(raw, offset, size, label))


def _section_for_range(sections, rva, size, *, require_raw=False):
    if type(rva) is not int or type(size) is not int or rva < 0 or size <= 0:
        return None
    end = rva + size
    for section in sections:
        span = section["raw_size"] if require_raw else section["mapped_size"]
        if section["virtual_address"] <= rva and end <= section["virtual_address"] + span:
            return section
    return None


def _rva_to_raw(plan, rva, size, label):
    if 0 <= rva and rva + size <= plan["size_of_headers"]:
        return rva
    section = _section_for_range(plan["sections"], rva, size, require_raw=True)
    if section is None:
        _fail("pe_rva_has_no_file_backing:" + label)
    offset = section["raw_pointer"] + rva - section["virtual_address"]
    if offset + size > plan["file_bytes"]:
        _fail("pe_rva_file_backing_truncated:" + label)
    return offset


def _directory(plan, index):
    return plan["data_directories"][index]


def _validate_loader_mutable_ranges(raw, plan):
    ranges = []

    import_rva, import_size = _directory(plan, IMAGE_DIRECTORY_ENTRY_IMPORT)
    iat_rva, iat_size = _directory(plan, IMAGE_DIRECTORY_ENTRY_IAT)
    if (import_rva == 0) != (import_size == 0):
        _fail("pe_import_directory_partial")
    if (iat_rva == 0) != (iat_size == 0):
        _fail("pe_iat_directory_partial")
    if import_rva and not iat_rva:
        _fail("pe_imports_without_accounted_iat_range")
    if iat_rva:
        section = _section_for_range(plan["sections"], iat_rva, iat_size)
        if section is None:
            _fail("pe_iat_outside_section")
        flags = section["characteristics"]
        if not flags & IMAGE_SCN_MEM_WRITE or flags & IMAGE_SCN_MEM_EXECUTE:
            _fail("pe_iat_not_in_nonexecutable_writable_section")
        if section["authority_bearing"]:
            _fail("pe_iat_overlaps_compared_authority_section")
        ranges.append({
            "kind": "IMPORT_ADDRESS_TABLE", "rva": iat_rva,
            "size": iat_size, "section_name_hex": section["name_hex"],
        })

    delay_rva, delay_size = _directory(plan, IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT)
    if delay_rva or delay_size:
        _fail("pe_delay_import_loader_mutation_not_supported")
    clr_rva, clr_size = _directory(plan, IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR)
    if clr_rva or clr_size:
        _fail("pe_managed_image_not_supported")

    tls_rva, tls_size = _directory(plan, IMAGE_DIRECTORY_ENTRY_TLS)
    if (tls_rva == 0) != (tls_size == 0):
        _fail("pe_tls_directory_partial")
    if tls_rva:
        if tls_size < 40:
            _fail("pe_tls_directory_too_small")
        tls_offset = _rva_to_raw(plan, tls_rva, 40, "tls_directory")
        address_of_index = _unpack(raw, tls_offset + 16, "<Q", "tls_address_of_index")[0]
        if address_of_index:
            if address_of_index < plan["preferred_image_base"]:
                _fail("pe_tls_index_va_before_image")
            index_rva = address_of_index - plan["preferred_image_base"]
            section = _section_for_range(plan["sections"], index_rva, 4)
            if section is None:
                _fail("pe_tls_index_outside_section")
            flags = section["characteristics"]
            if not flags & IMAGE_SCN_MEM_WRITE or flags & IMAGE_SCN_MEM_EXECUTE:
                _fail("pe_tls_index_not_in_nonexecutable_writable_section")
            if section["authority_bearing"]:
                _fail("pe_tls_index_overlaps_compared_authority_section")
            ranges.append({
                "kind": "TLS_INDEX", "rva": index_rva, "size": 4,
                "section_name_hex": section["name_hex"],
            })
    ranges.sort(key=lambda row: (row["rva"], row["size"], row["kind"]))
    for left, right in zip(ranges, ranges[1:]):
        if left["rva"] + left["size"] > right["rva"]:
            _fail("pe_loader_mutable_ranges_overlap")
    return ranges


def _parse_base_relocations(raw, plan):
    directory_rva, directory_size = _directory(plan, IMAGE_DIRECTORY_ENTRY_BASERELOC)
    if (directory_rva == 0) != (directory_size == 0):
        _fail("pe_base_relocation_directory_partial")
    if not directory_rva:
        return []
    directory_section = _section_for_range(
        plan["sections"], directory_rva, directory_size
    )
    if directory_section is None:
        _fail("pe_base_relocation_directory_outside_section")
    directory_flags = directory_section["characteristics"]
    if directory_flags & (IMAGE_SCN_MEM_EXECUTE | IMAGE_SCN_MEM_WRITE):
        _fail("pe_base_relocation_directory_in_mutable_or_executable_section")
    directory_offset = _rva_to_raw(
        plan, directory_rva, directory_size, "base_relocation_directory"
    )
    data = _take(raw, directory_offset, directory_size, "base_relocation_directory")
    cursor = 0
    relocations = []
    targets = set()
    while cursor < len(data):
        remaining = data[cursor:]
        if remaining and not any(remaining):
            break
        if len(remaining) < 8:
            _fail("pe_base_relocation_block_header_truncated")
        page_rva, block_size = struct.unpack("<II", remaining[:8])
        if block_size < 8 or block_size > len(remaining) or (block_size - 8) % 2:
            _fail("pe_base_relocation_block_size_invalid")
        entries = struct.unpack(
            "<" + "H" * ((block_size - 8) // 2), remaining[8:block_size]
        )
        for encoded in entries:
            kind, offset = encoded >> 12, encoded & 0x0FFF
            if kind == IMAGE_REL_BASED_ABSOLUTE:
                continue
            if kind != IMAGE_REL_BASED_DIR64:
                _fail("pe_unsupported_base_relocation_type:" + str(kind))
            target_rva = page_rva + offset
            section = _section_for_range(plan["sections"], target_rva, 8)
            if section is None:
                _fail("pe_base_relocation_target_outside_section")
            if not (
                target_rva + 8 <= directory_rva
                or directory_rva + directory_size <= target_rva
            ):
                _fail("pe_base_relocation_target_overlaps_relocation_directory")
            for mutable in plan["loader_mutable_ranges"]:
                if not (
                    target_rva + 8 <= mutable["rva"]
                    or mutable["rva"] + mutable["size"] <= target_rva
                ):
                    _fail("pe_base_relocation_target_overlaps_loader_mutable_range")
            if target_rva in targets:
                _fail("pe_duplicate_base_relocation_target")
            targets.add(target_rva)
            relocations.append({"rva": target_rva, "type": kind, "width": 8})
        cursor += block_size
    relocations.sort(key=lambda row: row["rva"])
    for left, right in zip(relocations, relocations[1:]):
        if left["rva"] + left["width"] > right["rva"]:
            _fail("pe_overlapping_base_relocation_targets")
    return relocations


def _parse_pe64(raw):
    if type(raw) is not bytes or not 512 <= len(raw) <= MAX_FILE_BYTES:
        _fail("pe_file_byte_length_invalid")
    if _take(raw, 0, 2, "dos_magic") != b"MZ":
        _fail("pe_dos_magic_invalid")
    pe_offset = _unpack(raw, 0x3C, "<I", "pe_offset")[0]
    if pe_offset < 0x40 or pe_offset > min(len(raw) - 24, 1024 * 1024):
        _fail("pe_header_offset_invalid")
    if _take(raw, pe_offset, 4, "pe_signature") != b"PE\x00\x00":
        _fail("pe_signature_invalid")
    coff = pe_offset + 4
    machine, section_count, _, _, _, optional_size, characteristics = _unpack(
        raw, coff, "<HHIIIHH", "coff_header"
    )
    if machine != PE_MACHINE_AMD64:
        _fail("pe_machine_not_amd64")
    if not 1 <= section_count <= MAX_SECTIONS:
        _fail("pe_section_count_invalid")
    if not characteristics & IMAGE_FILE_EXECUTABLE_IMAGE or characteristics & IMAGE_FILE_DLL:
        _fail("pe_not_native_executable_image")
    optional = coff + 20
    if optional_size < 240 or optional + optional_size > len(raw):
        _fail("pe_optional_header_size_invalid")
    if _unpack(raw, optional, "<H", "optional_magic")[0] != PE32_PLUS_MAGIC:
        _fail("pe_optional_magic_not_pe32_plus")
    entry_rva = _unpack(raw, optional + 16, "<I", "entry_point_rva")[0]
    preferred_base = _unpack(raw, optional + 24, "<Q", "image_base")[0]
    section_alignment, file_alignment = _unpack(
        raw, optional + 32, "<II", "image_alignments"
    )
    size_of_image, size_of_headers = _unpack(
        raw, optional + 56, "<II", "image_sizes"
    )
    number_of_directories = _unpack(
        raw, optional + 108, "<I", "directory_count"
    )[0]
    if preferred_base == 0 or preferred_base % 0x10000:
        _fail("pe_preferred_image_base_invalid")
    if not _power_of_two(section_alignment) or not 4096 <= section_alignment <= 1024 * 1024:
        _fail("pe_section_alignment_invalid")
    if not _power_of_two(file_alignment) or not 512 <= file_alignment <= 65536:
        _fail("pe_file_alignment_invalid")
    if file_alignment > section_alignment:
        _fail("pe_file_alignment_exceeds_section_alignment")
    if not 16 <= number_of_directories <= 64:
        _fail("pe_data_directory_count_invalid")
    directory_end = optional + 112 + number_of_directories * 8
    if directory_end > optional + optional_size:
        _fail("pe_data_directories_truncated")
    section_table = optional + optional_size
    section_table_end = section_table + section_count * 40
    if (
        size_of_headers < section_table_end or size_of_headers > len(raw)
        or size_of_headers % file_alignment
    ):
        _fail("pe_size_of_headers_invalid")
    if (
        size_of_image <= size_of_headers or size_of_image > MAX_IMAGE_BYTES
        or size_of_image % section_alignment
    ):
        _fail("pe_size_of_image_invalid")

    data_directories = [
        _unpack(raw, optional + 112 + index * 8, "<II", "data_directory")[0:2]
        for index in range(16)
    ]
    sections = []
    for index in range(section_count):
        offset = section_table + index * 40
        name = _take(raw, offset, 8, "section_name").rstrip(b"\x00")
        virtual_size, virtual_address, raw_size, raw_pointer = _unpack(
            raw, offset + 8, "<IIII", "section_layout"
        )
        section_characteristics = _unpack(
            raw, offset + 36, "<I", "section_characteristics"
        )[0]
        if not name or len(name) > 8:
            _fail("pe_section_name_invalid")
        declared_size = max(virtual_size, raw_size)
        if declared_size <= 0 or virtual_address % section_alignment:
            _fail("pe_section_virtual_layout_invalid")
        mapped_size = _align_up(declared_size, section_alignment)
        if virtual_address < _align_up(size_of_headers, section_alignment):
            _fail("pe_section_overlaps_headers")
        if virtual_address + mapped_size > size_of_image:
            _fail("pe_section_exceeds_image")
        if raw_size:
            if raw_pointer < size_of_headers or raw_pointer % file_alignment:
                _fail("pe_section_raw_pointer_invalid")
            if raw_size % file_alignment or raw_pointer + raw_size > len(raw):
                _fail("pe_section_raw_layout_invalid")
        execute = bool(section_characteristics & IMAGE_SCN_MEM_EXECUTE)
        write = bool(section_characteristics & IMAGE_SCN_MEM_WRITE)
        read = bool(section_characteristics & IMAGE_SCN_MEM_READ)
        discardable = bool(section_characteristics & IMAGE_SCN_MEM_DISCARDABLE)
        if execute and write:
            _fail("pe_writable_executable_section_refused")
        if execute and discardable:
            _fail("pe_discardable_executable_section_refused")
        authority = execute or (read and not write and not discardable)
        sections.append({
            "index": index, "name_hex": name.hex(),
            "virtual_size": virtual_size, "virtual_address": virtual_address,
            "raw_size": raw_size, "raw_pointer": raw_pointer,
            "mapped_size": mapped_size, "characteristics": section_characteristics,
            "authority_bearing": authority,
        })
    sections.sort(key=lambda row: row["virtual_address"])
    for left, right in zip(sections, sections[1:]):
        if left["virtual_address"] + left["mapped_size"] > right["virtual_address"]:
            _fail("pe_virtual_sections_overlap")
    raw_sections = sorted(
        (section for section in sections if section["raw_size"]),
        key=lambda row: row["raw_pointer"],
    )
    for left, right in zip(raw_sections, raw_sections[1:]):
        if left["raw_pointer"] + left["raw_size"] > right["raw_pointer"]:
            _fail("pe_raw_sections_overlap")
    entry_section = _section_for_range(sections, entry_rva, 1)
    if entry_section is None or not entry_section["authority_bearing"]:
        _fail("pe_entry_point_not_in_authority_section")
    entry_flags = entry_section["characteristics"]
    if not entry_flags & IMAGE_SCN_MEM_EXECUTE or entry_flags & IMAGE_SCN_MEM_WRITE:
        _fail("pe_entry_point_not_in_nonwritable_executable_section")

    plan = {
        "file_bytes": len(raw), "file_sha256": _sha256(raw),
        "machine": machine, "pe_format": "PE32_PLUS_AMD64",
        "preferred_image_base": preferred_base,
        "entry_point_rva": entry_rva, "size_of_image": size_of_image,
        "size_of_headers": size_of_headers,
        "section_alignment": section_alignment, "file_alignment": file_alignment,
        "sections": sections, "data_directories": data_directories,
    }
    for index, (directory_rva, directory_size) in enumerate(data_directories):
        if (directory_rva == 0) != (directory_size == 0):
            _fail("pe_data_directory_partial:" + str(index))
        if not directory_rva:
            continue
        if index == IMAGE_DIRECTORY_ENTRY_SECURITY:
            if directory_rva + directory_size > len(raw):
                _fail("pe_security_directory_outside_file")
            continue
        if directory_rva + directory_size > size_of_image:
            _fail("pe_data_directory_outside_image:" + str(index))
        if directory_rva + directory_size <= size_of_headers:
            continue
        if _section_for_range(
            sections, directory_rva, directory_size, require_raw=True
        ) is None:
            _fail("pe_data_directory_without_file_backing:" + str(index))
    plan["loader_mutable_ranges"] = _validate_loader_mutable_ranges(raw, plan)
    plan["base_relocations"] = _parse_base_relocations(raw, plan)
    return plan


def _expected_region_bytes(raw, plan, rva, size, relocation_delta):
    if rva == 0:
        expected = bytearray(_take(raw, 0, size, "expected_headers"))
    else:
        section = _section_for_range(plan["sections"], rva, size)
        if section is None or section["virtual_address"] != rva:
            _fail("expected_region_not_exact_section")
        expected = bytearray(size)
        copied = min(section["raw_size"], size)
        if copied:
            expected[:copied] = _take(
                raw, section["raw_pointer"], copied, "expected_section_raw"
            )
    region_end = rva + size
    for relocation in plan["base_relocations"]:
        target = relocation["rva"]
        if rva <= target and target + 8 <= region_end:
            local = target - rva
            original = struct.unpack_from("<Q", expected, local)[0]
            struct.pack_into("<Q", expected, local, (original + relocation_delta) & ((1 << 64) - 1))
    return bytes(expected)


def _attest_loaded_main_image(
    held_file_raw, *, remote_module_base, module_size_of_image,
    module_entry_point, remote_reader,
):
    plan = _parse_pe64(held_file_raw)
    integers = (remote_module_base, module_size_of_image, module_entry_point)
    if not all(type(value) is int and value > 0 for value in integers):
        _fail("remote_module_facts_invalid")
    if remote_module_base % 0x10000:
        _fail("remote_module_base_unaligned")
    if module_size_of_image != plan["size_of_image"]:
        _fail("remote_module_size_of_image_mismatch")
    expected_entry = remote_module_base + plan["entry_point_rva"]
    if module_entry_point != expected_entry:
        _fail("remote_module_entry_point_mismatch")
    relocation_delta = remote_module_base - plan["preferred_image_base"]
    if relocation_delta and not plan["base_relocations"]:
        _fail("remote_module_relocated_without_declared_base_relocations")
    if not callable(remote_reader):
        _fail("remote_reader_not_callable")

    region_specs = [{
        "kind": "PE_HEADERS", "name_hex": "", "rva": 0,
        "size": plan["size_of_headers"],
    }]
    for section in plan["sections"]:
        if section["authority_bearing"]:
            region_specs.append({
                "kind": "AUTHORITY_SECTION", "name_hex": section["name_hex"],
                "rva": section["virtual_address"], "size": section["mapped_size"],
            })
    if len(region_specs) < 2:
        _fail("pe_has_no_authority_section")
    region_manifest = []
    total = 0
    for spec in region_specs:
        expected = _expected_region_bytes(
            held_file_raw, plan, spec["rva"], spec["size"], relocation_delta
        )
        observed = remote_reader(spec["rva"], spec["size"])
        if type(observed) is not bytes or len(observed) != spec["size"]:
            _fail("remote_authority_region_read_invalid")
        if observed != expected:
            _fail(
                "mapped_authority_region_bytes_mismatch:rva="
                + format(spec["rva"], "x")
            )
        row = dict(spec)
        row["sha256"] = _sha256(observed)
        region_manifest.append(row)
        total += len(observed)

    relocation_manifest = plan["base_relocations"]
    mutable_manifest = plan["loader_mutable_ranges"]
    attestation = {
        "schema": ATTESTATION_SCHEMA, "status": ATTESTATION_STATUS,
        "pe_machine": plan["machine"], "pe_format": plan["pe_format"],
        "held_file_sha256": plan["file_sha256"],
        "preferred_image_base": plan["preferred_image_base"],
        "remote_module_base": remote_module_base,
        "size_of_image": plan["size_of_image"],
        "entry_point_rva": plan["entry_point_rva"],
        "remote_entry_point": module_entry_point,
        "relocation_delta": relocation_delta,
        "base_relocation_count": len(relocation_manifest),
        "base_relocation_manifest_sha256": _sha256(
            _canonical_json_bytes(relocation_manifest)
        ),
        "compared_region_count": len(region_manifest),
        "compared_region_bytes": total,
        "compared_region_manifest_sha256": _sha256(
            _canonical_json_bytes(region_manifest)
        ),
        "loader_mutable_range_count": len(mutable_manifest),
        "loader_mutable_range_manifest_sha256": _sha256(
            _canonical_json_bytes(mutable_manifest)
        ),
        "writable_executable_section_count": 0,
    }
    attestation["attestation_content_sha256"] = _sha256(
        _canonical_json_bytes(attestation)
    )
    return attestation


def _validate_attestation_shape(attestation, expected_held_sha256):
    keys = {
        "schema", "status", "pe_machine", "pe_format", "held_file_sha256",
        "preferred_image_base", "remote_module_base", "size_of_image",
        "entry_point_rva", "remote_entry_point", "relocation_delta",
        "base_relocation_count", "base_relocation_manifest_sha256",
        "compared_region_count", "compared_region_bytes",
        "compared_region_manifest_sha256", "loader_mutable_range_count",
        "loader_mutable_range_manifest_sha256",
        "writable_executable_section_count", "attestation_content_sha256",
    }
    if type(attestation) is not dict or set(attestation) != keys:
        _fail("mapped_image_attestation_shape_drift")
    if attestation["schema"] != ATTESTATION_SCHEMA or attestation["status"] != ATTESTATION_STATUS:
        _fail("mapped_image_attestation_identity_drift")
    if attestation["pe_machine"] != PE_MACHINE_AMD64 or attestation["pe_format"] != "PE32_PLUS_AMD64":
        _fail("mapped_image_attestation_pe_identity_drift")
    if not _hex64(expected_held_sha256) or attestation["held_file_sha256"] != expected_held_sha256:
        _fail("mapped_image_attestation_held_sha256_mismatch")
    for key in (
        "base_relocation_manifest_sha256", "compared_region_manifest_sha256",
        "loader_mutable_range_manifest_sha256", "attestation_content_sha256",
    ):
        if not _hex64(attestation[key]):
            _fail("mapped_image_attestation_digest_invalid:" + key)
    for key in (
        "preferred_image_base", "remote_module_base", "size_of_image",
        "entry_point_rva", "remote_entry_point", "base_relocation_count",
        "compared_region_count", "compared_region_bytes",
        "loader_mutable_range_count", "writable_executable_section_count",
    ):
        if type(attestation[key]) is not int or attestation[key] < 0:
            _fail("mapped_image_attestation_integer_invalid:" + key)
    if type(attestation["relocation_delta"]) is not int:
        _fail("mapped_image_attestation_integer_invalid:relocation_delta")
    if (
        attestation["preferred_image_base"] <= 0
        or attestation["remote_module_base"] <= 0
        or attestation["size_of_image"] <= 0
        or attestation["entry_point_rva"] <= 0
        or attestation["remote_entry_point"]
        != attestation["remote_module_base"] + attestation["entry_point_rva"]
        or attestation["relocation_delta"]
        != attestation["remote_module_base"] - attestation["preferred_image_base"]
    ):
        _fail("mapped_image_attestation_module_facts_inconsistent")
    if attestation["compared_region_count"] < 2 or attestation["compared_region_bytes"] <= 0:
        _fail("mapped_image_attestation_compared_region_claim_invalid")
    if attestation["writable_executable_section_count"] != 0:
        _fail("mapped_image_attestation_writable_executable_claim")
    content = dict(attestation)
    claimed = content.pop("attestation_content_sha256")
    if _sha256(_canonical_json_bytes(content)) != claimed:
        _fail("mapped_image_attestation_content_sha256_mismatch")
    return attestation
