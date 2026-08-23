# SysEx Forge

**Local, reverse-engineered Soundmondo → Y2L conversion for Yamaha MONTAGE / MODX / MODX+ / MONTAGE M / MODX M.**

SysEx Forge started as a mapping project to identify Yamaha SysEx blocks and convert them into the modern MODX M / MONTAGE M Y2L structure. It has grown into a complete integration layer covering source parsing, engine detection, parameter normalization, waveform remapping, dependency handling and Y2L emission.

All browser conversion runs locally. No SysEx or library file needs to be uploaded to a server.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Current Status](#current-status)
- [Supported Platforms](#supported-platforms)
- [Waveform Mapping](#waveform-mapping)
- [Y2L Integrity Fixes](#y2l-integrity-fixes)
- [Project Files](#project-files)
- [Verification Policy](#verification-policy)
- [Known Limitations](#known-limitations)
- [Documentation](#documentation)
- [Development Workflow](#development-workflow)

---

## Features

- Parse Yamaha Soundmondo SysEx dumps from legacy and M-generation instruments
- Detect source family from Yamaha model ID
- Normalize source parameters into a common bridge representation
- Convert **AWM2**, **FM-X**, **AN-X** and **Drum** Performances
- Preserve multi-Part Performance structure where the source contains it
- Remap legacy preset waveform IDs to MODX M waveform IDs
- Detect unresolved User/Library waveform dependencies and fail closed
- Preserve or convert Yamaha Performance Common, Part Common, engine data, Scenes, Arps, Control Assign and selected FX structures
- Export modern `.Y2L` files for MODX M / MONTAGE M / ESP
- Bulk-convert many `.syx` files into separate Y2L files in a ZIP
- Validate modern EPFM container integrity before export
- No telemetry and no cloud processing

---

## Quick Start

### Browser converter

1. Open `tools/ysfc_forge_sysex_converter_v1_58.html` in a modern browser.
2. Drag one or more Soundmondo `.syx` files onto the import area.
3. Review detected platform, engines, Parts and dependency warnings.
4. Optionally load a companion `.Y2L` / `.Y2U` when external waveform dependencies must be resolved.
5. Convert one file or use bulk conversion.
6. Load the resulting Y2L in MODX M / MONTAGE M / ESP and verify the result.

### Python integration layer

The recoverable development pipeline is structured approximately as:

```text
Soundmondo .syx
      │
      ▼
sysex_parser.py
      │
      ▼
ysfc_bridge.py
      │
      ├── normalized parameter model
      ├── source-family/model-id routing
      ├── waveform/dependency mapping
      └── engine-specific bridge data
      │
      ▼
ysfc_serializer_adapter.py / Y2L serializer
      │
      ▼
MODX M / MONTAGE M .Y2L
```

The browser converter is currently the most complete end-to-end Soundmondo writer. Python adapters should be treated fail-closed unless the relevant path is explicitly marked verified.

---

## Architecture

SysEx Forge is split into four conceptual layers:

| Layer | Purpose |
|---|---|
| **Parser** | Reads Yamaha SysEx packets, addresses, model IDs and block payloads |
| **Normalizer / Bridge** | Converts source-specific parameters into a stable internal representation |
| **Mapping / Dependencies** | Handles waveform IDs, Arps, engine identities and source→target differences |
| **Serializer / Writer** | Emits modern Y2L Performance and container structures |

The project deliberately avoids “best guess” conversion. Unknown or ambiguous data is preserved only when structurally safe; otherwise export is blocked or a warning is shown.

---

## Current Status

### Engine mapping checkpoints

| Engine | SysEx Forge checkpoint | Status |
|---|---|---|
| **FM-X** | v1.0.75 | ✅  ESP verified |
| **AWM2** | v1.1.26 | ✅ ESP verified |
| **Drum** | v1.2.7 | ✅ ESP verified |
| **AN-X** | v1.3.9 | ✅ ESP verified |

Selected ESP-verified milestones include:

- FM-X core, operators, Smart Morph preservation and extended controller coverage
- AWM2 element engine, Part Common, Control Assign, Arp slots, Motion Sequence, Zone and key-controller destinations
- Drum key engine, Part Common, Control Assign, Motion Sequence and Zone state
- AN-X oscillator, synthesis/EG, filter, amp/AEG and LFO structures

The mapping project and the production Soundmondo converter are related but versioned separately. `v1.x` engine checkpoints document reverse-engineering progress; `ysfc_forge_sysex_converter_v1_27.html` is the current browser application.

---

## Supported Platforms

Canonical source-family routing is based on Yamaha model ID:

| Model ID | Source family | Typical products |
|---:|---|---|
| `0x02` | `legacy_montage` | MONTAGE |
| `0x07` | `legacy_modx` | MODX / MODX+ |
| `0x0D` | `m_generation` | MONTAGE M / MODX M |

The source family is derived from model identity, not guessed from UI labels or filenames.

### Soundmondo block families

Legacy sources use Yamaha three-byte Performance block addresses such as:

```text
30 40 00   Performance Common
31 0p 00   Performance Part
41 ep 00   AWM2 Oscillator / Amplitude / Pitch
42 ep 00   AWM2 Filter / EQ / LFO
48 0p 00   FM-X Common
49 op 00   FM-X Operator
5p kk 00   Drum Key
```

M-generation Soundmondo uses four-byte addresses such as:

```text
06 00 00 00   Performance Name
06 00 01 00   Performance Common 1-byte
06 00 02 00   Performance Common 2-byte
1p 00 01 00   Part 1-byte
1p 00 02 00   Part 2-byte
2p xx ee 00   AWM2 Element blocks
3p xx xx 00   FM-X blocks
4p xx xx 00   AN-X blocks
2p 10 kk 00   Drum Key
```

See `SYSEX_FORGE_REFERENCE.md` for the compact block reference.

---

## Waveform Mapping

Legacy AWM2 preset waveform IDs are not numerically identical to MODX M IDs.

The current master mapping covers:

- **6347** legacy waveform identities considered
- **6346** mapped to MODX M
- **1** intentionally unresolved waveform: legacy ID **3720 — `Sagat2 Sw`**

Mapping confidence is retained instead of flattened:

- `EXACT_NAME`
- `NORMALIZED_EXACT`
- `STRUCTURAL_MATCH`
- `UNRESOLVED`

Unresolved preset or external User/Library waveforms must not be silently redirected to another waveform.

Recommended repository artifacts:

```text
mapping/
  waveforms_legacy.py
  waveform_remap_legacy_to_m.py
  YSFC_waveform_mapping_master_v1.json
  YSFC_waveform_mapping_master_v1.csv
  YSFC_waveform_mapping_production_v1.js
```

---

## Y2L Integrity Fixes

Two important container bugs were identified during large-library testing.

### EPFM tail integrity

The tail after the NUL-terminated EPFM name must consist of complete 32-bit words:

```text
0, 4, 8, 12, 16, ... bytes  → valid
1, 2, 3, 5, 6, 7, ...       → invalid
```

A final remainder of 1–3 bytes may be trimmed **only when every trimmed byte is zero**. Non-zero incomplete data must block export.

### EPFM Performance IDs — 5 × 128

Modern Y2L supports 640 Performance slots as five banks of 128:

```text
bank = index // 128
slot = index % 128
id   = 0x00400000 | (bank << 8) | slot
```

Examples:

```text
0   → 0x00400000
127 → 0x0040007F
128 → 0x00400100
255 → 0x0040017F
256 → 0x00400200
512 → 0x00400400
639 → 0x0040047F
```

This encoding was isolated and verified in MODX M ESP at the exact 128→129 boundary. Packed-ID files containing **129, 130, 256 and 414 Performances** loaded successfully.

The old assumptions below are obsolete:

```text
rec[11] = index & 0xFF
0x00400000 + index
```

The SysEx Converter normally emits one Performance per Y2L, but v1.27 uses the shared rule defensively so future multi-Performance support cannot reintroduce the bug.

---

## Project Files

A full development checkout should contain these areas:

```text
tools/
  ysfc_forge_sysex_converter_v1_58.html

integration/soundmondo/
  sysex_parser.py
  ysfc_bridge.py
  ysfc_serializer_adapter.py
  block_maps/
  parameter_maps/
  tests/

mapping/
  waveform mapping sources and generated artifacts

serializer/
  ysfc_serializer.py
  ysfc_transcoder_classic_to_y2l.py
  ysfc_source_family.py
  supporting enums / helpers

docs/
  SYSEX_FORGE_FULL_CONTEXT.md
  SYSEX_FORGE_FULL_CONTEXT_sv.md
  SYSEX_FORGE_REFERENCE.md
  SYSEX_FORGE_REFERENCE_sv.md
```

Private Soundmondo corpus files and Yamaha PDF manuals should not be redistributed in the public repository.

---

## Verification Policy

SysEx Forge uses an evidence-first policy.

| Mark | Meaning |
|---|---|
| **ESP_VERIFIED** | Result loaded and was inspected in MODX M ESP |
| **★★★★★** | Binary-verified using controlled A/B test files |
| **★★★★☆** | Derived from official Yamaha data / strong structural evidence |
| **★★★☆☆** | Probable mapping, not yet directly verified |
| **[STRUCT]** | Structure identified but UI semantics incomplete |
| **[UNKNOWN]** | Do not write or infer |

Core policy:

> **Fail closed rather than invent defaults or mappings.**

A missing source family, unresolved dependency or ambiguous block must never be silently replaced with unrelated template values merely to make a file export.

---

## Known Limitations

- External User/Library waveform dependencies require explicit resolution or a companion library.
- Generic reconstruction of Smart Morph interpolation tables is not considered complete merely because transport/preservation works.
- Effect parameters cannot be blindly raw-copied across generations when effect layouts differ.
- Some M-generation Soundmondo versions use observed payload lengths that differ from Yamaha's documented bulk-dump lengths; those overrides are kept separately.
- Hardware coverage is centered on MODX M / ESP. MONTAGE M is structurally compatible but should continue to receive hardware verification.
- Python adapter paths are not automatically equivalent to the current browser converter; check verification status before using them for production emission.

---

## Documentation

| Document | Purpose |
|---|---|
| [`README.md`](README.md) | Project overview and quick start |
| [`README_sv.md`](README_sv.md) | Swedish project overview |
| [`SYSEX_FORGE_REFERENCE.md`](SYSEX_FORGE_REFERENCE.md) | Parameter-level master byte map: Soundmondo/WebMIDI source → Y2L target |
| [`SYSEX_FORGE_REFERENCE_sv.md`](SYSEX_FORGE_REFERENCE_sv.md) | Compact Swedish reference |
| [`SYSEX_FORGE_FULL_CONTEXT.md`](SYSEX_FORGE_FULL_CONTEXT.md) | Full technical/recovery context |
| [`SYSEX_FORGE_FULL_CONTEXT_sv.md`](SYSEX_FORGE_FULL_CONTEXT_sv.md) | Full Swedish technical/recovery context |

For the target Y2L format itself, the companion YSFC Forge documentation remains authoritative for target blob offsets and container structure.

---

## Development Workflow

Recommended workflow for a new mapping:

1. Create a clean baseline Performance.
2. Change exactly one UI parameter.
3. Export or capture Soundmondo SysEx.
4. Diff source blocks and identify the changed byte(s).
5. Confirm encoding with at least one second value when practical.
6. Add parser/bridge mapping.
7. Generate Y2L.
8. Test in MODX M ESP.
9. Mark `ESP_VERIFIED` only after the resulting Performance loads and the UI/sound matches.
10. Update Full Context + Reference and add a regression fixture.

Do not promote an inferred mapping to verified status solely because a file parses successfully.
