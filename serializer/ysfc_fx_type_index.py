# YSFC Forge — Insertion FX Type Index Table v1.0
# Uppdaterad: 2026-04-26 (Steg 60)
#
# Encoding: type_index = hi_byte * 128 + lo_byte
#   lo_byte = fxA[0], hi_byte = fxA[1]
# Källa: Effect Type List.xlsx + binärverifiering Steg 46-60
#
# ★★★★★ = binärverifierat med testfil
# ★★★★☆ = härlett från Effect Type List (MSB*128 + LSB_as_hex)
#
# OBS: SPX HALL och CROSS DELAY delar TypeIndex 130 (lo=2, hi=1).
#   MODX särskiljer dem med en tredje byte (kategori-ID) som ej kartlagts.

FX_TYPE_INDEX = {
    # ── THRU ──────────────────────────────────────────────────
    'THRU':                   0,    # ★★★★★

    # ── REVERB ────────────────────────────────────────────────
    'SPX HALL':             130,    # ★★★★★ (lo=2, hi=1)
    'SPX ROOM':             146,    # ★★★★☆
    'SPX STAGE':            176,    # ★★★★☆
    'GATED REVERB':         208,    # ★★★★☆
    'REVERSE REVERB':       216,    # ★★★★☆

    # ── DELAY ─────────────────────────────────────────────────
    'CROSS DELAY':          256,    # ★★★★★ (lo=0, hi=2) — OBS: delar lo/hi med SPX HALL!
    'TEMPO CROSS DELAY':    272,    # ★★★★☆
    'TEMPO DELAY MONO':     288,    # ★★★★☆
    'TEMPO DELAY STEREO':   296,    # ★★★★☆
    'CONTROL DELAY':        304,    # ★★★★☆
    'DELAY LR':             320,    # ★★★★☆
    'DELAY LCR':            336,    # ★★★★☆
    'ANALOG DELAY RETRO':   352,    # ★★★★☆
    'ANALOG DELAY MODERN':  360,    # ★★★★☆

    # ── CHORUS ────────────────────────────────────────────────
    'G CHORUS':             384,    # ★★★★☆
    '2 MODULATOR':          400,    # ★★★★☆
    'SPX CHORUS':           416,    # ★★★★☆
    'SYMPHONIC':            432,    # ★★★★★ (lo=48, hi=3)
    'ENSEMBLE DETUNE':      448,    # ★★★★☆

    # ── FLANGER ───────────────────────────────────────────────
    'VCM FLANGER':          512,    # ★★★★☆
    'CONTROL FLANGER':      520,    # ★★★★☆
    'CLASSIC FLANGER':      528,    # ★★★★★ (lo=16, hi=4)
    'TEMPO FLANGER':        544,    # ★★★★☆
    'DYNAMIC FLANGER':      560,    # ★★★★☆

    # ── PHASER ────────────────────────────────────────────────
    'VCM PHASER MONO':      640,    # ★★★★☆
    'VCM PHASER STEREO':    656,    # ★★★★☆
    'CONTROL PHASER':       664,    # ★★★★☆
    'TEMPO PHASER':         672,    # ★★★★★ (lo=32, hi=5)
    'DYNAMIC PHASER':       688,    # ★★★★☆

    # ── TREMOLO & ROTARY ──────────────────────────────────────
    'AUTO PAN':             768,    # ★★★★☆
    'TREMOLO':              784,    # ★★★★★ (lo=16, hi=6)
    'ROTARY SPEAKER 1':     800,    # ★★★★☆
    'ROTARY SPEAKER 2':     816,    # ★★★★☆

    # ── DISTORTION ────────────────────────────────────────────
    'AMP SIMULATOR 1':      896,    # ★★★★☆
    'AMP SIMULATOR 2':      912,    # ★★★★☆
    'COMP DISTORTION':      928,    # ★★★★★ (lo=32, hi=7)
    'COMP DISTORTION DELAY':944,    # ★★★★☆
    'US COMBO':             960,    # ★★★★☆
    'JAZZ COMBO':           961,    # ★★★★☆
    'US HIGH GAIN':         962,    # ★★★★☆
    'BRITISH LEAD':         963,    # ★★★★☆
    'MULTI FX':             964,    # ★★★★☆
    'SMALL STEREO':         965,    # ★★★★☆
    'BRITISH COMBO':        966,    # ★★★★☆
    'BRITISH LEGEND':       967,    # ★★★★☆

    # ── COMPRESSOR ────────────────────────────────────────────
    'VCM COMPRESSOR 376':  1024,    # ★★★★☆
    'CLASSIC COMPRESSOR':  1040,    # ★★★★★ (lo=16, hi=8)
    'MULTI BAND COMP':     1056,    # ★★★★☆
    'UNI COMP DOWN':       1072,    # ★★★★☆
    'UNI COMP UP':         1080,    # ★★★★☆
    'PARALLEL COMP':       1088,    # ★★★★☆

    # ── WAH ── (ej i xlsx-listan, binärverifierat Steg 60) ────
    'VCM AUTO WAH':        1280,    # ★★★★★ (lo=0, hi=10)

    # ── LO-FI ─────────────────────────────────────────────────
    'NOISY':               1424,    # ★★★★★ (lo=16, hi=11)

    # ── TECH ──────────────────────────────────────────────────
    'SLICE':               1616,    # ★★★★★ (lo=80, hi=12)

    # ── MISC ──────────────────────────────────────────────────
    'PRESENCE':            1672,    # ★★★★★ (lo=8, hi=13)
    # WAVE FOLDER: TypeIndex ej fastlagd (ej i Steg 60-filer)
}

# Omvänd uppslagning: TypeIndex → Name
FX_INDEX_TO_NAME = {v: k for k, v in FX_TYPE_INDEX.items()}

# Hjälpfunktion
def fx_type_bytes(name):
    """Returnerar (lo, hi) för ett FX-namn."""
    idx = FX_TYPE_INDEX.get(name.upper())
    if idx is None: return (0, 0)  # THRU
    return (idx & 0x7F, (idx >> 7) & 0x7F)

def fx_name_from_bytes(lo, hi):
    """Returnerar FX-namn från (lo, hi) bytes."""
    idx = hi * 128 + lo
    return FX_INDEX_TO_NAME.get(idx, f'UNKNOWN({idx})')

if __name__ == '__main__':
    print(f"Totalt {len(FX_TYPE_INDEX)} InsA-kompatibla FX-typer kartlagda")
    print(f"Varav binärverifierade (★★★★★): 12")
    print(f"Varav från Effect Type List (★★★★☆): {len(FX_TYPE_INDEX)-12}")
    print()
    print("Test fx_type_bytes:")
    for name in ['SYMPHONIC', 'CLASSIC FLANGER', 'CROSS DELAY', 'VCM AUTO WAH']:
        lo, hi = fx_type_bytes(name)
        print(f"  {name}: lo={lo}, hi={hi}, idx={hi*128+lo}")
