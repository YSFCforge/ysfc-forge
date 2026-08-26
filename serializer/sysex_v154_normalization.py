"""SysEx Forge v1.54 cross-generation normalization rules.

This module contains only rules locked by Yamaha documentation plus direct
MODX M ESP/WebMIDI reference evidence.  It is deliberately small and fail-closed
so Python integrations can reuse the same semantics as browser converter v1.54.
"""
from __future__ import annotations

V154_CHECKPOINT = "2026-08-23"

# Modern AWM2 Element 1-byte header: rel +7..+38 = Controller Set 1..32 Switch.
AWM2_CONTROLLER_SET_FIRST_REL = 7
AWM2_CONTROLLER_SET_COUNT = 32

# Direct ESP-reference legacy normalization: Set 1 Off, Sets 2..32 On.
LEGACY_AWM2_CONTROLLER_SWITCH_DEFAULTS = (0,) + (1,) * 31

# Motion Sequence source/target geometry used by browser v1.54.
LEGACY_MS_LANE_PATTERNS = ("32 sp 00", "33 sp 00", "34 sp 00", "35 sp 00")
MODERN_MS_LANE1_PART_REL = 2228
MODERN_MS_LANE_STRIDE = 884
MODERN_MS_SEQ1_REL_IN_LANE = 36
MODERN_MS_SEQ_STRIDE = 106


def normalize_legacy_motion_sequence_amplitude(raw: int) -> int:
    """Map only the documented generation-specific default.

    Legacy default 0x40 -> MODX M default 0x7F. Non-default values are preserved.
    """
    raw = int(raw)
    if not 0 <= raw <= 0x7F:
        raise ValueError("Motion Sequence Amplitude must be u7")
    return 0x7F if raw == 0x40 else raw


def normalize_legacy_motion_sequence_shape_sw1(raw: int) -> int:
    """Map legacy Shape Control SW1 default 0 to MODX M default 1.

    The legacy field is boolean. Browser v1.54 normalizes the legacy default 0 to
    the modern generation default 1; explicit 1 remains 1.
    """
    raw = int(raw)
    if raw not in (0, 1):
        raise ValueError("Shape Control SW1 must be boolean")
    return 1


def fold_legacy_curve_direction(step_type_ab: int, direction_a: int, direction_b: int) -> int:
    """Fold legacy A/B + per-curve direction into MODX M Step Type 0..3."""
    ab = int(step_type_ab)
    da = int(direction_a)
    db = int(direction_b)
    if ab not in (0, 1) or da not in (0, 1) or db not in (0, 1):
        raise ValueError("step type and directions must be boolean")
    return ab + ((db if ab else da) << 1)


def legacy_awm2_controller_switch_vector() -> tuple[int, ...]:
    """Return the v1.54 ESP-reference normalization vector for Set 1..32."""
    return LEGACY_AWM2_CONTROLLER_SWITCH_DEFAULTS
