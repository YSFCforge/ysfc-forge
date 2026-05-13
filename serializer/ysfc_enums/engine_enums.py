"""
YSFC Forge — Engine-Specific Enum Definitions

Engine-specifika dropdown-värden från MODX M / ESP Plugin UI.
Källa: ESP Plugin skärmdumpar + binärverifierade tester.

Status efter skärmdump-genomgång (2026-05-10):
- AN-X OSC Waveforms: ★★★★★ (5 alternativ)
- AN-X Filter Types (Type1+Type2): ★★★★★ (11 alternativ, samma för båda)
- AN-X LFO Wave Shape: ★★★★★ (13 alternativ inkl User)
- AWM2 Element LFO Wave: ★★★★★ (3 alternativ)
- AWM2 Part LFO Wave: ★★★★★ (13 alternativ inkl User)
- FM-X Algorithm: ★★★★★ (1-88)
- FM-X Spectral Form: ★★★★★ (7 alternativ)
- CA Curve Types: ★★★★★ (20 presets + 32 user)
- Drum Engine: parametrar per key (ej "elements")
"""

# ──────────────────────────────────────────────────────────────────────
# AN-X ENGINE
# ──────────────────────────────────────────────────────────────────────

# AN-X OSC Waveform — 5 alternativ ★★★★★
# Default: Saw1
# Källa: ESP UI screenshot
ANX_OSC_WAVEFORMS = {
    0: 'Saw1',
    1: 'Saw2',
    2: 'Square',
    3: 'Triangle',
    4: 'Sine',
}

# AN-X Filter Types — 11 alternativ ★★★★★
# Type1 default: LPF24
# Type2 default: HPF24
# SAMMA dropdown för båda Type1 och Type2
# Källa: ESP UI screenshot
ANX_FILTER_TYPES = {
    0:  'Thru',
    1:  'LPF24',
    2:  'LPF18',
    3:  'LPF12',
    4:  'LPF6',
    5:  'HPF24',
    6:  'HPF18',
    7:  'HPF12',
    8:  'HPF6',
    9:  'BPF12',
    10: 'BPF6',
}

# Alias för båda typer (samma lista)
ANX_FILTER_TYPE1 = ANX_FILTER_TYPES
ANX_FILTER_TYPE2 = ANX_FILTER_TYPES

# AN-X LFO Wave Shape — 13 alternativ ★★★★★
# Default: Triangle
# Källa: ESP UI screenshot (Part LFO)
ANX_LFO_SHAPES = {
    0:  'Triangle',
    1:  'Triangle+',
    2:  'Saw Up',
    3:  'Saw Down',
    4:  'Squ1/4',
    5:  'Squ1/3',
    6:  'Square',
    7:  'Squ2/3',
    8:  'Squ3/4',
    9:  'Trapezoid',
    10: 'S/H1',
    11: 'S/H2',
    12: 'User',
}


# ──────────────────────────────────────────────────────────────────────
# AWM2 ENGINE
# ──────────────────────────────────────────────────────────────────────

# AWM2 Filter Types — 22 entries (binärverifierat tidigare)
AWM2_FILTER_TYPES = {
    0:  'LPF24D',
    1:  'LPF18D',
    2:  'LPF12D',
    3:  'LPF6D',
    4:  'LPF+HPF',
    5:  'BPF',
    6:  'BPFw',
    7:  'BPF12D',
    8:  'BEF',
    9:  'BEF12D',
    10: 'HPF24D',
    11: 'HPF12D',
    12: 'DualLPF',
    13: 'DualHPF',
    14: 'DualBPF',
    15: 'DualBEF',
    16: 'LPF12+BPF6',
    17: 'Thru',
    18: 'LPF24A',
    19: 'LPF18A',
    20: 'HPF24A',
    21: 'HPF18A',
}

# AWM2 Element LFO Wave — BARA 3 alternativ ★★★★★
# Default: Triangle
# Källa: ESP UI screenshot
# OBS: Element-nivåns LFO är ENKLARE än Part-nivåns!
AWM2_ELEMENT_LFO_WAVES = {
    0: 'Saw',
    1: 'Triangle',
    2: 'Square',
}

# AWM2 Part LFO Wave — 13 alternativ ★★★★★
# Default: Triangle
# SAMMA dropdown som AN-X Part LFO
AWM2_PART_LFO_WAVES = {
    0:  'Triangle',
    1:  'Triangle+',
    2:  'Saw Up',
    3:  'Saw Down',
    4:  'Squ1/4',
    5:  'Squ1/3',
    6:  'Square',
    7:  'Squ2/3',
    8:  'Squ3/4',
    9:  'Trapezoid',
    10: 'S/H1',
    11: 'S/H2',
    12: 'User',
}

# AWM2 Element switch
AWM2_ELEMENT_SWITCH = {0: 'Off', 1: 'On'}


# ──────────────────────────────────────────────────────────────────────
# FM-X ENGINE
# ──────────────────────────────────────────────────────────────────────

# Antal FM-X algoritmer
FMX_ALGORITHM_COUNT = 88

# FM-X Algorithm-numrering (1-88)
FMX_ALGORITHMS = {i: f'Algorithm {i}' for i in range(1, 89)}

# FM-X OP Spectral Form — 7 alternativ ★★★★★
# Default: Sine
# Källa: ESP UI screenshot
FMX_SPECTRAL_FORM = {
    0: 'Sine',
    1: 'All 1',
    2: 'All 2',
    3: 'Odd 1',
    4: 'Odd 2',
    5: 'Res 1',
    6: 'Res 2',
}

# OP On/Off
FMX_OP_SWITCH = {0: 'Off', 1: 'On'}


# ──────────────────────────────────────────────────────────────────────
# DRUM ENGINE
# ──────────────────────────────────────────────────────────────────────

# Notera: Drum-engine har INTE "elements" som AWM2 (8 elements) eller
# AN-X (3 OSC). Istället har Drum 73 KEYS, en per MIDI-not (typiskt C0-C6).
# Varje key är en självständig "ljud-enhet" med sin egen wave + parametrar.
#
# Per-key parametrar inkluderar:
# - Wave (val från Waveform List)
# - Pitch, Pan, Volume
# - AEG (Attack/Decay/Sustain/Release)
# - Filter (Cutoff/Resonance)
# - Receive Note On/Off
# - Reverse On/Off
# - Velocity Limit
# - Drum Group (för "choke groups")
# 
# Drum-engine har därför INGA "element types" som behöver en enum-lista.

# Drum Key Receive Note On/Off
DRUM_KEY_RECEIVE_NOTE = {0: 'Off', 1: 'On'}

# Drum Key Reverse Playback
DRUM_KEY_REVERSE = {0: 'Off', 1: 'On'}

# Drum Key Switch (key on/off)
DRUM_KEY_SWITCH = {0: 'Off', 1: 'On'}


# ──────────────────────────────────────────────────────────────────────
# CONTROL ASSIGN (CA) ENUMS
# ──────────────────────────────────────────────────────────────────────

# CA Curve Type-mod (Preset eller User)
CA_CURVE_TYPE_MODE = {0: 'Preset', 1: 'User'}

# CA Curve Types — Preset: 20 alternativ ★★★★★
# Default: Standard
# Källa: ESP UI screenshot
CA_CURVE_PRESETS = {
    0:  'Standard',
    1:  'Sigmoid',
    2:  'Threshold',
    3:  'Bell',
    4:  'Dogleg',
    5:  'FM',
    6:  'AM',
    7:  'M',
    8:  'Discrete Saw',
    9:  'Smooth Saw',
    10: 'Triangle',
    11: 'Square',
    12: 'Trapezoid',
    13: 'Tilt Sine',
    14: 'Bounce',
    15: 'Resonance',
    16: 'Sequence',
    17: 'Hold',
    18: 'Harmonic',
    19: 'Steps',
}

# CA Curve Types — User: 32 alternativ ★★★★★
# Default-namn: "Init Curve N"
# Källa: ESP UI screenshot
CA_CURVE_USERS = {i: f'Init Curve {i+1}' for i in range(32)}

# CA Polarity
CA_POLARITY = {0: 'Uni', 1: 'Bi'}

# Backward-compat alias
CURVE_TYPES = CA_CURVE_PRESETS
POLARITY = CA_POLARITY


# ──────────────────────────────────────────────────────────────────────
# COMMON ENUMS (samma över alla engines)
# ──────────────────────────────────────────────────────────────────────

# On/Off (universal)
ON_OFF = {0: 'Off', 1: 'On'}

# MIDI Channel (för Tx Rx Ch)
MIDI_CHANNELS = {
    **{i: f'Ch {i+1}' for i in range(16)},
    127: 'Off',
}

# Receive Switch (alla per-part)
RECEIVE_SWITCH = {0: 'Off', 1: 'On'}

# Scene number
SCENE_NUMBERS = {i: f'Scene {i+1}' for i in range(8)}

# Pan (c64 encoding: 0=L64, 64=Center, 127=R63)
def encode_pan(ui_value):
    """UI -64 to +63 → byte 0-127."""
    return max(0, min(127, ui_value + 64))

def decode_pan(byte_value):
    """Byte 0-127 → UI -64 to +63."""
    return byte_value - 64

def pan_label(byte_value):
    """Returns UI label like 'L64', 'C', 'R63'."""
    ui = decode_pan(byte_value)
    if ui < 0: return f'L{-ui}'
    if ui > 0: return f'R{ui}'
    return 'C'


# EQ Type (Master EQ Low/High)
EQ_TYPE = {0: 'Shelf', 1: 'Peak'}

# Reverb/Variation/Master FX ON/OFF (default 1)
FX_ON_OFF = {0: 'Off', 1: 'On'}

# Side Chain
SIDE_CHAIN = {0: 'Off', 1: 'On'}

# Hardware Ribbon Mode (abs 33)
RIBBON_MODE = {0: 'Reset', 1: 'Hold'}

# Hardware Ribbon Slider Direction (abs 57)
SLIDER_DIRECTION = {0: 'Normal', 1: 'Reverse'}

# Ribbon Grid Mode (abs 216)
RIBBON_GRID_MODE = {
    0: 'Continuous',
    1: '5-step',
    2: '3-step',
}

# Ribbon Assign Mode (abs 30, 31)
RIBBON_ASSIGN_MODE = {0: 'Momentary', 1: 'Latch'}


# ──────────────────────────────────────────────────────────────────────
# AN-X MODIFIER (Wave Folder + Modifier Wave)
# ──────────────────────────────────────────────────────────────────────

# AN-X Wave Folder Type — 2 alternativ ★★★★★
# Två-knappsväljare i UI (Soft/Hard)
# Källa: ESP UI screenshot
ANX_FOLDER_TYPES = {
    0: 'Soft',
    1: 'Hard',
}

# AN-X Modifier Wave — 5 alternativ ★★★★★
# Default: Triangle
# Källa: ESP UI screenshot
ANX_MODIFIER_WAVES = {
    0: 'Saw',
    1: 'Square',
    2: 'Triangle',
    3: 'Sine',
    4: 'Random',
}


# ──────────────────────────────────────────────────────────────────────
# Backward-compat aliases (gamla namn från v1.0)
# ──────────────────────────────────────────────────────────────────────

# AWM2_LFO_WAVES — gammalt namn, peka på Element-nivå för tydlighet
# Använd nya AWM2_ELEMENT_LFO_WAVES eller AWM2_PART_LFO_WAVES
AWM2_LFO_WAVES = AWM2_ELEMENT_LFO_WAVES


if __name__ == '__main__':
    print("Engine-specific enums (efter skärmdump-genomgång 2026-05-10):")
    print(f"  AN-X OSC Waveforms:        {len(ANX_OSC_WAVEFORMS)} ★★★★★")
    print(f"  AN-X Filter Types:         {len(ANX_FILTER_TYPES)} ★★★★★ (Type1=Type2)")
    print(f"  AN-X LFO Shapes:           {len(ANX_LFO_SHAPES)} ★★★★★")
    print(f"  AN-X Wave Folder Types:    {len(ANX_FOLDER_TYPES)} ★★★★★")
    print(f"  AN-X Modifier Waves:       {len(ANX_MODIFIER_WAVES)} ★★★★★")
    print(f"  AWM2 Filter Types:         {len(AWM2_FILTER_TYPES)} (binärverifierat tidigare)")
    print(f"  AWM2 Element LFO Waves:    {len(AWM2_ELEMENT_LFO_WAVES)} ★★★★★")
    print(f"  AWM2 Part LFO Waves:       {len(AWM2_PART_LFO_WAVES)} ★★★★★")
    print(f"  FM-X Algorithms:           {len(FMX_ALGORITHMS)} ★★★★★")
    print(f"  FM-X Spectral Form:        {len(FMX_SPECTRAL_FORM)} ★★★★★")
    print(f"  CA Curve Presets:          {len(CA_CURVE_PRESETS)} ★★★★★")
    print(f"  CA Curve User:             {len(CA_CURVE_USERS)} ★★★★★")
    print(f"  Common: ON_OFF, MIDI_CHANNELS, EQ_TYPE, etc.")
