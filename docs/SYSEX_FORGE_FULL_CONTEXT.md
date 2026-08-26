# SysEx Forge — Full Context

*Soundmondo SysEx → MODX M / MONTAGE M Y2L integration project*  
*Primary verification target: Yamaha MODX M + MODX M ESP*  

---

## Foreword — how to read this document

This is the recovery/master context for the **SysEx Forge** integration project.

SysEx Forge is not the Y2L format mapping project itself. The target Y2L format is documented in the companion **YSFC Forge** documentation. SysEx Forge sits above that format work and answers a different question:

> How do we take a Yamaha Soundmondo SysEx Performance from multiple Yamaha generations and emit a structurally valid, high-fidelity modern Y2L Performance?

The document therefore concentrates on:

1. source SysEx families and block layouts;
2. source→normalized mapping;
3. source→target generation differences;
4. waveform/dependency resolution;
5. Y2L writer integration;
6. ESP-verified conversion checkpoints;
7. fail-closed rules and unresolved areas.

### Evidence priority

1. **ESP_VERIFIED** — generated Y2L loaded in MODX M ESP and the relevant UI/sound state was inspected.
2. **★★★★★ Binary verified** — controlled single-edit diff or equivalent direct binary evidence.
3. **★★★★☆ Yamaha-derived** — official Yamaha Data List / MIDI bulk table plus structural confirmation.
4. **★★★☆☆ Inferred** — strong pattern but not directly verified.
5. **[STRUCT]** — structure known, semantics incomplete.
6. **[UNKNOWN]** — do not write or invent.

Never upgrade an inferred field to verified merely because a file loads.

---

# 1. Project purpose

SysEx Forge converts Yamaha Soundmondo SysEx Performances into modern Y2L Performances usable by:

- MODX M
- MONTAGE M
- MODX M ESP

Supported source families include:

- MONTAGE
- MODX
- MODX+
- MONTAGE M
- MODX M

The project is designed as an interoperability layer, not a SysEx librarian and not a generic MIDI editor.

---

# 2. Relationship to YSFC Forge

The projects share code and research but have separate responsibilities.

## YSFC Forge

Responsible for:

- modern Y2L/Y2U container structure;
- DPFM blob structure;
- Performance Common / Part Common target offsets;
- AWM2 / FM-X / AN-X / Drum target engine layouts;
- EPFM/DPFM records;
- library merging/editing/transcoding.

## SysEx Forge

Responsible for:

- identifying Yamaha Soundmondo source blocks;
- parsing legacy and M-generation SysEx;
- normalizing source parameters;
- converting source enums/encodings;
- mapping legacy preset waveforms to MODX M;
- detecting User/Library dependencies;
- routing data into YSFC serializer/writer structures;
- end-to-end Soundmondo → Y2L validation.

Target offsets should not be duplicated independently when the authoritative mapping already exists in YSFC Forge.

---

# 3. Repository architecture

Recommended source tree:

```text
tools/
  ysfc_forge_sysex_converter_v1_27.html

integration/soundmondo/
  sysex_parser.py
  ysfc_bridge.py
  ysfc_serializer_adapter.py
  block_tables.py / block_maps/
  normalized_parameter_map.*
  effect_type_map.*
  tests/

mapping/
  waveforms_legacy.py
  waveform_remap_legacy_to_m.py
  YSFC_waveform_mapping_master_v1.json
  YSFC_waveform_mapping_master_v1.csv
  YSFC_waveform_mapping_production_v1.js

serializer/
  ysfc_serializer.py
  ysfc_serializer_classic.py
  ysfc_transcoder_classic_to_y2l.py
  ysfc_source_family.py
  ysfc_enums/

tests/
  conversion and container regression tests

docs/
  SYSEX_FORGE_FULL_CONTEXT.md
  SYSEX_FORGE_FULL_CONTEXT_sv.md
  SYSEX_FORGE_REFERENCE.md
  SYSEX_FORGE_REFERENCE_sv.md
```

---

# 4. Source-family identification

The canonical routing is:

```text
modelId → source family → engine/Part topology → mapping path → Y2L writer
```

Do not use an independent `sourceProfile` control path when Yamaha model identity is available.

| Model ID | Canonical source family | Products |
|---:|---|---|
| `0x02` | `legacy_montage` | MONTAGE |
| `0x07` | `legacy_modx` | MODX / MODX+ |
| `0x0D` | `m_generation` | MONTAGE M / MODX M |

File format/version may still matter for physical parsing and compatibility validation, but model ID is the semantic source-family selector.

---

# 5. SysEx framing

Yamaha Performance bulk messages use manufacturer ID `0x43` and the Yamaha group/model family used by the relevant generation.

Soundmondo captures contain a series of block messages rather than one monolithic raw Performance structure.

The parser should retain:

- Yamaha model ID;
- address bytes;
- raw payload;
- detected block family;
- source Soundmondo version if present;
- Part/Element/Operator/Key indices captured from the address;
- provenance/confidence.

Unknown blocks should be retained as observed data when possible, but must not automatically be copied into a structurally different target layout.

---

# 6. Legacy block map

Legacy MONTAGE / MODX / MODX+ Soundmondo uses three-byte addresses.

Core blocks:

| Address pattern | Meaning | Typical payload |
|---|---|---:|
| `30 40 00` | Performance Common | 94 |
| `30 41 00` | Reverb | 71 |
| `30 42 00` | Variation | 72 |
| `30 43 00` | A/D Insertion A | 68 |
| `30 44 00` | A/D Insertion B | 68 |
| `30 45 00` | Master EQ | 21 |
| `30 46 00` | Master Effect | 72 |
| `30 47 00` | Arpeggio Common | 13 |
| `30 48 00` | Motion Seq Common | 6 |
| `30 4C 00` | Scene Common | 128 |
| `31 0p 00` | Performance Part | 121 |
| `31 1p 00` | Part Motion Seq / Lane settings | 64 |
| `31 2p 00` | Insertion A | 68 |
| `31 3p 00` | Insertion B | 68 |
| `31 4p 00` | Part LFO | 39 |
| `31 5p 00` | Zone | 17 |
| `31 6p 00` | Arpeggio Part | 92 |
| `41 ep 00` | AWM2 Oscillator + Amp + Pitch | 103 |
| `42 ep 00` | AWM2 Filter + EQ + LFO | 70 |
| `48 0p 00` | FM-X Common | 86 |
| `49 op 00` | FM-X Operator | 47 |
| `5p kk 00` | Drum Key | 47 |

Observed undocumented metadata/extension blocks must remain separately classified from Yamaha-documented blocks.

---

# 7. M-generation block map

MONTAGE M / MODX M uses four-byte Soundmondo addresses.

## 7.1 Performance Common

| Address | Block |
|---|---|
| `06 00 00 00` | Performance Name |
| `06 00 01 00` | Performance Common 1-byte |
| `06 00 02 00` | Performance Common 2-byte |
| `06 00 03 00` | Performance Common Controller |
| `06 00 04 00` | A/D Insertion A |
| `06 00 05 00` | A/D Insertion B |
| `06 00 06 00` | Arpeggio Common |
| `06 00 07 00` | Reverb |
| `06 00 08 00` | Variation |
| `06 00 09 00` | VCM Rotary Speaker |
| `06 00 0A 00` | Master EQ |
| `06 00 0B 00` | Master Effect |
| `06 00 0C 00` | Motion Seq Common |
| `06 00 0D 00` | Super Knob settings |
| `06 00 10 00` | FM-X Smart Morph data |
| `06 00 11 00` | FM-X Smart Morph PNG |
| `06 00 20 00` | AN-X Smart Morph data |
| `06 00 21 00` | AN-X Smart Morph PNG |

## 7.2 Part Common

| Pattern | Block |
|---|---|
| `1p 00 00 00` | Part Name |
| `1p 00 01 00` | Part 1-byte |
| `1p 00 02 00` | Part 2-byte |
| `1p 00 03 00` | Part Pitch / Effect 2-byte |
| `1p 00 04 00` | Insertion A |
| `1p 00 05 00` | Insertion B |
| `1p 00 06 00` | Arpeggio Part |
| `1p 00 07 00` | LFO |
| `1p 00 08 00` | Zone |
| `1p 00 09 00` | Key Controller Box |
| `1p 03 0c 00` | Scene Part |
| `1p 05 bb 00` | Controller boxes |
| `1p 06 L0 00` | Motion Seq Lane 1-byte settings |
| `1p 07 L0 00` | Motion Seq Lane 2-byte settings |
| `1p 08 Lm 00` | Motion Seq Lane sequence |

## 7.3 Engines

AWM2:

```text
2p 00 ee 00   Element 1-byte
2p 01 ee 00   Oscillator
2p 02 ee 00   Amplitude
2p 03 ee 00   Pitch
2p 04 ee 00   Filter + EQ + LFO
```

Drum:

```text
2p 10 kk 00   Drum Key
```

FM-X:

```text
3p 00 00 00   FM-X Part Common
3p 00 01 00   FM-X Filter
3p 01 0o 00   Operator Controller Box Switch
3p 02 0o 00   Operator
```

AN-X:

```text
4p 00 00 00   AN-X Part Common
4p 01 0o 00   Oscillator Controller Box Switch
4p 02 0o 00   Oscillator
4p 03 0f 00   Filter Controller Box Switch
4p 04 0f 00   Filter
4p 05 00 00   Wave Folder
```

Observed Soundmondo payload sizes may differ from Yamaha's bulk-table sizes for specific Soundmondo versions. Store empirical overrides explicitly rather than replacing the documented sizes.

---

# 8. Normalized bridge model

The bridge layer exists to prevent source-generation details from leaking directly into the Y2L writer.

A normalized Performance should carry at least:

```text
source_family
model_id
soundmondo_version
performance:
  name
  category
  volume
  pan
  tempo
  arp_master
  motion_seq_master
parts[]:
  part_number
  name
  engine
  enabled
  keyboard_control
  note_limits
  velocity_limits
  volume
  pan
  engine_data
  arp_data
  scene_data
  controller_assignments
dependencies:
  preset_waveforms
  user_waveforms
  library_waveforms
  user_arps
warnings[]
provenance[]
```

The bridge must distinguish:

- missing source data;
- source default;
- explicit source value;
- unresolved dependency;
- unsupported feature.

These states are not interchangeable.

---

# 9. Engine status

## 9.1 FM-X

FM-X was the first engine driven to a completion checkpoint.

Verified milestones include:

- operator identity and core frequency/level structures;
- Algorithm / Feedback;
- PEG / filter / LFO groups;
- operator controller sensitivity groups;
- 1st-LFO destination depth ratios;
- extended 2nd-LFO matrix;
- Smart Morph transport/preservation.

Checkpoint: **v1.0.75**, with later documentation corrections around operator-relative controller/LFO fields.

Smart Morph note:

> Preserving transported Smart Morph data does not prove that arbitrary interpolation-table reconstruction is understood.

## 9.2 AWM2 Normal Part

ESP-verified sequence:

- v1.1.2 Active Emission
- v1.1.3 Amplitude + AEG
- v1.1.4 Filter + FEG
- v1.1.5 Pitch + PEG
- v1.1.6 Element LFO + EQ
- v1.1.7 Element Completion
- v1.1.8 Part Common Core
- v1.1.9 Note Shift
- v1.1.12 Control Assign
- v1.1.13 Preset Arp Slots 8/8
- v1.1.14 Arp Common + Play FX
- v1.1.16 Motion Sequence receive
- v1.1.17 Motion Sequence lanes/sequences
- v1.1.20 Part 2-byte Core
- v1.1.26 Zone + Key Controller Destination Completion

AWM2 completion checkpoint: **v1.1.26**.

## 9.3 Drum

ESP-verified milestones:

- v1.2.1 Drum Key emission
- v1.2.2 Part Common
- v1.2.3 2-byte + Pitch/Effect
- v1.2.6 Control Assign + Motion Sequence
- v1.2.7 Final Part State + Zone Completion

Drum completion checkpoint: **v1.2.7**.

## 9.4 AN-X

ESP-verified milestones:

- v1.3.0 Source/Destination Coverage
- v1.3.1 Oscillator Identity/Tuning
- v1.3.2 Part settings + Osc Out Level
- v1.3.3 Oscillator Synthesis + EG
- v1.3.5 Filter Core
- v1.3.6 Amp + AEG
- v1.3.9 Pitch LFO + Mod LFO

Current AN-X checkpoint in this context: **v1.3.9**.

---

# 10. Key On Delay

A cross-generation AWM2 issue was isolated around Key On Delay handling.

The production mapping must use the verified source/target fields rather than infer a byte from local proximity.

This work also reinforced the project rule that a field with a similar name in legacy and M-generation structures is not necessarily stored with the same width, unit or placement.

Keep direct verification fixtures for Key On Delay in the repository/recovery package.

---

# 11. Portamento

Portamento was mapped separately for Performance and Part scope.

## 11.1 Target modern Y2L offsets

Within target modern structures:

```text
Performance Portamento Switch   Common rel +29
Performance Portamento Time     Common rel +94

Part Portamento Switch          Part Common rel +39
Part Portamento Time            Part Common rel +220
Part Portamento Mode            Part Common rel +222
```

Important correction:

```text
Common +41 = Assignable Switch
```

It is **not** Portamento.

## 11.2 Legacy Soundmondo source

```text
30 40 00 +0x3A   Performance Portamento Switch
30 40 00 +0x39   Performance Portamento Time

31 0p 00 +0x31   Part Portamento Switch
31 0p 00 +0x32   Part Portamento Time
31 0p 00 +0x33   Part Portamento Mode
```

## 11.3 M-generation Soundmondo source

```text
06 00 01 00 +0x00   Performance Portamento Switch
06 00 02 00 +0x20   Performance Portamento Time

1p 00 01 00 +0x0A   Part Portamento Switch
1p 00 03 00 +0x08   Part Portamento Time
1p 00 03 00 +0x0A   Part Portamento Mode
```

SysEx Converter v1.26 introduced the optional **Force Portamento OFF** diagnostic/export option, disabled by default. Normal conversion should preserve valid source Portamento state.

---

# 12. Waveform mapping

## 12.1 Problem

Legacy preset waveform numbers cannot be copied directly to MODX M.

The same semantic waveform frequently has a different numeric ID in the target generation.

## 12.2 Master result

Legacy waveform corpus:

```text
Total identities considered: 6347
Mapped:                     6346
Unresolved:                    1
```

Only unresolved entry:

```text
legacy ID 3720  Sagat2 Sw
```

## 12.3 Confidence classes

```text
EXACT_NAME
NORMALIZED_EXACT
STRUCTURAL_MATCH
UNRESOLVED
```

The confidence class must stay attached to the mapping so that later auditing can distinguish direct identity from a structurally justified match.

## 12.4 Fail-closed behavior

If an AWM2 element references:

- a known preset waveform → map it;
- an external User/Library waveform with a resolvable companion dependency → resolve it;
- an unresolved external waveform → block or warn, never silently substitute.

---

# 13. Arps and dependencies

Preset Arp slots and User Arp dependencies are separate concerns.

Verified/implemented integration work includes:

- 8 preset-Arp slots;
- Arp Common / Play FX core;
- User Arp detection in legacy library sources;
- later corrections for X8L/X8U User Arp handling in YSFC-related code.

A Soundmondo SysEx alone may not contain every external User/Library dependency required to reproduce a Performance. Companion library support exists for that reason.

The dependency layer should produce explicit outcomes:

```text
resolved preset dependency
resolved companion-library dependency
unresolved external dependency
not applicable
```

---

# 14. Control Assign

Control Assign was mapped in both the target Y2L project and the Soundmondo integration.

Important UI terminology:

- the user-visible field is **CURVE TYPE**;
- there is no separate user-visible field between Destination and CURVE TYPE merely because an unknown record offset exists there;
- the green graph represents **Depth**, not a separate parameter.

Verified target Control Assign facts from clean tests include:

```text
CURVE TYPE target absolute 0x22D4 / 8916
Polarity target absolute   0x22DA / 8922
Depth target absolute      0x22DC / 8924
Depth raw = UI + 128
UNI = 0
BI  = 1
```

Unknown/reserved offsets must stay unknown until independently proven.

---

# 15. Multi-Part topology

Multi-Part generation exposed structural fields that cannot be derived from single-Part templates by naïve repetition.

One verified Python correction established:

```text
single Part:
  Entr rel16..18 = 02 00 01

contiguous Parts 1..N, N=2..8:
  Entr rel16..18 = 00 00 ((1<<N)-1)
```

A three-Part verified case:

```text
00 00 07
```

For generic sparse topologies or >8 Parts, do not extrapolate this one-byte topology rule unless using separately verified/native Entr handling.

Part Common pointer behavior also required engine-aware handling rather than blindly copying Part 1 metadata.

This is an example of the project-wide rule:

> multi-Part structure must be inferred from multi-Part evidence.

---

# 16. Modern EPFM integrity

## 16.1 EPFM name tail

Each modern EPFM record contains a fixed header followed by a NUL-terminated Performance name and optional reference words.

The data after the NUL must have length divisible by four.

Valid:

```text
0, 4, 8, 12, ...
```

Invalid:

```text
1,2,3,5,6,7,9,10,11,...
```

Defensive sanitizer:

1. find the first NUL after the name start;
2. calculate tail length;
3. if remainder is zero, leave unchanged;
4. if remainder is 1–3, inspect only those final bytes;
5. trim them only if all are `00`;
6. otherwise block export.

Do not turn every tail into zero bytes. Complete 4-byte words are real structure and must be preserved.

## 16.2 5 × 128 Performance IDs

Modern Y2L maximum Performance capacity is 640.

Encoding:

```text
bank = floor(index / 128)
slot = index % 128
ID   = 0x00400000 | (bank << 8) | slot
```

Boundary evidence:

- 115, 120, 127, 128 first-N files loaded;
- 129, 144, 160, 192, 224 failed with the old scheme;
- packed-ID files with 129, 130, 256 and 414 all loaded.

Therefore the exact bank transition is verified at 128→129.

Obsolete implementations:

```text
record[11] = index & 0xFF
entry_id = 0x00400000 + index
```

---

# 17. SysEx Converter application history

Important production checkpoints:

| Version | Meaning |
|---|---|
| **v1.19** | Safe conversion-logic baseline after stress testing |
| **v1.20** | UI-only |
| **v1.21** | Filename/UI changes |
| **v1.22** | Structured writer log |
| **v1.23** | Multi-engine colored badges |
| **v1.24** | EPFM tail sanitizer/fix |
| **v1.25** | Portamento experiment; first target mapping partly wrong |
| **v1.26** | Corrected Portamento preservation / Force OFF optional |
| **v1.27** | Defensive shared 5×128 modern EPFM Performance-ID rule |

Rejected baseline:

```text
v1.17
```

Reason: it substituted template defaults for missing source families. This violates fail-closed conversion policy.

---

# 18. Stress-test summary

A broad Soundmondo source corpus was tested against the safe converter baseline.

Observed totals:

```text
MONTAGE M   471 total / 432 export / 39 blocked
MODX M      116 total / 101 export / 15 blocked
MODX+       384 total / 308 export / 76 blocked
MODX       4089 total / 3432 export / 657 blocked
MONTAGE    2070 total / 1882 export / 188 blocked
```

A blocked export is not automatically a bug. Many blocks are intentional when a dependency or source structure is not safely convertible.

---

# 19. Writer safety rules

The following rules are mandatory for production paths.

## 19.1 No invented defaults

Do not replace an absent source family with target template values unless Yamaha sparse semantics have been proven for that specific omission.

## 19.2 No blind raw copy across generations

A Yamaha parameter with the same UI label may:

- use a different address;
- use different width;
- use a different enum;
- use different unit/range;
- be split into another block.

Copy only through a verified mapping.

## 19.3 Preserve provenance

For every normalized field where practical, retain:

```text
source block
source offset
source value
mapping rule
confidence/evidence
```

## 19.4 Validate after serialization

At minimum:

- EPFM count;
- EPFM ID sequence;
- EPFM tail integrity;
- EPFM blob length / DPFM offset;
- DPFM record count;
- target Performance blob structural invariants.

---

# 20. Companion library handling

A companion Y2L/Y2U can be loaded by the browser converter to resolve external waveform/sample dependencies.

The original companion file is never modified.

The user explicitly selects which target bank the companion file represents (User / Library 1..8), because bank identity is semantic and should not be guessed.

---

# 21. Testing methodology

Preferred mapping experiment:

```text
baseline
   ↓
change exactly one parameter
   ↓
capture/export Soundmondo
   ↓
binary diff
   ↓
second-value confirmation
   ↓
parser mapping
   ↓
Y2L emission
   ↓
ESP load
   ↓
UI/sound inspection
```

For range/encoding fields, use values that disambiguate:

- direct vs centered encodings;
- u8 vs u16;
- signed vs biased;
- enum vs bitfield.

Examples:

```text
Depth +55 / -55
Polarity UNI / BI
Portamento On / Off
Note Shift +12
```

---

# 22. Recovery guidance

A future developer should recover the project in this order:

1. Start from the latest verified browser converter.
2. Restore source-family/model-ID routing.
3. Restore block tables and normalized parameter maps.
4. Restore waveform master mapping.
5. Restore serializer/Y2L writer.
6. Run parser/bridge tests.
7. Run waveform mapping validation.
8. Run EPFM tail and 5×128 regression tests.
9. Test a small known ESP fixture.
10. Only then expand to new mappings.

Do not start from an old experimental Python adapter and assume it has parity with the latest browser writer.

---

# 23. Open areas

High-value remaining work includes:

- continued AN-X coverage beyond the latest checkpoint where still applicable;
- more MONTAGE M hardware verification;
- complete external User/Library Arp and waveform dependency workflows;
- effect-specific conversion where layouts differ by generation;
- generic Smart Morph reconstruction beyond preserved transport;
- multi-Part edge cases with sparse/>8 topology;
- keeping Python emission behavior synchronized with the production browser writer.

---

# 24. Canonical current rules

For quick recovery, these are non-negotiable current facts:

```text
Source family:
  model 02 → legacy_montage
  model 07 → legacy_modx
  model 0D → m_generation

Modern Y2L max Performances:
  640 = 5 × 128

Modern EPFM Performance ID:
  0x00400000 | ((index//128)<<8) | (index%128)

Modern EPFM tail:
  bytes after name NUL must be multiple of 4

Waveform master:
  6346 / 6347 mapped
  unresolved legacy 3720 = Sagat2 Sw

Portamento target:
  Perf Switch +29
  Perf Time +94
  Part Switch +39
  Part Time +220
  Part Mode +222

Common +41:
  Assignable Switch, NOT Portamento

Conversion policy:
  FAIL CLOSED
```

---

# 25. Document roles

- **README** — project introduction and usage.
- **REFERENCE** — compact block/mapping lookup.
- **FULL_CONTEXT** — complete recovery context, history, evidence and current rules.

When a rule changes after new ESP evidence, update **REFERENCE and FULL_CONTEXT together** and explicitly mark the older rule superseded.

---

# 26. Parameter-level master byte-map recovery

The companion `SYSEX_FORGE_REFERENCE.md` is now the authoritative **parameter-level byte map** for SysEx Forge. It includes the complete 153-point FM-X source→target matrix, normalized cross-generation source fields, explicit AWM2/AN-X/Arp/FX source offsets, current AWM2/FM-X/AN-X/Drum Y2L target maps, Control Assign, Sidechain, Portamento and EPFM integrity rules.

## 26.1 Source and target evidence remain separate

```text
Soundmondo/WebMIDI block + source offset
                ↓
        normalized semantic field
                ↓
Y2L blob/Part/engine/record target offset
```

A row is fully cross-mapped only when both sides have evidence. Missing source or target coordinates are left blank rather than inferred.

## 26.2 Recovery source hierarchy

The master byte map was rebuilt from:

1. `FMX_COVERAGE_MATRIX_v177.csv` — 153 FM-X source→destination parameter points.
2. `normalized_parameter_map.json` — legacy/M-generation Performance and Part source fields.
3. current `sysex_parser.py` — explicit AWM2/AN-X/Arp/FX source coordinates and codecs.
4. 2026-08-12 Control Assign/Sidechain recovery spec.
5. current Performance Editor / serializer constants — modern Y2L AWM2/FM-X/AN-X/Drum targets.
6. ESP-verified Portamento and EPFM boundary experiments.

## 26.3 Maintenance rule

For every future mapping, update code/mapping data, `SYSEX_FORGE_REFERENCE.md` (exact coordinates/encoding) and `SYSEX_FORGE_FULL_CONTEXT.md` (experiment/rationale/status) together. The Reference is the first place to look when asking **“which byte is this parameter?”**.
