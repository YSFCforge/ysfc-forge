# Classic → Y2L parameter map used in v15.24

This is a first parameter-based bridge for the classic X7L/X8L → Y2L transcoder. It deliberately replaces the previous byte-isolation approach.

## Sources used

- `docs/YSFC_FORGE_REFERENCE.md`
- `docs/YSFC_FORGE_FULL_CONTEXT.md`
- `serializer/ysfc_serializer.py`
- `serializer/ysfc_serializer_classic.py`
- `serializer/classic_to_y2l_mapping.md`
- ESP-saved reference: `Test save arp  from ESP.Y2L`
- Library Builder output: `New_empty_Y2L_16_slots_pool_43_9KB_merge_3.Y2L`
- Classic reference: `classic_x7l_merge_3.X7L`

## Main fixes

### AWM2 element waveform bridge

Classic preset waveform ids are not always valid as modern Y2L/MODX M waveform ids. v15.24 adds a narrow bridge confirmed by the current ESP reference:

| Classic stored id | ESP/Y2L id | Rule |
|---:|---:|---|
| 2058 | 2141 | +83 |
| 2060 | 2143 | +83 |
| 2117 | 2311 | +194 |
| 2118 | 2312 | +194 |
| 2127 | 2321 | +194 |

Implemented rule:

```text
2049..2109 → +83
2110..2399 → +194
other ids  → unchanged
```

This is intentionally narrow and should be expanded only with more verified pairs.

### AWM2 element LFO layout

ESP-imported classic AWM2 elements use the non-extended LFO layout in the tested references:

```text
element[6]   = 0
element[11]  = 0
element[289] = classic element byte 135  # non-extended LFO speed
element[307] = 0                         # extended LFO speed cleared
```

### Part Common mapping

The classic part header is now preserved in the JS parser:

```text
name[21]
type/main_category/sub_category
part_switch/keyboard_switch
velocity/note/pitch-bend fields
manyParameters[274/275]
scenes[176 in verified 4.0.5/5.0.1]
assignable knob names
control boxes
```

Mapped Y2L Part Common fields:

| Y2L rel | Field | Classic source |
|---:|---|---|
| 31 | keyboard control | part header keyboard_switch |
| 36 | part switch | part header part_switch |
| 114 | main category | part header main_category |
| 116 | sub category | part header sub_category |
| 130 | volume | manyParameters[2] |
| 136 | variation send | manyParameters[6] |
| 212 | pitch bend upper | part header pbUpper |
| 214 | pitch bend lower | part header pbLower |
| 220 | portamento time | manyParameters[10] |
| 222 | portamento mode | manyParameters[11] |
| 238 | part EQ low frequency | manyParameters[53] |
| 282..314 | Insertion A type/subtype/params | manyParameters[139..177] sparse mapping |
| 338..370 | Insertion B type/subtype/params | manyParameters[197..235] sparse mapping |
| 500/502/514/516/520/524 | AWM2 LFO modulation-control matrix subset | manyParameters[66/67/74/76/78/80] |

### Arpeggio scene slot holes

When a classic scene contains a stale arp id, v15.24 preserves the scene slot position as `00 00` instead of collapsing later arp ids leftward. This matches ESP behavior for mixed/stale classic scene tables.

## Verification status

`node --check` passes for the generated v15.24 JavaScript.

The direct patched test file `New_empty_Y2L_merge_3_v15_24_param_map_test.Y2L` shows the expected waveform id/bank fixes versus the ESP reference for all three test performances. Sound must still be verified in ESP/hardware.
