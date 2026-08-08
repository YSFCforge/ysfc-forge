# YSFC Forge — Compact Reference

Patch editor and reverse engineering project for the Yamaha MODX M / Montage M binary format (Y2L/Y2U).

**Hardware:** MODX M8 firmware 3.0, ESP Plugin v3.0<br>
**Source:** Binary-verified single-edit test files compared against Init Voice baselines (AWM2, AN-X, FM-X, Drum)<br>
**Data attribution:** Reference tables are derived from Yamaha's publicly published MODX M Data List (© Yamaha Corporation) for interoperability; the document itself is not redistributed. See the main [README](../README.md#data-attribution).

---

## Status

| Engine | Mapped fields | UI coverage |
|---|---:|---:|
| AWM2 (per element × 8..128) | 128 fields + 8 [INTERN] | ✅ **Verified** |
| AN-X (engine total) | 171 fields + 458 [INTERN] | ✅ **Verified** |
| FM-X (Pre-OP + 8 × OP) | 141 fields + 863 [INTERN] | ✅ **Verified** |
| Drum (per key × 73) | 27 key fields + 27 Part Common | ✅ **Verified** |
| Part Common | 88 fields (AWM2/FM-X/AN-X) + 6 (Drum) | ✅ Core verified |

**Total field positions in serializer:** ~2057
**Test corpus:** 2010+ binary-verified files

All four engines are binary-verified across all known user-editable parameters. Multi/GM 16-part files are supported via the multi-part architecture (Performance Common + 16 × Part Common stride 5765 + Engine Pool with 15 AWM2 + 1 Drum on Part 10).

---

## Current format support model

YSFC Forge currently treats the supported Yamaha file families as separate but related layouts:

| Family | Typical versions | File extensions | Current role in YSFC Forge |
|---|---|---|---|
| MODX M / MONTAGE M long layout | `5.1.x` / modern `.Y2L`/`.Y2U` exports | `.Y2L`, `.Y2U` | Primary native export target |
| MONTAGE M short layout | `4.1.x` / `.X2L`-style library layout | often seen as `.Y2L` or `.X2L` depending on source | Experimental Performance import; converted to the long Y2L layout for export |
| Legacy MONTAGE | `4.0.x` | `.X7L`, `.X7U` | Experimental Performance import/conversion |
| Legacy MODX / MODX+ | `5.0.x` | `.X8L`, `.X8U` | Experimental Performance import/conversion |

The Library Builder's current goal is to export selected Performances and required dependencies. It does not attempt to clone full library state. Live Sets, Patterns, Favorites and some device-side library metadata are intentionally outside the current export scope.

### Current Library Builder conversion scope

| Source type | Engines | Dependencies | Notes |
|---|---|---|---|
| Native long `.Y2L`/`.Y2U` | AWM2, FM-X, AN-X, Drum | Selective waveforms, samples, arpeggios | Primary supported path |
| Legacy `.X7L`/`.X8L` | AWM2, FM-X, Drum | Selective waveforms, samples, arpeggios | Converted to modern Y2L DPFM layout; classic AN-X is not expected in normal X7L/X8L sources |
| MONTAGE M short-layout `.X2L`-style files | AWM2, FM-X, AN-X, Drum | Performance export; dependencies are handled when referenced through supported sections | Short common/part/engine regions are expanded to the long Y2L layout |

AN-X is fully supported in the Y2L/Y2U target format. AN-X is not expected to occur in original legacy MONTAGE/MODX `.X7L`/`.X8L` libraries; if a classic source exposes an unknown part type, it should be treated as an unknown classic engine rather than assumed to be a valid classic AN-X source.


## Performance ↔ Waveform linkage & selective export

A performance references a USER waveform via fixed DPFM-blob byte structures:
`SIG_A` = `00 00 00 28 01 XX YY 00 [ID] 00 01 00 01`, `SIG_B` =
`01 00 00 00 01 00 0C 00 [ID] 00 40`. The byte after `0x28` is the bank
(`01`=user → `[ID]` indexes the EWFM/EWIM catalog; `00`=preset, ignored).
Catalog ID = `recPayload[10:12]` (BE u16).

**Renumber rule:** sort distinct referenced old IDs → assign `1..N` (1-based).
Patch every `[ID]` byte old→new in kept blobs; write new IDs into rebuilt
EWFM/EWIM. Pure renumber touches only the `[ID]` byte. Arpeggio refs sit
after a `80 00` pitch run + optional `00` pad as `([ARP_ID] 2f)` pairs
(id<21, may repeat ≤4×); renumber is identical but **0-based**
(sort distinct referenced arp ids → `0..N-1`). EARP/DARP are rebuilt
selectively; blob arp `[ID]` bytes repointed old→new.

**Sizing.** Y2L dependency sections, the DPFM performance pool and the EPFM
performance index are all sized exactly to payload (MODX rejects any
size-field/data slack): uniform 8-byte-per-blob framing,
`exactSize = Σ(8 + payload) − 4 + 8`. Container uses ESP's exact 12-chunk
layout (`EPFM EWFM EARP ESYS EFVT EWIM DPFM DWFM DARP DSYS DFVT DWIM`);
`u32@0x20` = chunk-count·8. `u32@0x3c` is a per-file build stamp, also
embedded as u16 before every EPFM/EWFM/EARP name (synthetic header `0x3c`
= source `0x3c`); EPFM rec byte[11] = compact dest slot index. DWFM blob
offset `60 + 64·k` is a 4-byte LE sample index = `base + i` (base = first
blob sub-entry's orig 4B LE value, i per sub-entry over all blobs).
A valid library file has a fixed directory region: entries from `0x40`,
FF-pad, `0x00` separator @`0x190`, first chunk @`0x191`.

Helpers: `scanWaveformRefPositions`, `scanArpRefPositions`,
`renumberPerfBlob`, `setRecPayloadId`. The export path renumbers blobs +
catalogs; a conservative copy-all fallback is preserved for untrusted
resolution. Per-performance W/S/Arp UI chips are gated by the same scanners.


## File structure (Y2L container)

### File header (64 bytes, binary-verified — see Appendix A.3 in YSFC_FORGE_FULL_CONTEXT.md)

| Offset | Hex | Size | Field | Notes |
|---:|---:|---:|---|---|
| 0 | 0x00 | 16 | Magic + null-pad | `YAMAHA-YSFC\x00\x00\x00\x00\x00` |
| 16 | 0x10 | 16 | Version + null-pad | `5.1.2` (Montage M / MODX M); `5.0.1` (MODX); `4.0.5` (Montage) |
| 32 | 0x20 | 4 | Catalogue size | `u32 BE` = block_count × 8; catalogue starts at 0x40 |
| 36 | 0x24 | 12 | Reserved | all `0xFF` |
| 48 | 0x30 | 4 | Library-info length | `u32 BE`; 241 b (Montage M / MODX M), 81 b (classic) |
| 52 | 0x34 | 8 | Reserved | all `0xFF` |
| 60 | 0x3C | 4 | Save counter | `u32 BE`; monotonically increasing — **not** Unix timestamp |

### EPFM Entry record payload (binary-verified)

| Rel | Size | Field | Notes |
|---:|---:|---|---|
| 0 | 4 | Blob size | `u32 BE` — DPFM blob size |
| 4 | 4 | DPFM offset | `u32 BE` — offset within DPFM payload |
| 9 | 1 | Constant | `0x40` (MODX validates) |
| 11 | 1 | Dest slot | compact sequential index (0, 1, 2, …) |
| 15 | 1 | Engine bits | `0x01`=AWM2/Drum, `0x02`=FM-X, `0x04`=AN-X; OR-combined |
| 16 | 1 | Source flag | `0x00`=ESP Plugin, `0x02`=MODX hardware |
| 27 | var | Name string | `"{idx}:{short_name}:{display_name}\0"` NUL-terminated ASCII |

Name string format: `"{slot_index}:{short_name}:{display_name}\0"`. The **third field** is the actual display name shown in MODX/ESP Plugin (matches `blob[4:]`). The second field is a short/category label. Example: `"0:Italian XL:Italian Grand XL\0"`.

Note: earlier documentation described this as `"IDX:LongName_padded:ShortName\0"` — that had the field order reversed and was incorrect.

**Format note:** Native long-layout DPFM uses `blob[6700]` as the common engine byte. MONTAGE M short-layout DPFM uses the corresponding common engine byte at `blob[6688]` before conversion. Legacy X7L/X8L DPFM is parsed as classic DataBlock-framed performance data and then rebuilt as modern Y2L. When reading unknown files, prefer EPFM engine-bit metadata when available and validate it against the detected DPFM layout.

```
YAMAHA-YSFC header
├── EPFM  Performance index
├── DPFM  Performance data
├── ELST  Live Set index
├── DLST  Live Set data
├── ESYS  System index
├── DSYS  System data
├── EFVT  Favorite index
└── DFVT  Favorite data
```

**Container abs → payload-rel conversion:** `payload = file_abs − 691` (for Part Common region; some baselines deviate depending on chunk layout).

---

## Part Common (payload rel +0..+469, abs 6701..7170)

### Identifiers & metadata
- `+0..+21` partName (ASCII × 22)
- `+31` monoPoly (u8 bool, default 1=Poly)
- `+32` portamento_sw

### Volume/Pan/Routing
- `+142` volume (u8 direct, default 100)
- `+105` ex_elem_sw / arpRandomSfx (shared byte; UI exposes these as separate controls)

### Shared Part-level AEG Offset (rel +144..+150)
Shared block — AWM2, FM-X and AN-X write here via the UI's "Part Settings > AEG Offset". **The Drum engine does NOT use this block** — for Drum, rel +144/+146 are filter fields (see Drum section).

| Rel | Field | Encoding | Default |
|---:|---|---|---:|
| +144 | aeg_offset_attack | c64 | 64 |
| +146 | aeg_offset_decay | c64 | 64 |
| +148 | aeg_offset_sustain | c64 | 64 |
| +150 | aeg_offset_release | c64 | 64 |

### AWM2-specific FEG Offset (rel +152..+158)
AWM2 only — FM-X and AN-X have FEG structures in the engine pool instead.

| Rel | Field | Encoding | Default |
|---:|---|---|---:|
| +152 | feg_offset_attack | c64 | 64 |
| +154 | feg_offset_decay | c64 | 64 |
| +156 | feg_offset_sustain | c64 | 64 |
| +158 | feg_offset_release | c64 | 64 |

### Element Count (rel +196)
u8 enum: 8, 16, 32, 64, 128. Default 8. Mirrored in Engine header byte 0 — the same value is stored in two places. File size grows linearly: extra bytes = (EC − 8) × 313.

### Other Part Common fields
- `+126` velocity_depth (AN-X), shared with Drum velDepth
- `+128` velocity_offset
- `+202` pitch_control_group
- `+212` pb_range_upper, `+214` pb_range_lower
- `+216` detune (u16le center)
- `+218` note_shift (c64)
- `+220` portamento_time
- `+222` portamento_mode (bool)
- `+224` portamento_time_mode (enum Rate1/Time1/Rate2/Time2)
- `+226` legato_slope (u8 0..7)

### Filter offsets (rel +164..+168, AN-X UI naming)
- `+164` filter_offset_fegdepth
- `+166` filter_offset_cutoff
- `+168` filter_offset_resonance

---

## Engine Header (5 bytes, abs 12464..12468)

| Abs | Field | Default |
|---:|---|---:|
| 12464 | element_count | 8 (AWM2) |
| 12465 | unknown_b1 | 0 |
| 12466 | engine_type | 0=AWM2, 1=Drum, 2=FM-X, 3=AN-X |
| 12467 | unknown_b3 | 0 |
| 12468 | unknown_marker | 43 (AWM2) |

---

## AWM2 Engine (per-element, stride 313 bytes)

**Engine pool start:** payload 12469
**Element N base:** 12469 + (N−1) × 313
**Support:** 8..128 elements per Part

### Addressing conventions (CRITICAL for byte analysis)

This reference uses an **"audit abs" convention** where Element 1 base = abs 12469. For binary diff analysis of Y2L files, the conversion is:

```
filoffset = audit_abs + 687
audit_abs = filoffset − 687
```

The constant 687 consists of: 64 (file header) + 8 (EPFM header) + 353 (EPFM data) + 8 (ESYS header) + 46 (ESYS data) + 8 (EFVT header) + 163 (EFVT data) + 8 (DPFM header) + 16 (DPFM sub-blob header including "Data..." and Performance Name prefix) + 13 (pre-Part area). Exact summation may vary per file type.

**Verification:** The file offset where `waveform_lo = 6` (Init Normal AWM2 Element 1 = CFX v06 St) should be `687 + 12469 + 51 = 13207`. This is a reliable reference point for any binary analysis.

**Note:** The serializer's `AWM2_ELEM_LAYOUT` uses a *different* convention where `ELEM_BASE = abs 12520`. Conversion to audit-abs:

```
audit_abs = AWM2_ELEM_LAYOUT_offset + 12520
audit_rel_within_element = AWM2_ELEM_LAYOUT_offset + 51
```

Summary of three different "abs" conventions in the project:
- **audit abs** (this reference): Element 1 base = 12469
- **AWM2_ELEM_LAYOUT** (serializer): Element 1 base = 12520 (ELEM_BASE = audit_abs − 51)
- **AWM2_ELEM1_BASE** (serializer): 12532 (audit_abs + 63)

### Per-element fields — COMPLETE

All rel values are within the 313-byte element. Element 1 base = audit abs 12469.

#### Header & metadata

| Rel | Field | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +0 | `element_header` | bool | E1=1, E2-8=0 | ★★★★★ |
| +1 | `keyondly_sync` | bool | 0 | ★★★★★ |
| +2 | `aeg_half_damper` | bool | 0 | ★★★★★ |
| +6 | `extended_lfo` | bool | 1 | ★★★★★ |
| +49 | `elem_group` | direct | 0 | ★★★★★ |
| +51 | `waveform_lo` | u8 | varies | ★★★★★ |
| +59 | `pan` | c64 | 64 | ★★★★★ |
| +61 | `aeg_random_pan` | u8 | 0 | ★★★★★ |
| +63 | `aeg_alternate_pan` | c64 | 64 | ★★★★★ |
| +65 | `aeg_scaling_pan` | c64 | 64 | ★★★★★ |
| +67 | `xa_control` | enum | 0 | ★★★★★ |
| +69 | `note_limit_low` | MIDI | 0 | ★★★★★ |
| +71 | `note_limit_high` | MIDI | 127 | ★★★★★ |
| +73 | `vel_limit_low` | u8 | 1 | ★★★★★ |
| +75 | `vel_limit_high` | u8 | 127 | ★★★★★ |
| +77 | `vel_xfade` | u8 | 0 | ★★★★★ |
| +79 | `delay_length` | u8 | 0 | ★★★★★ |
| +81 | `elem_connect` | enum | 1 | ★★★★★ |
| +85 | `keyondly_sync_delay` | u8 | 11 | ★★★★★ |

`extended_lfo` at rel +6 determines which Speed byte the UI shows — rel +289 when OFF, rel +307 when ON. Default is ON for Init Normal AWM2.

#### AMP block

| Rel | Field | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +91 | `level` | direct | 127 | ★★★★★ |
| +93 | `amp_level_vel` | c64 | 64 | ★★★★★ |
| +95 | `aeg_offset` | c64 | 0 | ★★★★★ |
| +97 | `amp_level_curve` | enum | 3 | ★★★★★ |
| +99 | `aeg_attack` | u8 | 0 | ★★★★★ |
| +101 | `aeg_decay1` | c64 | 64 | ★★★★★ |
| +103 | `aeg_decay2` | c64 | 64 | ★★★★★ |
| +105 | `aeg_half_damper_time` | u8 | 127 | ★★★★★ |
| +107 | `aeg_release` | u8 | 50 | ★★★★★ |
| +109 | `aeg_initial_level` | u8 | 0 | ★★★★★ |
| +111 | `aeg_attack_level` | u8 | 127 | ★★★★★ |
| +113 | `aeg_decay1_level` | u8 | 127 | ★★★★★ |
| +115 | `aeg_decay2_level` | u8 | 127 | ★★★★★ |
| +117 | `amp_segment_decay` | u8 | 4 | ★★★★★ |
| +119 | `amp_time_vel` | c64 | 64 | ★★★★★ |

#### Pitch block

| Rel | Field | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +149 | `coarse_tune` | c64 | 64 | ★★★★★ |
| +151 | `fine_tune` | c64 | 64 | ★★★★★ |
| +153 | `pitch_vel` | c64 | 64 | ★★★★★ |
| +155 | `pitch_random` | u8 | 0 | ★★★★★ |
| +157 | `pitch_key` | u8 | 96 | ★★★★★ |
| +159 | `pegKFCenterNote` | MIDI | 60 | ★★★★★ |
| +161 | `fine_key` | c64 | 64 | ★★★★★ |
| +163 | `peg_hold_time` | u8 | 0 | ★★★★★ |

#### PEG block

| Rel | Field | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +169 | `peg_signature` | u8 | 64 | ★★★★★ |
| +173 | `peg_level_hold` | c128 | 128 | ★★★★★ |
| +175 | `peg_level_attack` | c128 | 128 | ★★★★★ |
| +177 | `peg_level_decay1` | c128 | 128 | ★★★★★ |
| +179 | `peg_level_decay2` | c128 | 128 | ★★★★★ |
| +181 | `peg_level_release` | c128 | 128 | ★★★★★ |
| +185 | `peg_segment` | enum | 4 | ★★★★★ |
| +187 | `peg_time_vel` | c64 | 64 | ★★★★★ |
| +189 | `peg_depth_vel` | c64 | 64 | ★★★★★ |
| +191 | `peg_curve` | enum | 2 | ★★★★★ |
| +193 | `peg_time_key` | c64 | 64 | ★★★★★ |
| +195 | `peg_center_key` | MIDI | 60 | ★★★★★ |

#### Filter block

| Rel | Field | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +201 | `filter_type` | enum | 4 | ★★★★★ |
| +203 | `filter_cutoff_lo` | u16le | 128 | ★★★★★ |
| +205 | `filter_cutoff_vel` | c64 | 64 | ★★★★★ |
| +207 | `filter_resonance` | u8 | 0 | ★★★★★ |
| +209 | `filter_resonance_vel` | c64 | 64 | ★★★★★ |
| +211 | `hpf_cutoff_lo` | u16le | 0 | ★★★★★ |
| +213 | `filter_distance` | c128 | 128 | ★★★★★ |
| +215 | `filter_gain` | u8 | 230 | ★★★★★ |

Filter type values: LPF24A=1, LPF18=2, default=4, DualBEF=17.

#### FEG block (Filter Envelope)

| Rel | Field | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +219 | `filter_time_attack` | u8 | 0 | ★★★★★ |
| +221 | `filter_time_decay1` | c64 | 64 | ★★★★★ |
| +223 | `filter_time_decay2` | c64 | 64 | ★★★★★ |
| +225 | `filter_time_release` | u8 | 80 | ★★★★★ |
| +227 | `filter_level_hold` | c128 | 128 | ★★★★★ |
| +229 | `filter_level_attack` | u8 | 255 | ★★★★★ |
| +231 | `filter_level_decay1` | u8 | 255 | ★★★★★ |
| +233 | `filter_level_decay2` | u8 | 255 | ★★★★★ |
| +235 | `filter_level_release` | c128 | 128 | ★★★★★ |
| +237 | `filter_feg_depth` | c104 | 104 | ★★★★★ |
| +239 | `filter_segment` | enum | 4 | ★★★★★ |
| +241 | `filter_time_vel` | c64 | 64 | ★★★★★ |
| +243 | `feg_depth_vel` | c64 | 64 | ★★★★★ |
| +245 | `filter_curve` | enum | 2 | ★★★★★ |

#### EQ block

| Rel | Field | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +271 | `eq_type` | enum | 0 | ★★★★★ |
| +273 | `eq_q_or_resonance` | u8 | 0 | ★★★★★ |
| +275 | `eq_low_freq` | u8 | 54 | ★★★★★ |
| +277 | `eq_low_gain` | c64 | 64 | ★★★★★ |
| +279 | `eq_high_freq` | u8 | 231 | ★★★★★ |
| +281 | `eq_high_gain` | c64 | 64 | ★★★★★ |

EQ type values: 0=2-band, 1=P.EQ, 2=Boost6.

#### LFO block

| Rel | Field | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +283 | `lfo_wave` | enum | 1 | ★★★★★ |
| +285 | `lfo_keyonreset` | bool | 1 | ★★★★★ |
| +287 | `lfo_delay` | u8 | 0 | ★★★★★ |
| +289 | `lfoSpeed` | u8 0..63 | 38 | ★★★★★ |
| +291 | `lfo_amp_mod_depth` | u8 | 0 | ★★★★★ |
| +293 | `lfo_pitch_mod_depth` | u8 | 0 | ★★★★★ |
| +295 | `lfo_filter_mod_depth` | u8 | 0 | ★★★★★ |
| +297 | `lfo_fade_in` | u8 | 0 | ★★★★★ |
| +307 | `lfo_extended_speed` | u16le 0..415 | 60 | ★★★★★ |

LFO wave: Saw=0, Tri=1, Square=2. `lfoSpeed` (+289) is active when `extended_lfo`=0; `lfo_extended_speed` (+307) is active when `extended_lfo`=1.

#### AMP Level Scaling (5 BP + 4 offsets)

| Rel | Field | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +121 | `amp_time_key` | c64 | 64 | ★★★★★ |
| +123 | `amp_scaling_center_key` | MIDI | 24 | ★★★★★ |
| +125 | `amp_scaling_bp1` | MIDI | 36 | ★★★★★ |
| +127 | `amp_scaling_bp2` | MIDI | 48 | ★★★★★ |
| +129 | `amp_scaling_bp3` | MIDI | 60 | ★★★★★ |
| +131 | `amp_scaling_bp4` | MIDI | 72 | ★★★★★ |
| +133 | `amp_scaling_offset1` | c128 | 128 | ★★★★★ |
| +135 | `amp_scaling_offset2` | c128 | 128 | ★★★★★ |
| +137 | `amp_scaling_offset3` | c128 | 128 | ★★★★★ |
| +139 | `amp_scaling_offset4` | c128 | 128 | ★★★★★ |
| +141 | `level_key` | c64 | 64 | ★★★★★ |
| +143 | `amp_release_adj` | c64 | 64 | ★★★★★ |

#### Filter Level Scaling (5 BP + 4 offsets)

| Rel | Field | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +247 | `filter_time_key` | c64 | 64 | ★★★★★ |
| +249 | `filter_scaling_center_key` | MIDI | 24 | ★★★★★ |
| +251 | `filter_scaling_bp1` | MIDI | 36 | ★★★★★ |
| +253 | `filter_scaling_bp2` | MIDI | 48 | ★★★★★ |
| +255 | `filter_scaling_bp3` | MIDI | 60 | ★★★★★ |
| +257 | `filter_scaling_bp4` | MIDI | 72 | ★★★★★ |
| +259 | `filter_scaling_cutoff_offset1` | c128 | 128 | ★★★★★ |
| +261 | `filter_scaling_cutoff_offset2` | c128 | 128 | ★★★★★ |
| +263 | `filter_scaling_cutoff_offset3` | c128 | 128 | ★★★★★ |
| +265 | `filter_scaling_cutoff_offset4` | c128 | 128 | ★★★★★ |
| +267 | `element_edit_counter` | u8 | 74 | ★★★★★ [INTERN] |
| +269 | `hpf_cutoff_key` | c64 | 64 | ★★★★★ |

#### LFO Element Matrix

| Rel | Field | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +299 | `element_lfo_phase_offset` | enum | 0 | ★★★★★ |
| +301 | `element_lfo_dest1_depth` | u8 | 127 | ★★★★★ |
| +303 | `element_lfo_dest2_depth` | u8 | 127 | ★★★★★ |
| +305 | `element_lfo_dest3_depth` | u8 | 127 | ★★★★★ |

### XA Control enum (rel +67)
0=Normal, 1=Legato, 2=KeyOff, 3=Cycle, 4=Random, 5=A.Sw Off, 6=A.Sw1 On, 7=A.Sw2 On

### [INTERN] bytes within AWM2 element

The following positions are firmware constants (verified 100% constant across 408 AWM2 test files):

| Rel | Default | Description |
|---:|---:|---|
| +46 | 40 | Firmware constant |
| +90 | 54 | Firmware constant |
| +148 | 48 | Firmware constant |
| +200 | 108 | Firmware constant |
| +309..+311 | 0 | Padding |
| +312 | 43 (0x2B '+') | Inter-element separator |

**Per-element summary:**
- 128 UI-mapped fields ★★★★★
- 8 [INTERN] bytes
- ~177 multi-byte split bytes (u16le hi-byte etc., already counted in UI fields)

Element 8 shows a different value at rel +312 because the DSYS chunk starts immediately after Element 8 without a padding zone.

---

## FM-X Engine

**Engine pool start:** payload 12466
**Pre-OP block:** rel +0..+147
**OP1 base:** payload 12676 (= engine rel +210)
**OP stride:** 123 bytes, 8 operators

### Pre-OP block

#### PEG (Pitch EG) — rel +11..+41

| Rel | Field | Encoding | Default |
|---:|---|---|---:|
| +11 | peg_pitch_velocity | c64 | 64 |
| +13 | peg_random_pitch | u8 | 0 |
| +15 | peg_pitch_key | c96 | 96 |
| +17 | peg_center_key | MIDI | 60 |
| +19 | peg_level_initial | c50 | 50 |
| +21 | peg_level_attack | c50 | 50 |
| +23 | peg_level_decay1 | c50 | 50 |
| +25 | peg_level_decay2 | c50 | 50 |
| +27 | peg_level_release | c50 | 50 |
| +29 | peg_time_attack | direct | 0 |
| +31 | peg_time_decay1 | direct | 0 |
| +33 | peg_time_decay2 | direct | 0 |
| +35 | peg_time_release | direct | 0 |
| +37 | peg_depth_velocity | direct | 0 |
| +39 | peg_depth | enum | 0 |
| +41 | peg_time_key | direct | 0 |

#### Common LFO + Algorithm — rel +43..+69
- `+43` lfo_wave (enum, default 5)
- `+47` second_lfo_phase (enum, default 0)
- `+49` second_lfo_delay (u8, default 0)
- `+51` key_on_reset (bool)
- `+59` algo (u8, default 69)
- `+61` feedback (u8)
- `+63` second_lfo_extended (bool, default 1)
- `+65` second_lfo_wave_speed (u8, default 50)
- `+69` op1_fm_harmonics (u8, default 128)

#### Filter — rel +81..+93

| Rel | Field | Encoding | Default |
|---:|---|---|---:|
| +81 | filter_type | enum | 21 |
| +83 | filter_cutoff | u16le | 1023 |
| +85 | filter_cutoff_vel | c64 | 64 |
| +87 | filter_resonance | direct | 10 |
| +89 | filter_resonance_vel | direct | 64 |
| +91 | filter_hpf_cutoff | direct | 0 |
| +93 | filter_resonance_vel_v | c64 | 64 |

Filter type values: Thru=21, LPF12+HPF12=4.

#### FEG (Filter EG) — rel +95..+131

| Rel | Field | Encoding | Default |
|---:|---|---|---:|
| +95 | feg_gain | u8 direct (0..255) | 255 |
| +97 | feg_hold_time | direct | 0 |
| +99 | feg_attack_time | direct | 0 |
| +101 | feg_decay_time | direct | 0 |
| +103 | feg_sustain_time | direct | 0 |
| +105 | feg_release_time | direct | 0 |
| +107 | feg_hold_level | c128 | 128 |
| +109 | feg_attack_level | c128 | 128 |
| +111 | feg_decay_level | c128 | 128 |
| +113 | feg_sustain_level | c128 | 128 |
| +115 | feg_release_level | c128 | 128 |
| +117 | feg_depth | c128 | 104 |
| +119 | feg_segment | enum 0..4 | 4=All |
| +121 | feg_time_vel | c64 | 64 |
| +123 | feg_depth_vel | c64 | 64 |
| +125 | feg_curve | enum 0..4 | 2 |
| +131 | feg_time_key_v | c64 | 64 |

#### Key Follow — rel +127..+147

| Rel | Field | Encoding | Default |
|---:|---|---|---:|
| +127 | time_key_scaling | c64 | 64 |
| +129 | center_key | MIDI | 24=C2 |
| +133 | break_point_1 | MIDI | 36 |
| +135 | break_point_2 | MIDI | 48 |
| +137 | break_point_3 | MIDI | 60 |
| +139 | break_point_4 | MIDI | 72 |
| +141 | cutoff_offset_1 | c128 | 128 |
| +143 | cutoff_offset_2 | c128 | 128 |
| +145 | cutoff_offset_3 | c128 | 128 |
| +147 | cutoff_offset_4 | c128 | 128 |

#### OP1-specific Pre-OP fields
- `+206` op1_keyonreset (bool, default 1)
- `+208` op1_freq_mode (enum 0=Ratio, 1=Fixed)

### OP block (123 bytes per operator, OP1..OP8)

Per-OP field layout (offsets relative to OP_BASE):

| Rel | Field | Encoding | Default |
|---:|---|---|---:|
| +0 | coarse | u8 | 1 |
| +2 | fine | u8 | 0 |
| +4 | detune | c16 | 15 |
| +6 | pitch_key_fixed | u8 | 0 |
| +8 | pitch_vel_fixed | u8 | 7 |
| +10 | spectral_form | enum 0..6 | 0 |
| +12 | spectral_skirt | u8 | 0 |
| +14 | spectral_resonance | u8 | 0 |
| +16 | level_initial | c50 | 50 |
| +18 | level_attack | c50 | 50 |
| +20 | time_attack | u8 | 0 |
| +22 | time_delay | u8 | 0 |
| +24 | aeg_attack_level | u8 | 99 |
| +26 | aeg_decay1_level | u8 | 99 |
| +28 | aeg_decay2_level | u8 | 99 |
| +30 | aeg_release_level | u8 | 0 |
| +32 | attack | u8 | 0 |
| +34 | decay1 | u8 | 0 |
| +36 | decay2 | u8 | 0 |
| +38 | release | u8 | 40 |
| +40 | hold | u8 | 0 |
| +42 | time_key | u8 | 0 |
| +44 | level | u8 | 0 |
| +46 | aeg_breakpoint | MIDI | 39 |
| +48 | lvl_key_lo | u8 | 0 |
| +50 | lvl_key_hi | u8 | 0 |
| +52 | curve_lo | enum | 0 |
| +54 | curve_hi | enum | 0 |
| +56 | level_vel | u8 | 7 |
| +58 | second_lfo_pitch_mod_dest | enum 0..7 | 3 |
| +60 | second_lfo_amp_mod_dest | enum 0..7 | 3 |
| +66 | trailer_a | u8 | 127 [INTERN] |
| +68 | trailer_b | u8 | 127 [INTERN] |
| +70 | trailer_c | u8 | 127 [INTERN] |

Per-OP fields `second_lfo_pitch_mod_dest` (+58) and `second_lfo_amp_mod_dest` (+60) are replicated across all 8 operators with stride 123. The three trailer bytes per OP are firmware constants of the same category as the AN-X filter trailers.

---

## Drum Engine

**Engine pool start:** payload 12466 (Drum Key 1 base = payload 12469, abs 13160)
**Drum Key stride:** 68 bytes per key
**Drum Key count:** 73 (C0..C6, MIDI 12..84)
**Address convention:** Drum uses `filoffset = audit + 669` (vs +687 for AWM2/AN-X/FM-X)

### Drum has its own Part Common layout

Drum Part Common rel +144/+146 are **filter fields**, not AEG offsets. The interpretation of Part Common rel +126..+158 is therefore engine-type dependent. For Drum:

| Rel | Field | Encoding | Default |
|---:|---|---|---:|
| +126 | drum_aeg_attack | c64 | 64 |
| +128 | drum_aeg_decay | c64 | 64 |
| +130 | drum_aeg_sustain | c64 | 64 |
| +132 | drum_aeg_release | c64 | 64 |
| +144 | drum_filter_cutoff | c64 | 64 |
| +146 | drum_filter_resonance | c64 | 64 |

### Drum Key fields (per key, rel within 68-byte key block)

| Rel | Field | Encoding | Default |
|---:|---|---|---:|
| +0 | drumKeySW | bool | 1 |
| +4 | drumKeyRcvNoteOff | bool | 0 |
| +6 | drumKeyAssignMode | enum | 1 |
| +8 | drumKeyGroup | enum | 0 |
| +10 | drumKeyWaveformNumber | u16le | 28 |
| +12 | drumKeyPan | c64 | 64 |
| +14 | drumKeyRandomPan | direct | 0 |
| +16 | drumKeyAlternatePan | c64 | 64 |
| +22 | drumKeyConnect | enum | 1 |
| +26 | drumKeyLevel | direct | 127 |
| +28 | drumKeyLevelVel | c64 | 64 |
| +30 | drumKeyTimeAttack | direct | 0 |
| +32 | drumKeyTimeDecay1 | direct | 96 |
| +34 | drumKeyTimeDecay2 | direct | 80 |
| +36 | drumKeyLevelDecay1 | direct | 127 |
| +38 | drumKeyCoarse | c64 | 64 |
| +40 | drumKeyFine | c64 | 64 |
| +42 | drumKeyPitchVel | c64 | 64 |
| +44 | drumKeyFilterCutoff | u16le | 1023 |
| +46 | drumKeyFilterCutoffVel | c64 | 64 |
| +48 | drumKeyFilterResonance | direct | 0 |
| +50 | drumKeyHpfCutoff | u16le | 0 |
| +52 | drumKeyEqType | enum | 0 |
| +56 | drumKeyEqLowFreq | direct | 54 |
| +58 | drumKeyEqLowGain | c64 | 64 |
| +60 | drumKeyEqHiFreq | direct | 231 |
| +62 | drumKeyEqHiGain | c64 | 64 |

### Drum Part Common (Part-level fields, absolute addresses)

| Abs | Field | Encoding | Default |
|---:|---|---|---:|
| 6736 | drumPartElemPanToggle | bool | 1 |
| 6802 | drumPartArpPlayOnly | bool | 0 |
| 6815 | drumPartMainCategory | enum | 16 |
| 6819 | drumPartVelLimitLow | u8 | 1 |
| 6821 | drumPartVelLimitHigh | u8 | 127 |
| 6823 | drumPartNoteLimitLow | MIDI | 0 |
| 6825 | drumPartNoteLimitHigh | MIDI | 127 |
| 6827 | drumPartVelDepth | c64 | 64 |
| 6829 | drumPartVelOffset | c64 | 64 |
| 6831 | drumPartVolume | u8 | 100 |
| 6833 | drumPartPan | c64 | 64 |
| 6835 | drumPartReverbSend | u8 | 0 |
| 6837 | drumPartVariationSend | u8 | 0 |
| 6839 | drumPartDryLevel | u8 | 127 |
| 6847 | drumPartOutput | enum | 0 |
| 6849 | drumPartFilterAegAttack | c64 | 64 |
| 6851 | drumPartFilterAegDecay | c64 | 64 |
| 6853 | drumPartFilterAegSustain | c64 | 64 |
| 6855 | drumPartFilterAegRelease | c64 | 64 |
| 6867 | drumPartFilterCutoff | c64 | 64 |
| 6869 | drumPartResonance | c64 | 64 |
| 6903 | drumPartControlGroup | enum | 0 |
| 6913 | drumPitchBendUpper | c64 | 66 |
| 6915 | drumPitchBendLower | c64 | 62 |
| 6917 | drumDetuneHz | u16le | 128 |
| 6919 | drumNoteShift | c64 | 64 |
| 6961 | drumPart2EqType | enum | 0 |

### UI differences from other engines

Drum does **not** have the Part Settings > AEG Offset menu that AWM2/FM-X/AN-X have. Instead, AEG is exposed as **absolute values** under the Filter/Amp tab. This means the Drum engine does not use the shared AEG offset block (rel +144..+150) like the other three engines, but has its own Part Common layout at the same byte positions.

### [INTERN] bytes within Drum keys

Of the 4964 bytes in the drum-key zone (68 × 73 keys), 4934 (99.4%) are firmware constants. Specifically:

- 33 zero-padded byte positions per key (rel +1, +2, +3, +5, +7, +9, +13, +15, +17, +19, +20, +21, +23, +24, +25, +27, +29, +31, +33, +35, +37, +39, +41, +43, +47, +49, +53, +54, +55, +57, +59, +61, +63)
- rel +18 (value 90) and rel +67 (value 64) — constant non-zero firmware values

---

## AN-X Engine

**Engine pool start:** payload 12466
**Pool size:** 684 bytes

### Pre-OSC block (payload 12466..12489)
- `12465` part_random_pan_anx (c64, default 0)
- `12467` alternate_pan_anx (c64, default 64)
- `12469` random_pan, `12471` scaling_pan
- `12482` part_key_on_delay_sw (bool)
- `12483` part_half_damper_sw (bool)
- `12485` osc_reset_mode (enum: Off=0, Phase=1, Tune=2, Full=3)
- `12487` voltage_drift (u8, default 64)
- `12489` ageing (u8, default 100)

### Pitch LFO (payload 12491..12511)
- `12491..12503` Pitch LFO fields
- `12509` pitch_lfo_delay
- `12511` pitch_lfo_fadein

### Noise block (payload 12513..12518)
- `12513` noise_tone (u8, default 64)
- `12515` noise_connect (enum, default 0)
- `12518` noise_unknown_1 (u8, default 0)

### FEG (Filter EG) block (payload 12517..12529)
- `12517` feg_attack (direct, default 0)
- `12519` feg_decay (direct, default 160)
- `12521` feg_sustain (direct, default 0)
- `12523` feg_release (direct, default 160)
- `12525` feg_sustain_anx (u8, default 0)
- `12527` feg_release_anx (u8, default 160)
- `12529` feg_time_vel (preliminary)

### Filter LFO (payload 12531..12541)
- `12531` filter_lfo_wave (enum: Triangle=2, Square=1)
- `12533` filter_lfo_speed (u16le, default 208)
- `12537` filter_lfo_phase (enum 16-step)
- `12539` filter_lfo_delay
- `12541` filter_lfo_fadein

### Amp + AEG block (payload 12543..12557)
- `12543` amp_level (u16le)
- `12545` amp_level_vel
- `12547` amp_lfo_depth (c128, default 128)
- `12549` amp_aeg_attack (direct, default 0)
- `12551` amp_aeg_decay (direct, default 160)
- `12553` amp_aeg_sustain (u16le, default 511)
- `12555` amp_aeg_release (direct, default 115)
- `12557` amp_aeg_time_vel (direct, default 0)

### Amp LFO block (payload 12563..12573)
- `12563` amp_lfo_wave (enum)
- `12565` amp_lfo_speed (u16le, default 208)

### OSC1/OSC2/OSC3 fields (per OSC)

OSC1 base = audit abs 12626, OSC2 = 12751, OSC3 = 12876. Stride ~125 bytes per OSC. Selected fields:

| Field | OSC1 abs | OSC2 abs | OSC3 abs |
|---|---:|---:|---:|
| waveform | 12626 | 12751 | 12876 |
| octave | 12628 | 12753 | 12878 |
| pitch_lo (u16le) | 12630 | — | 12881 |
| peg_depth_marker | 12633 | — | 12883 |
| pitch_lfo_marker | 12637 | — | — |
| sync_pitch | 12638 | 12763 | — |
| pulse_width_vel | 12648 | — | — |
| shaper | 12654 | 12779 | — |
| ring_level_vel | 12668 | — | — |
| connect | 12670 | — | — |
| pulse_width | — | 12771 | 12896 |

### Filter 1 (payload 13005..13027)
- `13005` filter1_type (enum, default 1 = LPF12)
- `13007` filter1_cutoff_lo / `13008` filter1_cutoff_hi (u16le, default 1023)
- `13009` filter1_cutoff_vel
- `13011` filter1_feg_depth_lo (u16le)
- `13013` filter1_feg_depth_vel
- `13015` filter1_lfo_depth_lo (u16le)
- `13017` filter1_cutoff_key
- `13019` filter1_resonance, `13021` filter1_resonance_vel
- `13023` filter1_drive, `13025` filter1_drive_vel
- `13027` filter1_out_level (c64, default 64)

### Filter 2 (payload 13082..13104)
- `13081` (pad/marker, default 30) — [INTERN]
- `13082` filter2_type (enum, default 5 = HPF24)
- `13084` filter2_cutoff_lo / `13085` filter2_cutoff_hi (u16le)
- `13086` filter2_cutoff_vel
- `13088` filter2_feg_depth_lo (u16le)
- `13090` filter2_feg_depth_vel
- `13092` filter2_lfo_depth_lo (u16le)
- `13094` filter2_cutoff_key
- `13096` filter2_resonance, `13098` filter2_resonance_vel
- `13100` filter2_drive, `13102` filter2_drive_vel
- `13104` filter2_out_level

### Wave Folder + Modifier LFO (payload 13116..13148)

UI: [PART] Modifier tab with three sub-pages (Folder, EG, LFO). The Modifier tab has **only one** "LFO Depth" knob (abs 13122) — no separate byte for "Wave Folder LFO Depth".

- `13116` wavefolder_amount (u8, default 0)
- `13118` wavefolder_vel (u8, default 0)
- `13120` wavefolder_eg_depth
- `13122` modlfo_depth (u8 c128, default 128)
- `13124` wavefolder_texture
- `13126` wavefolder_type (enum, default 1 = Hard)

### Modifier EG (payload 13128..13134)
- `13128` modeg_attack, `13130` modeg_decay, `13132` modeg_sustain, `13134` modeg_release

### Modifier LFO (payload 13138..13148)
- `13138` modlfo_wave (enum, default 2 = Triangle)
- `13140` modlfo_speed_lo (u16le, default 208)
- `13146` modlfo_delay
- `13148` modlfo_fadein

### UI control redundancy in AN-X

AN-X exposes AEG in two separate UI controls with different encodings:

| UI location | Address | Encoding |
|---|---|---|
| Part Settings > AEG Offset | Part Common rel +144..+150 | c64 (offset added) |
| Filter/Amp > AMP > AEG | engine-pool 12549..12555 | direct (absolute value) |

Both exist in parallel. An editor must expose both.

---

## Control Assign

**Per-Part Control Assign:** 8 slots × 22 bytes stride, base address varies per Part
**Common Control Assign:** 32 slots × 22 bytes stride, abs 2452..3155 (944 bytes)

### Slot structure (22 bytes)

Verified from 35 test files including `Test-AWM2_Part_ControlAssign_destination1-8`, `AWM2_00_Init_CA_Source_AsgnKnob1..8`, `CA_CurveType_*`, `CA_Param1_8`.

| Rel | Field | Encoding | Default | Notes |
|---:|---|---|---:|---|
| +0 | enabled | bool | 0 | 0→1 on edit |
| +2 | dest_category | u8 | 1 | → 8 when slot activated |
| +3 | dest_category_hi | u8 | 0 | |
| +4 | destination_lo | u8 | 1 | Actual destination (lo byte) |
| +5 | destination_hi | u8 | 0 | 1 for index ≥128 |
| +8 | param2_or_curve_aux | u8 | 0 | Param2 / Steps-count / Threshold-aux |
| +10 | param1_or_curve_pri | u8 | 5 | Param1 AND curve primary (shared) |
| +12 | curve_secondary | u8 | 0 | Sigmoid→3, Threshold→1 |
| +14 | polarity | enum | 0 | Uni=0, Bi=1 |
| +16 | endmark | u8 const | 192 | 0xC0 |
| +21 | trailer | u8 | 18 | |

### Destination encoding (critical!)

Destination consists of **two bytes**: `destination_lo` (+4) and `destination_hi` (+5). Together they form an index into the authoritative 414-entry list `CONTROLLER_DESTINATIONS` (`ysfc_enums/controllers.py`):

```
CONTROLLER_DESTINATIONS_idx = destination_lo + destination_hi * 256
```

- For destinations with index **0..255**: write the value in `destination_lo`, `destination_hi=0`
- For destinations with index **256..511** (Performance, MS, Arp, Per-Part Assign Knobs): write `destination_lo = (idx − 256)`, `destination_hi = 1`

### Destination quick reference (verified subset)

For the complete list, see `ysfc_enums/controllers.py` (CONTROLLER_DESTINATIONS, 414 entries).

| Lo | Hi | Idx | Destination | Status |
|---:|---:|---:|---|:---:|
| 1 | 0 | 1 | InsA Param 1 (default) | ★★★★★ |
| 2..24 | 0 | 2..24 | InsA Param 2..24 (linear) | ★★★★★ |
| 25 | 0 | 25 | InsB Param 1 (specific param# in CA+11) | ★★★★★ |
| 50 | 0 | 50 | Part Reverb Send | ★★★★★ |
| 51 | 0 | 51 | Part Variation Send | ★★★★★ |
| 59 | 0 | 59 | Part LFO Destination 3 Depth | ★★★★★ |
| 60 | 0 | 60 | Element Level | ★★★★★ |
| 61 | 0 | 61 | Element Pan | ★★★★★ |
| 62 | 0 | 62 | Element Key On Delay Time | ★★★★★ |
| 85 | 0 | 85 | Element Cutoff Frequency | ★★★★★ |
| 87 | 0 | 87 | Element HPF Cutoff Frequency | ★★★★★ |
| 100 | 1 | 356 | Part Pan | ★★★★★ |
| 105 | 1 | 361 | Arp Gate Time | ★★★★★ |
| 118 | 1 | 374 | Motion Seq Length ("MS Length") | ★★★★★ |
| 142 | 0 | 142 | (alt Filter Cutoff) | ★★★★★ |

### Part After Touch — Part rel +600..+663 (64 bytes)

A separate 4-slot register with its own 16-byte stride. Has its own smaller destination enum.

| Rel | Field | Encoding | Default |
|---:|---|---|---:|
| +0 | enabled | bool | 0 |
| +2 | destination | enum | 1 (Pitch; 9=FilterCutoff) |
| +6 | param2 | u8 | 0 |
| +8 | param1 | u8 | 5 |
| +10 | curve_type | enum | 0 |
| +12 | polarity | enum | 0 (Uni=0, Bi=1) |
| +14 | endmark | const | 192 |

---

## Multi/GM 16-part files

Multi/GM files use the same multi-part architecture as standard multi-part Y2L files:

```
Performance Common              6701 bytes
16 × Part Common               92240 bytes (stride 5765)
Engine pool                    42583 bytes (15 × AWM2_stride + 1 × Drum_stride)
DPFM total                    141536 bytes
```

In a Multi/GM Init file, Parts 1–9 and 11–16 are AWM2 (Concert GrandPiano), and Part 10 is Drum (Standard Drum Kit). The 73 drum keys for Part 10 start at file offset 122261.

Multi/GM is supported by the existing multi-part code via `SUBBLOB_POINTER_REL = (5763, 5764)` and `get_subblob_pointer_pos()`. No new fields or structures are required in the serializer.

---

## Encoding conventions

| Notation | Description | Default |
|---|---|---:|
| direct | raw = UI value | varies |
| c64 | UI = raw − 64 | 64 |
| c128 | UI = raw − 128 | 128 |
| c50 | UI = raw − 50 | 50 |
| MIDI | C-2 = 0, C-1 = 12, ..., C3 = 60, ..., G8 = 127 | varies |
| bool | 0 = Off, 1 = On | varies |
| enum | enum-mapped | varies |
| u16le | little-endian 16-bit | varies |

---

## NOISE bytes (filtered out during diff analysis)

Always:
`{22-24, 60-63, 66, 184-198, 232, 234, 358, 376, 396-399, 488, 654, 670, 6705-6725, 7167-7168, 7419}`

Plus CRC/save-counter bytes:
`{710-711, 7411-7412}`

EC-sensitive hash bytes (when Element Count changes):
`{102, 103, 110, 111, 375, 673, 674, 685, 686}`

For Drum-specific testing, also filter:
`{filoffset 680-720, filoffset 7380-7400}` (DPFM sub-blob header noise)


## Insertion Connection Type (Y2L)

Binary verified in MODX M/ESP Y2L (2026-08-08): Part Common rel `+232` (Part 1 abs `6933`), u8. Values: `0=Parallel`, `1=A_to_B`, `2=B_to_A`. This field controls the routing *between* InsA and InsB and is distinct from per-element `elem_connect`. Classic-source mapping remains unverified.
