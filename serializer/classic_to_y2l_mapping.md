# Classic / Short-layout Import to Y2L Mapping

This document describes the current YSFC Forge import/conversion model for non-native source libraries. It is a current-state technical reference, not a changelog.

## Scope

The Library Builder exports selected Performances and the dependencies required by those Performances. It does not try to clone a complete source library.

Currently in scope:

- selected Performance records
- DPFM performance blobs
- required user waveforms
- required sample data
- required arpeggios
- compact renumbering of copied dependencies

Currently outside the Library Builder scope:

- Live Sets
- Patterns
- Favorites
- complete device-side library metadata
- guaranteed byte-identical full-library cloning

## Source families

| Source family | Versions / extensions | Internal model | Current conversion strategy |
|---|---|---|---|
| Native long-layout Y2L/Y2U | MODX M / modern M generation | 6701-byte Performance Common, 5765-byte Part Common | Direct merge / selective dependency rewrite |
| MONTAGE M short-layout / X2L-style | MONTAGE M 4.1.x style libraries | 6689-byte Performance Common, 5621-byte Part Common | Expand to long-layout Y2L before export |
| Legacy MONTAGE | 4.0.x `.X7L` / `.X7U` | Classic DataBlock-framed DPFM | Parse classic blob and rebuild as modern Y2L DPFM |
| Legacy MODX / MODX+ | 5.0.x `.X8L` / `.X8U` | Classic DataBlock-framed DPFM | Parse classic blob and rebuild as modern Y2L DPFM |

## Native long-layout Y2L target DPFM

Modern long-layout DPFM uses:

```text
Performance Common: 6701 bytes
Part Common:        5765 bytes per part
Engine pool:        variable, one engine block per part
```

Important offsets:

```text
common[6695] = physical/template Part-slot count
common[6700] = engine byte for Part 1 / primary engine indicator
part stride  = 5765
```

Engine bytes:

```text
0x00 / AWM2 engine block: AWM2
0x01 / Drum engine block: Drum
0x02 / FM-X engine block: FM-X
0x03 / AN-X engine block: AN-X
```

Engine block sizes in the long-layout Y2L target:

| Engine | First part | Additional part including separator | Notes |
|---|---:|---:|---|
| AWM2 | 2503 | 2508 | 3-byte header + 7×313 + last element 309 |
| Drum | 4963 | 4968 | 73 key records, last record truncated |
| FM-X | 1143 | 1148 | Pre-OP + 8 operators, OP8 shorter |
| AN-X | 684 | 689 | 3-oscillator AN-X engine block |

Additional engine blocks are preceded by a 5-byte separator:

```text
00 00 00 <engine_magic> 00
```

Known magic bytes:

```text
AWM2 = 0x08
Drum = 0x49
FM-X = 0x52
AN-X = 0x6e
```

## MONTAGE M short-layout / X2L-style conversion

Some MONTAGE M / X2L-style libraries use a shorter DPFM layout that ESP can read directly but that must be expanded when the Library Builder writes a long-layout Y2L export.

Short-layout structure:

```text
Performance Common: 6689 bytes
Part Common:        5621 bytes per part
common[6683]        = classic physical Part-slot count in that layout
common[6688]        = engine byte for Part 1 / primary engine indicator
```

Conversion to long-layout:

```text
6689-byte common -> 6701-byte common
5621-byte part   -> 5765-byte part
engine region    -> moved after the expanded part-common area
```

Engine-region conversion:

| Engine | Short engine | Long engine | Conversion |
|---|---:|---:|---|
| AWM2 | 2503 | 2503 | copy as-is |
| Drum | 4963 | 4963 | copy as-is |
| FM-X | 1071 | 1143 | expand to long FM-X engine layout |
| AN-X | 639 | 684 | expand to long AN-X engine layout |

The current short-to-long conversion is DPFM-focused. Live Set and Pattern chunks may exist in the source library, but they are not preserved by the Library Builder.

## Legacy X7L/X8L classic DPFM parsing

Classic MONTAGE/MODX performance blobs are not the same as modern Y2L DPFM blobs. They are parsed as DataBlock-framed classic structures and rebuilt as modern Y2L DPFM.

Classic DPFM high-level structure:

```text
DataBlock:      Performance common
DataBlock × 4:  reverb / variation / master EQ / master effect
u32be:          part count
DataBlock × N:  part headers
DataBlock × 2:  AD part, digital input part
per part:       part type + element/operator/key data
tail:           play settings / scene and arp related data
```

Classic part type values:

```text
0 = AWM2
1 = Drum
2 = FM-X
```

AN-X is supported in the modern Y2L/Y2U target format. Original legacy MONTAGE/MODX X7L/X8L sources are not expected to contain AN-X as a normal classic part type. A type outside the known classic set should be treated as an unknown classic engine rather than assumed to be valid AN-X.

## Classic engine conversion status

| Classic engine | Current Y2L conversion status | Notes |
|---|---|---|
| AWM2 | Supported | Element parameters are mapped into the modern AWM2 engine layout |
| Drum | Supported | Converted to real Y2L Drum engine; not AWM2 fallback |
| FM-X | Supported | Classic opaque FM-X common/operator blocks are mapped into the modern FM-X engine layout |
| Unknown classic type | Not supported | Should be blocked or explicitly warned to avoid silent corrupt exports |

## Classic AWM2 mapping model

Classic AWM2 elements are read in canonical classic field order and written into the modern Y2L AWM2 element layout.

Key conversions:

- classic filter type `17` (`Thru`) maps to Y2L filter type `21`
- classic cutoff byte `0..255` maps to Y2L cutoff Hz using logarithmic frequency conversion
- classic FEG depth center `64` maps to Y2L FEG depth center `104`
- user waveform references are rewritten to the new compact Y2L dependency IDs after dependency selection

The long Y2L AWM2 engine block is:

```text
header:       00 00 2B
Elements 1-7: 313 bytes each
Element 8:    309 bytes
Total:        2503 bytes
```

## Classic Drum mapping model

Classic Drum parts are converted to real Y2L Drum engine blocks.

The Y2L Drum engine uses:

```text
73 drum key records
68 bytes per key conceptually
last key record truncated so total engine size is 4963 bytes
```

The Drum engine has its own Part Common interpretation. It does not use the same Part Common AEG offset block as AWM2/FM-X/AN-X. In Drum Part Common, the drum AEG and filter fields are stored in Drum-specific offsets.

Classic Drum waveform/sample references are handled through the same dependency-renumbering model as AWM2, but applied per Drum key/element where relevant.

## Classic FM-X mapping model

Classic FM-X stores a compact common block and eight compact operator blocks. The current conversion maps this data into the modern Y2L FM-X engine layout.

Modern Y2L FM-X engine size:

```text
1143 bytes total
210-byte pre-operator block
OP1-OP7: 123 bytes each
OP8:     72 bytes
```

Classic FM-X common/operator values are written into the low byte of modern Y2L u16 fields where the modern format uses u16 storage. Fields with no classic source are kept from the modern template/default.

## Dependency selection and renumbering

The Library Builder performs selective dependency export. It does not blindly copy all dependency records when it can reliably resolve the references used by the selected Performances.

Dependency families:

| Entry chunk | Data chunk | Meaning |
|---|---|---|
| EWFM | DWFM | Waveform metadata / waveform keybanks |
| EWIM | DWIM | Sample/wave data |
| EARP | DARP | Arpeggio metadata/data |

Waveform/sample IDs are compacted to `1..N`.

Arpeggio IDs are compacted to `0..N-1`.

After dependencies are selected and renumbered, all references in the exported DPFM blobs are rewritten to the new IDs. Orphan arpeggios are not exported when the final exported Performance blobs do not reference them.

Dependency sections are sized exactly to their payload. Empty dependency sections are omitted rather than emitted as padded zero-count chunks.

## Container model for synthetic exports

Synthetic Y2L exports use a fixed, ESP-compatible directory/library region and write only the chunks needed by the export.

Typical chunk order with dependencies:

```text
EPFM EWFM EARP ESYS EFVT EWIM DPFM DWFM DARP DSYS DFVT DWIM
```

A dependency-free performance-only file may contain only the core performance/system/favorite chunks.

The build stamp at header offset `0x3c` is also embedded in entry records and must remain internally consistent within the file.

## Licensing note

The modern Y2L/Y2U research and MONTAGE M/MODX M engine mapping in YSFC Forge are based on independent analysis and ESP/hardware comparisons.

Legacy X7L/X8L support is partly informed by, and in some areas derived from, ConvertWithMoss by Jürgen Moßgraber. ConvertWithMoss-derived code, structures, tables, formulas, parsing logic or conversion logic are distributed under LGPL-3.0 terms. See the repository `NOTICE.md` and `licenses/LGPL-3.0.txt`.


## Verified Y2L Insertion Connection Type

Controlled MODX M / ESP exports (2026-08-08) established the Part Common routing field independently of the InsA/InsB effect blocks:

- Part Common relative offset **+232** (Part 1 blob absolute offset 6933)
- `0` = `Parallel`
- `1` = `A_to_B`
- `2` = `B_to_A`

This is binary-verified from three otherwise-identical `Init Normal` Y2L files. The classic-source byte/index for this field has **not** yet been identified, so the classic→Y2L transcoder must not guess it.
