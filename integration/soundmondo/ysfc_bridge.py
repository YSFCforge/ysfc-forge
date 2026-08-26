#!/usr/bin/env python3
# RECOVERY CHECKPOINT 2026-08-21 / SysEx Converter v1.21
# The standalone HTML app is the authoritative production runtime for
# Soundmondo SysEx -> MODX M Y2L conversion at this checkpoint.
# Keep fail-closed behavior: do not invent missing source blocks,
# external waveform/Arp dependencies, or unverified mappings.
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import sysex_parser as sp

BRIDGE_SCHEMA_VERSION = 1
KIND = "ysfc_performance_intermediate"


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _scene_index(scene: dict[str, Any]) -> int | None:
    n = scene.get("number")
    return n - 1 if isinstance(n, int) and n > 0 else None


def _part_index(part: dict[str, Any]) -> int | None:
    n = part.get("number")
    return n - 1 if isinstance(n, int) and n > 0 else None


def _effect_bridge(ins: dict[str, Any] | None) -> dict[str, Any]:
    ins = ins or {}
    out = {
        "connection": ins.get("connection"),
        "connection_code": ins.get("connection_code"),
        "A": _clone(ins.get("A")),
        "B": _clone(ins.get("B")),
    }
    if ins.get("provenance"):
        out["provenance"] = _clone(ins["provenance"])
    return out


def _arp_bridge(arp: dict[str, Any] | None) -> dict[str, Any]:
    arp = arp or {}
    slots = []
    for slot in arp.get("slots") or []:
        slots.append({
            "slot_index": (slot.get("slot") - 1) if isinstance(slot.get("slot"), int) else None,
            "slot_number": slot.get("slot"),
            "status": slot.get("status"),
            "bank": slot.get("bank"),
            "number": slot.get("arp_number"),
            "raw_number": slot.get("raw_number"),
            "raw_extra": slot.get("raw_extra"),
            "provenance": _clone(slot.get("provenance")),
        })
    return {
        "master_part_switch": arp.get("switch_on"),
        "play_only": arp.get("play_only"),
        "loop": arp.get("loop_on"),
        "slots": slots,
    }


def _part_bridge(part: dict[str, Any]) -> dict[str, Any]:
    idx = _part_index(part)
    return {
        "part_index": idx,
        "part_number": part.get("number"),
        "identity": {
            "name": part.get("name"),
            "engine": part.get("engine"),
            "part_type": part.get("part_type"),
            "main_category_code": part.get("main_category_code"),
            "sub_category_code": part.get("sub_category_code"),
        },
        "switches": {
            "enabled": part.get("enabled"),
            "keyboard_control": part.get("keyboard_control"),
            "mute": part.get("mute"),
            "mode": part.get("mode"),
        },
        "mix": {
            "volume": part.get("volume"),
            "pan": part.get("pan"),
            "reverb_send": (part.get("effects") or {}).get("reverb_send"),
            "variation_send": (part.get("effects") or {}).get("variation_send"),
            "dry_level": (part.get("effects") or {}).get("dry_level"),
        },
        "note_range": _clone(part.get("note_limit")),
        "velocity_range": _clone(part.get("velocity_limit")),
        "pitch": _clone(part.get("pitch")),
        "arpeggio": _arp_bridge(part.get("arpeggio")),
        "insertion_fx": _effect_bridge((part.get("effects") or {}).get("insertion")),
        "engine_data": _clone(part.get("engine_data")),
        "source_observed_block_categories": _clone(part.get("observed_block_categories")),
        "provenance": _clone(part.get("provenance")),
    }


def _scene_bridge(scene: dict[str, Any]) -> dict[str, Any]:
    parts = []
    for p in scene.get("parts") or []:
        pn = p.get("part_number") or p.get("number")
        parts.append({
            "part_index": pn - 1 if isinstance(pn, int) and pn > 0 else None,
            "part_number": pn,
            "mute": p.get("mute"),
            "volume": p.get("volume"),
            "pan": p.get("pan"),
            "reverb_send": p.get("reverb_send"),
            "variation_send": p.get("variation_send"),
            "dry_level": p.get("dry_level"),
            "provenance": _clone(p.get("provenance")),
        })
    return {
        "scene_index": _scene_index(scene),
        "scene_number": scene.get("number"),
        "parts": parts,
    }


def _dependencies(perf: dict[str, Any]) -> list[dict[str, Any]]:
    deps: list[dict[str, Any]] = []
    seen: set[tuple] = set()
    for part in perf.get("parts") or []:
        pnum = part.get("number")
        eng = part.get("engine")
        ed = part.get("engine_data") or {}
        if eng == "AWM2":
            for elem in ed.get("elements") or []:
                bank = elem.get("wave_bank")
                bank_code = elem.get("wave_bank_code")
                wave = elem.get("wave_number")
                if bank_code is not None and bank_code != 0:
                    key = ("waveform", pnum, elem.get("number"), bank_code, wave)
                    if key not in seen:
                        seen.add(key)
                        deps.append({
                            "kind": "external_waveform",
                            "part_number": pnum,
                            "element_number": elem.get("number"),
                            "bank": bank,
                            "bank_code": bank_code,
                            "wave_number": wave,
                            "resolution": "not_contained_in_performance_sysex",
                        })
        arp = part.get("arpeggio") or {}
        for slot in arp.get("slots") or []:
            bank = slot.get("bank")
            if slot.get("status") == "assigned" and bank not in (None, "preset"):

                key = ("arp", pnum, slot.get("slot"), bank, slot.get("arp_number"))
                if key not in seen:
                    seen.add(key)
                    deps.append({
                        "kind": "external_arpeggio",
                        "part_number": pnum,
                        "slot_number": slot.get("slot"),
                        "bank": bank,
                        "arp_number": slot.get("arp_number"),
                        "resolution": "not_contained_in_performance_sysex",
                    })
    return deps


def _target_assessment(perf: dict[str, Any], deps: list[dict[str, Any]]) -> dict[str, Any]:
    engines = sorted({p.get("engine") for p in perf.get("parts") or [] if p.get("engine")})
    classic_reasons: list[str] = []
    y2l_reasons: list[str] = []
    if "AN-X" in engines:
        classic_reasons.append("AN-X has no classic X7L engine representation")
    if any(d["kind"] == "external_waveform" for d in deps):
        classic_reasons.append("Performance references non-preset waveforms that are not carried by the .syx file")
        y2l_reasons.append("Performance references non-preset waveforms that require dependency material")
    if any(d["kind"] == "external_arpeggio" for d in deps):
        classic_reasons.append("Performance references User/Library Arps that are not carried by the .syx file")
        y2l_reasons.append("Performance references User/Library Arps that require dependency material")

    # Bridge readiness means semantic intermediate can be produced. It is deliberately
    # distinct from binary-writer readiness, because serializer integration is next.
    return {
        "classic_x7l_4_0_5": {
            "bridge_status": "blocked" if classic_reasons else "candidate",
            "reasons": classic_reasons,
            "serializer_integration": "not_connected",
        },
        "modx_m_y2l": {
            "bridge_status": "dependency_required" if y2l_reasons else "candidate",
            "reasons": y2l_reasons,
            "serializer_integration": "not_connected",
        },
    }


def build_ysfc_intermediate(normalized: dict[str, Any], *, source_file: str | None = None,
                            include_source_snapshot: bool = False) -> dict[str, Any]:
    deps = _dependencies(normalized)
    out: dict[str, Any] = {
        "bridge_schema_version": BRIDGE_SCHEMA_VERSION,
        "kind": KIND,
        "source": {
            "file": source_file,
            "profile": normalized.get("source_profile"),
            "model_id": normalized.get("model_id"),
            "normalized_schema_version": normalized.get("schema_version"),
            "transport_invalid_message_count": normalized.get("transport_invalid_message_count", 0),
            "normalization_warnings": _clone(normalized.get("normalization_warnings")),
        },
        "performance": {
            "name": normalized.get("name"),
            "common": {
                "tempo_bpm": normalized.get("tempo_bpm"),
                "volume": normalized.get("volume"),
                "pan": normalized.get("pan"),
                "main_category_code": normalized.get("main_category_code"),
                "sub_category_code": normalized.get("sub_category_code"),
                "arp_master_on": normalized.get("arp_master_on"),
                "motion_seq_master_on": normalized.get("motion_seq_master_on"),
            },
            "parts": [_part_bridge(p) for p in normalized.get("parts") or []],
            "scenes": [_scene_bridge(s) for s in normalized.get("scenes") or []],
            "provenance": _clone(normalized.get("provenance")),
        },
        "dependencies": deps,
        "coverage": {
            "mapped": [
                "performance common basics", "part identity/switches/mix/ranges",
                "part note shift", "scene part snapshots", "Arp switches and 8 slot references",
                "Insertion A/B type/routing/sidechain/raw parameter pairs",
                "legacy AWM2 element core", "FM-X core/operator subset", "AN-X oscillator subset"
            ],
            "deferred": [
                "complete controller/control-assign model", "complete Motion Sequence/Super Knob model",
                "complete drum-key parameter model", "complete M-generation AWM2 oscillator/waveform/filter model",
                "per-effect semantic parameter decoding", "global Reverb/Variation/Master Effect model",
                "binary serializer field offsets and final X7L/Y2L emission"
            ],
            "semantics": "partial_but_provenance_preserving"
        },
        "target_assessment": _target_assessment(normalized, deps),
        "bridge_notes": [
            "This is a semantic YSFC-oriented intermediate, not a binary X7L/Y2L file.",
            "Raw effect parameter pairs are preserved losslessly; per-effect parameter semantics remain deferred.",
            "Serializer-specific byte offsets are intentionally outside the SysEx parser project.",
        ],
    }
    if include_source_snapshot:
        out["normalized_source_snapshot"] = _clone(normalized)
    return out


def convert_sysex_file(path: Path, *, include_source_snapshot: bool = False) -> dict[str, Any]:
    parsed = sp.parse_file(path)
    return build_ysfc_intermediate(
        parsed.get("normalized_performance") or {},
        source_file=path.name,
        include_source_snapshot=include_source_snapshot,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert Yamaha Soundmondo .syx to YSFC-oriented intermediate JSON")
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--include-source-snapshot", action="store_true")
    args = ap.parse_args()
    result = convert_sysex_file(args.input, include_source_snapshot=args.include_source_snapshot)
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
