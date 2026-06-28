#!/usr/bin/env python3
"""Classic X7L/X8L -> X7L performance transcoding.

This module is intentionally independent of the existing classic -> Y2L
transcoder.  Its target is the MONTAGE classic performance layout (4.0.2).

X7L input is preserved byte-for-byte.  X8L input is parsed as MODX classic and
normalised to the X7L/MONTAGE block sizes documented by Yamaha/CWM:
  * common scenes: 8 x 21 -> 8 x 11
  * part manyParameters: 275 -> 274
  * part scenes: 8 x 22 -> 8 x 21 (target version 4.0.2)
  * AD input block: 143 -> 142
  * AWM2/Drum element extension: 5-byte tail -> 2-byte tail
The musical fields and opaque blocks common to both formats are retained.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from ysfc_serializer_classic import (
    FORMAT_MONTAGE,
    FORMAT_MODX,
    PART_TYPE_AWM2,
    PART_TYPE_DRUM,
    PART_TYPE_FMX,
    ClassicPerformance,
    parse_classic_blob,
)

TARGET_X7_VERSION = "4.0.2"
TARGET_X7_VERSION_INT = 402


@dataclass(frozen=True)
class X7TranscodeResult:
    blob: bytes
    source_format: str
    warnings: tuple[str, ...] = ()


def _scene_stride_convert(data: bytes, source_stride: int, target_stride: int) -> bytes:
    """Convert eight scene records while retaining their common prefix."""
    expected = 8 * source_stride
    if len(data) < expected:
        raise ValueError(f"scene block too short: {len(data)} < {expected}")
    return b"".join(
        data[i * source_stride:i * source_stride + target_stride]
        for i in range(8)
    )


def _normalise_x8_performance(perf: ClassicPerformance) -> tuple[ClassicPerformance, list[str]]:
    out = deepcopy(perf)
    warnings: list[str] = []
    out.fmt = FORMAT_MONTAGE
    out.version = TARGET_X7_VERSION_INT

    # Performance common: MODX has ten extra bytes per scene.
    out.scene_data = _scene_stride_convert(perf.scene_data, 21, 11)

    # MODX AD input has one additional byte at the end.
    if len(out.ad_part) == 143:
        out.ad_part = out.ad_part[:142]
    elif len(out.ad_part) != 142:
        warnings.append(f"unexpected AD-part size {len(out.ad_part)}; preserved")

    for part_index, part in enumerate(out.parts):
        if len(part.many_parameters) == 275:
            part.many_parameters = part.many_parameters[:274]
        elif len(part.many_parameters) != 274:
            warnings.append(
                f"part {part_index + 1}: unexpected manyParameters size "
                f"{len(part.many_parameters)}; preserved"
            )

        # X8L/5.0.1 uses 22 bytes per part scene; X7L/4.0.2 uses 21.
        if len(part.scenes) == 176:
            part.scenes = _scene_stride_convert(part.scenes, 22, 21)
        elif len(part.scenes) != 168:
            warnings.append(
                f"part {part_index + 1}: unexpected scene size {len(part.scenes)}; preserved"
            )

        if part.type in (PART_TYPE_AWM2, PART_TYPE_DRUM):
            for element in part.elements:
                # The three MODX-only bytes precede waveformNumber.
                element.unknown_bytes = None
        elif part.type == PART_TYPE_FMX:
            # FM-X payloads are opaque. Known classic blocks are compatible at
            # 67 bytes common + 8 x 51 byte operators. Reject unknown layouts
            # instead of silently producing corrupt X7L data.
            common_len = len(part.fmx_common_opaque or b"")
            op_lens = {len(op) for op in part.fmx_operator_opaque}
            if common_len != 67 or op_lens != {51}:
                raise ValueError(
                    f"part {part_index + 1}: unsupported X8L FM-X layout "
                    f"common={common_len}, operators={sorted(op_lens)}"
                )

    return out, warnings


def transcode_classic_blob_to_x7l(blob: bytes, source_version: str) -> X7TranscodeResult:
    """Return one classic Performance encoded for the X7L 4.0.2 target."""
    perf = parse_classic_blob(blob, source_version)
    if perf.fmt == FORMAT_MONTAGE:
        # 4.0.0 and 4.0.2 share the target part-scene width and can safely be
        # preserved.  4.0.5 introduced 22-byte part scenes and must therefore
        # be normalised to the 4.0.2 21-byte layout.
        if perf.version < 405:
            return X7TranscodeResult(blob=blob, source_format=perf.fmt)
        converted = deepcopy(perf)
        converted.version = TARGET_X7_VERSION_INT
        warnings: list[str] = []
        for part_index, part in enumerate(converted.parts):
            if len(part.scenes) == 176:
                part.scenes = _scene_stride_convert(part.scenes, 22, 21)
            elif len(part.scenes) != 168:
                warnings.append(
                    f"part {part_index + 1}: unexpected X7L scene size "
                    f"{len(part.scenes)}; preserved"
                )
        out = converted.to_blob()
        check = parse_classic_blob(out, TARGET_X7_VERSION)
        if check.to_blob() != out:
            raise ValueError("internal X7L 4.0.5 -> 4.0.2 round-trip validation failed")
        return X7TranscodeResult(
            blob=out,
            source_format=perf.fmt,
            warnings=tuple(warnings),
        )
    if perf.fmt != FORMAT_MODX:
        raise ValueError(f"unsupported classic source version {source_version!r}")

    converted, warnings = _normalise_x8_performance(perf)
    out = converted.to_blob()

    # Structural self-check: the result must be readable as X7L and stable.
    check = parse_classic_blob(out, TARGET_X7_VERSION)
    rebuilt = check.to_blob()
    if rebuilt != out:
        raise ValueError("internal X8L -> X7L round-trip validation failed")
    return X7TranscodeResult(
        blob=out,
        source_format=perf.fmt,
        warnings=tuple(warnings),
    )
