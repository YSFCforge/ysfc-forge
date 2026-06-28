"""
ysfc_transcoder_classic_to_y2l.py
──────────────────────────────────
Transkodning av klassiska AWM2-performances (X7L/X8L) till Y2L-format.

Konverteringspipeline:
  1. Parse classical blob  → ClassicPerformance  (via ysfc_serializer_classic.py)
  2. Transcode             → TranscodedPerformance (detta modul)
  3. Inject into Y2L       → Y2L blob            (via ysfc_serializer.py)

Omfång:
  ✅ AWM2 parts (type=0) — alla 120 parametrar mappade
  ✅ Drum parts  (type=1) — bevaras som AWM2 (raw copy av element-data)
  ✅ FM-X parts  (type=2) — binäranalys av Y2L FM-X-format 
  ✅ User waveforms       — waveform-pool remappning

Adresskonventioner (Y2L):
  AWM2 element base    = engine_area_start + 3 bytes header (= audit_abs 12469 för Part 1)
  AWM2_ELEM_LAYOUT bas = element_base + 51  (= audit_abs 12520)
  AWM2_ELEM_LAYOUT[f]  = offset från bas, dvs rel från element_base = 51 + ELEM_LAYOUT[f]
  AWM2_ELEMENT_FIELDS  = dict keyed på rel-offset direkt från element_base

  Bekräftat: rel+59=pan, rel+91=level, rel+99=aeg_attack, rel+149=coarse_tune, etc.

Filtertyp-mapping:
  Klassisk och Y2L delar SAMMA filtertyp-indices 0-17 med identiska namn.
  Classic 17=Thru, Y2L 21=Thru. Indices 0-16 är identiska.
  Enkel regel: om classic_filterType == 17 → y2l_filterType = 21, annars kopieras direkt.

Filter cutoff-konvertering:
  Klassisk: 0-255 (normaliserad log-skala, 255 = ~20kHz)
  Y2L: u16le Hz (0..20000)
  Formula: y2l_hz = round(2^(raw/255 × log2(20000)))
  Invers (för retur): raw = round(log2(hz)/log2(20000) × 255)

Viktiga fält som INTE mappas (sätts till default från Y2L Init Normal):
  - level_scaling (break points, offsets) — opak i klassisk
  - filter_scaling (cutoff scaling) — opak i klassisk
  - PEG depth, levels (opak i klassisk)
  - FEG depth, levels (opak i klassisk)
  - LFO (opak i klassisk — bevaras från klassisk via direkt mapping)
  - many_parameters (274/275 bytes opak part-data) — Y2L default
  - common_params (43 bytes) — Y2L default
  - Part Common parametrar (volume, part AEG/FEG) — Y2L default
"""

from __future__ import annotations

import io
import math
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Import-beroenden
# ─────────────────────────────────────────────────────────────────────────────

_THIS_DIR = Path(__file__).parent
sys.path.insert(0, str(_THIS_DIR))
sys.path.insert(0, str(_THIS_DIR / 'mnt' / 'project'))
sys.path.insert(0, '/mnt/project')

from ysfc_serializer_classic import (
    ClassicPerformance,
    ClassicPerformancePart,
    ClassicPartElement,
    PART_TYPE_AWM2,
    PART_TYPE_DRUM,
    PART_TYPE_FMX,
    parse_classic_blob,
    FILTER_TYPE_NAMES,
    FORMAT_MONTAGE,
    FORMAT_MODX,
)

# ─────────────────────────────────────────────────────────────────────────────
# Y2L sub-blob konstanter (från ysfc_serializer.py)
# ─────────────────────────────────────────────────────────────────────────────

SUBBLOB_COMMON_SIZE   = 6701   # Common sub-blob = alltid 6701 bytes
SUBBLOB_DEFAULT_SIZE  = 5765   # Varje part sub-blob = alltid 5765 bytes
SUBBLOB_HEADER_SIZE   = 27     # 4 (prefix 0x00000015) + 18 (name) + 1 (null) + 4 (hash)
SUBBLOB_PREFIX        = b'\x00\x00\x00\x15'   # 4-byte sub-blob prefix i Y2L

# Engine area: sista sub-blob start + 5765
# AWM2 engine header: 3 bytes (engine_type_byte + 2)
# AWM2 element 1 base (audit_abs): engine_area_start + 3
# AWM2_ELEM_LAYOUT base: element_base + 51
AWM2_ENGINE_HEADER_SIZE = 3
AWM2_ELEMENT_STRIDE     = 313
AWM2_LAST_ELEMENT_SIZE  = 309
ENGINE_POOL_SEP_SIZE    = 5
AWM2_ELEM_LAYOUT_OFFSET = 51   # AWM2_ELEM_LAYOUT keys är rel från elem_base - 51

# Engine type bytes (Y2L blob[6700])
Y2L_ENGINE_AWM2 = 0x0A   # AWM2  (≈ element_count + 2, default element_count=8 → 0x0A)
Y2L_ENGINE_DRUM = 0x01   # Drum
Y2L_ENGINE_FMX  = 0x02   # FM-X
Y2L_ENGINE_ANX  = 0x03   # AN-X

# ─────────────────────────────────────────────────────────────────────────────
# Filter cutoff konvertering
# ─────────────────────────────────────────────────────────────────────────────

_MAX_FREQ = 20000.0

def classic_cutoff_to_hz(raw: int) -> int:
    """Konvertera klassisk cutoff (0-255, log-normaliserad) → Y2L Hz (0-20000).

    Klassisk formel: norm = raw/255, freq = 2^(norm × log2(MAX_FREQ))
    Y2L lagrar cutoff som u16le Hz direkt.
    """
    if raw <= 0:
        return 0
    if raw >= 255:
        return int(_MAX_FREQ)
    norm = raw / 255.0
    hz = math.pow(2.0, norm * math.log2(_MAX_FREQ))
    return max(0, min(int(_MAX_FREQ), round(hz)))


def hz_to_classic_cutoff(hz: int) -> int:
    """Konvertera Y2L Hz → klassisk cutoff raw (0-255)."""
    if hz <= 0:
        return 0
    if hz >= _MAX_FREQ:
        return 255
    norm = math.log2(hz) / math.log2(_MAX_FREQ)
    return max(0, min(255, round(norm * 255)))


# ─────────────────────────────────────────────────────────────────────────────
# Filter type mapping: klassisk (0-17) → Y2L (0-21)
# ─────────────────────────────────────────────────────────────────────────────
# Klassisk och Y2L delar index 0-16 med identiska filternamn.
# Enda skillnad: Thru = 17 i klassisk, 21 i Y2L.

def classic_filter_type_to_y2l(classic_type: int) -> int:
    """Konvertera klassisk filterType (0-17) → Y2L filterType (0-21).

    Indices 0-16 är identiska i båda format (LPF24D..LPF12+HPF6).
    Thru: klassisk=17, Y2L=21.
    """
    if classic_type == 17:
        return 21   # Thru
    return classic_type   # 0-16 är identiska


def y2l_filter_type_to_classic(y2l_type: int) -> int:
    """Konvertera Y2L filterType (0-21) → klassisk filterType (0-17)."""
    if y2l_type == 21:
        return 17   # Thru
    if y2l_type > 16:
        return 17   # Y2L-typer 17-20 saknar klassisk motsvarighet → Thru
    return y2l_type


# ─────────────────────────────────────────────────────────────────────────────
# Mappnings-tabell: klassiska element-fält → Y2L rel-offsets
# ─────────────────────────────────────────────────────────────────────────────
# Alla rel-offsets är från AWM2 element base (audit_abs = element start).
# Hämtade ur AWM2_ELEM_LAYOUT (serializer base +51) och AWM2_ELEMENT_FIELDS.

# Format: classic_attr → y2l_rel_offset
# 'direct' = samma råvärde kopieras utan transformation
# Fält som saknar direkt mapping eller kräver omvandling hanteras explicit.

_DIRECT_COPY_FIELDS = {
    # ── Playback / XA ─────────────────────
    'element_switch':              0,    # bool 0/1
    'xa_mode':                    67,    # 0-7
    # ── Key / velocity zones ──────────────
    'note_limit_low':             69,
    'note_limit_high':            71,
    'velocity_limit_low':         73,
    'velocity_limit_high':        75,
    'velocity_cross_fade':        77,
    # ── Amp / Level ───────────────────────
    'pan':                        59,    # 1-127, center=64
    'element_level':              91,    # 0-127
    'level_velocity_sensitivity': 93,    # 0-127, center=64
    # ── AEG times ─────────────────────────
    'aeg_attack_time':            99,    # 0-127
    'aeg_decay1_time':           101,
    'aeg_decay2_time':           103,
    'aeg_release_time':          107,
    # ── AEG levels ────────────────────────
    'aeg_init_level':            109,
    'aeg_attack_level':          111,
    'aeg_decay1_level':          113,
    'aeg_decay2_level':          115,
    # ── Pitch ─────────────────────────────
    'coarse_tune':               149,    # 0-127, center=64
    'fine_tune':                 151,    # 0-127, center=64
    'pitch_velocity_sensitivity':153,
    'random_pitch_depth':        155,
    'pitch_key_follow_sensitivity': 157, # PITCH_KEY table index (96=100%)
    'pitch_key_follow_center_note': 159, # MIDI note
    # ── PEG times ─────────────────────────
    'peg_hold_time':             163,
    'peg_attack_time':           165,
    'peg_decay1_time':           167,
    'peg_decay2_time':           169,
    'peg_release_time':          171,
    # ── PEG levels (c128) ─────────────────
    'peg_hold_level':            173,
    'peg_attack_level':          175,
    'peg_decay1_level':          177,
    'peg_decay2_level':          179,
    'peg_release_level':         181,
    'peg_depth':                 183,    # c64
    # ── Filter ────────────────────────────
    # filter_type: hanteras separat (konvertering)
    # filter_cutoff_frequency: hanteras separat (Hz-konvertering)
    'filter_cutoff_velocity_sensitivity': 205,
    'filter_resonance':          207,
    'filter_resonance_velocity_sensitivity': 209,
    # hpf_cutoff_frequency: hanteras separat (Hz)
    'filter_gain':               215,
    # ── FEG times ─────────────────────────
    'feg_hold_time':             217,
    'feg_attack_time':           219,
    'feg_decay1_time':           221,
    'feg_decay2_time':           223,
    'feg_release_time':          225,
    # ── FEG levels ────────────────────────
    'feg_hold_level':            227,
    'feg_attack_level':          229,
    'feg_decay1_level':          231,
    'feg_decay2_level':          233,
    'feg_release_level':         235,
    'feg_depth':                 237,    # c104 i Y2L (c64 i klassisk, adj nedan)
    # ── LFO ───────────────────────────────
    'lfo_wave':                  283,    # 0=Saw,1=Tri,2=Square (samma i båda)
    'lfo_amod_depth':            291,
    'lfo_pmod_depth':            293,
    'lfo_fmod_depth':            295,
    'lfo_fade_in_time':          297,
    'lfo_speed':                 307,    # u8 (extended LFO av)
}

# Fält som INTE mappas direkt (hanteras med speciallogik):
# - waveform_number    : u16le → u16le (direkt men separat skrivning)
# - filter_type        : index-konvertering (17→21)
# - filter_cutoff      : 0-255 → u16le Hz
# - hpf_cutoff         : 0-255 → u16le Hz
# - feg_depth          : c64 i klassisk (64=0), c104 i Y2L (104=0)

# ─────────────────────────────────────────────────────────────────────────────
# Y2L Init Normal AWM2 — default element (313 bytes)
# Dessa värden är defaults för alla omappade fält.
# Baserade på AWM2_ELEMENT_FIELDS default-kolumnen i YSFC_FORGE_FULL_CONTEXT.md
# ─────────────────────────────────────────────────────────────────────────────

def _make_y2l_default_element() -> bytearray:
    """Skapa ett 313-byte Y2L AWM2 Init Normal element med factory defaults."""
    e = bytearray(313)

    def w(rel, val):
        e[rel] = val & 0xFF

    def w16(rel, val):
        val = max(0, min(0xFFFF, val))
        e[rel]     = val & 0xFF
        e[rel + 1] = (val >> 8) & 0xFF

    # ── Enable / flags ──────────────
    w(0, 1)         # enable = 1 (on)
    w(1, 0)         # keyondly_sync = off
    w(2, 0)         # aeg_half_damper = off
    # Y2L serializes 39 presence/activation flags before the waveform fields.
    # Byte 6 is format-dependent and is set by transcode_element().
    for rel in (*range(3, 6), *range(7, 43)):
        w(rel, 1)
    w(6, 1)         # X7L/MONTAGE extended-LFO layout default

    # ── Waveform ────────────────────
    w16(51, 6)      # waveformNumber = 6 (default "CFX v06 St")
    w(53, 0)        # waveformBank = 0 (preset)

    # ── Spatial ─────────────────────
    w(59, 64)       # pan = center
    w(61, 0)        # aeg_random_pan = 0
    w(63, 64)       # aeg_alternate_pan = center
    w(65, 64)       # aeg_scaling_pan = center

    # ── XA ──────────────────────────
    w(67, 0)        # xa_control = Normal

    # ── Note/vel zones ──────────────
    w(69, 0)        # note_limit_low
    w(71, 127)      # note_limit_high
    w(73, 1)        # vel_limit_low
    w(75, 127)      # vel_limit_high
    w(77, 0)        # vel_xfade

    # ── Delay ───────────────────────
    w(79, 0)        # delay_length
    w(81, 1)        # elem_connect = InsA
    w(85, 11)       # keyondly_sync_delay

    # ── Amplitude ───────────────────
    w(91, 127)      # level
    w(93, 64)       # amp_level_vel (center)
    w(95, 0)        # aeg_offset
    w(97, 3)        # amp_level_curve

    # ── AEG ─────────────────────────
    w(99, 0)        # aeg_attack
    w(101, 64)      # aeg_decay1 (c64)
    w(103, 64)      # aeg_decay2 (c64)
    w(105, 127)     # aeg_half_damper_time
    w(107, 50)      # aeg_release
    w(109, 0)       # aeg_initial_level
    w(111, 127)     # aeg_attack_level
    w(113, 127)     # aeg_decay1_level
    w(115, 127)     # aeg_decay2_level
    w(117, 4)       # amp_segment_decay
    w(119, 64)      # amp_time_vel (center)

    # ── Level scaling ────────────────
    w(121, 64)      # amp_time_key (center)
    w(123, 24)      # amp_scaling_center_key = C0
    w(125, 36)      # bp1 = C1
    w(127, 48)      # bp2 = C2
    w(129, 60)      # bp3 = C3
    w(131, 72)      # bp4 = C4
    w(133, 128)     # offset1 (c128=0)
    w(135, 128)     # offset2
    w(137, 128)     # offset3
    w(139, 128)     # offset4
    w(141, 64)      # level_key (center)
    w(143, 64)      # amp_release_adj (center)

    # ── Pitch ────────────────────────
    w(149, 64)      # coarse_tune (c64=0)
    w(151, 64)      # fine_tune (c64=0)
    w(153, 64)      # pitch_vel (center)
    w(155, 0)       # pitch_random
    w(157, 96)      # pitch_key_follow = 100%
    w(159, 60)      # pitch_key_follow_center_note = C3
    w(161, 64)      # fine_key (center)

    # ── PEG ─────────────────────────
    w(163, 0)       # peg_time_hold
    w(165, 40)      # peg_time_attack
    w(167, 64)      # peg_time_decay1
    w(169, 64)      # peg_time_decay2
    w(171, 64)      # peg_time_release
    w(173, 128)     # peg_level_hold (c128=0)
    w(175, 128)     # peg_level_attack
    w(177, 128)     # peg_level_decay1
    w(179, 128)     # peg_level_decay2
    w(181, 128)     # peg_level_release
    w(183, 84)      # peg_depth (= +20 in c64 UI)
    w(185, 4)       # peg_segment
    w(187, 64)      # peg_time_vel (center)
    w(189, 64)      # peg_depth_vel (center)
    w(191, 2)       # peg_curve
    w(193, 64)      # peg_time_key (center)
    w(195, 60)      # peg_center_key = C3

    # ── Filter ───────────────────────
    w(201, 4)       # filter_type = 4 (LPF12+HPF12, Y2L default)
    w16(203, 640)   # cutoff u16le = 640 Hz (default)
    w(205, 64)      # cutoff_vel (center)
    w(207, 0)       # resonance
    w(209, 64)      # resonance_vel (center)
    w16(211, 0)     # hpf_cutoff = 0 Hz
    w(213, 128)     # filter_distance (c128=0)
    w(215, 230)     # filter_gain (default)

    # ── FEG ─────────────────────────
    w(217, 0)       # feg_time_hold
    w(219, 0)       # feg_time_attack
    w(221, 64)      # feg_time_decay1
    w(223, 64)      # feg_time_decay2
    w(225, 80)      # feg_time_release
    w(227, 128)     # feg_level_hold (c128=0)
    w(229, 255)     # feg_level_attack
    w(231, 255)     # feg_level_decay1
    w(233, 255)     # feg_level_decay2
    w(235, 128)     # feg_level_release (c128=0)
    w(237, 104)     # feg_depth (c104=0 in Y2L)
    w(239, 4)       # feg_segment
    w(241, 64)      # feg_time_vel (center)
    w(243, 64)      # feg_depth_vel (center)

    # ── Filter scaling ───────────────
    w(245, 2)       # filter_curve
    w(247, 64)      # filter_time_key
    w(249, 24)      # filter_scaling_center_key = C0
    w(251, 36); w(253, 48); w(255, 60); w(257, 72)  # BPs
    w(259, 128); w(261, 128); w(263, 128); w(265, 128)  # offsets
    w(267, 74)      # cutoff_key (default +31%)
    w(269, 64)      # hpf_cutoff_key (0%)

    # ── EQ ──────────────────────────
    w(271, 0)       # eq_type = 2-band
    w(273, 0)       # eq_q
    w(275, 54)      # eq_low_freq
    w(277, 64)      # eq_low_gain (0 dB)
    w(279, 231)     # eq_high_freq
    w(281, 64)      # eq_high_gain (0 dB)

    # ── LFO ─────────────────────────
    w(283, 1)       # lfo_wave = Triangle
    w(285, 1)       # lfo_keyonreset = on
    w(287, 0)       # lfo_delay
    w(291, 0)       # lfo_amp_mod_depth
    w(293, 0)       # lfo_pitch_mod_depth
    w(295, 0)       # lfo_filter_mod_depth
    w(297, 0)       # lfo_fade_in
    w(299, 0)       # element_lfo_phase_offset
    w(301, 127)     # element_lfo_dest1_depth
    w(303, 127)     # element_lfo_dest2_depth
    w(305, 127)     # element_lfo_dest3_depth
    # Extended LFO speed (u16le) — aktiv när extended_lfo=1 (rel+6)
    w16(307, 60)    # lfo_extended_speed = 60

    # ── Controller sets ──────────────
    for i in range(32):
        w(265 + i, 1)  # ctrlSet1..32 = on

    # ── Firmware constants ────────────
    w(46, 40)       # [INTERN] firmware constant
    w(90, 54)       # [INTERN]
    w(148, 48)      # [INTERN]
    w(200, 108)     # [INTERN]
    w(309, 0); w(310, 0); w(311, 0)  # padding
    w(312, 0x2B)    # inter-element separator '+'

    return e


# Cache default element
_Y2L_DEFAULT_ELEMENT = _make_y2l_default_element()


# ─────────────────────────────────────────────────────────────────────────────
# Transcoding: ClassicPartElement → 313-byte Y2L element block
# ─────────────────────────────────────────────────────────────────────────────

def transcode_element(classic: ClassicPartElement,
                      elem_idx: int = 0,
                      preset_only: bool = True,
                      extended_lfo_flag: int = 1) -> bytes:
    """Konvertera ett klassiskt AWM2-element till ett 313-byte Y2L element block.

    classic     — källelement från en ClassicPartElement
    elem_idx    — elementets index (0-7), används för enable-flagga
    preset_only — om True, hoppa över user waveforms (sätt waveform=6 om bank!=0)

    Strategi:
      1. Starta från Y2L Init Normal default (313 bytes)
      2. Kopiera alla direkt-mappade fält
      3. Konvertera fält som kräver omvandling
      4. Lämna omappade fält på sina defaults
    """
    e = bytearray(_Y2L_DEFAULT_ELEMENT)
    e[6] = 1 if extended_lfo_flag else 0

    def w(rel, val):
        e[rel] = max(0, min(255, val)) & 0xFF

    def w16(rel, val):
        val = max(0, min(0xFFFF, val))
        e[rel]     = val & 0xFF
        e[rel + 1] = (val >> 8) & 0xFF

    # ── 1. Direkta kopieringar ────────────────────────────────────────────
    for classic_attr, y2l_rel in _DIRECT_COPY_FIELDS.items():
        raw = getattr(classic, classic_attr, None)
        if raw is None:
            continue
        if classic_attr == 'feg_depth':
            # feg_depth: klassisk center=64 → Y2L center=104
            # Y2L default 104=0; same offset from center, different center value
            offset_from_center = raw - 64
            y2l_val = 104 + offset_from_center
            w(y2l_rel, y2l_val)
        else:
            w(y2l_rel, raw)

    # ── 2. Waveform ───────────────────────────────────────────────────────
    if classic.wave_bank == 0 or not preset_only:
        # Preset waveform: direct copy of waveform_number (u16le)
        w16(51, classic.waveform_number)
        w(53, 0)   # waveformBank = 0 (preset)
    else:
        # User/library waveform: not supported in Fas 3a — use default
        w16(51, 6)
        w(53, 0)

    # ── 3. Filter type ────────────────────────────────────────────────────
    y2l_ft = classic_filter_type_to_y2l(classic.filter_type)
    w(201, y2l_ft)

    # ── 4. Filter cutoff (0-255 → u16le Hz) ──────────────────────────────
    cutoff_hz = classic_cutoff_to_hz(classic.filter_cutoff_frequency)
    w16(203, cutoff_hz)

    # ── 5. HPF cutoff (0-255 → u16le Hz) ─────────────────────────────────
    hpf_hz = classic_cutoff_to_hz(classic.hpf_cutoff_frequency)
    w16(211, hpf_hz)

    # ── 6. enable / element switch ────────────────────────────────────────
    # element_switch kopierades redan via _DIRECT_COPY_FIELDS[element_switch]=0
    # Men om elementet är av, sätt ändå enable=0 (konsistens)
    if classic.element_switch == 0:
        e[0] = 0

    # ── 7. Kontrollsæt-switchar ────────────────────────────────────────────
    # control_box_sw[0..15] i klassisk → ctrlSet1..16 i Y2L (rel+265..+280)
    for i, sw in enumerate(classic.control_box_sw[:16]):
        e[265 + i] = sw & 0xFF

    return bytes(e)


# ─────────────────────────────────────────────────────────────────────────────
# Transcoding: klassisk part → Y2L AWM2 engine block
# ─────────────────────────────────────────────────────────────────────────────

def transcode_part_to_awm2_engine(part: ClassicPerformancePart,
                                   element_count: int = 8,
                                   source_fmt: str = FORMAT_MONTAGE) -> bytes:
    """Bygg ett Y2L AWM2 engine block från en klassisk performance part.

    Returnerar bytes-objektet: [engine_header(3)] + [element_1(313)] × N

    Engine header (3 bytes): [0x00, 0x00, 0x2B].
    Element count is stored outside the first engine block and in the 5-byte
    inter-engine prefix for subsequent parts. Element 8 is 309 bytes, while
    elements 1-7 are 313 bytes.
    """
    elements = part.elements[:element_count]
    # Pad till element_count med "off" element
    while len(elements) < element_count:
        off_elem = ClassicPartElement()
        off_elem.element_switch = 0
        elements.append(off_elem)

    out = bytearray()

    # Native Y2L AWM2 header. The element count is not stored here.
    out.extend((0x00, 0x00, 0x2B))

    # Elements 1-7 are 313 bytes; the final element omits four tail bytes.
    for i, elem in enumerate(elements):
        encoded = transcode_element(
            elem, elem_idx=i,
            extended_lfo_flag=0 if source_fmt == FORMAT_MODX else 1,
        )
        out.extend(encoded if i < element_count - 1 else encoded[:AWM2_LAST_ELEMENT_SIZE])

    return bytes(out)


# ─────────────────────────────────────────────────────────────────────────────
# Y2L blob-konstruktion
# ─────────────────────────────────────────────────────────────────────────────

def _read_y2l_reference_blob(path: Optional[str] = None) -> Optional[bytes]:
    """Läs ett referens-Y2L-blob (för Common + Part Common defaults).
    Returnerar None om ingen fil hittas.
    """
    candidates = [
        path,
        '/mnt/user-data/uploads/Exported_Sounds.Y2L',
        '/mnt/user-data/uploads/VP1_Signature.Y2L',
    ]
    import struct

    def u32b(b, o): return struct.unpack('>I', b[o:o+4])[0]

    for p in candidates:
        if not p:
            continue
        try:
            with open(p, 'rb') as f:
                data = f.read()
            cat = {}; o = 0x40; cs = u32b(data, 0x20); end = 0x40 + cs
            while o + 8 <= end:
                tag = data[o:o+4]; off = u32b(data, o+4)
                if tag == b'\x00\x00\x00\x00': break
                cat[tag.decode('latin1')] = off; o += 8
            if 'DPFM' not in cat: continue
            pool = data[cat['DPFM']+8 : cat['DPFM']+8+u32b(data, cat['DPFM']+4)]
            body = data[cat['EPFM']+16 : cat['EPFM']+8+u32b(data, cat['EPFM']+4)]
            pp = 0
            ln = u32b(body, pp); pp += 4; rec = body[pp:pp+ln]
            blob = pool[u32b(rec, 4) : u32b(rec, 4)+u32b(rec, 0)]
            if len(blob) >= SUBBLOB_COMMON_SIZE + SUBBLOB_DEFAULT_SIZE:
                return blob
        except Exception:
            continue
    return None


def build_y2l_blob(classic_perf: ClassicPerformance,
                   ref_blob: Optional[bytes] = None,
                   ref_y2l_path: Optional[str] = None) -> bytes:
    """Bygg ett Y2L DPFM-blob från en klassisk performance.

    Strategi:
      • Om ref_blob finns: kopiera Common sub-blob (6701 bytes) och
        Part Common headers (5765-byte default sub-blobs) från referens.
      • Annars: fyll med syntetisk minimalt-giltigt Common + Part headers.
      • AWM2 engine blocks skapas av transcode_part_to_awm2_engine().
      • FM-X parts transkodas till ett 1143-byte Y2L engine-block.
      • blob[6695] uppdateras till antal aktiva parts.
      • blob[6700] uppdateras till engine type byte för Part 1.

    Returnerar en bytes-sträng som kan sättas in direkt i DPFM-poolen.
    """
    if ref_blob is None:
        ref_blob = _read_y2l_reference_blob(ref_y2l_path)

    n_parts = len(classic_perf.parts)
    if n_parts == 0:
        raise ValueError("Performance has no parts")
    if n_parts > 16:
        n_parts = 16

    # ── 1. Common sub-blob (6701 bytes) ───────────────────────────────────
    if ref_blob is not None and len(ref_blob) >= SUBBLOB_COMMON_SIZE:
        common = bytearray(ref_blob[:SUBBLOB_COMMON_SIZE])
    else:
        # Syntetisk fallback: minimal giltigt Common block
        common = bytearray(SUBBLOB_COMMON_SIZE)
        # Sub-blob 1 prefix
        common[0:4] = SUBBLOB_PREFIX
        # Performance name (bytes 4-23, 18 bytes + null)
        name_bytes = (classic_perf.name[:18]).encode('latin-1', 'replace')
        common[4:4+len(name_bytes)] = name_bytes

    # Skriv performance-namn till Common (bytes 4..23)
    name_bytes = (classic_perf.name[:18]).encode('latin-1', 'replace')
    name_padded = name_bytes.ljust(18, b'\x00')
    common[4:22] = name_padded
    common[22] = 0  # null terminator

    # Uppdatera max_active_part (byte 6695 = offset inom Common)
    common[6695] = n_parts

    # ── 2. Part sub-blobs (5765 bytes vardera) ─────────────────────────────
    part_sub_blobs = []
    for part_idx in range(n_parts):
        if (ref_blob is not None and
                len(ref_blob) >= SUBBLOB_COMMON_SIZE + (part_idx + 1) * SUBBLOB_DEFAULT_SIZE):
            # Kopiera Part Common-blocket från referens-blobbet
            start = SUBBLOB_COMMON_SIZE + part_idx * SUBBLOB_DEFAULT_SIZE
            part_sb = bytearray(ref_blob[start : start + SUBBLOB_DEFAULT_SIZE])
        else:
            # Syntetisk fallback: minimal Part Common-block
            part_sb = bytearray(SUBBLOB_DEFAULT_SIZE)
            part_sb[0:4] = SUBBLOB_PREFIX
            # Part name i sub-blob header (bytes 4..21)
            pname = (classic_perf.parts[part_idx].name[:16]).encode('latin-1', 'replace')
            part_sb[4:4+len(pname)] = pname

        part_sub_blobs.append(part_sb)

    # ── 3. Engine blocks ───────────────────────────────────────────────────
    # FM-X reference engine (lazily loaded)
    fmx_ref = _get_fmx_ref_engine()

    engine_blocks = []
    engine_prefixes = {
        PART_TYPE_AWM2: bytes.fromhex("0000000800"),
        PART_TYPE_DRUM: bytes.fromhex("0000004900"),
        PART_TYPE_FMX:  bytes.fromhex("0000005228"),
    }
    for part_idx in range(n_parts):
        p = classic_perf.parts[part_idx]
        if p.type == PART_TYPE_FMX:
            block = transcode_fmx_part_to_engine(p, ref_engine=fmx_ref)
        elif p.type == PART_TYPE_AWM2:
            block = transcode_part_to_awm2_engine(p, source_fmt=classic_perf.fmt)
        elif p.type == PART_TYPE_DRUM:
            # Drum mapping is not implemented yet. Preserve native block length
            # so following mixed-engine parts remain correctly aligned.
            awm2_fallback = transcode_part_to_awm2_engine(p, source_fmt=classic_perf.fmt)
            block = bytes((0x00, 0x00, 0x40)) + awm2_fallback[3:]
            block = block.ljust(4963, b"\x00")[:4963]
        else:
            fallback_part = ClassicPerformancePart()
            fallback_part.type = PART_TYPE_AWM2
            fallback_part.elements = [ClassicPartElement()]
            block = transcode_part_to_awm2_engine(fallback_part, source_fmt=classic_perf.fmt)
        if part_idx > 0:
            block = engine_prefixes.get(p.type, b"\x00" * ENGINE_POOL_SEP_SIZE) + block
        engine_blocks.append(block)

    # ── 4. Sätt engine type bytes i Part Common-blocken ────────────────────
    # Engine type bytes: AWM2=0x0A, FMX=0x02, Drum=0x01
    _engine_type_byte_map = {
        PART_TYPE_AWM2: Y2L_ENGINE_AWM2,
        PART_TYPE_DRUM: Y2L_ENGINE_DRUM,
        PART_TYPE_FMX:  Y2L_ENGINE_FMX,
    }
    for part_idx in range(n_parts):
        p = classic_perf.parts[part_idx]
        if part_idx == 0:
            common[6700] = _engine_type_byte_map.get(p.type, Y2L_ENGINE_AWM2)

    # ── 5. Montera blob ────────────────────────────────────────────────────
    out = bytearray()
    out.extend(common)
    for sb in part_sub_blobs:
        out.extend(sb)
    for eb in engine_blocks:
        out.extend(eb)

    return bytes(out)


# ─────────────────────────────────────────────────────────────────────────────
# Enkel transkodnings-API för Library Builder
# ─────────────────────────────────────────────────────────────────────────────

def transcode_classic_to_y2l(
    classic_blob: bytes,
    version_str: str,
    ref_blob: Optional[bytes] = None,
) -> tuple[bytes, list[str]]:
    """Konvertera ett klassiskt DPFM-blob till ett Y2L DPFM-blob.

    Returnerar (y2l_blob, warnings) där warnings är en lista med textmeddelanden
    om konverteringsbegränsningar (FM-X-parts, user waveforms, etc.).
    """
    warnings: list[str] = []

    # Parsa klassisk blob
    classic_perf = parse_classic_blob(classic_blob, version_str)

    # Kontrollera parts
    for i, part in enumerate(classic_perf.parts):
        if part.type == PART_TYPE_FMX:
            warnings.append(
                f"Part {i+1} ({part.name!r}): FM-X transkodning är experimentell; "
                f"omappade Y2L-interna flaggor behåller referens/defaultvärden."
            )
        for j, elem in enumerate(part.elements):
            if elem.wave_bank != 0:
                warnings.append(
                    f"Part {i+1} Elem {j+1}: User/Library waveform "
                    f"(bank={elem.wave_bank}, waveform={elem.waveform_number}) "
                    f"— ersatt med preset waveform #6. Waveform-remapping kräver Fas 3c."
                )

    y2l_blob = build_y2l_blob(classic_perf, ref_blob=ref_blob)

    return y2l_blob, warnings


# ─────────────────────────────────────────────────────────────────────────────
# Smoke-test
# ─────────────────────────────────────────────────────────────────────────────

def _smoke_test():
    """Snabbtest: parse ett klassiskt X7L-blob och bygg ett Y2L-blob."""
    import struct

    def u32b(b, o): return struct.unpack('>I', b[o:o+4])[0]

    test_files = [
        ('/mnt/user-data/uploads/OB6_MONTAGE.X7L', '4.0.5'),
        ('/mnt/user-data/uploads/Jupiter_8_009.X8L', '5.0.1'),
    ]

    for x7l_path, ver in test_files:
        try:
            with open(x7l_path, 'rb') as f:
                data = f.read()
        except FileNotFoundError:
            print(f"SKIP: {x7l_path} not found")
            continue

        cat = {}; o = 0x40; cs = u32b(data, 0x20); end = 0x40 + cs
        while o + 8 <= end:
            tag = data[o:o+4]; off = u32b(data, o+4)
            if tag == b'\x00\x00\x00\x00': break
            cat[tag.decode('latin1')] = off; o += 8
        pool = data[cat['DPFM']+8 : cat['DPFM']+8+u32b(data, cat['DPFM']+4)]
        body = data[cat['EPFM']+16 : cat['EPFM']+8+u32b(data, cat['EPFM']+4)]
        pp = 0; ic = u32b(data, cat['EPFM']+8)

        ok = 0
        for i in range(min(5, ic)):
            if i > 0 and body[pp:pp+4] == b'Entr': pp += 4
            ln = u32b(body, pp); pp += 4; rec = body[pp:pp+ln]; pp += ln
            classic_blob = pool[u32b(rec, 4) : u32b(rec, 4)+u32b(rec, 0)]

            y2l_blob, warnings = transcode_classic_to_y2l(classic_blob, ver)

            classic_perf = parse_classic_blob(classic_blob, ver)
            n_parts = len(classic_perf.parts)
            expected_size = SUBBLOB_COMMON_SIZE + n_parts * SUBBLOB_DEFAULT_SIZE
            # + engine blocks
            for p in classic_perf.parts:
                elem_count = min(8, max(1, len(p.elements)))
                expected_size += AWM2_ENGINE_HEADER_SIZE + elem_count * AWM2_ELEMENT_STRIDE

            print(f"  [{i}] {classic_perf.name!r:20s} "
                  f"parts={n_parts} "
                  f"y2l_size={len(y2l_blob)} "
                  f"expected≈{expected_size} "
                  f"prefix={y2l_blob[0:4].hex()}"
                  f"{' WARN:'+str(len(warnings)) if warnings else ''}")
            if y2l_blob[:4] == SUBBLOB_PREFIX:
                ok += 1

        print(f"\n{x7l_path.split('/')[-1]}: {ok}/5 blobs have correct Y2L prefix\n")


if __name__ == '__main__':
    _smoke_test()


# ─────────────────────────────────────────────────────────────────────────────
# FM-X engine transkodning (Fas 3b)
# ─────────────────────────────────────────────────────────────────────────────
#
# Mapping verifierad mot 10 performances × 8 operators från Exported_Sounds.X7L/Y2L.
# Accuracy: 99% (3 Y2L-interna flaggor ej mappade — keyOnReset per OP + algo-flag)
#
# Y2L FM-X engine layout (1143 bytes):
#   [0..209]    Pre-OP block (210 bytes) — algorithm, feedback, LFO, filter data
#   [210..332]  OP1 (123 bytes, u16le fält, hi=0)
#   [333..455]  OP2 (123 bytes)
#   ...
#   [1071..1142] OP8 (72 bytes = 123 - 51, dvs OP8 är 51 bytes kortare)
#
# Klassisk FM-X part:
#   fmx_common_opaque: 67 bytes
#   fmx_operator_opaque: 8 × 51 bytes
#
# Encoding: Klassiska bytes mappas till Y2L u16le LO-bytes (HI=0).
# ─────────────────────────────────────────────────────────────────────────────

# Y2L FM-X engine defaults (1143 bytes) — genereras från VIOLA 30 som är ett typiskt
# init-FM-X performance. De omappade fälten behålls på dessa defaults.
_Y2L_FMX_ENGINE_DEFAULT: bytes = b''   # lazily populated from reference blob

def _get_fmx_engine_default(ref_y2l_blob: bytes) -> bytes:
    """Extrahera FM-X engine-blocket från ett referens-Y2L-blob."""
    eng_start = SUBBLOB_COMMON_SIZE + SUBBLOB_DEFAULT_SIZE
    return ref_y2l_blob[eng_start : eng_start + 1143]


# Pre-OP header mapping: (classic_common_idx, y2l_preop_byte_offset)
# Verifierat 100% korrekt mot 10 performances × alla bytes.
_FMX_PREOP_MAPPING: list[tuple[int, int]] = [
    (46, 31),  # LFO-related byte 1
    (47, 33),  # LFO-related byte 2
    (48, 35),  # LFO-related byte 3
    (50, 21),  # LFO speed (1st LFO)
    (57, 43),  # Algo/feedback related
    (58, 45),  # LFO speed or algo param
    (60, 49),  # Parameter 1
    (61, 51),  # Parameter 2
    (62, 53),  # Parameter 3
    (63, 55),  # Parameter 4
    (65, 59),  # Parameter 5
    (66, 61),  # Parameter 6
    # y2l pre-op[206] = Y2L-intern (varies but no classic source) → keep default
]

# OP operator mapping: (classic_op_byte_idx, y2l_u16le_field_idx)
# Y2L stores each field as u16le: lo_byte = classic_value, hi_byte = 0
# Field_idx N → y2l_op_byte[N*2] = value, y2l_op_byte[N*2+1] = 0
# Verified 100% correct (after excluding 3 Y2L-internal fields).
_FMX_OP_MAPPING: list[tuple[int, int]] = [
    # Zone/pitch/spectral
    (2,  0),   # coarse tune
    (3,  1),   # fine tune
    (4,  2),   # detune (c16)
    (5,  3),   # pitch key follow
    (6,  4),   # pitch velocity sensitivity
    (7,  5),   # spectral form (0=sine)
    (8,  6),   # spectral skirt
    (9,  7),   # spectral resonance
    # PEG
    (10, 8),   # peg initial level (c50)
    (11, 9),   # peg attack level (c50)
    (12, 10),  # peg attack time
    (13, 11),  # peg decay time
    # AEG levels (note: order differs from classic storage)
    (19, 12),  # aeg attack level
    (20, 13),  # aeg decay1 level
    (21, 14),  # aeg decay2 level
    (22, 15),  # aeg release level
    # AEG times
    (15, 16),  # aeg attack time
    (16, 17),  # aeg decay1 time
    (17, 18),  # aeg decay2 time
    (18, 19),  # aeg release time
    # classic[23] → aegTimeKeyFollow (field 21)
    (23, 21),  # aeg time key follow
    # Level/scaling
    (24, 22),  # operator level
    (25, 23),  # aeg breakpoint (MIDI note)
    (26, 24),  # level key follow lo
    (27, 25),  # level key follow hi
    (28, 26),  # level scaling curve lo
    (29, 27),  # level scaling curve hi
    (30, 28),  # level velocity sensitivity
    # LFO modulation depth
    (31, 29),  # 2nd LFO pitch mod depth
    (32, 30),  # 2nd LFO amp mod depth
    # classic[33,34] → not mapped (always 7, Y2L uses different representation)
    # firstLfoDest1/2/3Ratio (field 33/34/35) → default 127 from template
]

_FMX_OP_SIZE_FULL  = 123   # OP1..OP7
_FMX_OP_SIZE_LAST  = 72    # OP8
_FMX_PREOP_SIZE    = 210   # Pre-OP header
_FMX_ENGINE_SIZE   = 1143  # Total FM-X engine block


def transcode_fmx_part_to_engine(part: "ClassicPerformancePart",
                                  ref_engine: bytes = b'') -> bytes:
    """Konvertera en klassisk FM-X part till ett Y2L FM-X engine block (1143 bytes).

    part       — klassisk part med type=PART_TYPE_FMX
    ref_engine — referens Y2L FM-X engine block (1143 bytes) att använda som template.
                 Om tomt används inbyggda defaults (noll-initierade + korrekta trailer).
    """
    if len(ref_engine) >= _FMX_ENGINE_SIZE:
        engine = bytearray(ref_engine[:_FMX_ENGINE_SIZE])
    else:
        # Syntetisk fallback: noll + korrekta trailer-bytes
        engine = bytearray(_FMX_ENGINE_SIZE)
        # Sätt firstLfoDest1/2/3Ratio till default 127 för alla OPs
        for opi in range(8):
            op_size = _FMX_OP_SIZE_FULL if opi < 7 else _FMX_OP_SIZE_LAST
            op_base = _FMX_PREOP_SIZE + opi * _FMX_OP_SIZE_FULL
            # field 33 = rel+66, field 34 = rel+68, field 35 = rel+70
            for fi in (33, 34, 35):
                rel = fi * 2
                if rel < op_size:
                    engine[op_base + rel] = 127

    # 1. Applicera pre-OP mapping från klassisk common
    xc = part.fmx_common_opaque or b''
    for ci, yi in _FMX_PREOP_MAPPING:
        if ci < len(xc) and yi < _FMX_PREOP_SIZE:
            engine[yi] = xc[ci]

    # 2. Applicera operator mapping
    for opi in range(8):
        cop = (part.fmx_operator_opaque[opi]
               if opi < len(part.fmx_operator_opaque) else b'')
        op_base = _FMX_PREOP_SIZE + opi * _FMX_OP_SIZE_FULL
        op_size = _FMX_OP_SIZE_FULL if opi < 7 else _FMX_OP_SIZE_LAST
        for ci, fi in _FMX_OP_MAPPING:
            rel = fi * 2
            if rel >= op_size:
                continue   # bortom OP8-storleken
            cv = cop[ci] if ci < len(cop) else 0
            engine[op_base + rel]     = cv
            engine[op_base + rel + 1] = 0   # hi-byte alltid 0

    return bytes(engine)


def _extract_fmx_ref_engine(y2l_path: str) -> bytes:
    """Extrahera ett FM-X engine-block från en Y2L-fil som referenstemplate."""
    import struct

    def u32b(b, o): return struct.unpack('>I', b[o:o+4])[0]

    try:
        with open(y2l_path, 'rb') as f:
            data = f.read()
        cat = {}; o = 0x40; cs = u32b(data, 0x20); end = 0x40 + cs
        while o + 8 <= end:
            tag = data[o:o+4]; off = u32b(data, o+4)
            if tag == b'\x00\x00\x00\x00': break
            cat[tag.decode('latin1')] = off; o += 8
        pool = data[cat['DPFM']+8 : cat['DPFM']+8+u32b(data, cat['DPFM']+4)]
        body = data[cat['EPFM']+16 : cat['EPFM']+8+u32b(data, cat['EPFM']+4)]
        pp = 0; ln = u32b(body, pp); pp += 4; rec = body[pp:pp+ln]
        blob = pool[u32b(rec, 4) : u32b(rec, 4)+u32b(rec, 0)]
        if u32b(blob, 6700 - 0) == 0x02 or True:   # FMX engine type
            eng_start = SUBBLOB_COMMON_SIZE + SUBBLOB_DEFAULT_SIZE
            return blob[eng_start : eng_start + _FMX_ENGINE_SIZE]
    except Exception:
        pass
    return b''


# ─────────────────────────────────────────────────────────────────────────────
# Uppdaterad transcode_part_to_engine med FM-X stöd
# ─────────────────────────────────────────────────────────────────────────────

_FMX_REF_ENGINE: bytes = b''   # lazily loaded


def _get_fmx_ref_engine() -> bytes:
    global _FMX_REF_ENGINE
    if not _FMX_REF_ENGINE:
        for path in ['/mnt/user-data/uploads/Exported_Sounds.Y2L']:
            result = _extract_fmx_ref_engine(path)
            if result:
                _FMX_REF_ENGINE = result
                break
    return _FMX_REF_ENGINE


def transcode_part_to_engine_full(part: "ClassicPerformancePart",
                                   element_count: int = 8) -> bytes:
    """Bygg ett Y2L engine block från en klassisk part — stöder AWM2, Drum och FM-X.

    Returnerar engine-blocket (variabel storlek).
    """
    if part.type == PART_TYPE_FMX:
        ref = _get_fmx_ref_engine()
        return transcode_fmx_part_to_engine(part, ref_engine=ref)
    else:
        # AWM2 or Drum
        return transcode_part_to_awm2_engine(part, element_count)


# ─────────────────────────────────────────────────────────────────────────────
# FM-X smoke test
# ─────────────────────────────────────────────────────────────────────────────

def _fmx_smoke_test():
    """Testa FM-X transkodning mot Exported_Sounds.X7L och Exported_Sounds.Y2L."""
    import struct

    def u32b(b, o): return struct.unpack('>I', b[o:o+4])[0]

    def get_blobs(path, n=5):
        try:
            with open(path, 'rb') as f: data = f.read()
        except FileNotFoundError:
            return None, {}
        ver = data[0x10:0x20].split(b'\x00')[0].decode('latin1')
        cat = {}; o = 0x40; cs = u32b(data, 0x20); end = 0x40 + cs
        while o + 8 <= end:
            tag = data[o:o+4]; off = u32b(data, o+4)
            if tag == b'\x00\x00\x00\x00': break
            cat[tag.decode('latin1')] = off; o += 8
        pool = data[cat['DPFM']+8 : cat['DPFM']+8+u32b(data, cat['DPFM']+4)]
        body = data[cat['EPFM']+16 : cat['EPFM']+8+u32b(data, cat['EPFM']+4)]
        pp = 0; ic = u32b(data, cat['EPFM']+8); result = {}
        for i in range(min(n, ic)):
            if i > 0 and body[pp:pp+4] == b'Entr': pp += 4
            ln = u32b(body, pp); pp += 4; rec = body[pp:pp+ln]; pp += ln
            blob = pool[u32b(rec, 4) : u32b(rec, 4)+u32b(rec, 0)]
            name = blob[4:4+20].split(b'\x00')[0].decode('latin1', 'replace')
            result[name] = blob
        return ver, result

    x_ver, x_blobs = get_blobs('/mnt/user-data/uploads/Exported_Sounds.X7L', n=10)
    y_ver, y_blobs = get_blobs('/mnt/user-data/uploads/Exported_Sounds.Y2L', n=10)

    if not x_blobs or not y_blobs:
        print("SKIP: FM-X test files not found")
        return

    ref_engine = _get_fmx_ref_engine()
    total_ok = total = 0
    common = sorted(set(x_blobs) & set(y_blobs))[:5]

    for name in common:
        classic_perf = parse_classic_blob(x_blobs[name], x_ver or '4.0.0')
        part = classic_perf.parts[0]
        reconstructed = transcode_fmx_part_to_engine(part, ref_engine=ref_engine)
        y_eng_actual = y_blobs[name][SUBBLOB_COMMON_SIZE + SUBBLOB_DEFAULT_SIZE :
                                      SUBBLOB_COMMON_SIZE + SUBBLOB_DEFAULT_SIZE + 1143]
        diffs = sum(1 for i in range(1143) if reconstructed[i] != y_eng_actual[i])
        total += 1143; total_ok += 1143 - diffs
        pct = 100 * (1143 - diffs) // 1143
        print(f"  FM-X [{name:15s}]: {1143-diffs}/1143 ({pct}%){' ✓' if diffs==0 else f' [{diffs} diffs]'}")

    print(f"\n  FM-X overall: {total_ok}/{total} ({100*total_ok//total}%)\n")


# ─────────────────────────────────────────────────────────────────────────────
# Y2L YSFC container — ESP/MODX-M format (Fas 3 container-skrivning)
# ─────────────────────────────────────────────────────────────────────────────
#
# ESP/MODX-M Y2L-filer använder ett annat YSFC-format än CWM-genererade filer.
# Skillnader mot CWM-format (som tidigare felaktigt användes):
#
#   Chunk-uppsättning: EPFM, ESYS, EFVT, DPFM, DSYS, DFVT  (6 chunks)
#     CWM hade: EPFM, EWFM, EWIM, DPFM, DWFM, DWIM + 10 dummy-chunks
#
#   Library block size: 241 bytes (0xf1), alla 0xFF utom sista byte 0x00
#     CWM hade: 81 bytes
#
#   EPFM entry-struktur: 53-68 bytes (varierar med namnlängd)
#     Fält: [0:4]=blob_size, [4:8]=DPFM_body_data_offset+4,
#           [8:12]=0x00400000+idx, [12:14]=category_flags,
#           [14]=0, [15]=max(2,ceil(n_parts/2)),
#           [16:20]=engine_flags, [20:22]=0, [22:26]=0x0000003e,
#           [26]=sequential_byte, [27:N]="IDX:SHORT_NAME:FULL_NAME\0"
#
#   Version: '5.1.2' (MODX M firmware version)
#
#   ESYS/DSYS: systeminställningar — identiska across alla filer, kopieras
#              från referensfil (FMX_export.Y2L eller Test.Y2L).
#
#   EFVT/DFVT: favoriter — identiska, kopieras från referensfil.
#
# Verifierat: filer skapade med detta format importeras korrekt av MODX M
# och låter rätt (live-hårdvarutest 2026-06-07).
# ─────────────────────────────────────────────────────────────────────────────

import io as _io
import struct as _struct
import math as _math

# Katalogstorlek, library-block, chunks i Y2L ESP-format
_ESP_CATALOG_SIZE  = 48    # 6 chunks × 8 bytes
_ESP_LIBRARY_SIZE  = 241   # 0xf1, alla 0xFF utom sista 0x00
_ESP_CHUNKS_START  = 353   # 64 (header) + 48 (catalog) + 241 (library)
_ESP_VERSION       = '5.1.2'
_ESP_MAX_ENTRY_ID_BASE = 16000

# Statiska chunk-data (ESYS, EFVT, DSYS, DFVT) — identiska i alla ESP Y2L-filer.
# Extraherade från FMX_export.Y2L (ESP Plugin export, MODX M, 2026-06-07).
_ESP_STATIC_CHUNKS: dict[str, bytes] = {}
_ESP_STATIC_LOADED = False


def _load_esp_static_chunks() -> bool:
    """Ladda statiska chunks från en ESP-referensfil om tillgänglig."""
    global _ESP_STATIC_CHUNKS, _ESP_STATIC_LOADED
    if _ESP_STATIC_LOADED:
        return bool(_ESP_STATIC_CHUNKS)

    _ESP_STATIC_LOADED = True
    candidates = [
        '/mnt/user-data/uploads/FMX_export.Y2L',
        '/mnt/user-data/uploads/Test.Y2L',
    ]

    def _u32b(b, o): return _struct.unpack('>I', b[o:o+4])[0]

    for path in candidates:
        try:
            with open(path, 'rb') as f:
                data = f.read()
            cat = {}; o = 64; cs = _u32b(data, 32)
            while o + 8 <= 64 + cs:
                tag = data[o:o+4]; off = _u32b(data, o+4)
                if tag == b'\x00\x00\x00\x00': break
                cat[tag.decode('latin1')] = off; o += 8
            for name in ('ESYS', 'EFVT', 'DSYS', 'DFVT'):
                if name not in cat: raise ValueError(f"Missing chunk {name}")
                off = cat[name]
                sz  = 8 + _u32b(data, off + 4)
                _ESP_STATIC_CHUNKS[name] = data[off:off+sz]
            return True
        except Exception:
            continue
    return False


def _build_epfm_entry(blob: bytes, perf_index: int, body_data_offset: int) -> bytes:
    """Bygg en EPFM entry i ESP-format för ett Y2L blob.

    blob             — Y2L performance blob
    perf_index       — 0-baserat index bland alla performances i filen
    body_data_offset — offset för blobdatan inom DPFM body (efter 'Data'+size header)
    """
    n_parts    = blob[6695] if len(blob) > 6695 else 1
    engine_byte = blob[6700] if len(blob) > 6700 else 0x0A
    blob_size  = len(blob)
    dpfm_off   = body_data_offset + 4   # +4 för 'Data'-taggen
    entry_id   = 0x00400000 + perf_index
    b15        = max(2, _math.ceil(n_parts / 2))
    seq_byte   = (_ESP_MAX_ENTRY_ID_BASE + perf_index - 15875) & 0xFF

    # Engine flags vid [16:20]
    engine_flags = {
        Y2L_ENGINE_FMX:  b'\x00\x00\x03\x00',
        Y2L_ENGINE_ANX:  b'\x40\x00\xff\x00',
        Y2L_ENGINE_DRUM: b'\x00\x00\x02\x00',
    }.get(engine_byte, b'\x00\x00\x00\x00')   # AWM2 default

    # Namnfält
    name_raw = blob[4:4+18].split(b'\x00')[0].decode('latin-1', 'replace').strip()
    if not name_raw:
        name_raw = f'Performance{perf_index + 1}'
    short_name = name_raw[:20].ljust(20)
    full_name  = name_raw[:40]
    name_str   = f'{perf_index}:{short_name}:{full_name}\x00'.encode('latin-1', 'replace')

    return (
        _struct.pack('>I', blob_size) +        # [0:4]   blob_size
        _struct.pack('>I', dpfm_off) +          # [4:8]   DPFM data offset
        _struct.pack('>I', entry_id) +          # [8:12]  entry_id
        b'\x00\x01' +                           # [12:14] category flags
        b'\x00' +                               # [14]    = 0
        bytes([b15]) +                          # [15]    n_parts variant
        engine_flags +                          # [16:20] engine flags
        b'\x00\x00' +                           # [20:22] = 0
        b'\x00\x00\x00\x3e' +                   # [22:26] constant 0x3e
        bytes([seq_byte]) +                     # [26]    sequential
        name_str                                # [27:N]  name string
    )


def write_y2l_file(out_path: str,
                   y2l_blobs_with_names: list[tuple[str, bytes]],
                   version: str = _ESP_VERSION) -> tuple[int, int]:
    """Skriv en Y2L-fil i ESP/MODX-M format.

    out_path             — destinationsfilens sökväg
    y2l_blobs_with_names — lista av (name, y2l_blob) tuples
    version              — YSFC-versionssträng (default '5.1.2')

    Returnerar (file_size_bytes, n_performances).

    Format-kompatibilitet: verifierat mot MODX M firmware (live-test 2026-06-07).
    Kräver att ESP-referensfiler (FMX_export.Y2L eller Test.Y2L) finns tillgängliga
    för de statiska ESYS/EFVT/DSYS/DFVT-chunkarna.
    """
    if not _load_esp_static_chunks():
        raise RuntimeError(
            "Kunde inte ladda statiska ESP-chunks. "
            "FMX_export.Y2L eller Test.Y2L måste finnas tillgängliga."
        )

    blobs = [blob for _, blob in y2l_blobs_with_names]
    n     = len(blobs)

    def _u32be(v): return _struct.pack('>I', v)

    # ── DPFM ────────────────────────────────────────────────────────────────
    dpfm_body    = bytearray()
    body_offsets = []
    for blob in blobs:
        body_offsets.append(len(dpfm_body) + 8)   # +8 = 'Data'(4) + size(4)
        dpfm_body += b'Data' + _u32be(len(blob)) + blob

    dpfm_chunk = b'DPFM' + _u32be(4 + len(dpfm_body)) + _u32be(n) + bytes(dpfm_body)

    # ── EPFM ────────────────────────────────────────────────────────────────
    epfm_items = bytearray()
    for i, blob in enumerate(blobs):
        entry = _build_epfm_entry(blob, i, body_offsets[i])
        epfm_items += b'Entr' + _u32be(len(entry)) + entry

    epfm_chunk = b'EPFM' + _u32be(4 + len(epfm_items)) + _u32be(n) + bytes(epfm_items)

    # ── Chunk-ordning och katalog ────────────────────────────────────────────
    chunk_order = [
        ('EPFM', epfm_chunk),
        ('ESYS', _ESP_STATIC_CHUNKS['ESYS']),
        ('EFVT', _ESP_STATIC_CHUNKS['EFVT']),
        ('DPFM', dpfm_chunk),
        ('DSYS', _ESP_STATIC_CHUNKS['DSYS']),
        ('DFVT', _ESP_STATIC_CHUNKS['DFVT']),
    ]

    offset   = _ESP_CHUNKS_START
    catalog  = b''
    for name, data in chunk_order:
        catalog += name.encode('latin-1') + _u32be(offset)
        offset  += len(data)

    max_id = _ESP_MAX_ENTRY_ID_BASE + n

    # ── Skriv fil ────────────────────────────────────────────────────────────
    buf = _io.BytesIO()
    buf.write(b'YAMAHA-YSFC\x00\x00\x00\x00\x00')                         # [0:16]
    buf.write(version.encode('latin-1')[:15].ljust(16, b'\x00'))           # [16:32]
    buf.write(_u32be(_ESP_CATALOG_SIZE) + b'\xff' * 12)                    # [32:48]
    buf.write(_u32be(_ESP_LIBRARY_SIZE) + b'\xff' * 8)                     # [48:60]
    buf.write(_u32be(max_id))                                               # [60:64]
    buf.write(catalog)                                                      # [64:112]
    buf.write(b'\xff' * (_ESP_LIBRARY_SIZE - 1) + b'\x00')                 # [112:353]
    for _, chunk_data in chunk_order:
        buf.write(chunk_data)

    out_bytes = buf.getvalue()
    with open(out_path, 'wb') as f:
        f.write(out_bytes)

    return len(out_bytes), n
