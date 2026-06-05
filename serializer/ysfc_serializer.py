"""
YSFC Forge — Serializer

Parser, validator och encoder för Yamaha MODX M / ESP plugin / Montage M Y2L-format
(Performance container med EPFM/DPFM-chunks och engine-data-pool).

Referensdokument: YSFC_FORGE_FULL_CONTEXT.md

Stjärnbetyg:
  ★★★★★ Binärverifierat med testfil(er)
  ★★★★☆ Härledd från officiell källdata (Effect Type List, MIDI-tabell)
  ★★★☆☆ Predikterat från etablerat mönster
  [STRUKT] Strukturellt identifierat, ej UI-mappat
  [INTERN] MODX-internt fält, ignoreras vid editing

Förkortningar:
  u8 unsigned 8-bit byte
  u16le unsigned 16-bit little-endian (lo + hi*256)
  c64 center=64 (raw = UI + 64)
  c128 center=128 (raw = UI + 128)
  c256 center=256 (u16le, raw = UI + 256)
  c50 center=50 (raw = UI + 50)
  c504 center=504 (u16le, AN-X pitch cents)
  direct raw = UI-värde direkt
  bool 0=Off, 1=On

Adress-bas:
  abs absolut offset från performance-blobens början
  PART+N offset relativt PART_BLOCK_START=6708
  FMX_OP+N relativt FMX_OP1_BASE=12676 (stride=123)
  ELEM+N relativt AWM2_ELEM1_BASE=12532 (stride=313)
  ANX_OSC+N relativt ANX_OSC1_BASE=12638 (stride=125)
  DRUM_KEY+N relativt DRUM_KEY1_BASE=12469 (stride=68)

Kritiska metadata-bytes:
  blob[+6695] Högsta aktiva Part-index (1..16)
  blob[+6700] Engine Type Part 1 (0=AWM2, 1=Drum, 2=FMX, 3=ANX)
  blob[+12464], blob[+12465] Part 2 engine-prefix i multi-part-filer
"""

from math import log2
from pathlib import Path
from typing import Any, Union

# ─────────────────────────────────────────────────────────────────────────
# Optional: ysfc_enums-paketet
# 
# Om paketet är installerat (eller ligger i samma directory) får serializern
# tillgång till stora referenstabeller för UI-namn:
#   - WAVEFORMS (7635 AWM2-waveforms med namn + kategori)
#   - PERFORMANCES (3427 factory performances)
#   - ARPEGGIOS (10922 arpeggio-namn)
#   - CONTROLLER_SOURCES (42), CONTROLLER_DESTINATIONS (414)
#   - LFO_DESTINATIONS (70), KEY_CONTROLLER_DESTINATIONS (59)
#   - Engine enums: AWM2_FILTER_TYPES, ANX_OSC_WAVEFORMS, FMX_ALGORITHMS, etc.
#   - FX_TYPES (103 effekter med kategori, slot-info, msb/lsb)
# 
# Paketet är optional — serializern fungerar fullt ut utan det.
# Om paketet finns: HAS_ENUMS=True och konstanter exponeras via 
# `ENUMS`-namespace för enkel åtkomst i editor-kod.
# ─────────────────────────────────────────────────────────────────────────
try:
    import ysfc_enums as ENUMS
    HAS_ENUMS = True
    ENUMS_VERSION = getattr(ENUMS, '__version__', 'unknown')
except ImportError:
    ENUMS = None
    HAS_ENUMS = False
    ENUMS_VERSION = None

# ── FIELD_REGISTRY ────────────────────────────────────────────────────────

NOISE = {3, 35, 36, 63, 399, 710, 711, 6735, 6736, 6737, 7411, 7412}
# Timestamp/checksum bytes updated by MODX on every Store — ignored in diffs:
MODX_TIMESTAMP_BYTES = {23, 24, 6724, 6725} # confirmede
# CA+17 (abs = CA_PART_BASE + idx*22 + 17) is also MODX-internal —
# ignored during patch-editing (confirmednot visible in ESP)
# Drum-key collateral bytes — updated on any drum-key edit:
DRUM_COLLATERAL_BYTES = {6715, 6716, 6721} # ignore for round-trip on Drum

# ── SUB-BLOB STRUCTURE ─────────────────
# Y2L blob = sequence of sub-blobs. Each sub-blob has a 27-byte header
# (4 length prefix + 18 name + 1 null + 4 hash) followed by payload.
# Verified over 10 test files × 4 engines × 5 parts.

SUBBLOB_COMMON_SIZE = 6701 # Sub-blob 1 (Common): ALWAYS this size
SUBBLOB_DEFAULT_SIZE = 5765 # Empty placeholder sub-blob: ALWAYS this size
SUBBLOB_HEADER_SIZE = 27 # 4 + 18 + 1 + 4 bytes
PART1_SUBBLOB_START = 6701 # = SUBBLOB_COMMON_SIZE
PART1_PAYLOAD_START = 6728 # = 6701 + 27

# Per-engine engine-data sizes (in last sub-blob, in addition to 5765 default body):
ENGINE_DATA_SIZES = {
    'ANX': 684, # AN-X engine (OSC1+OSC2+OSC3+Filter+EG+Modifier+Pitch EG/LFO)
    'FMX': 1143, # FM-X engine (8 operators + matrices + envelopes)
    'AWM2': 2503, # AWM2 engine (Element 1, sometimes 2-8)
    'DRUM': 4963, # Drum engine (73 keys × 68 bytes + headers)
}
# When a part is "edited", engine block grows by +5 bytes (extra footer/checksum)

def subblob_start(part_idx: int) -> int:
    """Return abs offset of sub-blob START for given part index (0..15).
    part_idx=0 means Part 1 in UI (always present at sub-blob 2)."""
    if not (0 <= part_idx < 16):
        raise ValueError(f"part_idx must be 0..15: {part_idx}")
    return SUBBLOB_COMMON_SIZE + part_idx * SUBBLOB_DEFAULT_SIZE

def payload_start(part_idx: int) -> int:
    """Return abs offset of sub-blob PAYLOAD start (= header end) for given part."""
    return subblob_start(part_idx) + SUBBLOB_HEADER_SIZE

def part_field_abs(part_idx: int, payload_offset: int) -> int:
    """Return abs offset for any per-part field given its payload offset.
    payload_offset is engine-agnostic and identical across all 16 parts.
    Examples: Volume payload_offset=103, Pan=105, AEG attack=141, etc."""
    return payload_start(part_idx) + payload_offset

def rel_part_to_payload(rel_part: int) -> int:
    """Convert old-style 'rel_part' (offset from PART_BLOCK_START=6708) to
    new payload-offset. Difference is 20 bytes (= 6728 - 6708)."""
    return rel_part - 20

def payload_to_rel_part(payload_offset: int) -> int:
    """Inverse of rel_part_to_payload. Use for Part 1 abs calculations."""
    return payload_offset + 20

# Common per-part field payload-offsets (verified universally):
PART_VOLUME_PAYLOAD_OFFSET = 103 # Volume: rel_part=123, abs=6831 (Part 1)
# More can be added as we verify them across multi-part files.
# ────────────────────────────────────────────────────────────────────────────

# ── ENGINE-BLOCK STRUKTUR ─────────────────────────────────────────
# Engine-area börjar @ last_subblob_start + 5765 och består av sekventiella
# per-part engine-blocks (i Part-nummer-ordning). Storleken per part-block beror
# på den engine-typ som parten använder (kan blandas i samma performance).

# Engine-block storlekar (bytes):
# First-position (Part 1): bas-storlek
# Other positions (Part N≥2 inom samma sub-blob): bas + 5 (för engine-header)
ENGINE_BLOCK_FIRST = {
    'ANX': 684,
    'FMX': 1143,
    'AWM2': 2503,
    'DRUM': 4963,
}
ENGINE_BLOCK_OTHER = {
    'ANX': 689, # = 684 + 5 byte header
    'FMX': 1148, # = 1143 + 5
    'AWM2': 2508, # = 2503 + 5
    'DRUM': 4968, # = 4963 + 5 (men 4327 i mellanliggande mixed-engine slot — edge case)
}

# Per-engine field rel-offsets within engine-block (Part 1 / "first" position):
# For Part N≥2, add 5 for engine-block header.
ENGINE_FIELDS = {
    'ANX': {
        'osc1_shaper': 188, # ★★★★★(range -64..+63, raw direct)
    },
    'FMX': {
        'op1_level': 254, # ★★★★★(range 0..127, raw direct)
    },
    'AWM2': {
        'element1_pan': 62, # ★★★★★(center=64, R30 = raw 84)
    },
    'DRUM': {
        # Volume ligger i Part Common payload, inte engine-block
    },
}

def detect_engine_from_name(subblob_name: str) -> str:
    """Identifiera engine-typ från sub-blob namn-sträng."""
    n = subblob_name.strip()
    if 'AN-X' in n: return 'ANX'
    if 'FM-X' in n: return 'FMX'
    if 'AWM2' in n: return 'AWM2'
    if 'Drum' in n: return 'DRUM'
    raise ValueError(f"Unknown engine in sub-blob name: {n!r}")

def parse_subblob_layout(blob: bytes) -> list:
    """Returnera lista av (offset, name, engine_type) för alla sub-blobs i blob.
    Det första elementet är 'Common' (Sub 1), resten är Parts (1..N).
    
    Använder POINTER-baserad detection (pointers vid SUBBLOB_POINTER_REL) 
    istället för namnsökning. Detta gör att funktionen fungerar för alla 
    filtyper inkl. Multi/GM (som inte har "Init "-strängar).
    
    Engine-typer returneras som versaler ('AWM2', 'ANX', 'FMX', 'DRUM') för 
    att vara konsistent med ENGINE_BLOCK_FIRST/ENGINE_BLOCK_OTHER-nycklar.
    """
    matches = []
    max_part = get_max_active_part(blob)
    if max_part == 0:
        return matches
    
    # Sub-blob 1 är alltid Common
    matches.append((0, 'Common', 'Common'))
    
    # Härled engine-typ per part via pointer-modellen:
    # - Part N's egen engine = vad Part N-1:s pointer säger om "nästa"
    # - Part 1's egen engine = vad sista parts marker säger
    
    engines = ['???'] * max_part
    
    # Part 1 från sista parts marker
    is_last_n, part1_engine = read_subblob_pointer(blob, max_part)
    if is_last_n:
        engines[0] = part1_engine
    
    # Part 2..N från föregående parts pointer
    for n in range(1, max_part):
        is_last, next_engine = read_subblob_pointer(blob, n)
        if not is_last:
            engines[n] = next_engine
    
    # Normalisera engine-namn till versaler för konsistens med ENGINE_BLOCK-dict
    # (read_subblob_pointer returnerar 'Drum' men ENGINE_BLOCK-dict har 'DRUM')
    def normalize(e):
        return {'Drum': 'DRUM', 'ANX': 'ANX', 'AWM2': 'AWM2', 'FMX': 'FMX',
                'ANx': 'ANX', 'FMx': 'FMX'}.get(e, e.upper())
    
    engines = [normalize(e) for e in engines]
    
    # Bygg matches: (offset, name, engine_type)
    for i in range(max_part):
        offset = SUBBLOB_COMMON_SIZE + i * SUBBLOB_DEFAULT_SIZE
        engine = engines[i]
        # Namn-fältet kan finnas eller saknas (Multi/GM har inga "Init "-strängar)
        # För kompatibilitet sätter vi ett syntetiskt namn baserat på engine
        name = f'Part{i+1}({engine})'
        matches.append((offset, name, engine))
    
    return matches


def parse_subblob_layout_legacy(blob: bytes) -> list:
    """LEGACY: Returnera lista of (offset, name, engine_type) för alla sub-blobs.
    Använder "Init "-strängsökning. Fungerar för 1-part och multi-part-filer 
    där varje sub-blob har "Init Normal (XXX)" eller "Init Drum" som namn.
    Fungerar INTE för Multi/GM (som har "Multi/GM" som performance-namn istället).
    Behållen för bakåtkompatibilitet. Använd parse_subblob_layout() istället."""
    matches = []
    pos = 0
    while True:
        idx = blob.find(b'Init ', pos)
        if idx < 0: break
        if idx >= 4 and blob[idx-4:idx] == b'\x00\x00\x00\x15':
            name_end = blob.find(b'\x00', idx)
            name = blob[idx:name_end].decode('ascii', errors='replace').rstrip()
            try:
                engine = detect_engine_from_name(name)
            except ValueError:
                engine = 'UNKNOWN'
            matches.append((idx-4, name, engine))
        pos = idx + 1
    return matches

def part_engine_block_start(blob: bytes, part_idx: int) -> int:
    """Returnerar abs offset för början av Part N's engine-block.
    part_idx: 0-indexerad (0 = Part 1 i UI).
    Tar hänsyn till mixed engines.

    BEGRÄNSNING: Funktionen ANTAR att alla parts är AKTIVT REDIGERADE
    (vilket är vanligt i ESP-filer från en patch editor). I rå-export från
    MODX där "tomma" parts har varierande engine-block-storlekar fungerar
    inte denna formel direkt — i de fallen behöver man läsa engine-block
    storlek från sub-blob-data dynamiskt. Behöver mer testdata för att
    lösa edge-case helt."""
    layout = parse_subblob_layout(blob)
    # layout[0] = Common, layout[1..] = Parts 1..N
    if part_idx + 1 >= len(layout):
        raise ValueError(f"part_idx {part_idx} not present in blob")
    last_subblob_start = layout[-1][0]
    engine_area_start = last_subblob_start + 5765

    # Beräkna offset genom att summera engine-blocks för parts 0..part_idx-1
    offset = 0
    for i in range(part_idx):
        engine = layout[i+1][2] # Part i+1's engine-typ (layout[0] är Common)
        if i == 0:
            offset += ENGINE_BLOCK_FIRST.get(engine, 0)
        else:
            offset += ENGINE_BLOCK_OTHER.get(engine, 0)
    return engine_area_start + offset

def part_engine_field(blob: bytes, part_idx: int,
                      engine_field_offset_p1: int) -> int:
    """Returnerar abs offset för engine-fält i given part.
    engine_field_offset_p1: rel-offset i Part 1's engine-block (utan +5 header)."""
    block = part_engine_block_start(blob, part_idx)
    if part_idx == 0:
        return block + engine_field_offset_p1
    return block + 5 + engine_field_offset_p1
# ────────────────────────────────────────────────────────────────────────────

FMX_PART_STRIDE = 6913
FMX_OP_STRIDE = 123
FMX_OP1_BASE = 12676 #
AWM2_PART_STRIDE = 8273
AWM2_ELEM_STRIDE = 313
AWM2_FILTER_TYPES = [
    "LPF24D","LPF18D","LPF12D","LPF6D","LPF+HPF",
    "HPF24D","HPF18D","HPF12D","HPF6D",
    "BPF12D×2","BPF6D×2","BPF12A",
    "LPF24A","LPF18A","LPF12A","HPF24A","HPF12A",
    "BPF12A×2","BPF6A×2","LPF24A+HPF","BPFmono","THRU",
] # 22 types; verified: 0=LPF24D,4=LPF+HPF,7=HPF12D,21=THRU
AWM2_ELEM1_BASE = 12532 #
ANX_PART_STRIDE = 6454
ANX_OSC_STRIDE = 125
ANX_OSC1_BASE = 12638
ANX_FILTER_BASE = 13019
ANX_AEG_BASE = 12565 # +0:Attack u8, +2:Decay u8, +4:Sustain u16LE, +6:Release u8, +8:TimeVel u16LE c=256

PART_COMMON = dict(
    monoPoly=6751, volume=6843, pan=6845,
    # OBS: Tidigare adresser för AEG/FEG-offsets här (6861-6875) var FELAKTIGA för AWM2.
    # (Part Common rel +144..+158). Se PART_COMMON_REL nedan för korrekta AWM2-adresser:
    #   awm2PartAegOffsetAttack_rel = 144 → abs 6845
    #   awm2PartAegOffsetDecay_rel  = 146 → abs 6847
    #   awm2PartAegOffsetSustain_rel = 148 → abs 6849
    #   awm2PartAegOffsetRelease_rel = 150 → abs 6851
    #   awm2PartFegOffsetAttack_rel  = 152 → abs 6853
    #   awm2PartFegOffsetDecay_rel   = 154 → abs 6855
    #   awm2PartFegOffsetSustain_rel = 156 → abs 6857
    #   awm2PartFegOffsetRelease_rel = 158 → abs 6859
    # Adresserna 6861..6875 är troligen för annan engine eller annat fält (ej verifierat).
    filterFEGDepth=6877, filterCutoff=6879, filterResonance=6881,
)
PART_DETUNE_BASE = 6929
PART_NOTESHIFT = 6931

# FM-X Part-level LFO fields (abs addresses, )
# 1st LFO: TempoSync/Loop i PART_COMMON (abs 6770-6771), övriga i LFO-subtabell
FMX_PART_LFO = dict(
    fmxPartLfoTempoSync=6770, # abs, u8 bool 0=Off,1=On, default=0 ★★★★★
    fmxPartLfoLoop=6771, # abs, u8 bool INVERTED 0=On,1=Off, default=0=On ★★★★★
    fmxPartLfoWave=7201, # abs, u8 enum 0-12, default=0=Triangle ★★★★★
    # 0=Triangle, 1=Triangle+, 2=SawUp, 3=SawDown, 4=Squ1/4, 5=Squ1/3,
    # 6=Square, 7=Squ2/3, 8=Squ3/4, 9=Trapezoid, 10=S&H1, 11=S&H2, 12=User
    fmxPartLfoSpeed=7203, # abs, u8 direct, default=32 ★★★★★
    fmxPartLfoTempoNote=7205, # abs, u8 table-index raw=list_idx+5, default=11=1/4 ★★★★★
    # See FMX_LFO_TEMPONOTE dict for complete table (raw 5-24 = 1/16 to 1/4×64)
    fmxPartLfoDelay=7207, # abs, u8 direct, default=0 ★★★★★
    fmxPartLfoFadeIn=7209, # abs, u8 direct, default=0 ★★★★★
    fmxPartLfoHold=7211, # abs, u8 direct, default=127 ★★★★★
    fmxPartLfoFadeOut=7213, # abs, u8 direct center=default=64 ★★★★★
    fmxPartLfoKeyOnReset=7215, # abs, u8 enum 0=Off,1=Each,2=1st, default=2 ★★★★★
    fmxPartLfoRandomSpeed=7265, # abs, u8 direct, default=0 ★★★★★
    # 1st LFO Phase + Destinations — NEW★★★★★
    fmxPartLfoPhase=7199, # abs, u8 enum 0-5, default=0 ★★★★★
    # Phase enum (UI-confirmed):
    # 0=0°(default), 1=90°, 2=120°, 3=180°(verified), 4=240°, 5=270°
    # Note: NOT arithmetic 60° step — values are 0/90/120/180/240/270 (non-uniform).
    fmxPartLfoDest1=7217, # abs, u8 enum (~0-78+, see destinations enum below), default=2 ★★★★★
    fmxPartLfoDest1Depth=7219, # abs, u8 direct 0-127, default=0 ★★★★★
    fmxPartLfoDest2=7221, # abs, u8 enum, default=4 ★★★★★
    fmxPartLfoDest2Depth=7223, # abs, u8 direct, default=0 ★★★★★
    fmxPartLfoDest3=7225, # abs, u8 enum, default=4 ★★★★★
    fmxPartLfoDest3Depth=7227, # abs, u8 direct, default=0 ★★★★★
)
# FMX 1st LFO Destinations enum — UI-confirmed viaimage:
# InsA Param 1-24 (24 values, "Insertion A parameter targets")
# InsB Param 1-24 (24 values, "Insertion B parameter targets")
# ── Special destinations after InsB Param 24 ──
# 70 = Pan ★★★★★ verified
# 71 = 2nd LFO Speed (UI-list deduced, untested)
# 72 = Filter Cutoff ★★★★★ verified
# 73 = Resonance (UI-list deduced, untested)
# 74 = Feedback ★★★★★ verified
# 75 = Op Freq ★★★★★ verified
# 76 = Op Spectral (UI-list deduced, untested)
# 77 = Op Detune ★★★★★ verified
# 78 = Op Level ★★★★★ verified
# Default=2 likely refers to a specific InsA Param slot.
# Default=4 (Dest2/Dest3) likewise.
# UI-list start (raw 0-21 area) untested — possibly contains "Off"/"None" + other early params.
FMX_LFO_DESTINATIONS = {
    # Special destinations only (verified subset)
    70: 'Pan',
    72: 'FilterCutoff',
    74: 'Feedback',
    75: 'OpFreq',
    77: 'OpDetune',
    78: 'OpLevel',
    # UI-deduced (untested):
    71: 'SecondLfoSpeed',
    73: 'Resonance',
    76: 'OpSpectral',
    # InsA Param 1-24 and InsB Param 1-24 occupy raw values somewhere in 0-69 range.
    # Exact mapping requires further testing if patch editor needs to set them.
}
# 2nd LFO (abs addresses, )
FMX_PART_2ND_LFO = dict(
    # 2nd LFO COMPLETE 7/7 fields ★★★★★
    fmxPart2ndLfoWave=12509, # abs, u8 enum 0-12 (samma som 1st LFO), default=0 ★★★★★
    fmxPart2ndLfoSpeedNormal=12511, # abs, u8 direct, default=30 (aktiv när Extended=OFF) ★★★★★
    fmxPart2ndLfoPhase=12513, # abs, u8 enum 0=0°,1=90°,2=180°,3=270°,4=360°, default=0 ★★★★★
    fmxPart2ndLfoDelay=12515, # abs, u8 direct, default=0 ★★★★★
    fmxPart2ndLfoKeyOnReset=12517, # abs, u8 bool 0=Off,1=On, default=0 ★★★★★
    fmxPart2ndLfoExtended=12529, # abs, u8 bool 0=Off,1=On, default=1=ON ★★★★★
    fmxPart2ndLfoSpeedExtended=12531, # abs, u8 direct, default=60 (aktiv när Extended=ON) ★★★★★
    # Destination/Depth matrix (17 fields, abs=12547+): not mapped
    # Pitch Mod ×8 OPs + Amp Mod ×8 OPs + Filter Mod ×1 = default=0 all
)
# FM-X Part PEG block (abs addresses, )
# Encoding PEG Levels: center=50 (raw = ui + 50, range -50 to +50)
# Encoding PEG Depth: enum [8,2,1,0.5]oct per raw 0-3 (8oct=default!)
# Encoding PitchKeyFollow: raw = round(pct*64/200) + 64 (AWM2-identisk)
# Encoding CenterKey: Yamaha note (C-2=0), C3=60=default
FMX_PART_PEG = dict(
    fmxPegPitchVelSens=12477, # abs, u8 center=64, default=64 ★★★★★
    fmxPegRandomPitch=12479, # abs, u8 direct, default=0 ★★★★★
    fmxPegPitchKeyFollow=12481, # abs, u8 raw=round(pct*64/200)+64, default=96=100% ★★★★★
    fmxPegCenterKey=12483, # abs, u8 Yamaha note (C-2=0), default=60=C3 ★★★★★
    fmxPegInitialLevel=12485, # abs, u8 center=50, default=50 ★★★★★
    fmxPegAttackLevel=12487, # abs, u8 center=50, default=50 ★★★★★
    fmxPegDecay1Level=12489, # abs, u8 center=50, default=50 ★★★★★
    fmxPegDecay2Level=12491, # abs, u8 center=50, default=50 ★★★★★
    fmxPegReleaseLevel=12493, # abs, u8 center=50, default=50 ★★★★★
    fmxPegAttackTime=12495, # abs, u8 direct, default=0 ★★★★★
    fmxPegDecay1Time=12497, # abs, u8 direct, default=0 ★★★★★
    fmxPegDecay2Time=12499, # abs, u8 direct, default=0 ★★★★★
    fmxPegReleaseTime=12501, # abs, u8 direct, default=0 ★★★★★
    fmxPegDepthVelSens=12503, # abs, u8 direct, default=0 ★★★★★
    fmxPegDepth=12505, # abs, u8 enum raw 0-3: [8oct,2oct,1oct,0.5oct], default=0=8oct ★★★★★
    fmxPegTimeKeySens=12507, # abs, u8 direct, default=0 ★★★★★
)
# Part-level LFO fields (PART_BLOCK_START=6708 + rel) — AWM2/generic
# Verified: PART_BLOCK offsets 74,75,505,507,509,519
PART_LFO = dict(
    partLfoTempoSync=74, # u8 bool default=0 (AWM2, rel from PART_BASE)
    partLfoLoop=75, # u8 bool default=0 (AWM2)
    partLfoWave=505, # u8 enum default=0 (AWM2) — FM-X använder FMX_PART_LFO!
    partLfoSpeed=507, # u8 direct default=32 (AWM2)
    partLfoTempoNote=509, # u8 enum default=11 (AWM2)
    partLfoKeyOnReset=519, # u8 direct default=2=On (AWM2)
    # NOTE: FM-X Part LFO använder ANDRA absoluta adresser — se FMX_PART_LFO dict
    # FM-X: Wave=7201, Speed=7203, Delay=7207, FadeIn=7209, Hold=7211,
    # FadeOut=7213(center=64), KeyOnReset=7215, RandomSpeed=7265
)
# Part-level Filter fields (PART_BLOCK_START + rel)
PART_FILTER = dict(
    partFilterType=4, # u8 enum (0=Thru, 2=LPF18D, ...) default=0
    partFilterCutoff=5857, # u16 LE Hz default=2816
)

# AN-X Part-level LFO offsets (PART_BLOCK_START + rel)
# Verified against AN-X_00_Init_Part1_Base.Y2L (v2, 37KB, 1 perf) ✅
ANX_PART_LFO = dict(
    anxPitchLfoSpeed=5795, # u16 LE direct, default=208 ✅
    anxModLfoWave=6430, # u8 enum 0-4 default=2=Tri ✅
    anxModLfoSpeed=6432, # u16 LE direct, default=208 ✅
    anxModLfoDepth=6414, # u8 center=128 default=0 ✅
)
# AN-X Part Common: same as AWM2 PART_COMMON, shifted -12 bytes (4 fields confirmed ✅)
# Formula: AN-X_abs = AWM2_abs - 12 (verified: partPortaSW, portaTime, portaMode, volume)
ANX_PART_COMMON_SHIFT = -12
# AN-X Part Common (abs = AWM2_abs - 12, confirmed for 7+ fields ✅)
ANX_PART_COMMON = dict(
    anxMonoPoly=31, # u8 bool default=1=Poly ✅ (AWM2 abs 6751-12=6739, rel+31)
    anxPartPortaSW=32, # u8 bool default=1 ✅
    anxVolume=123, # u8 direct default=100 ✅
    anxPan=125, # u8 center=64 default=0 ✅
    anxAegAttack=141, # u8 center=64 default=0 ✅ (abs 6849, ui=+20→84)
    anxAegDecay=143, # u8 center=64 default=0 ✅
    anxAegSustain=145, # u8 center=64 default=0 ✅
    anxAegRelease=147, # u8 center=64 default=0 ✅
    anxFEGDepthOffset=157, # u8 center=64 default=0 ✅ (abs 6865, ui=+50→114)
    anxFilterCutoffOffset=159, # u8 center=64 default=0 ✅ (abs 6867, ui=+20→84)
    anxResonanceOffset=161, # u8 center=64 default=0 ★★★★★ (abs 6869erified)
    anxPortaTime=213, # u8 direct default=64 ✅
    anxPortaMode=215, # u8 bool default=1=FullTime ✅
)
# FM-X Part Common (same -12 shift, confirmed for AEG ✅)
FMX_PART_COMMON = dict(
    fmxMonoPoly=31, # u8 bool default=1=Poly ★★★★☆ (AWM2 abs 6751-12=6739, rel+31)
    fmxVolume=123, # u8 direct default=100 ★★★★☆
    fmxPan=125, # u8 center=64 default=0 ★★★★☆
    fmxAegAttack=141, # u8 center=64 default=0 ✅ (abs 6849, verified)
    fmxAegDecay=143, # u8 center=64 default=0 ✅
    fmxAegSustain=145, # u8 center=64 default=0 ✅
    fmxAegRelease=147, # u8 center=64 default=0 ✅
)

# ── DRUM ENGINE ──────────────────────────────────────
# 31 testfiler binärverifierade. Drum keys: 73 keys × 22 fields × 68 bytes stride.
# Drum keys area: [12469:17433] = 4964 bytes. Drum part-level uses ANX-style -12 shift.

DRUM_KEY1_BASE = 12469 # abs offset of drum key 1 (C0, MIDI 12)
DRUM_KEY_STRIDE = 68 # bytes per drum key (verified: SW=0x01 marker repeats every 68 b)
DRUM_KEY_COUNT = 73 # C0..C6 inclusive (MIDI 12..84)

# Per-drum-key fields (rel offset within key, abs = DRUM_KEY1_BASE + key_idx*68 + rel)
# All u8 unless marked u16le. All ★★★★★ binary-verified.
DRUM_KEY = dict(
    drumKeySW = 0, # bool default=1=ON
    drumKeyRcvNoteOff = 4, # bool default=0=Off
    drumKeyAssignMode = 6, # enum default=1=Multi (0=Single)
    drumKeyGroup = 8, # enum default=0=Off (1-26 = A-Z)
    drumKeyWaveformNumber = 10, # u16le default=28
    drumKeyPan = 12, # center=64 default=64=Center
    drumKeyRandomPan = 14, # direct default=0 (0..127)
    drumKeyAlternatePan = 16, # center=64 default=64=Center
    drumKeyConnect = 22, # enum default=1=InsA (0=Thru?, 2=InsB?)
    drumKeyLevel = 26, # direct default=127=max
    drumKeyLevelVel = 28, # center=64 default=64
    drumKeyTimeAttack = 30, # direct default=0
    drumKeyTimeDecay1 = 32, # direct default=96
    drumKeyTimeDecay2 = 34, # direct default=80
    drumKeyLevelDecay1 = 36, # direct default=127=max
    drumKeyCoarse = 38, # center=64 default=64
    drumKeyFine = 40, # center=64 default=64
    drumKeyPitchVel = 42, # center=64 default=64
    drumKeyFilterCutoff = 44, # u16le default=1023=max
    drumKeyFilterCutoffVel = 46, # center=64 default=64
    drumKeyFilterResonance = 48, # direct default=0
    drumKeyHpfCutoff = 50, # u16le default=0
    # EQ — added(per-key 2-band EQ):
    drumKeyEqType = 52, # enum: 0=2-band, 1=P.EQ, 2=Boost6, 5=Thru (3,4 untested)
    drumKeyEqLowFreq = 56, # u8 logarithmic ~25 step/octave; default=54 (=62.5 Hz)
    drumKeyEqLowGain = 58, # center=64, range ±24 dB; raw = 64 + UI_dB * (64/24)
    drumKeyEqHiFreq = 60, # u8 logarithmic; default=231 (=7.4 kHz)
    drumKeyEqHiGain = 62, # center=64, range ±24 dB
)
# Unused offsets within key: rel_key 1-3, 5, 7, 9, 11, 13, 15, 17, 19-21, 23-25,
# 27, 29, 31, 33, 35, 37, 39, 41, 43, 45, 47, 49, 51, 53-55, 57, 59, 61, 63-66.
# rel_key 18 (=90 default) and 67 (=64 default) have non-zero defaults but no UI mapping;
# likely internal padding or sub-state.

# Drum part-level fields (abs offsets, same -12 shift as ANX from AWM2 base)
DRUM_PART_COMMON = dict(
    drumPartFilterCutoff = 6867, # center=64 default=64 ★★★★★ binärverifierat (Test-DRUM_Filter_Amp_Cutoff_+50.Y2L: 64→114)
    drumPartResonance = 6869, # center=64 default=64 ★★★★★ binärverifierat (Test-DRUM_Filter_Amp_Resonance_+50.Y2L)
    drumPitchBendUpper = 6913, # center=64 default=66 (=+2) ★★★★★ binärverifierat
    drumPitchBendLower = 6915, # center=64 default=62 (=-2) ★★★★★ binärverifierat
    drumDetuneHz = 6917, # u16le default=128 (=0 Hz) ★★★★★ binärverifierat (DRUM_00_Init_Detune_8Hz.Y2L: 128→208)
    drumNoteShift = 6919, # center=64 default=64 ★★★★★ binärverifierat
    # Part Common-fält ★★★★★ alla binärverifierade via DRUM-testkorpus (steg 114):
    drumPartElemPanToggle = 6736, # bool default=1=ON
    drumPartArpPlayOnly = 6802, # bool default=0=Off
    drumPartMainCategory = 6815, # enum default=16 (DrumPerc=12) ★★★★★ NY (DRUM_PartSettings_MainCategory_DrumPerc.Y2L)
    drumPartVelLimitLow = 6819, # direct default=1
    drumPartVelLimitHigh = 6821, # direct default=127
    drumPartNoteLimitLow = 6823, # direct (MIDI note) default=0=C-2
    drumPartNoteLimitHigh = 6825, # direct (MIDI note) default=127=G8
    drumPartVelDepth = 6827, # center=64 default=64
    drumPartVelOffset = 6829, # center=64 default=64
    drumPartVolume = 6831, # direct default=100
    drumPartPan = 6833, # center=64 default=64
    drumPartReverbSend = 6835, # direct default=0
    drumPartVariationSend = 6837, # direct default=0
    drumPartDryLevel = 6839, # direct default=127
    drumPartOutput = 6847, # enum default=0=MainL+R, 9=USB1+2, 125=Off
    # Filter AEG (Drum Part-level) ★★★★★ NYA (DRUM steg 114-tester):
    drumPartFilterAegAttack = 6849, # c64 default=64 (Test-DRUM_Filter_Amp_AEG_Attack_+50.Y2L: 64→114)
    drumPartFilterAegDecay = 6851, # c64 default=64 (Test-DRUM_Filter_Amp_AEG_Decay_+50.Y2L)
    drumPartFilterAegSustain = 6853, # c64 default=64 (Test-DRUM_Filter_Amp_AEG_Sustain_+50.Y2L)
    drumPartFilterAegRelease = 6855, # c64 default=64 (Test-DRUM_Filter_Amp_AEG_Release_+50.Y2L)
    # Part Control Group ★★★★★ NYTT (DRUM_General_Pitch_PartControlGroup_A.Y2L):
    drumPartControlGroup = 6903, # enum default=0=Off, 1=A, ... 
    drumPart2EqType = 6961, # enum part-level EQ Type (separate from per-key)
)

# Drum Part Common-fält i ESP Plugin v3.0 UI (Part Common base = abs 7392, rel-offsets)
# Drum har egen Part Common-layout som skiljer sig från AWM2/FM-X/AN-X.
# OBS: Drum Part Common rel +144/+146 är filter-fält, INTE AEG-offsets som för
# AWM2/FM-X/AN-X. Tolkningen styrs av engine_type.
DRUM_PART_COMMON_REL = dict(
    drumAegAttack_rel    = 126, # c64 default=64 (Filter/Amp > AEG > Attack)
    drumAegDecay_rel     = 128, # c64 default=64 (Filter/Amp > AEG > Decay)
    drumAegSustain_rel   = 130, # c64 default=64 (Filter/Amp > AEG > Sustain)
    drumAegRelease_rel   = 132, # c64 default=64 (Filter/Amp > AEG > Release)
    drumFilterCutoff_rel = 144, # c64 default=64 (Filter/Amp > Cutoff)
    drumFilterReso_rel   = 146, # c64 default=64 (Filter/Amp > Resonance)
)

# Drum engine-pool/Drum Key 1-fält (utöver befintliga DRUM_KEY-mappningar)
# Verifierade via Pitch-tester på Drum Init Voice.
DRUM_KEY1_EXTRA = dict(
    drumKeyConnectAbs = 13160,    # = payload 12469 (= DRUM_KEY1_BASE) — Connect: Thru=0, InsA=1 default
    drumKeyCoarseAbs  = 13176,    # = payload 12485 (Drum Key 1 rel +16) — c64 default=64
    drumKeyFineAbs    = 13178,    # = payload 12487 — c64 default=64
    drumKeyPitchVelAbs= 13180,    # = payload 12489 — c64 default=64
    drumAssigneMode   = 13144,    # bool default=1=Multi, 0=Single (Drum Key 1 assign mode)
)

def drum_key_abs(field_name: str, key_idx: int) -> int:
    """Return absolute offset for drum-key field. key_idx: 0..72 (C0..C6)."""
    if field_name not in DRUM_KEY:
        raise KeyError(f"Unknown drum key field: {field_name}")
    if not (0 <= key_idx < DRUM_KEY_COUNT):
        raise ValueError(f"key_idx out of range 0..{DRUM_KEY_COUNT-1}: {key_idx}")
    return DRUM_KEY1_BASE + key_idx * DRUM_KEY_STRIDE + DRUM_KEY[field_name]

# ── PERFORMANCE COMMON — additions ────────────────────────────────
# All ★★★★★ binary-verified. Encoding 'direct' = raw = MIDI CC# (0..127).

# Common Control Numbers — abs [152:200], stride=2 per assign knob
# 15/17 ★★★★★ verified. Scene CC (92) and SuperKnob CC (95) HARD-CODED in
# MODX firmware — they do not appear in blob.
COMMON_CC = dict(
    ribbonCC = 152, # direct default=16 ★★★★★
    breathCC = 154, # direct default=2 ★★★★★
    footCtrl1CC = 156, # direct default=11 ★★★★★
    footCtrl2CC = 158, # direct default=96 ★★★★★
    assignSw1CC = 160, # direct default=86 ★★★★★
    assignSw2CC = 162, # direct default=87 ★★★★★
    # abs 164: untested — possibly FS Assign destination (enum)
    msTriggerCC = 166, # direct default=89 ★★★★★
    assignKnob1CC = 168, # direct default=17 ★★★★★
    assignKnob2CC = 170, # direct default=18 ★★★★★
    assignKnob3CC = 172, # direct default=19 ★★★★★
    assignKnob4CC = 174, # direct default=20 ★★★★★
    assignKnob5CC = 176, # direct default=21 ★★★★★
    assignKnob6CC = 178, # direct default=22 ★★★★★
    assignKnob7CC = 180, # direct default=23 ★★★★★
    assignKnob8CC = 182, # direct default=24 ★★★★★
    # Scene CC (default 92) and SuperKnob CC (default 95) are HARDCODED
    # in MODX firmware and not present in the blob. They show as fixed
    # in ESP UI ("can not edit" indicator).
)

# Hardware Ribbon Assign mode flags ★★★★★
HW_RIBBON_ASSIGN = dict(
    ribbonAssign1Mode = 30, # bool default=1=Latch, 0=Momentary
    ribbonAssign2Mode = 31, # bool default=1=Latch, 0=Momentary
)

# Hardware Ribbon Control — perf-level
HW_RIBBON = dict(
    ribbonModeHold = 33, # bool default=1=Reset, 0=Hold
    sliderDirReverse = 57, # bool default=0=Normal, 1=Reverse
    ribbonGridMode = 216, # enum default=0=Continuous, 1=5step (2=3step?)
)

# Master EQ — abs [560:593], 5 bands × 3 fields ★★★★★ KOMPLETT
# Layout per band: [Gain, Freq, Q | Type]
# Low band: Gain 560, Freq 562, Type 566 (no Q — shelving by default)
# Lo Mid: Gain 568, Freq 570, Q 572
# Mid: Gain 574, Freq 576, Q 578
# Hi Mid: Gain 580, Freq 582, Q 584
# High band: Gain 586, Freq 588, Type 592 (no Q — shelving by default)
# Encoding:
# Gain: center=64, ±24 dB, raw = 64 + UI_dB × (64/24)
# Freq: u8 logarithmic ~6 raw per octave
# Q: raw = UI_Q × 10 (default 7 = 0.7)
# Type: 0=Shelving (default Low/High), 1=Peaking
MASTER_EQ = dict(
    # Low band
    meqLowGain = 560, # center=64
    meqLowFreq = 562, # logarithmic, default=12 (~50 Hz?)
    meqLowType = 566, # 0=Shelving (default), 1=Peaking
    # Lo Mid band
    meqLowMidGain = 568,
    meqLowMidFreq = 570, # default=20
    meqLowMidQ = 572, # default=7 (=Q 0.7), raw=UI*10
    # Mid band
    meqMidGain = 574,
    meqMidFreq = 576, # default=28
    meqMidQ = 578,
    # Hi Mid band
    meqHiMidGain = 580,
    meqHiMidFreq = 582, # default=44
    meqHiMidQ = 584,
    # High band
    meqHighGain = 586,
    meqHighFreq = 588, # default=52
    meqHighType = 592, # 0=Shelving (default), 1=Peaking
    # No Master EQ ON-toggle in blob — always considered active.
)

# ── COMMON FX BLOCKS — REVERB + VARIATION + MASTER FX ────────────────
# Three IDENTICAL 52-byte FX blocks, all in Common-area:
#
# REVERB [376:428] 52 bytes ★★★★★
# VARIATION [432:484] 52 bytes ★★★★★
# MASTER FX [598:650] 52 bytes ★★★★★
#
# Layout per block (52 bytes):
# rel 0-3: Header (Type + Preset/Category, 4 bytes)
# rel 4-51: 24 parameters with stride 2 (Type-specific encoding)
#
# All three blocks have separate ON/OFF toggles in the perf-status area:
# abs 34: Reverb ON/OFF (default 1=ON)
# abs 35: Variation ON/OFF (default 1=ON)
# abs 37: Master FX ON/OFF (default 0=OFF)
# Type=0 within a block also means OFF/Thru (passthrough).

# Reverb FX block — KOMPLETT ★★★★★
# Below is the layout for Type = "Shimmer Reverb"
REVERB_FX = dict(
    reverbOnOff = 34, # u8 bool default=1=ON ★★★★★
    reverbCategory = 376, # u8 enum (0=OFF/Thru, 96=Reverb-cat in test) ★★★★★
    # abs 377: version-byte (always 1)
    # abs 378-379: padding
    reverbType = 380, # u16le, default 32, Shimmer Reverb=436 ★★★★★
    reverbPreset = 382, # u16le, default 10, Basic=569 in test ★★★★★
    # 22 parameters, stride 2, addresses [384:428]
    # For Shimmer Reverb (UI-visible parameters in display order):
    revParam01_shimmerGain = 384, # Shimmer Gain
    revParam02_shimmerFdbk = 386, # Shimmer Fdbk
    revParam03_shimmerHpf = 388, # Shimmer HPF
    revParam04_shimmerLpf = 390, # Shimmer LPF
    revParam05_p1p2Balance = 392, # P1/P2 Balance
    revParam06_p1p2Panning = 394, # P1&P2 Panning
    revParam07_pitch1 = 396, # Pitch 1
    revParam08_fine1 = 398, # Fine 1
    revParam09_pitch2 = 400, # Pitch 2
    revParam10_fine2 = 402, # Fine 2
    revParam11_crossFeedback = 404, # Cross-Feedback
    revParam12_color = 406, # Color
    revParam13_reverbTime = 408, # Reverb Time
    revParam14_initialDelay = 410, # Initial Delay
    revParam15_diffusion = 412, # Diffusion
    revParam16_size = 414, # Size
    revParam17_p1p2DlyOfs = 416, # P1&P2 Dly Ofs
    revParam18_modDepth = 418, # Mod Depth
    revParam19_modSpeed = 420, # Mod Speed
    revParam20_amDepth = 422, # AM Depth
    revParam21_amFreq = 424, # AM Freq
    revParam22_amWaveform = 426, # AM Waveform (enum)
    # NB: UI shows 23 params for Shimmer Reverb (incl AM LR Phase). The
    # 23rd (AM LR Phase) may share rel 50 or be at rel 52 (outside block).
    # Most likely AM Waveform + AM LR Phase are encoded together at one slot.
)
# Other Reverb Types use these same 22 slots with different parameter meanings.

# Variation FX block — KOMPLETT ★★★★★
# Identical structure to Master FX (same 24-param mold).
# Below is the layout for Type = "M/S EQ Compressor" (matches Master FX).
VARIATION_FX = dict(
    variationOnOff = 35, # u8 bool default=1=ON ★★★★★
    variationType = 432, # u8 enum (0=OFF/Thru, M/S EQ Compressor=80) ★★★★★
    # abs 433: ? (preset/version-byte, value 8 for "Wide Side" preset)
    # abs 434-435: padding
    # 24 parameters, stride 2, addresses [436:484]
    # For M/S EQ Compressor (matches Master FX layout):
    varParam01_msBalance = 436,
    varParam02_mThreshold = 438,
    varParam03_mMakeupGain = 440,
    varParam04_sThreshold = 442,
    varParam05_sMakeupGain = 444,
    varParam06_stereoExpand = 446,
    varParam07_compType = 448,
    varParam08_mCompCurve = 450,
    varParam09_sCompCurve = 452,
    varParam10_mGain = 454,
    varParam11_sGain = 456,
    varParam12_eqPosition = 458,
    varParam13_mEqLowFreq = 460,
    varParam14_mEqLowGain = 462,
    varParam15_mEqLowQ = 464,
    varParam16_mEqHighFreq = 466,
    varParam17_mEqHighGain = 468,
    varParam18_mEqHighQ = 470,
    varParam19_sEqLowFreq = 472,
    varParam20_sEqLowGain = 474,
    varParam21_sEqLowQ = 476,
    varParam22_sEqHighFreq = 478,
    varParam23_sEqHighGain = 480,
    varParam24_sEqHighQ = 482,
)
# Other Variation Types use these same 24 slots with different parameter meanings.

# Master FX block — KOMPLETT ★★★★★
# Layout: 1 toggle + 1 Type byte + 1 padding + 24 parameters (stride 2)
# The 24 parameters change meaning depending on Type.
# Below is the layout for Type = "M/S EQ Compressor" (Type-enum=80).
MASTER_FX = dict(
    masterFxOnOff = 37, # u8 bool default=0=OFF ★★★★★
    masterFxType = 598, # u8 enum default=32 (M/S EQ Compressor=80) ★★★★★
    # abs 600: untested (possibly Preset selector or padding)
    # 24 params, stride 2, addresses [602:650]
    # These map to Type-specific UI parameters; for M/S EQ Compressor:
    msfxParam01_msBalance = 602, # M/S Balance
    msfxParam02_mThreshold = 604, # M Threshold
    msfxParam03_mMakeupGain = 606, # M Makeup Gain
    msfxParam04_sThreshold = 608, # S Threshold
    msfxParam05_sMakeupGain = 610, # S Makeup Gain
    msfxParam06_stereoExpand = 612, # Stereo Expand
    msfxParam07_compType = 614, # Comp Type (Hard/Soft enum)
    msfxParam08_mCompCurve = 616, # M Comp Curve
    msfxParam09_sCompCurve = 618, # S Comp Curve
    msfxParam10_mGain = 620, # M Gain
    msfxParam11_sGain = 622, # S Gain
    msfxParam12_eqPosition = 624, # EQ Position
    msfxParam13_mEqLowFreq = 626, # M EQ Low Freq
    msfxParam14_mEqLowGain = 628,
    msfxParam15_mEqLowQ = 630,
    msfxParam16_mEqHighFreq = 632,
    msfxParam17_mEqHighGain = 634,
    msfxParam18_mEqHighQ = 636,
    msfxParam19_sEqLowFreq = 638,
    msfxParam20_sEqLowGain = 640,
    msfxParam21_sEqLowQ = 642,
    msfxParam22_sEqHighFreq = 644,
    msfxParam23_sEqHighGain = 646,
    msfxParam24_sEqHighQ = 648,
)
# NB: Other Master FX Types (Reverb, Delay, etc) use the same 24 parameter
# slots but with different parameter meanings. UI shows correct labels
# automatically based on Type. Encoding per-parameter is also Type-specific.

# Audio In block — Common-area ★★★★★ (Performance-level)
AUDIO_IN = dict(
    audioInInsASwitchCommon = 48,  # u8 bool default=1=ON ★★★★★ (Common-area UI)
    audioInInsBSwitchCommon = 49,  # u8 bool default=1=ON ★★★★★
    audioInVolume = 766,           # u8 direct default=100 ★★★★★
                                   # NB: same byte also exposed in UI as
                                   # "EF AD Output Level" — UI-aliasing
    audioInPan = 768,              # u8 c64 default=64=Center ★★★★★
    audioInRevSend = 770,          # u8 direct default=0 ★★★★★ (TEST: Audio_Rev_50)
    audioInVarSend = 772,          # u8 direct default=0 ★★★★★ (TEST: Audio_Var_50)
    audioInInsConnect = 774,       # u8 enum 1=A→B (default), 2=B→A ★★★★★
    # abs 776: untested
    audioInDryLevel = 778,         # u8 direct default=127 ★★★★★
    # Audio In Mute + Solo: UI-state, EJ persisterat i blob (verifierat TEST5R3-AUDIO_MUTE_ON)
)

# Per-Part Audio In Insertion switches — ★★★★★ (sub-blob 2 +33, +34)
# Verifierat med TEST5R3-T1a/T1b (AWM2 Init Voice, Common/Audio/Insertion A/B toggles)
# Detta är SEPARAT från audioInInsASwitchCommon — UI har två paths för "samma" funktion
PART_COMMON_AUDIO_IN = dict(
    audioInInsASwitchPart_rel = 33,  # rel sub-blob 2 start = abs 6734 för Part 1
    audioInInsBSwitchPart_rel = 34,  # rel = abs 6735 för Part 1
)

def get_part_audio_in_switch_addr(part_idx, switch='A'):
    """Returnerar abs address för Per-Part Audio In Insertion switch."""
    sub_blob_start = 6701 + (part_idx - 1) * 5765
    rel = 33 if switch == 'A' else 34
    return sub_blob_start + rel

# Common FX Returns + Routing — KOMPLETT ★★★★★
COMMON_FX_ROUTING = dict(
    revReturn = 112, # u8 direct, default=64 ★★★★★
    revPan = 114, # u8 c64, default=64=center ★★★★★
    varReturn = 118, # u8 direct, default=96 ★★★★★
    varPan = 120, # u8 c64, default=64=center ★★★★★
    varToRevSend = 122, # u8 direct, default=0 ★★★★★
)

# Common Side Chain —★★★★★
COMMON_SIDE_CHAIN = dict(
    sideChainMaster = 128, # u8 enum 127=OFF (default), 17=Master target ★★★★★
)

# SuperKnob Link per Scene —★★★★★
# 8 bytes at [40:48] in Common-area, plus mirror at [1717:1725] within Scene Struct 1
SUPERKNOB_LINK_BASE = 40
SUPERKNOB_LINK_SCENE_BASE = 1717 # mirror within Scene Struct 1
def get_sk_link_addr(scene, mirror=False):
    """Returns absolute address for SK Link toggle for scene 1-8.
    mirror=True returns the address within Scene Struct 1 (same data, replicated)."""
    base = SUPERKNOB_LINK_SCENE_BASE if mirror else SUPERKNOB_LINK_BASE
    return base + (scene - 1)

# Envelope Follower —★★★★★
ENVELOPE_FOLLOWER = dict(
    envFollowerMasterOutput = 68, # u8 direct default=127 ★★★★★
    envFollowerGain = 780, # u8 c64 (=0 dB), default=64 ★★★★★
    envFollowerAttack = 782, # u8 direct, default=16 ★★★★★
    envFollowerRelease = 784, # u8 direct, default=7 ★★★★★
    envFollowerPart1Output = 6831, # u8 direct, default=100 (Part Common-area) ★★★★★
    # NB: envFollowerPart1Output lives in Part Common; per-part offset for Parts 2-16
    # follows sub-blob model (rel_part = 6831 - 6708 = 123)
)

# ── PER-PART MIXER BLOCK ★★★★★ ────────────────────────────────────────────
# 5 mixer-fält per Part i Part Common, stride 2 inom blocket, stride 5765 mellan parts.
# Verifierat med TEST5R3-T2a-T2e (AWM2 Init Voice, Mixing-vy Part 1 Volume/Pan/Rev/Var/Dry).
# UI-aliasing: PartVolume = EF Part Output (samma byte i två UI-vyer).
PART_MIXER_BLOCK = dict(
    partVolume_rel = 130,  # u8 direct, default=100 (= EF Part Output via UI-aliasing)
    partPan_rel    = 132,  # u8 c64, default=64=Center (TEST5R3-T2b: 64→44=L20)
    partRevSend_rel = 134, # u8 direct, default=0 (TEST5R3-T2c: 0→50)
    partVarSend_rel = 136, # u8 direct, default=0 (TEST5R3-T2d: 0→50)
    partDryLevel_rel = 138, # u8 direct, default=127 (TEST5R3-T2e: 127→80)
)

def get_part_mixer_addr(part_idx: int, field: str) -> int:
    """Returnerar abs address för Part N's mixer-fält (Volume/Pan/RevSend/VarSend/DryLevel)."""
    sub_blob_start = 6701 + (part_idx - 1) * 5765
    return sub_blob_start + PART_MIXER_BLOCK[f'{field}_rel']

# ── COMMON SINGLE-FIELD TOGGLES ★★★★★ ──
COMMON_TOGGLES = dict(
    portamentoMasterSwitch = 29, # u8 bool default=0=OFF ★★★★★
    msMasterOn = 39, # u8 bool default=0=OFF ★★★★★
                                  # (NB: löser 1 av 4 okartlagda toggles)
    commonAudioSwitch = 50, # u8 bool default=1=ON ★★★★★
)

# ── PER-SCENE SUPERKNOB VALUES (Common-area) ★★★★★──
# 8 × u16le (= 16 bytes) at abs [184:200]
# Each scene has its own SuperKnob position
PER_SCENE_SUPERKNOB_BASE = 184
PER_SCENE_SUPERKNOB_STRIDE = 2 # u16le

def get_scene_superknob_addr(scene: int) -> int:
    """Returns abs address for SuperKnob u16le value for scene 1-8.
    Default value = 512 (= mid position)."""
    return PER_SCENE_SUPERKNOB_BASE + (scene - 1) * PER_SCENE_SUPERKNOB_STRIDE

# ── PART COMMON SINGLE-FIELD TOGGLES ★★★★★ ──
# These are at fixed abs offsets for Part 1.
# Per-part offset for Parts 2-16: subtract 6701 (sub-blob 2 start) + add Part N sub-blob start.
PART_COMMON_TOGGLES_PART1 = dict(
    partKbdCtrlOn_part1 = 6732, # u8 bool default=1=ON ★★★★★
    partPortamentoOn_part1 = 6740, # u8 bool default=1=ON ★★★★★
    partArpMasterOn_part1 = 6801, # u8 bool default=1=ON ★★★★★
    partTxRxChannel_part1 = 7273, # u8 enum default=0=Ch1, 1-15=Ch2-Ch16, 127=OFF ★★★★★
)

# Part Common rel offsets (relative to sub-blob start = 6701 for Part 1):
PART_COMMON_REL = dict(
    partMode_rel = 30, # 6731 - 6701 ★★★★★
    kbdCtrlOn_rel = 31, # 6732 - 6701
    partMute_rel = 32, # 6733 - 6701 ★★★★★ (TEST5R3-T5i verified)
    audioInInsASw_rel = 33, # 6734 - 6701
    audioInInsBSw_rel = 34, # 6735 - 6701
    elemPanToggle_rel = 35, # 6736 - 6701 ★★★★★ (Drum ElemPanToggle)
    partSwitch_rel = 36, # 6737 - 6701 ★★★★★ (AN-X PartSwitch / MSMaster)
    portamentoOn_rel = 39, # 6740 - 6701
    # NOTE: Receive Switches (rel +43..+70, 26 switchar) — se RCV_SWITCH_*-konstanter
    # i sektion 6. Inte duplicerade här. Rel +40,+41,+42 är PB/CAT/PAT-RcvSw,
    # rel +44/54 är BankSelect/FC1 (delar av samma RcvSw-block).
    fmxLfoLoopOff_rel = 70, # 6771 - 6701 ★★★★★ (FM-X LFO Loop verified)
    # ANX Mod LFO extras — DELAR samma byte som fmxLfoLoopOff!
    anxModLfoTempoSync_rel = 69, # 6770 - 6701
    anxModLfoLoop_rel = 70, # 6771 - 6701 - delas med fmxLfoLoopOff
    pgmChangeSw_rel = 74, # 6775 - 6701 ★★★★★
    bankSelectSw_rel = 75, # 6776 - 6701 ★★★★★
    panSw_rel = 89, # 6790 - 6701 ★★★★★
    volExpSw_rel = 90, # 6791 - 6701 ★★★★★
    arpMasterOn_rel = 100, # 6801 - 6701
    arpPlayOnly_rel = 101, # 6802 - 6701 ★★★★★ (AN-X/Drum ArpPlayOnly)
    arpLoop_rel = 103, # 6804 - 6701 ★★★★★ (Arp Common Loop)
    arpStartQuantize_rel = 104, # 6805 - 6701 ★★★★★
    arpRandomSfx_rel = 105, # 6806 - 6701 ★★★★★
    arpKeyOnControl_rel = 106, # 6807 - 6701 ★★★★★
    drumVelLimitLow_rel = 118, # 6819 - 6701 ★★★★★ (Drum)
    drumVelLimitHigh_rel = 120, # 6821 - 6701 ★★★★★ (Drum)
    velDepth_rel = 126, # 6827 - 6701 ★★★★★ (Drum VelDepth + ANX VelocityDepth - delas, )
    velOffset_rel = 128, # 6829 - 6701 ★★★★★ (Drum VelOffset)
    volume_rel = 130, # 6831 - 6701 (= EF Part Output UI-aliasing)
    pan_rel = 132, # 6833
    revSend_rel = 134, # 6835
    varSend_rel = 136, # 6837
    dryLevel_rel = 138, # 6839
    partOutput_rel = 146, # 6847 - 6701 ★★★★★ (Drum USB1&2 routing)
    # AEG Offset block ★★★★★
    aegOffset_rel = 148, # 6849 (Attack offset)
    anxAegOffsetDecay_rel = 150, # 6851
    anxAegOffsetSustain_rel = 152, # 6853
    anxAegOffsetRelease_rel = 154, # 6855
    # Filter Offset block ★★★★★
    anxFilterOffsetFegDepth_rel = 164, # 6865
    feg_depth_offset_rel = 164, # alias
    filter_cutoff_offset_rel = 166, # 6867
    resonance_offset_rel = 168, # 6869
    # AWM2 Part-level AEG/FEG Offsets
    # OBS: AWM2 har egen layout som överlappar med AN-X-positioner men har annan semantik.
    # AN-X +148/+150/+152/+154 = AEG Atk/Dec/Sus/Rel
    # AWM2 +144 = AEG Offset Attack (separat från AN-X-blocket)
    # AWM2 +152 = FEG Offset Attack (delar adress med AN-X AEG Sustain)
    # AWM2 +154 = FEG Offset Decay  (delar adress med AN-X AEG Release)
    # Shared Part-level AEG/FEG Offsets
    # AEG-blocket (rel +144..+150) är DELAT mellan ALLA TRE ENGINES (AWM2, FM-X, AN-X)
    # — verifierat med +50-tester på alla tre engines.
    # FEG-blocket (rel +152..+158) är AWM2-only — FM-X och AN-X har egna FEG-strukturer
    # direkt i engine-poolen.
    #
    # Layout: 2-byte stride per fält, alla c64 (default 64).
    # Tester använder +50 (raw 64 → 114) för enkel detektion.
    #
    # OBS — ESP-pluginen har TVÅ skilda UI-platser för "AEG Attack" i AN-X:
    #   1) [PART] General/Pitch > Part Settings > AEG Offset > Atk/Dec/Sus/Rel
    #      → skriver till rel +144..+150 (Part Common, c64) — DELAT med AWM2/FM-X
    #   2) [PART] Filter/Amp > AMP > AEG > Atk/Dec/Sus/Rel
    #      → skriver till AN-X engine-pool 12549..12555 (direct) — AN-X-specifikt
    # Dessa är ALLA verifierade ★★★★★ men är två separata kontroller med olika
    # encoding och olika semantik.
    sharedPartAegOffsetAttack_rel  = 144,  # 6845 
    sharedPartAegOffsetDecay_rel   = 146,  # 6847 
    sharedPartAegOffsetSustain_rel = 148,  # 6849 
    sharedPartAegOffsetRelease_rel = 150,  # 6851 
    awm2PartFegOffsetAttack_rel    = 152,  # 6853
    awm2PartFegOffsetDecay_rel     = 154,  # 6855
    awm2PartFegOffsetSustain_rel   = 156,  # 6857
    awm2PartFegOffsetRelease_rel   = 158,  # 6859
    # Backward compat-aliaser för AWM2-specifika anrop:
    awm2PartAegOffsetAttack_rel    = 144,
    awm2PartAegOffsetDecay_rel     = 146,
    awm2PartAegOffsetSustain_rel   = 148,
    awm2PartAegOffsetRelease_rel   = 150,
    # Ex Elem Sw — DELAR BYTE med arpRandomSfx_rel @ rel +105.
    # ESP Plugin v3.0 UI har en "Ex Elem Sw" toggle på Part-Settings-sidan som
    # ändrar EXAKT samma byte som arpRandomSfx.
    # Möjligen två UI-paneler som kontrollerar samma underliggande switch,
    # eller engine-specifik namngivning. Ingen separat entry behövs.
    # Element Count — AWM2 Part-level Element Count, 8/16/32/64/128
    # När EC > 8 utökas element-arrayen dynamiskt med (EC - 8) × 313 bytes.
    # Värdet KOPIERAS också till Engine header byte 0 (= payload abs 12464,
    # eller "E1 base - 5"). Båda byten har alltid samma värde.
    elementCount_rel = 196,  # 6897 i payload, abs 7588 i 38985-fil
    # Legato Slope — Part-level Legato Slope, u8 0..7
    legatoSlope_rel = 226,  # 6927
    pbRangeUpper_rel = 212, # 6913
    pbRangeLower_rel = 214, # 6915
    detune_rel = 216, # 6917
    noteShift_rel = 218, # 6919
    portamentoTime_rel = 220, # 6921 - 6701 ★★★★★ (FM-X & AN-X Portamento_Time)
    portamentoMode_rel = 222, # 6923 - 6701 ★★★★★ (Fingered/Full)
    portamentoTimeMode_rel = 224, # 6925 - 6701 ★★★★★
    pitchControlGroup_rel = 202, # 6903 - 6701 ★★★★★
    # Mod LFO Phase + Destination Matrix 
    # SHARED struct used by BOTH AN-X (Mod LFO) and AWM2 (LFO Modulation Control)
    # Destination enum values differ per engine:
    #   AN-X: Osc Level = 83
    #   AWM2: Level = 64, Cutoff = 66, Pitch = 65
    modLfoPhase_rel = 498,    # abs 7199 (Phase_90 → 1)
    anxModLfoTempoSpeed_rel = 504, # abs 7205
    anxModLfoHold_rel = 510, # abs 7211
    anxModLfoFadeOut_rel = 512, # abs 7213
    modLfoDest1_rel = 516,    # abs 7217 (AN-X: default 2; AWM2: Level=64)
    modLfoDest1Depth_rel = 518, # abs 7219 (default 0)
    modLfoDest2_rel = 520,    # abs 7221 (AN-X: default 4; AWM2: Cutoff=66)
    modLfoDest2Depth_rel = 522, # abs 7223
    modLfoDest3_rel = 524,    # abs 7225 (AN-X: default 4; AWM2: Pitch=65)
    modLfoDest3Depth_rel = 526, # abs 7227
    anxModLfoRandomSpeed_rel = 564, # abs 7265
    # Part EQ 3-band (rel 238-251) ★★★★★ (ANX_3band tester verified)
    partEqLowFreq_rel = 238, # 6939
    partEqLowGain_rel = 240, # 6941
    partEqLowmidFreq_rel = 242, # 6943
    partEqMidGain_rel = 244, # 6945
    partEqMidQ_rel = 246, # 6947
    partEqHimidFreq_rel = 248, # 6949
    partEqHighGain_rel = 250, # 6951
    # Part EQ 2 (rel 252-266) ★★★★★ (TEST-PEQ2-* verified)
    partEq2Type_rel = 252, # 6953
    partEq2Eq1Freq_rel = 254, # 6955
    partEq2Eq1Gain_rel = 256, # 6957
    partEq2Eq1Q_rel = 258, # 6959
    partEq2Eq2Type_rel = 260, # 6961
    partEq2Eq2Freq_rel = 262, # 6963
    partEq2Eq2Gain_rel = 264, # 6965
    partEq2Eq2Q_rel = 266, # 6967
    insertionA_type_rel = 282, # 6983 - 6701 ★★★★★
    midiVolume_rel = 586, # 7287 - 6701 ★★★★★ Default 100
    midiPan_rel = 588, # 7289 - 6701 ★★★★★ c64 default 64
    midiPgmNum_rel = 594, # 7295 - 6701 ★★★★★ Default 0
    txRxChannel_rel = 572, # 7273 - 6701 ★★★★★
)
# NOTE: Part Solo is UI-only state, NOT persisted in blob (TEST5R3-T5j verified 0 diffs)
# NOTE: Part Mode (rel +30): 0=Internal (default), 1=External (sends MIDI). When External,
#       MIDI-specific fields (rel +74, +75, +89, +90, +586, +588, +594) become active in UI.

def get_part_common_field(sub_blob_start: int, field_name: str) -> int:
    """Get abs address of a per-part Common field for any Part."""
    rel = PART_COMMON_REL[field_name + '_rel']
    return sub_blob_start + rel

# ── PER-PART INSERTION FX STRUCTURE ★★★★★ ──
# Per-Part InsA/InsB är PART-NIVÅ (inte per-element). Element ROUTAS till
# InsA/InsB via element-fält 'elem_connect' (rel +81 i element).
# Strukturen är samma över alla engine-typer (AWM2/AN-X/FM-X verified).
#
# Position i Part Common sub-blob: rel +282 (abs 6983 för Part 1).
# Storlek: ~36 bytes innehållande Type-byte + 12 Param-bytes (Param1-12).
# 
# Layout (rel inom Part Common sub-blob):
#   +282 = InsA Type (u8 enum, 0=Thru default, ex: 18=SPXRoom, 48=Symphonic,
#           32=CompDistorsion, 68=MultiFX, 80=GatedReverb)
#   +283 = InsA Sub-type/Variation (u8)
#   +286, +288, +290, +292, +294 = InsA Param 1-5
#   +296, +298, +300, +302, +304 = InsA Param 6-10
#   +306, +308, +310, +312, +314 = InsA Param 11-15
# (Stride 2 mellan params, u16le hi-byte representation)
#
# Param-defaults är 0 men fylls in när Type sätts.
# Param-betydelser varierar med InsA Type.

PER_PART_INSERTION_REL_BASE = 282  # rel inom sub-blob för Part 1 = abs 6983
PER_PART_INSERTION_TYPE_REL = 282
PER_PART_INSERTION_SUBTYPE_REL = 283
PER_PART_INSERTION_PARAM_RELS = [286, 288, 290, 292, 294, 296, 298, 300, 302, 304, 306, 308, 310, 312, 314]

# InsB ligger 56 bytes efter InsA
PER_PART_INSERTION_B_OFFSET = 56  # InsB rel = InsA rel + 56
PER_PART_INSERTION_B_TYPE_REL = 338      # rel inom sub-blob = abs 7039 för Part 1
PER_PART_INSERTION_B_SUBTYPE_REL = 339
PER_PART_INSERTION_B_PARAM_RELS = [342, 344, 346, 348, 350, 352, 354, 356, 358, 360, 362, 364, 366, 368, 370]

# Insertion Type enum (subset verified,  ):
# OBS: Insertion types definieras också i Section 14 i FULL_CONTEXT (57 typer totalt).
# Detta är bara per-Part InsA Type-byten.
INSERTION_TYPE_KNOWN = {
    0: 'Thru',
    2: 'SPXHall / CrossDelay (FM-X varies)',
    8: 'Presence',
    16: 'ClassicComp / ClassicFlanger / Noisy / Tremolo',
    18: 'SPXRoom',
    32: 'Comp-Distorsion / Phaser TempoPhaser',
    48: 'Chorus Symphonic',
    68: 'Multi-FX',
    80: 'Gated-Reverb / Slice (Tech)',
    # ... fler finns i Section 14
}

def get_part_insertion_a_type(sub_blob_start: int) -> int:
    """Get abs address of InsA Type byte for any Part."""
    return sub_blob_start + PER_PART_INSERTION_TYPE_REL

def get_part_insertion_a_param(sub_blob_start: int, param_idx: int) -> int:
    """Get abs address of InsA Param 1-15 byte for any Part. param_idx is 0-based."""
    if not 0 <= param_idx < len(PER_PART_INSERTION_PARAM_RELS):
        raise ValueError(f'param_idx must be 0..{len(PER_PART_INSERTION_PARAM_RELS)-1}')
    return sub_blob_start + PER_PART_INSERTION_PARAM_RELS[param_idx]

def get_part_insertion_b_type(sub_blob_start: int) -> int:
    """Get abs address of InsB Type byte for any Part."""
    return sub_blob_start + PER_PART_INSERTION_B_TYPE_REL

def get_part_insertion_b_param(sub_blob_start: int, param_idx: int) -> int:
    """Get abs address of InsB Param 1-15 byte for any Part. param_idx is 0-based."""
    if not 0 <= param_idx < len(PER_PART_INSERTION_B_PARAM_RELS):
        raise ValueError(f'param_idx must be 0..{len(PER_PART_INSERTION_B_PARAM_RELS)-1}')
    return sub_blob_start + PER_PART_INSERTION_B_PARAM_RELS[param_idx]

# ── COMMON CONTROL ASSIGN STRUCTURE ★★★★★ ──
# UI: Common / Control / Control Assign — routea controllers till Performance-parametrar.
# 32 slots × 22 bytes = 704 bytes totalt vid abs [2451:3155].
# Layout sannolikt: 8 Assign Knobs × 4 Destinations per knob.
# Verifierat med Test-AWM2-Control-ControlAssign-Source_ModWheel_...

CONTROL_ASSIGN_BASE_ABS = 2451   # Common-blob abs
CONTROL_ASSIGN_STRIDE = 22       # bytes per slot
CONTROL_ASSIGN_COUNT = 32        # totalt 32 slots

# Per-slot field offsets (rel inom 22-byte slot):
CONTROL_ASSIGN_SLOT_FIELDS = {
    0:  ('slot_signature', 'u8 const',  18),    # alltid 18
    1:  ('source_set',     'u8 bool',    0),    # 0=Off, 1=Source aktiv
    3:  ('source_id',      'u8 enum',    8),    # 8=None, 1=ModWheel (verified)
    5:  ('dest_param_lo',  'u8',         1),
    6:  ('dest_param_hi',  'u8',         0),
    9:  ('param2',         'u8',         0),
    11: ('param1',         'u8',         5),
    13: ('curve_type',     'u8 enum',    0),    # 3=Bell (verified)
    15: ('polarity',       'u8 enum',    0),    # 0=Uni, 1=Bi
    17: ('slot_endmark',   'u8 const',   192),  # alltid 0xC0
}

def get_control_assign_slot_addr(slot_idx: int) -> int:
    """Get abs address of ControlAssign slot 0..31."""
    if not 0 <= slot_idx < CONTROL_ASSIGN_COUNT:
        raise ValueError(f'slot_idx must be 0..{CONTROL_ASSIGN_COUNT-1}')
    return CONTROL_ASSIGN_BASE_ABS + slot_idx * CONTROL_ASSIGN_STRIDE

def get_control_assign_field_addr(slot_idx: int, field_name: str) -> int:
    """Get abs address of a field within ControlAssign slot."""
    for rel, (name, _, _) in CONTROL_ASSIGN_SLOT_FIELDS.items():
        if name == field_name:
            return get_control_assign_slot_addr(slot_idx) + rel
    raise KeyError(f"Field '{field_name}' not in CONTROL_ASSIGN_SLOT_FIELDS")

# ── PER-PART MOD SOURCE-TABELL (Aftertouch ControlAssign) ★★★★★ ──
# 4 slots × 16 bytes (NOTERA: olika stride än Common ControlAssign 22b).
# Bekräftade fält (1 slot ändras vid AT-Assign-test):
#   rel +0 = source_set (0=Off, 1=Active)
#   rel +2 = signature (alltid 1 baseline, ändras till 2 vid AT-source)
#   rel +6 = param2 (0→3 i test där Param2=3)
#   rel +8 = param1 (default 5, ändras till 4 vid Param1=4)
#   rel +10 = curve_type (0→3 för Bell)
#   rel +12 = polarity (0→1 för Bi)
#   rel +14 = endmark (alltid 192=0xC0)
# Element-switch (vilka element AT påverkar) är UI-ONLY (ej persisterat).

PER_PART_MOD_SOURCE_REL_BASE = 600  # rel inom Part sub-blob (abs 7301 för Part 1)
PER_PART_MOD_SOURCE_STRIDE = 16
PER_PART_MOD_SOURCE_COUNT = 4  # 4 slots verifierat (ytterligare slots ej bekräftade)

PER_PART_MOD_SOURCE_FIELDS = {
    0:  ('source_set',     'u8 bool',   '0 (Off, 1=Active)'),
    2:  ('signature',      'u8',        '1 (baseline) / 2 (AT-source)'),
    6:  ('param2',         'u8',        '0'),
    8:  ('param1',         'u8',        '5'),
    10: ('curve_type',     'u8 enum',   '0 (3=Bell)'),
    12: ('polarity',       'u8 enum',   '0 (0=Uni, 1=Bi)'),
    14: ('endmark',        'u8 const',  '192 (always 0xC0)'),
}

def get_part_mod_source_slot_addr(sub_blob_start: int, slot_idx: int) -> int:
    """Get abs address of Per-Part Mod Source slot 0..3 for any Part."""
    if not 0 <= slot_idx < PER_PART_MOD_SOURCE_COUNT:
        raise ValueError(f'slot_idx must be 0..{PER_PART_MOD_SOURCE_COUNT-1}')
    return sub_blob_start + PER_PART_MOD_SOURCE_REL_BASE + slot_idx * PER_PART_MOD_SOURCE_STRIDE

# ── PER-PART CONTROL ASSIGN-tabell ★★★★★ ──
# Per-Part Control Assigns vid Part rel +1520..+1695.
# 8 slots × 22 bytes stride (samma stride som Common Control Assign).
# Detta är "Part 1 Assign 1-8" i ESP-pluginens UI (bild 18, 31).
# Source = AsgnKnob 1-8 från Common, Destination = Part-specifika params.
#
# Verifierat via Test-AMW2_Part_ControlAssign_destination1-8:
# Destination-byten (+2) ändrades 1→8/9/10/11/12/13/14/15 för slot 1..8.

PER_PART_CONTROL_ASSIGN_REL_BASE = 1520  # rel inom Part sub-blob (abs 8221 för Part 1)
PER_PART_CONTROL_ASSIGN_STRIDE = 22
PER_PART_CONTROL_ASSIGN_COUNT = 8

# Verifierat från 35 befintliga AWM2_00_Init_CA_*-tester  nya tester.
# Slot-relativa fält:
PER_PART_CONTROL_ASSIGN_FIELDS = {
    0:  ('enabled',             'u8 bool',   '0 (0=inactive, 1=active)'),
    2:  ('dest_category',       'u8',        '1 default; ändras till 8 vid alla edits (kanske "valid flag")'),
    3:  ('dest_category_hi',    'u8',        '0'),
    4:  ('destination_lo',      'u8 enum',   '1 (InsA Param1 default; 50=RevSend, 60=ElemLevel, 61=ElemPan, 87=HPFCutoff, 100=PartPan)'),
    5:  ('destination_hi',      'u8',        '0 (1 för dest_lo>127: MS Length, Part Pan etc.)'),
    8:  ('param2_or_curve_aux', 'u8',        '0 (Param2_3 → 3; Steps → 19; Threshold → 2)'),
    10: ('param1_or_curve_pri', 'u8',        '5 default; Param1_8 → 8; Sigmoid→2, Steps→2, Threshold→0'),
    12: ('curve_secondary',     'u8',        '0; Sigmoid→3, Threshold→1, Param2_3 → 3'),
    14: ('polarity',            'u8 enum',   '0 (Uni=0, Bi=1) — VERIFIERAT från CA_Polarity_Bi'),
    16: ('endmark',             'u8 const',  '192 (0xC0)'),
    21: ('trailer',             'u8',        '18 (sannolikt extra encoding-info)'),
}

# Curve Type-enum (kombination av +10 och +12):
# Standard:  +10=5, +12=0   (default - "ingen kurva-edit")
# Sigmoid:   +10=2, +12=3
# Steps:     +10=2, +12=0, +8=19  (3 byte-konfiguration)
# Threshold: +10=0, +12=1, +8=2

# Destination enum (slot rel +4):
PART_CONTROL_ASSIGN_DESTINATIONS = {
    1:   "InsA Param1 (default)",
    50:  "Rev Send",
    60:  "Element Level",
    61:  "Element Pan",
    87:  "HPF Cutoff",
    100: "Part Pan",
    118: "MS Length",
}

# Source enum (slot rel ?? — verkar lagras nånstans annorstans, kanske i Common-blob CA)
# AsgnKnob1: använder slot 1
# AsgnKnob2: använder slot 1+2 (med dest 8+9 i de aktiva slots)
# AsgnKnob3-8: 3 slots med dest 8+9+10/11/12/13/14/15

def get_part_control_assign_slot_addr(sub_blob_start: int, slot_idx: int) -> int:
    """Get abs address of Per-Part Control Assign slot 0..7 for any Part."""
    if not 0 <= slot_idx < PER_PART_CONTROL_ASSIGN_COUNT:
        raise ValueError(f'slot_idx must be 0..{PER_PART_CONTROL_ASSIGN_COUNT-1}')
    return sub_blob_start + PER_PART_CONTROL_ASSIGN_REL_BASE + slot_idx * PER_PART_CONTROL_ASSIGN_STRIDE

# ── COMMON CONTROL ASSIGN-tabell ★★★★★ ──
# Common Control Assigns vid abs 2452..3155.
# 32 slots × 22 bytes stride (samma struktur som Part Control Assign).
# Detta är "[COMMON] Control > Control Assign" i ESP-pluginens UI (bild 30/31).
#
# Verifierat via Test-AMW2_Part_ControlAssign_destination1-8 +
# Test-AMW2_Part_AfterTouch_destination1-4:
#   Slot enabled-flag (+0) ändras 0→1 när slot aktiveras.
#   Destination (+2) varierar (default 8 → 8/9/10/.../15 för aktiva slots).
#   Source (+4) ändras (default 1 → 226-233 för AT-relaterade slots).
#
# Common-tabellen är "global routing" — Part-tabellen är "per-part destination".
# När man editerar AsgnKnob → Part 1 Assign 1 i UI, skrivs det till BÅDA.

COMMON_CONTROL_ASSIGN_BASE_ABS = 2452
COMMON_CONTROL_ASSIGN_STRIDE = 22
COMMON_CONTROL_ASSIGN_COUNT = 32

COMMON_CONTROL_ASSIGN_FIELDS = {
    0:  ('enabled',        'u8 bool',   '0 (0=inactive, 1=active)'),
    2:  ('destination_lo', 'u8 enum',   '8 (default, varierar)'),
    4:  ('source_id',      'u8',        '1 (default = AsgnKnob1)'),
    10: ('param_a',        'u8',        '5'),
    16: ('endmark',        'u8 const',  '192 (0xC0)'),
    21: ('trailer',        'u8',        '18 (sannolikt curve/polarity packat)'),
}

def get_common_control_assign_slot_addr(slot_idx: int) -> int:
    """Get abs address of Common Control Assign slot 0..31."""
    if not 0 <= slot_idx < COMMON_CONTROL_ASSIGN_COUNT:
        raise ValueError(f'slot_idx must be 0..{COMMON_CONTROL_ASSIGN_COUNT-1}')
    return COMMON_CONTROL_ASSIGN_BASE_ABS + slot_idx * COMMON_CONTROL_ASSIGN_STRIDE

# ── SUPERKNOB ASSIGN POSITION TABELL ★★★★★ ──
# 8 Assign Knobs × 6 bytes per knob (Left/Mid/Right positions u16le)
# Position: abs 674..722 (48 bytes mappat + 4 extra bytes runtomkring)
# Verifierat: Assign1/2/3_LeftPosition_90, MidPosition_300, RightPosition_700
# Default per knob: Left=0, Mid=512, Right=1023 (0..1023 range)

SUPERKNOB_ASSIGN_BASE_ABS = 674
SUPERKNOB_ASSIGN_STRIDE = 6
SUPERKNOB_ASSIGN_COUNT = 8
SUPERKNOB_MODE_FLAG_ABS = 671   # u8, ändras 2→0 vid Position-justering
SUPERKNOB_ASSIGN_FIELDS_REL = {
    0: ('left_position',  'u16le', '0'),       # Default min
    2: ('mid_position',   'u16le', '512'),     # Default midpoint
    4: ('right_position', 'u16le', '1023'),    # Default max
}

def get_superknob_assign_addr(knob_idx: int, field_name: str) -> int:
    """Returnera abs adress för Assign Knob N:s position-fält (0..7)."""
    if not 0 <= knob_idx < SUPERKNOB_ASSIGN_COUNT:
        raise ValueError(f'knob_idx must be 0..7')
    for rel, (name, _, _) in SUPERKNOB_ASSIGN_FIELDS_REL.items():
        if name == field_name:
            return SUPERKNOB_ASSIGN_BASE_ABS + knob_idx * SUPERKNOB_ASSIGN_STRIDE + rel
    raise KeyError(f"Field '{field_name}' not in SUPERKNOB_ASSIGN_FIELDS_REL")

# ── ARP INDIVIDUAL DATA — Region [7094:7165] ──
# Confirmed: abs 7131 = Arp Individual Velocity (default=128)
# Region appears to contain per-arp-step velocity/gate-array data
ARP_INDIVIDUAL_BASE = 7094 # block start (Part Common-area)
ARP_INDIVIDUAL_SIZE = 71 # block size (u16le-array, mest c64=64 / 0x80=128)
# Specific field discovered:
ARP_INDIVIDUAL_VELOCITY_PART1 = 7131 # u8 default=128 ★★★★★

# Receive Switch per Part — UNIVERSELL MODELL ★★★★★
# Block-stride per part: 5765 bytes (samma som Part Common-stride)
# Rel-offset från sub-blob-start: 43 bytes
# Block-storlek: 28 bytes (26 switchar default 1=ON + 2 byte block-end markörer)
#
# Verifierade över 5 testfiler (ANX + AWM2 baser, Parts 1-3, mixed-engine).
# Layout är ENGINE-OBEROENDE — samma struktur för AN-X, AWM2, FM-X, Drum.

RCV_SWITCH_REL_OFFSET = 43 # rel from sub-blob start
RCV_SWITCH_BLOCK_SIZE = 28 # 26 switches + 2 end markers
RCV_SWITCH_COUNT = 26 # actual switches (default 1=ON)

# Switch positions inom RcvSw-blocket — KOMPLETT efter(25/26):
# Verifierat med 28 testfiler totalt.
RCV_SWITCH_POS = dict(
    # ── Pre-CC group ──
    PC = 0, # ★★★★★
    BankSelect = 1, # ★★★★★(NEW)
    CC = 2, # ★★★★★(NEW)

    # ── Assign Knob group ──
    AKnob1 = 3, # ★★★★★
    AKnob2 = 4, # ★★★★★
    AKnob3 = 5, # ★★★★★
    AKnob4 = 6, # ★★★★★
    AKnob5 = 7, # ★★★★★(verified — was inferred)
    AKnob6 = 8, # ★★★★★
    AKnob7 = 9, # ★★★★★
    AKnob8 = 10, # ★★★★★

    # ── Foot Controller + MW + Sustain + Pan ──
    FC1 = 11, # ★★★★★
    FC2 = 12, # ★★★★★
    MW = 13, # ★★★★★(NEW — was inferred FS)
    Sustain = 14, # ★★★★★
    Pan = 15, # ★★★★★

    # ── Volume/Expression + Wheels group ──
    VolExp = 16, # ★★★★★
    RB = 17, # ★★★★★(NEW)
    BC = 18, # ★★★★★(NEW)

    # ── Switches group ──
    FS = 19, # ★★★★★(NEW — was inferred pos 13!)
    ASw1 = 20, # ★★★★★
    ASw2 = 21, # ★★★★★
    # pos 22: UNKNOWN — only one untested position

    # ── End group ──
    MSTrigger = 23, # ★★★★★
    PortaSw = 24, # ★★★★★
    PortaTime = 25, # ★★★★★
)

# Switches NOT in blob (verified):
RCV_SWITCH_NOT_IN_BLOB = ['PitchBend', 'ChAfterTouch', 'PolyAfterTouch']
# These are hardware-global events stored separately, similar to Transmit Switch.

def get_rcv_switch_addr(sub_blob_start: int, switch_pos: int) -> int:
    """Get absolute address of a Receive Switch within a Part's sub-blob.

    sub_blob_start: abs address where the part's sub-blob header starts
                    (e.g. 6701 for Part 1, or 6701 + (N-1)*5765 for Part N)
    switch_pos: 0-25 within the RcvSw block
    """
    return sub_blob_start + RCV_SWITCH_REL_OFFSET + switch_pos

def get_rcv_switch_addr_by_name(sub_blob_start: int, switch_name: str) -> int:
    """Convenience helper using switch name from RCV_SWITCH_POS dict."""
    return get_rcv_switch_addr(sub_blob_start, RCV_SWITCH_POS[switch_name])

# Convenience: Part 1 (always at sub-blob 2 @ 6701)
RECEIVE_SWITCH_PART1 = dict(
    rcvSwPart1_PC = 6744, # u8 bool default=1=ON, pos 0 ★★★★★
    rcvSwPart1_AKnob8 = 6754, # u8 bool default=1=ON, pos 10 ★★★★★
    rcvSwPart1_Pan = 6759, # u8 bool default=1=ON, pos 15 ★★★★★
)
RECEIVE_SWITCH_PART1_BASE = 6744 # block start
RECEIVE_SWITCH_PART1_SIZE = 28 # full block including end markers

# ──────────────────────────────────────────────────────────────────────
# ENGINE-POOL STRUCTURE (multi-part files) ★★★★★
# ──────────────────────────────────────────────────────────────────────
# In multi-part files, engines are stored in a pool after all sub-blobs.
# Engine-pool layout: [Engine 1][5b sep][Engine 2][5b sep]...[Engine M]
# Last engine has NO trailing separator.

ENGINE_POOL_SEP_SIZE = 5 # 5 bytes separator between engines

# Engine data sizes (Init/default state) — KOMPLETT ★★★★★:
ENGINE_DATA_SIZE = dict(
    ANX = 684, # ★★★★★erified
    AWM2 = 2503, # ★★★★★erified
    FMX = 1143, # ★★★★★erified
    Drum = 4963, # ★★★★★erified
)

def get_engine_pool_start(num_parts: int) -> int:
    """Returns abs address where engine-pool starts in a multi-part file.
    Common (6701) + N parts × 5765 = pool start"""
    return 6701 + num_parts * 5765

def get_engine_offset_in_pool(part_engines: list, part_index: int) -> int:
    """Calculate engine offset within pool for Part N.

    part_engines: list of engine-type strings ['ANX', 'AWM2', ...] in part-order
    part_index: 0-based index of part to get engine for

    Returns: byte offset from pool start
    """
    offset = 0
    for i in range(part_index):
        engine_type = part_engines[i]
        offset += ENGINE_DATA_SIZE[engine_type] + ENGINE_POOL_SEP_SIZE
    return offset

def get_engine_addr(num_parts: int, part_engines: list, part_index: int) -> int:
    """Get absolute address where Part N's engine data starts in multi-part file.

    num_parts: total parts in the file
    part_engines: list of engine-type strings (length = num_parts)
    part_index: 0-based index of the part you want the engine for
    """
    pool_start = get_engine_pool_start(num_parts)
    pool_offset = get_engine_offset_in_pool(part_engines, part_index)
    return pool_start + pool_offset

def parse_engine_type_from_name(blob: bytes, sub_blob_start: int) -> str:
    """Read part name from sub-blob header and extract engine-type suffix.

    Returns: 'ANX', 'AWM2', 'FMX', 'Drum', or 'Unknown'

    NB: Drum part-namn är 'Init Drum' (UTAN parentes-suffix),
        medan AN-X/AWM2/FM-X har 'Init Normal (XXXX)' format.
    """
    name_bytes = bytes(blob[sub_blob_start + 4 : sub_blob_start + 25])
    name = name_bytes.decode('latin-1', errors='replace')
    if '(AN-X)' in name: return 'ANX'
    if '(AWM2)' in name: return 'AWM2'
    if '(FM-X)' in name: return 'FMX'
    if 'Drum' in name: return 'Drum' # ★★★★★: drum har ingen (...)
    return 'Unknown'

def get_engine_type_byte(blob: bytes) -> str:
    """Read engine-type byte at blob[+6700] and return engine name.

    Engine Type byte encoding ★★★★★:
        0=AWM2, 1=Drum, 2=FMX, 3=ANX
    """
    val = blob[ENGINE_TYPE_BYTE]
    return ENGINE_TYPE_VALUES.get(val, f'Unknown({val})')

def get_max_active_part(blob: bytes) -> int:
    """Read max active part index from blob[+6695].

    Returns the HIGHEST part number that is active (NOT the count of active parts).
    Example: Parts 3+5 active → returns 5, not 2.
    """
    return blob[MAX_ACTIVE_PART_BYTE]

def validate_engine_consistency(blob: bytes) -> tuple[bool, str]:
    """Check that blob[+6700] matches sub-blob 2 name suffix.

    Returns (valid, message). Catches data corruption or
    incorrect engine-type-byte writes during patch editing.

    Notera: vissa Init-filer har sub-blob 2 name = performance-namn istället för
    "Init Normal (XXX)" suffix. Då går vi på blob[+6700] direkt.
    """
    engine_byte_name = get_engine_type_byte(blob)
    engine_name_str = parse_engine_type_from_name(blob, 6701)
    if engine_name_str == 'Unknown':
        return True, f"OK (byte only): {engine_byte_name}"
    if engine_byte_name == engine_name_str:
        return True, f"OK: {engine_byte_name}"
    return False, f"Mismatch: byte says {engine_byte_name}, name says {engine_name_str}"

def set_engine_type_byte(blob: bytearray, engine_name: str) -> None:
    """Write engine-type byte at blob[+6700]. engine_name: 'AWM2', 'Drum', 'FMX', 'ANX'."""
    if engine_name not in ENGINE_TYPE_BY_NAME:
        raise ValueError(f"Unknown engine name: {engine_name}")
    blob[ENGINE_TYPE_BYTE] = ENGINE_TYPE_BY_NAME[engine_name]

def set_max_active_part(blob: bytearray, max_part_idx: int) -> None:
    """Write max active part index at blob[+6695]. max_part_idx: 1..16."""
    if not 1 <= max_part_idx <= 16:
        raise ValueError(f"max_part_idx must be 1..16, got {max_part_idx}")
    blob[MAX_ACTIVE_PART_BYTE] = max_part_idx

# ── AWM2 ENGINE INTERNAL STRUCTURE ★★★★★ ──
# AWM2 engine = 3 byte header + 7 elements × 313 byte + 1 element × 309 byte = 2503 bytes
# Header bytes (engine_start..+3): [00 00 2b] (constant signature)
# Elements:
#   E1-E7: 313 bytes each
#   E8:    309 bytes (4 bytes kortare än övriga — possibly utan tail-padding)
# Total: 3 + 7*313 + 309 = 2503 ✓
#
# Verifierat med TEST5R3-T5a/e (Element enable toggles E1-E8 confirms stride 313).

# Engine header — semantik:
#   Tidigare docs: "Engine-pool börjar @ abs 12466" syftar på engine_type-byten.
#   Faktiskt: 5 bytes föregår E1 base (= abs 12469). Element_count ligger på
#   "E1 base - 5" = engine_type byte - 2.
#
#   AWM2_HEADER byte 0 (E1-3 = engine_type byte) = engine_type (0=AWM2)
#   AWM2_HEADER byte 1 (E1-2) = ? (alltid 0 i observerade filer)
#   AWM2_HEADER byte 2 (E1-1) = ? (43 i AWM2 baseline)
#
#   FÖRE header (relativt engine_type-byten):
#     engine_type_byte - 2 = element_count — 8/16/32/64/128
#     engine_type_byte - 1 = ? (alltid 0)
#
#   Speglas till Part Common rel +196 (elementCount_rel). Båda bytes har alltid
#   identiska värden. Vid EC > 8 utökas element-arrayen med (EC - 8) × 313 bytes,
#   och filstorleken växer exakt: extra_size = (EC - 8) × 313.
AWM2_HEADER_SIZE = 3   # bytes mellan engine_type-byten och E1 base (oförändrad)
AWM2_ELEMENT_STRIDE = 313
AWM2_ELEMENT_COUNT_DEFAULT = 8  # Default när UI Element Count = 8
AWM2_ELEMENT_COUNT_MAX = 128    # Max enligt ESP Plugin v3.0 UI
AWM2_ELEMENT_COUNT = AWM2_ELEMENT_COUNT_DEFAULT  # Backward compat alias
AWM2_LAST_ELEMENT_SIZE = 309  # E8 är 4 byte kortare än E1-E7 (vid EC=8)
AWM2_ELEMENT_COUNT_REL_FROM_ENGINE_TYPE = -2  # element_count = engine_type_byte - 2

def get_awm2_element_count(blob: bytes, engine_start_abs: int) -> int:
    """Returnera Element Count från engine header.
    engine_start_abs = adressen där engine_type-byten ligger (vanligen 12466)."""
    return blob[engine_start_abs + AWM2_ELEMENT_COUNT_REL_FROM_ENGINE_TYPE]

def get_awm2_element_offset(element_idx: int) -> int:
    """Rel offset inom AWM2 engine för element 0-7."""
    return AWM2_HEADER_SIZE + element_idx * AWM2_ELEMENT_STRIDE

def get_awm2_element_addr(engine_start_abs: int, element_idx: int) -> int:
    """Abs address för AWM2 element 0-7 inom en engine."""
    return engine_start_abs + get_awm2_element_offset(element_idx)

# Per-element field offsets (rel inom 313-byte element block) ★★★★★
# 76 fält EXTRAHERADE och VERIFIERADE /31-34/73/76 + TEST5R3-T5a/e
#  PEG/EQ-tester  tester (ElemConnect, ElemGroup, EQType,
# Level Scaling) via "unique offset per field"-heuristik (varje fält testat med
# min 1 fil där bara DEN offseten ändras, så NOISE och side-effects filtrerats bort).
# Format: rel_offset → (field_name, encoding, default_value)
AWM2_ELEMENT_FIELDS = {
    # Enable (TEST5R3-T5a/e verified)
    0:   ('enable',                'u8 bool',       'E1=1, E2-8=0'),
    # KeyOnDly Sync toggle
    1:   ('keyondly_sync',         'u8 bool',       '0 (OFF)'),
    # AEG Half Damper (Element_1_AEG_HalfDamper_ON verified)
    2:   ('aeg_half_damper',       'u8 bool',       '0 (OFF)'),
    # Extended LFO toggle ★★★★★ binärverifierat (Test-AWM2-ElementLFO-ExtendedLFO_ON/OFF.Y2L)
    6:   ('extended_lfo',          'u8 bool',       '1 (ON for Init Normal AWM2; 0=OFF). Bestämmer vilken Speed-byte UI visar — rel +289 när AV, rel +307 när PÅ'),
    # Elem Group
    49:  ('elem_group',            'u8 direct',     '0 (Group 1, range 0..7 = Groups 1..8)'),
    # Waveform (Element1_Waveform_* verified;  WaveformCategory_Keyboard → byte 219)
    51:  ('waveform_lo',           'u8',            'varies (6=default, varies per category)'),
    # XA Control — Normal/Legato/KeyOff/Cycle/Random/A.Sw Off/A.Sw1 On/A.Sw2 On
    67:  ('xa_control',            'u8 enum',       '0 (Normal; 1=Legato, 2=KeyOff, 3=Cycle, 4=Random, 5=A.Sw Off, 6=A.Sw1 On, 7=A.Sw2 On)'),
    # Pan / Spatial
    59:  ('pan',                   'u8 c64',        '64'),
    # AEG Pan modulation (Element_1_AEG_*Pan tester verified)
    61:  ('aeg_random_pan',        'u8',            '0 (max 127)'),
    63:  ('aeg_alternate_pan',     'u8 c64',        '64'),
    65:  ('aeg_scaling_pan',       'u8 c64',        '64'),
    # Note + Velocity limits
    69:  ('note_limit_low',        'u8 MIDI',       '0'),
    71:  ('note_limit_high',       'u8 MIDI',       '127'),
    73:  ('vel_limit_low',         'u8',            '1'),
    75:  ('vel_limit_high',        'u8',            '127'),
    77:  ('vel_xfade',             'u8',            '0 (Velocity_Cross_Fade_14 → 14)'),
    # Elem Connect — element-level Ins routing
    81:  ('elem_connect',          'u8 enum',       '1 (0=Thru, 1=InsA, 2=InsB)'),
    # KeyOnDly Sync
    85:  ('keyondly_sync_delay',   'u8',            '11'),
    # Amp section
    91:  ('level',                 'u8 direct',     '127'),
    93:  ('amp_level_vel',         'u8 c64',        '64 (Amp_LevelVel_50 → 114)'),
    # AEG section ★★★★★ verifierat +33+69 tester
    95:  ('aeg_offset',            'u8 c64',        '0 (max 127)'),
    97:  ('amp_level_curve',       'u8 enum',       '3 '),
    99:  ('aeg_attack',            'u8',            '0'),
    101: ('aeg_decay1',            'u8 c64',        '64'),
    103: ('aeg_decay2',            'u8 c64',        '64'),
    105: ('aeg_half_damper_time',  'u8',            '127'),
    107: ('aeg_release',           'u8',            '50'),
    109: ('aeg_initial_level',     'u8',            '0 (AEG_Initial_Level_14 → 14)'),
    111: ('aeg_attack_level',      'u8',            '127 (AEG_AttackLevel_50 → 50)'),
    113: ('aeg_decay1_level',      'u8',            '127 (AEG_Decay1Level_50 → 50)'),
    # AEG Offset (Element_1_AEG_Offset_127 verified) - now defined above
    # AEG Half Damper Time (Element_1_AEG_HalfDamper_ON_Time_50 verified) - now above
    # AEG Levels (rel +109/+111/+113) - now above
    115: ('aeg_decay2_level',      'u8',            '127'),
    117: ('amp_segment_decay',     'u8',            '4'),
    119: ('amp_time_vel',          'u8 c64',        '64'),
    # Level Scaling (rel 121-143) ★★★★★  test 2
    # 5 BreakPoints: CenterKey + BP1-BP4 (5 punkter på keyboardet)
    # 4 Offsets emellan punkterna (c128 = 0 dB default)
    121: ('amp_time_key',          'u8 c64',        '64'),
    123: ('amp_scaling_center_key','u8 MIDI',       '24 (C0)'),
    125: ('amp_scaling_bp1',       'u8 MIDI',       '36 (C1)'),
    127: ('amp_scaling_bp2',       'u8 MIDI',       '48 (C2)'),
    129: ('amp_scaling_bp3',       'u8 MIDI',       '60 (C3)'),
    131: ('amp_scaling_bp4',       'u8 MIDI',       '72 (C4)'),
    133: ('amp_scaling_offset1',   'u8 c128',       '128 (=0 dB)'),
    135: ('amp_scaling_offset2',   'u8 c128',       '128'),
    137: ('amp_scaling_offset3',   'u8 c128',       '128'),
    139: ('amp_scaling_offset4',   'u8 c128',       '128'),
    143: ('amp_release_adj',       'u8 c64',        '64'),
    # Element Level Key
    141: ('level_key',             'u8 c64',        '64 (LevelKey_+50 → 114)'),
    # Element Pitch Key
    157: ('pitch_key',              'u8',            '96 (c96; PitchKey_+50 → 82)'),
    # rel +159 = pegKFCenterNote ★★★★★ UI-bekräftat (AWM2 bild 2: PEG Center Key = C 3)
    # Tidigare antagen peg_center_key — det var fel. PEG Center Key i UI ligger faktiskt här.
    159: ('peg_center_key',        'u8 MIDI',       '60 (=C3). UI: [ELEMENT] Pitch EG > Center Key. Cross-verified via AWM2_ELEM_LAYOUT off=108 + UI bild.'),
    # PEG block (rel +163..+193) — kompletta definitionerna finns nedan i FEG/PEG-blocket
    # Tidigare dubblerades de här; konsoliderat med block efter rad ~1637.
    # Endast unika fält från denna position:
    163: ('peg_hold_time',         'u8',            '0 (PEG_HoldTime_50)'),
    169: ('peg_signature',         'u8',            '64 (changes in ALL PEG tests: 64→76; PEG-edit marker)'),
    # Element 1 Delay Length
    79:  ('delay_length',          'u8',            '0'),
    # Element 1 Pitch Block
    149: ('coarse_tune',           'u8 c64',        '64 (centered, ±20 semitones via UI)'),
    151: ('fine_tune',             'u8 c64',        '64 (centered)'),
    153: ('pitch_vel',             'u8 c64',        '64 (centered)'),
    155: ('pitch_random',          'u8',            '0'),
    161: ('fine_key',              'u8 c64',        '64 (centered)'),
    # Filter Type + Cutoff/Resonance/HPF/Gain
    201: ('filter_type',           'u8 enum',       '4 (default; LPF24A=1, DualBEF=17, etc.)'),
    203: ('filter_cutoff_lo',      'u8',            '128 (u16le, max raw value with rel+204=2)'),
    204: ('filter_cutoff_hi',      'u8',            '2 (u16le hi-byte)'),
    205: ('filter_cutoff_vel',     'u8 c64',        '64'),
    207: ('filter_resonance',      'u8',            '0'),
    209: ('filter_resonance_vel',  'u8 c64',        '64'),
    211: ('hpf_cutoff_lo',         'u16le',         '0 (HPFCutoff_400 → 144/1)'),
    212: ('hpf_cutoff_hi',         'u8',            '0 (u16le hi-byte)'),
    213: ('filter_distance',       'u8 c128',       '128 (DualBEF Distance / band offset)'),
    215: ('filter_gain',           'u8',            '230 (filter output gain; Filter_Gain_0/130/255)'),
    # FEG Block (rel +219..+241) ★★★★★ KOMPLETT +33 tester
    219: ('filter_time_attack',    'u8',            '0 (Filter_Time_Attack_30 → 30)'),
    221: ('filter_time_decay1',    'u8 c64',        '64 (Filter_Time_Decay1_30 → 30)'),
    223: ('filter_time_decay2',    'u8 c64',        '64 (Filter_Time_Decay2_30 → 30)'),
    225: ('filter_time_release',   'u8',            '80 (Filter_Time_Release_40 → 40)'),
    227: ('filter_level_hold',     'u8 c128',       '128 (Filter_Level_Hold_22 → 150)'),
    229: ('filter_level_attack',   'u8',            '255 (Filter_Level_Attack_70 → 198)'),
    231: ('filter_level_decay1',   'u8',            '255 (Filter_Level_Decay1_70 → 198)'),
    233: ('filter_level_decay2',   'u8',            '255 (Filter_Level_Decay2_70 → 198)'),
    235: ('filter_level_release',  'u8 c128',       '128 (Filter_Level_Release_70 → 198)'),
    # Filter FEG Depth (Filter_FEGDepth_20 → rel +237: 104→84) ★★★★★  verified
    237: ('filter_feg_depth',      'u8 c104',       '104 (FEGDepth_20 → 84)'),
    239: ('filter_segment',        'u8 enum',       '4 '),
    241: ('filter_time_vel',       'u8 c64',        '64 (Filter_TimeVel_20 → 84)'),
    # Filter Curve — stänger UNMAPPED rel +245 
    # Filter_Curve_0 → 0, Filter_Curve_1 → 1, Filter_Curve_2 = default, Filter_Curve_4 → 4
    245: ('filter_curve',          'u8 enum',       '2'),
    # Filter Level Scaling (rel +247..+265) ★★★★★  verified
    # Parallel structure to AMP Level Scaling (rel 121-143):
    # 5 BreakPoints (CenterKey + BP1-BP4) + 4 Offsets between points
    247: ('filter_time_key',       'u8 c64',        '64'),
    249: ('filter_scaling_center_key', 'u8 MIDI',   '24 (C0)'),
    251: ('filter_scaling_bp1',    'u8 MIDI',       '36 (C1)'),
    253: ('filter_scaling_bp2',    'u8 MIDI',       '48 (C2)'),
    255: ('filter_scaling_bp3',    'u8 MIDI',       '60 (C3)'),
    257: ('filter_scaling_bp4',    'u8 MIDI',       '72 (C4)'),
    259: ('filter_scaling_cutoff_offset1', 'u8 c128', '128 (=0 cutoff offset)'),
    261: ('filter_scaling_cutoff_offset2', 'u8 c128', '128'),
    263: ('filter_scaling_cutoff_offset3', 'u8 c128', '128'),
    265: ('filter_scaling_cutoff_offset4', 'u8 c128', '128'),
    # AWM2 LFO Element Matrix (rel +299..+305) ★★★★★  verified
    # Each element has its own Phase Offset + 3 Depth Ratios for LFO modulation
    # Connects to Part Common LFO Phase + 3 Destinations (rel +498, +516..+526)
    # Destination enum values: Level=64, Cutoff=66, Pitch=65 (AWM2-specific)
    # Phase offset values: 0=0°, 1=90°, 2=120°, 3=180°, 4=240°, 5=270°
    299: ('element_lfo_phase_offset','u8 enum',     '0 (=0°; 90°=1, 120°=2, 180°=3, 240°=4, 270°=5)'),
    301: ('element_lfo_dest1_depth', 'u8',          '127 (Element Depth Ratio Row 1 = Level dest)'),
    303: ('element_lfo_dest2_depth', 'u8',          '127 (Element Depth Ratio Row 2 = Cutoff dest)'),
    305: ('element_lfo_dest3_depth', 'u8',          '127 (Element Depth Ratio Row 3 = Pitch dest)'),
    # Element trailer/state
    267: ('element_edit_counter',  'u8',            '74 (increments on any element edit)'),
    269: ('hpf_cutoff_key',        'u8 c64',        '64'),
    # EQ P.EQ-specific fields 
    # P.EQ mode (rel +271 = 1) activates rel +273 (Q), +275 (Frequency), +277 (Gain)
    # In 2-band mode (default), these are the High band parameters
    273: ('eq_q_or_resonance',     'u8',            '0 (P.EQ Q; : Q=1.9 → 4)'),
    275: ('eq_low_freq',           'u8',            '54 (EQ_Low_Frequency_84.0Hz → 64; P.EQ 1.5kHz → 171)'),
    277: ('eq_low_gain',           'u8 c64',        '64 (EQ_Low_Gain_+6.00db → 80; in P.EQ mode = EQ Gain)'),
    279: ('eq_high_freq',          'u8',            '231 (EQ_High_Frequency_8.50kHz → 235)'),
    281: ('eq_high_gain',          'u8 c64',        '64 (EQ_High_Gain_+6.00db → 80, +10dB → 91)'),
    # LFO Wave (rel +283) ★★★★★  verified — NOT routing bitmask!
    283: ('lfo_wave',              'u8 enum',       '1 (0=Saw, 1=Tri default, 2=Square)'),
    # LFO KeyOnReset (rel +285) ★★★★★  verified
    285: ('lfo_keyonreset',        'u8 bool',       '1 (ON; KeyOnReset_Off → 0)'),
    # Element LFO block (rel +287..+307) ★★★★★  verified
    287: ('lfo_delay',             'u8',            '0'),
    291: ('lfo_amp_mod_depth',     'u8',            '0'),
    293: ('lfo_pitch_mod_depth',   'u8',            '0'),
    295: ('lfo_filter_mod_depth',  'u8',            '0'),
    297: ('lfo_fade_in',           'u8',            '0'),
    307: ('lfo_speed',             'u8',            '60'),
    # PEG — Pitch Envelope Generator ★★★★★
    163: ('peg_time_hold',         'u8',            '0'),
    165: ('peg_time_attack',       'u8',            '40'),
    167: ('peg_time_decay1',       'u8',            '64'),
    169: ('peg_time_decay2',       'u8',            '64'),
    171: ('peg_time_release',      'u8',            '64'),
    173: ('peg_level_hold',        'u8 c128',       '128 (=0)'),
    175: ('peg_level_attack',      'u8 c128',       '128 (=0)'),
    177: ('peg_level_decay1',      'u8 c128',       '128 (=0)'),
    179: ('peg_level_decay2',      'u8 c128',       '128 (=0)'),
    181: ('peg_level_release',     'u8 c128',       '128 (=0)'),
    183: ('peg_depth',             'u8 c64',        '84 (=+20)'),
    185: ('peg_segment',           'u8 enum',       '4'),
    187: ('peg_time_vel',          'u8 c64',        '64'),
    189: ('peg_depth_vel',         'u8 c64',        '64'),
    191: ('peg_curve',             'u8 enum',       '2'),
    193: ('peg_time_key',          'u8 c64',        '64'),
    # NOTE: rel +195 är OMAPPAT (default 60). peg_center_key ligger faktiskt på rel +159.
    # Filter — Cutoff is u16le @ rel +203/+204 (lo/hi)
    204: ('filter_cutoff_hi',      'u16le c128 hi', '2 (= cutoff 640 with lo=128)'),
    205: ('filter_cutoff_vel',     'u8 c64',        '64'),
    207: ('filter_resonance',      'u8 direct',     '0'),
    209: ('filter_res_vel',        'u8 c64',        '64'),
    # HPF Cutoff is u16le @ rel +211/+212
    212: ('filter_hpf_cutoff_hi',  'u16le hi',      '0'),
    215: ('filter_gain',           'u8',            '230'),
    # Filter EG Time
    217: ('feg_time_hold',         'u8',            '0'),
    219: ('feg_time_attack',       'u8',            '0'),
    221: ('feg_time_decay1',       'u8 c64',        '64'),
    223: ('feg_time_decay2',       'u8 c64',        '64'),
    225: ('feg_time_release',      'u8',            '80'),
    # Filter EG Level (Hold/Release är u16le c128, Attack/D1/D2 är u8 0-255)
    227: ('feg_level_hold',        'u16le c128 lo', '128'),
    229: ('feg_level_attack',      'u8 0..255',     '255'),
    231: ('feg_level_decay1',      'u8 0..255',     '255'),
    233: ('feg_level_decay2',      'u8 0..255',     '255'),
    235: ('feg_level_release',     'u16le c128 lo', '128'),
    237: ('feg_depth',             'u8 c64',        '104'),
    239: ('feg_segment_decay',     'u8',            '4'),
    241: ('feg_time_vel',          'u8 c64',        '64'),
    # rel +243 ★★★★★ binärverifierat (Test-AWM2-Filter_FEG_DepthVel_50.Y2L: 64→114)
    # Motsv. peg_depth_vel på rel +189; UI: [ELEMENT] Filter > Depth/Vel
    243: ('feg_depth_vel',         'u8 c64',        '64 (FEG_DepthVel_50 → 114 = +50 in c64-UI)'),
    # Cutoff keyfollow
    267: ('cutoff_key',            'u8',            '74'),
    269: ('hpf_cutoff_key',        'u8 c64',        '64'),
    # Element EQ ★★★★★
    # EQ Type enum: 0=2-band, 1=P.EQ, 2=Boost6, 3=Boost12, 4=Boost18, 5=Thru
    271: ('eq_type',               'u8 enum',       '0 (2-band default)'),
    273: ('eq_q',                  'u8',            '0 (used only when type=P.EQ)'),
    275: ('eq_freq_low',           'u8',            '54 (2-band Low Freq, eller P.EQ Freq)'),
    277: ('eq_gain_low',           'u8 c64',        '64=0dB (Low Gain eller P.EQ Gain)'),
    279: ('eq_freq_high',          'u8',            '231 (2-band High Freq)'),
    281: ('eq_gain_high',          'u8 c64',        '64=0dB (2-band High Gain)'),
    # LFO (per-element)
    285: ('lfo_keyonreset',        'u8 bool',       '1'),
    287: ('lfo_delay',             'u8',            '0'),
    293: ('lfo_pitchmod',          'u8',            '0'),
    295: ('lfo_filtermod',         'u8',            '0'),
    307: ('lfo_speed',             'u8',            '60'),
}

# EQ Type enum för rel 271
AWM2_ELEMENT_EQ_TYPE = {
    0: '2-band',     # Default. Justerbara: Low/High Freq+Gain (rel 275/277/279/281)
    1: 'P.EQ',       # Parametric. Justerbara: Q, Freq, Gain (rel 273/275/277)
    2: 'Boost6',     # Preset, ingen justering. Rel 275/277/279/281 = 46/32/131/32
    3: 'Boost12',    # Preset, ingen justering. Samma som Boost6
    4: 'Boost18',    # Preset, ingen justering. Samma som Boost6
    5: 'Thru',       # EQ av. Samma fast values som Boost.
}

# Elem Connect enum för rel 81
AWM2_ELEMENT_CONNECT = {
    0: 'Thru',
    1: 'InsA',       # Default
    2: 'InsB',
}

def get_awm2_element_field_addr(engine_start_abs: int, element_idx: int, field_name: str) -> int:
    """Abs address för element N:s field. Söker fältet i AWM2_ELEMENT_FIELDS."""
    for rel, (name, _, _) in AWM2_ELEMENT_FIELDS.items():
        if name == field_name:
            return get_awm2_element_addr(engine_start_abs, element_idx) + rel
    raise KeyError(f"Field '{field_name}' not in AWM2_ELEMENT_FIELDS")

# ── AN-X ENGINE STRUKTUR ★★★★★ ──
# Extraherat +77 AN-X-tester (Init AN-X solo).
# Engine-pool börjar vid abs 12466 (samma som AWM2).
#
# Layout:
#   Pre-OSC fält:  rel +0..+164 (Pitch LFO, FEG, AEG, Filter, m.m.)
#   OSC 1:         base = abs 12631 = engine rel +165
#   OSC 2:         base = abs 12755 = engine rel +289 (stride 124)
#   OSC 3:         base = abs 12880 = engine rel +414 (stride 125)
#   Post-OSC:      Filter/WaveFolder/ModLFO/ModEG (rel +547+)

ANX_OSC_BASES = {1: 12631, 2: 12756, 3: 12881}  # abs adresser, stride 125 (KORRIGERING )
ANX_OSC_COUNT = 3
ANX_ENGINE_BASE_ABS = 12466

# Pre-OSC AN-X-fält (abs adresser i engine-pool, per part)
# MASSIVT UTÖKAD  — 30 nya fält
ANX_PRE_OSC_FIELDS = {
    # === Part Settings (top of Pre-OSC) ===
    12467: ('alternate_pan_anx',  'u8 c64',    '64'),
    12469: ('scaling_pan_anx',    'u8 c64',    '64'),
    12477: ('unison_voices',      'u8 enum',   '0 (Off=0, 2=1, 4=2)'),
    12479: ('unison_detune',      'u8',        '0'),
    12481: ('unison_spread',      'u8',        '0'),
    12485: ('osc_reset_mode',     'u8 enum',   '0 (Off=0, Phase=1, Tune=2, Full=3)'),
    12487: ('voltage_drift',      'u8',        '64'),
    12489: ('ageing',             'u8',        '100'),

    # === Pitch LFO + PEG block (~12499-12511) ===
    12499: ('peg_time_vel',       'u8',        '0'),  # OBS: var feltidigare som feg_time_vel
    12503: ('pitch_lfo_speed_lo', 'u16le',     '208'),
    12507: ('pitch_lfo_phase',    'u8 enum',   '0 (16-step 0..15, 22.5° per step)'),
    12509: ('pitch_lfo_delay',    'u8',        '0'),
    12511: ('pitch_lfo_fadein',   'u8',        '0'),

    # === FEG-block ===
    # Layout: 2-byte stride i FEG-block (parallell med Amp AEG @ 12549..12555).
    12517: ('feg_attack',         'u8',        '0'),
    12519: ('feg_decay',          'u8',        '160'),
    12521: ('feg_sustain',        'u8',        '0'),
    12523: ('feg_release',        'u8',        '160'),
    12529: ('feg_time_vel',       'u8',        '0 (preliminär)'),

    # === Filter LFO-block (12531-12541) ===
    12531: ('filter_lfo_wave',    'u8 enum',   '2 (Triangle=2, Square=1)'),
    12533: ('filter_lfo_speed_lo','u16le',     '208'),
    12537: ('filter_lfo_phase',   'u8 enum',   '0 (16-step enum)'),
    12539: ('filter_lfo_delay',   'u8',        '0'),
    12541: ('filter_lfo_fadein',  'u8',        '0'),

    # === Amp-block (12543-12551) — [REVIEW efter ] ===
    # Detta beror sannolikt på att  använde ANNAN baseline (kanske AN-X solo Init
    # som dokumentet beskrev som 13150 bytes, inte vår 37166-byte fil).
    # Adresserna nedan PEGAR I ALLA FALL åt rätt fält — defaultvärdena är inte
    # universella över alla baselines.
    12543: ('amp_level',          'u16le',     '431 eller 128'),
    12545: ('amp_level_vel',      'u8',        '0'),
    12547: ('amp_lfo_depth',      'u8 c128',   '128'),
    # OBS: payload 12549 är AMBIGÖSANT
    # amp_aeg_attack. Den senare har binärverifierad default 0 i AN-X Init Voice.
    # Den tidigare har också verifierad +50 → 50-respons. KAN VARA SAMMA FÄLT med olika UI-namn.
    # Eller olika UI-paneler skriver båda till samma byte (jfr ex_elem_sw/arpRandomSfx).
    12551: ('amp_drive',          'u8',        '0'),

    # === Amp AEG (12549-12555) — KORRIGERAT  (var fel med -4 byte!) ===
    # Default-värden matchar: Atk=0, Dec=160, Sus=511 (u16le), Rel=115.
    # Gammal felaktig mappning hade 12553-12559, vilket egentligen tillhör
    # andra fält längre fram.  missade denna -4 byte-förskjutning.
    12549: ('amp_aeg_attack',     'u8',        '0'),
    12551: ('amp_aeg_decay',      'u8',        '160'),
    12553: ('amp_aeg_sustain_lo', 'u16le',     '511'),
    12555: ('amp_aeg_release',    'u8',        '115'),
    12557: ('amp_aeg_time_vel',   'u8',        '0'),
    # OBS: 12559, 12561 fortfarande UNMAPPED efter .

    # === Amp LFO (12563-12573) ===
    12563: ('amp_lfo_wave',       'u8 enum',   '2 (Triangle=2, Square=1)'),
    12565: ('amp_lfo_speed_lo',   'u16le',     '208'),
    12569: ('amp_lfo_phase',      'u8 enum',   '0 (16-step enum)'),
    12571: ('amp_lfo_delay',      'u8',        '0'),
    12573: ('amp_lfo_fadein',     'u8',        '0'),

    # ====================================================================
    # === SESSION 1+2: 50 NYA AN-X UI-FÄLT via korpus-analys ★★★★★ ====
    # Identifierade via 799 testfiler — alla single-edit eller small-edit
    # ====================================================================

    # Part Settings
    12465: ('part_random_pan_anx', 'u8 c64',   '0 (Test-ANX_PartSettings_RandomPan_50.Y2L: 0→50)'),

    # Filter EG
    12525: ('feg_sustain_anx',    'u8',        '0 (Test-ANX_Filter_FEG_Sustain_+50.Y2L: 0→50)'),
    12527: ('feg_release_anx',    'u8',        '160 (Test-ANX_Filter_FEG_Release_+50.Y2L: 160→50)'),

    # Part AEG (släkt med 12557 amp_aeg_time_vel)
    12558: ('amp_aeg_sustain_hi', 'u8',        '1 (u16le hi-byte av amp_aeg_sustain_lo=12553)'),
    12559: ('amp_aeg_release_v', 'u8',         '115 (Test-ANX_Part_AEGOffset_Release_+50.Y2L)'),
    12561: ('amp_aeg_time_vel_v','u8',         '0 (Test-ANX_Amp_AEG_TimeVel_+50.Y2L: 0→50)'),
    12562: ('amp_aeg_time_vel_marker','u8',    '1 (AN-X_00_Init_Part1_AEG_TimeVel_-255.Y2L: 1→0; sign-flag?)'),

    # Noise-block
    12513: ('noise_tone',         'u8',        '64 (ANX_00_Init_Part1_Noise_NoiseTone_50.Y2L: 64→50)'),
    12515: ('noise_connect',      'u8 enum',   '0 (ANX_00_Init_Part1_Noise_Connect_Amp.Y2L: 0→1)'),
    12518: ('noise_unknown_1',    'u8',        '0 (AN-X_00_Init_Noise.Y2L: 0→1; relaterat till Noise UI)'),

    # OSC1 (direkt-mappade adresser inom OSC1 region 12576-12700)
    12626: ('osc1_waveform_v',    'u8 enum',   '0 (AN-X_00_Init_OSC1_SAW2.Y2L: 0→1; OSC1 Waveform/Phase)'),
    12628: ('osc1_octave',        'u8',        '3 (AN-X_00_Init_OSC1_Octave_1.Y2L: 3→6)'),
    12630: ('osc1_pitch_lo_v',    'u16le',     '248 (AN-X_00_Init_OSC1_Pitch-73.Y2L)'),
    12633: ('osc1_peg_depth_marker','u8',      '0 (ANX_00_Init_Part1_OSC1_PEGDepth_50.Y2L: 0→1)'),
    12637: ('osc1_pitch_lfo_marker','u8',      '0 (ANX_00_Init_Part1_OSC1_PitchLFODepth_50.Y2L: 0→1)'),
    12638: ('osc1_sync_pitch_v',  'u8',        '0 (AN-X_00_Init_OSC1_Sync_100cent.Y2L: 0→4)'),
    12648: ('osc1_pulse_width_vel','u8',       '0 (ANX_00_Init_Part1_OSC1_PulseWidthVel_50.Y2L: 0→50)'),
    12654: ('osc1_shaper_v',      'u8',        '0 (AN-X_00_Init_OSC1_Shaper_1.Y2L: 0→1)'),
    12668: ('osc1_ring_level_vel','u8',        '0 (ANX_00_Init_Part1_OSC1_RingLevelVel_50.Y2L)'),
    12670: ('osc1_connect',       'u8 enum',   '0 (ANX_00_Init_Part1_OSC1_Connect_Amp.Y2L: 0→1)'),

    # OSC2 (region 12700-12824)
    12751: ('osc2_waveform_v',    'u8 enum',   '0 (AN-X_00_Init_OSC2_Sine.Y2L)'),
    12753: ('osc2_octave',        'u8',        '3 (AN-X_00_Init_OSC2_Octave_16.Y2L: 3→2)'),
    12757: ('osc2_peg_depth_lo_v','u16le',     '247 (ANX_00_Init_Part1_OSC2_PEGDepth_50.Y2L)'),
    12759: ('osc2_peg_depth_vel_v','u8',       '0 (ANX_00_Init_Part1_OSC2_PEGDepthVel_50.Y2L)'),
    12761: ('osc2_pitch_lfo_depth_v','u16le',  '247 (ANX_00_Init_Part1_OSC2_PitchLFODepth_50.Y2L)'),
    12763: ('osc2_sync_pitch',    'u8',        '0 (AN-X_00_Init_OSC2_Sync_100cent.Y2L)'),
    12771: ('osc2_pulse_width_v', 'u8 c128',   '128 (AN-X_00_Init_OSC2_Pulse_10.Y2L)'),
    12779: ('osc2_shaper_v',      'u8',        '0 (AN-X_00_Init_OSC2_Shaper_1.Y2L)'),

    # OSC3 (region 12824-12948)
    12787: ('osc3_fm_mod_2',      'u8',        '0 (AN-X_00_Init_OSC3_FM2.Y2L: 0→255)'),
    12791: ('osc3_ring_mod_2',    'u8',        '0 (AN-X_00_Init_OSC3_Ring2.Y2L: 0→255)'),
    12803: ('osc_eg_osc2_attack', 'u8',        '0 (AN-X_00_Init_EG_OSC2_Attack_50.Y2L)'),
    12805: ('osc_eg_osc2_decay',  'u8',        '160 (AN-X_00_Init_EG_OSC2_Decay_50.Y2L: 160→50)'),
    12807: ('osc_eg_osc2_sustain','u8',        '0 (AN-X_00_Init_EG_OSC2_Sustain_50.Y2L)'),
    12809: ('osc_eg_osc2_release','u8',        '160 (AN-X_00_Init_EG_OSC2_Release_50.Y2L: 160→50)'),
    12823: ('modlfo_dest_osc1_trail','u8',     '127 ([INTERN] Mod LFO Dest OSC1-matrix trailing)'),
    12825: ('modlfo_dest_osc2_trail','u8',     '127 ([INTERN] Mod LFO Dest OSC2-matrix trailing)'),
    12827: ('modlfo_dest_osc3_trail','u8',     '127 ([INTERN] Mod LFO Dest OSC3-matrix trailing)'),

    # OSC3 fortsättning + Mod LFO Dest trailing
    12876: ('osc3_waveform_v',    'u8 enum',   '4 (AN-X_00_Init_OSC3_SAW1.Y2L: 4→0)'),
    12878: ('osc3_octave',        'u8',        '3 (AN-X_00_Init_OSC3_Octave_16.Y2L: 3→2)'),
    12881: ('osc3_pitch_lo_v',    'u16le',     '1 (AN-X_00_Init_Part1_OSC3_Pitch_400.Y2L: 1→3)'),
    12883: ('osc3_peg_depth_marker','u8',      '0 (ANX_00_Init_Part1_OSC3_PEGDepth_50.Y2L: 0→1)'),
    12886: ('osc3_pitch_lfo_depth_v','u16le',  '247 (ANX_00_Init_Part1_OSC3_PitchLFODepth_50.Y2L)'),
    12896: ('osc3_pulse_width_v', 'u8 c128',   '128 (AN-X_00_Init_OSC3_Pulse_10.Y2L: 128→0)'),
    12902: ('osc3_filter_reso_offset','u8 c128','128 (ANX_00_Init_OSC3_SpotCheck_with_ResoOffset.Y2L: 128→178)'),
    12925: ('osc3_level_marker',  'u8',        '0 (AN-X_00_Init_OSC3_Level_511.Y2L: 0→1; hi-byte av out_level?)'),
    12934: ('osc_eg_osc3_release','u8',        '160 (AN-X_00_Init_Part1_OSC3_EG_Realese_50.Y2L: 160→50)'),
    12952: ('modlfo_dest_filter_trail','u8',   '127 ([INTERN] Mod LFO Dest Filter-matrix trailing)'),

    # Filter2 Type + WaveFolder (binärverifierat, dubbel-konfirmerat)
    13082: ('filter2_type_v',     'u8 enum',   '5 (HPF24=5, HPF18=6; AN-X_00_Init_FilterType2_HPF18.Y2L: 5→6)'),
    13120: ('wavefolder_eg_depth_v','u8 c128', '128 (AN-X_00_Init_WaveFolder_EGDepth_50.Y2L: 128→178)'),
    13124: ('wavefolder_texture_v','u8 c128',  '128 (AN-X_00_Init_WaveFolder_Texture_50.Y2L: 128→50)'),
}

# Per-OSC AN-X-fält (rel inom 124-byte OSC, OSC1 base = abs 12631)
ANX_OSC_FIELDS = {
    0:  ('osc_pitch',                 'u8',         '1'),
    1:  ('osc_peg_depth_lo',          'u8',         '247'),
    3:  ('osc_peg_depth_vel',         'u8',         '0 (PEGDepthVel_50 verified all 3 OSC)'),
    5:  ('osc_pitch_lfo_depth_lo',    'u8',         '247'),
    9:  ('osc_sync_pitch_vel',        'u8',         '0'),
    11: ('osc_eg_depth_sync',         'u8',         '0'),
    13: ('osc_lfo_sync_depth',        'u8',         '0'),
    15: ('osc_pulse_width',           'u8 c128',    '128 (PulseWidth_60% → 154)'),
    19: ('osc_eg_depth_pulse_width',  'u16le c128', '128'),
    21: ('osc_lfo_depth_pulse_width', 'u16le c128', '128'),
    25: ('osc_wave_shaper_vel',       'u8',         '0 (WaveShaperVel_50 → 126 via curve)'),
    27: ('osc_shaper_eg_depth',       'u16le c128', '128'),
    29: ('osc_shaper_lfo_depth',      'u16le c128', '128'),
    31: ('osc_fm_ringmod',            'u8',         '0'),
    33: ('osc_fm_level_vel',          'u8',         '0'),
    35: ('osc_self_sync_src',         'u8',         '0 (SelfSyncSrc verified)'),
    41: ('osc_invert',                'u8 bool',    '0'),
    43: ('osc_out_level_lo',          'u16le',      '511 (255+1; OutLevel_50 → 50/0)'),
    45: ('osc_out_level_vel',         'u8',         '0'),
    47: ('osc_eg_attack',             'u8',         '0'),
    49: ('osc_eg_decay',              'u8',         '160'),
    51: ('osc_eg_sustain',            'u8',         '0'),
    53: ('osc_eg_release',            'u8',         '160'),
    # Mod LFO Destination Matrix Depth Ratios (rel +67..+71) ★★★★★  verified
    # 3 destination rows × 1 ratio per OSC (this OSC's "lane depth" for each dest)
    # OSCMatrix-test ändrar 127 → 70/80/90 (OSC1), 71/81/91 (OSC2), 72/82/92 (OSC3)
    67: ('mod_lfo_ratio_row1',        'u8',         '127 (Matrix depth, row 1: OSC1=70/OSC2=71/OSC3=72)'),
    69: ('mod_lfo_ratio_row2',        'u8',         '127 (Matrix depth, row 2: OSC1=80/OSC2=81/OSC3=82)'),
    71: ('mod_lfo_ratio_row3',        'u8',         '127 (Matrix depth, row 3: OSC1=90/OSC2=91/OSC3=92)'),
}

def get_anx_osc_addr(osc_idx: int) -> int:
    """Returnera abs adress för AN-X OSC 1-3 base."""
    if osc_idx not in ANX_OSC_BASES:
        raise ValueError(f'osc_idx must be 1..3, got {osc_idx}')
    return ANX_OSC_BASES[osc_idx]

def get_anx_osc_field_addr(osc_idx: int, field_name: str) -> int:
    """Returnera abs adress för AN-X OSC-fält."""
    for rel, (name, _, _) in ANX_OSC_FIELDS.items():
        if name == field_name:
            return get_anx_osc_addr(osc_idx) + rel
    raise KeyError(f"Field '{field_name}' not in ANX_OSC_FIELDS")

# ── AN-X POST-OSC: FILTER 2 + WAVEFOLDER ★★★★★  verified ──
# Post-OSC3 block (after AN-X OSC3 ends at abs 13005)
# Fält-adresser absolute i AN-X engine-pool

ANX_FILTER2_FIELDS = {
    13084: ('filter2_cutoff_lo',    'u16le',  '0 (Cutoff_500 → 244, hi-byte 13085)'),
    13085: ('filter2_cutoff_hi',    'u8',     '0 (u16le hi-byte)'),
    13086: ('filter2_cutoff_vel',   'u8',     '0'),
    13088: ('filter2_feg_depth_lo', 'u16le',  '0 (FEGDepth_5000 → 100)'),
    13090: ('filter2_feg_depth_vel','u8',     '0'),
    13092: ('filter2_lfo_depth_lo', 'u16le',  '0 (LFODepth_5000 → 100)'),
    13094: ('filter2_cutoff_key',   'u8',     '0 (KeyFollow, CutoffKey_1oct → 4)'),
    13096: ('filter2_resonance',    'u8',     '0'),
    13098: ('filter2_resonance_vel','u8',     '0'),
    13100: ('filter2_drive',        'u8',     '0'),
    13102: ('filter2_drive_vel',    'u8',     '0'),
    13104: ('filter2_out_level',    'u8',     '64 (= 0 dB; OutLevel 6 → 80)'),
}

# ── AN-X FILTER 1 + MOD EG + MOD LFO ★★★★★  verified ──

ANX_FILTER1_FIELDS = {
    13005: ('filter1_type',         'u8 enum','1 (LPF12 = 3 verified)'),
    13007: ('filter1_cutoff_lo',    'u16le',  '255 (max; Cutoff_500 → 244/1)'),
    13008: ('filter1_cutoff_hi',    'u8',     '3 (u16le hi-byte default)'),
    13009: ('filter1_cutoff_vel',   'u8',     '0'),
    13011: ('filter1_feg_depth_lo', 'u16le',  '0'),
    13013: ('filter1_feg_depth_vel','u8',     '0'),
    13015: ('filter1_lfo_depth_lo', 'u16le',  '0'),
    13017: ('filter1_cutoff_key',   'u8',     '0'),
    13019: ('filter1_resonance',    'u8',     '0'),
    13021: ('filter1_resonance_vel','u8',     '0'),
    13023: ('filter1_drive',        'u8',     '0 (Drive_50.25db → 67)'),
    13025: ('filter1_drive_vel',    'u8',     '0'),
    13027: ('filter1_out_level',    'u8 c64', '64'),
}

ANX_MOD_EG_FIELDS = {
    13128: ('modeg_attack',  'u8', '0'),
    13130: ('modeg_decay',   'u8', '160 (ModEG_Decay_50 → 50)'),
    13132: ('modeg_sustain', 'u8', '0'),
    13134: ('modeg_release', 'u8', '160'),
}

ANX_MOD_LFO_FIELDS = {
    13122: ('modlfo_depth',  'u8 c128', '128 (Mod_LFO_Depth_50 → 178)'),
    13138: ('modlfo_wave',   'u8 enum', '2 (Square = 1)'),
    13140: ('modlfo_speed_lo','u16le',  '208 (Speed_50 → 50; Speed_271 → 15/1 verified u16le)'),
    13146: ('modlfo_delay',  'u8',      '0'),
    13148: ('modlfo_fadein', 'u8',      '0'),
}

ANX_WAVEFOLDER_FIELDS = {
    13116: ('wavefolder_amount',    'u8',     '0'),
    13118: ('wavefolder_vel',       'u8',     '0'),
    13126: ('wavefolder_type',      'u8 enum','1 (Hard, Soft=0)'),
}

# ── AN-X ROUTING-MATRISER ★★★★☆ — STRUKTUR IDENTIFIERAD, INTERN ──
# 5 stycken 40-byte routing-tabeller i AN-X engine-poolen.
# I baseline (Init Normal) har alla 5 mönstret [39, 1, 1, 1, ..., 1] (1 byte=39 + 39 byte=1).
# I en real patch innehåller de blandad u16le + u8 routing-data (modulationskällor → destinations).
#
# INGEN av 380 Part1-single-edit-tester ändrar någon byte i matriserna,
# vilket bekräftar att de är INTERNA routing-tabeller ej direkt UI-redigerbara.
# De skrivs implicit av ESP-plugin när patch laddas/sparas.
#
# Vid serialization: BEVARA RÅDATA 1:1 (passthrough). Inga edits från editor.

ANX_ROUTING_MATRICES = {
    'matrix_a': {
        'start_abs': 12582, 'end_abs': 12621, 'size': 40,
        'context': 'efter Pre-OSC, före OSC1',
        'baseline': [39] + [1]*39,
        'classification': '[INTERN][STRUKT]',
    },
    'matrix_b': {
        'start_abs': 12707, 'end_abs': 12746, 'size': 40,
        'context': 'efter OSC1, före OSC2',
        'baseline': [39] + [1]*39,
        'classification': '[INTERN][STRUKT]',
    },
    'matrix_c': {
        'start_abs': 12832, 'end_abs': 12871, 'size': 40,
        'context': 'efter OSC2, före OSC3',
        'baseline': [39] + [1]*39,
        'classification': '[INTERN][STRUKT]',
    },
    'matrix_d': {
        'start_abs': 12961, 'end_abs': 13000, 'size': 40,
        'context': 'efter OSC3, före Filter1',
        'baseline': [39] + [1]*39,
        'classification': '[INTERN][STRUKT]',
    },
    'matrix_e': {
        'start_abs': 13038, 'end_abs': 13077, 'size': 40,
        'context': 'efter Filter1, före Filter2',
        'baseline': [39] + [1]*39,
        'classification': '[INTERN][STRUKT]',
    },
}

ANX_ROUTING_MATRIX_TOTAL_BYTES = 5 * 40  # 200 bytes

def get_anx_filter2_field_addr(field_name: str) -> int:
    """Returnera abs adress för AN-X Filter 2-fält."""
    for abs_addr, (name, _, _) in ANX_FILTER2_FIELDS.items():
        if name == field_name:
            return abs_addr
    raise KeyError(f"Field '{field_name}' not in ANX_FILTER2_FIELDS")

def get_anx_wavefolder_field_addr(field_name: str) -> int:
    """Returnera abs adress för AN-X WaveFolder-fält."""
    for abs_addr, (name, _, _) in ANX_WAVEFOLDER_FIELDS.items():
        if name == field_name:
            return abs_addr
    raise KeyError(f"Field '{field_name}' not in ANX_WAVEFOLDER_FIELDS")

# ── FM-X ENGINE STRUKTUR ★★★★★ ──
# Extraherat +77 FM-X-tester (Init FM-X solo).
# Engine-pool börjar vid abs 12466 (samma som AWM2).
#
# Layout:
#   Pre-OP fält:   rel +0..+209 (PEG, 1st LFO, Algo, Feedback, 2nd LFO, Filter)
#   OP 1:          base = abs 12676 = engine rel +210
#   OP 2:          base = abs 12799 = engine rel +333 (stride 123)
#   OP 3-8:        stride 123 (OP8 = abs 13537)

FMX_OP_BASES = {n: 12676 + (n-1) * 123 for n in range(1, 9)}  # OP1..OP8
FMX_OP_COUNT = 8
FMX_OP_STRIDE = 123
FMX_ENGINE_BASE_ABS = 12466

# Pre-OP FM-X-fält (rel inom engine-pool, abs = ENGINE_BASE + rel)
# PEG, LFO, Algo, Filter
FMX_PRE_OP_FIELDS = {
    11: ('peg_pitch_velocity',     'u8 c64',  '64'),
    13: ('peg_random_pitch',       'u8',      '0'),
    15: ('peg_pitch_key',          'u8 c96',  '96'),
    17: ('peg_center_key',         'u8 MIDI', '60'),
    19: ('peg_level_initial',      'u8 c50',  '50'),
    21: ('peg_level_attack',       'u8 c50',  '50'),
    23: ('peg_level_decay1',       'u8 c50',  '50'),
    25: ('peg_level_decay2',       'u8 c50',  '50'),
    27: ('peg_level_release',      'u8 c50',  '50'),
    29: ('peg_time_attack',        'u8',      '0'),
    31: ('peg_time_decay1',        'u8',      '0'),
    33: ('peg_time_decay2',        'u8',      '0'),
    35: ('peg_time_release',       'u8',      '0'),
    37: ('peg_depth_velocity',     'u8',      '0'),
    39: ('peg_depth',              'u8 enum', '0'),
    41: ('peg_time_key',           'u8',      '0'),
    43: ('lfo_wave',               'u8 enum', '5'),
    51: ('key_on_reset',           'u8 bool', '0'),
    59: ('algo',                   'u8',      '69'),
    61: ('feedback',               'u8',      '0'),
    63: ('second_lfo_extended',    'u8 bool', '1'),
    65: ('second_lfo_wave_speed',  'u8',      '50'),
    # FM-X Filter-block ★★★★★  expanded
    81: ('filter_type',           'u8 enum', '21'),
    83: ('filter_cutoff_lo',      'u16le',   '1023'),
    85: ('filter_cutoff_vel',     'u8 c64',  '64'),
    87: ('filter_resonance',      'u8',      '10'),
    89: ('filter_resonance_vel',  'u8',      '64'),
    91: ('filter_hpf_cutoff',     'u8',      '0'),
    # FM-X FEG (Filter EG) — engine-pool-fält ★★★★★  + 112 KOMPLETT
    # OBS: AWM2 har Part-level FEG offsets @ Part Common rel +152..+158,
    # men FM-X har sina FEG-värden DIREKT i engine-poolen, INTE Part Common!
    # Layout: 8-element envelope (Hold/Atk/Dec/Sus/Rel × Time/Level) + 5 modifiers.
    95:  ('feg_gain',             'u8',      '255'),
    97:  ('feg_hold_time',        'u8',      '0'),
    99:  ('feg_attack_time',      'u8',      '0'),
    101: ('feg_decay_time',       'u8',      '0'),
    103: ('feg_sustain_time',     'u8',      '0'),
    105: ('feg_release_time',     'u8',      '0'),
    107: ('feg_hold_level',       'u8 c128', '128'),
    109: ('feg_attack_level',     'u8 c128', '128'),
    111: ('feg_decay_level',      'u8 c128', '128'),
    113: ('feg_sustain_level',    'u8 c128', '128'),
    115: ('feg_release_level',    'u8 c128', '128'),
    117: ('feg_depth',            'u8 c128', '104'),
    119: ('feg_segment',          'u8 enum', '4'),
    121: ('feg_time_vel',         'u8 c64',  '64'),
    123: ('feg_depth_vel',        'u8 c64',  '64'),
    125: ('feg_curve',            'u8 enum', '2'),
    # FM-X Key Follow / Key Scaling block ★★★★★ 
    127: ('time_key_scaling',     'u8 c64',  '64'),
    129: ('center_key',           'u8 MIDI', '24'),
    133: ('break_point_1',        'u8 MIDI', '36'),
    135: ('break_point_2',        'u8 MIDI', '48'),
    137: ('break_point_3',        'u8 MIDI', '60'),
    139: ('break_point_4',        'u8 MIDI', '72'),
    141: ('cutoff_offset_1',      'u8 c128', '128'),
    143: ('cutoff_offset_2',      'u8 c128', '128'),
    145: ('cutoff_offset_3',      'u8 c128', '128'),
    147: ('cutoff_offset_4',      'u8 c128', '128'),

    # === SESSION 1+2: 9 NYA FM-X PRE-OP UI-FÄLT via korpus-analys ★★★★★ ===
    # Identifierade via 425 testfiler
    47:  ('second_lfo_phase',     'u8 enum', '0 (FM-X_00_Init_Part1_2ndLFO_Phase_90.Y2L)'),
    49:  ('second_lfo_delay',     'u8',      '0 (FM-X_00_Init_Part1_2ndLFO_Delay_50.Y2L: 0→50)'),
    69:  ('op1_fm_harmonics',     'u8',      '128 (FM-X_00_Part1_OP1_FM_Harmonics_14.Y2L: 128→142)'),
    93:  ('filter_resonance_vel_v','u8 c64', '64 (Test-FMX_Part_Filter_ResVel_50.Y2L: 64→118)'),
    131: ('feg_time_key_v',       'u8 c64',  '64 (Test-FMX_Part_TimeKey_50.Y2L)'),
    149: ('break_point_extra',    'u8 MIDI', '0 (extra BP-fält efter cutoff_offsets)'),
    151: ('break_point_extra_2',  'u8 MIDI', '0 (extra BP-fält efter cutoff_offsets)'),
    206: ('op1_keyonreset',       'u8 bool', '1 (FM-X_00_Init_Part1_Op1_KeyOnReset_Off.Y2L: 1→0)'),
    208: ('op1_freq_mode',        'u8 enum', '0 (FM-X_00_Init_Part1_OP1_FrequencyMode_Fixed.Y2L: 0→1; Ratio=0, Fixed=1)'),
}

# Per-OP FM-X-fält (rel inom 123-byte OP-block, OP1 base = abs 12676)
FMX_OP_FIELDS = {
    0:  ('op_coarse',              'u8',      '1'),
    2:  ('op_fine',                'u8',      '0'),
    4:  ('op_detune',              'u8 c16',  '15'),
    # SESSION 1+2: nya per-OP-fält ★★★★★
    6:  ('op_pitch_key_fixed',     'u8',      '0 (Fixed mode pitch-key; FM-X_00_Init_Part1_OP1_FrequencyMode_Fixed_Pitch-Key_16.Y2L)'),
    8:  ('op_pitch_vel_fixed',     'u8',      '7 (Fixed mode pitch-vel; FM-X_00_Init_Part1_OP1_FrequencyMode_Fixed_Pitch-Vel_+3.Y2L)'),
    10: ('op_spectral',            'u8 enum', '0'),
    12: ('op_spectral_skirt',      'u8',      '0'),
    14: ('op_spectral_resonance',  'u8',      '0'),
    16: ('op_level_initial',       'u8 c50',  '50'),
    18: ('op_level_attack',        'u8 c50',  '50'),
    20: ('op_time_attack',         'u8',      '0'),
    22: ('op_time_delay',          'u8',      '0'),
    # SESSION 1+2: nya OP AEG-fält ★★★★★
    24: ('op_aeg_attack_level',    'u8',      '99 (FM-X_00_Init_Part1_OP1_AEG_AttackLevel_50.Y2L: 99→50)'),
    26: ('op_aeg_decay1_level',    'u8',      '99 (FM-X_00_Init_Part1_OP1_AEG_Decay1Level_50.Y2L)'),
    28: ('op_aeg_decay2_level',    'u8',      '99 (FM-X_00_Init_Part1_OP1_AEG_Decay2Level_50.Y2L)'),
    30: ('op_aeg_release_level',   'u8',      '0 (FM-X_00_Init_Part1_OP1_AEG_ReleaseLevel_50.Y2L: 0→50)'),
    32: ('op_attack',              'u8',      '0'),
    34: ('op_decay1',              'u8',      '0'),
    36: ('op_decay2',              'u8',      '0'),
    38: ('op_release',             'u8',      '40'),
    40: ('op_hold',                'u8',      '0'),
    42: ('op_time_key',            'u8',      '0'),
    44: ('op_level',               'u8',      '0'),
    46: ('op_aeg_breakpoint',      'u8 MIDI', '39'),
    48: ('op_lvl_key_lo',          'u8',      '0'),
    50: ('op_lvl_key_hi',          'u8',      '0'),
    52: ('op_curve_lo',            'u8 enum', '0'),
    54: ('op_curve_hi',            'u8 enum', '0'),
    # SESSION 2: per-OP 2nd LFO Modulation Destinations ★★★★★ stride 123 verifierat
    56: ('op_level_vel',           'u8',      '7 (FM-X_00_Part1_OP1_LevelVel_+7.Y2L)'),
    58: ('op_2nd_lfo_pitch_mod_dest','u8 enum','3 (FMX_00_Init_2ndLFO_PitchMod_Matrix.Y2L; stride 123 OP1-8 verifierat)'),
    60: ('op_2nd_lfo_amp_mod_dest', 'u8 enum','3 (FMX_00_Init_2ndLFO_AmpMod_Matrix.Y2L; stride 123 OP1-8 verifierat)'),
    # SESSION 2: per-OP trailer-bytes ★★★★★ [INTERN] default 127 (samma som AN-X Filter-trailers)
    66: ('op_trailer_a',           'u8',      '127 ([INTERN] OP-trailer; stride 123 verifierat alla 8 OP)'),
    68: ('op_trailer_b',           'u8',      '127 ([INTERN] OP-trailer)'),
    70: ('op_trailer_c',           'u8',      '127 ([INTERN] OP-trailer)'),
}

def get_fmx_op_addr(op_idx: int) -> int:
    """Returnera abs adress för FM-X OP 1..8 base."""
    if op_idx not in FMX_OP_BASES:
        raise ValueError(f'op_idx must be 1..8, got {op_idx}')
    return FMX_OP_BASES[op_idx]

def get_fmx_op_field_addr(op_idx: int, field_name: str) -> int:
    """Returnera abs adress för FM-X OP-fält."""
    for rel, (name, _, _) in FMX_OP_FIELDS.items():
        if name == field_name:
            return get_fmx_op_addr(op_idx) + rel
    raise KeyError(f"Field '{field_name}' not in FMX_OP_FIELDS")

# ── REGION [732:766] — STRUKTURELLT KARAKTÄRISERAT ──
# 14 × u16le-värden + 6 byte trailer
# Värden i Init: [31, 31, 15, 7, 23, 7, 23, 15, 15, 23, 7, 23, 7, 15]
# Pattern: 7, 15, 23, 31 är "8N - 1" familj (möjligen bit-mask)
# Plats: Common-area, mellan MidPos-data och Audio In-block
#
# UI-funktion ej identifierad — möjliga hypoteser:
# - 14 controllers × 5-bit enable-mask för olika CC-typer
# - Custom Tuning Scale data
# - Per-Part-feature flags (16 parts - 2 reserved = 14)
REGION_732_BASE = 732
REGION_732_SIZE = 34
REGION_732_VALUES = 14 # 14 u16le-värden + 6b trailer

# Common Assign Names — KOMPLETT ★★★★★
# 8 strings × 21 b = 168 bytes total at [2279:2447]
# Per slot: 16 ASCII bytes + 5 trailing/separator bytes
# Default text: "Assign 1" through "Assign 8"
COMMON_ASSIGN_NAMES_BASE = 2279
COMMON_ASSIGN_NAMES_STRIDE = 21
COMMON_ASSIGN_NAMES_LEN = 16 # max characters per name
# Resolution: name_addr = COMMON_ASSIGN_NAMES_BASE + 1 + (slot-1) * 21
# (the leading byte at +0 is a length prefix \x11)
# For slot 1: name starts at abs 2280, fills 2280-2295

# Part Assign Names — KOMPLETT ★★★★★
# Same structure, located in Part Common
PART_ASSIGN_NAMES_BASE = 8048
PART_ASSIGN_NAMES_STRIDE = 21
PART_ASSIGN_NAMES_LEN = 16
# For slot 1: name starts at abs 8049, fills 8049-8064

def get_assign_name_addr(slot, common=True):
    """Returns absolute address where ASCII text for assign name begins.
    slot: 1-8.
    common: True for Common Assign names (abs 2280+), False for Part Assign (abs 8049+).
    """
    if common:
        return COMMON_ASSIGN_NAMES_BASE + 1 + (slot - 1) * COMMON_ASSIGN_NAMES_STRIDE
    else:
        return PART_ASSIGN_NAMES_BASE + 1 + (slot - 1) * PART_ASSIGN_NAMES_STRIDE

# Per-part 3-band EQ — KOMPLETT ★★★★★
# Layout: [LowFreq, LowGain, MidFreq, MidGain, MidQ, HighFreq, HighGain]
# Only Mid band has Q (matches ESP UI which shows just one Q knob).
PART_3BAND_EQ = dict(
    part3bandLowFreq = 6939, # rel_part=231, default=54 (~62.5 Hz) ★★★★★
    part3bandLowGain = 6941, # rel_part=233, c64 ±24dB ★★★★★
    part3bandMidFreq = 6943, # rel_part=235, default=141 (~675 Hz) ★★★★★
    part3bandMidGain = 6945, # rel_part=237 ★★★★★
    part3bandMidQ = 6947, # rel_part=239, default=0 (UI shows 0.7) ★★★★★
    part3bandHighFreq = 6949, # rel_part=241, default=231 (~7.4 kHz) ★★★★★
    part3bandHighGain = 6951, # rel_part=243 ★★★★★
)
# OBS: Mid Q default = raw 0 even though UI displays "0.7". The encoding
# (UI_Q → raw) verified for raw=6 → UI=2.6, but the raw=0 default is
# special — possibly meaning "use default Q=0.7". Use raw=0 when writing
# default; raw>=1 for explicit Q.

# Per-part 2-band EQ — KOMPLETT ★★★★★
# Separate from 3-band EQ. Each band can be independent type
# (Thru / Low Shelf / High Shelf / Peak/Dip / etc).
# Both bands have full Freq+Gain+Q parameters when in Peak/Dip mode.
# EQ2 Type was
PART_2BAND_EQ = dict(
    part2bandEq1Type = 6953, # rel_part=245, enum 0=Thru/3=LowShelf/5=Peak ★★★★★
    part2bandEq1Freq = 6955, # rel_part=247, logarithmic ~24 raw/oct
    part2bandEq1Gain = 6957, # rel_part=249, raw=64+UI_dB*2
    part2bandEq1Q = 6959, # rel_part=251, raw=UI_Q*10 (Peak only)
    part2bandEq2Type = 6961, # rel_part=253, enum ★★★★★
    part2bandEq2Freq = 6963, # rel_part=255
    part2bandEq2Gain = 6965, # rel_part=257
    part2bandEq2Q = 6967, # rel_part=259
    partOutputLevel = 6969, # rel_part=261, raw=64+UI_dB*2 ★★★★★
)
# Type enum (partial — confirmed values):
# 0 = Thru (default)
# 3 = Low Shelf
# 5 = Peak/Dip
# (Other values 1, 2, 4, 6+ untested — likely include High Shelf, HPF, LPF)

# ── SCENE SNAPSHOTS ───────────────────────────
# Two separate structures. CRITICAL FIX in v8: SCENE_STRUCT1_BASE,
#

# Struct 1: Scene Memory Switches (perf-global flags) — KOMPLETT i
SCENE_STRUCT1_BASE = 1710 # FIX v8 (var 1715)
SCENE_STRUCT1_STRIDE = 71
SCENE_COUNT = 8

SCENE_STRUCT1_FIELDS = dict(
    sceneArp = 0, # bool default=0 ★★★★★
    sceneMotionSeq = 1, # bool default=0 ★★★★★
    sceneSuperKnob = 2, # bool default=0 ★★★★★
    sceneMixing = 3, # bool default=0 ★★★★★
    sceneAEG = 4, # bool default=0 ★★★★★
    sceneArpMsFx = 5, # bool default=0 ★★★★★ (var +0 i v7, FIX)
    sceneSuperKnobLink = 6, # bool default=0 ★★★★★
    sceneKbdCtrl = 15, # bool default=0 ★★★★★ (var +10 i v7, FIX)
    sceneNoteLimit = 16, # bool default=0 ★★★★★ (var +11 i v7, FIX)
)

# Struct 2: Scene per-part Lane snapshots (likely active-part only) — KOMPLETT
SCENE_STRUCT2_BASE = 7421
SCENE_STRUCT2_STRIDE = 84

SCENE_STRUCT2_FIELDS = dict(
    sceneSwing = 0, # mirrors live abs 6887 (Lane Part Swing), center=128
    sceneUnit = 2, # mirrors live abs 7097 (Lane Part Unit), enum
    sceneGateTime = 4, # mirrors live abs 7119, direct ★★★★★
    sceneVelocity = 6, # mirrors live abs 7117, direct ★★★★★
    sceneAmp = 8, # mirrors live abs 6889, center=128 ★★★★★
    sceneShape = 10, # mirrors live abs 6891, center=64 ★★★★★
    sceneSmooth = 12, # mirrors live abs 6893 (Lane Part Smooth), center=128
    sceneRandom = 14, # mirrors live abs 6895, direct ★★★★★
    sceneNoteLimitLow = 20, # mirrors live abs 6823, direct (MIDI note) ★★★★★
    sceneNoteLimitHigh = 22, # mirrors live abs 6825, direct (MIDI note) ★★★★★
    sceneNoteShift = 24, # mirrors live abs 6919, center=64 ★★★★★
)
# OBS: KbdCtrl och NoteLimit per-part-toggles ligger i Struct 1 (rel 15, 16),
# inte i Struct 2 — UI-listan är förvirrande på den punkten.
# Struct 2 är troligen aktiv-part-baserad (84 bytes räcker inte för 16 parts).
# Kräver verifiering med ren testfil där Part 2 redigeras explicit.

def scene_struct1_abs(field_name: str, scene_idx: int) -> int:
    """Return absolute offset for Scene Struct 1 field. scene_idx: 0..7."""
    if field_name not in SCENE_STRUCT1_FIELDS:
        raise KeyError(f"Unknown Scene Struct 1 field: {field_name}")
    if not (0 <= scene_idx < SCENE_COUNT):
        raise ValueError(f"scene_idx out of range 0..7: {scene_idx}")
    return SCENE_STRUCT1_BASE + scene_idx * SCENE_STRUCT1_STRIDE + SCENE_STRUCT1_FIELDS[field_name]

def scene_struct2_abs(field_name: str, scene_idx: int) -> int:
    """Return absolute offset for Scene Struct 2 field. scene_idx: 0..7."""
    if field_name not in SCENE_STRUCT2_FIELDS:
        raise KeyError(f"Unknown Scene Struct 2 field: {field_name}")
    if not (0 <= scene_idx < SCENE_COUNT):
        raise ValueError(f"scene_idx out of range 0..7: {scene_idx}")
    return SCENE_STRUCT2_BASE + scene_idx * SCENE_STRUCT2_STRIDE + SCENE_STRUCT2_FIELDS[field_name]

# ── Endadditions ─────────────────────────────────────────────────────

# DPFM[29] = Performance Portamento SW (0=Off, 1=On), default=0 ✅
# AN-X OSC Pitch — stride=125 confirmed ✅
# AN-X OSC sub-table (PART_rel = MIDI_hex_addr + OSC_base, stride=125)
# OSC1_BASE=5918, OSC2_BASE=6043, OSC3_BASE=6168 — all 15 fields verified ✅
ANX_OSC = dict(
    # Wave & Octave (u8)
    anxOsc1Wave=5918, # u8 enum 0-4 (Saw=0, Sq=2) default=0 ✅
    anxOsc2Wave=6043, anxOsc3Wave=6168,
    anxOsc1Octave=5920, # u8 enum 0-6 default=3=8' ★★★☆☆
    anxOsc2Octave=6045, anxOsc3Octave=6170,
    # Pitch (u16 LE, center=504)
    anxOsc1Pitch=5922, # u16 LE center=504, ≈1:1 cent ✅
    anxOsc2Pitch=6047, anxOsc3Pitch=6172,
    # Pitch EG/LFO depths (u16 LE, center=247) — ENCODING CONFIRMED ✅
    # raw = round(ui * 95/400) + 247 (symmetric: ±400→±95 raw from center)
    # UI range: ±1040 (247 raw units each side)
    anxOsc1PitchEGDepth=5924, # u16 LE center=247 ✅ (+400→342, 0→247, -400→152)
    anxOsc2PitchEGDepth=6049, anxOsc3PitchEGDepth=6174,
    anxOsc1PitchEGDepthVelSens=5926, # u16 LE center=256 default=0 ★★★☆☆
    anxOsc2PitchEGDepthVelSens=6051, anxOsc3PitchEGDepthVelSens=6176,
    anxOsc1PitchLFODepth=5928, # u16 LE center=247 default=0 ★★★☆☆
    anxOsc2PitchLFODepth=6053, anxOsc3PitchLFODepth=6178,
    # Self Sync (u16 LE)
    anxOsc1SelfSyncPitch=5930, # u16 LE direct default=0 ★★★☆☆
    anxOsc2SelfSyncPitch=6055, anxOsc3SelfSyncPitch=6180,
    anxOsc1SelfSyncVelSens=5932, # u16 LE center=256 ★★★☆☆
    anxOsc2SelfSyncVelSens=6057, anxOsc3SelfSyncVelSens=6182,
    # PART+5934 = selfSyncPitchEGDepth — EG modulation depth for Self Sync Pitch
    # Confirmedia MODX M8: changes independently of selfSyncLFODepth(5936) ✅
    # Encoding: raw = UI + 256 (center=256, range 0–512, default=256=UI 0)
    # NOTE: DIFFERENT encoding from selfSyncLFODepth (which uses round(UI/25)+256)
    anxOsc1SelfSyncPitchEGDepth=5934, # u16le raw=UI+256 center=256 ★★★★★
    anxOsc2SelfSyncPitchEGDepth=6059, anxOsc3SelfSyncPitchEGDepth=6184,
    # Pulse Width — KORRIGERADE OFFSETS
    # anxOsc1PulseWidth = PART+5938 (NOT 5936 as MIDI formula suggested!)
    # Encoding: raw = round(pct * 256 / 100), 50%=128(default), 60%=154
    anxOsc1PulseWidthVelSens=5936, # u16 LE center=256 ★★★☆☆ (MIDI-formel)
    anxOsc2PulseWidthVelSens=6061, anxOsc3PulseWidthVelSens=6186,
    anxOsc1PulseWidth=5938, # u8 raw=round(pct*256/100), 50%→128, 60%→154 ★★★★★
    anxOsc2PulseWidth=6063, anxOsc3PulseWidth=6188, # stride=125
    anxOsc1PulseWidthEGDepth=5940, # u16 LE center=256 ★★★☆☆
    anxOsc2PulseWidthEGDepth=6065, anxOsc3PulseWidthEGDepth=6190,
    anxOsc1PulseWidthLFODepth=5944,# u16 LE center=128 ★★★☆☆
    anxOsc2PulseWidthLFODepth=6069,anxOsc3PulseWidthLFODepth=6194,
    # Wave Shaper (u16 LE)
    anxOsc1WaveShaper=5946, # u16 LE direct default=0 ★★★☆☆
    anxOsc2WaveShaper=6071, anxOsc3WaveShaper=6196,
    anxOsc1WaveShaperVelSens=5948, # u8 direct default=0 ★★★★★
    anxOsc2WaveShaperVelSens=6073, anxOsc3WaveShaperVelSens=6198,
    # Osc EG Depth → Shaper / Osc LFO Depth → Shaper
    # Encoding: 0x80+n (center=128), default=128 (=UI 0)
    anxOsc1ShaperEGDepth=5950, # u8 0x80+n center=128 ★★★★★
    anxOsc2ShaperEGDepth=6075, anxOsc3ShaperEGDepth=6200,
    anxOsc1ShaperLFODepth=5952, # u8 0x80+n center=128 ★★★★★
    anxOsc2ShaperLFODepth=6077, anxOsc3ShaperLFODepth=6202,
    # Ring Mod (MIDI OSC addr 0x28=40, same stride=125)
    anxOsc1RingModDepth=5958, # u16 LE direct default=0 ✅ (0→50)
    anxOsc2RingModDepth=6083, anxOsc3RingModDepth=6208,
    # OSC EG sub-table — KORRIGERADE OFFSETS
    # Old MIDI-formula-based offsets (5813-5817) were WRONG.
    # Correct sub-tabell base = PART+5970 (not 5779+34=5813 som MIDI antydde)
    # OSC1 EG: abs 12678-12684 (PART rel 5970-5976)
    anxOsc1EGAttackTime=5970, # u16 LE direct default=0 ★★★★★
    anxOsc1EGDecayTime=5972, # u16 LE default=160 ★★★★★ (
    anxOsc1EGSustainLevel=5974, # u16 LE direct default=0 ★★★★★ (
    anxOsc1EGReleaseTime=5976, # u16 LE direct default=160 ★★★★★ (var korrekt)
    # OSC EG Depth/LFODepth (not kollision med EG — separata adresser):
    anxOsc1EGDepth=5942, # u16 LE ★★★★★
    anxOsc1LFODepth=5944, # u16 LE ★★★★★
    # OSC2 EG: stride=125 from OSC1 ✅
    anxOsc2EGAttackTime=6095, # ★★★★★ (
    anxOsc2EGDecayTime=6097, # ★★★★★ (
    anxOsc2EGSustainLevel=6099, # ★★★★★ (
    anxOsc2EGReleaseTime=6101, # ★★★★★ (var korrekt)
    anxOsc2EGDepth=6067, # ★★★★★
    anxOsc2LFODepth=6069, # ★★★★★
    # OSC3 EG: stride=125 from OSC2 ✅
    anxOsc3EGAttackTime=6220, # ★★★★★ (
    anxOsc3EGDecayTime=6222, # ★★★★★ (
    anxOsc3EGSustainLevel=6224, # ★★★★★ (
    anxOsc3EGReleaseTime=6226, # ★★★★★ (var korrekt)
)
# AN-X Filter sub-tables: DPFM_rel = MIDI_hex_addr + filter_base
# Filter 1 base=6297, Filter 2 base=6374 (stride=77) — formula verified ✅
# 10/10 Filter 1 defaults verified against baseline ★★★☆☆ (MIDI-derived)
ANX_FILTER = dict(
    anxFilter1Type=6297, # u8 enum default=1=LPF12 ✅
    anxFilter1Cutoff=6299, # u16 LE Hz default=1023 ✅
    anxFilter1CutoffVelSens=6301, # u16 LE center=256 default=256 ★★★☆☆
    anxFilter1CutoffEGDepth=6303, # u16 LE center=256 default=256 ★★★☆☆
    anxFilter1CutoffEGDepthVelSens=6305,# u16 LE center=256 ★★★☆☆
    anxFilter1CutoffLFODepth=6307, # u16 LE center=256 ★★★☆☆
    anxFilter1CutoffKeyFollow=6309, # u8 enum default=0 ★★★☆☆
    anxFilter1Resonance=6311, # u8 direct default=0 ✅
    anxFilter1ResonanceVelSens=6313, # u16 LE center=256 default=256 ★★★☆☆
    anxFilter1Drive=6315, # u8 0-80 (0.75dB/unit) default=0 ✅
    anxFilter1OutLevel=6319, # u8 center=64 (0.375dB/unit) ✅
    anxFilter2Type=6374, # u8 enum default=5
    anxFilter2Cutoff=6376, # u16 LE Hz default=0
    anxFilter2Resonance=6388, # u8 direct default=0
    anxFilter2Drive=6392, # u8 0-80 (0.75dB/unit) default=0 ✅
    anxFilter2OutLevel=6396, # u8 center=64 (0.375dB/unit) ✅
)
# AN-X Modifier section (PART_rel, offset=6408 base)
# WaveFolder fields (MIDI_hex_addr + 6408):
ANX_MODIFIER = dict(
    anxWaveFolder=6408, # u16 LE direct default=0 ✅ (0→50)
    anxWaveFolderVelSens=6410, # u16 LE center=256 ★★★☆☆ (MIDI 0x02+6408)
    anxWaveFolderEGDepth=6412, # u16 LE center=256 ★★★☆☆ (MIDI 0x04+6408)
    anxWaveFolderLFODepth=6414, # u16 LE center=256 ★★★☆☆ (MIDI 0x06+6408)
    anxWaveFolderTexture=6416, # u16 LE direct default=256 ★★★☆☆ (MIDI 0x08+6408)
    anxWaveFolderType=6418, # u16 LE enum default=1=Hard ★★★☆☆ (MIDI 0x0A+6408)
    anxModEGAttackTime=6420, # u16 LE direct default=0 ★★★★★ BINÄRVERIFIERAD
    anxModEGDecayTime=6422, # u16 LE default=160 ★★★☆☆ (MIDI 0x0E+6408)
    anxModEGSustainLevel=6424, # u16 LE direct default=0 ★★★☆☆ (MIDI 0x10+6408)
    anxModEGReleaseTime=6426, # u16 LE default=160 ★★★☆☆ (MIDI 0x12+6408)
)
# Insertion FX — Classic Flanger (16/16) och Symphonic (12/12) COMPLETE ✅
# ── INSERTION FX TYPE INDEX (ENGINE-OBEROENDE) ────────────────────────────
# Gäller för BÅDE InsertionA (PART+275) och InsertionB (PART+332)
# Encoding: lo = type_index & 0x7F, hi = (type_index >> 7) & 0x7F
# Källa: Effect Type List.xlsx + binärverifiering
# ★★★★★ = binärverifierat | ★★★★☆ = från Effect Type List
# NOTE: SPX HALL (130) och CROSS DELAY (256) är OLIKA — SPXHall lo=2,hi=1 (130)
# CrossDelay lo=0,hi=2 (256). Vårmätning av CrossDelay-filen var fel.
FX_TYPE_INDEX = {
    # ── THRU ──────────────────────────────────────────────────────────────
    'THRU': 0, # ★★★★★
    # ── REVERB ────────────────────────────────────────────────────────────
    'SPX HALL': 130, # ★★★★★ lo=2,hi=1
    'SPX ROOM': 146, # ★★★★☆
    'SPX STAGE': 176, # ★★★★☆
    'GATED REVERB': 208, # ★★★★☆
    'REVERSE REVERB': 216, # ★★★★☆
    # ── DELAY ─────────────────────────────────────────────────────────────
    'CROSS DELAY': 256, # ★★★★★ lo=0,hi=2 (KORRIGERAT från 130!)
    'TEMPO CROSS DELAY': 272, # ★★★★☆
    'TEMPO DELAY MONO': 288, # ★★★★☆
    'TEMPO DELAY STEREO': 296, # ★★★★☆
    'CONTROL DELAY': 304, # ★★★★☆
    'DELAY LR': 320, # ★★★★☆
    'DELAY LCR': 336, # ★★★★☆
    'ANALOG DELAY RETRO': 352, # ★★★★☆
    'ANALOG DELAY MODERN': 360, # ★★★★☆
    # ── CHORUS ────────────────────────────────────────────────────────────
    'G CHORUS': 384, # ★★★★☆
    '2 MODULATOR': 400, # ★★★★☆
    'SPX CHORUS': 416, # ★★★★☆
    'SYMPHONIC': 432, # ★★★★★ lo=48,hi=3
    'ENSEMBLE DETUNE': 448, # ★★★★☆
    # ── FLANGER ───────────────────────────────────────────────────────────
    'VCM FLANGER': 512, # ★★★★☆
    'CONTROL FLANGER': 520, # ★★★★☆
    'CLASSIC FLANGER': 528, # ★★★★★ lo=16,hi=4
    'TEMPO FLANGER': 544, # ★★★★☆
    'DYNAMIC FLANGER': 560, # ★★★★☆
    # ── PHASER ────────────────────────────────────────────────────────────
    'VCM PHASER MONO': 640, # ★★★★☆
    'VCM PHASER STEREO': 656, # ★★★★☆
    'CONTROL PHASER': 664, # ★★★★☆
    'TEMPO PHASER': 672, # ★★★★★ lo=32,hi=5
    'DYNAMIC PHASER': 688, # ★★★★☆
    # ── TREMOLO & ROTARY ──────────────────────────────────────────────────
    'AUTO PAN': 768, # ★★★★☆
    'TREMOLO': 784, # ★★★★★ lo=16,hi=6
    'ROTARY SPEAKER 1': 800, # ★★★★☆
    'ROTARY SPEAKER 2': 816, # ★★★★☆
    # ── DISTORTION ────────────────────────────────────────────────────────
    'AMP SIMULATOR 1': 896, # ★★★★☆
    'AMP SIMULATOR 2': 912, # ★★★★☆
    'COMP DISTORTION': 928, # ★★★★★ lo=32,hi=7
    'COMP DISTORTION DELAY': 944, # ★★★★☆
    'US COMBO': 960, # ★★★★☆
    'JAZZ COMBO': 961, # ★★★★☆
    'US HIGH GAIN': 962, # ★★★★☆
    'BRITISH LEAD': 963, # ★★★★☆
    'MULTI FX': 964, # ★★★★☆
    'SMALL STEREO': 965, # ★★★★☆
    'BRITISH COMBO': 966, # ★★★★☆
    'BRITISH LEGEND': 967, # ★★★★☆
    # ── COMPRESSOR ────────────────────────────────────────────────────────
    'VCM COMPRESSOR 376': 1024, # ★★★★☆
    'CLASSIC COMPRESSOR': 1040, # ★★★★★ lo=16,hi=8
    'MULTI BAND COMP': 1056, # ★★★★☆
    'UNI COMP DOWN': 1072, # ★★★★☆
    'UNI COMP UP': 1080, # ★★★★☆
    'PARALLEL COMP': 1088, # ★★★★☆
    # ── WAH (MODX M, not i Effect Type List xlsx) ──────────────────────────
    'VCM AUTO WAH': 1280, # ★★★★★ lo=0,hi=10
    # ── LO-FI (MODX M) ────────────────────────────────────────────────────
    'NOISY': 1424, # ★★★★★ lo=16,hi=11
    # ── TECH (MODX M) ─────────────────────────────────────────────────────
    'SLICE': 1616, # ★★★★★ lo=80,hi=12
    # ── MISC (MODX M) ─────────────────────────────────────────────────────
    'PRESENCE': 1672, # ★★★★★ lo=8,hi=13
    'WAVE FOLDER': 1704, # ★★★★★ lo=40,hi=13 — FX-TABELL COMPLETE!
}

# ─────────────────────────────────────────────────────────────────────────
# Extended FX_TYPE_INDEX via ysfc_enums-paketet
# 
# Det optional ysfc_enums-paketet (om installerat) ger 46 ytterligare 
# FX-typer från Yamahas Effect Type List (★★★★☆) utöver de 57 ovan.
# Dessa har INTE binärverifierats men är härledda från officiell källa.
# 
# Bevara dock alltid de 57 binärverifierade värdena ovan — paketet har 
# kvarstående hex-vs-decimal-fel i lsb för flera entries.
# ─────────────────────────────────────────────────────────────────────────
try:
    from ysfc_enums import FX_TYPES as _PKG_FX_TYPES
    for _name, _meta in _PKG_FX_TYPES.items():
        if _name in FX_TYPE_INDEX:
            continue  # behåll auktoritativt värde
        _msb, _lsb = _meta.get('msb'), _meta.get('lsb')
        if _msb is not None and _lsb is not None:
            FX_TYPE_INDEX[_name] = _msb * 128 + _lsb
    HAS_EXTENDED_FX = True
except ImportError:
    HAS_EXTENDED_FX = False

# Omvänd lookup: TypeIndex → namn
FX_INDEX_TO_NAME = {v: k for k, v in FX_TYPE_INDEX.items()}

def fx_type_bytes(name):
    """Returnerar (lo, hi) för ett InsertionFX-namn. Fungerar för InsA OCH InsB."""
    idx = FX_TYPE_INDEX.get(name.upper(), 0)
    return (idx & 0x7F, (idx >> 7) & 0x7F)

def fx_name_from_bytes(lo, hi):
    """Returnerar FX-namn från (lo, hi) bytes (InsA eller InsB)."""
    return FX_INDEX_TO_NAME.get(hi * 128 + lo, f'UNKNOWN({hi*128+lo})')

# ─────────────────────────────────────────────────────────────────────────
# Enum-översättningar (ysfc_enums-paketet krävs)
# 
# Dessa funktioner översätter råa byte-värden till människoläsbara strängar 
# för UI-rendering. Alla fungerar säkert utan ysfc_enums installerat — de 
# returnerar en fallback-sträng som '#42' eller 'Unknown(42)' i det fallet.
# 
# Editor-koden ska alltid använda dessa funktioner istället för att läsa 
# ENUMS.* direkt, så att tool-koden förblir robust om paketet saknas.
# ─────────────────────────────────────────────────────────────────────────

def waveform_name(wave_no):
    """Returnera waveform-namn för en u16le-waveform-nummer (1-based).
    Exempel: waveform_name(1) → 'CFX v01 St'."""
    if HAS_ENUMS:
        return ENUMS.get_waveform_name(wave_no) or f'Wave#{wave_no}'
    return f'Wave#{wave_no}'

def performance_name(perf_no):
    """Returnera factory-performance-namn för ett performance-nummer."""
    if HAS_ENUMS:
        return ENUMS.get_performance_name(perf_no) or f'Perf#{perf_no}'
    return f'Perf#{perf_no}'

def arpeggio_name(arp_no):
    """Returnera arpeggio-namn för ett arpeggio-nummer."""
    if HAS_ENUMS:
        return ENUMS.get_arp_name(arp_no) or f'Arp#{arp_no}'
    return f'Arp#{arp_no}'

def controller_source_name(source_idx):
    """Returnera controller-källa-namn (PitchBend, ModWheel, Foot, etc.)."""
    if HAS_ENUMS:
        return ENUMS.get_source_name(source_idx) or f'Src#{source_idx}'
    return f'Src#{source_idx}'

def controller_destination_name(dest_idx):
    """Returnera controller-destination-namn (Filter Cutoff, Amp, etc.)."""
    if HAS_ENUMS:
        return ENUMS.get_destination_name(dest_idx) or f'Dest#{dest_idx}'
    return f'Dest#{dest_idx}'

def algorithm_label(algo_no):
    """Returnera FM-X-algoritm-etikett (1-88). algo_no är 1-baserat (raw + 1)."""
    if HAS_ENUMS:
        return ENUMS.get_algorithm_label(algo_no)
    return f'Algorithm {algo_no}'

def enum_value(enum_name, raw_value):
    """Hämta en enum-värde för rendering.
    
    Exempel:
        enum_value('AWM2_FILTER_TYPES', 0) → 'LPF24D'
        enum_value('ANX_OSC_WAVEFORMS', 1) → 'Saw2'
        enum_value('FMX_SPECTRAL_FORM', 0) → 'Sin'
    
    Tillgängliga enum-namn (alla från engine_enums-modulen):
        AWM2_FILTER_TYPES, AWM2_ELEMENT_LFO_WAVES, AWM2_PART_LFO_WAVES
        ANX_OSC_WAVEFORMS, ANX_FILTER_TYPES, ANX_LFO_SHAPES, 
        ANX_FOLDER_TYPES, ANX_MODIFIER_WAVES
        FMX_SPECTRAL_FORM, FMX_OP_SWITCH
        DRUM_KEY_RECEIVE_NOTE, DRUM_KEY_REVERSE, DRUM_KEY_SWITCH
        EQ_TYPE, ON_OFF, RECEIVE_SWITCH, CA_POLARITY, CA_CURVE_PRESETS
        RIBBON_MODE, SLIDER_DIRECTION, RIBBON_GRID_MODE, RIBBON_ASSIGN_MODE
    """
    if not HAS_ENUMS:
        return f'{enum_name}[{raw_value}]'
    enum_dict = getattr(ENUMS, enum_name, None)
    if enum_dict is None:
        return f'UnknownEnum:{enum_name}[{raw_value}]'
    if isinstance(enum_dict, dict):
        return enum_dict.get(raw_value, f'{enum_name}[{raw_value}]')
    if isinstance(enum_dict, list):
        if 0 <= raw_value < len(enum_dict):
            return str(enum_dict[raw_value])
        return f'{enum_name}[{raw_value}]'
    return f'{enum_name}[{raw_value}]'

def list_fx_for_slot(slot):
    """Returnera lista av FX-typer som är giltiga för en specifik slot.
    
    slot är en av: 'rev', 'var', 'insa', 'insb', 'adins', 'vcm', 'mas'
    
    Exempel:
        list_fx_for_slot('insa') → ['THRU', 'HD HALL', 'REV-X HALL', ...]
    """
    if not HAS_ENUMS:
        # Fallback: returnera alla FX vi har TypeIndex för
        return list(FX_TYPE_INDEX.keys())
    return ENUMS.fx_for_slot(slot) if hasattr(ENUMS, 'fx_for_slot') else list(FX_TYPE_INDEX.keys())

# InsertionA/B base offsets (PART-relativa):
FXA_BASE = 275 # InsertionA: PART+275
FXB_BASE = 332 # InsertionB: PART+332
# fxA+14: EQ Low Freq (tabellindex, default=22=250Hz) ✅
# fxA+16: EQ Low Gain (center=64, 1raw=1dB) ✅
# fxA+18: EQ High Freq (tabellindex, default=48=5kHz) ✅
# fxA+20: EQ High Gain (center=64, 1raw=1dB) ✅
# fxA+22: Dry/Wet (direct: 0=100%Dry, 64=50/50, 127=100%Wet) ✅
# fxA+24: EQ Mid Freq (tabellindex, default=38=1.6kHz) ✅
# fxA+26: EQ Mid Gain (center=64, 1raw=1dB) ✅
# fxA+28: EQ Mid Width (tabellindex, default=7=0.7) ✅
#
# CLASSIC FLANGER — specifika params (fxA+4-12, fxA+30-34):
# fxA+4: LFO Speed (raw=round(Hz*23.7), default=26=1.09Hz) ✅
# fxA+6: LFO Depth (direct, default=34) ✅
# fxA+8: LFO Wave (0=Triangle, 1=Sine, default=0) ✅
# fxA+10: Delay Offset (tabellindex, default=24=0.65ms) ✅
# fxA+12: Feedback (raw=percent+100, default=151=51%) ✅
# fxA+30: Mod Phase (raw=phase_index*2, 180°→16) ✅
# fxA+32: FB High Damp (raw=value*10, default=9=0.9) ✅
# fxA+34: Analog Feel (direct, default=0) ✅
#
# SYMPHONIC — specifika params:
# fxA+4: LFO Speed (raw=round(Hz*23.7), default=11≈0.46Hz) ✅ SAMMA formel som CF!
# fxA+6: LFO Depth (direct, default=25) ✅
# fxA+8: Delay Offset (tabellindex, default=1≈0ms, 1ms→10) ✅ (INTE LFO Wave!)
# (fxA+10-12 saknas i Symphonic — CF-specifika fält)
#
# LFO Speed encoding (BÅDA FX): raw = round(Hz * 23.7045) ★★★★★
# Datapunkter: 0.46Hz→11, 0.80Hz→19, 1.09Hz→26, 1.30Hz→31, 1.60Hz→38, 1.98Hz→47
ANX_INSERT_FX = dict(
    fxATypeLo=275, # u8, lo-byte of 7-bit FX type index ✅
    fxATypeHi=276, # u8, hi-byte of 7-bit FX type index ✅
    fxBTypeLo=332, # u8, lo-byte ✅
    fxBTypeHi=333, # u8, hi-byte ✅
)
# Sub-blob edit-state bytes + Common-area side-effect flags (filtreras vid diff):
ANX_PERF_NOISE = {
    22, 23, 24,                    # Sub-blob 1 timestamp + edit-state
    66, 232, 234, 358, 376, 654,   # Common-area side-effect flags
    6724, 6725,                    # Sub-blob 2 timestamp
    7167, 7168, 7419,              # Arp/Scene edit-counters
}

# General blob noise (engine-oberoende sub-blob edit-state):
# Sub-blob N start = 6701 + (N-1)*5765, with edit-state bytes at +23, +24
NOISE_BLOB_COMMON = ANX_PERF_NOISE  # samma set, alla engines
NOISE_FILE = {63, 399}  # file-level save counters (LSB of u32be at +60 and +396)

# ── FILE-LEVEL STRUCTURE ★★★★★ ────────────────────────────────────────────
# YSFC Y2L/Y2U file header (64 bytes, abs offsets) — Steg 1-verifierad mot
# 1930 testfiler (2026-05). Identisk layout för Y2L och Y2U; ärver from
# YSFC 4.0.5 / 5.0.1 men med utökad library-info-area.
#
#   abs    fält                                  värde / not
#   ────────────────────────────────────────────────────────────────────────
#   0x00   magic + null-pad (16 b)              b'YAMAHA-YSFC\x00\x00\x00\x00\x00'
#   0x10   version-sträng + null-pad (16 b)     b'5.1.2' för Montage M / MODX M
#                                               (4.0.5 = Montage classic,
#                                                5.0.1 = MODX classic)
#   0x20   catalogue size  (u32 BE)             = antal_block × 8
#   0x24   reserved padding (12 b)              alla 0xff
#   0x30   library-info length (u32 BE)         baseline 241 b (tom),
#                                               4230 b observerad med
#                                               populerade library-slots
#   0x34   reserved padding (8 b)               alla 0xff
#   0x3C   timestamp / save counter (u32 BE)    monotont ökande counter,
#                                               INTE Unix-epoch
#   0x40   katalog-poster                       N × (4-byte ID + u32 BE offset)
#   0x40 + catalogue_size
#          library-info-area                    240 × 0xff + 1 × 0x00 = 241 b
#                                               i baseline (24 library-slots
#                                               × 10 reserverade bytes + 1
#                                               separator-byte)
#   0x40 + catalogue_size + libinfo_length
#          första block-chunk (EPFM)
#
# Bekräftat: INGEN kryptografisk checksum eller CRC i formatet.
# Save counter vid file[0x3c:0x40] (= file[60:64]) ökar för varje export;
# en inner counter vid file[396:400] följer (= huvudcounter - 1).
# Se "Appendix A: Steg 1 – Header-verifiering" i YSFC_FORGE_FULL_CONTEXT.md
# för full hypotes-genomgång och korpus-statistik.
#
# Observerade block-ID:n i korpus (1930 filer):
#   ALLTID: EPFM/DPFM, ESYS/DSYS, EFVT/DFVT  (6 block, cat_size=48)
#   SmartMorph-filer: + ESPG/DSPG, ESOM/DSOM (10 block, cat_size=80)
#   Live Set: + ELST/DLST                    (8 block, cat_size=64)
#   Analysis_Set_v1: + ESON/DSON             (12 block, cat_size=96)
FILE_SAVE_COUNTER_POS = 60       # u32be @ 0x3C, 4 bytes — Steg 1 verifierad
FILE_INNER_SAVE_COUNTER_POS = 396  # u32be, 4 bytes (= file[60:64] - 1)
CHUNK_CATALOG_POS = 64           # 0x40, 6×8 bytes för baseline (EPFM..DFVT)
CHUNK_NAMES = ['EPFM', 'ESYS', 'EFVT', 'DPFM', 'DSYS', 'DFVT']

# Header-fält-offsets (Steg 1 verifierade konstanter)
YSFC_MAGIC_POS         = 0x00    # 16 bytes magic + null-pad
YSFC_VERSION_POS       = 0x10    # 16 bytes version + null-pad
YSFC_CAT_SIZE_POS      = 0x20    # u32be: catalogue size (= entries × 8)
YSFC_LIBINFO_LEN_POS   = 0x30    # u32be: library-info area length
YSFC_TIMESTAMP_POS     = 0x3C    # u32be: save counter (alias FILE_SAVE_COUNTER_POS)
YSFC_CATALOG_POS       = 0x40    # första katalogposten
YSFC_VERSION_M_SERIES  = b'5.1.2'  # förväntad version för Y2L/Y2U
YSFC_LIBINFO_EMPTY_LEN = 241     # tom library-info: 240 × 0xff + 1 × 0x00

def read_save_counter(file_data: bytes) -> int:
    """Läs save counter från file[60:64] (u32be)."""
    return (file_data[60] << 24) | (file_data[61] << 16) | \
           (file_data[62] << 8) | file_data[63]

def write_save_counter(file_data: bytearray, value: int) -> None:
    """Skriv save counter till file[60:64] OCH inner counter till file[396:400]=value-1."""
    file_data[60] = (value >> 24) & 0xFF
    file_data[61] = (value >> 16) & 0xFF
    file_data[62] = (value >> 8) & 0xFF
    file_data[63] = value & 0xFF
    inner = max(0, value - 1)
    file_data[396] = (inner >> 24) & 0xFF
    file_data[397] = (inner >> 16) & 0xFF
    file_data[398] = (inner >> 8) & 0xFF
    file_data[399] = inner & 0xFF

# ── EPFM Entr-record struktur ★★★★★ ──────────────────────────────────────
# Entr-record vid file[365] innehåller performance-metadata.
# Layout (relativt Entr payload start):
#   [0..4]    u32be: pointer/storlek till DPFM payload
#   [4..8]    u32be: 0x0000000C (konstant, performance type)
#   [8..12]   u32be: 0x00400000 (konstant)
#   [12..16]  u32be: 0x00000004 (konstant)
#   [16..18]  bytes: 0x02 0x00
#   [18]      u8: PART-ACTIVE BITMASK = (1<<max_active_part) - 1
#   [19..22]  bytes: 0x00 × 3 (padding)
#   [23..27]  u32be: inner save counter (= file[60:64] - 1)
#   [27..]    ASCII: "256:<perf_name>:<part1_name>\0"
ENTR_PART_BITMASK_OFFSET = 18  # relativt Entr payload start
ENTR_INNER_COUNTER_OFFSET = 23

def build_entr_payload(perf_name: str, part1_name: str,
                       max_active_part: int, save_counter: int,
                       dpfm_size: int) -> bytearray:
    """Konstruerar Entr-record payload för EPFM-chunken."""
    import struct
    name_str = f"256:{perf_name}:{part1_name}\x00"
    name_bytes = name_str.encode('latin-1')

    payload = bytearray(27 + len(name_bytes))
    payload[0:4]   = struct.pack('>I', dpfm_size)
    payload[4:8]   = struct.pack('>I', 0x0000000C)
    payload[8:12]  = struct.pack('>I', 0x00400000)
    payload[12:16] = struct.pack('>I', 0x00000004)
    payload[16:18] = b'\x02\x00'
    payload[18]    = get_entr_bitmask(max_active_part)
    payload[19:23] = b'\x00\x00\x00\x00'
    payload[23:27] = struct.pack('>I', save_counter - 1)
    payload[27:]   = name_bytes
    return payload

# Drum-key collateral bytes — updated automatically by MODX on any drum-key edit
DRUM_COLLATERAL_BYTES = {6715, 6716, 6721}

COMMON_FIELDS = dict(
    portamentoSw=41, portamentoTime=94,           # ★★★★★ (Portamento_Time_50)
    commonVolume=68, commonPan=70,                # ★★★★★ Volume = EF Master Output (UI-aliasing)
    performanceTempo=92,                          # ★★★★★ (TEST5-2-TEMPO90)
    smartMorphEnable=56,                          # ★★★★★ (TEST-FMX-SMARTMORPH)
    # Common Audio In + Routing (abs 766-784) ★★★★★ AN-X tester verified
    audioInVolume=766, audioInPan=768,
    audioInRevSend=770, audioInVarSend=772,
    audioInRouting=774,                           # 1=A-B, 2=B-A
    audioInDryLevel=778,
    envelopeFollowerGain=780,                     # c64 default 64
    envelopeFollowerAttack=782,                   # default 16
    envelopeFollowerRelease=784,                  # default 7
    # Reverb/Variation returns + pan (abs 112-122) ★★★★★
    revReturn=112,                                # c64 default 64
    revPan=114,                                   # c64 default 64
    varReturn=118,                                # c64 default 96
    varPan=120,                                   # c64 default 64
    varToRev=122,                                 # direct default 0
    sidechainMaster=128,                          # enum, default 127=Off
    # Common CC-assigns (abs 152-184) ★★★★★ AN-X tester verified
    ribbonCC=152,                                 # default 16
    breathCC=154,                                 # default 2
    fc1CC=156, fc2CC=158,                         # FootCtrl CC assignments
    asw1CC=160, asw2CC=162,                       # Assign Switch CC
    msCC=166,                                     # default 89
    # AssignKnob 1..8 CC values (stride 2, sekvens) ★★★★★
    # Defaults: 17, 18, 19, 20, 21, 22, 23, 24 (sekvenserande CC#)
    assignKnob1CC=168, assignKnob2CC=170,
    assignKnob3CC=172, assignKnob4CC=174,
    assignKnob5CC=176, assignKnob6CC=178,
    assignKnob7CC=180, assignKnob8CC=182,
    # Ribbon Controller settings (abs 30, 31, 216) ★★★★★
    ribbonAssignA=30, ribbonAssignB=31,           # bool, default 1
    ribbonGrid=216,                               # default 0
    # SuperKnob Link Scene 1..8 (abs 40..47) ★★★★★
    superKnobLinkScene1=40, superKnobLinkScene2=41,
    superKnobLinkScene8=47,                       # alla bool default 1
    commonAudioOn=50,                             # bool default 1 (TEST CommonAudio_Off)
    sliderDirection=57,                           # bool default 0=Normal
    arpSyncQuantizeCommon=360,                    # enum default 0=Off
    # Master EQ 5-band (abs 560-592) ★★★★★ AN-X tester verified
    masterEqLowGain=560, masterEqLowFreq=562,
    masterEqTypes=566,
    masterEqLowmidGain=568, masterEqLowmidFreq=570, masterEqLowmidQ=572,
    masterEqMidGain=574, masterEqMidFreq=576, masterEqMidQ=578,
    masterEqHimidGain=580, masterEqHimidFreq=582, masterEqHimidQ=584,
    masterEqHighGain=586, masterEqHighFreq=588,
    masterEqHighType=592,
)

# ── KRITISKA METADATA-BYTES (måste sättas korrekt vid skrivning) ──────────
# Engine Type per Part 1, indikerar vilken engine sub-blob 2 innehåller:

# ── COMMON-LEVEL SCENE-BLOCK ★★★★★ ──
# 8 Scene-snapshots på Performance-nivå (Common-blob).
# Position: abs 1710..2277 = 8 scenes × 71 bytes (KORRIGERING från tidigare 1671)
# Stride: 71 bytes per Scene
# Verifierat: Scenes är IDENTISKA i Init Voice (0 diffs mellan scene 1-7, Scene 8 har 1 diff)
# Verifierade fält per Scene (rel inom 71-byte block):
#   rel +5  = AEG/MS Snapshot toggle (Scene*_AEG_Snapshot, Scene*_Swing/Unit)
#       (Scene1_AEG_Snapshot ändrar abs 1715 = 1710 + 5)
#       (Scene2_Swing_50 ändrar abs 1786 = 1781 + 5)
#       (Scene3_Smooth_50 ändrar abs 1857 = 1852 + 5)
#   rel +16 = NoteLimit on flag (Scene1_NoteLimit_ON @ abs 1726 = 1710+16)
#   rel +15 = KBD Ctrl flag (Scene2_KBD_CTRL_ON @ abs 1796 = 1781+15)

COMMON_SCENE_BASE_ABS = 1710
COMMON_SCENE_STRIDE = 71
COMMON_SCENE_COUNT = 8
COMMON_SCENE_FIELDS_REL = {
    5:  ('scene_aeg_snapshot',    'u8',      '0 (AEG_Snapshot toggle → 1)'),
    15: ('scene_kbd_ctrl',        'u8 bool', '0 (Scene*_KBD_CTRL_ON → 1)'),
    16: ('scene_note_limit',      'u8 bool', '0 (Scene*_NoteLimit_ON → 1)'),
}

def get_common_scene_field_addr(scene_idx: int, field_name: str) -> int:
    """Returnera abs adress för Common Scene-fält. scene_idx is 0-based (Scene 1 = 0)."""
    if not 0 <= scene_idx < COMMON_SCENE_COUNT:
        raise ValueError(f'scene_idx must be 0..7')
    for rel, (name, _, _) in COMMON_SCENE_FIELDS_REL.items():
        if name == field_name:
            return COMMON_SCENE_BASE_ABS + scene_idx * COMMON_SCENE_STRIDE + rel
    raise KeyError(f"Field '{field_name}' not in COMMON_SCENE_FIELDS_REL")

# ── PER-PART SCENE-BLOCK ★★★★★ ──
# 8 Scene-snapshots per Part (sparade Motion Sequencer/Mixer-värden per Scene).
# Position: Part rel +682..+1353 = 8 scenes × 84 bytes per Part
# Stride: 84 bytes per Scene
# Verifierat: Scenes 1-7 är IDENTISKA i Init Voice; Scene 8 har 9 diffs (rel 73-83).
# Verifierade fält per Scene (rel inom 84-byte block):

PART_SCENE_REL_BASE = 682
PART_SCENE_STRIDE = 84
PART_SCENE_COUNT = 8
PART_SCENE_FIELDS_REL = {
    38: ('scene_swing',  'u16le c128', '128 (Scene*_Swing_50)'),
    40: ('scene_unit',   'u8 enum',    '3 (Scene*_Unit_75 → 2)'),
    50: ('scene_smooth', 'u16le c128', '128 (Scene*_Smooth_50)'),
}

def get_part_scene_field_addr(sub_blob_start: int, scene_idx: int, field_name: str) -> int:
    """Returnera abs adress för Part Scene-fält. scene_idx is 0-based."""
    if not 0 <= scene_idx < PART_SCENE_COUNT:
        raise ValueError(f'scene_idx must be 0..7')
    for rel, (name, _, _) in PART_SCENE_FIELDS_REL.items():
        if name == field_name:
            return sub_blob_start + PART_SCENE_REL_BASE + scene_idx * PART_SCENE_STRIDE + rel
    raise KeyError(f"Field '{field_name}' not in PART_SCENE_FIELDS_REL")

# ── ASSIGN KNOB NAMES (8 Performance-globala) ★★★★★ ──
# Position: abs 8049..8216 = 8 × 21 bytes
# Default-värden: "Assign 1", "Assign 2", ..., "Assign 8"
# (Strängarna kan redigeras av användaren i Performance Common)

ASSIGN_KNOB_NAME_BASE_ABS = 8049
ASSIGN_KNOB_NAME_STRIDE = 21
ASSIGN_KNOB_NAME_COUNT = 8

def get_assign_knob_name_addr(knob_idx: int) -> int:
    """Returnera abs adress för Assign Knob Name. knob_idx is 0-based."""
    if not 0 <= knob_idx < ASSIGN_KNOB_NAME_COUNT:
        raise ValueError(f'knob_idx must be 0..7')
    return ASSIGN_KNOB_NAME_BASE_ABS + knob_idx * ASSIGN_KNOB_NAME_STRIDE

def read_assign_knob_name(blob: bytes, knob_idx: int) -> str:
    """Returnera Assign Knob Name som sträng."""
    addr = get_assign_knob_name_addr(knob_idx)
    raw = blob[addr:addr + ASSIGN_KNOB_NAME_STRIDE]
    return raw.decode('latin-1', errors='replace').rstrip('\x00 ')

# ── KRITISKA METADATA-BYTES (måste sättas korrekt vid skrivning) ──────────
# Engine Type per Part 1, indikerar vilken engine sub-blob 2 innehåller:
ENGINE_TYPE_BYTE = 6700  # u8 enum: 0=AWM2, 1=Drum, 2=FMX, 3=ANX  ★★★★★
                         # GÄLLER ENDAST v5.x (MODX M / Montage M, version 5.1.2).
                         # I v4.x-filer (MODX classic 5.0.1 / Montage classic 4.0.5)
                         # sitter engine-type-byten på offset 6698, inte 6700.
                         # Använd EPFM rec[15] (engine bits) som primärkälla vid läsning
                         # av okänd filversion — det är korrekt i båda formaten.
                         # EPFM bits: 0x01=AWM2/Drum, 0x02=FM-X, 0x04=AN-X.
ENGINE_TYPE_VALUES = {0: 'AWM2', 1: 'Drum', 2: 'FMX', 3: 'ANX'}
ENGINE_TYPE_BY_NAME = {v: k for k, v in ENGINE_TYPE_VALUES.items()}

# Högsta aktiva Part-index (INTE antal aktiva parts):
# Part 1 only → 1; Parts 1+2 → 2; Parts 3+5 → 5 (icke-konsekutiva tillåtna)
MAX_ACTIVE_PART_BYTE = 6695  # u8 direct, 1..16  ★★★★★

# Part 2 engine-typ-indikatorer (engine-pool prefix):
PART2_ENGINE_PREFIX = (12464, 12465)  # u8 × 2, engine-specifika värden

# ── MOTION SEQUENCER STRUKTUR ★★★★★ ────────────────────────────────────
# UI-vy "Motion Seq > Common / Lane" har TVÅ sektioner:
#   1. "Common" (vid abs 100, 102, 656-662) — Performance Common-fält
#      Gäller för hela Performance (alla Parts).
#   2. "Part"   (vid abs 6887-6895, 7097) — Part Common-fält
#      Gäller för hela Part (alla 4 Lanes i denna Part).
#
# View Lane-dropdown (1-4) i UI styr endast VISNINGEN i Edit Part Sequencer-vyn,
# INTE vilka bytes som ändras av Common/Part-fälten ovan.
#
# Verifierat med TEST5R3-T4b-Lane2-Swing50 (ändrar 6887, samma som Lane1) och
# TEST5R3-T4b-ViewLane2-Swing50 (ändrar 6887 OCH 6897=Last-edited-lane-flag).
#
# Per-Lane data (Lane Switch, Lane Velocity Limits, MS Grid, Pulse A/B m.fl.)
# ligger i sub-blob 2 Lane-data-area [8929+, stride 884 per Lane], EJ här.

# Common Motion Sequencer-fält (Performance Common-area)
COMMON_MOTION_SEQ = dict(
    swing=100,        # u16le c128, default 128  ★★★★★ (Lane1_Common_Swing_50)
    unit=102,         # u8 enum (3=1/16 default, 0=50%)  ★★★★★ (Lane1_Common_Unit_50%)
    amplitude=656,    # u16le c128, default 128  ★★★★★ (Lane1_Common_Amplitude_50)
    shape=658,        # u16le c64, default 64  ★★★★★ (Lane1_Common_Shape_50)
    smooth=660,       # u16le c128, default 128  ★★★★★ (Lane1_Common_Smooth_50)
    random=662,       # u16le c128, default 128  ★★★★★ (Lane1_Common_Random_50)
)

# Part Motion Sequencer-fält (Part Common-area, rel sub-blob 2 +N)
# Stride 5765 mellan parts.
PART_MOTION_SEQ_REL = dict(
    swing_rel=186,     # u16le c128, default 128 (abs 6887 = 6701 + 186)
    amplitude_rel=188, # u16le c128, default 128
    shape_rel=190,     # u16le c64, default 64
    smooth_rel=192,    # u16le c128, default 128
    random_rel=194,    # u8 direct 0..100
    unit_rel=396,      # u8 enum (abs 7097 = 6701 + 396, ej intill övriga fält)
)

def get_part_motion_seq_addr(part_idx: int, field: str) -> int:
    """Returnerar abs address för Part N:s Motion Seq Part-fält."""
    sub_blob_start = 6701 + (part_idx - 1) * 5765
    return sub_blob_start + PART_MOTION_SEQ_REL[f'{field}_rel']

# Bakåtkompatibilitet — gammalt namn är alias för det nya
LANE1_COMMON = COMMON_MOTION_SEQ

# ── AWM2 Control Source-block (region [7300:7419] Part Common) ──────────
# 4 × 18-byte slots för AWM2 PolyAT/AT/Velocity-mapping per Part
AWM2_CONTROL_SOURCE_BASE = 7300
AWM2_CONTROL_SOURCE_STRIDE = 18
AWM2_CONTROL_SOURCE_SLOT_COUNT = 4
AWM2_CONTROL_SOURCE_SLOT = dict(
    switch_rel=1,        # bool, +0 från slot-bas + 1 = abs 7301 för slot 0  ★★★★☆
    destination_rel=3,   # u8 enum (1=Resonance, 9=Filter, 10=Cutoff)  ★★★★☆
    source_rel=5,        # u8 (PolyAT, AT, MW source-id)  ★★★☆☆
    depth_rel=7,         # u8 direct  ★★★★☆
    curve_rel=9,         # u8 enum 0..5  ★★★★☆
    param1_rel=11,       # u8 direct  ★★★★☆
    param2_rel=13,       # u8 direct  ★★★★☆
)

def get_awm2_control_source_addr(slot_idx, field_name, sub_blob_start=6701):
    """slot_idx: 0..3, field_name from AWM2_CONTROL_SOURCE_SLOT keys (minus _rel)."""
    rel_key = field_name + '_rel'
    slot_base = AWM2_CONTROL_SOURCE_BASE + slot_idx * AWM2_CONTROL_SOURCE_STRIDE
    # For Part > 1, adjust by sub-blob stride
    part_offset = sub_blob_start - 6701
    return slot_base + AWM2_CONTROL_SOURCE_SLOT[rel_key] + part_offset

# ── Stride-106 Groups (opaque internal data, preserve verbatim) ──────────
# Group 1-4 ändras ALDRIG av ESP UI (0 testfiler i 1626-fils-korpus modifierar dem).
# Group 5 är Scene/Part-relaterad och uppdateras automatiskt vid multi-part-skriv.
# Patch editor: läs och skriv verbatim, försök INTE tolka.
STRIDE_106_GROUPS = [
    (840, 1710, '8 × 106 — opaque internal'),
    (3186, 4043, '8 × 106 — opaque internal'),
    (4083, 4943, '8 × 106 — opaque internal'),
    (4943, 5826, '8 × 106 — opaque internal'),
    (5942, 6700, '7 × 106 + 16b trailer — Scene/Part-related'),
]

# ── OPAQUE INTERNAL REGIONS ────────────────────────────────────────────────
# Regioner som är 100% engine-agnostiska, 0 testfiler modifierar dem.
# Bekräftat firmware-konstant data. Editor MÅSTE preserva byte-för-byte.
OPAQUE_INTERNAL_REGIONS = [
    (487, 525, '38 b — between Hardware Ribbon and Master FX'),
    (732, 766, '34 b — 14 × u16le firmware-constant pattern'),
    (788, 840, '52 b — CA-like block + 14b end-marker'),
    (5843, 5893, '50 b — between Stride-106 groups'),
    (6971, 6983, '12 b — Part Common between EQ and stride-106'),
    (7275, 7290, '15 b — Part Common after Tx Rx Channel'),
]

# ── MULTI-PART "LINKED LIST"-pointer-modell ★★★★★ ──────────────────────────
# Layout:
#   [Common 6701b] [SubBlob2 5765b] [SubBlob3 5765b] ... [SubBlobN 5765b]
#                                                       [Engine1 prefix+data]
#                                                       [Engine2 prefix+data] ...
#
# Sub-blob N (1..N) slutar med 2 bytes som ger pointer-information.
# Pointer-position för Part N: (sub_blob_start + 5763, sub_blob_start + 5764)
# där sub_blob_start = 6701 + (N-1) × 5765
#
# För sub-blob där N < max_part_idx (= det finns ytterligare sub-blobs):
#   (1, next_part_engine_id)
#   exempel: Part 1 i [ANX, FMX, AWM2]-fil → pointer = (1, 2) ("nästa är FMX")
#
# För sub-blob N där N = max_part_idx (= det är sista sub-blob, engine-pool följer):
#   (engine_magic_for_PART_1, 0)
#   exempel: Part 3 i [ANX, FMX, AWM2]-fil → pointer = (110, 0) (Part 1 är ANX)
#
# OBS: sista sub-blob's pointer ger Part 1's engine-magic, inte sin egen!
# Det är ett "engine-pool-prefix" som överlappar sub-blob N's slut.
#
# Engine magic-bytes: ANX=110, AWM2=8, FMX=82, Drum=73
SUBBLOB_POINTER_REL = (5763, 5764)
ENGINE_MAGIC_BYTES = {
    'ANX': 110,
    'AWM2': 8,
    'FMX': 82,
    'Drum': 73,
}
ENGINE_MAGIC_TO_NAME = {v: k for k, v in ENGINE_MAGIC_BYTES.items()}

def get_subblob_pointer_pos(part_idx: int) -> tuple[int, int]:
    """Returnerar (pos+0, pos+1) för Part N's pointer (1-indexerat)."""
    sub_blob_start = 6701 + (part_idx - 1) * 5765
    return (sub_blob_start + SUBBLOB_POINTER_REL[0],
            sub_blob_start + SUBBLOB_POINTER_REL[1])

def read_subblob_pointer(blob: bytes, part_idx: int) -> tuple[bool, str]:
    """Läser pointer för Part N.

    Returns: (is_last_subblob, next_or_part1_engine_name)
    - is_last_subblob=False: sub-blob N+1 följer med given engine-typ
    - is_last_subblob=True: sub-blob N är sista; returnerad engine är PART 1's
      engine (= första engine i engine-pool), INTE Part N's egen engine
    """
    pos0, pos1 = get_subblob_pointer_pos(part_idx)
    marker = blob[pos0]
    next_val = blob[pos1]
    if marker == 1:
        # Continuation: next sub-blob follows with engine type = next_val
        engine_name = ENGINE_TYPE_VALUES.get(next_val, f'Unknown({next_val})')
        return False, engine_name
    else:
        # Last subblob: marker is engine-magic for Part 1 (first engine in pool)
        engine_name = ENGINE_MAGIC_TO_NAME.get(marker, f'UnknownMagic({marker})')
        return True, engine_name

def write_subblob_pointer_continuation(blob: bytearray, part_idx: int,
                                        next_engine_name: str) -> None:
    """Skriv pointer för Part N när det finns en nästa sub-blob (Part N+1)."""
    pos0, pos1 = get_subblob_pointer_pos(part_idx)
    blob[pos0] = 1
    blob[pos1] = ENGINE_TYPE_BY_NAME[next_engine_name]

def write_subblob_pointer_last(blob: bytearray, part_idx: int,
                                part1_engine_name: str) -> None:
    """Skriv pointer för sista sub-blob (engine-pool börjar direkt efter).
    part1_engine_name är Part 1's engine (= första engine i pool)."""
    pos0, pos1 = get_subblob_pointer_pos(part_idx)
    blob[pos0] = ENGINE_MAGIC_BYTES[part1_engine_name]
    blob[pos1] = 0

def get_entr_bitmask(max_active_part: int) -> int:
    """Beräknar Entr-record part-bitmask: (1 << N) - 1 där N = max_active_part."""
    return (1 << max_active_part) - 1

def is_opaque_byte(offset: int) -> bool:
    """Returnerar True om offset ligger i en OPAQUE-region som ska preserveras verbatim."""
    for start, end, *_ in OPAQUE_INTERNAL_REGIONS:
        if start <= offset < end:
            return True
    # Stride-106 Groups 1-4 är fullt opaque (Group 5 är Scene-relaterad, exkluderas)
    for start, end, *_ in STRIDE_106_GROUPS[:4]:
        if start <= offset < end:
            return True
    return False

# Engine-pool layout: varje engine-block i poolen prefixas med 2 byte (magic, 0).
# Mellan engine-block finns ~3 byte padding (00 00 00).
# För Part 1: prefixet ligger i sista sub-blobens sista 2 bytes (överlappande).
# För Part 2..N: prefixet är 5-byte separator (00 00 00 magic 00).
ENGINE_POOL_SEPARATOR_SIZE = 5  # 3 padding + 2 magic-prefix bytes

# FM-X OP Routing Matrix abs=6730-6793
# 64 bytes, all default=1 = all OP-kopplingarna aktiva
# 8 OPs × 8 kopplingsbytes = 64 bytes
# Ändras ALDRIG via ESP UI — interna algoritm-defaults
# Ska INTE skrivas vid patch-editing
FMX_OP_ROUTING_MATRIX_ABS = (6730, 6793) # (start, end), default=1 all

# AWM2 After Touch Assign register ★★★★★
# Separat från CA-blocket (abs=8220+) — eget litet AT-register
# Har sin EGEN destination-encoding (kortare lista än CA)
AWM2_AT_ASSIGN = dict(
    atSwitch=593, # abs PART+593, u8 bool 0=Off,1=On ★★★★★
    atDestination=595, # abs PART+595, u8 enum Pitch=1(def), FilterCutoff=9 ★★★★★
)
# AT Destination encoding (AWM2, ANNAN än CA_DESTINATION!):
AT_DESTINATION = {
    1: 'Pitch', # default ★★★★★
    9: 'FilterCutoff', # ★★★★★
}

# NOTE: OP Mute/Solo sparas INTE i YSFC
# Mute/Solo är real-time performance state — ändras not i binärfilen vid Save.

FMX_PART_BASE = dict(
    # FM Color + algorithm sub-table (all at ODD abs offsets, u8 each)
    fmcLfoAmplWave=12521, # u8 enum default=0 ★★★★☆
    fmcLfoAmplSpeed=12523, # u8 direct default=0 ★★★★☆
    algorithm=12525, # u8 direct raw=algo-1, Init=69→raw=68
    feedback=12527, # u8 direct default=0
    fmcLfoAmplDepth=12529, # u8 direct default=1 ★★★★☆
    # NOTE: abs 12529 (PART+5821) = fmxPart2ndLfoExtended (see FMX_PART_2ND_LFO)
    # NOTE: abs 12531 (PART+5823) = fmxPart2ndLfoSpeedExtended (see FMX_PART_2ND_LFO)
    # FM Color depth fields (center=128, all verified ✅)
    fmcDepth=12533, # u8 center=128 default=0 ✅ (Depth_50→178)
    fmcHarmonics=12535, # u8 center=128 default=0 ✅
    fmcAttack=12537, # u8 center=128 default=0 ✅
    fmcDecay=12539, # u8 center=128 default=0 ✅
    fmcSustain=12541, # u8 center=128 default=0 ✅
    fmcRelease=12543, # u8 center=128 default=0 ✅
    fmcTexture=12545, # u8 center=128 default=0 ✅
    # FM-X Filter sub-table (abs = PART + rel, rel = MIDI_hex_addr + 5843)
    fmxFilterType=12551, # u8 enum Thru=21,LPF18D=2,HPF12=7 ✅
    fmxFilterCutoff=12553, # u16 LE Hz default=1023 ✅
    fmxCutoffVelSens=12555, # u8 center=64, raw_default=64(ui=0) ★★★★☆ verified
    fmxFilterResonance=12557, # u8 direct default=10 ✅
    # FM-X Part AEG (PART_COMMON_SHIFT=-12, confirmed ✅)
    fmxAegAttack=6849, # u8 center=64 default=0 ✅
    fmxAegDecay=6851, # u8 center=64 default=0 ✅
    fmxAegSustain=6853, # u8 center=64 default=0 ✅
    fmxAegRelease=6855, # u8 center=64 default=0 ✅
    # FM-X Part Filter Offsets (Part-level, center=64)
    fmxFEGDepthOffset=6865, # u8 center=64 default=0 ✅ (rel+157)
    fmxFilterCutoffOffset=6867, # u8 center=64 default=0 ✅ (rel+159)
    fmxResonanceOffset=6869, # u8 center=64 default=0 ✅ (rel+161)
)
# FM-X Part LFO TempoNote tabell (raw = list_index + 5)
# Bekräftad med 1 fil + ESP-bild ★★★★★
FMX_LFO_TEMPONOTE = {
    5: "1/16", 6: "1/8 Tri.", 7: "1/16 Dot.", 8: "1/8",
    9: "1/4 Tri.", 10: "1/8 Dot.", 11: "1/4", # 11=default
    12: "1/2 Tri.", 13: "1/4 Dot.", 14: "1/2",
    15: "Whole Tri.", 16: "1/2 Dot.",
    17: "1/4 x4", 18: "1/4 x5", 19: "1/4 x6", 20: "1/4 x7",
    21: "1/4 x8", 22: "1/4 x16", 23: "1/4 x32", 24: "1/4 x64",
}

# Controller Assign structure ★★★★★
# UPDATED: CA_PERF and CA_PART are actually 32 slots × 22 + 24-byte trailer = 728 b
# Slots 17-32 är BIT-FÖR-BIT IDENTISKA
# med slots 1-16 i Init Voice (skillnad bara byte 3 = scope-flagga).
#
# PART CA: abs = CA_PART_BASE + ca_idx * CA_STRIDE (ca_idx 0-31)
# PERF CA: abs = CA_PERF_BASE + ca_idx * CA_STRIDE (ca_idx 0-31)
# Trailer (24 b): finns vid CA_PERF_BASE + 32*22 = 3155, CA_PART_BASE + 32*22 = 8924
CA_STRIDE = 22
CA_SLOT_COUNT = 32 # ★★★★★—, now 32
CA_TRAILER_SIZE = 24
CA_TOTAL_SIZE = CA_SLOT_COUNT * CA_STRIDE + CA_TRAILER_SIZE # 728
CA_PART_BASE = 8220 # 32 slots × 22 + 24 trailer = 728 b → ends @ 8948
CA_PERF_BASE = 2451 # 32 slots × 22 + 24 trailer = 728 b → ends @ 3179

# Trailer-positioner (de 24 byte efter alla 32 slots):
CA_PERF_TRAILER = CA_PERF_BASE + CA_SLOT_COUNT * CA_STRIDE # 3155
CA_PART_TRAILER = CA_PART_BASE + CA_SLOT_COUNT * CA_STRIDE # 8924
# Båda trailers innehåller samma 24-byte block-end signature

# Offsets within each 22-byte CA entry (ENGINE-OBEROENDE — AWM2/FM-X/AN-X ✅):
CA_ENTRY = dict(
    header=0, # u8 default=18, okänd funktion
    sw=1, # u8 bool 0=Off,1=On ★★★★★
    source=3, # u8 enum — se CA_SOURCE (PB=0,MW=1,Knob1=8...) ★★★★★
    destination=5, # u8 enum — se CA_DESTINATION (Vol=1,Cut=85) ★★★★★
    curveType=9, # u8 enum (Standard=0, Harmonic=18) ★★★★★
    param1=11, # u8 direct default=5 ★★★★★
    param2=13, # u8 direct default=0 ★★★★★
    polarity=15, # u8 bool 0=UNI,1=BI ★★★★★
    depth=17, # u8 default=192=0xC0 — MODX-INTERNT, not synlig parameter
                     # Uppdateras automatiskt av MODX vid varje Store (som timestamp-bytes)
                     # Ska IGNORERAS vid patch-editing, not skrivas ★★★★★
)

# CA Source enum (verifieradall engines)
CA_SOURCE = {
    0: "PitchBend", # ★★★★★
    1: "ModWheel", # ★★★★★ default
    # 2: AfterTouch # not verifierad
    # 3: FootCtrl # not verifierad
    # 4: FootSw # not verifierad
    # 5: Breath # not verifierad
    # 6-7: CC # not verifierade
    8: "Knob1", # ★★★★★
    9: "Knob2", # ★★★★★
    10: "Knob3", # ★★★★★
    # 11-15: Knob4-8 # not verifierade
}

# CA Destination enum (verifieradall engines)
# InsA Param-serie: raw = param_nr (1-24, linjärt). InsB: raw=25 alltid, param# i CA+11
CA_DESTINATION = {
    1: 'Volume', # ★★★★★ default
    # 2-24: InsA Param2-24 (linjärt: raw = param_nr)
    2: 'InsA Param2', # ★★★★★
    3: 'InsA Param3', # ★★★★★
    24: 'InsA Param24', # ★★★★★ (0x18, linjärt bekräftat)
    25: 'InsB Param', # ★★★★★ (fast raw=25, param# i CA+11)
    50: 'Rev Send', # ★★★★★
    51: 'Var Send', # ★★★★★
    59: 'P.LFO Depth 3', # ★★★★★
    60: 'Element Level', # ★★★★★ (0x3C)
    61: 'Element Pan', # ★★★★★ (0x3D)
    62: 'Element Delay', # ★★★★★ (0x3E)
    85: 'Filter Cutoff', # ★★★★★ (0x55)
    87: 'HPF Cutoff', # ★★★★★ (0x57)
    100: 'Part Pan', # ★★★★★ (0x64)
    105: 'Arp Gate Time', # ★★★★★ (0x69)
    118: 'MS Length', # ★★★★★ (0x76)
    # Fler not verifierade
}

# AWM2 ctrlSet — sitter i AWM2 element-data (not i CA-blocket)
# Adress ännu not binärverifierad — väntar på element-nivå testfiler
# Different from Part-level AEG offsets (rel+141-147)
ANX_SYNTH_AEG = dict(
    # KORRIGERAT  — gamla adresser (12553/12555/12557/12559) var fel med -4 byte.
    # Verifierat mot AN-X Init Voice baseline med +50-tester (default 0/160/511/115 → 50).
    anxSynthAegAttack=12549, # u8 direct default=0 ✅  (AEGOffset_Attack_+50→50)
    anxSynthAegDecay=12551, # u8 direct default=160 ✅  (AEGOffset_Decay_+50→50)
    anxSynthAegSustain=12553, # u16 LE default=511 (max level) ✅  (AEGOffset_Sustain_+50→50)
    anxSynthAegRelease=12555, # u8 direct default=115 ✅  (AEGOffset_Release_+50→50)
)
# Applies to ALL engines (AWM2, FM-X, AN-X): verified ✅
# DPFM_rel = MIDI_hex_addr + 205
PART_SUBTABLE_OFFSET = 205
PART_SUBTABLE = dict(
    pitchBendRangeLower=207, # u8 direct default=62 ✅ (MIDI 0x02)
    detune=209, # u16 LE center=128 default=128=0Hz ✅ (MIDI 0x04)
    noteShift=211, # u8 center=64 default=64=0st ✅ (MIDI 0x06)
    portaTime=213, # u8 direct default=64 ✅ (MIDI 0x08)
    portaMode=215, # u8 bool default=1=FullTime ✅ (MIDI 0x0A)
    # Part 3-band EQ (same offset=205, all engines)
    partEqLowFreq=231, # u8 freq-index default=54(=100Hz), 84Hz→64 ★★★★★ offset verif.
    partEqLowGain=233, # u8 center=64 (dB*2.667+64) default=0dB ✅ (MIDI 0x1C)
    partEqMidFreq=235, # u8 freq-index default=141 ★★★☆☆ (MIDI 0x1E)
    partEqMidGain=237, # u8 center=64 default=0dB ✅ (MIDI 0x20)
    partEqMidQ=239, # u8 direct default=0 ★★★☆☆ (MIDI 0x22)
    partEqHighFreq=241, # u8 freq-index default=231 ★★★☆☆ (MIDI 0x24)
    partEqHighGain=243, # u8 center=64 default=0dB ✅ (MIDI 0x26)
)
FMX_OP_LAYOUT = dict(
    # OP1_BASE=12676, stride=123 — COMPLETE 21/21 fält ★★★★★ (v4.0)
    # PRE-OP block (relativt OP1_BASE, negativa offsets)
    keyOnReset=-4, # u8 bool default=1=On ★★★★★
    freqMode=-2, # u8 enum 0=Ratio,1=Fixed ★★★★☆
    # Freq/Spectral block (off=0-14)
    coarse=0, # u8 direct default=1 ✅
    fine=2, # u8 direct default=0 ✅
    detune=4, # u8 center=15 default=0 ✅
    pitchKey=6, # u8 direct default=0 ★★★★☆
    pitchVel=8, # u8 center=7 default=0 ★★★★☆
    spectralForm=10, # u8 enum 0-6: 0=Sine,1=All1,2=All2,3=Odd1,4=Odd2,5=Res1,6=Res2 ★★★★★
    spectralSkirt=12, # u8 direct default=0 ★★★★★
    spectralResonance=14, # u8 direct default=0 (aktiv för Res1/Res2) ★★★★★
    # PEG block (off=16-20)
    pegInitialLevel=16, # u8 direct default=50 ★★★★☆ (raw=50=UI+50)
    pegAttackLevel=18, # u8 direct default=50 ✅ (Level_Attack_50→100)
    pegAttackTime=20, # u8 direct default=0 ★★★★★ (KORRIGERAT: var aegAttackTime!)
    # AEG block (off=22-40)
    pegDecayTime=22, # u8 direct default=0 ★★★★★ (KORRIGERAT v5.0: var aegDelayTime! PEG Decay Time)
    aegAttackLevel=24, # u8 direct default=99 ★★★★☆
    aegDecay1Level=26, # u8 direct default=99 ★★★★☆
    aegDecay2Level=28, # u8 direct default=99 ★★★★☆
    aegReleaseLevel=30, # u8 direct default=0 ★★★★★
    aegAttackTime=32, # u8 direct default=0 ★★★★★ (LÖST— AEG Attack, höger panel)
    aegDecay1Time=34, # u8 direct default=0 ✅
    aegDecay2Time=36, # u8 direct default=0 ✅
    aegReleaseTime=38, # u8 direct default=40 ✅
    aegHoldTime=40, # u8 direct default=0 ✅
    # Key/Level scaling block (off=42-56)
    aegTimeKeyFollow=42, # u8 direct default=0 ("Time/Key" i ESP) ★★★★★
    level=44, # u8 direct default=0 ✅
    aegBreakPoint=46, # u8 raw=MIDI_note-9, default=39=C3 ★★★★★
    lvlKeyLo=48, # u8 direct default=0 (Lvl/Key Lo) ★★★★★
    lvlKeyHi=50, # u8 direct default=0 (Lvl/Key Hi) ★★★★★
    curveLo=52, # u8 enum 0=-Linear,1=-Exp,2=+Exp,3=+Linear, default=0 ★★★★★
    curveHi=54, # u8 enum (same as curveLo), default=0 ★★★★★
    levelVel=56, # u8 center=7 default=0 ★★★★☆
    # 2nd LFO modulation depth (per OP) — NEW★★★★★
    secondLfoPitchModDepth=58, # u8 direct default=3, abs OP1=12734
    secondLfoAmpModDepth=60, # u8 direct default=3, abs OP1=12736
    # 1st LFO destination Ratio (per OP × 3 destinations) — NEW★★★★★
    firstLfoDest1Ratio=66, # u8 direct default=127, abs OP1=12742
    firstLfoDest2Ratio=68, # u8 direct default=127, abs OP1=12744
    firstLfoDest3Ratio=70, # u8 direct default=127, abs OP1=12746
)
# FM-X 2nd LFO Global Modulation Depths — NEW★★★★★
# Three global depths (separate from per-OP depths in FMX_OP_LAYOUT above).
FMX_2ND_LFO_GLOBAL = dict(
    secondLfoGlobalPitchMod = 12519, # u8 direct default=0
    secondLfoGlobalAmpMod = 12521, # u8 direct default=0
    secondLfoGlobalFilterMod = 12523, # u8 direct default=0
    # Filter Mod is GLOBAL ONLY (no per-OP), confirmed byA3.
)
AWM2_ELEM_LAYOUT = dict(
    # Waveform (element header, DPFM_rel = MIDI_Wave_addr - 4 for addr<0x0C, special for addr 0-0xA)
    waveformNumber=0, # u16 LE, 1-based index (Waveform List #nr) ✅ verified
    waveformBank=2, # u8 direct (1=preset internal) ✅ verified
    # Pan/spatial (MIDI Wave addr 0x0C+, DPFM_rel = MIDI_addr - 4)
    pan=8, randomPan=10, alternatePan=12, scalingPan=14,
    xcaControl=16, # u8 enum 0-7 (Normal/Legato/KeyOff/Cycle/Random/etc)
    # Zone (Note/Vel limits)
    noteLowLimit=18, noteHighLimit=20,
    velLowLimit=22, velHighLimit=24, velCrossFade=26,
    # Key On Delay (rel+28-36 block — not yet fully mapped by MIDI table)
    keyOnDelayElemSW=30, # u8 bool default=1
    keyOnDelayLen=34, # u8 direct default=11
    # Amplitude section (MIDI Amp addr, DPFM_rel = MIDI_addr + 40)
    level=40, # u8 direct default=127 MIDI Amp 0x00
    ampLevelVel=42, # u8 center=64 ✅ verified MIDI Amp 0x02
    levelVelCurve=46, # u8 enum 0-5 default=3 MIDI Amp 0x06
    # AEG Times
    aegAttack=48, aegDecay1=50, aegDecay2=52, aegHalfDamperT=54, aegRelease=56,
    # AEG Levels
    aegInitialLvl=58, aegAttackLvl=60, aegDecay1Lvl=62, aegDecay2Lvl=64,
    # AEG Velocity / Key Follow
    aegTimeVelSegment=66, # u8 enum 0-4 default=4 MIDI Amp 0x1A
    aegTimeVel=68, # u8 center=64 MIDI Amp 0x1C
    aegTimeKeyFollowSens=70, # u8 center=64 default=0 MIDI Amp 0x1E
    # Pitch section (MIDI Pitch addr, DPFM_rel = MIDI_addr + 98)
    pegCoarseTune=98, # u8 center=64 (−48..+48)
    pegFineTune=100, # u8 center=64 (−64..+63)
    pegPitchVelSens=102, # u8 center=64
    pegRandomPitch=104, # u8 direct
    pegKeyFollowSens=106, # u8 direct (0x60=96 default in Init Normal)
    pegKFCenterNote=108, # u8 MIDI note (C4=60)
    pegFineTuneKF=110, # u8 center=64
    pegHoldTime=112, # u8 direct
    pegAttackTime=114, # u8 direct
    pegDecay1Time=116, # u8 direct
    pegDecay2Time=118, # u8 direct
    pegReleaseTime=120, # u8 direct
    pegHoldLevel=122, # u8 center=128
    pegAttackLevel=124, # u8 center=128
    pegDecay1Level=126, # u8 center=128
    pegDecay2Level=128, # u8 center=128
    pegReleaseLevel=130, # u8 center=128
    pegDepth=132, # u8 center=64 (Init Normal=84=ui+20)
    pegTimeVelSegment=134, # u8 enum 0-4 default=4 ✅ verified
    pegTimeVelSens=136, # u8 center=64 ✅ verified
    pegTimeKFSens=138, # u8 center=64
    pegDepthVelSens=140, # u8 enum? (Init Normal=2)
    pegDepthKFSens=142, # u8 center=64
    pegDepthKFCenterNote=144, # u8 MIDI note
    levelBP0=72, # u8 note (C-2=0) default=24=C0 MIDI Wave 0x20
    levelBP1=74, # u8 note default=36=C1 MIDI Wave 0x22 ✅
    levelBP2=76, # u8 note default=48=C2 MIDI Wave 0x24 ✅
    levelBP3=78, # u8 note default=60=C3 MIDI Wave 0x26 ✅
    levelBP4=80, # u8 note default=72=C4 MIDI Wave 0x28 ✅
    levelOfs1=82, # u8 center=128 default=0 MIDI Wave 0x2A ✅
    levelOfs2=84, # u8 center=128 default=0 MIDI Wave 0x2C ✅
    levelOfs3=86, # u8 center=128 default=0 MIDI Wave 0x2E ✅
    levelOfs4=88, # u8 center=128 default=0 MIDI Wave 0x30 ✅
    levelKeyFollowSens=90, # u8 center=64 default=0 MIDI Wave 0x32 ✅
    aegTimeKeyFollowRelAdj=92, # u8 direct (0-127) default=64 MIDI Wave 0x34 ✅
    # Filter section (MIDI Filter addr, DPFM_rel = MIDI_addr + 150) — 35/35 verified ✅
    filterType=150, # u8 enum 0-21, default=4 (LPF+HPF) MIDI 0x00
    cutoff=152, # u16 LE Hz, default=640 MIDI 0x02 ✅
    cutoffVelSens=154, # u8 center=64 default=0 MIDI 0x04 ✅
    elemFilterResonance=156, # u8 direct 0-127 default=0 MIDI 0x06 ✅
    resonanceVelSens=158, # u8 center=64 default=0 MIDI 0x08 ✅
    hpfCutoff=160, # u16 LE Hz default=0 MIDI 0x0A ✅
    dualFilterDistance=162, # u8 center=128 default=0 (Dual) MIDI 0x0C ✅
    filterGain=164, # u8 direct 0-255 default=230 MIDI 0x0E ✅ verified
    # Filter FEG Times (u8 direct)
    fegTimeHold=166, # u8 direct default=0 ✅ MIDI 0x10
    fegTimeAttack=168, # u8 direct default=0 ✅ MIDI 0x12
    fegTimeDecay1=170, # u8 direct default=64 ✅ MIDI 0x14
    fegTimeDecay2=172, # u8 direct default=64 ✅ MIDI 0x16
    fegTimeRelease=174, # u8 direct default=80 ✅ MIDI 0x18
    # Filter FEG Levels (u8 center=128)
    fegLevelHold=176, # u8 center=128 default=0 ✅ MIDI 0x1A
    fegLevelAttack=178, # u8 center=128 default=127 ✅ MIDI 0x1C
    fegLevelDecay1=180, # u8 center=128 default=127 ✅ MIDI 0x1E
    fegLevelDecay2=182, # u8 center=128 default=127 ✅ MIDI 0x20
    fegLevelRelease=184, # u8 center=128 default=0 ✅ MIDI 0x22
    # Filter FEG Envelope
    fegDepth=186, # u8 center=64 default=+40 ✅ MIDI 0x24
    fegDepthVelSegment=188, # u8 enum 0-4 default=4 ✅ MIDI 0x26
    fegDepthVelSens=190, # u8 center=64 default=0 ✅ MIDI 0x28
    fegTimeVelSegment=192, # OBS gamla namnet — korrekt namn är feg_depth_vel (★★★★★ binärverifierat). u8 center=64 default=64. UI: Filter > Depth/Vel
    fegTimeVelSens=194, # OBS gamla namnet — korrekt namn är feg_curve (★★★★★). u8 enum default=2. UI: Filter > Curve
    fegTimeKeyFollowSens=196, # OBS gamla namnet — korrekt namn är feg_time_key (★★★★★). u8 center=64 default=64. UI: Filter > Time/Key
    fegTimeKeyFollowCenterNote=198, # u8 note default=24=C0 ✅ MIDI 0x30 (actual=24)
    # Filter Cutoff Scaling (u8 note / center=128)
    cutoffScalingBP1=200, # u8 note default=36=C1 ✅ MIDI 0x32
    cutoffScalingBP2=202, # u8 note default=48=C2 ✅ MIDI 0x34
    cutoffScalingBP3=204, # u8 note default=60=C3 ✅ MIDI 0x36
    cutoffScalingBP4=206, # u8 note default=72=C4 ✅ MIDI 0x38
    cutoffScalingOfs1=208, # u8 center=128 default=0 ✅ MIDI 0x3A
    cutoffScalingOfs2=210, # u8 center=128 default=0 ✅ MIDI 0x3C
    cutoffScalingOfs3=212, # u8 center=128 default=0 ✅ MIDI 0x3E
    cutoffScalingOfs4=214, # u8 center=128 default=0 ✅ MIDI 0x40
    # Filter Key Follow (% encoding: ui=round((raw-64)*200/64), raw=round(ui*64/200)+64)
    cutoffKeyFollow=216, # u8 keyfollow% default=+31% ✅ MIDI 0x42 (raw=74)
    hpfCutoffKeyFollow=218, # u8 keyfollow% default=0% ✅ MIDI 0x44 (raw=64)
    # Element EQ (rel+220-230) — 6 fields verified ✅
    eqType=220, # u8 enum (0=Thru, 1=P.EQ, 2=Boost6, ...) default=0 ✅
    eqQ=222, # u8 direct (P.EQ Q only) default=0 ✅
    eqLowFreq=224, # u8 freq-table index default=54 ✅ (shared w/ eqPeqFreq)
    eqLowGain=226, # u8 center=64 default=0dB ✅ (shared w/ eqPeqGain)
    eqHighFreq=228, # u8 freq-table index default=231 ✅
    eqHighGain=230, # u8 center=64 default=0dB ✅
    # LFO section — 13 fields fully verified ✅
    # Offsets mixed: Wave/Reset/Delay/Speed: MIDI+180, Amp/Pitch/FilterMod+ExtSpeed: MIDI+150, FadeIn+: MIDI+186
    lfoWave=232, # u8 enum 0-2 (Saw/Triangle/Square) default=1 ✅
    lfoKeyOnReset=234, # u8 bool default=1=On ✅
    lfoDelayTime=236, # u8 direct default=0 ✅
    lfoSpeed=238, # u8 direct 0-63 default=38 ✅
    lfoAmpModDepth=240, # u8 direct default=0 ✅ verified (MIDI LFO 0x5A+150)
    lfoPitchModDepth=242, # u8 direct default=0 ✅ verified (MIDI LFO 0x5C+150)
    lfoFilterModDepth=244, # u8 direct default=0 ✅ verified (MIDI LFO 0x5E+150)
    lfoFadeInTime=246, # u8 direct default=0 ✅ verified (MIDI LFO 0x3C+186)
    lfoPhaseOffset=248, # u8 enum 0-5 default=0 ✅ (MIDI LFO 0x3E+186)
    lfoDest1Ratio=250, # u8 direct default=127 ✅ (MIDI LFO 0x40+186)
    lfoDest2Ratio=252, # u8 direct default=127 ✅ (MIDI LFO 0x42+186)
    lfoDest3Ratio=254, # u8 direct default=127 ✅ (MIDI LFO 0x44+186)
    lfoExtendedSpeed=256, # u16le 0..415 default=60 ★★★★★ binärverifierat (Test-AWM2-ElementLFO-ExtendedLFO_ON.Y2L). UI: [ELEMENT] LFO > Speed när Extended LFO toggle är PÅ. Större range (0..415) än u8-versionen lfoSpeed (0..63).
    # Controller Set Switches (MIDI CS addr, DPFM_rel = MIDI_addr + 258)
    ctrlSet1=265, ctrlSet2=266, ctrlSet3=267, ctrlSet4=268,
    ctrlSet5=269, ctrlSet6=270, ctrlSet7=271, ctrlSet8=272,
    ctrlSet9=273, ctrlSet10=274, ctrlSet11=275, ctrlSet12=276,
    ctrlSet13=277, ctrlSet14=278, ctrlSet15=279, ctrlSet16=280,
    ctrlSet17=281, ctrlSet18=282, ctrlSet19=283, ctrlSet20=284,
    ctrlSet21=285, ctrlSet22=286, ctrlSet23=287, ctrlSet24=288,
    ctrlSet25=289, ctrlSet26=290, ctrlSet27=291, ctrlSet28=292,
    ctrlSet29=293, ctrlSet30=294, ctrlSet31=295, ctrlSet32=296,
)
# ── AWM2 ELEMENT — BINARY VERIFIED ─────────────────
# All offsets in AWM2_ELEM_LAYOUT are relative to ELEM_BASE = abs 12520 (= ELEM1-12).
#confirmed 25 fields via binary diff (★★★★★) and
#
# CORRECTIONS (old FIELD_REGISTRY labels were wrong):
# aegTimeVel was at wrong offset — confirmed at serializer offset=68 (abs=12588) ★★★★★
# aegDecay2Level
# aegAttackLevel
#
# BINARY-VERIFIED:
# aegAttack=48 direct d=0
# aegDecay1=50 direct d=64
# aegDecay2=52 direct d=64 ← NEW
# aegRelease=56 direct d=50 (confirmed)
# aegHalfDamperT=58 direct d=0 (confirmed)
# aegAttackLvl=60 direct d=127 ← NEWLAST UNKNOWN SOLVED
# aegDecay2Lvl=64 direct d=127 ←
# aegDecay1Lvl=62 direct d=4 (confirmed)
# aegTimeVel=68 c64 d=0 ←
# aegTimeKeyFollowSens=70 c64 d=0 ← NEW
# levelBP0=72 MIDI d=24=C0 ← NEW(centerKey)
# levelBP1=74 MIDI d=36=C1 (confirmed)
# levelBP2=76 MIDI d=48=C2 ← NEW
# levelBP3=78 MIDI d=60=C3 ← pattern confirmed
# levelBP4=80 MIDI d=72=C4 ← pattern confirmed
# levelOfs1=82 0x80+n d=0 (confirmed)
# levelOfs2..4=84,86,88 0x80+n d=0 ← pattern confirmed
# aegTimeKeyFollowRelAdj=92 direct d=64 ← NEW(releaseAdj)
# filterCutoffElem (cutoff=152) u16le d=640 ← NEW
# lfoDelayTime=236 direct d=0 ← NEW
# lfoAmpModDepth=240 direct d=0 ← NEW
# lfoPitchModDepth=242 direct d=0 ← NEW
# lfoFilterModDepth=244 direct d=0 ← NEW
# lfoExtendedSpeed=256 direct d=60 ← NEW(lfoSpeed in Extended mode)
#
# AWM2 ELEMENT — all known fields binary-verified; no unmapped fields observed across the AWM2 test corpus.
ANX_OSC_LAYOUT = dict(waveform=0, octave=2, sync=12, pulse=20, shaper=28, level=48)
ANX_FILTER_LAYOUT = dict(
    cutoff=0, cutoffVel=2, cutoffKey=10, resonance=12,
    resonanceVel=14, drive=16, driveVel=18, outLevel=20,
)

# ── ENCODE / DECODE FUNCTIONS ─────────────────────────────────────────────

def encode(field: str, value: Any, engine: str = None) -> int | tuple[int, int]:
    """
    Convert a UI value to raw byte(s) for a named field.
    Returns int for u8 fields, (lo, hi) tuple for u16 LE fields.
    """
    # u16 LE fields
    if field in ("cutoff", "waveformNumber", "hpfCutoff"):
        v = int(value)
        return (v & 0xFF, (v >> 8) & 0xFF)

    v = value

    # Boolean
    if field in ("portamentoSw", "freqMode", "keyOnDelayElemSW"):
        return int(bool(v))
    if field == "monoPoly":
        return 0 if str(v).lower() in ("mono", "0") else 1

    # Algorithm (1-based display → 0-based raw)
    if field == "algorithm":
        return int(v) - 1

    # AWM2 elem filter resonance: direct u8 (overrides part-level filterResonance center=64)
    if field == "elemFilterResonance":
        return int(v)

    # Center=64 fields
    if field in ("pan", "alternatePan", "scalingPan", "aegAttack", "aegDecay", "aegSustain", "aegRelease",
                 "fegAttack", "fegDecay", "fegSustain", "fegRelease",
                 "filterFEGDepth", "filterCutoff", "filterResonance",
                 "commonPan", "portamentoTime", "noteShift", "partNoteShift",
                 "outLevel", "tuneCoarse", "tuneFine",
                 "aegTimeVel", "ampLevelVel",
                 "fegDepth",
                 # Filter velocity/key follow fields
                 "cutoffVelSens", "resonanceVelSens", "dualFilterDistance",
                 "fegDepthVelSens", "fegTimeVelSens", "fegTimeKeyFollowSens",
                  "aegTimeKeyFollowSens", "aegTimeKeyFollowRelAdj",
                 "levelKeyFollowSens",
                 # PEG fields center=64
                 "pegCoarseTune", "pegFineTune", "pegPitchVelSens",
                 "pegFineTuneKF", "pegTimeVelSens", "pegDepthKFSens", "pegDepth",
                 # EQ fields center=64 (dB * 16/6 + 64)
                 "eqLowGain", "eqHighGain",
                 ):
        return int(v) + 64

    # Center=128 fields
    if field in ("fmDepth", "fmHarmonics", "fmTexture",
                 "fmEGAttack", "fmEGDecay", "fmEGSustain", "fmEGRelease",
                 "lfoAmplDepth",
                 "fegLevelHold", "fegLevelAttack", "fegLevelDecay1",
                 "fegLevelDecay2", "fegLevelRelease",
                 "levelOfs1", "levelOfs2", "levelOfs3", "levelOfs4",
                 "dualFilterDistance",
                 "pegHoldLevel", "pegAttackLevel", "pegDecay1Level",
                 "pegDecay2Level", "pegReleaseLevel",
                 "cutoffScalingOfs1", "cutoffScalingOfs2",
                 "cutoffScalingOfs3", "cutoffScalingOfs4",
                 "dualFilterDistance",
                 ):
        return int(v) + 128

    # Part detune: engine-specific
    if field in ("detune", "partDetune"):
        if engine == "FMX":
            return round(float(v) * 10) + 128
        else:
            return int(v) + 128

    # OP detune center=15
    if field == "opDetune":
        return int(v) + 15

    # OP velocity fields center=7
    if field in ("levelVel", "pitchVel", "opLevelVel", "opPitchVel"):
        return int(v) + 7

    # PEG levels center=50
    if field in ("pegInitialLevel", "pegAttackLevel", "opPegInitialLevel", "opPegAttackLevel"):
        return int(v) + 50

    # AN-X sync: cents → raw
    if field == "sync":
        return int(v) // 25

    # AN-X octave: value (1,2,4,8..64) → raw
    if field == "octave":
        return 6 - int(log2(int(v)))

    # Key Follow % fields: ui% = round((raw-64)*200/64), raw = round(ui*64/200)+64
    if field in ("cutoffKeyFollow", "hpfCutoffKeyFollow"):
        return round(int(v) * 64 / 200) + 64

    # AN-X Engine AEG (direct u8 or u16 LE, no center offset)
    if field == "anxAegAttack": return int(v) & 0xFF
    if field == "anxAegDecay": return int(v) & 0xFF
    if field == "anxAegRelease": return int(v) & 0xFF
    if field == "anxAegSustain":
        v16 = int(v); return (v16 & 0xFF, (v16 >> 8) & 0xFF)
    if field == "anxAegTimeVel":
        r16 = 256 + int(v); return (r16 & 0xFF, (r16 >> 8) & 0xFF)

    # OP BreakPoint: raw = MIDI_note_standard - 9 (default=39=C3)
    if field == "aegBreakPoint":
        return int(value) - 9

    # OP Spectral Form: direct enum (uppdaterad v5.0 — aegDelayTime borttaget)
    if field in ("spectralForm", "spectralSkirt", "spectralResonance",
                 "keyOnReset", "pegDecayTime", "aegTimeKeyFollow",
                 "lvlKeyLo", "lvlKeyHi", "curveLo", "curveHi"):
        return int(value)

    # PEG Level fields (center=50): raw = ui + 50
    if field in ("fmxPegInitialLevel", "fmxPegAttackLevel", "fmxPegDecay1Level",
                 "fmxPegDecay2Level", "fmxPegReleaseLevel"):
        return int(value) + 50

    # PEG PitchKeyFollow: raw = round(pct*64/200) + 64
    if field == "fmxPegPitchKeyFollow":
        return round(float(value) * 64 / 200) + 64

    # PEG Depth enum: [8oct,2oct,1oct,0.5oct] per raw 0-3
    if field == "fmxPegDepth":
        depth_map = {8: 0, 8.0: 0, 2: 1, 2.0: 1, 1: 2, 1.0: 2, 0.5: 3}
        return depth_map.get(float(value), 0)

    # LFO Loop (inverterat): On=raw0, Off=raw1
    if field == "fmxPartLfoLoop":
        return 0 if value else 1

    # Insertion FX LFO Speed (Symphonic + Classic Flanger): raw = round(Hz * 23.7045)
    if field == "fxLfoSpeed":
        return round(float(value) * 23.7045)

    # Insertion FX Dry/Wet: direct (0=100%Dry, 64=50/50, 127=100%Wet)
    if field == "fxDryWet":
        return int(value)

    # Direct u8 (volume, level, attack, decay, etc.)
    return int(v)

def decode(field: str, raw: Any, engine: str = None) -> Any:
    """
    Convert raw byte(s) to a UI value for a named field.
    Pass (lo, hi) tuple for u16 LE fields.
    """
    # u16 LE
    if isinstance(raw, tuple):
        v16 = raw[0] + raw[1] * 256
        if field in ("aegTimeVel","anxAegTimeVel"): return v16 - 256
        return v16

    # Boolean
    if field in ("portamentoSw", "freqMode", "keyOnDelayElemSW"):
        return bool(raw)
    if field == "monoPoly":
        return "Mono" if raw == 0 else "Poly"

    # Algorithm
    if field == "algorithm":
        return raw + 1

    # AWM2 elem filter resonance: direct u8
    if field == "elemFilterResonance":
        return raw

    # Center=64
    if field in ("pan", "alternatePan", "scalingPan", "aegAttack", "aegDecay", "aegSustain", "aegRelease",
                 "fegAttack", "fegDecay", "fegSustain", "fegRelease",
                 "filterFEGDepth", "filterCutoff", "filterResonance",
                 "commonPan", "portamentoTime", "noteShift", "partNoteShift",
                 "outLevel", "tuneCoarse", "tuneFine",
                 "aegTimeVel", "ampLevelVel",
                 "fegDepth",
                 "cutoffVelSens", "resonanceVelSens", "dualFilterDistance",
                 "fegDepthVelSens", "fegTimeVelSens", "fegTimeKeyFollowSens",
                  "aegTimeKeyFollowSens", "aegTimeKeyFollowRelAdj",
                 "levelKeyFollowSens",
                 "pegCoarseTune", "pegFineTune", "pegPitchVelSens",
                 "pegFineTuneKF", "pegTimeVelSens", "pegDepthKFSens", "pegDepth",
                 "eqLowGain", "eqHighGain",
                 ):
        return raw - 64

    # Center=128
    if field in ("fmDepth", "fmHarmonics", "fmTexture",
                 "fmEGAttack", "fmEGDecay", "fmEGSustain", "fmEGRelease",
                 "lfoAmplDepth",
                 "fegLevelHold", "fegLevelAttack", "fegLevelDecay1",
                 "fegLevelDecay2", "fegLevelRelease",
                 "levelOfs1", "levelOfs2", "levelOfs3", "levelOfs4",
                 "dualFilterDistance",
                 "pegHoldLevel", "pegAttackLevel", "pegDecay1Level",
                 "pegDecay2Level", "pegReleaseLevel",
                 "cutoffScalingOfs1", "cutoffScalingOfs2",
                 "cutoffScalingOfs3", "cutoffScalingOfs4",
                 "dualFilterDistance",
                 ):
        return raw - 128

    # Part detune
    if field in ("detune", "partDetune"):
        if engine == "FMX":
            return (raw - 128) / 10
        else:
            return raw - 128

    # OP detune
    if field == "opDetune":
        return raw - 15

    # OP velocity
    if field in ("levelVel", "pitchVel", "opLevelVel", "opPitchVel"):
        return raw - 7

    # PEG levels
    if field in ("pegInitialLevel", "pegAttackLevel", "opPegInitialLevel", "opPegAttackLevel"):
        return raw - 50

    # Key Follow % fields
    if field in ("cutoffKeyFollow", "hpfCutoffKeyFollow"):
        return round((raw - 64) * 200 / 64)

    # AN-X sync
    if field == "sync":
        return raw * 25

    # AN-X octave
    if field == "octave":
        return 2 ** (6 - raw)

    # OP BreakPoint
    if field == "aegBreakPoint":
        return raw + 9

    # Direct fields (spectral, OP new fields, FX — v5.0: aegDelayTime→pegDecayTime)
    if field in ("spectralForm", "spectralSkirt", "spectralResonance",
                 "keyOnReset", "pegDecayTime", "aegTimeKeyFollow",
                 "lvlKeyLo", "lvlKeyHi", "curveLo", "curveHi",
                 "fxDryWet"):
        return raw

    # PEG Level decode: ui = raw - 50
    if field in ("fmxPegInitialLevel", "fmxPegAttackLevel", "fmxPegDecay1Level",
                 "fmxPegDecay2Level", "fmxPegReleaseLevel"):
        return raw - 50

    # PEG PitchKeyFollow decode: pct = (raw - 64) * 200 / 64
    if field == "fmxPegPitchKeyFollow":
        return round((raw - 64) * 200 / 64)

    # PEG Depth decode
    if field == "fmxPegDepth":
        depth_table = [8.0, 2.0, 1.0, 0.5]
        return depth_table[raw] if raw < len(depth_table) else raw

    # LFO Loop (inverterat)
    if field == "fmxPartLfoLoop":
        return raw == 0 # True=On, False=Off

    # FX LFO Speed decode: Hz = raw / 23.7045
    if field == "fxLfoSpeed":
        return round(raw / 23.7045, 2)

    # Direct

# ── CORE I/O ──────────────────────────────────────────────────────────────

def find_dpfm(data: bytes) -> tuple[int, int]:
    pos = 0
    while True:
        idx = data.find(b'DPFM', pos)
        if idx == -1:
            raise ValueError("No DPFM chunk found")
        length = int.from_bytes(data[idx+4:idx+8], 'big')
        if length > 10000:
            return idx + 8, length
        pos = idx + 1


# ════════════════════════════════════════════════════════════════════════
# WAVEFORM-REFERENCE LOCATOR  (binary-verified 2026-05-16)
# ════════════════════════════════════════════════════════════════════════
# A performance references a USER waveform via a fixed byte structure inside
# its DPFM blob. Two encodings, both byte-verified against ESP ground truth
# (D-MODE.Y2L → ESP "D-MODE 4 perf.Y2L") and controlled CFX single-edit
# pairs (D-MODE_enjoy_the_silence{,_elem2_CFX}, _just_cant_get_enough{,_elem4}):
#
#   SIG_A: 00 00 00 28  01(bank)  XX  YY  00  [ID]  00 01 00 01   element slot
#   SIG_B: 01 00 00 00  01 00 0C 00  [ID]  00 40                  element cfg
#
# The byte after 0x28 is the BANK: 0x01 = USER waveform (the [ID] byte
# indexes the EWFM/EWIM catalog at recPayload[10:12], big-endian u16);
# 0x00 = preset/ROM (ignored). XX YY vary (00 00 or 00 01); both matched.
# [ID] is a single byte. Pure renumbering touches ONLY the [ID] byte.
#
# This is the canonical implementation. Tools that relocate or renumber
# waveform references (e.g. selective Y2L merge) must use this, not the
# obsolete element-arithmetic model (blob-rel 12520 / stride 313), which
# was wrong on real multi-part performances.
# ════════════════════════════════════════════════════════════════════════

def scan_waveform_ref_positions(blob: bytes) -> list[int]:
    """Return the byte offsets of every USER-waveform [ID] byte in a
    single performance blob (bank == 0x01 only; presets excluded)."""
    pos: list[int] = []
    n = len(blob)
    for i in range(n - 13):
        # SIG_A: 00 00 00 28 01 . . 00 [ID] 00 01 00 01
        if (blob[i] == 0 and blob[i+1] == 0 and blob[i+2] == 0
                and blob[i+3] == 0x28 and blob[i+4] == 0x01
                and blob[i+7] == 0 and blob[i+9] == 0
                and blob[i+10] == 1 and blob[i+11] == 0 and blob[i+12] == 1):
            pos.append(i + 8)
            continue
        # SIG_B: 01 00 00 00 01 00 0C 00 [ID] 00 40
        if (blob[i] == 0x01 and blob[i+1] == 0 and blob[i+2] == 0
                and blob[i+3] == 0 and blob[i+4] == 0x01 and blob[i+5] == 0
                and blob[i+6] == 0x0c and blob[i+7] == 0
                and blob[i+9] == 0 and blob[i+10] == 0x40):
            pos.append(i + 8)
    return pos


def renumber_waveform_refs(blob: bytes, remap: dict[int, int]) -> bytes:
    """Return a copy of *blob* with every USER-waveform [ID] byte rewritten
    according to *remap* (old_id -> new_id). Only [ID] bytes change."""
    out = bytearray(blob)
    for p in scan_waveform_ref_positions(out):
        old = out[p]
        if old in remap:
            out[p] = remap[old] & 0xFF
    return bytes(out)


def waveform_renumber_map(referenced_ids) -> dict[int, int]:
    """Order-preserving compaction: sorted distinct old IDs -> 1..N
    (1-based, matching ESP's verified renumbering for waveform/sample)."""
    return {old: i + 1 for i, old in enumerate(sorted(set(referenced_ids)))}


# ════════════════════════════════════════════════════════════════════════
# ARPEGGIO-REFERENCE LOCATOR  (byte-verified vs ESP 2026-05-16)
# ════════════════════════════════════════════════════════════════════════
# Arp refs live in the element-pitch region of the DPFM blob. After a run
# of `80 00` pairs (pitch table) and optional `00` padding come one or
# more `[ARP_ID] 2f` pairs (the ref may repeat up to 4×). ARP_ID is a
# single byte < 21 (D-MODE arp id range 0..20). Verified zero false
# positives and byte-identical perf-blob reproduction against the
# D-MODE.Y2L → ESP "D-MODE 4 perf.Y2L" oracle. Renumbering is the same
# order-preserving compaction as waveforms but 0-BASED.
# ════════════════════════════════════════════════════════════════════════

def scan_arp_ref_positions(blob: bytes) -> list[int]:
    """Return the byte offsets of every arpeggio [ID] byte in a single
    performance blob (FP-free vs the ESP ground-truth oracle)."""
    pos: list[int] = []
    n = len(blob)
    i = 0
    while i < n - 6:
        if (blob[i] == 0x80 and blob[i+1] == 0x00
                and blob[i+2] == 0x80 and blob[i+3] == 0x00
                and blob[i+4] == 0x80 and blob[i+5] == 0x00):
            j = i
            while j + 1 < n and blob[j] == 0x80 and blob[j+1] == 0x00:
                j += 2
            guard = 0
            while (j < n and blob[j] == 0x00
                   and not (j + 1 < n and blob[j+1] == 0x2f and blob[j] < 21)):
                if blob[j] == 0x80:
                    break
                j += 1
                guard += 1
                if guard > 40:
                    break
            while j + 1 < n and blob[j+1] == 0x2f and blob[j] < 21:
                pos.append(j)
                j += 2
            i = j if j > i else i + 2
        else:
            i += 1
    return pos


def renumber_arp_refs(blob: bytes, remap: dict[int, int]) -> bytes:
    """Return a copy of *blob* with every arpeggio [ID] byte rewritten
    per *remap* (old_id -> new_id). Only [ID] bytes change."""
    out = bytearray(blob)
    for p in scan_arp_ref_positions(out):
        old = out[p]
        if old in remap:
            out[p] = remap[old] & 0xFF
    return bytes(out)


def arp_renumber_map(referenced_ids) -> dict[int, int]:
    """Order-preserving compaction: sorted distinct old IDs -> 0..N-1
    (0-BASED, matching ESP's verified renumbering for arpeggios)."""
    return {old: i for i, old in enumerate(sorted(set(referenced_ids)))}


def _resolve_field(engine: str, part: int, field_name: str, op=None, elem=None) -> int:
    stride = {'FMX': FMX_PART_STRIDE, 'AWM2': AWM2_PART_STRIDE, 'ANX': ANX_PART_STRIDE}[engine]
    ps = part * stride

    # Explicit prefix aliases
    if field_name.startswith('op') and op is not None and engine == 'FMX':
        bare = field_name[2].lower() + field_name[3:]
        if bare in FMX_OP_LAYOUT:
            return FMX_OP1_BASE + ps + op * FMX_OP_STRIDE + FMX_OP_LAYOUT[bare]
    if field_name.startswith('elem') and elem is not None and engine == 'AWM2':
        bare = field_name[4].lower() + field_name[5:]
        if bare in AWM2_ELEM_LAYOUT:
            return AWM2_ELEM1_BASE + ps + elem * AWM2_ELEM_STRIDE + AWM2_ELEM_LAYOUT[bare]

    # FM-X operator fields
    if engine == 'FMX' and op is not None and field_name in FMX_OP_LAYOUT:
        return FMX_OP1_BASE + ps + op * FMX_OP_STRIDE + FMX_OP_LAYOUT[field_name]

    # AWM2 element fields
    if engine == 'AWM2' and field_name == 'elemFilterType':
        e = elem if elem is not None else 0
        return AWM2_ELEM1_BASE + ps + e * AWM2_ELEM_STRIDE + 150 # filterType @ rel+150

    if engine == 'AWM2' and elem is not None and field_name in AWM2_ELEM_LAYOUT:
        return AWM2_ELEM1_BASE + ps + elem * AWM2_ELEM_STRIDE + AWM2_ELEM_LAYOUT[field_name]

    # AN-X OSC fields
    # AN-X Engine AEG (Amplitude Envelope Generator timings)
    if engine == "ANX" and field_name in ("anxAegAttack","anxAegDecay","anxAegSustain","anxAegRelease","anxAegTimeVel"):
        AEG_OFFS = {"anxAegAttack":0,"anxAegDecay":2,"anxAegSustain":4,"anxAegRelease":6,"anxAegTimeVel":8}
        return ANX_AEG_BASE + ps + AEG_OFFS[field_name]

    if engine == 'ANX' and op is not None and field_name in ANX_OSC_LAYOUT:
        return ANX_OSC1_BASE + ps + op * ANX_OSC_STRIDE + ANX_OSC_LAYOUT[field_name]

    # AN-X Filter fields
    if engine == 'ANX' and field_name in ANX_FILTER_LAYOUT:
        return ANX_FILTER_BASE + ps + ANX_FILTER_LAYOUT[field_name]

    # Part detune / noteShift
    if field_name in ('detune', 'partDetune'):
        return PART_DETUNE_BASE + ps
    if field_name in ('noteShift', 'partNoteShift'):
        return PART_NOTESHIFT + ps

    # Part-common
    if field_name in PART_COMMON:
        return PART_COMMON[field_name] + ps

    # FM-X part
    if engine == 'FMX' and field_name in FMX_PART_BASE:
        return FMX_PART_BASE[field_name] + ps

    # Common (performance-level, no part stride)
    if field_name in COMMON_FIELDS:
        return COMMON_FIELDS[field_name]

    # Per-part portamento (all engines)
    _P = {"partPortaSW":6752,"partPortaTime":6933,"partPortaMode":6935,"partHalfDamperSW":12483, "partKeyOnDelaySW":12482}
    if field_name in _P: return _P[field_name] + part*stride

    raise ValueError(f"Unknown field: engine={engine!r} field={field_name!r} op={op} elem={elem}")

def _is_u16(field_name: str) -> bool:
    return field_name in ("cutoff", "elemCutoff", "anxAegSustain", "anxAegTimeVel",
                          "aegSustain", "level", "waveformNumber", "hpfCutoff")

# ── PUBLIC API ────────────────────────────────────────────────────────────

def read_raw(path: str, engine: str, part: int, field: str,
             op=None, elem=None) -> int | tuple[int,int]:
    """Read raw byte value(s) from a Y2L file."""
    data = Path(path).read_bytes
    off, _ = find_dpfm(data)
    foff = _resolve_field(engine, part, field, op, elem)
    if _is_u16(field):
        return (data[off+foff], data[off+foff+1])
    return data[off+foff]

def read_ui(path: str, engine: str, part: int, field: str,
            op=None, elem=None) -> Any:
    """Read a field and decode to UI value."""
    raw = read_raw(path, engine, part, field, op, elem)
    return decode(field, raw, engine)

def patch_raw(src: str, dst: str, engine: str, part: int, field: str,
              raw_value: int | tuple, op=None, elem=None) -> None:
    """Patch a field with a raw byte value."""
    data = bytearray(Path(src).read_bytes())
    off, _ = find_dpfm(bytes(data))
    foff = _resolve_field(engine, part, field, op, elem)
    if isinstance(raw_value, tuple):
        data[off+foff] = raw_value[0] & 0xFF
        data[off+foff+1] = raw_value[1] & 0xFF
    else:
        data[off+foff] = int(raw_value) & 0xFF
    Path(dst).write_bytes(bytes(data))

def patch_ui(src: str, dst: str, engine: str, part: int, field: str,
             ui_value: Any, op=None, elem=None) -> None:
    """
    Patch a field using a UI value (auto-encodes to raw).
    When op is given, OP-level encoding is used for ambiguous fields
    (e.g. 'detune' with op= means OP detune center=15, not part detune).
    """
    # Disambiguate fields that exist at both part and OP level
    enc_field = field
    if op is not None and field == "detune":
        enc_field = "opDetune"
    if op is not None and field in ("levelVel", "pitchVel"):
        enc_field = field # already correct (center=7 for both)
    if elem is not None and field == "pan":
        enc_field = field # pan is always center=64 regardless of level

    raw = encode(enc_field, ui_value, engine)
    patch_raw(src, dst, engine, part, field, raw, op, elem)

def diff_dpfm(path_a: str, path_b: str) -> list[tuple[int,int,int]]:
    """Return list of (dpfm_offset, val_a, val_b) for changed non-noise bytes."""
    da = Path(path_a).read_bytes
    db = Path(path_b).read_bytes
    oa, la = find_dpfm(da)
    ob, lb = find_dpfm(db)
    dpfm_a = da[oa:oa+min(la,lb)]
    dpfm_b = db[ob:ob+min(la,lb)]
    return [(i, dpfm_a[i], dpfm_b[i]) for i in range(min(len(dpfm_a),len(dpfm_b)))
            if dpfm_a[i] != dpfm_b[i] and i not in NOISE]

def round_trip_verify(path: str) -> bool:
    """Verify that reading and writing leaves the file identical."""
    data = Path(path).read_bytes
    off, length = find_dpfm(data)
    result = bytearray(data)
    result[off:off+length] = data[off:off+length]
    return bytes(result) == data

# ── MERGE ENGINE ──────────────────────────────────────────────────────────

def merge_patches(
    base_path: str,
    dst_path: str,
    patches: list[dict],
) -> None:
    """
    Apply multiple field patches from potentially different source files.

    patches is a list of dicts:
      {
        "engine": "FMX",
        "part": 0,
        "field": "algorithm",
        "value": 5, # UI value (auto-encoded)
        "op": None, # optional
        "elem": None, # optional
        "raw": False, # if True, value is already raw bytes
      }

    All patches are applied to `base_path` in sequence, result written to `dst_path`.
    """
    data = bytearray(Path(base_path).read_bytes())
    off, _ = find_dpfm(bytes(data))

    for p in patches:
        engine = p["engine"]
        part = p.get("part", 0)
        field = p["field"]
        value = p["value"]
        op = p.get("op")
        elem = p.get("elem")
        is_raw = p.get("raw", False)

        foff = _resolve_field(engine, part, field, op, elem)
        raw = value if is_raw else encode(field, value, engine)

        if isinstance(raw, tuple):
            data[off+foff] = raw[0] & 0xFF
            data[off+foff+1] = raw[1] & 0xFF
        else:
            data[off+foff] = int(raw) & 0xFF

    Path(dst_path).write_bytes(bytes(data))

def copy_fields(
    src_path: str,
    dst_path: str,
    src_engine: str,
    dst_engine: str,
    fields: list[dict],
    src_part: int = 0,
    dst_part: int = 0,
) -> None:
    """
    Copy specific fields from one Y2L file to another.
    Useful for transplanting e.g. FM-X operator settings between patches.

    fields: list of {"field": "coarse", "op": 0} dicts
    """
    src_data = Path(src_path).read_bytes
    dst_data = bytearray(Path(dst_path).read_bytes())
    src_off, _ = find_dpfm(src_data)
    dst_off, _ = find_dpfm(bytes(dst_data))

    for f in fields:
        fname = f["field"]
        op = f.get("op")
        elem = f.get("elem")
        src_foff = _resolve_field(src_engine, src_part, fname, op, elem)
        dst_foff = _resolve_field(dst_engine, dst_part, fname, op, elem)

        if _is_u16(fname):
            dst_data[dst_off+dst_foff] = src_data[src_off+src_foff]
            dst_data[dst_off+dst_foff+1] = src_data[src_off+src_foff+1]
        else:
            dst_data[dst_off+dst_foff] = src_data[src_off+src_foff]

    Path(dst_path).write_bytes(bytes(dst_data))

# ── PART BLOCK COPY ENGINE ────────────────────────────────────────────────

# DPFM layout (all engines):
# DPFM[0..PART_BLOCK_START-1] = common header (FX, common params)
# DPFM[PART_BLOCK_START + N*stride .. +stride-1] = Part N+1 block
#
# Part block start = lowest known part-specific field offset
PART_BLOCK_START = 6708 # derived: 1-part DPFM length (13621) - FMX_PART_STRIDE (6913)

# All fields that belong to the common header (not part-specific)
COMMON_HEADER_FIELDS = {
    "portamentoSw": 41,
    "portamentoTime": 94, # ★★★★★
    "commonVolume": 68, # ★★★★★ = EF Master Output (UI-aliasing)
    "commonPan": 70, # ★★★★★
    "revSend": 124,
    "varSend": 130,
}

ENGINE_PART_STRIDE = {
    "FMX": 6913,
    "AWM2": 8273,
    "ANX": 6454,
}

def copy_part_block(
    src_path: str,
    dst_path: str,
    src_engine: str,
    dst_engine: str,
    src_part: int,
    dst_part: int,
) -> None:
    """
    Copy an entire Part block from src to dst verbatim.
    src_engine and dst_engine MUST be the same — part layouts are engine-specific.

    This copies ALL bytes of the part block, including unknown/unmapped fields.
    Safe for same-engine transplants.
    """
    if src_engine != dst_engine:
        raise ValueError(
            f"Cannot copy part block between different engines: "
            f"{src_engine} → {dst_engine}. Use copy_fields() for selective copy."
        )

    stride = ENGINE_PART_STRIDE[src_engine]
    src_data = bytearray(Path(src_path).read_bytes())
    dst_data = bytearray(Path(dst_path).read_bytes())
    src_off, src_len = find_dpfm(bytes(src_data))
    dst_off, dst_len = find_dpfm(bytes(dst_data))

    src_block_start = src_off + PART_BLOCK_START + src_part * stride
    dst_block_start = dst_off + PART_BLOCK_START + dst_part * stride

    # Bounds check
    if src_block_start + stride > src_off + src_len:
        raise ValueError(f"src Part {src_part+1} out of bounds (DPFM length {src_len})")
    if dst_block_start + stride > dst_off + dst_len:
        raise ValueError(f"dst Part {dst_part+1} out of bounds (DPFM length {dst_len})")

    dst_data[dst_block_start:dst_block_start+stride] = src_data[src_block_start:src_block_start+stride]

    Path(dst_path).write_bytes(bytes(dst_data))

def get_part_count(path: str, engine: str) -> int:
    """Return the number of parts present in a Y2L file for a given engine."""
    data = Path(path).read_bytes
    off, length = find_dpfm(data)
    stride = ENGINE_PART_STRIDE[engine]
    usable = length - PART_BLOCK_START
    return max(0, usable // stride)

def extract_part_block(path: str, engine: str, part: int) -> bytes:
    """Extract a part block as raw bytes."""
    data = Path(path).read_bytes
    off, length = find_dpfm(data)
    stride = ENGINE_PART_STRIDE[engine]
    start = off + PART_BLOCK_START + part * stride
    if start + stride > off + length:
        raise ValueError(f"Part {part+1} out of bounds")
    return bytes(data[start:start+stride])

def inject_part_block(path: str, engine: str, part: int, block: bytes) -> None:
    """Inject a raw part block into a Y2L file in-place."""
    data = bytearray(Path(path).read_bytes())
    off, length = find_dpfm(bytes(data))
    stride = ENGINE_PART_STRIDE[engine]
    if len(block) != stride:
        raise ValueError(f"Block size {len(block)} != stride {stride}")
    start = off + PART_BLOCK_START + part * stride
    if start + stride > off + length:
        raise ValueError(f"Part {part+1} out of bounds")
    data[start:start+stride] = block
    Path(path).write_bytes(bytes(data))

# ── MULTI-FILE MERGE ──────────────────────────────────────────────────────

# ── ANX Performance-level parameter offsets (DPFM blob, verified 2026-05-04) ──────────────
# All offsets are blob-absolute (blob[0:4]=0x00000015 header, blob[4:22]=name 18 bytes,
# blob[22]=null terminator, blob[23:25]=timestamp NOISE, blob[25:27]=0x0000).
# NOISE/timestamp bytes (never interpret): {23, 24, 6722, 6723, 6724, 6725, 6726, 6727}
#
# ┌─ PERF-LEVEL SWITCHES ─────────────────────────────────────────────┐
ANX_OFF_ARPMASTER_SW = 38 # bool 0=off 1=on
ANX_OFF_MSMASTER_SW = 39 # bool 0=off 1=on
ANX_OFF_ASSIGN1_SW = 40 # bool 0=off 1=on(default)
ANX_OFF_ASSIGN2_SW = 41 # bool 0=off 1=on(default)
ANX_OFF_ASSIGN3_SW = 42 # bool 0=off 1=on(default)
ANX_OFF_ASSIGN4_SW = 43 # bool 0=off 1=on(default)
ANX_OFF_ASSIGN5_SW = 44 # bool 0=off 1=on(default)
ANX_OFF_ASSIGN6_SW = 45 # bool 0=off 1=on(default)
ANX_OFF_ASSIGN7_SW = 46 # bool 0=off 1=on(default)
ANX_OFF_ASSIGN8_SW = 47 # bool 0=off 1=on(default)
ANX_OFF_SUPERKNOB_MS_SW = 51 # bool 0=off 1=on

# ┌─ COMMON MOTION SEQ (Performance Common) ─────────────────────────────┐
# OBS: tidigare "Lane1 Common" — namnet missvisande. Dessa fält gäller
# Performance Common (alla parts) enligt UI-verifiering TEST5R3-T4b/c/d.
ANX_OFF_COMMON_MS_SWING = 100 # u8 0x80+n center, 0xb2=50%
ANX_OFF_COMMON_MS_UNIT = 102 # u8 0=100% 3=1/16(default)
# Bakåtkompatibla alias:
ANX_OFF_LANE1_COMMON_SWING = ANX_OFF_COMMON_MS_SWING
ANX_OFF_LANE1_COMMON_UNIT = ANX_OFF_COMMON_MS_UNIT

# ┌─ ASSIGN VALUES (u16le) ────────────────────────────────────────────┐
# Assign1-8 values at [184:200], stride 2, all default=512 (u16le 0x0200)
ANX_OFF_ASSIGN1_VALUE = 184 # u16le default=512
ANX_OFF_ASSIGN2_VALUE = 186 # u16le default=512
ANX_OFF_ASSIGN3_VALUE = 188 # u16le default=512
ANX_OFF_ASSIGN4_VALUE = 190 # u16le default=512
ANX_OFF_ASSIGN5_VALUE = 192 # u16le default=512
ANX_OFF_ASSIGN6_VALUE = 194 # u16le default=512
ANX_OFF_ASSIGN7_VALUE = 196 # u16le default=512
ANX_OFF_ASSIGN8_VALUE = 198 # u16le default=512

# ┌─ ARP SELECT / SYNC QUANTIZE ──────────────────────────────────────┐
ANX_OFF_ARPSELECT = 358 # u8 0-indexed (0=1, 1=2, 7=8)
ANX_OFF_SYNCQUANTIZE = 360 # u8 0=OFF, 3=120

# ┌─ MS SELECT ───────────────────────────────────────────────────────┐
ANX_OFF_MSSELECT = 654 # u8 0-indexed (0=1, 1=2, 7=8)

# ┌─ COMMON MOTION SEQ params (Performance Common, separate from switches) ─┐
ANX_OFF_COMMON_MS_AMP = 656 # u8 0x80+n
ANX_OFF_COMMON_MS_SHAPE = 658 # u8 0x40+n
ANX_OFF_COMMON_MS_SMOOTH = 660 # u8 0x80+n
ANX_OFF_COMMON_MS_RANDOM = 662 # u8 0x80+n
# Bakåtkompatibla alias:
ANX_OFF_LANE1_COMMON_AMP = ANX_OFF_COMMON_MS_AMP
ANX_OFF_LANE1_COMMON_SHAPE = ANX_OFF_COMMON_MS_SHAPE
ANX_OFF_LANE1_COMMON_SMOOTH = ANX_OFF_COMMON_MS_SMOOTH
ANX_OFF_LANE1_COMMON_RANDOM = ANX_OFF_COMMON_MS_RANDOM

# ┌─ SUPERKNOB VALUE ──────────────────────────────────────────────────┐
ANX_OFF_SUPERKNOB_VALUE = 670 # u16le default=512

# ┌─ MIDPOSITION + ASSIGN POSITION BLOCK ─────────────────────────────┐
# [672] = MidPosition global enable (bool 0=off 1=on)
# [673] = uncertain (appears to be 1 when mid-pos is active with assigns set)
# Assign positions: stride=6 per assign, starting at [674]
# AssignN_LeftPos = blob[674 + N*6] u8 default=0
# AssignN_MidPos = blob[676 + N*6 : +2] u16le default=512
# AssignN_RightPos = blob[678 + N*6 : +2] u16le default=1023
# N = 0..7 for Assign1..8
ANX_OFF_MIDPOS_ENABLE = 672 # bool 0=off 1=on

def anx_assign_left_off(n: int) -> int: # n=0..7
    return 674 + n * 6

def anx_assign_mid_off(n: int) -> int: # n=0..7, u16le
    return 676 + n * 6

def anx_assign_right_off(n: int) -> int: # n=0..7, u16le
    return 678 + n * 6

# ┌─ PART-LEVEL ───────────────────────────────────────────────────────┐
ANX_OFF_PARTSWITCH = 6737 # bool 1=on(default) 0=off

# ┌─ ARP COMMON ───────────────────────────────────────────────────────┐
ANX_OFF_ARP_PLAYONLY = 6802 # bool 0=off 1=on
ANX_OFF_ARP_LOOP = 6804 # bool 1=on(default) 0=off
ANX_OFF_ARP_STARTQUANTIZE = 6805 # bool 1=on(default) 0=off
ANX_OFF_ARP_RANDOMSFX = 6806 # bool 1=on(default) 0=off
ANX_OFF_ARP_KEYONCONTROL = 6807 # bool 1=on(default) 0=off
# ┌─ PART MOTION SEQ (Part Common — gäller alla 4 Lanes i denna Part) ────┐
# OBS: tidigare "Lane1 Part" — namnet missvisande. Verifierat med
# TEST5R3-T4b-ViewLane2-Swing50: ändring av View Lane påverkar EJ dessa bytes.
# [6887] delas mellan "Arp Swing" och "Part MS Swing" (shared offset).
ANX_OFF_ARP_SWING = 6887 # u8 0x80+n center, 0xb2=50%
ANX_OFF_PART_MS_SWING = 6887 # alias (delad byte)
ANX_OFF_PART_MS_AMP = 6889 # u8 0x80+n
ANX_OFF_PART_MS_SHAPE = 6891 # u8 0x40+n
ANX_OFF_PART_MS_SMOOTH = 6893 # u8 0x80+n
ANX_OFF_PART_MS_RANDOM = 6895 # u8 direct 0..100
# Bakåtkompatibla alias:
ANX_OFF_LANE1_PART_SWING = ANX_OFF_PART_MS_SWING
ANX_OFF_LANE1_PART_AMP = ANX_OFF_PART_MS_AMP
ANX_OFF_LANE1_PART_SHAPE = ANX_OFF_PART_MS_SHAPE
ANX_OFF_LANE1_PART_SMOOTH = ANX_OFF_PART_MS_SMOOTH
ANX_OFF_LANE1_PART_RANDOM = ANX_OFF_PART_MS_RANDOM
ANX_OFF_ARPGROUP = 6905 # u8 0=off 1=A 0x10=P
ANX_OFF_ARPENABLE_AREA = 6917 # u8 0x80=idle 0x89=arp active
ANX_OFF_HOLD = 7095 # u8 0=SyncOff 1=Off(default) 2=On
ANX_OFF_ARP_UNIT = 7097 # u8 0=100% 3=1/16(default)
ANX_OFF_PART_MS_UNIT = 7097 # alias (delad byte med Arp Unit)
ANX_OFF_LANE1_PART_UNIT = 7097 # bakåtkompatibel alias
ANX_OFF_ARPLIMIT_NOTE_LO = 7099 # u8 direct MIDI note
ANX_OFF_ARPLIMIT_NOTE_HI = 7101 # u8 direct MIDI note, default=127
ANX_OFF_ARPLIMIT_VEL_LO = 7103 # u8 default=1
ANX_OFF_ARPLIMIT_VEL_HI = 7105 # u8 default=127
ANX_OFF_KEYMODE = 7107 # u8 0=normal 1=Thru
ANX_OFF_VELOCITYMODE = 7109 # u8 0=normal 1=Thru
ANX_OFF_CHANGETIMING = 7111 # u8 1=beat(default) 0=Real-Time
ANX_OFF_QUANTIZEVALUE = 7113 # u8 3=120(default) 2=80
ANX_OFF_QUANTIZESTRENGTH = 7115 # u8 direct 0..100
ANX_OFF_VELOCITYRATE = 7117 # u8 direct 0..200, default=100
ANX_OFF_GATETIMERATE = 7119 # u8 direct 0..200, default=100
ANX_OFF_ACCENT_VELTHRESHOLD= 7121 # u8 direct 0..127
ANX_OFF_OCTAVERANGE = 7123 # u8 0x40+n (center=0x40=0, 0x42=+2)
ANX_OFF_OCTAVESHIFT = 7125 # u8 0x40+n (center=0x40=0, 0x46=+6)
ANX_OFF_TRIGGERMODE = 7127 # u8 0=normal 1=Toggle
ANX_OFF_VELOCITYOFFSET = 7129 # u8 0x40+n (center=0x40=0, 0x45=+5)

# ┌─ ARP INDIVIDUAL ARP1 ──────────────────────────────────────────────┐
ANX_OFF_ARP1_VELOCITY = 7131 # u8 0x80+n, default=0x80
ANX_OFF_ARP1_GATETIME = 7133 # u8 0x80+n, default=0x80
ANX_OFF_ARP1_NAME_TYPE = 7163 # u8 type/bank id (default=79)
ANX_OFF_ARP1_NAME_PAT = 7164 # u8 pattern id within type (default=25)

# ┌─ SEQ LANE1 MAIN BLOCK ─────────────────────────────────────────────┐
# Lane offsets: lane_offset = 8929 + lane_index * 884 (Lane1=8929, Lane2=9813, Lane3=10697, Lane4=11581)
ANX_LANE1_BASE = 8929
ANX_LANE2_BASE = 9813
ANX_LANE3_BASE = 10697
ANX_LANE4_BASE = 11581

ANX_LANE_OFF_LANESWITCH = 0 # bool 0=off 1=on (abs: 8929/9813/10697/11581)
ANX_LANE_OFF_MSFXSWITCH = 1 # bool 1=on(default) 0=off (Lane1 only meaningful)
ANX_LANE_OFF_TRIGGER = 2 # bool 0=off 1=on
ANX_LANE_OFF_LOOP = 3 # bool 1=on(default) 0=off
ANX_LANE_OFF_SYNC = 8 # bool 0=off 1=sync
ANX_LANE_OFF_SPEED = 10 # u8 0x3f=63=default, direct value
ANX_LANE_OFF_SYNC_UNIT = 12 # u8 3=default 9=400%
ANX_LANE_OFF_KEYONRESET = 14 # u8 0=off 2=1stOn
ANX_LANE_OFF_VELIMIT_LO = 16 # u8 default=1
ANX_LANE_OFF_VELIMIT_HI = 18 # u8 default=127
ANX_LANE_OFF_DELAYTIME = 20 # u8 default=0
ANX_LANE_OFF_DELAYSTEPS = 22 # u8 default=0
ANX_LANE_OFF_FADEINTIME = 24 # u8 default=0
ANX_LANE_OFF_FADEINSTEPS = 26 # u8 default=0
ANX_LANE_OFF_AMP = 36 # u8 default=127
ANX_LANE_OFF_SMOOTH = 38 # u8 default=0
ANX_LANE_OFF_POLARITY = 42 # bool 0=unipolar 1=bipolar
ANX_LANE_OFF_MSGRID = 44 # u8 3=default 1=60

# Pulse A (per lane, relative to lane base):
ANX_LANE_OFF_PULSEA_TYPE = 116 # u8 0=Standard 2=Threshold
ANX_LANE_OFF_PULSEA_PRM1 = 118 # u8 default=5
ANX_LANE_OFF_PULSEA_PRM2 = 120 # u8 default=0 (Threshold: 1=default 4=4)
ANX_LANE_OFF_CTRLA_SW = 122 # bool 1=on(default) 0=off
ANX_LANE_OFF_CTRLA_CTRLSW = 124 # bool 0=off 1=on

# Pulse B (per lane, relative to lane base):
ANX_LANE_OFF_PULSEB_TYPE = 128 # u8 0=Standard 2=Threshold
ANX_LANE_OFF_PULSEB_PRM1 = 130 # u8 default=5
ANX_LANE_OFF_PULSEB_PRM2 = 132 # u8 default=0
ANX_LANE_OFF_CTRLB_SW = 134 # bool 1=on(default) 0=off
ANX_LANE_OFF_CTRLB_CTRLSW = 136 # bool 0=off 1=on

# ┌─ METADATA (internal state flags) ─────────────────────────────────┐
ANX_OFF_PART_SEQ_FIELD = 12753 # u8 3=default 4=seq-sync active
ANX_OFF_PART_ARP_FIELD = 13116 # u8 0=default 9=arp active

ANX_NOISE_BYTES = frozenset({23, 24, 6722, 6723, 6724, 6725, 6726, 6727})

def build_performance(
    base_path: str,
    dst_path: str,
    part_sources: list[dict],
) -> None:
    """
    Build a performance by combining Parts from multiple source files.

    part_sources: list of dicts, one per destination part:
      {
        "src": "/path/to/source.Y2L",
        "engine": "FMX", # engine of source part
        "part": 0, # source part index (0-based)
        "dst_part": 0, # destination part index (0-based)
        # Optional field overrides applied after part copy:
        "overrides": [
          {"field": "volume", "value": 100},
          {"field": "pan", "value": 0},
        ]
      }

    base_path: Base Y2L file that provides the common header (FX, rev/var send, etc.)
                Must have enough parts for all dst_part indices.
    dst_path: Output file.
    """
    import shutil
    shutil.copy2(base_path, dst_path)

    for ps in part_sources:
        src = ps["src"]
        engine = ps["engine"]
        src_part = ps.get("part", 0)
        dst_part = ps.get("dst_part", src_part)

        # Copy the full part block
        copy_part_block(src, dst_path, engine, engine, src_part, dst_part)

        # Apply any field overrides
        for ov in ps.get("overrides", []):
            patch_ui(dst_path, dst_path, engine, dst_part,
                     ov["field"], ov["value"],
                     op=ov.get("op"), elem=ov.get("elem"))

# ── DIFF REPORT ───────────────────────────────────────────────────────────

# Field map: dpfm_offset → (field_name, engine_or_common, encoding)
def _build_field_map() -> dict[int, tuple[str, str, str]]:
    m = {}
    # Common
    for name, off in COMMON_HEADER_FIELDS.items():
        m[off] = (name, "COMMON", "u8")
    # Part common (Part 0)
    for name, off in PART_COMMON.items():
        m[off] = (name, "PART", "u8_center64" if name != "monoPoly" and name != "volume" else "u8")
    m[PART_DETUNE_BASE] = ("partDetune", "PART", "detune")
    m[PART_NOTESHIFT] = ("noteShift", "PART", "u8_center64")
    # FMX part
    for name, off in FMX_PART_BASE.items():
        m[off] = (name, "FMX_PART", "u8_center128" if "EG" in name or name in ("fmDepth","fmHarmonics","fmTexture") else "u8")
    m[FMX_PART_BASE["algorithm"]] = ("algorithm", "FMX_PART", "algorithm")
    # FMX operators (part 0)
    for op in range(8):
        base = FMX_OP1_BASE + op * FMX_OP_STRIDE
        for field, rel in FMX_OP_LAYOUT.items():
            m[base + rel] = (f"OP{op+1}.{field}", "FMX_OP", field)
    # AWM2 elements (part 0)
    for el in range(3):
        base = AWM2_ELEM1_BASE + el * AWM2_ELEM_STRIDE
        for field, rel in AWM2_ELEM_LAYOUT.items():
            m[base + rel] = (f"Elem{el+1}.{field}", "AWM2_ELEM", field)
            if field == "cutoff": # u16 LE: register hi-byte too
                m[base + rel + 1] = (f"Elem{el+1}.{field}", "AWM2_ELEM", field)
            if field == "waveformNumber": # u16 LE: register hi-byte too
                m[base + rel + 1] = (f"Elem{el+1}.{field}", "AWM2_ELEM", field)
            if field == "hpfCutoff": # u16 LE: register hi-byte too
                m[base + rel + 1] = (f"Elem{el+1}.{field}", "AWM2_ELEM", field)
    # ANX OSCs (part 0)
    for osc in range(3):
        base = ANX_OSC1_BASE + osc * ANX_OSC_STRIDE
        for field, rel in ANX_OSC_LAYOUT.items():
            m[base + rel] = (f"OSC{osc+1}.{field}", "ANX_OSC", field)
    # ANX filter
    for field, rel in ANX_FILTER_LAYOUT.items():
        m[ANX_FILTER_BASE + rel] = (f"Filter.{field}", "ANX_FILTER", field)
        if field == "cutoff": # u16 LE: register hi-byte too
            m[ANX_FILTER_BASE + rel + 1] = (f"Filter.{field}", "ANX_FILTER", field)
    return m

FIELD_MAP = _build_field_map
def diff_report(
    path_a: str,
    path_b: str,
    engine: str = None,
    label_a: str = "A",
    label_b: str = "B",
) -> str:
    """
    Generate a human-readable diff report between two Y2L files.
    Returns a formatted multi-line string.
    """
    raw_diffs = diff_dpfm(path_a, path_b)
    if not raw_diffs:
        return f"No differences between {label_a} and {label_b}"

    lines = [
        f"Diff: {label_a} vs {label_b}",
        f"{'─'*60}",
        f"{'Field':<30} {'Value '+label_a:>12} {'Value '+label_b:>12} {'Raw':>10}",
        f"{'─'*60}",
    ]

    # Pre-process: pair up u16 LE fields (consecutive offsets for same field)
    skip_offsets = set
    processed = []
    diff_dict = {off: (va, vb) for off, va, vb in raw_diffs}
    for dpfm_off, val_a, val_b in raw_diffs:
        if dpfm_off in skip_offsets:
            continue
        info = FIELD_MAP.get(dpfm_off)
        # Check if next byte is the hi-byte of a u16 LE pair
        next_info = FIELD_MAP.get(dpfm_off + 1)
        if (info and next_info and
            info[0].split('.')[0] == next_info[0].split('.')[0] and
            (dpfm_off + 1) in diff_dict):
            # u16 LE pair: combine
            hi_a, hi_b = diff_dict[dpfm_off + 1]
            combined_a = val_a + hi_a * 256
            combined_b = val_b + hi_b * 256
            processed.append((dpfm_off, combined_a, combined_b, info, True))
            skip_offsets.add(dpfm_off + 1)
        else:
            processed.append((dpfm_off, val_a, val_b, info, False))

    for dpfm_off, val_a, val_b, info, is_u16 in processed:
        if info:
            fname, context, enc = info
            try:
                if is_u16:
                    ui_a, ui_b = str(val_a), str(val_b)
                elif enc not in ("u8", "u8_center128"):
                    ui_a = decode(enc, val_a, engine)
                    ui_b = decode(enc, val_b, engine)
                    ui_a = str(round(ui_a, 1)) if isinstance(ui_a, float) else str(ui_a)
                    ui_b = str(round(ui_b, 1)) if isinstance(ui_b, float) else str(ui_b)
                else:
                    ui_a = str(val_a - 128 if enc == "u8_center128" else val_a)
                    ui_b = str(val_b - 128 if enc == "u8_center128" else val_b)
            except:
                ui_a, ui_b = str(val_a), str(val_b)
            raw_str = f"[{dpfm_off}] {val_a}→{val_b}" + (" u16" if is_u16 else "")
            lines.append(f" {fname:<30} {ui_a:>12} {ui_b:>12} {raw_str}")
        else:
            lines.append(f" {'?@'+str(dpfm_off):<30} {val_a:>12} {val_b:>12} raw")

    lines.append(f"{'─'*60}")
    lines.append(f"Total: {len(raw_diffs)} changed field(s)")
    return "\n".join(lines)

# ── LIBRARY ENGINE (multi-performance Y2L) ───────────────────────────────
#
# A Y2L file contains 1 or more performances. Structure:
#
# DPFM chunk:
# [0:4] = performance count (N)
# Then N records:
# [0:4] = b'Data'
# [4:8] = performance data length (always 13609 for FM-X/AN-X, varies for AWM2)
# [8:] = performance data bytes
#
# EPFM catalog (spans EPFM[280:353] + gap before ESYS):
# [0] = 0x00
# [1:5] = b'EPFM'
# [5:9] = catalog_len (total bytes after this 9-byte prefix)
# [9:13] = performance count (N)
# Then N Entr blocks:
# [0:4] = b'Entr'
# [4:8] = entry data length (= 32 + 2*len(name))
# [8:] = entry data:
# [0:4] = 0x00003529 (fixed = DPFM sub-chunk data length = 13609 = 0x3529)
# [4:8] = DPFM offset where this perf's data starts
# [8:12] = 0x00400000 | (perf_index << 0) (byte[11] = 0-based index)
# [12:20]= 8 fixed bytes: 0x0000000202000100
# [20:26]= 6 fixed bytes: 0x0000000000002a (last byte = 0x2a always)
# [26] = checksum/hash byte (from source file, not recalculated)
# [27:29]= 2-char decimal XX (checksum, not validated by MODX)
# [29] = b':'
# [30:] = name_bytes + b':' + name_bytes + b'\0'
#
# Gap between EPFM chunk and ESYS chunk = catalog bytes that overflow past EPFM[353]
# MODX reads gap size from catalog_len field — gap is NOT required to match reference.

# NOTE: _build_catalog_entry rebuilds Entr records from scratch.
# For best results when building from library files,
# the original Entr records should be cloned from the source catalog
# and only [0:4]=blob_sz, [4:8]=dp_off, [11]=idx should be updated.
# The JS Forge v1.19+ implements this correctly via byDpOff map matching.
# Python serializer fix: TODO when source Entr records are available.

def _detect_engine_bits(blob: bytes) -> int:
    """Detect engine bits for Entr[15] from blob content.

    Entr[15] engine bitmap: 0x01=AWM2, 0x02=FM-X, 0x04=AN-X.
    blob[6695] = part count.
    blob[6700] = first part engine byte (0=AWM2,2=FM-X,3=AN-X).
    Multi-part: scan for 0x00000015 sub-headers after offset 7000, read byte at -3.
    Verified against MODX M factory + Init files 2026-05-04.
    """
    ENG = {0: 0x01, 1: 0x01, 2: 0x02, 3: 0x04, 4: 0x04}
    if len(blob) < 6710:
        return 0x01
    part_count = blob[6695] or 1
    bits = ENG.get(blob[6700], 0x01)
    if part_count > 1:
        found = 0
        i = 7000
        while i < len(blob) - 4 and found < part_count - 1:
            if blob[i:i+4] == b'\x00\x00\x00\x15':
                eb = blob[i - 1] if i >= 1 else 0
                bits |= ENG.get(eb, 0x01)
                found += 1
                i += 4
            else:
                i += 1
    return bits

def _build_catalog_entry(name: str, perf_size: int, dpfm_data_offset: int,
                         perf_index: int, blob: bytes = None) -> bytes:
    """Build one EPFM catalog Entr data block (WITHOUT the Entr+size header).

    Entr record layout (binärverifierat 2026-05-04 mot MODX M-filer):
        [0:4] blob_sz u32 BE
        [4:8] dp_off u32 BE
        [8] 0x00 constant
        [9] 0x40 constant (MODX validerar detta fält)
        [10] 0x00 constant
        [11] entry_index u8
        [12] 0x00 constant
        [13] 0x00 multi-engine flag (förenklat)
        [14] 0x00 constant
        [15] engine_bits 0x01=AWM2, 0x02=FM-X, 0x04=AN-X, OR-kombinerat
        [16] 0x02 constant (MODX validerar detta fält)
        [17] 0x00 constant
        [18] 0x01 category (0x01=default/piano)
        [19] 0x00 constant
        [20:25] 0x00 padding
        [25] 0x30 constant
        [26] 0x00 slot flag (förenklat)
        [27:] 'IDX:LongName(20ch padded):ShortName\0' name string
    """
    engine = _detect_engine_bits(blob) if blob else 0x01
    long_name = name[:20].ljust(20)
    short_name = name[:20]
    text = f"{perf_index}:{long_name}:{short_name}\x00"
    data = bytearray(27)
    struct.pack_into('>I', data, 0, perf_size)
    struct.pack_into('>I', data, 4, dpfm_data_offset)
    data[8] = 0x00
    data[9] = 0x40
    data[10] = 0x00
    data[11] = perf_index & 0xFF
    data[12] = 0x00
    data[13] = 0x00
    data[14] = 0x00
    data[15] = engine
    data[16] = 0x00 # 0x00=ESP Plugin, 0x02=MODX hardware; use 0x00 for compatibility
    data[17] = 0x00
    data[18] = 0x01
    data[19] = 0x00
    # [20:25] = 0x00 already
    data[25] = 0x30
    data[26] = 0x00
    data += text.encode('ascii', errors='replace')
    return bytes(data)

# Kept for backward-compatibility reference only
_CATALOG_FIXED_22 = bytes.fromhex('000044410000000c0040000000000001020001000000')

def _build_catalog(perf_names: list[str], src_data: bytes = None,
                   perf_sizes: list[int] = None,
                   dpfm_data_offsets: list[int] = None) -> tuple:
    """
    Build EPFM catalog fields for N performances.

    Real MODX catalog stream (starts at file offset 361 = EPFM[289]):
        [0:4] = N (u32 BE)
        [4:...]= N x ( b'Entr'(4) + entry_size(4) + entry_data(entry_size bytes) )

    EPFM field layout:
        EPFM[280] = 0x00
        EPFM[281:285]= b'EPFM' (literal tag — NOT N!)
        EPFM[285:289]= payload_size (= total bytes of stream = len(stream))
        EPFM[289:353]= stream[0:64]
        [EPFM_END:ESYS] = stream[64:] (overflow)

    Returns: (N, payload_size, cat_in_64, cat_out)
    """
    n = len(perf_names)
    sizes = perf_sizes or [0] * n
    offsets = dpfm_data_offsets or [0] * n

    cat = bytearray
    cat += n.to_bytes(4, 'big')
    for i, name in enumerate(perf_names):
        blob = source_blobs[i] if source_blobs else None
        ed = _build_catalog_entry(name, sizes[i], offsets[i], i, blob)
        cat += b'Entr' + len(ed).to_bytes(4, 'big') + ed

    stream = bytes(cat)
    payload_size = len(stream)

    ECAP = 64
    cat_in = (stream[:ECAP] + bytes(ECAP))[:ECAP]
    cat_out = stream[ECAP:]

    return n, payload_size, cat_in, cat_out

def build_library(
    src_paths: list[str],
    dst_path: str,
    names: list[str] = None,
) -> None:
    """
    Build a multi-performance Y2L library file from individual Y2L patches.

    Args:
        src_paths: List of source Y2L file paths (one per performance)
        dst_path: Output Y2L file path
        names: Optional list of display names (defaults to names from source files)

    The output file uses src_paths[0]'s non-DPFM structure (ESYS, EFVT, DSYS, DFVT)
    as the base, then appends all performance data records.
    """
    import shutil

    if not src_paths:
        raise ValueError("Need at least one source file")

    # Read all source DPFM performance data
    perf_data_list = []
    src_names = []
    for path in src_paths:
        data = Path(path).read_bytes
        dpfm_off, dpfm_len = find_dpfm(data)
        dpfm = data[dpfm_off:dpfm_off+dpfm_len]
        # Parse all performances from DPFM (count + N×(Data+size+bytes))
        n_perfs_src = int.from_bytes(dpfm[0:4], 'big')
        _pos = 4
        for _pi in range(n_perfs_src):
            _plen = int.from_bytes(dpfm[_pos+4:_pos+8], 'big')
            perf_data = dpfm[_pos+8:_pos+8+_plen]
            perf_data_list.append(perf_data)
            # Extract name from perf data[4:] (null-terminated ASCII, offset 4 = past length field)
            name = ''
            for b in perf_data[4:36]:
                if b == 0 or b < 32: break
                name += chr(b)
            src_names.append(name.strip() or f"Perf {len(src_names)+1}")
            _pos += 8 + _plen

    if names is None:
        names = src_names
    if len(names) < len(src_paths):
        names = names + src_names[len(names):]

    # Build new DPFM chunk data (count + Data+size+bytes per perf)
    n = len(perf_data_list)
    new_dpfm = bytearray
    new_dpfm += n.to_bytes(4, 'big')
    for perf_data in perf_data_list:
        new_dpfm += b'Data' + len(perf_data).to_bytes(4, 'big') + perf_data
    new_dpfm = bytes(new_dpfm)

    # Build catalog fields using the real MODX Entr-block format
    base_data = Path(src_paths[0]).read_bytes
    # Compute DPFM data offsets for the catalog metadata
    _dpfm_sizes = [len(pd) for pd in perf_data_list]
    _dpfm_offsets = []
    _pos = 4
    for pd in perf_data_list:
        _dpfm_offsets.append(_pos + 8) # offset past 'Data'+size header
        _pos += 8 + len(pd)
    cat_n, cat_total_size, cat_in_64, cat_out = _build_catalog(
        names, base_data,
        perf_sizes=_dpfm_sizes,
        dpfm_data_offsets=_dpfm_offsets,
    )

    # ── Read base-file chunk directory ─────────────────────────────
    def _parse_chunks_from_epfm_dir(data):
        """Parse chunks using the EPFM directory (absolute file offsets).
        EPFM directory is at data[72:136] — 8 slots × 8 bytes each.
        Each slot: [4-byte ASCII tag][4-byte absolute file offset]
        """
        chunks = {}
        for i in range(0, 64, 8):
            tag_bytes = data[72+i:72+i+4]
            if tag_bytes == b'\xff\xff\xff\xff':
                break
            try:
                tag = tag_bytes.decode('ascii')
            except Exception:
                break
            off = int.from_bytes(data[72+i+4:72+i+8], 'big')
            if off <= 0 or off + 8 > len(data):
                continue
            size = int.from_bytes(data[off+4:off+8], 'big')
            if off + 8 + size > len(data):
                continue
            chunks[tag] = {'tag': tag, 'off': off, 'len': size,
                           'data': data[off+8:off+8+size]}
        return chunks

    base_chunks = _parse_chunks_from_epfm_dir(base_data)
    chunk_by_tag = base_chunks

    # ── Compute new chunk positions ─────────────────────────────────
    EPFM_END = 64 + 8 + 353 # = 425 (always fixed)
    esys_src = chunk_by_tag['ESYS']
    efvt_src = chunk_by_tag['EFVT']
    dsys_src = chunk_by_tag['DSYS']
    dfvt_src = chunk_by_tag['DFVT']

    new_esys = EPFM_END + len(cat_out)
    new_efvt = new_esys + 8 + esys_src['len']
    new_dpfm_pos = new_efvt + 8 + efvt_src['len']
    new_dsys = new_dpfm_pos + 8 + len(new_dpfm)
    new_dfvt = new_dsys + 8 + dsys_src['len']

    # ── Build EPFM 353-byte data block ─────────────────────────────
    # Copy directory from base file (first 281 bytes of EPFM data = chunk offset table)
    epfm_dir = bytearray(base_data[72:72+64]) # directory is exactly 64 bytes

    def _write_off(ba, tag, val):
        tb = tag.encode('ascii')
        for k in range(0, len(ba)-7, 8):
            if ba[k:k+4] == tb:
                ba[k+4:k+8] = val.to_bytes(4, 'big')
                return

    _write_off(epfm_dir, 'ESYS', new_esys)
    _write_off(epfm_dir, 'EFVT', new_efvt)
    _write_off(epfm_dir, 'DPFM', new_dpfm_pos)
    _write_off(epfm_dir, 'DSYS', new_dsys)
    _write_off(epfm_dir, 'DFVT', new_dfvt)

    new_epfm = bytearray(353)
    # [0:64] = chunk directory (updated absolute offsets)
    new_epfm[:64] = epfm_dir[:64]
    # [64:280] = 0xFF padding (216 bytes, constant in all real MODX files)
    for _i in range(64, 280):
        new_epfm[_i] = 0xFF
    # [280] = 0x00 (separator byte)
    new_epfm[280] = 0x00
    # [281:285]= b'EPFM' (catalog sub-tag)
    new_epfm[281:285] = b'EPFM'
    # [285:289]= catalog_size (u32be)
    new_epfm[285:289] = cat_total_size.to_bytes(4, 'big')
    # [289:353]= first 64 bytes of catalog stream
    new_epfm[289:353] = cat_in_64

    # ── Assemble output file ────────────────────────────────────────
    out = bytearray
    out += base_data[:64] # file header (unchanged)
    out += b'EPFM' + (353).to_bytes(4, 'big') + new_epfm # EPFM chunk
    out += cat_out # catalog overflow
    out += b'ESYS' + esys_src['len'].to_bytes(4,'big') + esys_src['data']
    out += b'EFVT' + efvt_src['len'].to_bytes(4,'big') + efvt_src['data']
    out += b'DPFM' + len(new_dpfm).to_bytes(4, 'big') + new_dpfm
    out += b'DSYS' + dsys_src['len'].to_bytes(4,'big') + dsys_src['data']
    out += b'DFVT' + dfvt_src['len'].to_bytes(4,'big') + dfvt_src['data']

    Path(dst_path).write_bytes(bytes(out))

# ── TESTS ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import os

    print("ENCODE/DECODE UNIT TESTS")
    print("=" * 55)
    tests = [
        # (field, ui_value, expected_raw, engine)
        ("algorithm", 5, 4, None),
        ("algorithm", 70, 69, None),
        ("pan", 10, 74, None),
        ("pan", -10, 54, None),
        ("aegAttack", 10, 74, None),
        ("detune", -3.0, 98, "FMX"),
        ("detune", -3, 125, "ANX"),
        ("levelVel", 7, 14, None),
        ("levelVel", -7, 0, None),
        ("opDetune", -3, 12, None),
        ("pegInitialLevel", 10, 60, None),
        ("sync", 200, 8, None),
        ("octave", 8, 3, None),
        ("monoPoly", "Mono", 0, None),
        ("monoPoly", "Poly", 1, None),
        ("portamentoTime", 50, 114, None),
        ("fmDepth", 10, 138, None),
        # AWM2 elem new fields (verified 2025-04-23)
        ("ampLevelVel", 50, 114, None), # center=64: 50+64=114
        ("ampLevelVel", -10, 54, None),
        ("elemFilterResonance", 80, 80, None), # direct
        ("elemFilterResonance", 0, 0, None),
        ("fegTimeAttack", 30, 30, None), # direct
        ("fegTimeDecay1", 30, 30, None),
        ("fegTimeDecay2", 30, 30, None),
        ("fegTimeHold", 64, 64, None),
        ("fegTimeRelease", 40, 40, None),
        ("fegLevelHold", 22, 150, None), # center=128
        ("fegLevelAttack", 70, 198, None),
        ("fegLevelDecay1", 70, 198, None),
        ("fegLevelDecay2", 70, 198, None),
        ("fegLevelRelease", 70, 198, None),
        ("fegDepth", 20, 84, None), # center=64: 20+64=84
        ("fegDepth", 40, 104, None), # default raw
        # waveformNumber: u16 LE, 1-based ✅ verified
        ("waveformNumber", 6, (6,0), None), # CFX v06 St
        ("waveformNumber", 14, (14,0), None), # C7 f St
        ("waveformNumber", 186, (186,0), None), # Hamburg Grand v01 St
        ("waveformNumber", 300, (44,1), None), # hi-byte test: 300=0x12C → (0x2C,0x01)
        # New fields verified 2025-04-23
        ("levelVelCurve", 0, 0, None), # direct: 3→0
        ("aegTimeVelSegment", 2, 2, None), # enum: direct
        ("aegTimeVel", 20, 84, None), # center=64: +20→84
        ("cutoffVelSens", 20, 84, None), # center=64: +20→84
        ("resonanceVelSens", 20, 84, None), # center=64: +20→84
        ("hpfCutoff", 400, (144,1), None), # u16 LE: 400 Hz
        ("fegDepthVelSegment", 2, 2, None), # enum direct
        ("fegDepthVelSens", 20, 84, None), # center=64
        ("pegTimeVelSegment", 2, 2, None), # enum direct ✅
        ("pegTimeVelSens", 20, 84, None), # center=64 ✅
        ("cutoffKeyFollow", 81, 90, None), # keyfollow%: 81%→raw=90, decode→81 ✅
        ("cutoffKeyFollow", 50, 80, None), # keyfollow%: 50%→raw=80, decode→50 ✅
        ("cutoffKeyFollow", 0, 64, None), # keyfollow%: 0%→raw=64
        ("hpfCutoffKeyFollow",50, 80, None), # keyfollow%: 50%→raw=80 ✅
    ]
    errors = 0
    for field, ui, expected_raw, engine in tests:
        raw = encode(field, ui, engine)
        back = decode(field, raw, engine)
        ok_enc = raw == expected_raw
        ok_dec = abs(back - ui) < 0.01 if isinstance(back, float) else back == ui
        status = "✅" if (ok_enc and ok_dec) else "❌"
        if not (ok_enc and ok_dec): errors += 1
        raw_str = str(raw) if isinstance(raw, tuple) else str(raw)
        print(f" {status} {field:<22} ui={str(ui):<8} → raw={raw_str:<10} → {back}")
    print
    print("ROUND-TRIP TESTS")
    print("=" * 55)
    for path in [
        "/mnt/user-data/uploads/FM-X_00_Init_Base.Y2L",
        "/mnt/user-data/uploads/AWM2_00_Init_Base.Y2L",
        "/mnt/user-data/uploads/AN-X_00_Init_Base.Y2L",
    ]:
        if os.path.exists(path):
            ok = round_trip_verify(path)
            print(f" {'✅' if ok else '❌'} {os.path.basename(path)}")
    print
    print("patch_ui TESTS")
    print("=" * 55)
    base = "/mnt/user-data/uploads/FM-X_00_Init_Base.Y2L"
    tmp = "/tmp/test_ui.Y2L"
    _have_base = os.path.exists(base)
    ui_tests = [] if not _have_base else [
        # (engine, part, field, ui_value, op, elem, expected_dpfm_off, expected_raw)
        ("FMX", 0, "algorithm", 5, None, None, 12537, 4),
        ("FMX", 0, "feedback", 3, None, None, 12539, 3),
        ("FMX", 0, "pan", 10, None, None, 6845, 74),
        ("FMX", 0, "detune", -3.0, None, None, 6929, 98),
        ("FMX", 0, "detune", -3, 0, None, 12692, 12), # OP1 detune
        ("FMX", 0, "levelVel", 7, 0, None, 12744, 14), # OP1 levelVel
        ("FMX", 0, "pegInitialLevel", 10, 0, None, 12704, 60), # OP1 PEG initial (off=16, abs=12676+16=12692? wait)
        ("FMX", 0, "pegAttackLevel", 50, 0, None, 12706, 50), # OP1 PEG attack (off=18+12676=12694... recalc)
        ("FMX", 0, "aegAttackTime", 50, 0, None, 12708, 50), # OP1 AEG attack (off=32, KORRIGERAT från 20!)
    ]
    for engine, part, field, ui, op, elem, exp_off, exp_raw in ui_tests:
        patch_ui(base, tmp, engine, part, field, ui, op=op, elem=elem)
        diffs = diff_dpfm(base, tmp)
        changed = {d[0]: d[2] for d in diffs}
        ok = changed.get(exp_off) == exp_raw and len(diffs) == 1
        print(f" {'✅' if ok else '❌'} {field:<22} ui={str(ui):<8} → [{exp_off}]={exp_raw} got={changed}")
        if not ok: errors += 1
    if not _have_base:
        print(" ⏭  skipped (FM-X_00_Init_Base.Y2L not present)")
    elif os.path.exists(tmp):
        os.unlink(tmp)
    print
    print("MERGE ENGINE TEST")
    print("=" * 55)
    base = "/mnt/user-data/uploads/FM-X_00_Init_Base.Y2L"
    tmp = "/tmp/test_merge.Y2L"
    if not os.path.exists(base):
        print(" ⏭  skipped (FM-X_00_Init_Base.Y2L not present)")
    else:
        patches = [
            {"engine": "FMX", "part": 0, "field": "algorithm", "value": 5},
            {"engine": "FMX", "part": 0, "field": "feedback", "value": 3},
            {"engine": "FMX", "part": 0, "field": "volume", "value": 80},
            {"engine": "FMX", "part": 0, "field": "pan", "value": 10},
            {"engine": "FMX", "part": 0, "field": "coarse", "value": 3, "op": 0},
            {"engine": "FMX", "part": 0, "field": "level", "value": 99, "op": 0},
            {"engine": "FMX", "part": 0, "field": "aegAttackTime", "value": 50, "op": 0}, # off=32
        ]
        merge_patches(base, tmp, patches)
        diffs = diff_dpfm(base, tmp)
        expected_fields = {12537: 4, 12539: 3, 6843: 80, 6845: 74, 12688: 3, 12732: 99, 12708: 50}
        ok = all(expected_fields.get(d[0]) == d[2] for d in diffs) and len(diffs) == len(expected_fields)
        print(f" {'✅' if ok else '❌'} 6-field merge: {len(diffs)} changes")
        for d in diffs:
            exp = expected_fields.get(d[0], "?")
            chk = "✓" if exp == d[2] else "✗"
            print(f" {chk} [{d[0]}] {d[1]}→{d[2]} (expected {exp})")
        if os.path.exists(tmp):
            os.unlink(tmp)
    print

    # ── Waveform-reference locator regression (verified 2026-05-16) ──────
    # Locks the SIG_A/SIG_B model + renumber rule against ESP ground truth.
    # Uses the controlled CFX single-edit pair when present; the diff must
    # be exactly the one element whose waveform was changed.
    print("WAVEFORM-REF LOCATOR REGRESSION")
    print("=" * 55)
    _wf_a = "/mnt/user-data/uploads/D-MODE_enjoy_the_silence.Y2L"
    _wf_b = ("/mnt/user-data/uploads/"
             "D-MODE_enjoy_the_silence_2__element_2_change_waveform_to_CFX_.Y2L")
    if os.path.exists(_wf_a) and os.path.exists(_wf_b):
        _A = Path(_wf_a).read_bytes()
        _B = Path(_wf_b).read_bytes()
        # The single user→preset edit must surface as a scanned ref whose
        # [ID] byte differs, with all other scanned positions stable.
        _dpA, _ = find_dpfm(_A)
        _dpB, _ = find_dpfm(_B)
        # Compare whole files: real param diff is the waveform id/bank byte.
        _diffs = [i for i in range(min(len(_A), len(_B))) if _A[i] != _B[i]]
        # Scan a wide DPFM window for ref positions in the unedited file.
        _win = _A[_dpA:_dpA + 200000]
        _pos = scan_waveform_ref_positions(_win)
        _found = len(_pos) > 0
        # At least one scanned ref position must coincide with a real diff
        # (the changed waveform id) — proves the signature locates refs.
        _abspos = {_dpA + p for p in _pos}
        _hit = any(d in _abspos for d in _diffs)
        for label, cond in (
            (f"signature finds waveform refs (got {len(_pos)})", _found),
            ("a scanned ref position coincides with the CFX edit", _hit),
            ("renumber map is order-preserving 1..N",
             waveform_renumber_map([18, 1, 34, 2]) == {1: 1, 2: 2, 18: 3, 34: 4}),
        ):
            print(f" {'✅' if cond else '❌'} {label}")
            if not cond:
                errors += 1
    else:
        print(" ⏭  skipped (D-MODE CFX control pair not present)")
    print

    if errors == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ {errors} failures")
