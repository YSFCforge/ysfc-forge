# Changelog

All notable changes to YSFC Forge are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Multi/GM 16-part file format** — full support for the 16-part multitimbral configuration (15 AWM2 + 1 Drum on Part 10, per GM standard)
- **Pointer-based sub-blob layout detection** — `parse_subblob_layout()` rewritten to use pointer model instead of name-string search, enabling Multi/GM support
- **Drum part Filter AEG fields** — `drumPartFilterAegAttack/Decay/Sustain/Release` (audit 6849-6855)
- **Drum part fields** — `drumPartMainCategory` (6815), `drumPartControlGroup` (6903)
- **AN-X UI fields** — 50 new fields identified through corpus analysis (Noise Tone/Connect, OSC1-3 Waveform/Octave/Pitch/Shaper, OSC EG fields, etc.)
- **FM-X UI fields** — per-OP `op_2nd_lfo_pitch_mod_dest` and `op_2nd_lfo_amp_mod_dest` (rel +58, +60) replicated across all 8 operators
- **FM-X PRE_OP fields** — `second_lfo_phase`, `second_lfo_delay`, `op1_fm_harmonics`, `filter_resonance_vel`, `op1_freq_mode`, etc.

### Fixed
- `detect_engine_from_name()` — `.strip` without parentheses (returned method object instead of string)
- `parse_subblob_layout()` — `.rstrip` without parentheses
- Casing mismatch between pointer-model return value (`'Drum'`) and `ENGINE_BLOCK_OTHER` keys (`'DRUM'`)

### Changed
- **AN-X coverage: ~72% → 100%** — all engine pool bytes accounted for
- **FM-X coverage: ~95% → 100%** — including the 5-byte per-OP gap (rel +58, +60, +66, +68, +70)
- **Drum coverage: partially mapped → 100%** — 27 DRUM_KEY fields + 27 DRUM_PART_COMMON fields binary-verified
- **AWM2 cleanup** — `extended_lfo` default 0→1, `lfoExtendedSpeed` u8→u16le, `feg_depth_vel` added at rel +243, `pegKFCenterNote` corrected
- **Test corpus** — expanded from 1908 to 2010+ binary-verified test files

### Methodology improvements
- **Corpus analysis method** — scanning all test files for 100%-constant bytes (firmware constants) and varying bytes (UI fields)
- **Stride pattern recognition** — discovered FM-X per-OP fields via 123-byte stride analysis (40 bytes mapped in one pass)
- **Small-edit expansion** — extended from single-edit (≤3 diff) to small-edit (≤15 diff) to capture multi-byte UI parameters

## [Previous milestones]

### AWM2 mapping complete (100%)
- All 8 elements binary-verified with stride 313
- Element 1 base = audit 12469
- PEG, FEG, EQ, LFO, Level Scaling all 100% mapped

### Drum filoffset convention discovered
- Drum uses `filoffset = audit + 669` (vs +687 for AWM2/AN-X/FM-X)
- Verified via drumKeySW pattern matching (74 positions, stride 68)

### Insertion FX index complete
- All 57 verified FX types documented
- Spans THRU through Wave Folder

### Common Scene block corrected
- Position corrected from abs 1671 to abs 1710 (8 scenes × 71 bytes)

---

## Versioning

YSFC Forge does not yet use formal version numbers for releases. This changelog tracks engine-mapping progress and major tool updates. When the project reaches a stable 1.0 release, semantic versioning will begin.

Tool files in `tools/`, `translators/`, and `utilities/` carry their own version numbers in the filename (e.g., `ysfc_forge_v1.19.html`).
