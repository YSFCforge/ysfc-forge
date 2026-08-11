# Reverse Engineering Status

> **FM-X completion checkpoint — 2026-08-11 / parser v1.0.77**  
> The Soundmondo→Y2L FM-X mapping represented by `FMX_COVERAGE_MATRIX_v177.csv` is now complete for 153 tracked Yamaha-documented parameter points and has an ESP-verified lineage. Important correction: OP-relative `+62/+64` are Pitch/Level Controller Sensitivity and `+66/+68/+70` are 1st-LFO destination depth ratios. Older text that labels `+66/+68/+70` as internal trailer bytes is superseded. The FM-X 2nd-LFO depth matrix is no longer partial. Smart Morph **transport/preservation** is verified, while generic reconstruction/interpolation-table editing remains a separate open problem.


This document contains the detailed reverse engineering status and methodology for YSFC Forge. For an overview, see the main [README](../README.md).

## Table of Contents

- [Methodology](#methodology)
- [Test Corpus](#test-corpus)
- [Engine Coverage](#engine-coverage)
- [Coverage by Section](#coverage-by-section)
- [Key Findings](#key-findings)
- [File Structure](#file-structure)
- [Encoding Reference](#encoding-reference)
- [What is Classified as Firmware Constants](#what-is-classified-as-firmware-constants)
- [What is Not Yet Mapped](#what-is-not-yet-mapped)
- [Save Counter / Noise Bytes](#save-counter--noise-bytes)

---

## Methodology

The YSFC binary format (`.Y2L`, `.Y2U`) is not officially documented by Yamaha. Every parameter offset in this project was discovered through binary differential analysis:

1. Export a baseline performance from MODX M hardware or ESP plugin (typically a stripped-down "Init Voice" with one part)
2. Change exactly one parameter via the UI
3. Export the modified file
4. Compare the two files byte-by-byte (after filtering save-counter noise)
5. Record the offset, encoding type, and value range
6. Cross-verify across all engine types to distinguish user fields from firmware constants

This approach has been applied iteratively over **2010+ verified test files** to reach the current engine coverage.

### Corpus analysis (advanced method)

For engines with large test corpora, a more powerful method is applied:

1. **Scan all test files for byte-position constancy** — bytes that are 100% constant across all test files are firmware constants ([INTERN])
2. **Identify varying bytes** — these are UI fields; match each one to the specific test file that changed it
3. **Stride pattern recognition** — when multiple varying bytes share a stride (e.g., 123 bytes for FM-X operators), they are part of a repeating structure

This corpus method enabled the final mapping of AN-X (50 fields identified in two sessions) and FM-X (44 fields + 5-byte per-OP gap).

### Verification levels

Every documented field has a star rating:

- **★★★★★** — Binary-verified with one or more test files (direct A/B diff evidence)
- **★★★★☆** — Derived from official source data, highly confident
- **★★★☆☆** — Likely correct, not binary-verified
- **★★☆☆☆** — Uncertain
- **[INTERN]** — MODX-internal firmware constant, not user-editable
- **[STRUKT]** — Structurally identified, no UI mapping yet

---

## Test Corpus

The reverse engineering effort is grounded in **2010+ binary-verified test files** generated through systematic parameter changes on real MODX M hardware. Every documented offset is backed by at least one A/B binary diff.

| Engine | Files | Share |
|---|---:|---:|
| AN-X | 799 | 40% |
| FM-X | 425 | 21% |
| AWM2 | 408 | 20% |
| Drum | 84 | 4% |
| Other / multi-part | 294 | 15% |

---

## Engine Coverage

All four engines have **every known user-editable parameter binary-verified** through A/B diff analysis across the 2010+ test exports.

| Engine | UI fields | [INTERN] bytes | Status |
|---|---:|---:|---|
| AWM2 | 128 | 8 | ✅ Verified |
| AN-X | 171 | 458 | ✅ Verified |
| FM-X | 141 | 863 | ✅ Verified |
| Drum | 54 | 4934 | ✅ Verified |

### Per-engine notes

**AWM2** — Sample-based engine with 8 elements per part. Stride 313 bytes per element. Element 1 base = audit 12469. Per-element fields include Waveform Number, AEG, PEG, EQ, Pan, Velocity Limits, and Level Scaling.

**AN-X** — Analog modeling engine with 3 OSCs, 2 Filters, WaveFolder, Mod EG/LFO. 684 engine pool bytes, of which 458 are firmware constants ([INTERN]) and 171 are direct UI fields (rest are routing matrices).

**FM-X** — FM synthesis engine with 8 operators, stride 123 bytes per OP. OP1 base = audit 12676. Includes PEG, FEG, Filter, Algorithm, Feedback, and 2nd LFO modulation matrices.

**Drum** — Drum kit engine with 73 drum keys (stride 68 bytes per key). Drum uses a different filoffset convention: `filoffset = audit + 669` (vs +687 for AWM2/AN-X/FM-X). All 27 DRUM_KEY fields binary-verified.

### Beyond the engines

The verification above applies to the four synthesis engines' user-editable parameter fields. File-level structures outside the engines are tracked separately:

| Structure | Status |
|---|---|
| Multi/GM 16-part container | ✅ Mapped |
| Insertion FX / Motion Sequencer / Arp / Control Assign | ✅ Mapped (see [Coverage by Section](#coverage-by-section)) |
| Scene snapshots | ⚠️ Structure verified, ~10 fields/scene UI-confirmed — see [What is Not Yet Mapped](#what-is-not-yet-mapped) |
| Smart Morph interpolation tables | ⚠️ Not yet mapped — see [What is Not Yet Mapped](#what-is-not-yet-mapped) |
| FM-X 2nd LFO depth matrix | ✅ Fully mapped / ESP-verified lineage |

---

## Coverage by Section

### FM-X

| Section | Fields | Coverage | Notes |
|---|---:|---|---|
| Operators (8 × complete tracked field set) | 8 operators | ✅ Verified | OP1@12676, stride 123 bytes |
| Pre-OP (PEG, LFO, Algo, Filter) | 23 | ✅ Verified | |
| Part Common | 15 | ✅ Verified | Algorithm, Feedback, Filter, FM Color, Volume |
| Per-OP 2nd LFO modulation | 16 | ✅ Verified | rel +58 (PitchMod), rel +60 (AmpMod) per OP |

### AWM2

| Section | Coverage | Notes |
|---|---|---|
| Elements (8 × 124 fields = 992 positions) | Verified (UI) | E1@12469, stride 313 bytes |
| PEG block (rel +163..+195) | ✅ Verified | |
| FEG block (rel +219..+241) | ✅ Verified | |
| EQ block (rel +271..+281) | ✅ Verified | 2-band + P.EQ + Boost modes |
| LFO + LFO Element Matrix | ✅ Verified | Phase Offset + 3 Depth Ratios per element |
| Level Scaling (AMP + Filter) | ✅ Verified | 5 BreakPoints + 4 Offsets each |

### AN-X

| Section | Coverage | Notes |
|---|---|---|
| Oscillators (3 × 26 fields) | ✅ Verified | OSC1@12631, OSC2@12756, OSC3@12881 (stride 125) |
| Part Settings | ✅ Verified | Unison, OSC Reset, Voltage Drift, Ageing |
| Pitch LFO | ✅ Verified | Wave, Speed, Phase (16-step enum), Delay, FadeIn |
| Filter LFO | ✅ Verified | Wave, Speed, Phase, Delay, FadeIn, Depth F1/F2 |
| Amp + Amp LFO | ✅ Verified | Level, Vel, Key, Drive + full LFO |
| Filter 1 + Filter 2 | ✅ Verified | 12+13 fields each |
| WaveFolder + Mod EG + Mod LFO | ✅ Verified | Mod LFO has 5 fields |
| Mod LFO extras | ✅ Verified | Tempo Sync, Hold, Fade Out, Random Speed, Loop |
| AEG Offset block | ✅ Verified | Part Common rel +148/150/152/154 |
| Filter Offset | ✅ Verified | Part Common rel +164/166/168 |
| Mod LFO Destination Matrix | ✅ Verified | Shared with AWM2 |
| Routing matrices (5 × 40 bytes) | [INTERN][STRUKT] | Not UI-editable, preserved as-is |

### Drum

| Section | Coverage | Notes |
|---|---|---|
| Drum Key (per key × 73 keys) | ✅ Verified | 27 fields per key, stride 68 |
| Drum Part Common | ✅ Verified | 27 fields including Filter AEG (audit 6849-6855) |
| Filter AEG (Part-level) | ✅ Verified | drumPartFilterAegAttack/Decay/Sustain/Release |

### Cross-engine sections

| Section | Coverage | Notes |
|---|---|---|
| Insertion FX | ✅ Verified | 57 verified FX types |
| Motion Sequencer (4 lanes × 884 bytes) | ✅ Verified | 116 fields |
| Arp Common | ✅ Verified | 34 fields |
| Common Control Assign (32 slots × 22 bytes) | ✅ Verified | abs 2452..3155 |
| Part Control Assign (8 slots × 22 bytes) | ✅ Verified | Part rel +1520..+1695 |
| Part After Touch (4 slots × 16 bytes) | ✅ Verified | Part rel +600..+663 |
| SuperKnob Assign Positions | ✅ Verified | 8 knobs × 6 bytes u16le at abs 674 |
| Assign Knob Names | ✅ Verified | 8 × 21 bytes ASCII at abs 8049 |
| Receive Switch per Part | ✅ Verified | Identical across all 4 engines |
| Master EQ 5-band | ✅ Verified | abs 560-592 |
| Audio In Routing | ✅ Verified | incl. Envelope Follower |
| Performance Common | ✅ Verified | Volume, Pan, Tempo, etc. |
| Part Common (Pitch Bend, Portamento, EQ, FX) | ✅ Core verified | Most fields binary-verified; a few low-traffic fields structurally mapped, not yet A/B-confirmed |

---

## Key Findings

### File format

- `Y2L` and `Y2U` are byte-for-byte identical — only the file extension changes how ESP presents the import dialog
- Performance name: starts at byte `perf[4]`, null-terminated, max ~16 characters of printable ASCII
- Scene count: `perf[6695]`, range 1–8
- Engine type byte: `perf[6700]`, values 0=AWM2, 1=Drum, 2=FMX, 3=ANX
- Common-blob size is 6701 bytes
- Part Common stride is 5765 bytes

### Engine pool layout

- AWM2 engine pool: 3 header bytes + 8 elements × 313 byte stride (E1@12469)
- AN-X engine pool: 3 OSC × 124 byte stride (OSC1@12631, OSC2@12755, OSC3@12880)
- FM-X engine pool: 8 OP × 123 byte stride (OP1@12676 ... OP8@13537)
- Drum engine pool: 73 keys × 68 byte stride (Key 1 audit @ 12469)

### Address conventions

- AWM2/AN-X/FM-X: `filoffset = audit + 687`
- Drum: `filoffset = audit + 669` (different convention)

### Multi-part / Multi/GM

- Pointer-based sub-blob detection: `SUBBLOB_POINTER_REL = (5763, 5764)`
- Engine magic bytes: AWM2=8, ANX=110, FMX=82, Drum=73
- Multi/GM files (16 parts: 15 AWM2 + 1 Drum on Part 10) use the same multi-part architecture

### Notable encoding details

- AN-X PitchEGDepth encoding: `raw = round(UI_cent × 247/4800) + 247`, range ±4800 cents
- AN-X Filter FEGDepth: `raw = round(UI/50) + 256`, range ±12700 cents
- FM-X Algorithm: `raw = algo − 1`
- PEG Center Key for AWM2 elements is at rel +159
- Common Scene block: 8 scenes × 71 bytes at abs **1710**
- Per-Part Scene block: 8 scenes × 84 bytes at Part rel +682

---

## File Structure

### Chunk layout

All YSFC files contain 6 chunks in this order:

```
EPFM @ offset 64   — Performance metadata
ESYS @ offset N    — System data
EFVT @ offset N    — Favorite data
DPFM @ offset N    — Performance data (the main payload)
DSYS @ offset N    — System tables
DFVT @ offset N    — Favorite tables
```

### DPFM internal structure

The DPFM chunk contains a single `Data` block with the performance payload:

```
Sub-blob 1: Performance Common         (6701 bytes)
Sub-blob 2: Part 1 Common              (5765 bytes)
Sub-blob 3: Part 2 Common              (5765 bytes)
...
Sub-blob N+1: Part N Common            (5765 bytes)
Engine pool                            (variable size, depends on engine mix)
```

### Multi/GM 16-part architecture

```
Performance Common              6701 bytes
16 × Part Common               92240 bytes (5765 × 16)
Engine pool                    42583 bytes (15 × AWM2_stride + 1 × Drum_stride)
DPFM total                    141536 bytes
```

---

## Encoding Reference

| Type | Formula |
|---|---|
| direct u8 | `raw = value` |
| center=64 | `raw = value + 64` |
| center=128 | `raw = value + 128` |
| AN-X PulseWidth | `raw = round(pct × 256/100)` |
| AN-X SelfSyncPitch | `raw = round(UI/25) + 256` |
| AN-X Filter FEGDepth | `raw = round(UI/50) + 256`, range ±12700 cents |
| AN-X PitchEGDepth | `raw = round(UI_cent × 247/4800) + 247`, range ±4800 cents |
| AN-X Assign / SuperKnob value | u16 little-endian, default=512 |
| SuperKnob Assign positions | u16 little-endian, Left=0/Mid=512/Right=1023 |
| FM-X algorithm | `raw = algo − 1` |
| FM-X OP detune | `raw = value + 15` |
| InsA/B TypeIndex | `lo = idx & 0x7F`, `hi = (idx >> 7) & 0x7F` |
| Waveform number | u16 little-endian, 1-based |
| Note MIDI value | u8, 0=C-2, 60=C3, 127=G8 |

---

## What is Classified as Firmware Constants

The following regions are structurally mapped but verified to be **identical across all engine types** (AWM2 / AN-X / FM-X), meaning they are firmware lookup tables rather than user parameters:

| Region | Size | Likely purpose |
|---|---:|---|
| Common abs 357-394 | 38 bytes | Arp Common firmware constants (includes Sync Quantize @ 360) |
| Common abs 487-524 | 38 bytes | AN-X Pitch checksum (abs 488 changes on any AN-X Pitch edit) |
| Common abs 732-764 | 33 bytes | SmartMorph FM-X data |
| Common abs 851-1680 | 830 bytes | 8 × 106-byte firmware lookup tables (16 c64-nodes per block) — likely velocity/aftertouch curves |

These were confirmed as firmware constants by byte-diffing the Init Voice baseline of all three engine types — the bytes are identical, so they cannot be user parameters tied to a specific engine.

### Drum [INTERN] bytes

Within drum keys (68 bytes × 73 keys = 4964 bytes), 4934 bytes (99.4%) are firmware constants. Specifically:

- Per drum key: 33 zero-padded byte positions (rel +1, +2, +3, +5, +7, +9, +13, +15, +17, +19, +20, +21, +23, +24, +25, +27, +29, +31, +33, +35, +37, +39, +41, +43, +47, +49, +53, +54, +55, +57, +59, +61, +63)
- Per drum key: rel +18 (value 90), rel +67 (value 64) — constant non-zero firmware values

---

## What is Not Yet Mapped

### Scene parameter snapshots

Scene structure is verified (8 × 71 bytes Common at abs 1710, 8 × 84 bytes per Part at rel +682) but only ~10 fields per scene have UI-confirmed mappings. The remaining bytes per scene are part of the snapshot mechanism but specific field-level mapping is incomplete.

### Smart Morph

The interpolation tables and FM-X morphing state are not mapped.

### FM-X 2nd LFO depth matrix

Completed in the v1.0.64 lineage: global Pitch/Amp/Filter modulation depths and per-operator Pitch/Amp depths are mapped and ESP-verified.

### Performance Editor tool (UI gap)

While the binary format is mapped (all known parameters verified), the Performance Editor UI does not yet expose all parameters:

- Multi-part performances — only Part 1's engine is currently shown
- Drum parameter editor — structure mapped, UI not yet built
- Undo/redo functionality not yet implemented

---

## Save Counter / Noise Bytes

The following bytes change on every save regardless of parameter edits (timestamps, internal counters):

```
abs 22-24, 60-63, 66, 232, 234, 358, 376, 396-399, 488, 654,
abs 6715-6716, 6721, 6724-6725, 7167-7168, 7419
```

For Drum-specific testing, also add:

```
filoffset 680-720, 7380-7400
```

These bytes are filtered out of diff analysis to avoid false positives.

---

## Further Reading

- [`YSFC_FORGE_REFERENCE.md`](YSFC_FORGE_REFERENCE.md) — Compact reference manual with all field positions
- [`YSFC_FORGE_FULL_CONTEXT.md`](YSFC_FORGE_FULL_CONTEXT.md) — Full technical documentation with test evidence
- [`../serializer/ysfc_serializer.py`](../serializer/ysfc_serializer.py) — Python parameter constants
