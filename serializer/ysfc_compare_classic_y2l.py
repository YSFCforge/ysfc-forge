#!/usr/bin/env python3
"""Compare matching X7L/X8L and Y2L libraries at Performance/engine level.

The tool matches Performances by normalized name (preserving duplicate order),
transcodes each classic Performance using the corresponding Y2L blob as a
structural reference, and compares the generated engine suffix against the
real Y2L engine suffix. A JSON report is written for regression testing.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ysfc_serializer_classic import parse_classic_blob
from ysfc_transcoder_classic_to_y2l import (
    SUBBLOB_COMMON_SIZE,
    SUBBLOB_DEFAULT_SIZE,
    AWM2_ENGINE_HEADER_SIZE,
    AWM2_ELEMENT_STRIDE,
    AWM2_LAST_ELEMENT_SIZE,
    ENGINE_POOL_SEP_SIZE,
    build_y2l_blob,
)


def u32be(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise ValueError(f"u32 out of range at {off}")
    return struct.unpack_from(">I", data, off)[0]


def read_container(path: Path) -> tuple[bytes, str, dict[str, int]]:
    data = path.read_bytes()
    if data[:11] != b"YAMAHA-YSFC":
        raise ValueError(f"{path.name}: not a YAMAHA-YSFC file")
    version = data[16:32].split(b"\0", 1)[0].decode("ascii", "replace")
    directory_size = u32be(data, 32)
    chunks: dict[str, int] = {}
    for off in range(64, 64 + directory_size, 8):
        tag_raw = data[off : off + 4]
        if tag_raw in (b"\0" * 4, b"\xff" * 4):
            break
        tag = tag_raw.decode("latin-1")
        chunk_off = u32be(data, off + 4)
        if chunk_off + 8 > len(data):
            raise ValueError(f"{path.name}: invalid {tag} offset {chunk_off}")
        chunks[tag] = chunk_off
    if "EPFM" not in chunks or "DPFM" not in chunks:
        raise ValueError(f"{path.name}: EPFM/DPFM missing")
    return data, version, chunks


def iter_tagged_records(payload: bytes, count: int, tag: bytes) -> Iterable[bytes]:
    pos = 4  # count
    for index in range(count):
        if payload[pos : pos + 4] == tag:
            pos += 4
        if pos + 4 > len(payload):
            raise ValueError(f"record {index}: missing length")
        length = u32be(payload, pos)
        pos += 4
        end = pos + length
        if end > len(payload):
            raise ValueError(f"record {index}: length exceeds payload")
        yield payload[pos:end]
        pos = end


def extract_performances(path: Path) -> tuple[str, list[dict]]:
    data, version, chunks = read_container(path)
    ep_off, dp_off = chunks["EPFM"], chunks["DPFM"]
    ep_size, dp_size = u32be(data, ep_off + 4), u32be(data, dp_off + 4)
    ep = data[ep_off + 8 : ep_off + 8 + ep_size]
    dp = data[dp_off + 8 : dp_off + 8 + dp_size]
    count = u32be(ep, 0)

    entries = list(iter_tagged_records(ep, count, b"Entr"))
    data_records = list(iter_tagged_records(dp, u32be(dp, 0), b"Data"))

    out = []
    for i, entry in enumerate(entries):
        length = u32be(entry, 0)
        offset = u32be(entry, 4)
        blob = None
        # Both classic and Y2L entries use absolute offsets into the DPFM payload
        # after the count; fall back to record order for unusual writers.
        if 0 <= offset <= len(dp) - length:
            candidate = dp[offset : offset + length]
            if len(candidate) == length:
                blob = candidate
        if blob is None and i < len(data_records):
            blob = data_records[i]
        if blob is None:
            raise ValueError(f"{path.name}: cannot resolve Performance {i}")

        # The blob name is the most reliable cross-format key.
        if path.suffix.lower() == ".y2l":
            name = blob[4:23].split(b"\0", 1)[0].decode("latin-1", "replace").strip()
        else:
            perf = parse_classic_blob(blob, version)
            name = perf.name
        out.append({"index": i, "name": name, "blob": blob})
    return version, out


def norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.casefold())


def diff_stats(expected: bytes, actual: bytes) -> dict:
    common = min(len(expected), len(actual))
    differing = sum(a != b for a, b in zip(expected[:common], actual[:common]))
    return {
        "expectedBytes": len(expected),
        "actualBytes": len(actual),
        "comparedBytes": common,
        "equalBytes": common - differing,
        "differentBytes": differing,
        "lengthDelta": len(expected) - len(actual),
        "equalPercent": round((common - differing) * 100.0 / common, 4) if common else 100.0,
        "exact": expected == actual,
    }



def engine_base_size(part_type: int) -> int:
    """Return native first-position Y2L engine size."""
    return {0: 2503, 1: 4963, 2: 1143}.get(part_type, 2503)

def engine_size(part_type: int, part_index: int = 0) -> int:
    """Return engine-pool span including the 5-byte prefix for Parts 2+."""
    return engine_base_size(part_type) + (ENGINE_POOL_SEP_SIZE if part_index > 0 else 0)


def engine_regions(part_type: int) -> list[tuple[str, int, int]]:
    """Describe stable internal regions of a generated Y2L engine block."""
    if part_type == 2:
        regions = [("fmxCommon", 0, 210)]
        for op in range(7):
            start = 210 + op * 123
            regions.append((f"operator[{op}]", start, start + 123))
        regions.append(("operator[7]", 210 + 7 * 123, 1143))
        return regions
    regions = [("engineHeader", 0, AWM2_ENGINE_HEADER_SIZE)]
    for elem in range(8):
        start = AWM2_ENGINE_HEADER_SIZE + elem * AWM2_ELEMENT_STRIDE
        size = AWM2_ELEMENT_STRIDE if elem < 7 else AWM2_LAST_ELEMENT_SIZE
        regions.append((f"element[{elem}]", start, start + size))
    return regions


def diff_positions(expected: bytes, actual: bytes, limit: int = 12) -> list[dict]:
    """Return the first differing positions with both byte values."""
    out = []
    for offset, (e, a) in enumerate(zip(expected, actual)):
        if e != a:
            out.append({"offset": offset, "generated": e, "actual": a})
            if len(out) >= limit:
                break
    return out


def compare_engine_parts(generated: bytes, actual: bytes, part_types: list[int]) -> list[dict]:
    """Compare engine suffixes part-by-part and by stable internal region."""
    results = []
    offset = 0
    for part_index, part_type in enumerate(part_types):
        size = engine_size(part_type, part_index)
        generated_part = generated[offset:offset + size]
        actual_part = actual[offset:offset + size]
        prefix = ENGINE_POOL_SEP_SIZE if part_index > 0 else 0
        regions = []
        if prefix:
            ps = diff_stats(generated_part[:prefix], actual_part[:prefix])
            ps.update({"label": "interEnginePrefix", "offset": 0, "firstDifferences": diff_positions(generated_part[:prefix], actual_part[:prefix])})
            regions.append(ps)
        for label, start, end in engine_regions(part_type):
            start += prefix
            end += prefix
            g = generated_part[start:end]
            a = actual_part[start:end]
            stats = diff_stats(g, a)
            stats["label"] = label
            stats["offset"] = start
            stats["firstDifferences"] = diff_positions(g, a)
            regions.append(stats)
        part_stats = diff_stats(generated_part, actual_part)
        part_stats.update({
            "partIndex": part_index,
            "partType": part_type,
            "engineOffset": offset,
            "regions": regions,
        })
        results.append(part_stats)
        offset += size
    return results

def compare_pair(classic_path: Path, y2l_path: Path) -> dict:
    classic_version, classic = extract_performances(classic_path)
    y2l_version, modern = extract_performances(y2l_path)

    modern_by_name: dict[str, deque] = defaultdict(deque)
    for item in modern:
        modern_by_name[norm_name(item["name"])].append(item)

    results = []
    unmatched_classic = []
    used_y2l_indices: set[int] = set()
    for c in classic:
        key = norm_name(c["name"])
        y = None
        match_method = "normalized-name"
        if key and modern_by_name[key]:
            y = modern_by_name[key].popleft()
        else:
            # Y2L names are limited to 18/19 visible bytes. For converted libraries
            # the source and destination order is normally preserved, so accept an
            # index match only when one normalized name is a prefix of the other.
            if c["index"] < len(modern):
                candidate = modern[c["index"]]
                ck, yk = norm_name(c["name"]), norm_name(candidate["name"])
                if candidate["index"] not in used_y2l_indices and ck and yk and (ck.startswith(yk) or yk.startswith(ck)):
                    y = candidate
                    match_method = "same-index-truncated-prefix"
                    q = modern_by_name.get(yk)
                    if q:
                        try:
                            q.remove(candidate)
                        except ValueError:
                            pass
        if y is None:
            unmatched_classic.append({"index": c["index"], "name": c["name"]})
            continue
        used_y2l_indices.add(y["index"])
        perf = parse_classic_blob(c["blob"], classic_version)
        generated = build_y2l_blob(perf, ref_blob=y["blob"])
        n_parts = min(16, len(perf.parts))
        engine_start = SUBBLOB_COMMON_SIZE + n_parts * SUBBLOB_DEFAULT_SIZE
        generated_engine = generated[engine_start:]
        actual_engine = y["blob"][engine_start:]
        part_types = [p.type for p in perf.parts[:n_parts]]
        results.append({
            "classicIndex": c["index"],
            "y2lIndex": y["index"],
            "name": c["name"],
            "y2lName": y["name"],
            "matchMethod": match_method,
            "partCount": n_parts,
            "partTypes": part_types,
            "wholeBlob": diff_stats(generated, y["blob"]),
            "engineSuffix": diff_stats(generated_engine, actual_engine),
            "engineParts": compare_engine_parts(generated_engine, actual_engine, part_types),
        })

    unmatched_y2l = []
    for queue in modern_by_name.values():
        unmatched_y2l.extend({"index": x["index"], "name": x["name"]} for x in queue)

    compared = len(results)
    exact_engines = sum(r["engineSuffix"]["exact"] for r in results)
    total_compared = sum(r["engineSuffix"]["comparedBytes"] for r in results)
    total_equal = sum(r["engineSuffix"]["equalBytes"] for r in results)
    by_type: dict[str, dict] = {}
    for r in results:
        signature = ",".join(map(str, r["partTypes"]))
        agg = by_type.setdefault(signature, {"performances": 0, "comparedBytes": 0, "equalBytes": 0, "exact": 0})
        agg["performances"] += 1
        agg["comparedBytes"] += r["engineSuffix"]["comparedBytes"]
        agg["equalBytes"] += r["engineSuffix"]["equalBytes"]
        agg["exact"] += int(r["engineSuffix"]["exact"])
    for agg in by_type.values():
        agg["equalPercent"] = round(agg["equalBytes"] * 100.0 / agg["comparedBytes"], 4) if agg["comparedBytes"] else 100.0

    by_engine_type: dict[str, dict] = {}
    by_region: dict[str, dict] = {}
    mismatch_offsets: dict[str, Counter] = defaultdict(Counter)
    for result in results:
        for part in result["engineParts"]:
            type_key = str(part["partType"])
            agg = by_engine_type.setdefault(type_key, {"parts": 0, "comparedBytes": 0, "equalBytes": 0, "exact": 0})
            agg["parts"] += 1
            agg["comparedBytes"] += part["comparedBytes"]
            agg["equalBytes"] += part["equalBytes"]
            agg["exact"] += int(part["exact"])
            for region in part["regions"]:
                region_key = f"{type_key}:{region['label']}"
                ragg = by_region.setdefault(region_key, {
                    "partType": part["partType"], "label": region["label"],
                    "instances": 0, "comparedBytes": 0, "equalBytes": 0, "exact": 0,
                })
                ragg["instances"] += 1
                ragg["comparedBytes"] += region["comparedBytes"]
                ragg["equalBytes"] += region["equalBytes"]
                ragg["exact"] += int(region["exact"])
                for diff in region["firstDifferences"]:
                    mismatch_offsets[region_key][diff["offset"]] += 1
    for agg in by_engine_type.values():
        agg["equalPercent"] = round(agg["equalBytes"] * 100.0 / agg["comparedBytes"], 4) if agg["comparedBytes"] else 100.0
    for key, agg in by_region.items():
        agg["equalPercent"] = round(agg["equalBytes"] * 100.0 / agg["comparedBytes"], 4) if agg["comparedBytes"] else 100.0
        agg["frequentEarlyMismatchOffsets"] = [
            {"offset": off, "occurrences": count}
            for off, count in mismatch_offsets[key].most_common(12)
        ]

    return {
        "schema": "ysfc-forge-classic-y2l-compare-v3",
        "classicFile": classic_path.name,
        "classicVersion": classic_version,
        "y2lFile": y2l_path.name,
        "y2lVersion": y2l_version,
        "summary": {
            "classicPerformances": len(classic),
            "y2lPerformances": len(modern),
            "matchedPerformances": compared,
            "unmatchedClassic": len(unmatched_classic),
            "unmatchedY2l": len(unmatched_y2l),
            "exactEngineSuffixes": exact_engines,
            "engineEqualPercent": round(total_equal * 100.0 / total_compared, 4) if total_compared else 100.0,
        },
        "byPartTypeSignature": by_type,
        "byEngineType": by_engine_type,
        "byEngineRegion": by_region,
        "unmatchedClassicEntries": unmatched_classic,
        "unmatchedY2lEntries": unmatched_y2l,
        "performances": results,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("classic", type=Path)
    ap.add_argument("y2l", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args()
    report = compare_pair(args.classic, args.y2l)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
