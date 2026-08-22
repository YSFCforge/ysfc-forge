#!/usr/bin/env python3
# RECOVERY CHECKPOINT 2026-08-21 / SysEx Converter v1.21
# The standalone HTML app is the authoritative production runtime for
# Soundmondo SysEx -> MODX M Y2L conversion at this checkpoint.
# Keep fail-closed behavior: do not invent missing source blocks,
# external waveform/Arp dependencies, or unverified mappings.
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Any

YAMAHA_ID = 0x43
GROUP_HIGH = 0x7F
GROUP_LOW = 0x1C
HERE = Path(__file__).resolve().parent
DEFAULT_TABLES = {
    "legacy": HERE / "legacy_bulk_blocks.json",
    "m_generation": HERE / "m_generation_bulk_blocks.json",
}
DEFAULT_PARAMETER_MAP = HERE / "normalized_parameter_map.json"
DEFAULT_EFFECT_TYPE_MAP = HERE / "effect_type_map.json"


@dataclass(frozen=True)
class ProtocolProfile:
    model_id: int
    name: str
    address_len: int
    table_key: str


PROFILES = {
    0x02: ProtocolProfile(0x02, "MONTAGE", 3, "legacy"),
    0x07: ProtocolProfile(0x07, "MODX/MODX+", 3, "legacy"),
    0x0D: ProtocolProfile(0x0D, "MONTAGE M/MODX M", 4, "m_generation"),
}


class SysExParseError(ValueError):
    pass


def split_sysex_stream(raw: bytes) -> tuple[list[bytes], list[str]]:
    messages: list[bytes] = []
    warnings: list[str] = []
    start = None
    for i, b in enumerate(raw):
        if b == 0xF0:
            if start is not None:
                warnings.append(f"Nested F0 at offset {i}; discarding unterminated message from {start}")
            start = i
        elif b == 0xF7:
            if start is None:
                warnings.append(f"Stray F7 at offset {i}")
            else:
                messages.append(raw[start:i + 1])
                start = None
        elif start is None and b not in (0x00, 0x0A, 0x0D, 0x20, 0x09):
            warnings.append(f"Non-SysEx byte 0x{b:02X} outside message at offset {i}")
    if start is not None:
        warnings.append(f"Unterminated SysEx message starting at offset {start}")
    return messages, warnings


def checksum_ok(model_id: int, address: bytes, data: bytes, checksum: int) -> bool:
    return ((model_id + sum(address) + sum(data) + checksum) & 0x7F) == 0


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_block_tables(paths: dict[str, Path] | None = None) -> dict[str, dict[str, Any]]:
    paths = paths or DEFAULT_TABLES
    return {key: load_json(path) for key, path in paths.items()}




def load_parameter_map(path: Path | None = None) -> dict[str, Any]:
    return load_json(path or DEFAULT_PARAMETER_MAP)


def load_effect_type_map(path: Path | None = None) -> dict[str, Any]:
    return load_json(path or DEFAULT_EFFECT_TYPE_MAP)


def u14(raw: bytes) -> int:
    if len(raw) != 2:
        raise ValueError("u14 requires exactly two 7-bit bytes")
    return (raw[0] << 7) | raw[1]


def midi_note_name(value: int) -> str:
    names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    return f"{names[value % 12]}{value // 12 - 2}"


def decode_normalized_value(raw: bytes, codec: str) -> Any:
    if codec == "ascii":
        return decode_ascii(raw)
    if codec == "u7":
        return raw[0]
    if codec == "u14":
        return u14(raw)
    if codec == "bool":
        return bool(raw[0])
    if codec == "pan_l63_r63":
        return raw[0] - 64
    if codec == "pan_u14_l63_r63":
        return u14(raw) - 64
    if codec == "note":
        return raw[0]
    if codec == "note_u14":
        return u14(raw)
    if codec == "part_mode":
        return {0: "internal", 1: "external"}.get(raw[0], f"unknown:{raw[0]}")
    if codec == "u7_center64":
        return raw[0] - 64
    if codec == "u14_center64":
        return u14(raw) - 64
    raise ValueError(f"Unknown normalized codec: {codec}")


def _extract_parameter(parsed: list[dict[str, Any]], table_key: str, spec: dict[str, Any],
                       part_no: int | None = None) -> tuple[Any, dict[str, Any]] | None:
    for m in parsed:
        if m.get("kind") != "bulk_dump" or m.get("protocol_table") != table_key:
            continue
        if not m.get("checksum_ok", False) or not m.get("byte_count_ok", False):
            continue
        address = bytes(m.get("address", []))
        captures = match_pattern(spec["pattern"], address)
        if captures is None:
            continue
        if part_no is not None and captures.get("p") != part_no:
            continue
        data_hex = m.get("data_hex", "")
        data = bytes.fromhex(data_hex) if data_hex else b""
        offset, size = spec["offset"], spec["size"]
        if offset + size > len(data):
            continue
        raw = data[offset:offset + size]
        value = decode_normalized_value(raw, spec["codec"])
        source = {
            "address": m.get("address_hex"),
            "block": m.get("block_name"),
            "offset": offset,
            "size": size,
            "codec": spec["codec"],
            "raw_hex": raw.hex(" ").upper(),
            "mapping_source_status": m.get("mapping_source_status", "yamaha_documented"),
        }
        return value, source
    return None


def _message_part_no(m: dict[str, Any]) -> int | None:
    caps = m.get("block_captures", {})
    if isinstance(caps.get("p"), int):
        return caps["p"]
    # Legacy Yamaha tables sometimes encode e/o + p as a single byte token (ep/op),
    # where the low nibble is the Part number. Recover p from the actual address.
    if m.get("protocol_table") == "legacy":
        addr = m.get("address", [])
        cat = m.get("block_category")
        if cat == "normal_part_element" and len(addr) >= 2:
            return addr[1] & 0x0F
        if cat == "drum_part_key" and len(addr) >= 1:
            return addr[0] & 0x0F
        if cat == "fmx_part" and len(addr) >= 2:
            return addr[1] & 0x0F
    return None


def _part_engine(parsed: list[dict[str, Any]], part_no: int) -> tuple[str | None, str | None, list[str]]:
    cats: set[str] = set()
    for m in parsed:
        if m.get("kind") != "bulk_dump":
            continue
        if _message_part_no(m) == part_no:
            cats.add(m.get("block_category", ""))
    if "anx_part" in cats:
        return "AN-X", "normal", sorted(cats)
    if "fmx_part" in cats:
        return "FM-X", "normal", sorted(cats)
    if "drum_part_key" in cats:
        return "AWM2", "drum", sorted(cats)
    if "normal_part_element" in cats:
        return "AWM2", "normal", sorted(cats)
    return None, None, sorted(cats)


def _bulk_messages(parsed: list[dict[str, Any]], table_key: str | None = None,
                   trusted_only: bool = True) -> list[dict[str, Any]]:
    return [m for m in parsed if m.get("kind") == "bulk_dump" and
            (table_key is None or m.get("protocol_table") == table_key) and
            (not trusted_only or (m.get("checksum_ok", False) and m.get("byte_count_ok", False)))]


def _matching_messages(parsed: list[dict[str, Any]], table_key: str, pattern: str,
                       part_no: int | None = None) -> list[tuple[dict[str, Any], dict[str, int]]]:
    found: list[tuple[dict[str, Any], dict[str, int]]] = []
    for m in _bulk_messages(parsed, table_key):
        address = bytes(m.get("address", []))
        caps = match_pattern(pattern, address)
        if caps is None:
            continue
        if part_no is not None and caps.get("p") != part_no:
            continue
        found.append((m, caps))
    return found


def _message_data(m: dict[str, Any]) -> bytes:
    h = m.get("data_hex", "")
    return bytes.fromhex(h) if h else b""


def _field_from_message(m: dict[str, Any], offset: int, size: int, codec: str) -> tuple[Any, dict[str, Any]] | None:
    data = _message_data(m)
    if offset + size > len(data):
        return None
    raw = data[offset:offset + size]
    value = decode_normalized_value(raw, codec)
    source = {
        "address": m.get("address_hex"),
        "block": m.get("block_name"),
        "offset": offset,
        "size": size,
        "codec": codec,
        "raw_hex": raw.hex(" ").upper(),
        "mapping_source_status": m.get("mapping_source_status", "yamaha_documented"),
    }
    return value, source


def _decode_scene_parts(parsed: list[dict[str, Any]], table_key: str) -> list[dict[str, Any]]:
    if table_key == "legacy":
        pattern = "36 cp 00"
        fields = [
            ("mute", 0x00, 1, "bool"), ("volume", 0x01, 1, "u7"),
            ("pan", 0x02, 1, "pan_l63_r63"), ("reverb_send", 0x03, 1, "u7"),
            ("variation_send", 0x04, 1, "u7"), ("dry_level", 0x05, 1, "u7"),
        ]
    else:
        pattern = "1p 03 0c 00"
        fields = [
            ("mute", 0x00, 2, "bool_u14"), ("volume", 0x02, 2, "u14"),
            ("pan", 0x04, 2, "pan_u14_l63_r63"), ("reverb_send", 0x06, 2, "u14"),
            ("variation_send", 0x08, 2, "u14"), ("dry_level", 0x0A, 2, "u14"),
        ]
    scenes: dict[int, dict[str, Any]] = {}
    for m, caps in _matching_messages(parsed, table_key, pattern):
        c, p = caps.get("c"), caps.get("p")
        if not isinstance(c, int) or not isinstance(p, int):
            continue
        scene = scenes.setdefault(c, {"number": c + 1, "parts": []})
        part: dict[str, Any] = {"number": p + 1, "provenance": {}}
        for field, off, size, codec in fields:
            actual_codec = "u14" if codec == "bool_u14" else codec
            got = _field_from_message(m, off, size, actual_codec)
            if got:
                value, source = got
                if codec == "bool_u14":
                    value = bool(value)
                    source["codec"] = "bool_u14"
                part[field] = value
                part["provenance"][field] = source
        scene["parts"].append(part)
    for scene in scenes.values():
        scene["parts"].sort(key=lambda x: x["number"])
    return [scenes[k] for k in sorted(scenes)]


def _legacy_fmx_engine_data(parsed: list[dict[str, Any]], part_no: int) -> dict[str, Any]:
    out: dict[str, Any] = {"operators": [], "provenance": {}}
    common = _matching_messages(parsed, "legacy", "48 0p 00", part_no)
    if common:
        m = common[0][0]
        for field, off, size, codec in [("algorithm_code", 0x4F, 1, "u7"), ("feedback", 0x50, 1, "u7")]:
            got = _field_from_message(m, off, size, codec)
            if got:
                val, src = got
                out[field] = val
                out["provenance"][field] = src
        if "algorithm_code" in out:
            out["algorithm_number"] = out["algorithm_code"] + 1
    # Legacy operator address packs operator in the high nibble and Part in the low nibble: 49 op 00.
    for m in _bulk_messages(parsed, "legacy"):
        addr = m.get("address", [])
        if len(addr) != 3 or addr[0] != 0x49 or addr[2] != 0x00 or (addr[1] & 0x0F) != part_no:
            continue
        op = (addr[1] >> 4) & 0x0F
        data: dict[str, Any] = {"number": op + 1, "provenance": {}}
        specs = [("frequency_mode_code", 0x03, 1, "u7"), ("tune_coarse", 0x04, 1, "u7"),
                 ("tune_fine", 0x05, 1, "u7"), ("detune_code", 0x06, 1, "u7"),
                 ("level", 0x1A, 1, "u7")]
        for field, off, size, codec in specs:
            got = _field_from_message(m, off, size, codec)
            if got:
                val, src = got; data[field] = val; data["provenance"][field] = src
        if "frequency_mode_code" in data:
            data["frequency_mode"] = {0: "ratio", 1: "fixed"}.get(data["frequency_mode_code"])
        if "detune_code" in data:
            data["detune"] = data["detune_code"] - 15
        out["operators"].append(data)
    out["operators"].sort(key=lambda x: x["number"])
    return out


def _m_fmx_engine_data(parsed: list[dict[str, Any]], part_no: int) -> dict[str, Any]:
    out: dict[str, Any] = {"operators": [], "provenance": {}}
    common = _matching_messages(parsed, "m_generation", "3p 00 00 00", part_no)
    if common:
        m = common[0][0]
        for field, off in [("algorithm_code", 0x3C), ("feedback", 0x3E)]:
            got = _field_from_message(m, off, 2, "u14")
            if got:
                val, src = got; out[field] = val; out["provenance"][field] = src
        if "algorithm_code" in out:
            out["algorithm_number"] = out["algorithm_code"] + 1
    for m, caps in _matching_messages(parsed, "m_generation", "3p 02 0o 00", part_no):
        op = caps.get("o")
        if not isinstance(op, int): continue
        data: dict[str, Any] = {"number": op + 1, "provenance": {}}
        specs = [("frequency_mode_code", 0x02), ("tune_coarse", 0x04), ("tune_fine", 0x06),
                 ("detune_code", 0x08), ("level", 0x30)]
        for field, off in specs:
            got = _field_from_message(m, off, 2, "u14")
            if got:
                val, src = got; data[field] = val; data["provenance"][field] = src
        if "frequency_mode_code" in data:
            data["frequency_mode"] = {0: "ratio", 1: "fixed"}.get(data["frequency_mode_code"])
        if "detune_code" in data:
            data["detune"] = data["detune_code"] - 15
        out["operators"].append(data)
    out["operators"].sort(key=lambda x: x["number"])
    return out


def _m_anx_engine_data(parsed: list[dict[str, Any]], part_no: int) -> dict[str, Any]:
    waves = {0: "Saw1", 1: "Saw2", 2: "Square", 3: "Triangle", 4: "Sine"}
    octaves = {0: "64'", 1: "32'", 2: "16'", 3: "8'", 4: "4'", 5: "2'", 6: "1'"}
    out: dict[str, Any] = {"oscillators": []}
    for m, caps in _matching_messages(parsed, "m_generation", "4p 02 0o 00", part_no):
        osc = caps.get("o")
        if not isinstance(osc, int): continue
        data: dict[str, Any] = {"number": osc + 1, "provenance": {}}
        for field, off in [("wave_code", 0x00), ("octave_code", 0x02), ("pitch_raw", 0x04), ("out_level", 0x30)]:
            got = _field_from_message(m, off, 2, "u14")
            if got:
                val, src = got; data[field] = val; data["provenance"][field] = src
        if "wave_code" in data: data["wave"] = waves.get(data["wave_code"], f"unknown:{data['wave_code']}")
        if "octave_code" in data: data["octave"] = octaves.get(data["octave_code"], f"unknown:{data['octave_code']}")
        # Keep pitch_raw losslessly. Yamaha documents the displayed cent range, but this pass
        # does not assume a conversion curve beyond the raw 14-bit representation.
        out["oscillators"].append(data)
    out["oscillators"].sort(key=lambda x: x["number"])
    return out


def _legacy_awm2_engine_data(parsed: list[dict[str, Any]], part_no: int) -> dict[str, Any]:
    """Decode documented legacy AWM2 Normal Part Element data (41/42 ep 00)."""
    wave_banks = {0: "preset", 1: "user", **{i + 1: f"library{i}" for i in range(1, 9)}}
    xa_modes = {
        0: "normal", 1: "legato", 2: "key_off", 3: "cycle", 4: "random",
        5: "assign_switch_off", 6: "assign_switch_1_on", 7: "assign_switch_2_on",
    }
    connection = {0: "thru", 1: "insertion_a", 2: "insertion_b"}
    elements: dict[int, dict[str, Any]] = {}

    # 41 ep 00 packs Element in high nibble and Part in low nibble.
    for m, caps in _matching_messages(parsed, "legacy", "41 ep 00", part_no):
        e = caps.get("e")
        if not isinstance(e, int):
            continue
        elem = elements.setdefault(e, {"number": e + 1, "provenance": {}})
        specs = [
            ("enabled", 0x00, 1, "bool"),
            ("wave_bank_code", 0x01, 1, "u7"),
            ("element_group_code", 0x02, 1, "u7"),
            ("wave_number", 0x03, 2, "u14"),
            ("pan", 0x08, 1, "pan_l63_r63"),
            ("random_pan_depth", 0x09, 1, "u7"),
            ("alternate_pan", 0x0A, 1, "u7_center64"),
            ("scaling_pan", 0x0B, 1, "u7_center64"),
            ("xa_control_code", 0x0C, 1, "u7"),
            ("note_low", 0x0D, 1, "note"),
            ("note_high", 0x0E, 1, "note"),
            ("velocity_low", 0x0F, 1, "u7"),
            ("velocity_high", 0x10, 1, "u7"),
            ("velocity_crossfade", 0x11, 1, "u7"),
            ("connection_code", 0x17, 1, "u7"),
            ("level", 0x28, 1, "u7"),
            ("coarse_tune", 0x49, 1, "u7_center64"),
            ("fine_tune", 0x4A, 1, "u7_center64"),
        ]
        for field, off, size, codec in specs:
            got = _field_from_message(m, off, size, codec)
            if got:
                val, src = got
                elem[field] = val
                elem["provenance"][field] = src
        if "wave_bank_code" in elem:
            elem["wave_bank"] = wave_banks.get(elem["wave_bank_code"], f"unknown:{elem['wave_bank_code']}")
        if "element_group_code" in elem:
            elem["element_group_number"] = elem["element_group_code"] + 1
        if "xa_control_code" in elem:
            elem["xa_control"] = xa_modes.get(elem["xa_control_code"], f"unknown:{elem['xa_control_code']}")
        if "connection_code" in elem:
            elem["connection"] = connection.get(elem["connection_code"], f"unknown:{elem['connection_code']}")
        if isinstance(elem.get("note_low"), int):
            elem["note_low_name"] = midi_note_name(elem["note_low"])
        if isinstance(elem.get("note_high"), int):
            elem["note_high_name"] = midi_note_name(elem["note_high"])

    # 42 ep 00: filter/EQ/LFO. Decode a conservative cross-conversion subset.
    for m, caps in _matching_messages(parsed, "legacy", "42 ep 00", part_no):
        e = caps.get("e")
        if not isinstance(e, int):
            continue
        elem = elements.setdefault(e, {"number": e + 1, "provenance": {}})
        specs = [
            ("filter_type_code", 0x00, 1, "u7"),
            ("filter_cutoff", 0x01, 2, "u14"),
            ("filter_resonance", 0x05, 1, "u7"),
            ("hpf_cutoff", 0x07, 2, "u14"),
            ("feg_depth", 0x1D, 1, "u7_center64"),
            ("lfo_wave_code", 0x3A, 1, "u7"),
            ("lfo_speed", 0x3D, 1, "u7"),
            ("lfo_amplitude_depth", 0x3E, 1, "u7"),
            ("lfo_pitch_depth", 0x3F, 1, "u7"),
            ("lfo_filter_depth", 0x40, 1, "u7"),
        ]
        for field, off, size, codec in specs:
            got = _field_from_message(m, off, size, codec)
            if got:
                val, src = got
                elem[field] = val
                elem["provenance"][field] = src
        if "lfo_wave_code" in elem:
            elem["lfo_wave"] = {0: "saw", 1: "triangle", 2: "square"}.get(
                elem["lfo_wave_code"], f"unknown:{elem['lfo_wave_code']}"
            )

    return {"elements": [elements[k] for k in sorted(elements)]}


def _decode_arp_reference_legacy(raw_number: int) -> dict[str, Any]:
    if raw_number == 0:
        return {"status": "off", "bank": "off", "arp_number": 0}
    if 1 <= raw_number <= 10239:
        return {"status": "assigned", "bank": "preset", "arp_number": raw_number}
    if 10240 <= raw_number <= 10495:
        return {"status": "assigned", "bank": "user", "arp_number": raw_number - 10240 + 1}
    if 10496 <= raw_number <= 12543:
        idx = (raw_number - 10496) // 256 + 1
        num = (raw_number - 10496) % 256 + 1
        return {"status": "assigned", "bank": f"library{idx}", "arp_number": num}
    return {"status": "unclassified", "bank": None, "arp_number": None}


def _decode_arp_reference_m(raw_number: int, extra: int) -> dict[str, Any]:
    if raw_number == 0:
        return {"status": "off", "bank": "off", "arp_number": 0}
    # The M-generation Arpeggio Type List ends at preset Arp 10922. The field
    # description still mentions the older 10239 limit, so use the actual M list
    # rather than the stale prose limit. User Arps start at 12032.
    if 1 <= raw_number <= 10922:
        return {"status": "assigned", "bank": "preset", "arp_number": raw_number}
    if 10923 <= raw_number <= 12031:
        return {"status": "documented_reserved_gap", "bank": None, "arp_number": None}
    if 12032 <= raw_number <= 12287:
        return {"status": "assigned", "bank": "user", "arp_number": raw_number - 12032 + 1}
    if 12288 <= raw_number <= 16127:
        idx = (raw_number - 12288) // 256 + 1
        num = (raw_number - 12288) % 256 + 1
        return {"status": "assigned", "bank": f"library{idx}", "arp_number": num}
    if 16128 <= raw_number <= 16382:
        return {"status": "assigned", "bank": "library16", "arp_number": raw_number - 16128 + 1}
    if raw_number == 16383:
        if extra == 0:
            return {"status": "assigned", "bank": "library16", "arp_number": 256}
        if 1 <= extra <= 2048:
            idx = 17 + (extra - 1) // 256
            num = (extra - 1) % 256 + 1
            return {"status": "assigned", "bank": f"library{idx}", "arp_number": num}
    return {"status": "unclassified", "bank": None, "arp_number": None}


def _decode_arp_slots(parsed: list[dict[str, Any]], table_key: str, part_no: int) -> list[dict[str, Any]]:
    pattern = "31 6p 00" if table_key == "legacy" else "1p 00 06 00"
    matches = _matching_messages(parsed, table_key, pattern, part_no)
    if not matches:
        return []
    m = matches[0][0]
    slots: list[dict[str, Any]] = []
    for i in range(8):
        if table_key == "legacy":
            off = 0x45 + i * 3
            got = _field_from_message(m, off, 2, "u14")
            if not got:
                continue
            raw_number, src = got
            decoded = _decode_arp_reference_legacy(raw_number)
            slot = {"slot": i + 1, "raw_number": raw_number, **decoded, "provenance": {"number": src}}
        else:
            off = 0x44 + i * 2
            extra_off = 0x54 + i * 2
            got = _field_from_message(m, off, 2, "u14")
            extra_got = _field_from_message(m, extra_off, 2, "u14")
            if not got:
                continue
            raw_number, src = got
            extra = extra_got[0] if extra_got else 0
            decoded = _decode_arp_reference_m(raw_number, extra)
            slot = {
                "slot": i + 1, "raw_number": raw_number, "raw_extra": extra, **decoded,
                "provenance": {"number": src},
            }
            if extra_got:
                slot["provenance"]["extra"] = extra_got[1]
        slots.append(slot)
    return slots


def _m_awm2_engine_data(parsed: list[dict[str, Any]], part_no: int) -> dict[str, Any]:
    elements: dict[int, dict[str, Any]] = {}
    for pattern, field_specs in [
        ("2p 02 ee 00", [("level", 0x00, "u14")]),
        ("2p 03 ee 00", [("coarse_tune", 0x00, "u14_center64"), ("fine_tune", 0x02, "u14_center64")]),
    ]:
        for m, caps in _matching_messages(parsed, "m_generation", pattern, part_no):
            e = caps.get("ee")
            if not isinstance(e, int): continue
            elem = elements.setdefault(e, {"number": e + 1, "provenance": {}})
            for field, off, codec in field_specs:
                got = _field_from_message(m, off, 2, codec)
                if got:
                    val, src = got; elem[field] = val; elem["provenance"][field] = src
    return {"elements": [elements[k] for k in sorted(elements)]}


def _engine_specific_data(parsed: list[dict[str, Any]], table_key: str, part_no: int,
                          engine: str | None) -> dict[str, Any] | None:
    if engine == "FM-X":
        return _legacy_fmx_engine_data(parsed, part_no) if table_key == "legacy" else _m_fmx_engine_data(parsed, part_no)
    if engine == "AN-X" and table_key == "m_generation":
        return _m_anx_engine_data(parsed, part_no)
    if engine == "AWM2" and table_key == "m_generation":
        return _m_awm2_engine_data(parsed, part_no)
    if engine == "AWM2" and table_key == "legacy":
        return _legacy_awm2_engine_data(parsed, part_no)
    return None



def _sidechain_name(value: int | None) -> str | None:
    if value is None:
        return None
    if 0 <= value <= 15:
        return f"part_{value + 1}"
    if value == 16:
        return "a_d"
    if value == 17:
        return "master"
    if value == 127:
        return "off"
    return f"unknown:{value}"


def _decode_insertion_effect(parsed: list[dict[str, Any]], table_key: str, part_no: int,
                             slot: str, effect_types: dict[str, Any]) -> dict[str, Any] | None:
    slot = slot.upper()
    if slot not in {"A", "B"}:
        raise ValueError("Insertion slot must be A or B")
    if table_key == "legacy":
        pattern = "31 2p 00" if slot == "A" else "31 3p 00"
        matches = _matching_messages(parsed, table_key, pattern, part_no)
        if not matches:
            return None
        m = matches[0][0]
        data = _message_data(m)
        if len(data) < 3:
            return None
        type_msb, type_lsb = data[0], data[1]
        preset = data[2]
        param_start = 3
        sidechain = data[0x43] if len(data) > 0x43 else None
        source = {"address": m.get("address_hex"), "block": m.get("block_name"),
                  "mapping_source_status": m.get("mapping_source_status", "yamaha_documented")}
    else:
        pattern = "1p 00 04 00" if slot == "A" else "1p 00 05 00"
        matches = _matching_messages(parsed, table_key, pattern, part_no)
        if not matches:
            return None
        m = matches[0][0]
        data = _message_data(m)
        if len(data) < 4:
            return None
        type_msb, type_lsb = data[0], data[1]
        preset = u14(data[2:4])
        param_start = 4
        side_spec = {"pattern": "1p 00 03 00", "offset": 0x3A if slot == "A" else 0x3C, "size": 2, "codec": "u14"}
        got = _extract_parameter(parsed, table_key, side_spec, part_no=part_no)
        sidechain = got[0] if got else None
        source = {"address": m.get("address_hex"), "block": m.get("block_name"),
                  "mapping_source_status": m.get("mapping_source_status", "yamaha_documented")}

    key = f"{type_msb:02X} {type_lsb:02X}"
    info = effect_types.get("profiles", {}).get(table_key, {}).get(key)
    params=[]
    for i in range(24):
        off = param_start + i * 2
        if off + 2 > len(data):
            break
        raw = data[off:off+2]
        params.append({"number": i + 1, "msb": raw[0], "lsb": raw[1],
                       "raw_u14": u14(raw), "raw_hex": raw.hex(" ").upper()})
    return {
        "slot": slot,
        "type_code": key,
        "type_msb": type_msb,
        "type_lsb": type_lsb,
        "type_name": info.get("name") if info else None,
        "type_short_name": info.get("short_name") if info else None,
        "category": info.get("category") if info else None,
        "type_status": "yamaha_documented" if info else "unmapped_type",
        "preset_number_raw": preset,
        "sidechain_code": sidechain,
        "sidechain": _sidechain_name(sidechain),
        "parameters": params,
        "provenance": source,
    }


def _decode_part_insertion_effects(parsed: list[dict[str, Any]], table_key: str, part_no: int,
                                   effect_types: dict[str, Any]) -> dict[str, Any]:
    a = _decode_insertion_effect(parsed, table_key, part_no, "A", effect_types)
    b = _decode_insertion_effect(parsed, table_key, part_no, "B", effect_types)
    connection_code = None
    connection_source = None
    if table_key == "legacy":
        spec = {"pattern": "31 0p 00", "offset": 0x3B, "size": 1, "codec": "u7"}
    else:
        spec = {"pattern": "1p 00 03 00", "offset": 0x14, "size": 2, "codec": "u14"}
    got = _extract_parameter(parsed, table_key, spec, part_no=part_no)
    if got:
        connection_code, connection_source = got
    connection = {0: "parallel", 1: "A_to_B", 2: "B_to_A"}.get(connection_code,
                 None if connection_code is None else f"unknown:{connection_code}")
    return {"connection_code": connection_code, "connection": connection,
            "A": a, "B": b, "provenance": {"connection": connection_source} if connection_source else {}}


def build_normalized_performance(parsed: list[dict[str, Any]], parameter_map: dict[str, Any], effect_type_map: dict[str, Any] | None = None) -> dict[str, Any]:
    effect_type_map = effect_type_map or load_effect_type_map()
    all_bulk = [m for m in parsed if m.get("kind") == "bulk_dump"]
    bulk = [m for m in all_bulk if m.get("checksum_ok", False) and m.get("byte_count_ok", False)]
    invalid_count = len(all_bulk) - len(bulk)
    if not bulk:
        return {
            "schema_version": parameter_map.get("schema_version", 1), "parts": [], "scenes": [],
            "transport_invalid_message_count": invalid_count,
            "normalization_warnings": ["No transport-valid Bulk Dump messages available for normalization"] if all_bulk else [],
        }
    table_key = bulk[0].get("protocol_table")
    profile_map = parameter_map.get("profiles", {}).get(table_key, {})
    out: dict[str, Any] = {
        "schema_version": parameter_map.get("schema_version", 1),
        "source_profile": bulk[0].get("profile"),
        "model_id": bulk[0].get("model_id_hex"),
        "parts": [],
        "scenes": _decode_scene_parts(parsed, table_key),
        "transport_invalid_message_count": invalid_count,
        "normalization_warnings": ([f"Skipped {invalid_count} transport-invalid Bulk Dump message(s) during normalization"]
                                   if invalid_count else []),
        "provenance": {},
    }
    perf_flat: dict[str, Any] = {}
    for spec in profile_map.get("performance", []):
        got = _extract_parameter(parsed, table_key, spec)
        if got is not None:
            value, source = got
            perf_flat[spec["field"]] = value
            out["provenance"][spec["field"]] = source

    out["name"] = perf_flat.get("name")
    out["tempo_bpm"] = perf_flat.get("tempo")
    out["volume"] = perf_flat.get("volume")
    out["pan"] = perf_flat.get("pan")
    out["main_category_code"] = perf_flat.get("main_category")
    out["sub_category_code"] = perf_flat.get("sub_category")
    out["arp_master_on"] = perf_flat.get("arp_master_on")
    out["motion_seq_master_on"] = perf_flat.get("motion_seq_master_on")

    part_numbers: set[int] = set()
    for m in bulk:
        pno = _message_part_no(m)
        if isinstance(pno, int) and 0 <= pno <= 15:
            part_numbers.add(pno)

    for pno in sorted(part_numbers):
        flat: dict[str, Any] = {}
        prov: dict[str, Any] = {}
        for spec in profile_map.get("part", []):
            got = _extract_parameter(parsed, table_key, spec, part_no=pno)
            if got is not None:
                value, source = got
                flat[spec["field"]] = value
                prov[spec["field"]] = source
        engine, part_type, observed_categories = _part_engine(parsed, pno)
        note_low = flat.get("note_low")
        note_high = flat.get("note_high")
        part = {
            "number": pno + 1,
            "name": flat.get("name"),
            "engine": engine,
            "part_type": part_type,
            "enabled": flat.get("enabled"),
            "mode": flat.get("mode"),
            "keyboard_control": flat.get("keyboard_control"),
            "mute": flat.get("mute"),
            "volume": flat.get("volume"),
            "pan": flat.get("pan"),
            "main_category_code": flat.get("main_category"),
            "sub_category_code": flat.get("sub_category"),
            "velocity_limit": {"low": flat.get("velocity_low"), "high": flat.get("velocity_high")},
            "note_limit": {
                "low": note_low, "high": note_high,
                "low_name": midi_note_name(note_low) if isinstance(note_low, int) and 0 <= note_low <= 127 else None,
                "high_name": midi_note_name(note_high) if isinstance(note_high, int) and 0 <= note_high <= 127 else None,
            },
            "pitch": {"note_shift_semitones": flat.get("note_shift")},
            "effects": {"reverb_send": flat.get("reverb_send"), "variation_send": flat.get("variation_send"),
                        "dry_level": flat.get("dry_level"),
                        "insertion": _decode_part_insertion_effects(parsed, table_key, pno, effect_type_map)},
            "arpeggio": {"switch_on": flat.get("arp_switch"), "play_only": flat.get("arp_play_only"),
                          "loop_on": flat.get("arp_loop"), "slots": _decode_arp_slots(parsed, table_key, pno)},
            "observed_block_categories": observed_categories,
            "provenance": prov,
        }
        eng = _engine_specific_data(parsed, table_key, pno, engine)
        if eng is not None:
            part["engine_data"] = eng
        out["parts"].append(part)
    return out

def _match_token(token: str, value: int, captures: dict[str, int], capture_keys: set[str]) -> bool:
    if len(token) != 2:
        raise ValueError(f"Invalid address token: {token}")
    if token[0].islower() and token[1].islower():
        # Yamaha notation uses repeated symbols for a whole byte (mm, nn, ee, kk)
        # and two different symbols for packed nibbles (cp, ep, op, sp).
        # Rule capture ranges reinforce the distinction, but callers such as
        # _matching_messages() may not pass ranges, so the notation itself must
        # also be sufficient.
        packed_nibbles = token[0] != token[1] or token[0] in capture_keys or token[1] in capture_keys
        if not packed_nibbles:
            old = captures.get(token)
            if old is not None and old != value:
                return False
            captures[token] = value
            return True
    hi, lo = value >> 4, value & 0x0F

    def match_nibble(symbol: str, nibble: int) -> bool:
        if symbol.islower() or symbol in capture_keys:
            old = captures.get(symbol)
            if old is not None and old != nibble:
                return False
            captures[symbol] = nibble
            return True
        try:
            return nibble == int(symbol, 16)
        except ValueError as exc:
            raise ValueError(f"Unknown address symbol {symbol!r} in token {token!r}") from exc

    return match_nibble(token[0], hi) and match_nibble(token[1], lo)


def match_pattern(pattern: str, address: bytes, ranges: dict[str, list[int]] | None = None) -> dict[str, int] | None:
    tokens = pattern.split()
    if len(tokens) != len(address):
        return None
    captures: dict[str, int] = {}
    capture_keys = set((ranges or {}).keys())
    for token, value in zip(tokens, address):
        if not _match_token(token, value, captures, capture_keys):
            return None
    for key, bounds in (ranges or {}).items():
        if key in captures and not (bounds[0] <= captures[key] <= bounds[1]):
            return None
    return captures


def pattern_specificity(pattern: str) -> int:
    score = 0
    for token in pattern.split():
        for c in token:
            if c in "0123456789ABCDEF":
                score += 4
    return score


def decode_ascii(data: bytes) -> str:
    return data.rstrip(b"\x00 ").decode("ascii", errors="replace")


def map_block(address: bytes, data: bytes, table: dict[str, Any]) -> dict[str, Any] | None:
    candidates = sorted(table.get("rules", []), key=lambda r: pattern_specificity(r["pattern"]), reverse=True)
    for rule in candidates:
        captures = match_pattern(rule["pattern"], address, rule.get("captures"))
        if captures is None:
            continue
        expected = rule.get("data_length")
        mapped: dict[str, Any] = {
            "block_category": rule["category"],
            "block_name": rule["name"],
            "block_pattern": rule["pattern"],
            "block_captures": captures,
            "expected_data_length": expected,
            "block_size_ok": expected is None or len(data) == expected,
            "mapping_source_status": rule.get("source_status", "yamaha_documented"),
        }
        if rule.get("text") == "ascii":
            text_data = data
            if "text_slice" in rule:
                a, b = rule["text_slice"]
                text_data = data[a:b]
            mapped["decoded_text"] = decode_ascii(text_data)
            if rule.get("decoded_field"):
                mapped["decoded_field"] = rule["decoded_field"]
        if rule.get("name") == "Soundmondo Format Version" and len(data) == 6:
            major = (data[0] << 7) | data[1]
            minor = (data[2] << 7) | data[3]
            bugfix = (data[4] << 7) | data[5]
            mapped["soundmondo_version"] = f"{major}.{minor}.{bugfix}"
            mapped["soundmondo_version_parts"] = [major, minor, bugfix]
        if rule.get("soundmondo_lengths"):
            mapped["soundmondo_length_variants"] = rule["soundmondo_lengths"]
        return mapped
    return None


def classify_message(msg: bytes, index: int, block_tables: dict[str, dict[str, Any]]) -> dict[str, Any]:
    base: dict[str, Any] = {"index": index, "length": len(msg), "raw_hex": msg.hex(" ").upper()}
    if len(msg) < 2 or msg[0] != 0xF0 or msg[-1] != 0xF7:
        return base | {"kind": "invalid", "error": "Missing F0/F7 framing"}
    if len(msg) < 7:
        return base | {"kind": "unknown", "error": "Message too short"}
    if msg[1] != YAMAHA_ID:
        return base | {"kind": "non_yamaha", "manufacturer_id": msg[1]}
    if msg[3:5] != bytes([GROUP_HIGH, GROUP_LOW]):
        return base | {"kind": "yamaha_other", "device_byte": msg[2], "group_hex": msg[3:5].hex(" ").upper()}

    device_byte = msg[2]
    command_nibble = device_byte & 0xF0
    device_no = device_byte & 0x0F
    if command_nibble != 0x00:
        return base | {"kind": "yamaha_non_bulk_dump", "device_byte": device_byte, "device_no": device_no,
                       "command_nibble": command_nibble}
    if len(msg) < 10:
        return base | {"kind": "invalid_bulk_dump", "error": "Bulk dump too short"}

    byte_count = (msg[5] << 7) | msg[6]
    model_id = msg[7]
    profile = PROFILES.get(model_id)
    if not profile:
        return base | {"kind": "bulk_dump_unknown_model", "device_no": device_no,
                       "byte_count": byte_count, "model_id": model_id}

    # Critical v0.3 rule: address width is selected by Yamaha Model ID, never inferred from message length.
    addr_start = 8
    addr_end = addr_start + profile.address_len
    if len(msg) < addr_end + 2:
        return base | {"kind": "invalid_bulk_dump", "error": "Too short for address/checksum"}
    address = msg[addr_start:addr_end]
    data = msg[addr_end:-2]
    checksum = msg[-2]
    calculated_count = 1 + profile.address_len + len(data)

    result: dict[str, Any] = base | {
        "kind": "bulk_dump",
        "profile": profile.name,
        "protocol_table": profile.table_key,
        "address_length": profile.address_len,
        "device_no": device_no,
        "byte_count": byte_count,
        "calculated_byte_count": calculated_count,
        "byte_count_ok": byte_count == calculated_count,
        "model_id": model_id,
        "model_id_hex": f"{model_id:02X}",
        "address": list(address),
        "address_hex": address.hex(" ").upper(),
        "data_length": len(data),
        "data_hex": data.hex(" ").upper(),
        "checksum": checksum,
        "checksum_hex": f"{checksum:02X}",
        "checksum_ok": checksum_ok(model_id, address, data, checksum),
    }

    table = block_tables.get(profile.table_key, {"rules": []})
    mapping = map_block(address, data, table)
    if mapping:
        result.update(mapping)
    else:
        result["block_category"] = "unmapped"
    return result


def build_performance_summary(parsed: list[dict[str, Any]]) -> dict[str, Any]:
    bulk = [m for m in parsed if m.get("kind") == "bulk_dump"]
    performance_name = None
    part_names: dict[str, str] = {}
    engines: set[str] = set()
    parts: set[int] = set()

    for m in bulk:
        if m.get("decoded_field") == "performance_name" and m.get("decoded_text"):
            performance_name = performance_name or m["decoded_text"]
        elif m.get("block_name") == "Performance Name" and m.get("decoded_text"):
            performance_name = performance_name or m["decoded_text"]
        cat = m.get("block_category")
        caps = m.get("block_captures", {})
        if "p" in caps:
            parts.add(caps["p"])
        if m.get("block_name") == "Performance Part Name" and "p" in caps:
            part_names[str(caps["p"] + 1)] = m.get("decoded_text", "")
        if cat in ("normal_part_element", "drum_part_key"):
            engines.add("AWM2")
        elif cat == "fmx_part":
            engines.add("FM-X")
        elif cat == "anx_part":
            engines.add("AN-X")

    return {
        "performance_name": performance_name,
        "part_numbers": [p + 1 for p in sorted(parts)],
        "part_count_observed": len(parts),
        "part_names": part_names,
        "engines_observed": sorted(engines),
    }


def parse_file(path: Path, include_raw: bool = False,
               block_tables: dict[str, dict[str, Any]] | None = None,
               parameter_map: dict[str, Any] | None = None) -> dict[str, Any]:
    block_tables = block_tables or load_block_tables()
    parameter_map = parameter_map or load_parameter_map()
    raw = path.read_bytes()
    messages, split_warnings = split_sysex_stream(raw)
    parsed = [classify_message(m, i, block_tables) for i, m in enumerate(messages)]

    normalized = build_normalized_performance(parsed, parameter_map)

    if not include_raw:
        for item in parsed:
            item.pop("raw_hex", None)
            if len(item.get("data_hex", "")) > 400:
                item.pop("data_hex", None)

    bulk = [m for m in parsed if m.get("kind") == "bulk_dump"]
    profiles = sorted({m["profile"] for m in bulk})
    model_ids = sorted({m["model_id_hex"] for m in bulk})
    mapped = [m for m in bulk if m.get("block_category") not in (None, "unmapped")]
    documented_size_mismatches = [m for m in mapped if not m.get("block_size_ok", True)]

    version_msg = next((m for m in bulk if m.get("soundmondo_version")), None)
    soundmondo_version = version_msg.get("soundmondo_version") if version_msg else None
    effective_size_failures = 0
    for m in mapped:
        variants = m.get("soundmondo_length_variants", {})
        effective = variants.get(soundmondo_version, m.get("expected_data_length")) if soundmondo_version else m.get("expected_data_length")
        m["effective_expected_data_length"] = effective
        m["effective_size_source"] = "observed_soundmondo" if soundmondo_version and soundmondo_version in variants else "yamaha_documented"
        m["effective_block_size_ok"] = effective is None or m.get("data_length") == effective
        if not m["effective_block_size_ok"]:
            effective_size_failures += 1

    return {
        "file": path.name,
        "path": str(path),
        "size": len(raw),
        "message_count": len(messages),
        "bulk_dump_count": len(bulk),
        "profiles": profiles,
        "model_ids": model_ids,
        "address_lengths": sorted({m["address_length"] for m in bulk}),
        "checksum_failures": sum(not m.get("checksum_ok", True) for m in bulk),
        "byte_count_failures": sum(not m.get("byte_count_ok", True) for m in bulk),
        "documented_block_size_mismatches": len(documented_size_mismatches),
        "effective_block_size_failures": effective_size_failures,
        "soundmondo_version": soundmondo_version,
        "mapped_block_count": len(mapped),
        "unmapped_block_count": len(bulk) - len(mapped),
        "mapping_coverage_pct": round(100.0 * len(mapped) / len(bulk), 2) if bulk else 0.0,
        "split_warnings": split_warnings,
        "performance": build_performance_summary(parsed),
        "normalized_performance": normalized,
        "messages": parsed,
    }


def iter_syx(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
    elif path.is_dir():
        yield from sorted(path.rglob("*.syx"))
    else:
        raise FileNotFoundError(path)


def compact_summary(result: dict[str, Any]) -> dict[str, Any]:
    bulk = [m for m in result["messages"] if m.get("kind") == "bulk_dump"]
    blocks: dict[str, int] = {}
    categories: dict[str, int] = {}
    for m in bulk:
        name = m.get("block_name", m.get("block_category", "unmapped"))
        blocks[name] = blocks.get(name, 0) + 1
        cat = m.get("block_category", "unmapped")
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "file": result["file"], "size": result["size"], "messages": result["message_count"],
        "bulk_dumps": result["bulk_dump_count"], "profiles": result["profiles"], "model_ids": result["model_ids"],
        "address_lengths": result["address_lengths"], "checksum_failures": result["checksum_failures"],
        "byte_count_failures": result["byte_count_failures"],
        "documented_block_size_mismatches": result["documented_block_size_mismatches"],
        "effective_block_size_failures": result["effective_block_size_failures"],
        "soundmondo_version": result["soundmondo_version"], "split_warning_count": len(result["split_warnings"]),
        "mapped_blocks": result["mapped_block_count"], "unmapped_blocks": result["unmapped_block_count"],
        "mapping_coverage_pct": result["mapping_coverage_pct"], "performance": result["performance"],
        "normalized_performance": result["normalized_performance"],
        "block_categories": categories, "block_names": blocks,
        "first_address": bulk[0]["address_hex"] if bulk else None,
        "last_address": bulk[-1]["address_hex"] if bulk else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Offline Yamaha MONTAGE/MODX SysEx bulk-dump parser prototype v0.6")
    ap.add_argument("input", type=Path, help=".syx file or directory containing .syx files")
    ap.add_argument("-o", "--output", type=Path, help="Write JSON to this file")
    ap.add_argument("--full", action="store_true", help="Include per-message details")
    ap.add_argument("--raw", action="store_true", help="Include full raw/data hex in detailed JSON")
    ap.add_argument("--legacy-table", type=Path, default=DEFAULT_TABLES["legacy"])
    ap.add_argument("--m-table", type=Path, default=DEFAULT_TABLES["m_generation"])
    ap.add_argument("--parameter-map", type=Path, default=DEFAULT_PARAMETER_MAP)
    args = ap.parse_args()

    tables = load_block_tables({"legacy": args.legacy_table, "m_generation": args.m_table})
    parameter_map = load_parameter_map(args.parameter_map)
    files = list(iter_syx(args.input))
    results = [parse_file(p, include_raw=args.raw, block_tables=tables, parameter_map=parameter_map) for p in files]
    payload: Any = results if args.full else [compact_summary(r) for r in results]
    if len(payload) == 1:
        payload = payload[0]
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)

    bad = sum(r["checksum_failures"] + r["byte_count_failures"] + r["effective_block_size_failures"] + len(r["split_warnings"]) for r in results)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
