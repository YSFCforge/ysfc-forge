#!/usr/bin/env python3
"""Profile-aware classic X7L writer and X7L/X8L -> X7L converter.

The existing classic -> Y2L path is intentionally untouched.  This writer
normalises supported classic containers to an X7L 4.0.2 target while retaining
the source container family (minimal, standard, extended, etc.) whenever the
family only contains X7-compatible sections.

Observed classic container dimensions are not fixed:
* the section catalogue at 0x40 can contain 2, 6, 12, 14, 18, ... entries;
* the library metadata region between catalogue and first section can be empty,
  81 bytes, 2040 bytes, or another valid length;
* X8L adds section types which must not be emitted in X7L.

Consequently no constant 12-entry catalogue or 81-byte metadata region is
assumed here.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct
from typing import Iterable, Sequence
import json
import hashlib
import os
import tempfile

from ysfc_serializer_classic import parse_classic_blob

from ysfc_transcoder_classic_to_x7l import (
    TARGET_X7_VERSION,
    transcode_classic_blob_to_x7l,
)

MAGIC = b"YAMAHA-YSFC"
TARGET_VERSION_FIELD = TARGET_X7_VERSION.encode("ascii").ljust(16, b"\0")
X7_CONTENT_NUMBER_BASE = 0x003F1000

# X8-only catalogue sections observed in MODX libraries.  Empty curve sections
# are known additions in 5.x and are not part of verified X7L catalogues.
X8_ONLY_TAGS = frozenset({"ECRV", "DCRV"})
WAVE_DEPENDENCY_TAGS = ("EWFM", "DWFM", "EWIM", "DWIM")
ARP_DEPENDENCY_TAGS = ("EARP", "DARP")
PERFORMANCE_TAGS = frozenset({"EPFM", "DPFM"})


def _u32be(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise ValueError(f"u32 out of range at {off}")
    return struct.unpack_from(">I", data, off)[0]


def _p32(value: int) -> bytes:
    return struct.pack(">I", value)


@dataclass(frozen=True)
class ClassicContainerProfile:
    version: str
    catalogue_size: int
    catalogue_entries: int
    library_region_size: int
    first_section_offset: int
    order: tuple[str, ...]
    source_family: str

    @property
    def profile_id(self) -> str:
        return (
            f"{self.version}_D{self.catalogue_size:02X}_"
            f"N{self.catalogue_entries}_L{self.library_region_size:X}_"
            f"F{self.first_section_offset:X}"
        )


@dataclass(frozen=True)
class ClassicContainer:
    data: bytes
    version: str
    header: bytes
    gap: bytes
    order: tuple[str, ...]
    payloads: dict[str, bytes]
    profile: ClassicContainerProfile


@dataclass(frozen=True)
class ClassicEntry:
    raw: bytes
    blob: bytes


@dataclass(frozen=True)
class ClassicWaveformBundle:
    ewfm_entry: bytes
    dwfm_data: bytes
    ewim_entry: bytes
    dwim_data: bytes

    @property
    def dedup_key(self) -> tuple[bytes, bytes, bytes, bytes]:
        # The first 12 bytes of entry records are rebuilt (length, offset and
        # content number). Everything after that is semantic metadata.
        return (self.ewfm_entry[12:], self.dwfm_data, self.ewim_entry[12:], self.dwim_data)




@dataclass(frozen=True)
class ClassicArpeggioBundle:
    """One classic user-arpeggio metadata/data pair.

    The first 12 bytes of EARP are transport metadata (data length, DARP
    offset and content number).  The remaining bytes plus the DARP record are
    the semantic arpeggio payload and can therefore be compared independently
    of source-local numbering.
    """

    earp_entry: bytes
    darp_data: bytes

    @property
    def dedup_key(self) -> tuple[bytes, bytes]:
        return (self.earp_entry[12:], self.darp_data)


@dataclass(frozen=True)
class ClassicMergeSource:
    source: bytes | Path | str
    selected_indices: tuple[int, ...] | None = None
    label: str | None = None


@dataclass(frozen=True)
class MergePerformanceItem:
    output_index: int
    source_number: int
    source_label: str
    source_index: int
    source_position: int
    name: str

    def to_dict(self) -> dict[str, int | str]:
        return {
            "outputIndex": self.output_index,
            "outputPosition": self.output_index + 1,
            "sourceNumber": self.source_number,
            "sourceLabel": self.source_label,
            "sourceIndex": self.source_index,
            "sourcePosition": self.source_position,
            "name": self.name,
        }






@dataclass(frozen=True)
class ClassicMergePreflightReport:
    """Serializable dry-run result for an ordered classic merge.

    A preflight performs the same parser, transcoder and dependency validation
    as the real writer, but does not write an output file.  This makes errors
    visible before the user commits to an export.
    """

    ok: bool
    source_count: int
    performance_count: int
    target_version: str
    estimated_output_bytes: int | None
    source_versions: tuple[str, ...] = ()
    source_profiles: tuple[str, ...] = ()
    performances: tuple[MergePerformanceItem, ...] = ()
    warnings: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "ysfc-forge-x7l-merge-preflight-v1",
            "ok": self.ok,
            "targetVersion": self.target_version,
            "sourceCount": self.source_count,
            "performanceCount": self.performance_count,
            "estimatedOutputBytes": self.estimated_output_bytes,
            "sourceVersions": list(self.source_versions),
            "sourceProfiles": list(self.source_profiles),
            "performances": [item.to_dict() for item in self.performances],
            "warnings": list(self.warnings),
            "blockers": list(self.blockers),
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent) + "\n"




@dataclass(frozen=True)
class ClassicMergeExportReceipt:
    """Verification receipt for one transactional merge export."""

    ok: bool
    output_path: str
    manifest_path: str | None
    preflight_path: str | None
    output_bytes: int
    output_sha256: str
    target_version: str
    source_count: int
    performance_count: int
    estimated_output_bytes: int
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "ysfc-forge-x7l-merge-export-receipt-v1",
            "ok": self.ok,
            "targetVersion": self.target_version,
            "sourceCount": self.source_count,
            "performanceCount": self.performance_count,
            "estimatedOutputBytes": self.estimated_output_bytes,
            "outputBytes": self.output_bytes,
            "outputSha256": self.output_sha256,
            "outputPath": self.output_path,
            "manifestPath": self.manifest_path,
            "preflightPath": self.preflight_path,
            "warnings": list(self.warnings),
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent) + "\n"


@dataclass(frozen=True)
class ClassicArpeggioReferenceCandidate:
    """A conservative candidate for a classic user-arpeggio reference.

    ``aligned`` marks candidates found on a 32-bit boundary.  Unaligned hits are
    retained for backwards-compatible diagnostics but must never be treated as
    fields: most are overlapping windows around another integer.  Candidates
    are never rewritten automatically.
    """

    offset: int
    arp_id: int
    raw_value: int
    aligned: bool = False


@dataclass(frozen=True)
class ClassicDependencyUsage:
    """Dependencies directly observable in selected Performance blobs.

    Classic AWM2 and Drum elements expose user/library waveform references as
    ``wave_bank != 0`` plus a source-local 1-based waveform number. FM-X has no
    waveform elements. Arpeggio references are not decoded yet and are therefore
    handled conservatively at section level by the multi-source merger.
    """

    user_waveform_ids: tuple[int, ...] = ()
    arpeggio_candidates: tuple[ClassicArpeggioReferenceCandidate, ...] = ()

    @property
    def uses_user_waveforms(self) -> bool:
        return bool(self.user_waveform_ids)

    @property
    def has_nonzero_arpeggio_candidates(self) -> bool:
        return bool(self.arpeggio_candidates)


def scan_classic_arpeggio_reference_candidates(
    blob: bytes, version: str, pool_size: int
) -> tuple[ClassicArpeggioReferenceCandidate, ...]:
    """Locate conservative non-zero user-arpeggio reference candidates.

    The classic Performance tail is not yet field-decoded.  Observed user arp
    references use a 32-bit big-endian content number ``0x00010000 + id``.
    ID zero is deliberately excluded because the same value is also used in
    many default/empty slots.  Returned positions are diagnostics only.
    """
    if pool_size <= 1:
        return ()
    performance = parse_classic_blob(blob, version)
    tail = performance.play_settings
    candidates: list[ClassicArpeggioReferenceCandidate] = []
    for offset in range(0, max(0, len(tail) - 3)):
        value = int.from_bytes(tail[offset:offset + 4], "big")
        arp_id = value - 0x00010000
        if 1 <= arp_id < pool_size:
            candidates.append(ClassicArpeggioReferenceCandidate(
                offset, arp_id, value, aligned=(offset % 4 == 0)
            ))
    return tuple(candidates)



@dataclass(frozen=True)
class ClassicArpeggioCandidateOffsetProfile:
    """Aggregate evidence for one candidate offset across Performances."""

    offset: int
    occurrence_count: int
    performance_count: int
    arp_ids: tuple[int, ...]
    aligned: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "offset": self.offset,
            "occurrenceCount": self.occurrence_count,
            "performanceCount": self.performance_count,
            "arpIds": list(self.arp_ids),
            "aligned": self.aligned,
        }


def profile_classic_arpeggio_candidate_offsets(
    blobs: Iterable[bytes], version: str, pool_size: int, *, aligned_only: bool = True
) -> tuple[ClassicArpeggioCandidateOffsetProfile, ...]:
    """Rank candidate positions without claiming that they are arp fields.

    The report is intentionally evidence-only.  By default only 32-bit-aligned
    positions are included, eliminating overlapping byte windows from the Step
    131 scanner.  A position appearing in several Performances is useful for
    reverse engineering, but is still not rewritten until a controlled oracle
    pair confirms its meaning.
    """
    by_offset: dict[int, list[tuple[int, int]]] = {}
    for performance_index, blob in enumerate(blobs):
        for candidate in scan_classic_arpeggio_reference_candidates(blob, version, pool_size):
            if aligned_only and not candidate.aligned:
                continue
            by_offset.setdefault(candidate.offset, []).append(
                (performance_index, candidate.arp_id)
            )
    profiles = []
    for offset, hits in by_offset.items():
        profiles.append(ClassicArpeggioCandidateOffsetProfile(
            offset=offset,
            occurrence_count=len(hits),
            performance_count=len({performance_index for performance_index, _ in hits}),
            arp_ids=tuple(sorted({arp_id for _, arp_id in hits})),
            aligned=(offset % 4 == 0),
        ))
    return tuple(sorted(
        profiles,
        key=lambda item: (-item.performance_count, -item.occurrence_count, item.offset),
    ))

@dataclass(frozen=True)
class ClassicArpeggioPeriodicFamilyProfile:
    """Evidence that candidate offsets repeat with a fixed record stride.

    This is still diagnostic only. Repetition is useful because real slot fields
    commonly recur at the same relative position in fixed-size records, whereas
    accidental 32-bit content-number matches are usually isolated.
    """

    stride: int
    residue: int
    offsets: tuple[int, ...]
    occurrence_count: int
    performance_count: int
    arp_ids: tuple[int, ...]
    contiguous_run_count: int
    longest_contiguous_run: int
    evidence_score: float

    def to_dict(self) -> dict[str, object]:
        return {
            "stride": self.stride,
            "residue": self.residue,
            "offsets": list(self.offsets),
            "occurrenceCount": self.occurrence_count,
            "performanceCount": self.performance_count,
            "arpIds": list(self.arp_ids),
            "contiguousRunCount": self.contiguous_run_count,
            "longestContiguousRun": self.longest_contiguous_run,
            "evidenceScore": self.evidence_score,
        }


def profile_classic_arpeggio_periodic_families(
    blobs: Iterable[bytes],
    version: str,
    pool_size: int,
    *,
    stride: int = 48,
    minimum_offsets: int = 2,
) -> tuple[ClassicArpeggioPeriodicFamilyProfile, ...]:
    """Group aligned candidates by position within a repeated record stride.

    The default 48-byte stride is an observed classic play-settings record
    spacing. The function does not declare any grouped position to be an arp
    field and never modifies input data.
    """
    if stride <= 0 or stride % 4:
        raise ValueError("stride must be a positive multiple of four")
    hits_by_offset: dict[int, list[tuple[int, int]]] = {}
    for performance_index, blob in enumerate(blobs):
        for candidate in scan_classic_arpeggio_reference_candidates(blob, version, pool_size):
            if candidate.aligned:
                hits_by_offset.setdefault(candidate.offset, []).append(
                    (performance_index, candidate.arp_id)
                )

    grouped: dict[int, list[int]] = {}
    for offset in hits_by_offset:
        grouped.setdefault(offset % stride, []).append(offset)

    families: list[ClassicArpeggioPeriodicFamilyProfile] = []
    for residue, offsets_raw in grouped.items():
        offsets = tuple(sorted(offsets_raw))
        if len(offsets) < minimum_offsets:
            continue
        runs: list[int] = []
        current = 1
        for previous, current_offset in zip(offsets, offsets[1:]):
            if current_offset - previous == stride:
                current += 1
            else:
                runs.append(current)
                current = 1
        runs.append(current)
        all_hits = [hit for offset in offsets for hit in hits_by_offset[offset]]
        occurrence_count = len(all_hits)
        performance_count = len({performance_index for performance_index, _ in all_hits})
        arp_ids = tuple(sorted({arp_id for _, arp_id in all_hits}))
        longest = max(runs)
        contiguous_runs = sum(1 for run in runs if run >= 2)
        # Evidence-only ranking. Diversity gets a small bonus, but repeated
        # offsets and consecutive stride runs dominate the score.
        score = round(
            len(offsets) * 2.0
            + performance_count * 0.5
            + longest * 2.5
            + contiguous_runs
            + min(len(arp_ids), 4) * 0.25,
            3,
        )
        families.append(ClassicArpeggioPeriodicFamilyProfile(
            stride=stride,
            residue=residue,
            offsets=offsets,
            occurrence_count=occurrence_count,
            performance_count=performance_count,
            arp_ids=arp_ids,
            contiguous_run_count=contiguous_runs,
            longest_contiguous_run=longest,
            evidence_score=score,
        ))
    return tuple(sorted(
        families,
        key=lambda item: (-item.evidence_score, -item.performance_count, item.residue),
    ))



@dataclass(frozen=True)
class ClassicArpeggioFieldLikelihoodProfile:
    """Evidence ranking for one aligned candidate field position.

    The score deliberately penalises positions dominated by arp ID 1 because
    that value is frequently indistinguishable from a classic default/content
    marker.  This remains diagnostic-only and is not used for rewriting.
    """

    offset: int
    occurrence_count: int
    performance_count: int
    arp_ids: tuple[int, ...]
    dominant_arp_id: int
    dominant_share: float
    nondefault_occurrence_count: int
    nondefault_arp_ids: tuple[int, ...]
    periodic_support: int
    likelihood_score: float

    def to_dict(self) -> dict[str, object]:
        return {
            "offset": self.offset,
            "occurrenceCount": self.occurrence_count,
            "performanceCount": self.performance_count,
            "arpIds": list(self.arp_ids),
            "dominantArpId": self.dominant_arp_id,
            "dominantShare": self.dominant_share,
            "nondefaultOccurrenceCount": self.nondefault_occurrence_count,
            "nondefaultArpIds": list(self.nondefault_arp_ids),
            "periodicSupport": self.periodic_support,
            "likelihoodScore": self.likelihood_score,
        }


def profile_classic_arpeggio_field_likelihood(
    blobs: Iterable[bytes],
    version: str,
    pool_size: int,
    *,
    stride: int = 48,
) -> tuple[ClassicArpeggioFieldLikelihoodProfile, ...]:
    """Rank aligned candidate offsets using diversity and periodic support.

    A likely assignment field should recur at a stable aligned offset, show
    more than the ambiguous default-like ID 1, and preferably belong to a
    repeated 48-byte slot family.  The result is evidence only.
    """
    if stride <= 0 or stride % 4:
        raise ValueError("stride must be a positive multiple of four")
    hits_by_offset: dict[int, list[tuple[int, int]]] = {}
    for performance_index, blob in enumerate(blobs):
        for candidate in scan_classic_arpeggio_reference_candidates(blob, version, pool_size):
            if candidate.aligned:
                hits_by_offset.setdefault(candidate.offset, []).append(
                    (performance_index, candidate.arp_id)
                )

    offsets_by_residue: dict[int, set[int]] = {}
    for offset in hits_by_offset:
        offsets_by_residue.setdefault(offset % stride, set()).add(offset)

    profiles: list[ClassicArpeggioFieldLikelihoodProfile] = []
    for offset, hits in hits_by_offset.items():
        counts: dict[int, int] = {}
        for _, arp_id in hits:
            counts[arp_id] = counts.get(arp_id, 0) + 1
        dominant_arp_id, dominant_count = max(
            counts.items(), key=lambda item: (item[1], -item[0])
        )
        occurrence_count = len(hits)
        performance_count = len({performance_index for performance_index, _ in hits})
        nondefault_occurrence_count = sum(
            count for arp_id, count in counts.items() if arp_id != 1
        )
        nondefault_arp_ids = tuple(sorted(arp_id for arp_id in counts if arp_id != 1))
        family_offsets = offsets_by_residue[offset % stride]
        periodic_support = sum(
            1 for other in family_offsets
            if other != offset and abs(other - offset) % stride == 0
        )
        dominant_share = dominant_count / occurrence_count
        # Reward independent Performances, non-default values and periodic
        # support. Strong ID-1 dominance is intentionally penalised.
        score = round(
            performance_count * 1.0
            + nondefault_occurrence_count * 2.5
            + len(nondefault_arp_ids) * 2.0
            + min(periodic_support, 4) * 1.5
            - (dominant_share * 4.0 if dominant_arp_id == 1 else 0.0),
            3,
        )
        profiles.append(ClassicArpeggioFieldLikelihoodProfile(
            offset=offset,
            occurrence_count=occurrence_count,
            performance_count=performance_count,
            arp_ids=tuple(sorted(counts)),
            dominant_arp_id=dominant_arp_id,
            dominant_share=round(dominant_share, 6),
            nondefault_occurrence_count=nondefault_occurrence_count,
            nondefault_arp_ids=nondefault_arp_ids,
            periodic_support=periodic_support,
            likelihood_score=score,
        ))
    return tuple(sorted(
        profiles,
        key=lambda item: (-item.likelihood_score, -item.nondefault_occurrence_count, item.offset),
    ))

def inspect_classic_dependency_usage(blobs: Iterable[bytes], version: str, arpeggio_pool_size: int = 0) -> ClassicDependencyUsage:
    ids: set[int] = set()
    arp_candidates: list[ClassicArpeggioReferenceCandidate] = []
    for blob in blobs:
        performance = parse_classic_blob(blob, version)
        if arpeggio_pool_size:
            arp_candidates.extend(scan_classic_arpeggio_reference_candidates(blob, version, arpeggio_pool_size))
        for part in performance.parts:
            for element in part.elements:
                if element.wave_bank != 0:
                    ids.add(int(element.waveform_number))
    return ClassicDependencyUsage(
        user_waveform_ids=tuple(sorted(ids)),
        arpeggio_candidates=tuple(arp_candidates),
    )


def _empty_count_payload(payload: bytes | None) -> bool:
    return payload in (None, b"\0\0\0\0")


def _dependency_signature(container: ClassicContainer, tags: Iterable[str]) -> tuple[tuple[str, bytes | None], ...]:
    return tuple((tag, container.payloads.get(tag)) for tag in tags)


@dataclass(frozen=True)
class X7FileResult:
    data: bytes
    source_version: str
    performance_count: int
    source_profile_id: str
    target_profile_id: str
    selected_indices: tuple[int, ...] = ()
    warnings: tuple[str, ...] = ()
    source_count: int = 1
    performance_items: tuple[MergePerformanceItem, ...] = ()

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "ysfc-forge-x7l-merge-manifest-v1",
            "targetVersion": TARGET_X7_VERSION,
            "sourceVersion": self.source_version,
            "sourceCount": self.source_count,
            "performanceCount": self.performance_count,
            "sourceProfileId": self.source_profile_id,
            "targetProfileId": self.target_profile_id,
            "performances": [item.to_dict() for item in self.performance_items],
            "warnings": list(self.warnings),
        }

    def manifest_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.manifest(), ensure_ascii=False, indent=indent) + "\n"


def _source_family(version: str) -> str:
    try:
        major = int(version.split(".", 1)[0])
    except (ValueError, IndexError):
        raise ValueError(f"unsupported classic version field {version!r}")
    if major == 4:
        return "X7L"
    if major == 5:
        return "X8L"
    raise ValueError(f"unsupported classic major version {version!r}")


def _source_label(source: bytes | Path | str, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    if isinstance(source, (Path, str)):
        return Path(source).name
    return "in-memory source"


def _performance_name(blob: bytes, version: str) -> str:
    return parse_classic_blob(blob, version).name


def read_classic_container(source: bytes | bytearray | memoryview | Path | str) -> ClassicContainer:
    data = Path(source).read_bytes() if isinstance(source, (Path, str)) else bytes(source)
    if data[:11] != MAGIC:
        raise ValueError("not a YAMAHA-YSFC container")
    if len(data) < 64:
        raise ValueError("truncated YSFC header")
    version = data[16:32].split(b"\0", 1)[0].decode("ascii", "replace")
    family = _source_family(version)
    catalogue_size = _u32be(data, 32)
    if catalogue_size == 0 or catalogue_size % 8:
        raise ValueError(f"invalid catalogue size {catalogue_size}")
    catalogue_entries = catalogue_size // 8
    directory_end = 64 + catalogue_size
    if directory_end > len(data):
        raise ValueError("section catalogue exceeds file")

    order: list[str] = []
    offsets: dict[str, int] = {}
    for off in range(64, directory_end, 8):
        tag_raw = data[off:off + 4]
        if tag_raw in (b"\0" * 4, b"\xff" * 4):
            continue
        tag = tag_raw.decode("latin-1")
        if tag in offsets:
            raise ValueError(f"duplicate catalogue tag {tag}")
        chunk_off = _u32be(data, off + 4)
        if chunk_off + 8 > len(data):
            raise ValueError(f"invalid {tag} chunk offset {chunk_off}")
        order.append(tag)
        offsets[tag] = chunk_off

    if not order:
        raise ValueError("empty section catalogue")
    first_chunk = min(offsets.values())
    if first_chunk < directory_end:
        raise ValueError("first section overlaps catalogue")
    gap = data[directory_end:first_chunk]

    # Header x30 is normally the library-region length.  Some historical files
    # may not mirror it, so actual offsets are authoritative but disagreement is
    # rejected when it would imply overlapping data.
    header_library_size = _u32be(data, 48)
    if header_library_size != len(gap) and directory_end + header_library_size > first_chunk:
        raise ValueError("header library-region size overlaps first section")

    payloads: dict[str, bytes] = {}
    ranges: list[tuple[int, int, str]] = []
    for tag in order:
        off = offsets[tag]
        actual_tag = data[off:off + 4].decode("latin-1")
        if actual_tag != tag:
            raise ValueError(f"catalogue tag {tag} points to {actual_tag}")
        size = _u32be(data, off + 4)
        end = off + 8 + size
        if end > len(data):
            raise ValueError(f"{tag} payload exceeds file")
        ranges.append((off, end, tag))
        payloads[tag] = data[off + 8:end]
    ranges.sort()
    for previous, current in zip(ranges, ranges[1:]):
        if previous[1] > current[0]:
            raise ValueError(f"sections {previous[2]} and {current[2]} overlap")

    profile = ClassicContainerProfile(
        version=version,
        catalogue_size=catalogue_size,
        catalogue_entries=catalogue_entries,
        library_region_size=len(gap),
        first_section_offset=first_chunk,
        order=tuple(order),
        source_family=family,
    )
    return ClassicContainer(
        data=data,
        version=version,
        header=data[:64],
        gap=gap,
        order=tuple(order),
        payloads=payloads,
        profile=profile,
    )


def _iter_tagged_records(payload: bytes, expected_tag: bytes) -> list[bytes]:
    if len(payload) < 4:
        raise ValueError("record payload too short")
    count = _u32be(payload, 0)
    pos = 4
    records: list[bytes] = []
    for index in range(count):
        if pos + 8 > len(payload) or payload[pos:pos + 4] != expected_tag:
            raise ValueError(f"record {index}: expected {expected_tag!r}")
        pos += 4
        length = _u32be(payload, pos)
        pos += 4
        end = pos + length
        if end > len(payload):
            raise ValueError(f"record {index}: exceeds section")
        records.append(payload[pos:end])
        pos = end
    if pos != len(payload):
        raise ValueError(f"unexpected {len(payload) - pos} trailing record bytes")
    return records


def extract_classic_entries(container: ClassicContainer) -> list[ClassicEntry]:
    try:
        epfm = container.payloads["EPFM"]
        dpfm = container.payloads["DPFM"]
    except KeyError as exc:
        raise ValueError("EPFM/DPFM missing") from exc
    entries = _iter_tagged_records(epfm, b"Entr")
    data_records = _iter_tagged_records(dpfm, b"Data")
    if len(entries) != len(data_records):
        raise ValueError("EPFM and DPFM record counts differ")
    out: list[ClassicEntry] = []
    for index, (entry, record_blob) in enumerate(zip(entries, data_records)):
        if len(entry) < 12:
            raise ValueError(f"EPFM entry {index} too short")
        declared_length = _u32be(entry, 0)
        if declared_length != len(record_blob):
            raise ValueError(
                f"EPFM entry {index} length {declared_length} != DPFM {len(record_blob)}"
            )
        out.append(ClassicEntry(raw=entry, blob=record_blob))
    return out


def _tagged_payload(tag: bytes, records: Iterable[bytes]) -> bytes:
    records = list(records)
    out = bytearray(_p32(len(records)))
    for record in records:
        out += tag
        out += _p32(len(record))
        out += record
    return bytes(out)



def extract_arpeggio_bundles(container: ClassicContainer) -> list[ClassicArpeggioBundle]:
    """Parse and validate paired EARP/DARP records.

    Empty classic pools are represented by a four-byte zero count.  For a
    non-empty pool, each EARP entry must point at the corresponding DARP record
    and declare its exact length.
    """
    earp_payload = container.payloads.get("EARP")
    darp_payload = container.payloads.get("DARP")
    if _empty_count_payload(earp_payload) and _empty_count_payload(darp_payload):
        return []
    if earp_payload is None or darp_payload is None:
        raise ValueError("incomplete arpeggio dependency sections")
    earp = _iter_tagged_records(earp_payload, b"Entr")
    darp = _iter_tagged_records(darp_payload, b"Data")
    if len(earp) != len(darp):
        raise ValueError("EARP/DARP record counts differ")
    bundles: list[ClassicArpeggioBundle] = []
    expected_offset = 12
    for index, (entry, data) in enumerate(zip(earp, darp), start=1):
        if len(entry) < 12:
            raise ValueError(f"arpeggio entry {index} too short")
        if _u32be(entry, 0) != len(data):
            raise ValueError(f"arpeggio entry {index} length mismatch")
        if _u32be(entry, 4) != expected_offset:
            raise ValueError(
                f"arpeggio entry {index} offset {_u32be(entry, 4)} != {expected_offset}"
            )
        bundles.append(ClassicArpeggioBundle(entry, data))
        expected_offset += 8 + len(data)
    return bundles


def rebuild_arpeggio_chunks(
    bundles: Sequence[ClassicArpeggioBundle],
) -> dict[str, bytes]:
    """Rebuild EARP/DARP with compact offsets and X7 user content numbers."""
    entries: list[bytes] = []
    data_records: list[bytes] = []
    data_offset = 12
    for arp_number, bundle in enumerate(bundles, start=1):
        entry = bytearray(bundle.earp_entry)
        entry[0:4] = _p32(len(bundle.darp_data))
        entry[4:8] = _p32(data_offset)
        # Observed classic user-arpeggio entries use 0x00010000 + zero-based ID.
        entry[8:12] = _p32(0x00010000 + arp_number - 1)
        entries.append(bytes(entry))
        data_records.append(bundle.darp_data)
        data_offset += 8 + len(bundle.darp_data)
    return {
        "EARP": _tagged_payload(b"Entr", entries),
        "DARP": _tagged_payload(b"Data", data_records),
    }


def _semantic_arpeggio_signature(container: ClassicContainer) -> tuple[tuple[bytes, bytes], ...]:
    return tuple(bundle.dedup_key for bundle in extract_arpeggio_bundles(container))


def extract_waveform_bundles(container: ClassicContainer) -> list[ClassicWaveformBundle]:
    """Extract source-local waveform+sample records as indivisible bundles.

    Classic files keep one EWFM/DWFM record pair and one EWIM/DWIM record pair
    per user waveform. DWFM keybanks refer only to sample records inside the
    corresponding DWIM item, so retaining all four records together avoids any
    need to rewrite internal keybank-to-sample references.
    """
    payloads = [container.payloads.get(tag) for tag in WAVE_DEPENDENCY_TAGS]
    if all(_empty_count_payload(payload) for payload in payloads):
        return []
    if any(payload is None for payload in payloads):
        raise ValueError("incomplete waveform dependency sections")
    ewfm = _iter_tagged_records(payloads[0], b"Entr")
    dwfm = _iter_tagged_records(payloads[1], b"Data")
    ewim = _iter_tagged_records(payloads[2], b"Entr")
    dwim = _iter_tagged_records(payloads[3], b"Data")
    counts = {len(ewfm), len(dwfm), len(ewim), len(dwim)}
    if len(counts) != 1:
        raise ValueError("EWFM/DWFM/EWIM/DWIM record counts differ")
    bundles: list[ClassicWaveformBundle] = []
    for index, records in enumerate(zip(ewfm, dwfm, ewim, dwim), start=1):
        e_wfm, d_wfm, e_wim, d_wim = records
        if len(e_wfm) < 12 or len(e_wim) < 12:
            raise ValueError(f"waveform entry {index} too short")
        if _u32be(e_wfm, 0) != len(d_wfm) or _u32be(e_wim, 0) != len(d_wim):
            raise ValueError(f"waveform entry {index} length mismatch")
        bundles.append(ClassicWaveformBundle(e_wfm, d_wfm, e_wim, d_wim))
    return bundles


def rebuild_waveform_chunks(
    bundles: Sequence[ClassicWaveformBundle],
) -> dict[str, bytes]:
    ewfm_entries: list[bytes] = []
    ewim_entries: list[bytes] = []
    dwfm_records: list[bytes] = []
    dwim_records: list[bytes] = []
    dwfm_offset = 12
    dwim_offset = 12
    for waveform_number, bundle in enumerate(bundles, start=1):
        content_number = 0x00010000 + waveform_number
        ewfm = bytearray(bundle.ewfm_entry)
        ewfm[0:4] = _p32(len(bundle.dwfm_data))
        ewfm[4:8] = _p32(dwfm_offset)
        ewfm[8:12] = _p32(content_number)
        ewim = bytearray(bundle.ewim_entry)
        ewim[0:4] = _p32(len(bundle.dwim_data))
        ewim[4:8] = _p32(dwim_offset)
        ewim[8:12] = _p32(content_number)
        ewfm_entries.append(bytes(ewfm))
        ewim_entries.append(bytes(ewim))
        dwfm_records.append(bundle.dwfm_data)
        dwim_records.append(bundle.dwim_data)
        dwfm_offset += 8 + len(bundle.dwfm_data)
        dwim_offset += 8 + len(bundle.dwim_data)
    return {
        "EWFM": _tagged_payload(b"Entr", ewfm_entries),
        "DWFM": _tagged_payload(b"Data", dwfm_records),
        "EWIM": _tagged_payload(b"Entr", ewim_entries),
        "DWIM": _tagged_payload(b"Data", dwim_records),
    }


def remap_x7_waveform_references(blob: bytes, remap: dict[int, int]) -> bytes:
    performance = parse_classic_blob(blob, TARGET_X7_VERSION)
    for part in performance.parts:
        for element in part.elements:
            if element.wave_bank != 0:
                old = int(element.waveform_number)
                try:
                    element.waveform_number = remap[old]
                except KeyError as exc:
                    raise ValueError(f"missing waveform remap for source-local ID {old}") from exc
    return performance.to_blob()

def rebuild_performance_chunks(
    source_entries: list[ClassicEntry],
    x7_blobs: list[bytes],
) -> tuple[bytes, bytes]:
    if len(source_entries) != len(x7_blobs):
        raise ValueError("entry/blob count mismatch")
    epfm_records: list[bytes] = []
    dpfm_records: list[bytes] = []
    dpfm_offset = 12
    for index, (source_entry, blob) in enumerate(zip(source_entries, x7_blobs)):
        entry = bytearray(source_entry.raw)
        entry[0:4] = _p32(len(blob))
        entry[4:8] = _p32(dpfm_offset)
        entry[8:12] = _p32(X7_CONTENT_NUMBER_BASE + index)
        epfm_records.append(bytes(entry))
        dpfm_records.append(blob)
        dpfm_offset += 8 + len(blob)
    return _tagged_payload(b"Entr", epfm_records), _tagged_payload(b"Data", dpfm_records)


def x7_target_order(source: ClassicContainer) -> tuple[str, ...]:
    """Return an X7-compatible catalogue without forcing a fixed family size.

    ECRV/DCRV also occur in valid 4.x X7L families, so they are preserved for
    X7L input.  They are removed only when normalising a 5.x X8L source.
    """
    if _source_family(source.version) == "X8L":
        order = tuple(tag for tag in source.order if tag not in X8_ONLY_TAGS)
    else:
        order = source.order
    if "EPFM" not in order or "DPFM" not in order:
        raise ValueError("source family lacks EPFM/DPFM")
    if len(set(order)) != len(order):
        raise ValueError("duplicate X7 target tags")
    return order


def write_x7_container(
    source: ClassicContainer,
    payloads: dict[str, bytes],
    order: tuple[str, ...] | None = None,
) -> bytes:
    order = order or x7_target_order(source)
    for required in ("EPFM", "DPFM"):
        if required not in order or required not in payloads:
            raise ValueError(f"{required} missing from X7 output")

    catalogue_size = len(order) * 8
    gap = source.gap  # Preserve the exact valid library metadata region.
    first_chunk = 64 + catalogue_size + len(gap)

    chunks = bytearray()
    offsets: dict[str, int] = {}
    cursor = first_chunk
    for tag in order:
        body = payloads.get(tag)
        if body is None:
            raise ValueError(f"payload missing for catalogue section {tag}")
        offsets[tag] = cursor
        chunk = tag.encode("latin-1") + _p32(len(body)) + body
        chunks += chunk
        cursor += len(chunk)

    header = bytearray(source.header)
    header[:11] = MAGIC
    header[11:16] = b"\0" * 5
    header[16:32] = TARGET_VERSION_FIELD
    header[32:36] = _p32(catalogue_size)
    header[36:48] = b"\xff" * 12
    header[48:52] = _p32(len(gap))
    header[52:60] = b"\xff" * 8
    # x3c is profile/library metadata and is retained from the source.

    catalogue = bytearray()
    for tag in order:
        catalogue += tag.encode("latin-1") + _p32(offsets[tag])
    return bytes(header + catalogue + gap + chunks)


def _normalise_selection(count: int, selected_indices: Iterable[int] | None) -> tuple[int, ...]:
    if selected_indices is None:
        return tuple(range(count))
    selected = tuple(int(i) for i in selected_indices)
    if not selected:
        raise ValueError("at least one Performance must be selected")
    if len(set(selected)) != len(selected):
        raise ValueError("duplicate Performance indices are not allowed")
    for index in selected:
        if index < 0 or index >= count:
            raise IndexError(f"Performance index {index} out of range 0..{count - 1}")
    return selected


def convert_classic_library_to_x7l(
    source: bytes | Path | str,
    selected_indices: Iterable[int] | None = None,
) -> X7FileResult:
    """Convert a full library or an ordered subset to X7L 4.0.2.

    The dependency sections are preserved from the single source container.
    This makes subset export safe even before cross-library dependency remapping
    is implemented: unused waveforms/samples may remain, but selected
    Performances cannot lose source-local dependencies.
    """
    container = read_classic_container(source)
    all_entries = extract_classic_entries(container)
    selected = _normalise_selection(len(all_entries), selected_indices)
    entries = [all_entries[i] for i in selected]
    warnings: list[str] = []
    x7_blobs: list[bytes] = []
    for output_index, (source_index, entry) in enumerate(zip(selected, entries)):
        result = transcode_classic_blob_to_x7l(entry.blob, container.version)
        x7_blobs.append(result.blob)
        warnings.extend(
            f"Performance {source_index + 1} (output {output_index + 1}): {w}"
            for w in result.warnings
        )

    epfm, dpfm = rebuild_performance_chunks(entries, x7_blobs)
    payloads = dict(container.payloads)
    payloads["EPFM"] = epfm
    payloads["DPFM"] = dpfm
    order = x7_target_order(container)
    output = write_x7_container(container, payloads, order)

    check = read_classic_container(output)
    if check.version != TARGET_X7_VERSION or check.profile.source_family != "X7L":
        raise ValueError("writer produced wrong X7L target")
    check_entries = extract_classic_entries(check)
    if [e.blob for e in check_entries] != x7_blobs:
        raise ValueError("file-level X7L round-trip validation failed")
    if check.order != order:
        raise ValueError("target catalogue order changed during validation")
    target_expected_first = 64 + len(order) * 8 + len(container.gap)
    if check.profile.first_section_offset != target_expected_first:
        raise ValueError("target first-section offset is inconsistent")

    label = _source_label(source)
    items = tuple(
        MergePerformanceItem(
            output_index=output_index,
            source_number=1,
            source_label=label,
            source_index=source_index,
            source_position=source_index + 1,
            name=_performance_name(entry.blob, container.version),
        )
        for output_index, (source_index, entry) in enumerate(zip(selected, entries))
    )
    return X7FileResult(
        data=output,
        source_version=container.version,
        performance_count=len(entries),
        source_profile_id=container.profile.profile_id,
        target_profile_id=check.profile.profile_id,
        selected_indices=selected,
        warnings=tuple(warnings),
        performance_items=items,
    )



def _compatible_dependency_payloads(
    containers: Sequence[ClassicContainer],
    selected_blobs: Sequence[Sequence[bytes]],
) -> tuple[ClassicContainer, tuple[str, ...], dict[str, bytes], tuple[str, ...], tuple[ClassicDependencyUsage, ...]]:
    """Choose a safe dependency owner for a multi-source merge.

    Step 127 relaxes the previous byte-identical-universe rule only where the
    selected Performance data proves that a source does not use its local user
    waveform pool. All sources that *do* reference user waveforms must still
    share one byte-identical EWFM/DWFM/EWIM/DWIM universe. This enables safe
    merges such as a sampled Juno library plus an FM-X-only library while still
    rejecting two unrelated sampled libraries until semantic waveform remapping
    is implemented.

    Arpeggio references are not decoded, so distinct non-empty EARP/DARP pools
    remain incompatible. System and live-set sections are library metadata, not
    Performance dependencies; the chosen dependency owner's versions are used.
    """
    if not containers:
        raise ValueError("at least one source container is required")
    if len(containers) != len(selected_blobs):
        raise ValueError("container/selection count mismatch")

    usages = tuple(
        inspect_classic_dependency_usage(
            blobs, container.version, len(extract_arpeggio_bundles(container))
        )
        for container, blobs in zip(containers, selected_blobs)
    )
    referencing = [i for i, usage in enumerate(usages) if usage.uses_user_waveforms]
    dependency_owner_index = referencing[0] if referencing else 0
    owner = containers[dependency_owner_index]
    warnings: list[str] = []

    # Waveform/sample pools are merged semantically below. Each referenced
    # source-local waveform is copied as an atomic EWFM/DWFM/EWIM/DWIM bundle
    # and Performance references are rewritten to the compact output IDs.
    for index, usage in enumerate(usages):
        if not usage.uses_user_waveforms:
            warnings.append(
                f"source {index + 1}: selected Performances use no user waveforms"
            )

        if usage.has_nonzero_arpeggio_candidates:
            ids = sorted({candidate.arp_id for candidate in usage.arpeggio_candidates})
            warnings.append(
                f"source {index + 1}: diagnostic non-zero user-arpeggio "
                f"candidates found for IDs {ids}; no arp bytes were rewritten"
            )

    # Compare arpeggio pools semantically rather than byte-for-byte.  Different
    # source-local offsets and content numbers no longer make otherwise
    # identical EARP/DARP universes incompatible.  Truly different pools remain
    # blocked until the Performance-side arp reference positions are verified.
    nonempty_arp_signatures: list[tuple[tuple[bytes, bytes], ...]] = []
    for container in containers:
        signature = _semantic_arpeggio_signature(container)
        if signature:
            nonempty_arp_signatures.append(signature)
    if nonempty_arp_signatures and any(
        signature != nonempty_arp_signatures[0]
        for signature in nonempty_arp_signatures[1:]
    ):
        raise ValueError(
            "sources contain semantically different non-empty arpeggio pools; "
            "Performance arpeggio reference remapping is not verified yet"
        )
    if nonempty_arp_signatures:
        warnings.append(
            f"verified one shared semantic arpeggio pool with "
            f"{len(nonempty_arp_signatures[0])} entries"
        )

    order = x7_target_order(owner)
    payloads = {tag: owner.payloads[tag] for tag in order if tag not in PERFORMANCE_TAGS}
    for source_no, container in enumerate(containers, start=1):
        if container is owner:
            continue
        if container.gap != owner.gap:
            warnings.append(
                f"source {source_no}: library metadata region differs; source "
                f"{dependency_owner_index + 1} metadata is used"
            )
        for tag in order:
            if tag in PERFORMANCE_TAGS or tag in WAVE_DEPENDENCY_TAGS or tag in ARP_DEPENDENCY_TAGS:
                continue
            if container.payloads.get(tag) != owner.payloads.get(tag):
                warnings.append(
                    f"source {source_no}: {tag} metadata differs or is absent; source "
                    f"{dependency_owner_index + 1} data is used"
                )

    return owner, order, payloads, tuple(warnings), usages


def merge_classic_libraries_to_x7l(
    sources: Sequence[ClassicMergeSource | tuple[bytes | Path | str, Iterable[int] | None]],
) -> X7FileResult:
    """Merge ordered Performance selections from compatible classic sources.

    It supports any mix of X7L 4.x and X8L 5.x source versions. Selected
    sources with no user-waveform references may differ from the chosen
    waveform/sample dependency universe. Different user-waveform pools are merged and renumbered. Different non-empty
    arpeggio pools are still rejected until arpeggio remapping is implemented.
    """
    if not sources:
        raise ValueError("at least one merge source is required")

    normalised: list[ClassicMergeSource] = []
    for item in sources:
        if isinstance(item, ClassicMergeSource):
            normalised.append(item)
        else:
            source, selected = item
            normalised.append(
                ClassicMergeSource(
                    source=source,
                    selected_indices=None if selected is None else tuple(int(i) for i in selected),
                )
            )

    containers = [read_classic_container(item.source) for item in normalised]
    entries_by_source = [extract_classic_entries(container) for container in containers]
    selections = [
        _normalise_selection(len(entries), item.selected_indices)
        for item, entries in zip(normalised, entries_by_source)
    ]
    selected_blobs = [
        [entries[index].blob for index in selected]
        for entries, selected in zip(entries_by_source, selections)
    ]
    template, order, dependency_payloads, compatibility_warnings, usages = (
        _compatible_dependency_payloads(containers, selected_blobs)
    )

    source_waveforms = [extract_waveform_bundles(container) for container in containers]
    merged_waveforms: list[ClassicWaveformBundle] = []
    waveform_key_to_id: dict[tuple[bytes, bytes, bytes, bytes], int] = {}
    waveform_remaps: list[dict[int, int]] = []
    for source_no, (bundles, usage) in enumerate(zip(source_waveforms, usages), start=1):
        remap: dict[int, int] = {}
        for old_id in usage.user_waveform_ids:
            if old_id < 1 or old_id > len(bundles):
                raise ValueError(
                    f"source {source_no}: waveform ID {old_id} out of range 1..{len(bundles)}"
                )
            bundle = bundles[old_id - 1]
            key = bundle.dedup_key
            new_id = waveform_key_to_id.get(key)
            if new_id is None:
                merged_waveforms.append(bundle)
                new_id = len(merged_waveforms)
                waveform_key_to_id[key] = new_id
            remap[old_id] = new_id
        waveform_remaps.append(remap)

    merged_entries: list[ClassicEntry] = []
    merged_blobs: list[bytes] = []
    warnings = list(compatibility_warnings)
    flattened_selection: list[int] = []
    performance_items: list[MergePerformanceItem] = []
    for source_no, (merge_source, container, all_entries, selected, waveform_remap) in enumerate(
        zip(normalised, containers, entries_by_source, selections, waveform_remaps), start=1
    ):
        source_label = _source_label(merge_source.source, merge_source.label)
        for source_index in selected:
            entry = all_entries[source_index]
            name = _performance_name(entry.blob, container.version)
            result = transcode_classic_blob_to_x7l(entry.blob, container.version)
            merged_entries.append(entry)
            merged_blobs.append(remap_x7_waveform_references(result.blob, waveform_remap))
            flattened_selection.append(source_index)
            performance_items.append(MergePerformanceItem(
                output_index=len(performance_items),
                source_number=source_no,
                source_label=source_label,
                source_index=source_index,
                source_position=source_index + 1,
                name=name,
            ))
            warnings.extend(
                f"Source {source_no} ({source_label}), Performance index {source_index} "
                f"(position {source_index + 1}, {name!r}): {warning}"
                for warning in result.warnings
            )

    epfm, dpfm = rebuild_performance_chunks(merged_entries, merged_blobs)
    payloads = dict(dependency_payloads)
    if all(tag in order for tag in WAVE_DEPENDENCY_TAGS):
        payloads.update(rebuild_waveform_chunks(merged_waveforms))
    elif merged_waveforms:
        raise ValueError("target container family lacks waveform dependency sections")
    payloads["EPFM"] = epfm
    payloads["DPFM"] = dpfm
    output = write_x7_container(template, payloads, order)

    check = read_classic_container(output)
    check_entries = extract_classic_entries(check)
    if check.version != TARGET_X7_VERSION:
        raise ValueError("multi-source writer produced wrong target version")
    if [entry.blob for entry in check_entries] != merged_blobs:
        raise ValueError("multi-source X7L round-trip validation failed")
    if check.order != order:
        raise ValueError("multi-source catalogue order changed")
    check_waveforms = extract_waveform_bundles(check)
    if len(check_waveforms) != len(merged_waveforms):
        raise ValueError("merged waveform-pool count changed during validation")
    for entry in check_entries:
        usage = inspect_classic_dependency_usage([entry.blob], TARGET_X7_VERSION)
        if usage.user_waveform_ids and max(usage.user_waveform_ids) > len(check_waveforms):
            raise ValueError("output Performance references waveform outside merged pool")

    versions = ",".join(container.version for container in containers)
    return X7FileResult(
        data=output,
        source_version=versions,
        performance_count=len(merged_entries),
        source_profile_id="+".join(container.profile.profile_id for container in containers),
        target_profile_id=check.profile.profile_id,
        selected_indices=tuple(flattened_selection),
        warnings=tuple(warnings),
        source_count=len(containers),
        performance_items=tuple(performance_items),
    )


def preflight_classic_libraries_to_x7l(
    sources: Sequence[ClassicMergeSource | tuple[bytes | Path | str, Iterable[int] | None]],
) -> ClassicMergePreflightReport:
    """Run the complete merge validation without writing an output file.

    The successful path deliberately invokes the production merger, ensuring
    that preflight and export cannot silently diverge.  On failure, source
    metadata and any selections that can still be decoded are retained in the
    report together with a blocker message.
    """
    source_versions: list[str] = []
    source_profiles: list[str] = []
    source_count = len(sources)
    try:
        normalised: list[ClassicMergeSource] = []
        for item in sources:
            if isinstance(item, ClassicMergeSource):
                normalised.append(item)
            else:
                source, selected = item
                normalised.append(ClassicMergeSource(
                    source=source,
                    selected_indices=None if selected is None else tuple(int(i) for i in selected),
                ))
        for item in normalised:
            container = read_classic_container(item.source)
            source_versions.append(container.version)
            source_profiles.append(container.profile.profile_id)
        result = merge_classic_libraries_to_x7l(normalised)
        return ClassicMergePreflightReport(
            ok=True,
            source_count=result.source_count,
            performance_count=result.performance_count,
            target_version=TARGET_X7_VERSION,
            estimated_output_bytes=len(result.data),
            source_versions=tuple(source_versions),
            source_profiles=tuple(source_profiles),
            performances=result.performance_items,
            warnings=result.warnings,
            blockers=(),
        )
    except Exception as exc:
        return ClassicMergePreflightReport(
            ok=False,
            source_count=source_count,
            performance_count=0,
            target_version=TARGET_X7_VERSION,
            estimated_output_bytes=None,
            source_versions=tuple(source_versions),
            source_profiles=tuple(source_profiles),
            performances=(),
            warnings=(),
            blockers=(str(exc),),
        )


def _load_merge_plan_sources(plan_path: bytes | Path | str) -> list[ClassicMergeSource]:
    """Parse a merge plan into validated source descriptors."""
    path = Path(plan_path)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read merge plan {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError("merge plan root must be a JSON object")
    schema = document.get("schema")
    if schema != "ysfc-forge-x7l-merge-plan-v1":
        raise ValueError(f"unsupported merge plan schema: {schema!r}")
    raw_sources = document.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError("merge plan must contain a non-empty sources array")

    sources: list[ClassicMergeSource] = []
    for position, raw in enumerate(raw_sources, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"merge plan source {position} must be an object")
        raw_path = raw.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError(f"merge plan source {position} has no valid path")
        source_path = Path(raw_path)
        if not source_path.is_absolute():
            source_path = path.parent / source_path
        raw_select = raw.get("select")
        selected: tuple[int, ...] | None
        if raw_select is None:
            selected = None
        elif isinstance(raw_select, list) and all(isinstance(item, int) and not isinstance(item, bool) for item in raw_select):
            selected = tuple(raw_select)
        else:
            raise ValueError(f"merge plan source {position} select must be an integer array")
        label = raw.get("label")
        if label is not None and not isinstance(label, str):
            raise ValueError(f"merge plan source {position} label must be a string")
        sources.append(ClassicMergeSource(source_path, selected, label))
    return sources


def preflight_classic_libraries_from_plan(plan_path: bytes | Path | str) -> ClassicMergePreflightReport:
    try:
        sources = _load_merge_plan_sources(plan_path)
    except Exception as exc:
        return ClassicMergePreflightReport(
            ok=False, source_count=0, performance_count=0,
            target_version=TARGET_X7_VERSION, estimated_output_bytes=None,
            blockers=(str(exc),),
        )
    return preflight_classic_libraries_to_x7l(sources)


def merge_classic_libraries_from_plan(plan_path: bytes | Path | str) -> X7FileResult:
    """Load a JSON merge plan and produce one X7L 4.0.2 result."""
    return merge_classic_libraries_to_x7l(_load_merge_plan_sources(plan_path))


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write bytes using fsync + os.replace so partial outputs are never exposed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _atomic_write_text(path: Path, text: str) -> None:
    _atomic_write_bytes(path, text.encode("utf-8"))


def export_classic_libraries_from_plan(
    plan_path: bytes | Path | str,
    output_path: Path | str,
    *,
    manifest_path: Path | str | None = None,
    preflight_path: Path | str | None = None,
    receipt_path: Path | str | None = None,
) -> ClassicMergeExportReceipt:
    """Preflight, build, verify and atomically publish one X7L 4.0.2 merge.

    The production result is built once after source validation. Its exact byte
    length must equal the preflight estimate. All requested sidecar documents
    are prepared before any final path is replaced.
    """
    sources = _load_merge_plan_sources(plan_path)
    preflight = preflight_classic_libraries_to_x7l(sources)
    if not preflight.ok:
        if preflight_path is not None:
            _atomic_write_text(Path(preflight_path), preflight.to_json())
        raise ValueError("merge preflight blocked export: " + "; ".join(preflight.blockers))

    result = merge_classic_libraries_to_x7l(sources)
    actual_size = len(result.data)
    if preflight.estimated_output_bytes != actual_size:
        raise ValueError(
            f"preflight/export size mismatch: estimated {preflight.estimated_output_bytes}, "
            f"built {actual_size}"
        )
    # Re-open the exact bytes immediately before publishing.
    verified = read_classic_container(result.data)
    if verified.version != TARGET_X7_VERSION:
        raise ValueError("transactional export verification produced wrong target version")
    if len(extract_classic_entries(verified)) != result.performance_count:
        raise ValueError("transactional export verification changed Performance count")

    output = Path(output_path)
    manifest = None if manifest_path is None else Path(manifest_path)
    preflight_out = None if preflight_path is None else Path(preflight_path)
    receipt_out = None if receipt_path is None else Path(receipt_path)
    sha256 = hashlib.sha256(result.data).hexdigest()
    receipt = ClassicMergeExportReceipt(
        ok=True,
        output_path=str(output),
        manifest_path=None if manifest is None else str(manifest),
        preflight_path=None if preflight_out is None else str(preflight_out),
        output_bytes=actual_size,
        output_sha256=sha256,
        target_version=TARGET_X7_VERSION,
        source_count=result.source_count,
        performance_count=result.performance_count,
        estimated_output_bytes=preflight.estimated_output_bytes or actual_size,
        warnings=result.warnings,
    )

    # Prepare sidecar content first. Each final file is then published atomically.
    if preflight_out is not None:
        _atomic_write_text(preflight_out, preflight.to_json())
    if manifest is not None:
        _atomic_write_text(manifest, result.manifest_json())
    _atomic_write_bytes(output, result.data)
    if receipt_out is not None:
        _atomic_write_text(receipt_out, receipt.to_json())
    return receipt


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Convert or merge classic X7L/X8L to X7L 4.0.2")
    parser.add_argument("source", type=Path, nargs="?")
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument(
        "--select",
        metavar="INDEXES",
        help="comma-separated zero-based Performance indices in output order",
    )
    parser.add_argument(
        "--merge-plan",
        type=Path,
        help="JSON plan for ordered multi-source X7L/X8L merge",
    )
    parser.add_argument(
        "--merge-output",
        type=Path,
        help="output X7L path when --merge-plan is used",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="write a JSON manifest with output position, source index and Performance name",
    )
    parser.add_argument(
        "--preflight",
        type=Path,
        metavar="REPORT.json",
        help="validate --merge-plan without writing X7L and save a JSON preflight report",
    )
    parser.add_argument(
        "--preflight-report",
        type=Path,
        metavar="REPORT.json",
        help="with --merge-output, save the successful preflight used for transactional export",
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        metavar="RECEIPT.json",
        help="with --merge-output, save SHA-256 and verified export metadata",
    )
    args = parser.parse_args()

    if args.merge_plan is not None:
        if args.source is not None or args.output is not None or args.select is not None:
            parser.error("--merge-plan cannot be combined with positional source/output or --select")
        if args.preflight is not None:
            if args.merge_output is not None or args.manifest is not None:
                parser.error("--preflight cannot be combined with --merge-output or --manifest")
            report = preflight_classic_libraries_from_plan(args.merge_plan)
            args.preflight.write_text(report.to_json(), encoding="utf-8")
            print(f"Preflight {'OK' if report.ok else 'BLOCKED'}: {args.preflight}")
            for blocker in report.blockers:
                print(f"blocker: {blocker}")
            return 0 if report.ok else 2
        if args.merge_output is None:
            parser.error("--merge-output is required with --merge-plan unless --preflight is used")
        receipt = export_classic_libraries_from_plan(
            args.merge_plan,
            args.merge_output,
            manifest_path=args.manifest,
            preflight_path=args.preflight_report,
            receipt_path=args.receipt,
        )
        print(
            f"Wrote {args.merge_output} ({receipt.performance_count} Performances, "
            f"X7L {receipt.target_version}, SHA-256 {receipt.output_sha256})"
        )
        return 0
    else:
        if args.preflight is not None:
            parser.error("--preflight requires --merge-plan")
        if args.preflight_report is not None or args.receipt is not None:
            parser.error("--preflight-report and --receipt require --merge-plan with --merge-output")
        if args.merge_output is not None:
            parser.error("--merge-output requires --merge-plan")
        if args.source is None or args.output is None:
            parser.error("source and output are required for single-source conversion")
        selected = None
        if args.select is not None:
            try:
                selected = [int(item.strip()) for item in args.select.split(",") if item.strip()]
            except ValueError as exc:
                parser.error(f"invalid --select value: {exc}")
        result = convert_classic_library_to_x7l(args.source, selected)
        output_path = args.output

    output_path.write_bytes(result.data)
    if args.manifest is not None:
        args.manifest.write_text(result.manifest_json(), encoding="utf-8")
    print(
        f"Wrote {output_path} ({result.performance_count} Performances, "
        f"{result.source_profile_id} -> {result.target_profile_id})"
    )
    for item in result.performance_items:
        print(
            f"  output {item.output_index + 1}: {item.name} "
            f"<- {item.source_label}, index {item.source_index} "
            f"(position {item.source_position})"
        )
    for warning in result.warnings:
        print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
