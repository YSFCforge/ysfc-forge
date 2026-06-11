"""
ysfc_serializer_classic.py
──────────────────────────
Reverse-engineered parser and serializer for Yamaha classic synthesizer
performance blobs — the DPFM data blocks found in X7L (Montage 4.0.x) and
X8L (MODX 5.0.x) library files.

Ported from ConvertWithMoss (git-moss/ConvertWithMoss, LGPLv3) Java classes:
  • YamahaYsfcPerformance.java
  • YamahaYsfcPerformancePart.java
  • YamahaYsfcPartElement.java
  • YamahaYsfcFileFormat.java

Original Java code © 2019-2026 Jürgen Moßgraber — mossgrabers.de (LGPLv3)
Python port © 2026 YSFC Forge

SCOPE
-----
This module covers AWM2 (type 0) and Drum (type 1) performance parts in the
classic X7L/X8L blob format.  FM-X parts (type 2) are read/stored as opaque
byte blocks — their operator data layout is not documented in CWM and is not
mapped here.

For the YSFC Forge Fas 3 blob-transkodning (classic X7L/X8L → Y2L/Y2U):
  1. Parse classic blob  → ClassicPerformance object
  2. Map parameters      → translate to Y2L equivalents (Fas 3 logic)
  3. Serialize to Y2L    → handled by ysfc_serializer.py (existing)

VERSION HANDLING (YamahaYsfcFileFormat enum in CWM)
----------------------------------------------------
  File version  Hardware              Extension   CWM constant
  4.0.x         Montage classic       X7L/X7U     MONTAGE  (maxVersion 405)
  4.1.x         Montage M             Y2L/Y2U     MONTAGE_M (not handled here)
  5.0.x         MODX / MODX+ classic  X8L/X8U     MODX     (maxVersion 501)
  5.1.x         MODX M                Y2L/Y2U     (not handled here)

The key difference between MONTAGE and MODX classic blobs (from CWM source):
  PerformancePart.manyParameters:  MONTAGE = 274 bytes,  MODX = 275 bytes
  Performance.sceneData:           MONTAGE = 8×11 = 88 bytes, MODX = 8×21 = 168 bytes

The outer blob starts with a 4-byte big-endian length prefix (0x000001af for
classic, compared to 0x00000015 for Y2L).  That prefix plus the name are
followed by the Performance common block, effects blocks, and parts — all
framed using the same ReadDataBlock / WriteDataBlock framing used in CWM
(u32be length prefix before each sub-block).
"""

from __future__ import annotations

import io
import struct
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Constants — file format versions
# ─────────────────────────────────────────────────────────────────────────────

FORMAT_MONTAGE   = "MONTAGE"   # 4.0.x  X7L/X7U
FORMAT_MODX      = "MODX"      # 5.0.x  X8L/X8U
FORMAT_UNKNOWN   = "UNKNOWN"


def detect_format(version_str: str) -> str:
    """Detect classic format from a YSFC header version string like '4.0.5' or '5.0.1'."""
    try:
        parts = version_str.strip().split(".")
        major, minor = int(parts[0]), int(parts[1])
        if major == 4 and minor == 0:
            return FORMAT_MONTAGE
        if major == 5 and minor == 0:
            return FORMAT_MODX
    except (ValueError, IndexError):
        pass
    return FORMAT_UNKNOWN


# ─────────────────────────────────────────────────────────────────────────────
# Stream helpers (mirrors CWM StreamUtils)
# ─────────────────────────────────────────────────────────────────────────────

def _read_u8(s: io.RawIOBase) -> int:
    b = s.read(1)
    if not b:
        raise EOFError("unexpected end of stream")
    return b[0]


def _read_u32be(s: io.RawIOBase) -> int:
    return struct.unpack(">I", s.read(4))[0]


def _read_u16le(s: io.RawIOBase) -> int:
    return struct.unpack("<H", s.read(2))[0]


def _read_ascii(s: io.RawIOBase, n: int) -> str:
    """Read n bytes as ASCII, strip trailing nulls/spaces."""
    raw = s.read(n)
    text = raw.decode("latin-1", errors="replace")
    null_pos = text.find("\x00")
    if null_pos >= 0:
        text = text[:null_pos]
    return text.rstrip()


def _read_data_block(s: io.RawIOBase) -> bytes:
    """Read a length-prefixed sub-block (u32be length, then data)."""
    length = _read_u32be(s)
    return s.read(length)


def _write_u8(s: io.BytesIO, v: int) -> None:
    s.write(bytes([v & 0xFF]))


def _write_u32be(s: io.BytesIO, v: int) -> None:
    s.write(struct.pack(">I", v & 0xFFFFFFFF))


def _write_u16le(s: io.BytesIO, v: int) -> None:
    s.write(struct.pack("<H", v & 0xFFFF))


def _write_ascii(s: io.BytesIO, text: str, n: int) -> None:
    """Write text as exactly n bytes, null-padded."""
    encoded = text.encode("latin-1", errors="replace")[:n]
    encoded += b"\x00" * (n - len(encoded))
    s.write(encoded)


def _write_data_block(s: io.BytesIO, data: bytes) -> None:
    """Write a length-prefixed sub-block."""
    _write_u32be(s, len(data))
    s.write(data)


# ─────────────────────────────────────────────────────────────────────────────
# ClassicPartElement  (YamahaYsfcPartElement in CWM)
# ─────────────────────────────────────────────────────────────────────────────
# Represents one AWM2 element inside a performance part.
# The read order below is the CANONICAL byte sequence as confirmed by CWM.
# Each field is 1 byte unless noted.  Total decoded bytes: 120 named + 2-5 tail.

@dataclass
class ClassicPartElement:
    """One AWM2 element in a classic (X7L/X8L) performance part.

    Field documentation — ranges are the raw stored values:
    All single-byte fields unless otherwise noted.

    Source: YamahaYsfcPartElement.java read() / write() methods.
    """

    # ── Playback switch / routing ──────────────────────────────
    element_switch:           int = 1    # 0=off, 1=on
    wave_bank:                int = 0    # 0=Preset, 1=User, 2-9=Library1-8
    element_group_number:     int = 0
    receive_note_off:         int = 1
    key_assign_mode:          int = 0
    alternate_group:          int = 0
    pan:                      int = 64   # 1-127, 64=center
    random_pan_depth:         int = 0
    alternate_pan_depth:      int = 64
    scaling_pan_depth:        int = 64
    xa_mode:                  int = 0    # 0=Normal,1=Legato,2=KeyOff,3=Cycle,4=Random,5=ASWOff,6=ASW1On,7=ASW2On

    # ── Key / velocity limits ──────────────────────────────────
    note_limit_low:           int = 0
    note_limit_high:          int = 127
    velocity_limit_low:       int = 1
    velocity_limit_high:      int = 127
    velocity_cross_fade:      int = 0
    key_on_delay:             int = 0
    key_on_delay_tempo_sync:  int = 0

    # ── Effect routing ─────────────────────────────────────────
    reverb_send_level:        int = 40
    variation_send_level:     int = 0
    insertion_effect_switch:  int = 0
    output_select:            int = 0

    # ── Control boxes 1-16 (one byte each) ────────────────────
    control_box_sw:           list[int] = field(default_factory=lambda: [0]*16)

    # ── Timing / misc ──────────────────────────────────────────
    key_on_delay_tempo:       int = 64
    half_damper_switch:       int = 0

    # ── Level / AEG (Amplitude Envelope Generator) ────────────
    element_level:            int = 127  # 0-127
    level_velocity_sensitivity: int = 64  # 0-127, 64=centre (0)
    level_velocity_offset:    int = 64
    level_sens_key_curve:     int = 0
    aeg_attack_time:          int = 0    # 0-127
    aeg_decay1_time:          int = 60
    aeg_decay2_time:          int = 40
    aeg_sustain_time:         int = 127
    aeg_release_time:         int = 50
    aeg_init_level:           int = 0
    aeg_attack_level:         int = 127
    aeg_decay1_level:         int = 127
    aeg_decay2_level:         int = 0
    aeg_time_velocity_segment:     int = 0
    aeg_time_velocity_sensitivity: int = 64
    aeg_time_key_follow_sensitivity:   int = 64
    aeg_time_key_follow_center_note:   int = 60
    aeg_time_key_follow_adjustment:    int = 0

    # ── Level scaling ─────────────────────────────────────────
    level_scaling_break_point_1: int = 0
    level_scaling_break_point_2: int = 0
    level_scaling_break_point_3: int = 0
    level_scaling_break_point_4: int = 0
    level_scaling_offset_1:  int = 64
    level_scaling_offset_2:  int = 64
    level_scaling_offset_3:  int = 64
    level_scaling_offset_4:  int = 64
    level_key_follow_sensitivity: int = 64

    # ── Pitch ──────────────────────────────────────────────────
    coarse_tune:              int = 64   # 16-112 → -48..+48 semitones; 64=0
    fine_tune:                int = 64   # 0-127 → -64..+63; 64=0
    pitch_velocity_sensitivity: int = 64
    random_pitch_depth:       int = 0
    pitch_key_follow_sensitivity: int = 96   # index into PITCH_KEY table; 96=100%
    pitch_key_follow_center_note: int = 60
    pitch_fine_scaling_sensitivity: int = 0

    # ── PEG (Pitch Envelope Generator) ────────────────────────
    peg_hold_time:            int = 0
    peg_attack_time:          int = 0
    peg_decay1_time:          int = 0
    peg_decay2_time:          int = 0
    peg_release_time:         int = 0
    peg_hold_level:           int = 128  # 0-255 → -128..+127; 128=0
    peg_attack_level:         int = 128
    peg_decay1_level:         int = 128
    peg_decay2_level:         int = 128
    peg_release_level:        int = 128
    peg_depth:                int = 64   # 0-127 → -64..+63; 64=0
    peg_time_velocity_segment:     int = 0
    peg_time_velocity_sensitivity: int = 64
    peg_level_velocity_sensitivity: int = 64
    peg_level_sens_velocity_curve:  int = 0
    peg_time_key_follow_sensitivity:   int = 64
    peg_time_key_follow_center_note:   int = 60

    # ── Filter ─────────────────────────────────────────────────
    # filter_type: 0=LPF24D,1=LPF24A,2=LPF18,3=LPF18s,4=LPF12+HPF12,
    #              5=LPF6+HPF12,6=HPF24D,7=HPF12,8=BPF12D,9=BPFw,
    #              10=BEF12,11=BEF6,12=DualLPF,13=DualHPF,14=DualBPF,
    #              15=DualBEF,16=LPF12+HPF6,17=Thru
    filter_type:              int = 17   # 17=Thru
    filter_cutoff_frequency:  int = 255  # 0-255
    filter_cutoff_velocity_sensitivity: int = 64
    filter_resonance:         int = 0    # 0-127
    filter_resonance_velocity_sensitivity: int = 64
    hpf_cutoff_frequency:     int = 0
    distance:                 int = 0
    filter_gain:              int = 0

    # ── FEG (Filter Envelope Generator) ───────────────────────
    feg_hold_time:            int = 0
    feg_attack_time:          int = 0
    feg_decay1_time:          int = 64
    feg_decay2_time:          int = 64
    feg_release_time:         int = 64
    feg_hold_level:           int = 128
    feg_attack_level:         int = 128
    feg_decay1_level:         int = 128
    feg_decay2_level:         int = 128
    feg_release_level:        int = 128
    feg_depth:                int = 64
    feg_time_velocity_segment:     int = 0
    feg_time_velocity_sensitivity: int = 64
    feg_level_velocity_sensitivity: int = 64
    feg_level_velocity_curve:      int = 0
    feg_time_key_follow_sensitivity:   int = 64
    feg_time_key_follow_center_note:   int = 60

    # ── Filter cutoff scaling ──────────────────────────────────
    filter_cutoff_scaling_break_point_1: int = 0
    filter_cutoff_scaling_break_point_2: int = 0
    filter_cutoff_scaling_break_point_3: int = 0
    filter_cutoff_scaling_break_point_4: int = 0
    filter_cutoff_scaling_offset_1: int = 64
    filter_cutoff_scaling_offset_2: int = 64
    filter_cutoff_scaling_offset_3: int = 64
    filter_cutoff_scaling_offset_4: int = 64
    filter_cutoff_key_follow_sensitivity: int = 64
    hpf_cutoff_key_follow_sensitivity:    int = 64

    # ── EQ ─────────────────────────────────────────────────────
    eq_type:       int = 0
    eq_resonance:  int = 0
    eq1_frequency: int = 64
    eq1_gain:      int = 64
    eq2_frequency: int = 64
    eq2_gain:      int = 64

    # ── LFO ────────────────────────────────────────────────────
    lfo_wave:               int = 0
    lfo_key_on_sync:        int = 0
    lfo_key_on_delay_time:  int = 0
    lfo_speed:              int = 40
    lfo_amod_depth:         int = 0
    lfo_pmod_depth:         int = 0
    lfo_fmod_depth:         int = 0
    lfo_fade_in_time:       int = 0
    common_lfo_phase_offset:      int = 0
    common_lfo_box1_depth_ratio:  int = 64
    common_lfo_box2_depth_ratio:  int = 64
    common_lfo_box3_depth_ratio:  int = 64

    # ── Tail bytes (version-dependent) ────────────────────────
    # CWM: "No idea about these 3 bytes" — present when rest==5, absent when rest==2
    unknown_bytes: Optional[bytes] = None   # None or 3 bytes

    # ── Waveform reference ────────────────────────────────────
    # 16-bit little-endian at end of element block
    # Range 1-6347 (Preset), or User/Library waveform number
    waveform_number: int = 1


    @classmethod
    def from_stream(cls, s: io.RawIOBase) -> "ClassicPartElement":
        """Parse one AWM2 element block from a stream.

        The stream is expected to be positioned at the start of the
        length-prefixed element data block (u32be len, then data).
        This mirrors YamahaYsfcPartElement.read().
        """
        data = _read_data_block(s)
        es = io.BytesIO(data)
        e = cls()

        e.element_switch          = _read_u8(es)
        e.wave_bank               = _read_u8(es)
        e.element_group_number    = _read_u8(es)
        e.receive_note_off        = _read_u8(es)
        e.key_assign_mode         = _read_u8(es)
        e.alternate_group         = _read_u8(es)
        e.pan                     = _read_u8(es)
        e.random_pan_depth        = _read_u8(es)
        e.alternate_pan_depth     = _read_u8(es)
        e.scaling_pan_depth       = _read_u8(es)
        e.xa_mode                 = _read_u8(es)
        e.note_limit_low          = _read_u8(es)
        e.note_limit_high         = _read_u8(es)
        e.velocity_limit_low      = _read_u8(es)
        e.velocity_limit_high     = _read_u8(es)
        e.velocity_cross_fade     = _read_u8(es)
        e.key_on_delay            = _read_u8(es)
        e.key_on_delay_tempo_sync = _read_u8(es)
        e.reverb_send_level       = _read_u8(es)
        e.variation_send_level    = _read_u8(es)
        e.insertion_effect_switch = _read_u8(es)
        e.output_select           = _read_u8(es)
        e.control_box_sw          = [_read_u8(es) for _ in range(16)]
        e.key_on_delay_tempo      = _read_u8(es)
        e.half_damper_switch      = _read_u8(es)
        e.element_level           = _read_u8(es)
        e.level_velocity_sensitivity   = _read_u8(es)
        e.level_velocity_offset        = _read_u8(es)
        e.level_sens_key_curve         = _read_u8(es)
        e.aeg_attack_time         = _read_u8(es)
        e.aeg_decay1_time         = _read_u8(es)
        e.aeg_decay2_time         = _read_u8(es)
        e.aeg_sustain_time        = _read_u8(es)
        e.aeg_release_time        = _read_u8(es)
        e.aeg_init_level          = _read_u8(es)
        e.aeg_attack_level        = _read_u8(es)
        e.aeg_decay1_level        = _read_u8(es)
        e.aeg_decay2_level        = _read_u8(es)
        e.aeg_time_velocity_segment          = _read_u8(es)
        e.aeg_time_velocity_sensitivity      = _read_u8(es)
        e.aeg_time_key_follow_sensitivity    = _read_u8(es)
        e.aeg_time_key_follow_center_note    = _read_u8(es)
        e.aeg_time_key_follow_adjustment     = _read_u8(es)
        e.level_scaling_break_point_1 = _read_u8(es)
        e.level_scaling_break_point_2 = _read_u8(es)
        e.level_scaling_break_point_3 = _read_u8(es)
        e.level_scaling_break_point_4 = _read_u8(es)
        e.level_scaling_offset_1  = _read_u8(es)
        e.level_scaling_offset_2  = _read_u8(es)
        e.level_scaling_offset_3  = _read_u8(es)
        e.level_scaling_offset_4  = _read_u8(es)
        e.level_key_follow_sensitivity = _read_u8(es)
        e.coarse_tune             = _read_u8(es)
        e.fine_tune               = _read_u8(es)
        e.pitch_velocity_sensitivity      = _read_u8(es)
        e.random_pitch_depth              = _read_u8(es)
        e.pitch_key_follow_sensitivity    = _read_u8(es)
        e.pitch_key_follow_center_note    = _read_u8(es)
        e.pitch_fine_scaling_sensitivity  = _read_u8(es)
        e.peg_hold_time           = _read_u8(es)
        e.peg_attack_time         = _read_u8(es)
        e.peg_decay1_time         = _read_u8(es)
        e.peg_decay2_time         = _read_u8(es)
        e.peg_release_time        = _read_u8(es)
        e.peg_hold_level          = _read_u8(es)
        e.peg_attack_level        = _read_u8(es)
        e.peg_decay1_level        = _read_u8(es)
        e.peg_decay2_level        = _read_u8(es)
        e.peg_release_level       = _read_u8(es)
        e.peg_depth               = _read_u8(es)
        e.peg_time_velocity_segment          = _read_u8(es)
        e.peg_time_velocity_sensitivity      = _read_u8(es)
        e.peg_level_velocity_sensitivity     = _read_u8(es)
        e.peg_level_sens_velocity_curve      = _read_u8(es)
        e.peg_time_key_follow_sensitivity    = _read_u8(es)
        e.peg_time_key_follow_center_note    = _read_u8(es)
        e.filter_type             = _read_u8(es)
        e.filter_cutoff_frequency = _read_u8(es)
        e.filter_cutoff_velocity_sensitivity        = _read_u8(es)
        e.filter_resonance                          = _read_u8(es)
        e.filter_resonance_velocity_sensitivity     = _read_u8(es)
        e.hpf_cutoff_frequency    = _read_u8(es)
        e.distance                = _read_u8(es)
        e.filter_gain             = _read_u8(es)
        e.feg_hold_time           = _read_u8(es)
        e.feg_attack_time         = _read_u8(es)
        e.feg_decay1_time         = _read_u8(es)
        e.feg_decay2_time         = _read_u8(es)
        e.feg_release_time        = _read_u8(es)
        e.feg_hold_level          = _read_u8(es)
        e.feg_attack_level        = _read_u8(es)
        e.feg_decay1_level        = _read_u8(es)
        e.feg_decay2_level        = _read_u8(es)
        e.feg_release_level       = _read_u8(es)
        e.feg_depth               = _read_u8(es)
        e.feg_time_velocity_segment          = _read_u8(es)
        e.feg_time_velocity_sensitivity      = _read_u8(es)
        e.feg_level_velocity_sensitivity     = _read_u8(es)
        e.feg_level_velocity_curve           = _read_u8(es)
        e.feg_time_key_follow_sensitivity    = _read_u8(es)
        e.feg_time_key_follow_center_note    = _read_u8(es)
        e.filter_cutoff_scaling_break_point_1 = _read_u8(es)
        e.filter_cutoff_scaling_break_point_2 = _read_u8(es)
        e.filter_cutoff_scaling_break_point_3 = _read_u8(es)
        e.filter_cutoff_scaling_break_point_4 = _read_u8(es)
        e.filter_cutoff_scaling_offset_1 = _read_u8(es)
        e.filter_cutoff_scaling_offset_2 = _read_u8(es)
        e.filter_cutoff_scaling_offset_3 = _read_u8(es)
        e.filter_cutoff_scaling_offset_4 = _read_u8(es)
        e.filter_cutoff_key_follow_sensitivity = _read_u8(es)
        e.hpf_cutoff_key_follow_sensitivity    = _read_u8(es)
        e.eq_type       = _read_u8(es)
        e.eq_resonance  = _read_u8(es)
        e.eq1_frequency = _read_u8(es)
        e.eq1_gain      = _read_u8(es)
        e.eq2_frequency = _read_u8(es)
        e.eq2_gain      = _read_u8(es)
        e.lfo_wave               = _read_u8(es)
        e.lfo_key_on_sync        = _read_u8(es)
        e.lfo_key_on_delay_time  = _read_u8(es)
        e.lfo_speed              = _read_u8(es)
        e.lfo_amod_depth         = _read_u8(es)
        e.lfo_pmod_depth         = _read_u8(es)
        e.lfo_fmod_depth         = _read_u8(es)
        e.lfo_fade_in_time       = _read_u8(es)
        e.common_lfo_phase_offset     = _read_u8(es)
        e.common_lfo_box1_depth_ratio = _read_u8(es)
        e.common_lfo_box2_depth_ratio = _read_u8(es)
        e.common_lfo_box3_depth_ratio = _read_u8(es)

        # CWM: "final int rest = elementDataIn.available(); if (rest != 2 && rest != 5) throw"
        rest = len(data) - es.tell()
        if rest not in (2, 5):
            raise ValueError(
                f"ClassicPartElement: unexpected tail size {rest} "
                f"(expected 2 or 5); total block={len(data)} bytes"
            )
        if rest == 5:
            e.unknown_bytes = es.read(3)
        else:
            e.unknown_bytes = None

        e.waveform_number = _read_u16le(es)
        return e


    def to_bytes(self) -> bytes:
        """Serialize back to the classic element block (without the outer length prefix)."""
        s = io.BytesIO()
        _write_u8(s, self.element_switch)
        _write_u8(s, self.wave_bank)
        _write_u8(s, self.element_group_number)
        _write_u8(s, self.receive_note_off)
        _write_u8(s, self.key_assign_mode)
        _write_u8(s, self.alternate_group)
        _write_u8(s, self.pan)
        _write_u8(s, self.random_pan_depth)
        _write_u8(s, self.alternate_pan_depth)
        _write_u8(s, self.scaling_pan_depth)
        _write_u8(s, self.xa_mode)
        _write_u8(s, self.note_limit_low)
        _write_u8(s, self.note_limit_high)
        _write_u8(s, self.velocity_limit_low)
        _write_u8(s, self.velocity_limit_high)
        _write_u8(s, self.velocity_cross_fade)
        _write_u8(s, self.key_on_delay)
        _write_u8(s, self.key_on_delay_tempo_sync)
        _write_u8(s, self.reverb_send_level)
        _write_u8(s, self.variation_send_level)
        _write_u8(s, self.insertion_effect_switch)
        _write_u8(s, self.output_select)
        for cb in self.control_box_sw:
            _write_u8(s, cb)
        _write_u8(s, self.key_on_delay_tempo)
        _write_u8(s, self.half_damper_switch)
        _write_u8(s, self.element_level)
        _write_u8(s, self.level_velocity_sensitivity)
        _write_u8(s, self.level_velocity_offset)
        _write_u8(s, self.level_sens_key_curve)
        _write_u8(s, self.aeg_attack_time)
        _write_u8(s, self.aeg_decay1_time)
        _write_u8(s, self.aeg_decay2_time)
        _write_u8(s, self.aeg_sustain_time)
        _write_u8(s, self.aeg_release_time)
        _write_u8(s, self.aeg_init_level)
        _write_u8(s, self.aeg_attack_level)
        _write_u8(s, self.aeg_decay1_level)
        _write_u8(s, self.aeg_decay2_level)
        _write_u8(s, self.aeg_time_velocity_segment)
        _write_u8(s, self.aeg_time_velocity_sensitivity)
        _write_u8(s, self.aeg_time_key_follow_sensitivity)
        _write_u8(s, self.aeg_time_key_follow_center_note)
        _write_u8(s, self.aeg_time_key_follow_adjustment)
        _write_u8(s, self.level_scaling_break_point_1)
        _write_u8(s, self.level_scaling_break_point_2)
        _write_u8(s, self.level_scaling_break_point_3)
        _write_u8(s, self.level_scaling_break_point_4)
        _write_u8(s, self.level_scaling_offset_1)
        _write_u8(s, self.level_scaling_offset_2)
        _write_u8(s, self.level_scaling_offset_3)
        _write_u8(s, self.level_scaling_offset_4)
        _write_u8(s, self.level_key_follow_sensitivity)
        _write_u8(s, self.coarse_tune)
        _write_u8(s, self.fine_tune)
        _write_u8(s, self.pitch_velocity_sensitivity)
        _write_u8(s, self.random_pitch_depth)
        _write_u8(s, self.pitch_key_follow_sensitivity)
        _write_u8(s, self.pitch_key_follow_center_note)
        _write_u8(s, self.pitch_fine_scaling_sensitivity)
        _write_u8(s, self.peg_hold_time)
        _write_u8(s, self.peg_attack_time)
        _write_u8(s, self.peg_decay1_time)
        _write_u8(s, self.peg_decay2_time)
        _write_u8(s, self.peg_release_time)
        _write_u8(s, self.peg_hold_level)
        _write_u8(s, self.peg_attack_level)
        _write_u8(s, self.peg_decay1_level)
        _write_u8(s, self.peg_decay2_level)
        _write_u8(s, self.peg_release_level)
        _write_u8(s, self.peg_depth)
        _write_u8(s, self.peg_time_velocity_segment)
        _write_u8(s, self.peg_time_velocity_sensitivity)
        _write_u8(s, self.peg_level_velocity_sensitivity)
        _write_u8(s, self.peg_level_sens_velocity_curve)
        _write_u8(s, self.peg_time_key_follow_sensitivity)
        _write_u8(s, self.peg_time_key_follow_center_note)
        _write_u8(s, self.filter_type)
        _write_u8(s, self.filter_cutoff_frequency)
        _write_u8(s, self.filter_cutoff_velocity_sensitivity)
        _write_u8(s, self.filter_resonance)
        _write_u8(s, self.filter_resonance_velocity_sensitivity)
        _write_u8(s, self.hpf_cutoff_frequency)
        _write_u8(s, self.distance)
        _write_u8(s, self.filter_gain)
        _write_u8(s, self.feg_hold_time)
        _write_u8(s, self.feg_attack_time)
        _write_u8(s, self.feg_decay1_time)
        _write_u8(s, self.feg_decay2_time)
        _write_u8(s, self.feg_release_time)
        _write_u8(s, self.feg_hold_level)
        _write_u8(s, self.feg_attack_level)
        _write_u8(s, self.feg_decay1_level)
        _write_u8(s, self.feg_decay2_level)
        _write_u8(s, self.feg_release_level)
        _write_u8(s, self.feg_depth)
        _write_u8(s, self.feg_time_velocity_segment)
        _write_u8(s, self.feg_time_velocity_sensitivity)
        _write_u8(s, self.feg_level_velocity_sensitivity)
        _write_u8(s, self.feg_level_velocity_curve)
        _write_u8(s, self.feg_time_key_follow_sensitivity)
        _write_u8(s, self.feg_time_key_follow_center_note)
        _write_u8(s, self.filter_cutoff_scaling_break_point_1)
        _write_u8(s, self.filter_cutoff_scaling_break_point_2)
        _write_u8(s, self.filter_cutoff_scaling_break_point_3)
        _write_u8(s, self.filter_cutoff_scaling_break_point_4)
        _write_u8(s, self.filter_cutoff_scaling_offset_1)
        _write_u8(s, self.filter_cutoff_scaling_offset_2)
        _write_u8(s, self.filter_cutoff_scaling_offset_3)
        _write_u8(s, self.filter_cutoff_scaling_offset_4)
        _write_u8(s, self.filter_cutoff_key_follow_sensitivity)
        _write_u8(s, self.hpf_cutoff_key_follow_sensitivity)
        _write_u8(s, self.eq_type)
        _write_u8(s, self.eq_resonance)
        _write_u8(s, self.eq1_frequency)
        _write_u8(s, self.eq1_gain)
        _write_u8(s, self.eq2_frequency)
        _write_u8(s, self.eq2_gain)
        _write_u8(s, self.lfo_wave)
        _write_u8(s, self.lfo_key_on_sync)
        _write_u8(s, self.lfo_key_on_delay_time)
        _write_u8(s, self.lfo_speed)
        _write_u8(s, self.lfo_amod_depth)
        _write_u8(s, self.lfo_pmod_depth)
        _write_u8(s, self.lfo_fmod_depth)
        _write_u8(s, self.lfo_fade_in_time)
        _write_u8(s, self.common_lfo_phase_offset)
        _write_u8(s, self.common_lfo_box1_depth_ratio)
        _write_u8(s, self.common_lfo_box2_depth_ratio)
        _write_u8(s, self.common_lfo_box3_depth_ratio)
        if self.unknown_bytes is not None:
            s.write(self.unknown_bytes)
        _write_u16le(s, self.waveform_number)
        return s.getvalue()


    def write_framed(self, out: io.BytesIO) -> None:
        """Write this element as a length-prefixed data block to out."""
        _write_data_block(out, self.to_bytes())


# ─────────────────────────────────────────────────────────────────────────────
# ClassicPerformancePart  (YamahaYsfcPerformancePart in CWM)
# ─────────────────────────────────────────────────────────────────────────────

# Part type constants (from CWM readParts switch)
PART_TYPE_AWM2 = 0   # Normal AWM part (8 elements)
PART_TYPE_DRUM = 1   # Drum kit AWM part (73 elements)
PART_TYPE_FMX  = 2   # FM-X part (not fully decoded)

@dataclass
class ClassicPerformancePart:
    """One part in a classic (X7L/X8L) performance.

    Source: YamahaYsfcPerformancePart.java read() method.

    Header fields (explicitly read by CWM):
      name[21]              — ASCII, null-terminated
      type[1]               — 0=AWM2, 1=Drum, 2=FM-X
      main_category[1]
      sub_category[1]
      part_switch[1]        — 0=off, 1=on
      keyboard_switch[1]
      velocity_limit_low[1]
      velocity_limit_high[1]
      note_limit_low[1]
      note_limit_high[1]
      pitch_bend_range_upper[1]
      pitch_bend_range_lower[1]
      many_parameters[274 or 275]  — opaque; 274 for MONTAGE, 275 for MODX
      scenes[88 or 168]    — 8×11 bytes for MONTAGE, 8×21 for MODX (version<405→8×21 else 8×22)
      assignable_knobs[8×17] — 8 × ASCII17
      control_boxes[16×9]  — 144 bytes opaque
    """
    _name_raw:              bytes = field(default_factory=lambda: b'Init Normal\x00' + b'\x00'*10)
    type:                   int   = PART_TYPE_AWM2
    main_category:          int   = 0
    sub_category:           int   = 0
    part_switch:            int   = 1
    keyboard_switch:        int   = 1
    velocity_limit_low:     int   = 1
    velocity_limit_high:    int   = 127
    note_limit_low:         int   = 0
    note_limit_high:        int   = 127
    pitch_bend_range_upper: int   = 64
    pitch_bend_range_lower: int   = 64

    # Opaque blocks — passed through unchanged in Fas 2/3
    many_parameters:        bytes = field(default_factory=lambda: bytes(274))
    scenes:                 bytes = field(default_factory=lambda: bytes(88))
    assignable_knobs:       list[str] = field(default_factory=lambda: [""] * 8)
    control_boxes:          bytes = field(default_factory=lambda: bytes(144))

    # AWM2/Drum elements (parsed for AWM2 parts)
    elements: list[ClassicPartElement] = field(default_factory=list)

    # FM-X opaque data (stored but not decoded — CWM skips FM parts for waveforms)
    fmx_common_opaque:      Optional[bytes] = None   # the 'common' data block for FM parts
    fmx_operator_opaque:    list[bytes] = field(default_factory=list)  # per-operator blocks



    @property
    def name(self) -> str:
        """Part name decoded from raw bytes (up to first null)."""
        raw = getattr(self, '_name_raw', b'')
        null = raw.find(b'\x00')
        return raw[:null].decode('latin-1', 'replace') if null >= 0 else raw.decode('latin-1', 'replace')

    @name.setter
    def name(self, value: str) -> None:
        encoded = value.encode('latin-1', 'replace')[:20]
        self._name_raw = encoded + b'\x00' * (21 - len(encoded))

    @classmethod
    def _read_header(cls, s: io.RawIOBase, fmt: str, version: int) -> "ClassicPerformancePart":
        """Read only the part header (not elements — elements are read separately in readParts)."""
        p = cls()
        p._name_raw         = s.read(21)  # raw bytes — may have binary data after null
        p.type              = _read_u8(s)
        p.main_category     = _read_u8(s)
        p.sub_category      = _read_u8(s)
        p.part_switch       = _read_u8(s)
        p.keyboard_switch   = _read_u8(s)
        p.velocity_limit_low  = _read_u8(s)
        p.velocity_limit_high = _read_u8(s)
        p.note_limit_low    = _read_u8(s)
        p.note_limit_high   = _read_u8(s)
        p.pitch_bend_range_upper = _read_u8(s)
        p.pitch_bend_range_lower = _read_u8(s)

        # Version-specific opaque block
        many_param_size = 274 if fmt == FORMAT_MONTAGE else 275
        p.many_parameters = s.read(many_param_size)

        # Scene data: CWM says version<405 → 8×21=168, else 8×22=176
        # (Note: for the part, not the performance common — different sizes!)
        if version < 405:
            p.scenes = s.read(8 * 21)
        else:
            p.scenes = s.read(8 * 22)

        # Assignable knobs 1-8 (17 bytes each) — stored as raw bytes (space-padded, not null-padded)
        p.assignable_knobs = [s.read(17) for _ in range(8)]

        # Control boxes 1-16 (9 bytes each, opaque)
        p.control_boxes = s.read(16 * 9)
        return p


    def _write_header(self, out: io.BytesIO) -> None:
        """Write part header bytes (not elements)."""
        name_raw = getattr(self, '_name_raw', None)
        if name_raw is None:
            name_raw = self.name.encode('latin-1', 'replace')[:21].ljust(21, b'\x00')
        out.write(name_raw[:21].ljust(21, b'\x00') if len(name_raw) < 21 else name_raw[:21])
        _write_u8(out, self.type)
        _write_u8(out, self.main_category)
        _write_u8(out, self.sub_category)
        _write_u8(out, self.part_switch)
        _write_u8(out, self.keyboard_switch)
        _write_u8(out, self.velocity_limit_low)
        _write_u8(out, self.velocity_limit_high)
        _write_u8(out, self.note_limit_low)
        _write_u8(out, self.note_limit_high)
        _write_u8(out, self.pitch_bend_range_upper)
        _write_u8(out, self.pitch_bend_range_lower)
        out.write(self.many_parameters)
        out.write(self.scenes)
        for k in self.assignable_knobs:
            # Write raw bytes (preserves binary data after null terminator)
            raw = k if isinstance(k, (bytes, bytearray)) else k.encode('latin-1', errors='replace')[:17].ljust(17, b'\x00')
            out.write(raw[:17].ljust(17, b'\x00') if len(raw) < 17 else raw[:17])
        out.write(self.control_boxes)


# ─────────────────────────────────────────────────────────────────────────────
# ClassicPerformance  (YamahaYsfcPerformance in CWM)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ClassicPerformance:
    """A complete classic (X7L/X8L) performance blob, decoded into named fields.

    Structure (outer blob bytes, after the 4-byte prefix is stripped):
      [common block]  — length-prefixed sub-block:
          name[21]           — performance name, ASCII null-terminated
          common_params[43]  — opaque common parameters
          scene_data[88|168] — 8×11=88 (MONTAGE) or 8×21=168 (MODX) bytes
          assignable_knobs[8×17]
          control_boxes[16×9]
          rest[...]          — remaining opaque bytes
      [reverb block]   — length-prefixed sub-block (opaque)
      [variation block] — length-prefixed sub-block (opaque)
      [master_eq block] — length-prefixed sub-block (opaque)
      [master_effect block] — length-prefixed sub-block (opaque)
      [part_count: u32be]
      [part_0_header block] [part_1_header block] ... (each length-prefixed)
      [ad_part block]       — length-prefixed (opaque)
      [digital_input_part block] — length-prefixed (opaque)
      [element section per part]:
          [part_type: u32be]  — 0=AWM2, 1=Drum, 2=FM-X
          if AWM2/Drum:
              [element_count: u32be]
              [element_0 block] ... (each length-prefixed)
          if FM-X:
              [operator_count: u32be]
              [fm_common block]  — length-prefixed
              [op_0 block] ...   — length-prefixed
      [play_settings: rest of stream]  — super knob + arp settings (opaque)

    Source: YamahaYsfcPerformance.java read() / write() methods.
    """
    _name_raw:          bytes = field(default_factory=lambda: b'Init Normal\x00' + b'\x00'*10)
    fmt:               str   = FORMAT_MONTAGE
    version:           int   = 405   # raw 3-digit version, e.g. 405 or 501

    # Common block opaque fields
    common_params:     bytes = field(default_factory=lambda: bytes(43))
    scene_data:        bytes = field(default_factory=lambda: bytes(88))
    assignable_knobs:  list = field(default_factory=lambda: [b'\x00' * 17] * 8)  # raw 17-byte blocks
    control_boxes:     bytes = field(default_factory=lambda: bytes(144))
    common_rest:       bytes = field(default_factory=bytes)

    # Effects — all opaque
    reverb_block:        bytes = field(default_factory=bytes)
    variation_block:     bytes = field(default_factory=bytes)
    master_eq_block:     bytes = field(default_factory=bytes)
    master_effect_block: bytes = field(default_factory=bytes)

    # Parts
    parts:               list[ClassicPerformancePart] = field(default_factory=list)

    # AD and digital input (opaque)
    ad_part:             bytes = field(default_factory=bytes)
    digital_input_part:  bytes = field(default_factory=bytes)

    # Play settings (super knob, arp) — opaque tail
    play_settings:       bytes = field(default_factory=bytes)



    @property
    def name(self) -> str:
        """Performance name decoded from raw bytes (up to first null)."""
        raw = getattr(self, '_name_raw', b'')
        null = raw.find(b'\x00')
        return raw[:null].decode('latin-1', 'replace') if null >= 0 else raw.decode('latin-1', 'replace')

    @name.setter
    def name(self, value: str) -> None:
        encoded = value.encode('latin-1', 'replace')[:20]
        self._name_raw = encoded + b'\x00' * (21 - len(encoded))

    @classmethod
    def from_blob(cls, blob: bytes, fmt: str, version: int) -> "ClassicPerformance":
        """Parse a raw classic DPFM blob.

        blob    — the raw bytes of the DPFM data block (including the 4-byte
                  big-endian length prefix that CWM's readDataBlock reads first).
        fmt     — FORMAT_MONTAGE or FORMAT_MODX
        version — 3-digit int, e.g. 405 or 501
        """
        # The blob as stored in the DPFM pool already includes the 4-byte
        # "name length prefix" (0x000001af for classic) before the name.
        # CWM's YamahaYsfcChunk.getDataArrays() strips the outer DPFM
        # framing and gives us the raw data starting from that prefix.
        # YamahaYsfcPerformance receives it as-is and calls read(stream).
        # The first thing read() does is readDataBlock(in, true) which reads
        # a u32be size and then that many bytes as the 'common' sub-block.
        # So blob[0:4] is the size of the common sub-block.
        s = io.BytesIO(blob)
        perf = cls()
        perf.fmt     = fmt
        perf.version = version
        perf._read(s)
        return perf


    def _read(self, s: io.BytesIO) -> None:
        self._read_common(io.BytesIO(_read_data_block(s)))
        self._read_effects(s)
        self._read_parts(s)


    def _read_common(self, s: io.BytesIO) -> None:
        """Parse the common sub-block — all fixed-size fields stored as raw bytes."""
        # Name field: 21 bytes. May contain binary data after null terminator.
        self._name_raw = s.read(21)

        self.common_params = s.read(43)

        # Scene data size is format-dependent
        if self.fmt == FORMAT_MONTAGE:
            self.scene_data = s.read(8 * 11)  # 88 bytes
        else:
            self.scene_data = s.read(8 * 21)  # 168 bytes

        # Knobs: stored as raw 17-byte blocks — they contain binary data
        # (e.g. center values 0x40) after the null terminator, not just text.
        self.assignable_knobs = [s.read(17) for _ in range(8)]
        self.control_boxes = s.read(16 * 9)   # 144 bytes

        # Whatever remains (format/version-dependent padding or extra params)
        self.common_rest = s.read()


    def _read_effects(self, s: io.BytesIO) -> None:
        self.reverb_block        = _read_data_block(s)
        self.variation_block     = _read_data_block(s)
        self.master_eq_block     = _read_data_block(s)
        self.master_effect_block = _read_data_block(s)


    def _read_parts(self, s: io.BytesIO) -> None:
        n_parts = _read_u32be(s)

        # Read all part headers first (each is a length-prefixed block)
        all_part_headers: list[ClassicPerformancePart] = []
        for _ in range(n_parts):
            part_data = _read_data_block(s)
            p = ClassicPerformancePart._read_header(
                io.BytesIO(part_data), self.fmt, self.version
            )
            all_part_headers.append(p)

        self.ad_part            = _read_data_block(s)
        self.digital_input_part = _read_data_block(s)

        # Element sections — one per part, in same order
        for i in range(n_parts):
            part_type = _read_u32be(s)
            p = all_part_headers[i]
            p.type = part_type

            if part_type in (PART_TYPE_AWM2, PART_TYPE_DRUM):
                n_elements = _read_u32be(s)
                p.elements = [ClassicPartElement.from_stream(s) for _ in range(n_elements)]
                self.parts.append(p)

            elif part_type == PART_TYPE_FMX:
                n_ops = _read_u32be(s)
                p.fmx_common_opaque = _read_data_block(s)
                p.fmx_operator_opaque = [_read_data_block(s) for _ in range(n_ops)]
                self.parts.append(p)

            else:
                raise ValueError(f"Unknown part type {part_type} in classic performance '{self.name}'")

        self.play_settings = s.read()


    def to_blob(self) -> bytes:
        """Re-serialize to the classic blob byte format."""
        out = io.BytesIO()

        # Common sub-block
        common_out = io.BytesIO()
        # Write raw bytes (preserves binary content after null terminator)
        name_raw = self._name_raw if hasattr(self, '_name_raw') else self.name.encode('latin-1', 'replace')[:21].ljust(21, b'\x00')
        common_out.write(name_raw[:21].ljust(21, b'\x00') if len(name_raw) < 21 else name_raw[:21])
        common_out.write(self.common_params)
        common_out.write(self.scene_data)
        for k in self.assignable_knobs:
            raw = k if isinstance(k, (bytes, bytearray)) else k.encode('latin-1', errors='replace')
            raw = raw[:17].ljust(17, b'\x00') if len(raw) < 17 else raw[:17]
            common_out.write(raw)
        common_out.write(self.control_boxes)
        common_out.write(self.common_rest)
        _write_data_block(out, common_out.getvalue())

        # Effects
        _write_data_block(out, self.reverb_block)
        _write_data_block(out, self.variation_block)
        _write_data_block(out, self.master_eq_block)
        _write_data_block(out, self.master_effect_block)

        # Parts — header blocks
        _write_u32be(out, len(self.parts))
        for p in self.parts:
            part_out = io.BytesIO()
            p._write_header(part_out)
            _write_data_block(out, part_out.getvalue())

        # AD + digital input
        _write_data_block(out, self.ad_part)
        _write_data_block(out, self.digital_input_part)

        # Element sections
        for p in self.parts:
            _write_u32be(out, p.type)
            if p.type in (PART_TYPE_AWM2, PART_TYPE_DRUM):
                _write_u32be(out, len(p.elements))
                for e in p.elements:
                    e.write_framed(out)
            elif p.type == PART_TYPE_FMX:
                n_ops = len(p.fmx_operator_opaque)
                _write_u32be(out, n_ops)
                _write_data_block(out, p.fmx_common_opaque or b"")
                for op_data in p.fmx_operator_opaque:
                    _write_data_block(out, op_data)

        out.write(self.play_settings)
        return out.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Pitch key follow lookup table (from CWM PITCH_KEY static map)
# Maps raw stored byte (0-127) → semitone percentage value (-200..+200)
# Used when converting pitch_key_follow_sensitivity for display or mapping
# ─────────────────────────────────────────────────────────────────────────────

PITCH_KEY_TABLE: dict[int, int] = {
    0:0, 1:-199, 2:-198, 3:-197, 4:-196, 5:-195, 6:-194, 7:-193,
    8:-192, 9:-191, 10:-190, 11:-185, 12:-180, 13:-175, 14:-170,
    15:-165, 16:-160, 17:-155, 18:-150, 19:-145, 20:-140, 21:-135,
    22:-130, 23:-125, 24:-120, 25:-115, 26:-110, 27:-105, 28:-104,
    29:-103, 30:-102, 31:-101, 32:-100, 33:-99, 34:-98, 35:-97,
    36:-96, 37:-95, 38:-90, 39:-85, 40:-80, 41:-75, 42:-70, 43:-65,
    44:-60, 45:-55, 46:-50, 47:-45, 48:-40, 49:-35, 50:-30, 51:-25,
    52:-20, 53:-15, 54:-10, 55:-9, 56:-8, 57:-7, 58:-6, 59:-5,
    60:-4, 61:-3, 62:-2, 63:-1, 64:0, 65:1, 66:2, 67:3, 68:4,
    69:5, 70:6, 71:7, 72:8, 73:9, 74:10, 75:15, 76:20, 77:25,
    78:30, 79:35, 80:40, 81:45, 82:50, 83:55, 84:60, 85:65,
    86:70, 87:75, 88:80, 89:85, 90:90, 91:95, 92:96, 93:97,
    94:98, 95:99, 96:100, 97:101, 98:102, 99:103, 100:104,
    101:105, 102:110, 103:115, 104:120, 105:125, 106:130,
    107:135, 108:140, 109:145, 110:150, 111:155, 112:160,
    113:165, 114:170, 115:175, 116:180, 117:185, 118:190,
    119:192, 120:193, 121:194, 122:195, 123:196, 124:197,
    125:198, 126:199, 127:200,
}

# Also used as inverse lookup: percentage → raw byte
PITCH_KEY_INVERSE: dict[int, int] = {v: k for k, v in PITCH_KEY_TABLE.items()}


def pitch_key_raw_to_pct(raw: int) -> int:
    """Convert stored byte (0-127) to semitone percentage (-200..+200)."""
    return PITCH_KEY_TABLE.get(raw, 0)


def pitch_key_pct_to_raw(pct: int) -> int:
    """Find closest raw byte for a semitone percentage value."""
    if pct in PITCH_KEY_INVERSE:
        return PITCH_KEY_INVERSE[pct]
    # Find nearest
    best = min(PITCH_KEY_TABLE.keys(), key=lambda k: abs(PITCH_KEY_TABLE[k] - pct))
    return best


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: parse classic blob from a raw bytes object (as stored in DPFM)
# ─────────────────────────────────────────────────────────────────────────────

def parse_classic_blob(blob: bytes, version_str: str) -> ClassicPerformance:
    """Parse a raw DPFM blob from a classic X7L or X8L file.

    blob        — the raw bytes at the DPFM pool entry (e.g. pool[dp_off:dp_off+item_size])
    version_str — the file version string from the YSFC header (e.g. '4.0.5' or '5.0.1')

    Returns a ClassicPerformance with all decoded fields.
    """
    fmt     = detect_format(version_str)
    version = _parse_version_int(version_str)
    return ClassicPerformance.from_blob(blob, fmt, version)


def _parse_version_int(version_str: str) -> int:
    """Convert '4.0.5' → 405, '5.0.1' → 501."""
    try:
        parts = version_str.strip().split(".")
        return int(parts[0]) * 100 + int(parts[1]) * 10 + int(parts[2])
    except (ValueError, IndexError):
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# Quick-dump utility (for debugging / verification)
# ─────────────────────────────────────────────────────────────────────────────

def dump_performance(perf: ClassicPerformance) -> str:
    """Return a human-readable summary of a parsed classic performance."""
    lines = [
        f"Performance: {perf.name!r}",
        f"  Format:  {perf.fmt}  (version {perf.version})",
        f"  Parts:   {len(perf.parts)}",
    ]
    for i, p in enumerate(perf.parts):
        type_label = {PART_TYPE_AWM2: "AWM2", PART_TYPE_DRUM: "Drum", PART_TYPE_FMX: "FM-X"}.get(p.type, f"?{p.type}")
        lines.append(f"  Part {i}: {p.name!r}  type={type_label}  switch={p.part_switch}  elements={len(p.elements)}")
        for j, e in enumerate(p.elements[:4]):
            if e.element_switch:
                lines.append(
                    f"    Elem {j}: on  waveform={e.waveform_number}  level={e.element_level}"
                    f"  pan={e.pan}  note={e.note_limit_low}-{e.note_limit_high}"
                    f"  vel={e.velocity_limit_low}-{e.velocity_limit_high}"
                    f"  filter={e.filter_type}  cutoff={e.filter_cutoff_frequency}"
                )
        if len(p.elements) > 4:
            lines.append(f"    ... ({len(p.elements) - 4} more elements)")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Self-test: round-trip parse → serialize → compare
# ─────────────────────────────────────────────────────────────────────────────

def roundtrip_test(blob: bytes, version_str: str) -> bool:
    """Parse a classic blob and re-serialize it; verify byte-identity.

    Returns True if the round-trip is perfect, False otherwise.
    Prints a diff summary if the blobs differ.
    """
    perf = parse_classic_blob(blob, version_str)
    rebuilt = perf.to_blob()
    if blob == rebuilt:
        print(f"  PASS  {perf.name!r} ({len(blob)} bytes)")
        return True
    # Find first differing byte
    min_len = min(len(blob), len(rebuilt))
    first_diff = next((i for i in range(min_len) if blob[i] != rebuilt[i]), min_len)
    print(
        f"  FAIL  {perf.name!r}: blobs differ at byte {first_diff:#x}  "
        f"orig={blob[first_diff]:#04x}  rebuilt={rebuilt[first_diff]:#04x}  "
        f"orig_len={len(blob)}  rebuilt_len={len(rebuilt)}"
    )
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Envelope time table (from CWM YamahaYsfcPartElement.ENVELOPE_TIMES)
# Raw value 0-127 → seconds
# Used for AEG/PEG/FEG time fields.
# IMPORTANT from CWM YamahaYsfcCreator.setElementParameters():
#   Attack times are passed in as  seconds × 6.0  before conversion.
#   Hold, Decay, Release times are passed in as plain seconds.
# ─────────────────────────────────────────────────────────────────────────────

ENVELOPE_TIMES: list[float] = [
    0.200, 0.21,  0.22,  0.23,  0.24,  0.25,  0.26,  0.27,  0.28,  0.29,
    0.300, 0.304, 0.308, 0.312, 0.316, 0.320, 0.324, 0.328, 0.332, 0.336,
    0.340, 0.343, 0.346, 0.349, 0.352, 0.355, 0.358, 0.361, 0.364, 0.367,
    0.370, 0.373, 0.376, 0.379, 0.382, 0.385, 0.388, 0.391, 0.394, 0.397,
    0.400, 0.404, 0.408, 0.412, 0.416, 0.420, 0.424, 0.428, 0.432, 0.436,
    0.440, 0.446, 0.452, 0.458, 0.464, 0.470, 0.476, 0.482, 0.488, 0.494,
    0.500, 0.54,  0.58,  0.62,  0.66,  0.70,  0.74,  0.78,  0.82,  0.86,
    0.900, 1.02,  1.14,  1.26,  1.38,  1.50,  1.62,  1.74,  1.86,  1.98,
    2.100, 2.29,  2.48,  2.67,  2.86,  3.05,  3.24,  3.43,  3.62,  3.81,
    4.000, 4.8,   5.6,   6.4,   7.2,   8.0,   8.8,   9.6,   10.4,  11.2,
    12.00, 13.3,  14.6,  15.9,  17.2,  18.5,  19.8,  21.1,  22.4,  23.7,
    25.00, 28.9,  32.8,  36.7,  40.6,  44.5,  48.4,  52.3,  56.2,  60.1,
    64.00, 67.714, 71.429, 75.143, 78.857, 82.571, 86.286, 90.000,
]

def envelope_raw_to_seconds(raw: int) -> float:
    """Convert raw AEG/PEG/FEG time value (0-127) → seconds."""
    return ENVELOPE_TIMES[max(0, min(127, raw))]


def envelope_seconds_to_raw(seconds: float) -> int:
    """Convert seconds → raw AEG/PEG/FEG time value (0-127).

    Finds the nearest representable value in the ENVELOPE_TIMES table.
    """
    if seconds <= ENVELOPE_TIMES[0]:
        return 0
    for i in range(127):
        if ENVELOPE_TIMES[i] <= seconds < ENVELOPE_TIMES[i + 1]:
            # Pick nearest
            if abs(seconds - ENVELOPE_TIMES[i]) <= abs(seconds - ENVELOPE_TIMES[i + 1]):
                return i
            return i + 1
    return 127


# ─────────────────────────────────────────────────────────────────────────────
# Parameter conversion utilities
# Source: YamahaYsfcCreator.setElementParameters() and createKeybank()
# These are the EXACT formulas CWM uses to map synthesis parameters to raw
# stored values.  Ported from Java to Python for use in Fas 3 transcoding.
# ─────────────────────────────────────────────────────────────────────────────

def gain_db_to_element_level(gain_db: float) -> int:
    """Convert gain in dB → element_level raw value (0-127).

    Source: YamahaYsfcCreator.setElementParameters() line 464-465
    Formula: round((gain_dB + 95.25) / (2 × 0.375))
           = round((gain_dB + 95.25) / 0.75)
    Range:  0 → -95.25 dB (silence),  127 → 0 dB (full level)
    """
    if gain_db == float('-inf') or gain_db < -95.25:
        return 0
    return int(round((gain_db + 95.25) / 0.75))


def element_level_to_gain_db(raw: int) -> float:
    """Convert element_level raw value (0-127) → gain in dB.

    Inverse of gain_db_to_element_level().
    Formula: gain_dB = raw × 0.75 − 95.25
    """
    if raw == 0:
        return float('-inf')
    return raw * 0.75 - 95.25


def gain_db_to_keybank_level(gain_db: float) -> int:
    """Convert gain in dB → keybank level raw value (0-255).

    Source: YamahaYsfcCreator.createKeybank() lines 784-785
    Formula: round((gain + 95.25) / 0.375) + 1   [NOTE: different from element_level!]
    Range:  0 → -95.25 dB,  255 → +0.20 dB (approx)
    Used for EWFM/DWFM (waveform) key-bank records, not performance elements.
    """
    if gain_db < -95.25:
        return 0
    return int(round((min(gain_db, 0.0) + 95.25) / 0.375)) + 1


def panning_to_raw(panning_normalized: float) -> int:
    """Convert normalized panning (-1.0..+1.0) → raw pan value (1-127, 64=center).

    Source: YamahaYsfcCreator.setElementParameters() line 460
    Formula: denormalizeIntegerRange(panning, -63, 63, 64)
    """
    raw = int(round(panning_normalized * 63)) + 64
    return max(1, min(127, raw))


def raw_to_panning(raw: int) -> float:
    """Convert raw pan (1-127, 64=center) → normalized panning (-1.0..+1.0)."""
    return (raw - 64) / 63.0


def velocity_sensitivity_to_raw(depth_normalized: float, half_range: bool = False) -> int:
    """Convert velocity sensitivity depth → raw value (0-127, 64=centre=0).

    Source: YamahaYsfcCreator.setElementParameters() line 464
    half_range=True:  maps −32..+32 (level vel sens — "gets unplayable past ±32")
    half_range=False: maps −64..+63 (full range)
    """
    limit = 32 if half_range else 63
    raw = int(round(depth_normalized * limit)) + 64
    return max(0, min(127, raw))


def aeg_attack_seconds_to_raw(attack_seconds: float) -> int:
    """Convert AEG/PEG/FEG attack time (seconds) → raw value (0-127).

    CRITICAL: CWM multiplies attack seconds by 6.0 before conversion.
    Source: YamahaYsfcCreator.setElementParameters() line 473
      element.setAegAttackTime(convertSecondsToEnvelopeTime(attack_sec × 6.0))
    This applies to: AEG attack, PEG attack, FEG attack.
    All OTHER envelope times (hold, decay, release) use plain seconds.
    """
    return envelope_seconds_to_raw(attack_seconds * 6.0)


def aeg_attack_raw_to_seconds(raw: int) -> float:
    """Convert raw AEG/PEG/FEG attack value → seconds (undoing the ×6 factor)."""
    return envelope_raw_to_seconds(raw) / 6.0


def coarse_tune_to_raw(semitones: float) -> tuple[int, int]:
    """Convert tuning in semitones (float) → (coarse_tune_raw, fine_tune_raw).

    Source: YamahaYsfcCreator.setElementParameters() lines 453-455
    coarse = round(semitones) + 64       [range 16-112, 64=0 semitones]
    fine   = round(frac_semitones × 100) + 64  [range 0-127, 64=0 cents]
    """
    semitones_int = int(round(semitones))
    frac_cents = (semitones - semitones_int) * 100
    coarse = max(16, min(112, semitones_int + 64))
    fine   = max(0,  min(127, int(round(frac_cents)) + 64))
    return coarse, fine


def raw_to_tuning_semitones(coarse_raw: int, fine_raw: int) -> float:
    """Convert (coarse_tune_raw, fine_tune_raw) → tuning in semitones (float)."""
    semitones = coarse_raw - 64
    cents = fine_raw - 64
    return semitones + cents / 100.0


# ─────────────────────────────────────────────────────────────────────────────
# Filter type mapping (from CWM YamahaYsfcCreator FILTER_TYPE_MAP)
# Maps (filter_family, pole_count) → Yamaha filterType index
# ─────────────────────────────────────────────────────────────────────────────

# filter_family values (matches CWM FilterType enum names)
FILTER_LPF = "LPF"   # Low-pass
FILTER_HPF = "HPF"   # High-pass
FILTER_BPF = "BPF"   # Band-pass
FILTER_BRF = "BRF"   # Band-rejection (notch)

# (family, poles) → filterType raw index
# filterType 17 = Thru (no filter) — the default
FILTER_TYPE_MAP: dict[tuple[str, int], int] = {
    (FILTER_LPF, 4): 0,   # LPF24D
    (FILTER_LPF, 3): 2,   # LPF18
    (FILTER_LPF, 2): 4,   # LPF12+HPF12
    (FILTER_HPF, 4): 6,   # HPF24D
    (FILTER_HPF, 2): 7,   # HPF12
    (FILTER_BPF, 2): 8,   # BPF12D
    (FILTER_BPF, 1): 9,   # BPFw
    (FILTER_BRF, 2): 10,  # BEF12
    (FILTER_BRF, 1): 11,  # BEF6
}

# Default when pole count is not in the map
FILTER_TYPE_DEFAULTS: dict[str, int] = {
    FILTER_LPF: 0,   # LPF24D
    FILTER_HPF: 6,   # HPF24D
    FILTER_BPF: 8,   # BPF12D
    FILTER_BRF: 10,  # BEF12
}

# Reverse mapping: filterType index → (family, approx_poles)
FILTER_TYPE_REVERSE: dict[int, tuple[str, int]] = {v: k for k, v in FILTER_TYPE_MAP.items()}


def filter_to_raw(family: str, poles: int) -> int:
    """Convert (filter family, pole count) → Yamaha filterType raw index.

    Returns 17 (Thru) for unknown families.
    Source: YamahaYsfcCreator FILTER_TYPE_MAP static initializer.
    """
    idx = FILTER_TYPE_MAP.get((family, poles))
    if idx is not None:
        return idx
    return FILTER_TYPE_DEFAULTS.get(family, 17)


def cutoff_normalized_to_raw(cutoff_normalized: float) -> int:
    """Convert normalized filter cutoff (0.0-1.0) → raw value (0-255).

    Source: YamahaYsfcCreator.setElementParameters() line 497
    Formula: round(normalize_frequency(cutoff, MAX_FREQ) × 255)
    CWM's normalizeFrequency maps Hz on a log scale to 0..1.
    For Fas 3: use directly if the source value is already normalized.
    """
    return max(0, min(255, int(round(cutoff_normalized * 255.0))))


def resonance_normalized_to_raw(resonance_normalized: float) -> int:
    """Convert normalized resonance (0.0-1.0) → raw value (0-127).

    Source: YamahaYsfcCreator.setElementParameters() line 498
    """
    return max(0, min(127, int(round(resonance_normalized * 127.0))))


# ─────────────────────────────────────────────────────────────────────────────
# Init Performance templates (binary blobs from CWM resources)
# These are valid classic DPFM blobs used as starting points for new performances.
# Format: prefix=0x00000200 (512-byte common block), classic AWM2 structure.
#
#   InitPerf405.bin   — Montage  4.0.5,  1 part,  6 746 bytes  (name='Tesform')
#   InitPerf405-8.bin — Montage  4.0.5,  8 parts, 32 765 bytes (name='Init Normal (AWM2) 8')
#   InitPerf501.bin   — MODX     5.0.1,  1 part,  6 748 bytes  (name='Init AWM2')
#   InitPerf501-8.bin — MODX     5.0.1,  8 parts, 32 774 bytes (name='Init Normal (AWM2) 8')
#
# Load with: parse_classic_blob(open('InitPerf405.bin','rb').read(), '4.0.5')
# ─────────────────────────────────────────────────────────────────────────────

INIT_PERF_TEMPLATE_NAMES = {
    ("MONTAGE", 1): "InitPerf405.bin",
    ("MONTAGE", 8): "InitPerf405-8.bin",
    ("MODX",    1): "InitPerf501.bin",
    ("MODX",    8): "InitPerf501-8.bin",
}


def load_init_template(fmt: str, num_parts: int, template_dir: str = ".") -> "ClassicPerformance":
    """Load a CWM Init Performance template as a ClassicPerformance object.

    fmt        — FORMAT_MONTAGE or FORMAT_MODX
    num_parts  — 1 (single-part) or 8 (eight-part)
    template_dir — directory containing InitPerf*.bin files

    The templates are useful as reference starting-points showing the default
    parameter values CWM uses when building new performances from scratch.
    """
    import os
    template_name = INIT_PERF_TEMPLATE_NAMES.get((fmt, num_parts))
    if template_name is None:
        raise ValueError(f"No template for fmt={fmt!r} num_parts={num_parts}")
    path = os.path.join(template_dir, template_name)
    with open(path, 'rb') as f:
        data = f.read()
    version_str = "4.0.5" if fmt == FORMAT_MONTAGE else "5.0.1"
    return parse_classic_blob(data, version_str)


# ─────────────────────────────────────────────────────────────────────────────
# Fas 3 helper: build a minimal ClassicPartElement with "sane defaults"
# matching what CWM would write for a new AWM2 performance.
# Source: YamahaYsfcCreator.setElementParameters() + template defaults.
# ─────────────────────────────────────────────────────────────────────────────

def make_default_element(
    waveform_number: int = 1,
    wave_bank: int = 1,
    note_low: int = 0,
    note_high: int = 127,
    vel_low: int = 1,
    vel_high: int = 127,
    element_level: int = 127,
    pan: int = 64,
    filter_type: int = 17,           # 17=Thru
    filter_cutoff: int = 255,
    aeg_attack_raw: int = 0,
    aeg_decay1_raw: int = 60,
    aeg_sustain_level: int = 127,    # aeg_decay1_level = aeg_decay2_level = sustain
    aeg_release_raw: int = 50,
    coarse_tune: int = 64,           # 64 = 0 semitones
    fine_tune: int = 64,             # 64 = 0 cents
) -> "ClassicPartElement":
    """Create a ClassicPartElement with defaults matching CWM's Init Normal template.

    Override individual fields as needed for Fas 3 parameter mapping.
    Waveform IDs: 1-based, same scheme in classic and Y2L for preset waveforms.
    """
    e = ClassicPartElement()
    e.element_switch     = 1
    e.wave_bank          = wave_bank
    e.waveform_number    = waveform_number
    e.note_limit_low     = note_low
    e.note_limit_high    = note_high
    e.velocity_limit_low  = vel_low
    e.velocity_limit_high = vel_high
    e.element_level      = element_level
    e.pan                = pan
    e.filter_type        = filter_type
    e.filter_cutoff_frequency = filter_cutoff
    e.aeg_attack_time    = aeg_attack_raw
    e.aeg_decay1_time    = aeg_decay1_raw
    e.aeg_decay2_time    = aeg_decay1_raw
    e.aeg_release_time   = aeg_release_raw
    e.aeg_attack_level   = 127
    e.aeg_decay1_level   = aeg_sustain_level
    e.aeg_decay2_level   = aeg_sustain_level
    e.aeg_init_level     = 0
    e.coarse_tune        = coarse_tune
    e.fine_tune          = fine_tune
    e.pitch_key_follow_sensitivity = 96  # 100%
    # PEG, FEG centres (128 = 0)
    e.peg_hold_level = e.peg_attack_level = e.peg_decay1_level = 128
    e.peg_decay2_level = e.peg_release_level = 128
    e.feg_hold_level = e.feg_attack_level = e.feg_decay1_level = 128
    e.feg_decay2_level = e.feg_release_level = 128
    # LFO off
    e.lfo_pmod_depth = e.lfo_amod_depth = e.lfo_fmod_depth = 0
    return e


# ─────────────────────────────────────────────────────────────────────────────
# Complete filter type name table (from YamahaYsfcDetector FILTER_TYPE_MAP +
# FILTER_POLE_MAP static maps, CWM v18.0.0)
#
# This is more complete than FILTER_TYPE_MAP above (which was ported from
# Creator and only covers the types Creator knows how to write).
# Use this table for display/inspection of filter_type raw values read from
# real X7L/X8L/Y2L blobs.
#
# NOTE — CWM BUG: Creator and Detector are INCONSISTENT on indices 9-13.
#   Creator: 9=BPFw(BPF,1), 10=BEF12(BRF,2), 11=BEF6(BRF,1)
#   Detector: (9 missing),   10=BPFw(BPF,1),  11=BPF6(BPF,1),
#             12=BEF12(BRF,2), 13=BEF6(BRF,1)
# Yamaha's Reference Manual names are authoritative. CWM's indices 9-13
# appear off-by-one in the Detector relative to the Creator.
# For Fas 3 raw→raw transcoding this doesn't matter; only affects display.
#
# Yamaha filterType indices (from Reference Manual, confirmed by CWM):
#   0=LPF24D, 1=LPF24A, 2=LPF18, 3=LPF18s, 4=LPF12+HPF12, 5=LPF6+HPF12,
#   6=HPF24D, 7=HPF12, 8=BPF12D, 9=BPFw, 10=BEF12, 11=BEF6,
#   12=DualLPF, 13=DualHPF, 14=DualBPF, 15=DualBEF, 16=LPF12+HPF6, 17=Thru
# ─────────────────────────────────────────────────────────────────────────────

# filterType raw index → (name, family, poles)
FILTER_TYPE_NAMES: dict[int, tuple[str, str, int]] = {
    0:  ("LPF24D",      FILTER_LPF, 4),
    1:  ("LPF24A",      FILTER_LPF, 4),
    2:  ("LPF18",       FILTER_LPF, 3),
    3:  ("LPF18s",      FILTER_LPF, 3),
    4:  ("LPF12+HPF12", FILTER_LPF, 2),
    5:  ("LPF6+HPF12",  FILTER_LPF, 1),
    6:  ("HPF24D",      FILTER_HPF, 4),
    7:  ("HPF12",       FILTER_HPF, 2),
    8:  ("BPF12D",      FILTER_BPF, 2),
    9:  ("BPFw",        FILTER_BPF, 1),
    10: ("BEF12",       FILTER_BRF, 2),
    11: ("BEF6",        FILTER_BRF, 1),
    12: ("DualLPF",     FILTER_LPF, 4),
    13: ("DualHPF",     FILTER_HPF, 4),
    14: ("DualBPF",     FILTER_BPF, 4),
    15: ("DualBEF",     FILTER_BRF, 4),
    16: ("LPF12+HPF6",  FILTER_LPF, 2),
    17: ("Thru",        "",         0),
}


def filter_type_name(raw_index: int) -> str:
    """Return the Yamaha filter type name for a raw filterType index (0-17).

    Returns 'Unknown(N)' for unrecognised values.
    Source: Yamaha Reference Manual + CWM YamahaYsfcDetector.
    """
    entry = FILTER_TYPE_NAMES.get(raw_index)
    return entry[0] if entry else f"Unknown({raw_index})"


# ─────────────────────────────────────────────────────────────────────────────
# YSFC file-level constants (from YsfcFile.java and YamahaYsfcChunk.java)
# Relevant if building a Y2L file from scratch in Fas 3.
# ─────────────────────────────────────────────────────────────────────────────

YSFC_MAGIC            = "YAMAHA-YSFC"
YSFC_HEADER_SIZE      = 64            # bytes, fixed
YSFC_LIBRARY_SIZE     = 81            # bytes, fixed (v4.x/5.x only, not v1.x)
YSFC_MAX_ENTRY_ID_START = 0x2711      # 10001 — entry IDs count up from here

# Chunk IDs
CHUNK_EPFM = "EPFM"   # Entry List Performance
CHUNK_DPFM = "DPFM"   # Data List Performance
CHUNK_EWFM = "EWFM"   # Entry List Waveform Metadata
CHUNK_DWFM = "DWFM"   # Data List Waveform Metadata
CHUNK_EWIM = "EWIM"   # Entry List Waveform Data (samples)
CHUNK_DWIM = "DWIM"   # Data List Waveform Data (samples)

# Chunk write order (from YsfcFile.sortAndUpdateChunks()):
# EPFM, EWFM, EWIM, DPFM, DWFM, DWIM,
# then 10 empty dummy chunks: EARP, DARP, ESOM, ESPG, DSOM, DSPG, ECRV, DCRV, ELST, DLST
CHUNK_WRITE_ORDER = [
    CHUNK_EPFM, CHUNK_EWFM, CHUNK_EWIM,
    CHUNK_DPFM, CHUNK_DWFM, CHUNK_DWIM,
    "EARP", "DARP", "ESOM", "ESPG", "DSOM", "DSPG", "ECRV", "DCRV", "ELST", "DLST",
]

# DWFM pool item format (from YsfcFile.addWaveChunks()):
#   u16le(keybank_count) + u16(padding=0) + keybank_records...
# DWIM pool item format:
#   u32be(wavedata_count) + wavedata_records... (each: u32be(size) + pcm_bytes)

# EPFM entry flags (from YamahaYsfcCreator.createPerformanceEntry()):
#   flags[0] = Motion Control (0=off)
#   flags[1] = Type Flag (0=AWM)
#   flags[2] = Favorite (0=off)
#   flags[3] = 0x01 SSS unavailable (>8 parts), 0x02 single-part, 0x04 arp, 0x08 motion seq, 0x10 mono
#   flags[4:6] = category bitmask (u16be, bit N = main category N)
EPFM_FLAG_SINGLE_PART    = 0x02
EPFM_FLAG_SSS_UNAVAIL    = 0x01
EPFM_FLAG_ARP_ENABLED    = 0x04
EPFM_FLAG_MOTION_SEQ     = 0x08
EPFM_FLAG_MONO_PART      = 0x10

# EPFM content_number base (Bank Select + Program Change)
EPFM_CONTENT_NUMBER_BASE = 0x3F2000   # +performanceIndex for each performance
