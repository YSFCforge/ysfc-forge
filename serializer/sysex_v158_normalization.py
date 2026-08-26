"""SysEx Forge v1.58 topology safety rules.

Rules here are locked by controlled MODX M ESP tests on 2026-08-23. They are
small, deterministic and fail-closed so Python writers can share the browser
converter's v1.58 semantics.
"""
from __future__ import annotations

V158_CHECKPOINT = "2026-08-23"
PHYSICAL_PART_SLOT_COUNT_OFFSET = 6695


def physical_part_slot_count(blob: bytes | bytearray) -> int:
    """Return the physical/template Part-slot count stored at blob[6695]."""
    if len(blob) <= PHYSICAL_PART_SLOT_COUNT_OFFSET:
        raise ValueError("Performance blob is too short to contain blob[6695]")
    count = int(blob[PHYSICAL_PART_SLOT_COUNT_OFFSET])
    if not 1 <= count <= 16:
        raise ValueError(f"Invalid physical Part-slot count {count}; expected 1..16")
    return count


def validate_logical_parts_fit_physical_slots(
    blob: bytes | bytearray, logical_part_count: int
) -> int:
    """Fail closed if an export plan exceeds the fixed template topology.

    Returns the physical slot count. A logical plan may use fewer slots than the
    physical template (for example 3 logical FM-X Parts in an 11-slot template).
    The caller must preserve blob[6695] unless it also rebuilds the physical
    topology itself.
    """
    logical = int(logical_part_count)
    if not 1 <= logical <= 16:
        raise ValueError(f"logical_part_count must be 1..16, got {logical}")
    physical = physical_part_slot_count(blob)
    if logical > physical:
        raise ValueError(
            f"Export requires {logical} Parts but template carries only "
            f"{physical} physical Part slots"
        )
    return physical


def set_slot_count_for_rebuilt_topology(blob: bytearray, rebuilt_slot_count: int) -> None:
    """Set blob[6695] only when the physical topology was rebuilt to this count."""
    count = int(rebuilt_slot_count)
    if not 1 <= count <= 16:
        raise ValueError(f"rebuilt_slot_count must be 1..16, got {count}")
    if len(blob) <= PHYSICAL_PART_SLOT_COUNT_OFFSET:
        raise ValueError("Performance blob is too short to contain blob[6695]")
    blob[PHYSICAL_PART_SLOT_COUNT_OFFSET] = count
