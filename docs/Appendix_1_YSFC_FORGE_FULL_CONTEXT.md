# YSFC Forge — Full Context

*MODX M8 firmware 3.0 + ESP Plugin v3.0*
*Foundation: 2010+ binary-verified test files*

---

## Current status

| Engine | Mapped fields | Status |
|---|---:|---:|
| **AWM2** (per element × 8..128) | 128 fields + 8 [INTERN] | ✅ **Verified** |
| **AN-X** (engine total) | 171 fields + 458 [INTERN] | ✅ **Verified** |
| **FM-X** (Pre-OP + 8 × OP) | 141 fields + 863 [INTERN] | ✅ **Verified** |
| **Drum** (per key × 73) | 27 key fields + 27 Part Common | ✅ **Verified** |
| **Part Common** | 88 fields (AWM2/FM-X/AN-X) + 6 (Drum) | ✅ **Core verified** |

**Total field positions in serializer:** ~2057
**Test corpus:** 2010+ binary-verified files

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


All four engines are binary-verified across all known user-editable parameters. Multi/GM 16-part files are supported (15 AWM2 + 1 Drum on Part 10, using the multi-part architecture).

**Structural insight: Drum engine has its own Part Common layout**

Drum does not share the universal AEG offset block (rel +144..+150) used by AWM2/FM-X/AN-X. For Drum the following applies instead:
- Rel +126..+132 = drum AEG (Attack/Decay/Sustain/Release, c64)
- Rel +144/+146 = drum filter cutoff/resonance (c64)

The interpretation of Part Common rel +126..+158 is governed by engine_type. The shared AEG block architecture therefore applies to only three of the four engines.

**On AN-X coverage:** The AN-X engine is fundamentally different from AWM2. AWM2 is a sample player where 8 identical elements share structure — each byte tends to be a direct UI parameter. AN-X is an analog model with complex modulation routing: of the engine pool's 684 bytes, 458 are firmware constants ([INTERN]) including routing matrices and stray flags. The 171 UI fields cover all user-editable parameters.

---

## Performance ↔ Waveform / Sample / Arpeggio linkage

Selective export copies only the dependencies that a chosen set of performances actually uses. A valid Y2L requires catalog IDs to be a **contiguous sequence**, so the export both copies the referenced dependencies and renumbers them, rewriting the in-blob references to match.

**Reference model.** A performance references a USER waveform via a fixed byte structure inside its DPFM blob. Two encodings exist (both byte-verified against ESP ground truth and controlled CFX single-edit pairs):

- `SIG_A`: `00 00 00 28  01(bank)  XX  YY  00  [ID]  00 01 00 01` — element slot
- `SIG_B`: `01 00 00 00  01 00 0C 00  [ID]  00 40` — element config

The byte after `0x28` is the **bank**: `0x01` = USER waveform (the `[ID]` byte indexes the EWFM/EWIM catalog), `0x00` = preset/ROM (ignored). `XX YY` vary (`00 00` or `00 01`); both are matched. `[ID]` is a single byte. The catalog ID lives at `recPayload[10:12]` (big-endian u16) of each EWFM/EWIM `Entr` record.

**Renumbering rule.** Collect the distinct referenced old IDs, sort them, assign new IDs `1..N` (1-based for waveform/sample). Rewrite every `[ID]` byte in each kept performance blob old→new, and write the new IDs into the rebuilt EWFM/EWIM `recPayload[10:12]`. Pure renumbering touches **only** the `[ID]` byte — the bank/Field-2 bytes are untouched.

**Arpeggios.** Arp references live in separate (`80 00 …`) element-pitch blocks using a distinct 0-based ID space. Arp refs sit after a run of `80 00` pairs (pitch table) and optional `00` padding, as one or more `[ARP_ID] 2f` pairs (the ref may repeat up to 4×); `ARP_ID` is a single byte < 21. The renumber rule is identical to waveforms but **0-based**: sort the distinct referenced arp IDs, assign `0..N-1`. EARP/DARP are rebuilt selectively with the new IDs; every kept performance blob has its arp `[ID]` bytes repointed old→new.

**Dependency-section sizing.** Y2L dependency sections are sized **exactly** to payload; MODX rejects any size-field/data slack. Each dep section (EWFM, DWFM, EWIM, DWIM, EARP, DARP), the DPFM performance pool, and the EPFM performance index are all sized to the byte using uniform 8-byte-per-blob framing accumulated then `exactSize(n) = Σ(8 + payload) − 4 + 8` (subtract the one 4-byte first-blob/record over-count, add the section header). A minimal Init/one-record floor is kept for empty selections.

**Container structure.** A valid library file uses ESP's exact 12-chunk layout (`EPFM EWFM EARP ESYS EFVT EWIM DPFM DWFM DARP DSYS DFVT DWIM`, no ECRV/ELST/DCRV/DLST stubs). `u32@0x20` = chunk-count × 8.

**Per-file build stamp.** `u32@0x3c` is a per-file build stamp that is also embedded as a u16 before every EPFM/EWFM/EARP name. It must be the same family within a file; the synthetic header `0x3c` is set to the source file's `0x3c`. EPFM record byte[11] = destination slot index (compact `0,1,2,3` for a 4-perf export).

**DWFM sample-index.** Each DWFM blob is `[4-byte header][N × 64-byte sub-entries]`; at blob offset `60 + 64·k` there is a 4-byte little-endian sample-data index. It must be a pure ascending counter `value[i] = base + i`, where `base` is the first blob sub-entry's original 4-byte LE value and `i` increments once per sub-entry across all blobs in order (full 32-bit LE).

**Fixed directory region.** A valid YSFC library file has a fixed-size directory region: entries from `dirOff` (0x40), FF-padding, a single `0x00` separator at `dirOff+0x150` (= 0x190), and the first chunk at `dirOff+0x151` (= 0x191). MODX computes every chunk's position from this fixed region.

**Per-performance dependency tags (UI).** Each performance row's W/S/Arp chips are gated on whether that specific performance actually references the dependency, using the same binary-verified scanners that drive the selective export (`scanWaveformRefPositions` / `scanArpRefPositions`). EWFM/EWIM share an id-space, so waveform refs gate both W and S; arp refs gate Arp. If a blob can't be read, the code falls back to file-level behaviour. The per-performance info column shows the engine label only (`AWM2`/`FM-X`/`AN-X`).

**Helpers:** `scanWaveformRefPositions`, `scanArpRefPositions`, `renumberPerfBlob`, `setRecPayloadId`, `resolveFileWaveformRefs`, `resolveFileArpRefs`, `getDepsForSelection`, `buildSyntheticY2LBuffer`, `buildDepPayload`, `cloneAndPatchOffLen`, `buildDPFMPayload`, `buildEPFMPayload`, `calcSyntheticDimensions`, `exportMergeToY2L`, `createSyntheticBaseFile`. A conservative copy-all fallback is preserved for any untrusted resolution (parse anomaly, blob < 12000 B, zero refs while a pool exists, or a referenced ID missing from a section catalog). If the chosen base file is also a source of any selected performance, a synthetic container is forced (`baseIsSource`).

---


## Foreword — How to read this document

This is a clean, deduplicated master reference for the YSFC format. Each field is listed once with its correct position, default, encoding and star rating.

**Sources of truth in priority order:**

1. **Binary-verified with test file ★★★★★** — diff-proven. This is authoritative.
2. **Derived from official Yamaha source data (★★★★☆)** — Effect Type List, MIDI table, etc.
3. **Predicted from established pattern (★★★☆☆)** — stride extrapolation, deduction.
4. **[STRUKT]** — structurally characterized but not UI-mapped.
5. **[INTERN]** — MODX-internal, not user-editable (ignored during editing).

**Abbreviations:**

```
u8       = unsigned 8-bit byte
u16le    = unsigned 16-bit little-endian (lo + hi*256)
u32be    = unsigned 32-bit big-endian
c64      = center=64       (raw = UI + 64)
c128     = center=128      (raw = UI + 128)
c256     = center=256      (u16le, raw = UI + 256)
c50      = center=50       (raw = UI + 50)
c504     = center=504      (u16le, AN-X pitch cents)
direct   = raw = UI value directly
bool     = 0=Off, 1=On
enum     = enumerated value
```

**Coordinate system:**

All absolute offsets are `blob[+N]` relative to the **performance blob's start** (where `blob[0..3] = 00 00 00 15`). This is the same as `dp[N+12]` if counted from DPFM payload start.

---

## Table of Contents

1. Y2L file format architecture
2. Container — EPFM / DPFM / ESYS / EFVT / ELST
3. Sub-blob universal model
4. Engine pool (multi-part)
5. Performance Common (Sub-blob 1)
6. Part Common (Sub-blob 2..N)
7. Receive Switch per part
8. Common Assigns (CA structures)
9. Scene Structures
10. MS Sequencer
11. Engine data: AN-X
12. Engine data: AWM2
13. Engine data: FM-X
14. Engine data: Drum
15. Insertion FX
16. Smart Morph
17. UI elements NOT IN BLOB
18. Remaining unmapped regions
19. Modified/Noise flags (filter during diff)
20. Helper functions (serializer)
21. Verification status and test file registry

---

# 1. Y2L file format architecture ★★★★★

The Y2L/Y2U file format consists of a 64-byte file header followed by an alternating sequence of "Entry" (E*) and "Data" (D*) chunks. Each E-chunk indexes entries; each D-chunk holds the corresponding data.

```
File header                 (64 bytes)
EPFM  Performance index     — entries pointing into DPFM
DPFM  Performance data      — main payload
ESYS  System index
DSYS  System data
EFVT  Favorite index
DFVT  Favorite data
ELST  Live Set index        (optional)
DLST  Live Set data         (optional)
```

`.Y2L` (Library file) and `.Y2U` (User file) are byte-for-byte identical — only the file extension differs (the ESP plugin uses the extension to decide which import dialog to present).

## 1.1 File header (64 bytes) ★★★★★

Binary-verified against 1930+ files (Appendix A.3). Earlier versions of this table had wrong field sizes and offsets — the corrected layout is below.

| Offset | Hex | Size | Field | Notes |
|---:|---:|---:|---|---|
| 0 | 0x00 | 16 | Magic + null-pad | `YAMAHA-YSFC\x00\x00\x00\x00\x00` (11 bytes ASCII + 5 null bytes) |
| 16 | 0x10 | 16 | Version + null-pad | `5.1.2\x00…` for Montage M / MODX M; `5.0.1` for MODX classic; `4.0.5` for Montage classic |
| 32 | 0x20 | 4 | Catalogue size | `u32 BE` = block_count × 8; catalogue always starts at 0x40 |
| 36 | 0x24 | 12 | Reserved padding | all `0xFF` |
| 48 | 0x30 | 4 | Library-info length | `u32 BE`; baseline 241 bytes (Montage M / MODX M), 81 bytes (classic) |
| 52 | 0x34 | 8 | Reserved padding | all `0xFF` |
| 60 | 0x3C | 4 | Save counter | `u32 BE`; monotonically increasing per export — **not** a Unix timestamp |

The save counter at 0x3C is part of the noise set (filtered during diff analysis). It is also embedded as a `u16` before every EPFM/EWFM/EARP record name; both must agree or MODX rejects the file. The catalogue always begins at absolute offset `0x40` regardless of the catalogue-size field.

## 1.2 EPFM chunk ★★★★★

EPFM (Entry Performance) is the performance index. It contains a fixed header followed by one Entry record per performance in the file.

```
EPFM chunk header   (8 bytes: 'EPFM' + size u32 BE)
count               (4 bytes u32 BE: number of Entry records)
'Entr'              (4 bytes: global type tag; also serves as the first record's tag)
rec1_size           (4 bytes u32 BE)
rec1_data           (rec1_size bytes)
'Entr' rec2_size rec2_data     ← subsequent records each preceded by their own 'Entr' tag
…
```

Note: the first record has **no** preceding `Entr` tag of its own — the global tag at bytes [4:8] serves that role. Records 2..N each have their own `Entr` tag.

Each Entry record payload (binary-verified against MODX M files):

| Rel | Size | Field | Notes |
|---:|---:|---|---|
| 0 | 4 | Blob size | `u32 BE` — size of this performance's DPFM blob |
| 4 | 4 | DPFM offset | `u32 BE` — offset of blob within DPFM payload |
| 8 | 1 | Constant | `0x00` |
| 9 | 1 | Constant | `0x40` (MODX validates this field) |
| 10 | 1 | Constant | `0x00` |
| 11 | 1 | Dest slot index | compact destination slot (0, 1, 2, … for sequential export) |
| 12 | 1 | Constant | `0x00` |
| 13 | 1 | Multi-engine flag | `0x00` (simplified) |
| 14 | 1 | Constant | `0x00` |
| 15 | 1 | Engine bits | `0x01`=AWM2, `0x02`=FM-X, `0x04`=AN-X; OR-combined for multi-engine parts |
| 16 | 1 | Source flag | `0x00`=ESP Plugin export, `0x02`=MODX hardware export |
| 17 | 1 | Constant | `0x00` |
| 18 | 1 | Category | `0x01`=default |
| 19 | 6 | Padding | all `0x00` |
| 25 | 1 | Constant | `0x30` |
| 26 | 1 | Slot flag | `0x00` (simplified) |
| 27 | var | Name string | `"IDX:ShortName:LongName\0"` — NUL-terminated ASCII |

The name string format is `"{slot_index}:{short_name}:{display_name}\0"`. The **display name** (third field) is what MODX and ESP Plugin show as the performance name — it matches `blob[4:]` exactly. The **short name** (second/middle field) is a truncated category label used internally and is NOT the display name. Example: `"0:Italian XL:Italian Grand XL\0"` — short name `"Italian XL"`, display name `"Italian Grand XL"`.

Note: earlier versions of this documentation had the field order reversed (described as `"IDX:LongName_padded:ShortName\0"`). That description was incorrect.

For a single-performance file the EPFM contains exactly one Entry record. For library files with multiple performances there is one Entry per performance.

## 1.2a v4.x file format differences (Montage classic / MODX classic) ★★★★☆

Files with version string `4.0.5` (Montage classic) or `5.0.1` (MODX classic) differ from the v5.x layout in two important ways:

**EPFM directory structure:** In v4.x files the EPFM chunk at `d[64]` is the directory structure itself — its payload contains chunk pointers (EARP, ESYS, EFVT, DPFM, …), not Entr records. The actual EPFM chunk containing Entr records is embedded further into the file (typically around offset `0x171`) and is not listed in the directory. To find it, scan forward from offset ~200 for the next `'EPFM'` tag with a valid `count + 'Entr'` payload.

**Engine-type byte offset:** In v4.x blobs the engine-type byte sits at `blob[6698]`, not `blob[6700]` as in v5.x. The sub-blob separator `0x00000015` follows immediately at `blob[6699:6703]`.

**Recommendation:** Always use EPFM `rec[15]` (engine bits: `0x01`=AWM2/Drum, `0x02`=FM-X, `0x04`=AN-X) as the primary engine source when reading files of unknown version — it is correct in both v4.x and v5.x. Use `blob[6700]` only as a fallback for confirmed v5.x files.

## 1.3 DPFM chunk ★★★★★

DPFM (Data Performance) contains the actual performance data. The chunk header is followed by a sequence of sub-blobs (one per performance).

```
DPFM header                       (8 bytes: 'DPFM' + size big-endian u32)
Sub-blob 1                        (Performance 1)
Sub-blob 2                        (Performance 2)
...
```

Each sub-blob is itself a self-contained performance — see Section 2 for the sub-blob structure.

For Multi/GM 16-part files, the DPFM contains a single very large sub-blob (~141,536 bytes) representing the 16-part Performance.

## 1.4 ESYS / DSYS (System Settings) ★★★★★

ESYS/DSYS hold system-level settings (master tune, MIDI channels, MIDI routing, etc.). These are typically constant across most files and are not edited via the per-Performance UI.

For most file types, ESYS is 46 bytes and DSYS is 1094 bytes.

## 1.5 EFVT / DFVT (Favorites) ★★★★★

EFVT/DFVT hold the Favorites bitmap (which performances are marked as favorites). EFVT is typically 163 bytes; DFVT is 22219 bytes.

The favorites bitmap is updated when the user toggles a performance as favorite. This is a noise region for performance-editing diffs.

## 1.6 ELST / DLST (Live Set) ★★★★★

ELST/DLST hold Live Set definitions (which performance is assigned to which slot in a Live Set bank). These chunks are absent in single-performance files and present in full library files.

## 1.7 File integrity — NO checksums ★★★★★

The YSFC format has **no checksums or integrity verification**. Any byte can be changed without invalidating the file (as long as the resulting structure is still parseable).

This has several consequences for editor design:

### Bytes that ALWAYS differ between two exports

When the user saves a performance twice without changes, the following bytes will still differ:

```
Date stamp:           offset 24      (4 bytes)
Save counter regions: 6715..6725     (~11 bytes)
Misc internal:        7167-7168, 7419
```

These bytes are part of the noise set and are filtered out during binary diff analysis.

### Consequences for editor

Since there is no checksum:
- Edits do not require any post-edit fixup
- A modified file is immediately valid as long as the structure is preserved
- Length changes (e.g., changing Element Count) require careful update of length-dependent fields

### Risk: no integrity check

The absence of checksums means a corrupted file cannot be detected by the format itself — only by attempting to load it. Editor implementations should:
- Always keep a backup of the original file
- Verify the round-trip (read → write → read) before destroying the original
- Validate the output by parsing it again before considering the save successful

---

# 2. Sub-blob universal model ★★★★★

A sub-blob is a self-contained Performance representation. Whether the file contains one performance or 256, each Performance is encoded as one sub-blob inside DPFM.

## 2.1 Layout

```
Sub-blob 1: Performance Common         (6701 bytes — shared metadata)
Sub-blob 2: Part 1 Common              (5765 bytes)
Sub-blob 3: Part 2 Common              (5765 bytes)
...
Sub-blob N+1: Part N Common            (5765 bytes)
Engine pool                            (variable size, depends on engine mix)
```

In a single-Part Performance, there is one Part Common (Sub-blob 2) plus a single engine block. In a multi-Part performance, each active Part has its own Part Common followed by its own engine data in the engine pool.

The sub-blob count and Part count are encoded in the Entr bitmask (see Section 3.7).

## 2.2 Sub-blob header (27 bytes) ★★★★★

Each sub-blob begins with a 27-byte header:

```
Bytes 0..3:    Sub-blob type marker
Bytes 4..7:    Sub-blob size (big-endian u32)
Bytes 8..N:    Variable header (name string, etc.)
```

The variable header includes the performance/part name and a few metadata fields. The exact layout depends on whether this is the Common sub-blob or a Part sub-blob.

## 2.3 Engine-type detection ★★★★★

The engine type for each Part is encoded at `blob[+6700]` (relative to performance blob start):

```
0 = AWM2
1 = Drum
2 = FM-X
3 = AN-X
```

For multi-part files, the engine type of subsequent parts is derived via the sub-blob pointer model (see Section 3.6).

## 2.4 Per-part address formula ★★★★★

For Part N (1-indexed) within a multi-part Performance:

```
Performance Common base = blob[0]              (6701 bytes)
Part N Common base = blob[6701 + (N-1) * 5765] (5765 bytes per part)
```

So:
- Part 1 Common: bytes 6701..12465
- Part 2 Common: bytes 12466..18230
- Part 3 Common: bytes 18231..23995
- ...

For a single-Part Performance, only Part 1 is present. The engine pool begins immediately after the Part Common(s).

## 2.5 Verification ★★★★★

The 5765-byte Part Common stride is verified by:
- 16 × stride 5765 in Multi/GM 16-part files (verified)
- Multiple multi-part Y2U files showing identical Part Common structure replicated at stride 5765
- The sub-blob pointer at rel +5763/+5764 (Section 3.6) always lies at this offset within each Part Common

## 2.6 Edit-flag bytes per sub-blob

Each sub-blob has internal edit-flag bytes that increment on edit. These are part of the noise set and are filtered during diff analysis:

- `blob[+6715]`: Performance edit counter (increments on every Performance save)
- `blob[+6716]`: Subtype counter
- `blob[+6721]`: Edit-related byte

These bytes change on every save regardless of which parameter was edited.

---

# 3. Engine pool (multi-part) ★★★★★

In multi-part files, engine data is stored in a shared pool after all sub-blobs.

## 3.1 Pool layout

```
[Engine 1 data][5b separator][Engine 2 data][5b separator]...[Engine M data]
                                                              ↑
                                                              no separator after last
```

**Constant:** `ENGINE_POOL_SEP_SIZE = 5`

## 3.2 Engine sizes ★★★★★

| Engine | Data size | Pool stride (with sep) |
|---|---|---|
| **AN-X** | 684 bytes | 689 |
| **AWM2** | 2503 bytes | 2508 |
| **FM-X** | 1143 bytes | 1148 |
| **Drum** | 4963 bytes | 4968 |

## 3.3 Pool start address

```python
ENGINE_POOL_BASE = 6701 + N_parts * 5765
```

Where `N_parts` is the count of active Parts. For a single-Part Performance, the pool starts immediately after Part 1's Common block:

```
pool_start = 6701 + 1 * 5765 = 12466
```

For a 16-part Multi/GM file:

```
pool_start = 6701 + 16 * 5765 = 99,141
```

## 3.4 Engine start signatures ★★★★★

Each engine block begins with a 5-byte header signature:

```
AWM2:  [01, 00, 00, 00, 28]          — final byte 0x28 = 40 dec, marker
AN-X:  [01, 00, 00, 00, 6E]          — final byte 0x6E = 110 dec
FM-X:  [01, 00, 00, 00, 52]          — final byte 0x52 = 82 dec
Drum:  [01, 00, 00, 00, 49]          — final byte 0x49 = 73 dec
```

The last byte of this 5-byte header is the engine-type magic byte. It can be used to identify the engine of a block when scanning the pool.

## 3.5 Engine pool addressing

For Part N with engine type E:

```python
# Engine block for Part N starts at:
engine_start_N = ENGINE_POOL_BASE + sum(
    ENGINE_STRIDE[engine_of_part_k]
    for k in range(1, N)
)

# (No separator after the last engine in the pool, but the calculation still uses
#  full strides for intermediate parts.)
```

## 3.6 Multi-part "linked list" pointer model ★★★★★

Each Part Common contains a 2-byte pointer that determines whether this is the last Part and what engine the next Part uses:

```
SUBBLOB_POINTER_REL = (5763, 5764)
```

For Part N's Part Common (located at `blob[6701 + (N-1) * 5765]`), the pointer bytes are at:

```
pos_marker = 6701 + (N-1) * 5765 + 5763
pos_next   = 6701 + (N-1) * 5765 + 5764
```

**Decoding:**

```python
marker = blob[pos_marker]
next_val = blob[pos_next]

if marker == 1:
    # Not the last Part; next_val identifies Part N+1's engine type
    # next_val: 0=AWM2, 1=Drum, 2=FM-X, 3=AN-X
    is_last = False
    next_engine = ENGINE_TYPE_VALUES[next_val]
else:
    # This IS the last Part; marker IS the engine-type magic byte for Part 1
    # marker: 8=AWM2, 110=AN-X, 82=FM-X, 73=Drum
    is_last = True
    part1_engine = ENGINE_MAGIC_TO_NAME[marker]
```

This means:
- Each Part's pointer tells you the engine type of the NEXT Part (if any)
- The LAST Part's pointer wraps around and tells you the engine type of Part 1
- This forms a circular linked list of engine types

## 3.7 Entr bitmask for active parts ★★★★★

The number of active Parts is encoded in an Entr-record bitmask within EPFM. This bitmask has one bit per Part (1 = active).

For a 16-Part Multi/GM file, all 16 bits are set. For a single-Part Performance, only bit 0 is set.

## 3.8 Helper API for multi-part pointer

```python
SUBBLOB_POINTER_REL = (5763, 5764)
ENGINE_MAGIC_BYTES  = {'ANX': 110, 'AWM2': 8, 'FMX': 82, 'Drum': 73}

def get_subblob_pointer_pos(part_idx):
    """Position of Part N's pointer (1-indexed)."""
    sub_blob_start = 6701 + (part_idx - 1) * 5765
    return (sub_blob_start + 5763, sub_blob_start + 5764)

def read_subblob_pointer(blob, part_idx):
    """Returns (is_last, next_or_part1_engine)."""
    pos0, pos1 = get_subblob_pointer_pos(part_idx)
    marker, next_val = blob[pos0], blob[pos1]
    if marker == 1:
        return False, ENGINE_TYPE_VALUES[next_val]
    return True, ENGINE_MAGIC_TO_NAME[marker]
```

## 3.9 Multi/GM 16-part files ★★★★★

**Multi/GM file type** is the YSFC 16-part multitimbral configuration. It is used as a GM-compatible tone generator (Multi/GM Performance with drums assigned to Part 10 per the GM standard).

**The file structure follows the documented multi-part model exactly:**

| Component | Size | Content |
|---|---:|---|
| Performance Common (sub-blob 1) | 6701 bytes | Standard Performance Common |
| 16 × Part Common (sub-blobs 2-17) | 5765 bytes each = 92240 bytes | Stride 5765 between parts |
| Engine pool | ~42583 bytes | 15 × AWM2 (stride 2508) + 1 × Drum (4963) for Part 10 |
| **DPFM total** | **141536 bytes** | Verified |

**Empirically verified:**

- 16 occurrences of "Concert GrandPiano" (AWM2 default waveform name) with stride 5765 between Part Common instances
- Stride jumps to 11530 (2 × 5765) between Part 9 → Part 11 because Part 10 is Drum (has a different default waveform)
- 73 drum keys at fo 122261 (Part 10 engine data starting position) with stride 68
- 72 of 73 drum keys have SW=1 in Multi/GM Init

**File size vs single-Part files:**

| File type | DPFM | Total file size |
|---|---:|---:|
| AWM2 single-part | 14981 | 38985 |
| AN-X single-part | 13162 | 37166 |
| FM-X single-part | 13682 | 37625 |
| Drum single-part | 17441 | 41427 |
| **Multi/GM 16-part** | **141536** | **165530** |

**Engine types per part in Multi/GM Init:**

- Parts 1-9: AWM2 (Concert GrandPiano)
- Part 10: Drum (Standard Drum Kit)
- Parts 11-16: AWM2 (Concert GrandPiano)

**Addressing convention:**

Multi/GM uses **exactly the same addressing model** as other multi-part files:
- Performance Common: `blob[0:6701]` (same fields as single-Part)
- Part N Common: `blob[6701 + (N-1)*5765 : 6701 + N*5765]` for N=1..16
- Engine pool: starts after the last Part Common
  - Part N engine base = engine_pool_start + sum(engine_stride for parts 1..N-1)

The addressing is **already supported** by existing serializer code via:
- `SUBBLOB_POINTER_REL = (5763, 5764)`
- `get_subblob_pointer_pos(part_idx)`
- `ENGINE_MAGIC_BYTES`

**Implication for editor:** Multi/GM requires **no new structures** or fields in the serializer. All documented and binary-verified Part Common, Engine Pool and Drum Key fields work identically on Multi/GM files — just with 16 parts instead of 1.

---

# 4. Performance Common (Sub-blob 1) ★★★★★

Region: `blob[0:6701]` (6701 bytes). Verified with ~25 binary-tested UI fields, multiple u16le pairs, and ~3000 bytes of constant padding.

## 4.1 Header (sub-blob 1 header, same as blob header)

| abs | Size | Field | Encoding | Status |
|---|---|---|---|---|
| 0..3 | 4 b | Sub-blob length prefix `00 00 00 15` | constant | ★★★★★ |
| 4..21 | 18 b | **Performance Name** | ASCII, space-padded | ★★★★★ |
| 22 | 1 b | Null terminator | 0x00 | ★★★★★ |
| 23..24 | 2 b | Timestamp/save counter — NOISE | ignored | ★★★★★ |
| 25..26 | 2 b | 0x00 0x00 | constant | ★★★★★ |

## 4.2 Performance Toggles + Single Fields

| abs | Field | Encoding | Default | Status |
|---|---|---|---|---|
| 29 | portamentoMasterSwitch | bool | 0=OFF | ★★★★★ |
| 30 | ribbonAssign1Mode | bool | 1=Latch (0=Moment) | ★★★★★ |
| 31 | ribbonAssign2Mode | bool | 1=Latch | ★★★★★ |
| 33 | ribbonMode (Hold/Reset) | bool | 1 | ★★★★★ |
| 34 | reverbOnOff | bool | 1=ON | ★★★★★ |
| 35 | variationOnOff | bool | 1=ON | ★★★★★ |
| 37 | masterFxOnOff | bool | 0=OFF | ★★★★★ |
| 38 | arpMasterOn | bool | 0 | ★★★★☆ |
| 39 | msMasterOn | bool | 0=OFF | ★★★★★ |
| 50 | commonAudioSwitch | bool | 1=ON | ★★★★★ |
| 56 | **smartMorphEnable** | bool | 0 (1 if SM active) | ★★★★★ |
| 57 | sliderDirection | bool | 0=Normal (1=Reverse) | ★★★★★ |
| 66 | modifiedFlag — NOISE | edit-state | varies | ★★★★★ |
| 68 | **Performance Volume = EF Master Output** | direct, 0..127 | 127 | ★★★★★ |
| 70 | **Performance Pan** | c64, -63..+63 | 64 (Center) | ★★★★★ |
| 92 | **Performance Tempo** | direct BPM (u8) | 120 | ★★★★★ |
| 94 | **Performance Portamento Time** | direct (possibly c64) | 64 | ★★★★★ |
| 104 | lastActiveScene | u8 (0=Scene1, 7=Scene8) | 0 | ★★★★★ |
| 216 | ribbonGridMode | enum (0=Cont, 1=5step) | 0 | ★★★★★ |

**UI aliasing:** Some bytes have two UI labels. `blob[+68]` is called "Performance Volume" in the Performance Edit view but "EF Master Output" in the Envelope Follower view — **the same physical byte**.

⚠️ **`blob[+80]` and `blob[+82]`** have constant value `0x40` in all tested files and are not changed by any known UI parameter. Copy verbatim.

⚠️ **`blob[+654]`** changes in 9+ unrelated tests (EF Part change, many InsertionAssign edits) — it is a **side-effect flag**, not a parameter. Filtered during diff.

## 4.2.1 Structural metadata bytes ★★★★★

Fundamental bytes that control blob architecture. Must be set correctly when writing.

| abs | Field | Encoding | Evidence |
|---|---|---|---|
| 6695 | **Max active Part index** | u8, 1..16 (HIGHEST number, NOT count) | 4 multi-part files, 100% correlation |
| 6700 | **Engine Type (Part 1)** | u8 enum: 0=AWM2, 1=Drum, 2=FMX, 3=ANX | 30+ engine-specific files, 100% correlation |
| 12464..12465 | **Part 2 engine prefix** | u8 × 2, engine-specific in multi-part | Engine-discriminating in sub-blob 2 |

**Examples of Max Active Part:**

- Part 1 only → `blob[+6695] = 1`
- Parts 1+2 → `blob[+6695] = 2`
- Parts 3+5 (non-consecutive) → `blob[+6695] = 5` (= highest, not count of 2)

**Consequence for editor:**

```python
def set_part_metadata(blob, active_part_indices, engine_part1):
    """active_part_indices: list of 1-based part numbers
       engine_part1: 'AWM2', 'Drum', 'FMX', or 'ANX'"""
    blob[6695] = max(active_part_indices)
    blob[6700] = {'AWM2': 0, 'Drum': 1, 'FMX': 2, 'ANX': 3}[engine_part1]
```

## 4.3 Hardware Ribbon Control

Summary of Ribbon-related fields (all ★★★★★):

| abs | Field | Encoding | Default |
|---|---|---|---|
| 30 | ribbonAssign1Mode | bool | 1=Latch |
| 31 | ribbonAssign2Mode | bool | 1=Latch |
| 33 | ribbonMode (Hold/Reset) | bool | 1=Reset (0=Hold) |
| 57 | sliderDirReverse | bool | 0=Normal |
| 216 | ribbonGridMode | enum | 0=Continuous |

## 4.4 SuperKnob Link Per Scene ★★★★★

8 bytes at `blob[40:48]` (one byte per scene), plus a mirror in Scene Struct 1.

| abs | Field | Encoding | Default |
|---|---|---|---|
| 40..47 | skLinkScene1..8 | u8 bool | 1=ON |
| 1717..1724 | (mirror within Scene Struct 1) | u8 bool | 1 |

The mirror is replicated data — updated in parallel.

```python
def get_sk_link_addr(scene, mirror=False):
    """scene = 1..8"""
    base = 1717 if mirror else 40
    return base + (scene - 1)
```

## 4.5 Common FX Routing ★★★★★

| abs | Field | Encoding | Default |
|---|---|---|---|
| 112 | revReturn | direct | 64 |
| 114 | revPan | c64 | 64 (Center) |
| 118 | varReturn | direct | 96 |
| 120 | varPan | c64 | 64 |
| 122 | varToRevSend | direct | 0 |
| 124 | revSend | direct | 0 |
| 128 | sideChainMaster | enum 127=OFF, 17=Master | 127 |
| 130 | varSend | direct | 0 |

## 4.6 Common CC Numbers ★★★★★

Region `blob[152:184]`, all u8 direct (raw = MIDI CC#), stride 2 per field.

| abs | Field | Default | Status |
|---|---|---|---|
| 152 | ribbonCC | 16 | ★★★★★ |
| 154 | breathCC | 2 | ★★★★★ |
| 156 | footCtrl1CC | 11 | ★★★★★ |
| 158 | footCtrl2CC | 96 | ★★★★★ |
| 160 | assignSw1CC | 86 | ★★★★★ |
| 162 | assignSw2CC | 87 | ★★★★★ |
| 164 | fsAssignDest | enum | ★★★☆☆ |
| 166 | msTriggerCC | 89 | ★★★★★ |
| 168..182 | assignKnob1..8 CC | 17..24 (stride 2) | ★★★★★ |

**Hard-coded in firmware (NOT IN BLOB):**
- Scene CC (= 92)
- Super Knob CC (= 95)
- Footswitch Assign (= Arp Sw)

## 4.7 Per-Scene SuperKnob Value ★★★★★

8 × u16le at `blob[184:200]` (one u16le per scene).

| abs | Field | Encoding | Default |
|---|---|---|---|
| 184..185 | sceneSuperKnob_1 | u16le | 512 (mid) |
| 186..187 | sceneSuperKnob_2 | u16le | 512 |
| 188..189 | sceneSuperKnob_3 | u16le | 512 |
| ... | ... | ... | ... |
| 198..199 | sceneSuperKnob_8 | u16le | 512 |

```python
def get_scene_superknob_addr(scene):
    """scene = 1..8"""
    return 184 + (scene - 1) * 2
```

## 4.8 Reverb FX ★★★★★

Region `blob[376:428]` (52 bytes). 26 fields.

| abs | Field | Encoding |
|---|---|---|
| 34 | reverbOnOff (in toggle area) | bool, default 1 |
| 376 | reverbCategory | u8 enum |
| 377 | version byte | constant 1 |
| 380..381 | reverbType | u16le, default 32 |
| 382..383 | reverbPreset | u16le, default 10 |
| 384..426 | 22 × u16le params (Type-specific) | stride 2 |

For Shimmer Reverb type, the 22 parameters are: Shimmer Gain, Shimmer Fdbk, Shimmer HPF, Shimmer LPF, P1/P2 Balance, P1&P2 Panning, Pitch 1, Fine 1, Pitch 2, Fine 2, Cross-Feedback, Color, Reverb Time, Initial Delay, Diffusion, Size, P1&P2 Dly Ofs, Mod Depth, Mod Speed, AM Depth, AM Freq, AM Waveform. Other Reverb Types use the same slots with different interpretations.

## 4.9 Variation FX ★★★★★

Region `blob[432:484]` (52 bytes). 28 fields.

| abs | Field | Encoding |
|---|---|---|
| 35 | variationOnOff (in toggle area) | bool, default 1 |
| 432 | variationType | u8 enum |
| 436..482 | 24 × u16le params | stride 2 |

For M/S EQ Compressor type, the parameters match the Master FX layout (24-param template).

## 4.10 Master EQ ★★★★★ / ★★★★☆

Region `blob[560:593]`. Per-band stride is non-uniform (Low uses 8 bytes due to shelf type; others 6 bytes).

| abs | Field | Encoding | Default | Status |
|---|---|---|---|---|
| 560 | meqLowGain | c64 (±24 dB) | 64 | ★★★★★ |
| 562 | meqLowFreq | u8 logarithmic ~6 raw/oct | 12 | ★★★★★ |
| 564 | meqLowQ | direct (raw = UI × 10) | 7 (=0.7) | ★★★★★ |
| 566 | meqLowType | enum 0=Shelf, 1=Peak | 0 | ★★★★★ |
| 568 | meqLowMidGain | c64 | 64 | ★★★★★ |
| 570 | meqLowMidFreq | u8 logarithmic | 20 | ★★★★☆ |
| 572 | meqLowMidQ | u8 direct | 7 | ★★★★★ |
| 574 | meqMidGain | c64 | 64 | ★★★★★ |
| 576 | meqMidFreq | u8 logarithmic | 28 | ★★★★★ |
| 578 | meqMidQ | u8 direct | 7 | ★★★★★ |
| 580 | meqHiMidGain | c64 | 64 | ★★★★★ |
| 582 | meqHiMidFreq | u8 logarithmic | 44 | ★★★★☆ |
| 584 | meqHiMidQ | u8 direct | 7 | ★★★★★ |
| 586 | meqHighGain | c64 | 64 | ★★★★★ |
| 588 | meqHighFreq | u8 logarithmic | 52 | ★★★★★ |
| 592 | meqHighType | enum 0=Shelf, 1=Peak | 0 | ★★★★★ |

**Design note:** When Q is changed, the Type flag can auto-update (+566 = 0 → 1 at Q-max). UI logic: Q is meaningful only for Peak type, not Shelf.

**★★★★☆ predicted fields:** Lo Mid Freq (570) and Hi Mid Freq (582) lack dedicated clean-1-diff test files. The stride pattern (6-byte block for non-Low bands) makes the positions highly likely but not empirically proven. Candidates for future verification.

## 4.11 Master FX ★★★★★

Region `blob[598:650]` (52 bytes). 26 fields. Structure identical to Reverb/Variation FX.

| abs | Field | Encoding |
|---|---|---|
| 37 | masterFxOnOff (toggle) | bool, default 0=OFF |
| 598..599 | masterFxType | u16le, default 32 (M/S EQ Compressor=80) |
| 602..648 | 24 × u16le params | stride 2 |

For M/S EQ Compressor type: M/S Balance, M Threshold, M Makeup Gain, S Threshold, S Makeup Gain, Stereo Expand, Comp Type, M Comp Curve, S Comp Curve, M Gain, S Gain, EQ Position, M EQ Low Freq/Gain/Q, M EQ High Freq/Gain/Q, S EQ Low Freq/Gain/Q, S EQ High Freq/Gain/Q.

## 4.12 SuperKnob Mid-Position ★★★★★

Region `blob[670:723]`.

| abs | Field | Encoding | Default |
|---|---|---|---|
| 670..671 | commonSuperKnobValue | u16le | 512 |
| 672 | midPositionEnable | bool | 0 |
| 674..721 | 8 assigns × 6 bytes | stride 6 per assign | - |

Per assign (N=0..7), abs = 674 + N × 6:

| Relative | Field | Encoding | Default |
|---|---|---|---|
| +0 | AssignN LeftPosition | u8 | 0 |
| +2 | AssignN MidPosition | u16le | 512 |
| +4 | AssignN RightPosition | u16le | 1023 |

## 4.13 Region [732:766] [STRUKT] ★★★★★

34 bytes, structurally characterized but UI function not identified.

```
[732:760]  14 × u16le values
[760:766]  6-byte trailer
```

**Default values:** `[31, 31, 15, 7, 23, 7, 23, 15, 15, 23, 7, 23, 7, 15]`

Pattern: all values belong to the "8N − 1" family (possible bit-mask). UI function unknown. Patch editor: read and write back unchanged.

## 4.14 Audio In + Envelope Follower ★★★★★

| abs | Field | Encoding | Default |
|---|---|---|---|
| 48 | audioInInsASwitchCommon | bool | 1=ON |
| 49 | audioInInsBSwitchCommon | bool | 1=ON |
| 766 | **audioInVolume = EF AD Output Level** | direct (UI aliasing) | 100 |
| 768 | audioInPan | c64 | 64 (Center) |
| 770 | audioInRevSend | direct | 0 |
| 772 | audioInVarSend | direct | 0 |
| 774 | audioInInsConnect | enum 1=A→B (default), 2=B→A | 1 |
| 778 | audioInDryLevel | direct | 127 |
| 780 | envFollowerGain | c64 | 64 (=0 dB) |
| 782 | envFollowerAttack | direct | 16 |
| 784 | envFollowerRelease | direct | 7 |

**UI aliasing:**
- `blob[+766]` has two UI labels — "Audio In Volume" and "EF AD Output Level". Same physical byte.
- `blob[+48, +49]` (Common view) controls the same logical function as `blob[+6734, +6735]` (Part view, section 5.1). The UI has two paths for Audio In Insertion A/B switches.

**Audio In Mute & Solo — NOT IN BLOB ★★★★★:**
The Mute and Solo buttons on the Audio In row in the Mixing view (Audio tab) are **UI state**, not persisted data. Toggling Mute results in 0 signal-diffs in the entire blob. The editor does not need to handle these.

## 4.15 Common Assign Names ★★★★★

Region `blob[2280:2447]` (8 strings × 21 bytes = 168 bytes).

```
COMMON_ASSIGN_NAMES_BASE   = 2279
COMMON_ASSIGN_NAMES_STRIDE = 21
COMMON_ASSIGN_NAMES_LEN    = 16  # max chars
```

Default: "Assign 1", "Assign 2", ..., "Assign 8".

```python
def get_common_assign_name_addr(slot):
    """slot = 1..8. ASCII starts at +1 from base (length prefix at +0)."""
    return 2279 + 1 + (slot - 1) * 21
```

## 4.16 CA_PERF (Common Assigns Performance) ★★★★★

See section 7 — identical structure to CA_PART (difference: scope flag).

## 4.17 Stride-106 Zone/Control block [STRUKT]

5 groups × 8 blocks = 40 blocks total, ~3300 bytes:

| Group | Region | Block count |
|---|---|---|
| 1 | `[840:1710]` | 8 blocks |
| 2 | `[3186:4043]` | 8 blocks |
| 3 | `[4083:4943]` | 8 blocks |
| 4 | `[4943:5826]` | 8 blocks |
| 5 | `[5942:6700]` | 8 blocks |

**Hypothesis:** Per-part Aftertouch/Velocity tables or Mod Source mappings. UI function not identified. Patch editor: read/write verbatim.

## 4.X Control Assign — 32 slots ★★★★★

UI: **Common / Control / Control Assign** — allows routing controllers (Mod Wheel, Aftertouch, Foot Controllers, etc.) to parameters in the Performance.

**Position:** `[2451:3155]` = 32 slots × 22 bytes = 704 bytes total.

```python
CONTROL_ASSIGN_BASE = 2451
CONTROL_ASSIGN_STRIDE = 22
CONTROL_ASSIGN_COUNT = 32  # 8 Assign Knobs × 4 Destinations per Knob
```

**Slot structure (22 bytes, rel 0..21):**

| Rel | Field | Encoding | Default | Interpretation |
|----:|---|---|---:|---|
| 0 | slot_signature | u8 const | 18 | Always 18 in all 32 slots |
| 1 | source_set | u8 bool | 0 | 0=Off, 1=Source active |
| 3 | source_id | u8 enum | 8 | 8=None default, 1=ModWheel/CC#1 (Yamaha enum) |
| 5 | dest_param_lo | u8 | 1 | Destination parameter low byte |
| 6 | dest_param_hi | u8 | 0 | Destination param hi / flag |
| 9 | param2 | u8 | 0 | Parameter 2 |
| 11 | param1 | u8 | 5 | Parameter 1 |
| 13 | curve_type | u8 enum | 0 | Curve type (0..3 for "Bell" etc.) |
| 15 | polarity | u8 enum | 0 | 0=Uni, 1=Bi |
| 17 | slot_endmark | u8 const | 192 | Always 192 (0xC0) in all slots |

**32 slots layout:** Most likely **8 Assign Knobs × 4 Destinations per Knob** (matching the Yamaha model where each knob can have 4 destination rows). Alternatively 8 Knobs × 4 Curve slots.

**Note:** This is **Common level** (Performance-global), NOT per Part or per Element. This is consistent with Controller Sets being Common level.

**Source enum (source_id rel +3):** 8=None, 1=ModWheel (CC#1). More values need verification with dedicated tests.

---

# 5. Part Common (Sub-blob 2..N) ★★★★★

Each Part Common is **5765 bytes** (sub-blob payload + 27-byte header).

The structure is shared by AWM2, FM-X, AN-X (with slight engine-specific interpretation in a few fields), and partially shared by Drum (which has its own layout for some byte ranges — see section 13.3).

## 5.1 Part Common single fields (Part 1, abs) ★★★★★

Verified absolute addresses for Part 1. For Part N, add `(N-1) * 5765`.

| abs | Field | Encoding | Default |
|---|---|---|---|
| 6708..6729 | partName (22 bytes ASCII) | string | "Init Normal (XXX)" |
| 6730 | monoPoly | bool | 1=Poly |
| 6732 | portamentoLegato | bool | 0 |
| 6733 | portamentoMode | enum | 0=Fingered |
| 6734 | partInsASw | bool | 1=ON |
| 6735 | partInsBSw | bool | 1=ON |
| 6736 | partElemPanToggle | bool | 1=ON |
| 6738 | partOctave | c64 | 64 |
| 6739 | partKeyOnDelaySw | bool | 0 |
| 6741 | partInsConnect | enum 1=A→B, 2=B→A | 1 |
| 6743 | partOutput | enum 0=L&R, 1=Off, 2=AsgnL... | 0 |
| 6745 | partInsB_DryLevel | direct | 127 |
| 6747 | partInsA_Variation Send | direct | 0 |
| 6749 | partInsA_Reverb Send | direct | 0 |
| 6751 | partVariationSend | direct | 0 |
| 6753 | partReverbSend | direct | 0 |
| 6755 | partDryLevel | direct | 127 |
| 6757 | partPan | c64 | 64 |
| 6759 | partVolume | direct | 100 |
| 6761 | partVelDepth | c64 | 64 |
| 6763 | partVelOffset | c64 | 64 |
| 6765 | partNoteLimitLow | MIDI | 0 |
| 6767 | partNoteLimitHigh | MIDI | 127 |
| 6769 | partVelLimitLow | u8 | 1 |
| 6771 | partVelLimitHigh | u8 | 127 |
| 6773 | partMainCategory | enum | 0 |
| 6775 | partSubCategory | enum | 0 |
| 6777 | partKbdCtrlSw | bool | 0 |
| 6779 | partMonoMonoSwitch | bool | 0 (Mono off=Poly) |
| 6781 | partArpHold | bool | 0 |
| 6782 | partArpOn | bool | 0 |
| 6783 | partArpVelLimitLow | u8 | 1 |
| 6785 | partArpVelLimitHigh | u8 | 127 |
| 6787 | partArpNoteLimitLow | MIDI | 0 |
| 6789 | partArpNoteLimitHigh | MIDI | 127 |
| 6791 | partArpKeyMode | enum | 0=Sort |
| 6793 | partArpUnit | enum | 0 |
| 6795 | partArpSwing | c64 | 64 |
| 6797 | partArpOctaveRange | c64 | 64 |
| 6799 | partArpQuantizeValue | enum | 0 |
| 6801 | partArpQuantizeStrength | direct | 0 |
| 6802 | partArpPlayOnly | bool | 0 |
| 6803 | partMotionSeqMaster | bool | 0 |
| 6805 | partVelocityDepth (mirror) | c64 | 64 |
| 6807 | partVelocityOffset (mirror) | c64 | 64 |
| 6809 | partPitchBendUpper | c64 | 66 (= +2) |
| 6811 | partPitchBendLower | c64 | 62 (= −2) |
| 6813 | partPortamentoTime | direct | 0 |
| 6815 | partMainCategory (alt) | enum | 0 |
| 6817 | partSubCategory (alt) | enum | 0 |
| 6818 | partKbdCtrlSw (alt) | bool | 0 |
| 6819 | partVelLimitLow (mirror) | u8 | 1 |
| 6821 | partVelLimitHigh (mirror) | u8 | 127 |
| 6823 | partNoteLimitLow (mirror) | MIDI | 0 |
| 6825 | partNoteLimitHigh (mirror) | MIDI | 127 |
| 6827 | partVelDepth (mirror) | c64 | 64 |
| 6829 | partVelOffset (mirror) | c64 | 64 |
| 6831 | partVolume (mirror) | u8 | 100 |
| 6833 | partPan (mirror) | c64 | 64 |
| 6835 | partReverbSend (mirror) | u8 | 0 |
| 6837 | partVariationSend (mirror) | u8 | 0 |
| 6839 | partDryLevel (mirror) | u8 | 127 |
| 6843 | partExpression | direct | 127 |
| 6847 | partOutput (mirror) | enum | 0 |
| 6851 | partAEG_OffsetAttack | c64 | 64 |
| 6853 | partAEG_OffsetDecay | c64 | 64 |
| 6855 | partAEG_OffsetSustain | c64 | 64 |
| 6857 | partAEG_OffsetRelease | c64 | 64 |
| 6859 | partFEG_OffsetAttack | c64 | 64 |
| 6861 | partFEG_OffsetDecay | c64 | 64 |
| 6863 | partFEG_OffsetSustain | c64 | 64 |
| 6865 | partFEG_OffsetRelease | c64 | 64 |
| 6867 | partFilterCutoff | c64 | 64 |
| 6869 | partResonance | c64 | 64 |
| 6871 | partFEGDepth | c64 | 64 |
| 6873..6883 | partMotionSeqLanes | bool × 8 | 0 |
| 6885 | partMotionSeqMaster (alt) | bool | 0 |
| 6913 | partPitchBendUpper (mirror) | c64 | 66 |
| 6915 | partPitchBendLower (mirror) | c64 | 62 |
| 6917 | partDetuneHz | u16le | 128 |
| 6919 | partNoteShift | c64 | 64 |
| 6921 | partFineTune | c64 | 64 |
| 6923 | partLegatoSlope | u8 0..7 | 0 |
| 6924 | partAfterTouchSwitch | bool | 0 |
| 6925 | partAfterTouchDest | enum (1=Pitch, 9=FilterCutoff) | 1 |

This list is not exhaustive — the Part Common contains many more fields including LFO, EG and FX-related parameters covered in sections 5.2..5.12.

## 5.2 Part LFO (FM-X) ★★★★★

Region within Part Common, specific to FM-X.

| Rel | Field | Encoding | Default |
|---|---|---|---|
| +200 | lfoSpeed | u8 | 38 |
| +202 | lfoSpeedFine | u8 | 0 |
| +204 | lfoWave | enum (Saw=0, Tri=1, Square=2) | 1 |
| +206 | lfoPhase | u8 | 0 |
| +208 | lfoKeyOnReset | bool | 1 |
| +210 | lfoTempoSync | bool | 0 |
| +212 | lfoFadeIn | u8 | 0 |
| +214 | lfoDelay | u8 | 0 |

## 5.3 Part 2nd LFO (FM-X) ★★★★★

| Rel | Field | Encoding | Default |
|---|---|---|---|
| +220 | secondLfoSpeed | u8 | 50 |
| +222 | secondLfoSpeedFine | u8 | 0 |
| +224 | secondLfoWave | enum | 0 |
| +226 | secondLfoKeyOnReset | bool | 1 |
| +228 | secondLfoTempoSync | bool | 0 |
| +230 | secondLfoFadeIn | u8 | 0 |
| +232 | secondLfoDelay | u8 | 0 |

## 5.4 Part PEG (FM-X) ★★★★★

Part-level Pitch EG (overlay on top of element/OP-level PEG).

| Rel | Field | Encoding | Default |
|---|---|---|---|
| +250 | partPegPitchKeyFollow | c64 | 64 |
| +252 | partPegPitchVel | c64 | 64 |
| +254 | partPegLevel0 | c50 | 50 |
| +256 | partPegLevelAttack | c50 | 50 |
| +258 | partPegLevelDecay1 | c50 | 50 |
| +260 | partPegLevelDecay2 | c50 | 50 |
| +262 | partPegLevelRelease | c50 | 50 |
| +264 | partPegTimeAttack | direct | 0 |
| +266 | partPegTimeDecay1 | direct | 0 |
| +268 | partPegTimeDecay2 | direct | 0 |
| +270 | partPegTimeRelease | direct | 0 |

## 5.5 Part AEG / FEG (engine-independent, AN-X/FM-X/AWM2) ★★★★★

The shared Part-level AEG and FEG offset block. See section 5.1 (abs 6851..6865).

For Drum, these byte positions have a different interpretation (see section 13.3).

## 5.6 Part Pitch Bend / Detune / Note Shift ★★★★★

| abs | Field | Encoding | Default |
|---|---|---|---|
| 6809 | partPitchBendUpper | c64 | 66 |
| 6811 | partPitchBendLower | c64 | 62 |
| 6913 | partPitchBendUpper (mirror) | c64 | 66 |
| 6915 | partPitchBendLower (mirror) | c64 | 62 |
| 6917 | partDetuneHz | u16le | 128 |
| 6919 | partNoteShift | c64 | 64 |
| 6921 | partFineTune | c64 | 64 |

## 5.7 Part 3-band EQ ★★★★★

Per-Part 3-band EQ (different from Element EQ and Common Master EQ).

| Rel | Field | Encoding | Default |
|---|---|---|---|
| +200 | partEqLowGain | c64 | 64 |
| +202 | partEqLowFreq | direct | 12 |
| +204 | partEqMidGain | c64 | 64 |
| +206 | partEqMidFreq | direct | 28 |
| +208 | partEqMidQ | direct | 7 |
| +210 | partEqHighGain | c64 | 64 |
| +212 | partEqHighFreq | direct | 52 |

## 5.8 Part 2-band EQ ★★★★★

Some Parts use a simpler 2-band EQ (Low Shelf + High Shelf):

| Rel | Field | Encoding | Default |
|---|---|---|---|
| +215 | partEqLowGain (2band) | c64 | 64 |
| +217 | partEqLowFreq (2band) | direct | 12 |
| +219 | partEqHighGain (2band) | c64 | 64 |
| +221 | partEqHighFreq (2band) | direct | 52 |

## 5.9 Arp Common ★★★★★

Per-Part Arp Common (34 fields). See full list in section 19.

| Rel | Field | Encoding | Default |
|---|---|---|---|
| +73..+74 | partArpVelLimitLow/High | u8 | 1/127 |
| +75..+76 | partArpNoteLimitLow/High | MIDI | 0/127 |
| +77 | partArpKeyMode | enum | 0 |
| +78 | partArpUnit | enum | 0 |
| +79 | partArpSwing | c64 | 64 |
| +80 | partArpOctaveRange | c64 | 64 |
| +82 | partArpQuantizeValue | enum | 0 |
| +83 | partArpQuantizeStrength | direct | 0 |
| +84 | partArpPlayOnly | bool | 0 |
| ... | (additional Arp params) | ... | ... |

## 5.10 Region [7094:7165] — Arp Individual data [STRUKT]

71 bytes of Arp-related individual phrase data. Structurally identified, UI function not fully mapped at field level. Patch editor: read/write verbatim.

## 5.11 Part Assign Names ★★★★★

8 strings × 21 bytes per Part. Stride 21, max 16 chars per name.

```python
def get_part_assign_name_addr(part, slot):
    """part = 1..N, slot = 1..8"""
    part_base = 6708 + (part - 1) * 5765
    return part_base + ASSIGN_NAMES_REL + 1 + (slot - 1) * 21
```

## 5.12 CA_PART (Per-Part Common Assigns) ★★★★★

See section 7 — same structure as CA_PERF. CA_PART has 8 slots per Part.

## 5.13 AWM2 Control Source block ★★★★☆

AWM2-specific 8-source control routing structure within Part Common.

Each source has: id, depth, polarity, curve. 8 sources × 5 bytes = 40 bytes.

| Rel | Field |
|---|---|
| +0 | source_id (enum: ModWheel, AfterTouch, etc.) |
| +1 | depth |
| +2 | polarity (Uni/Bi) |
| +3 | curve_type |
| +4 | reserved |

The exact rel offset within Part Common depends on the AWM2 sub-layout; refer to the AWM2 engine section (12) for details.

---

# 6. Receive Switch per Part ★★★★★

Each Part has a Receive Switch (RcvSw) bitmap controlling which MIDI controllers it responds to.

## 6.1 Block architecture

```
RCV_SW_BLOCK_SIZE = 26 bytes per Part
```

The 26-byte block contains one bit per receivable controller (Pitch Bend, Modulation Wheel, Sustain, Sostenuto, Soft Pedal, Foot Controller 1/2, Breath, Expression, Pan, Volume, etc.).

The block layout is **identical across all 4 engines** (AWM2/AN-X/FM-X/Drum).

## 6.2 RcvSw positions (26/26 mapped)

| Rel | Field | Encoding | Default |
|---:|---|---|---:|
| +0 | rcvSw_PitchBend | bool | 1 |
| +1 | rcvSw_ModWheel | bool | 1 |
| +2 | rcvSw_AfterTouch | bool | 1 |
| +3 | rcvSw_PolyAT | bool | 1 |
| +4 | rcvSw_ChannelAT | bool | 1 |
| +5 | rcvSw_Sustain | bool | 1 |
| +6 | rcvSw_Sostenuto | bool | 1 |
| +7 | rcvSw_SoftPedal | bool | 1 |
| +8 | rcvSw_FootCtrl1 | bool | 1 |
| +9 | rcvSw_FootCtrl2 | bool | 1 |
| +10 | rcvSw_FootSwitch | bool | 1 |
| +11 | rcvSw_Breath | bool | 1 |
| +12 | rcvSw_Volume | bool | 1 |
| +13 | rcvSw_Pan | bool | 1 |
| +14 | rcvSw_Expression | bool | 1 |
| +15 | rcvSw_Bank | bool | 1 |
| +16 | rcvSw_Program | bool | 1 |
| +17 | rcvSw_RPN_NRPN | bool | 1 |
| +18 | rcvSw_Asw1 | bool | 1 |
| +19 | rcvSw_Asw2 | bool | 1 |
| +20 | rcvSw_Ribbon | bool | 1 |
| +21 | rcvSw_MS_Trigger | bool | 1 |
| +22..+25 | (reserved) | bool | 1 |

## 6.3 RcvSw helpers

```python
RCV_SW_BLOCK_REL = 5648  # within Part Common
RCV_SW_BLOCK_SIZE = 26

def get_rcv_sw_addr(part, controller_idx):
    """part = 1..N, controller_idx = 0..25"""
    part_base = 6701 + (part - 1) * 5765
    return part_base + RCV_SW_BLOCK_REL + controller_idx
```

## 6.4 RcvSw — NOT IN BLOB ★★★★★

Some receive switches visible in the UI are **not** stored in the Performance blob:
- Master Tune (global system setting in ESYS/DSYS)
- MIDI Channel In/Out (global, not per-Performance)
- Local Control On/Off (UI state)

These are not Performance-level data and should not be edited via the per-Performance blob.

---

# 7. Common Assigns (CA structures) ★★★★★

## 7.1 CA constants

```python
CA_PERF_BASE = 2451      # 32 slots × 22 bytes
CA_PART_BASE_REL = 1520  # within Part Common, 8 slots × 22 bytes
CA_STRIDE = 22
CA_PERF_COUNT = 32
CA_PART_COUNT = 8
```

## 7.2 CA slot layout (22 bytes per slot) ★★★★★

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

## 7.3 Difference CA_PERF vs CA_PART

| Attribute | CA_PERF | CA_PART |
|---|---|---|
| Base address | 2451 | 1520 (Part Common relative) |
| Slot count | 32 | 8 |
| Scope | Performance-global | Per-Part |
| Destinations | Performance + Common params | Part + Element params |

The slot structure (22 bytes) is identical in both.

## 7.4 CA Source enum

42 controller sources are defined. See `ysfc_enums/controllers.py` (`CONTROLLER_SOURCES`).

Common values:
- 0 = Pitch Bend
- 1 = Mod Wheel
- 2 = After Touch
- 8 = None
- 17..24 = Assign Knob 1..8

## 7.5 CA Destination enum (verified subset)

The complete list has 414 entries (see `CONTROLLER_DESTINATIONS`).

### Encoding (critical!)

Destination consists of **two bytes**: `destination_lo` (+4) and `destination_hi` (+5):

```
CONTROLLER_DESTINATIONS_idx = destination_lo + destination_hi * 256
```

- For destinations with index **0..255**: write the value in `destination_lo`, `destination_hi=0`
- For destinations with index **256..511** (Performance, MS, Arp, Per-Part Assign Knobs): write `destination_lo = (idx − 256)`, `destination_hi = 1`

Quick reference:

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

## 7.6 CA CurveType enum (verified subset)

| Value | Curve |
|---:|---|
| 0 | Linear |
| 1 | Concave |
| 2 | Convex |
| 3 | Bell |
| 4 | Sigmoid |
| 5 | Threshold |

## 7.7 Block-end signature (trailer)

Each CA slot ends with byte `0xC0` (192) at rel +16 — this is the "endmark" that delimits one slot from the next. Always preserved.

---

# 8. Scene Structures ★★★★★

Two separate structures: Scene Struct 1 (performance-global flags) and Scene Struct 2 (per-Part Lane snapshots).

## 8.1 Scene Struct 1 — performance-global ★★★★★

```
SCENE_STRUCT1_BASE   = 1710
SCENE_STRUCT1_STRIDE = 71
SCENE_COUNT          = 8
```

**Region:** `blob[1710:2278]` = 568 bytes (8 scenes × 71 bytes).

**Per-scene fields (9 fields within 71-byte record):**

| Relative | Field | Encoding | Default |
|---|---|---|---|
| +0 | sceneArp | bool | 0 |
| +1 | sceneMotionSeq | bool | 0 |
| +2 | sceneSuperKnob | bool | 0 |
| +3 | sceneMixing | bool | 0 |
| +4 | sceneAEG | bool | 0 |
| +5 | sceneArpMsFx | bool | 0 |
| +6 | sceneSuperKnobLink | bool | 0 |
| +15 | sceneKbdCtrl | bool | 0 |
| +16 | sceneNoteLimit | bool | 0 |

**Per-scene SuperKnob value mirror:** `blob[+1710 + N*71 + 25..26]` (u16le, same data as per-scene SK array at abs 184).

```python
def scene_struct1_abs(field_name, scene_idx):
    """scene_idx: 0..7"""
    return 1710 + scene_idx * 71 + SCENE_STRUCT1_FIELDS[field_name]
```

**Cross-scene verification:**
- Scene 4 SuperKnob @ 1925 = 1710 + 3×71 + 2 ✓
- Scene 8 ArpMsFx @ 2212 = 1710 + 7×71 + 5 ✓
- Scene 8 SuperKnob @ 2209 = 1710 + 7×71 + 2 ✓

## 8.2 Scene Struct 2 — per-Part Lane ★★★★★

```
SCENE_STRUCT2_BASE   = 7421
SCENE_STRUCT2_STRIDE = 84
```

**Region:** `blob[7421:8093]` = 672 bytes (8 scenes × 84 bytes).

**Per-scene fields (11 fields):**

| Relative | Field | Live mirror abs | Encoding |
|---|---|---|---|
| +0 | sceneSwing | 6887 | c128 |
| +2 | sceneUnit | 7097 | enum |
| +4 | sceneGateTime | 7119 | direct |
| +6 | sceneVelocity | 7117 | direct |
| +8 | sceneAmp | 6889 | c128 |
| +10 | sceneShape | 6891 | c64 |
| +12 | sceneSmooth | 6893 | c128 |
| +14 | sceneRandom | 6895 | direct |
| +20 | sceneNoteLimitLow | 6823 | MIDI note |
| +22 | sceneNoteLimitHigh | 6825 | MIDI note |
| +24 | sceneNoteShift | 6919 | c64 |

**Note:** KbdCtrl and NoteLimit per-part toggles are in **Struct 1** (rel 15, 16), not in Struct 2. The UI listing is confusing on this point.

## 8.3 Side effects during scene editing

- `blob[+32]` changes during Scene Common Offset toggle (performance-level master switch)
- `blob[+7417]` changes when Scene1 AEG Offset is turned Off (160→115, mechanism unknown)
- `blob[+7419]` changes on every per-part scene edit (modified flag, +1)

---

# 9. MS Sequencer ★★★★★

Region: `blob[8929:12404]` (in Part Common). Stride **884 bytes per lane** × 4 lanes.

**Lane bases (Part 1):**

| Lane | Base (abs) |
|---|---|
| Lane 1 | 8929 |
| Lane 2 | 9813 |
| Lane 3 | 10697 |
| Lane 4 | 11581 |

(Difference 884 ✓ verified across all 4 lanes.)

## 9.1 Per-lane offsets (relative from lane base) ★★★★★

| Rel | Field | Encoding | Default |
|---|---|---|---|
| +0 | LaneSwitch | bool | 0 |
| +1 | MSFXSwitch | bool | 1 |
| +2 | Trigger | bool | 0 |
| +3 | Loop | bool | 1 |
| +8 | SyncSwitch | bool | 0 |
| +10 | Speed | u8 direct | 63 |
| +12 | Sync_Tempo_Unit | u8 (3=default, 9=400%) | 3 |
| +14 | KeyOnReset | u8 (0=Off, 2=1stOn) | 0 |
| +16 | LaneVelLimit_Low | direct | 1 |
| +18 | LaneVelLimit_High | direct | 127 |
| +20 | DelayTime | direct | 0 |
| +22 | DelaySteps | direct | 0 |
| +24 | FadeInTime | direct | 0 |
| +26 | FadeInSteps | direct | 0 |
| +36 | Amp | direct | 127 |
| +38 | Smooth | direct | 0 |
| +42 | Polarity | bool (0=UNI, 1=BI) | 0 |
| +44 | MSGrid | u8 (3=default, 1=60) | 3 |
| +116 | PulseA Type | u8 (0=Standard, 2=Threshold) | 0 |
| +118 | PulseA Prm1 | direct | 5 |
| +120 | PulseA Prm2 | direct | 0 |
| +122 | ControlA Switch | bool | 1 |
| +124 | ControlA ControlSwitch | bool | 0 |
| +128 | PulseB Type | u8 | 0 |
| +130 | PulseB Prm1 | direct | 5 |
| +132 | PulseB Prm2 | direct | 0 |
| +134 | ControlB Switch | bool | 1 |
| +136 | ControlB ControlSwitch | bool | 0 |

## 9.2 Common Motion Sequencer (Performance Common) ★★★★★

Six Performance Common fields control Motion Seq globally for the entire Performance.

**UI name vs internal terminology:** In the UI view "Motion Seq > Common / Lane" the section is called "Common". These fields are **not per-Lane** — they apply to all Lanes and all Parts. The correct name is "Common Motion Seq" or "Performance MS".

| abs | Field | Encoding | Default |
|---|---|---|---|
| 100..101 | Common MS Swing | u16le c128 | 128 |
| 102 | Common MS Unit | u8 enum (3=1/16, 0=50%) | 3 |
| 358 | ArpSelect | u8 0-indexed | 0 (=Arp1) |
| 360 | SyncQuantize | u8 | 0 (=OFF) |
| 654 | MSSelect | u8 0-indexed | 0 (=MS1) — Note: collision with side-effect flag (section 17) |
| 656..657 | Common MS Amplitude | u16le c128 | 128 |
| 658..659 | Common MS Shape | u16le c64 | 64 |
| 660..661 | Common MS Smooth | u16le c128 | 128 |
| 662..663 | Common MS Random | u16le c128 | 128 |

## 9.3 Part Motion Sequencer (Part Common) ★★★★★

Six Part Common fields that control Motion Seq for the entire Part (all 4 Lanes in the part). In the UI view these appear under the "Part" section, distinct from the "Common" section above.

The View Lane dropdown does **not** affect these bytes — it only controls the Edit Part Sequencer view's display.

| abs (Part 1) | Rel (sub-blob +N) | Field | Encoding | Default |
|---:|---:|---|---|---:|
| 6887..6888 | +186 | Part MS Swing | u16le c128 | 128 |
| 6889..6890 | +188 | Part MS Amplitude | u16le c128 | 128 |
| 6891..6892 | +190 | Part MS Shape | u16le c64 | 64 |
| 6893..6894 | +192 | Part MS Smooth | u16le c128 | 128 |
| 6895 | +194 | Part MS Random | u8 direct 0..100 | 0 |
| 7097 | +396 | Part MS Unit | u8 enum (3=1/16, 0=50%) | 3 |

**Stride:** 5765 bytes between parts (Part 2 Swing @ 12652 = 6887 + 5765).

**Shared offsets:** `abs 6887` is shared with "Arp Swing" (same byte used for both functions). `abs 7097` is shared with "Arp Unit".

## 9.4 Per-lane data (Lane block) ★★★★★

| abs | Field | Encoding | Default |
|---|---|---|---|
| 12753 | Part seq-field | u8 (3=default, 4=seq-sync) | 3 |
| 13116 | Part arp-field | u8 (0=default, 9=arp-active) | 0 |

---

# 10. Engine data: AN-X ★★★★★

**Engine size:** 684 bytes (689 in pool with separator).
**Pool base (Part 1, solo):** abs 12466 (= after sub-blob 2's 5765 + 0 sep).

For Part N in multi-part file: see section 3 (engine-pool addressing).

## 10.1 AN-X coverage summary

Through scanning of **799 AN-X test files** against baseline, all 686 bytes in the engine pool are classified:

| Category | Count | Status |
|---|---:|---|
| Mapped & constant | 55 | UI-mapped fields that don't change in tests (default values) |
| Mapped & varies | 121 | UI-mapped fields ★★★★★ |
| Unmapped constants | 452 | [INTERN] — firmware constants (100% identical across 799 files) |
| Unmapped dominant (>95%) | 50 | UI fields varying in one or more test files |
| Filter trailers | 6 | [INTERN] — confirmed non-UI |

**Final result: 171 UI-mapped fields ★★★★★, 458 [INTERN] bytes, 0 unmapped — all known UI fields verified** ✅

## 10.2 OSC1 / OSC2 / OSC3 — stride 125 ★★★★★

```
ANX_OSC1_BASE = 12626
ANX_OSC_STRIDE = 125
ANX_OSC2_BASE = 12751 = 12626 + 125
ANX_OSC3_BASE = 12876 = 12626 + 250
```

**Per-OSC layout (selected fields):**

| Rel | Field | Encoding | Default |
|---:|---|---|---|
| +0 | osc_waveform | enum 0..4 (Saw, Sq, ...) | 0 |
| +2 | osc_octave | enum 0..6 | 3 (=8') |
| +4..+5 | osc_pitch | u16le c504 (cents) | 504 |
| +6..+7 | osc_peg_depth | u16le c247 | 247 |
| +8..+9 | osc_peg_depth_vel | u16le c256 | 256 |
| +10..+11 | osc_pitch_lfo_depth | u16le c247 | 247 |
| +12..+13 | osc_sync_pitch | u16le | 0 |
| +14..+15 | osc_sync_vel | u16le c256 | 256 |
| +16..+17 | osc_sync_eg_depth | u16le c256 | 256 |
| +18..+19 | osc_sync_lfo_depth | u16le c256 | 256 |
| +20 | osc_pulse_width | u8 | 128 (=50%) |
| +20..+21 | osc_pulse_width_vel | u16le c256 | 256 |
| +24..+25 | osc_pulse_width_eg_depth | u16le c256 | 256 |
| +26..+27 | osc_pulse_width_lfo_depth | u16le c128 | 128 |
| +28..+29 | osc_wave_shaper | u16le | 0 |
| +30 | osc_wave_shaper_vel | u8 | 0 |
| +32 | osc_shaper_eg_depth | u8 c128 | 128 |
| +34 | osc_shaper_lfo_depth | u8 c128 | 128 |
| +38 | osc_fm_level_vel | u8 | 0 |
| +40 | osc_ring_mod | u8 | 0 |
| +46 | osc_key_on_reset | bool | varies |
| +48..+49 | osc_level | u16le | 0 |
| +52..+53 | osc_eg_attack | u16le | 0 |
| +54..+55 | osc_eg_decay | u16le | 160 |
| +56..+57 | osc_eg_sustain | u16le | 0 |
| +58..+59 | osc_eg_release | u16le | 160 |
| +67 | mod_lfo_ratio_row1 | u8 | 127 |
| +69 | mod_lfo_ratio_row2 | u8 | 127 |
| +71 | mod_lfo_ratio_row3 | u8 | 127 |

## 10.3 AN-X Pre-OSC (Part Settings, Pitch LFO, Filter LFO, Amp + Amp LFO) ★★★★★

### Part Settings (Pre-OSC top):

| abs | Field | Encoding | Default |
|---|---|---|---|
| 12465 | part_random_pan_anx | u8 c64 | 0 |
| 12467 | alternate_pan_anx | u8 c64 | 64 |
| 12469 | scaling_pan_anx | u8 c64 | 64 |
| 12477 | unison_voices | u8 enum | 0 |
| 12479 | unison_detune | u8 | 0 |
| 12481 | unison_spread | u8 | 0 |
| 12485 | osc_reset_mode | u8 enum | 0 (Off=0, Phase=1, Tune=2, Full=3) |
| 12487 | voltage_drift | u8 | 64 |
| 12489 | ageing | u8 | 100 |

### Pitch LFO + PEG block (12499-12511):

| abs | Field | Encoding | Default |
|---|---|---|---|
| 12499 | peg_time_vel | u8 | 0 |
| 12503 | pitch_lfo_speed | u16le | 208 |
| 12507 | pitch_lfo_phase | u8 enum 16-step | 0 |
| 12509 | pitch_lfo_delay | u8 | 0 |
| 12511 | pitch_lfo_fadein | u8 | 0 |

### Noise block (12513-12518):

| abs | Field | Encoding | Default |
|---|---|---|---|
| 12513 | noise_tone | u8 | 64 |
| 12515 | noise_connect | u8 enum | 0 (Thru/Amp/InsA/InsB) |
| 12518 | noise_unknown_1 | u8 | 0 |

### FEG block (12517-12529):

| abs | Field | Encoding | Default |
|---|---|---|---|
| 12517 | feg_attack | u8 | 0 |
| 12519 | feg_decay | u8 | 160 |
| 12521 | feg_sustain | u8 | 0 |
| 12523 | feg_release | u8 | 160 |
| 12525 | feg_sustain_anx | u8 | 0 |
| 12527 | feg_release_anx | u8 | 160 |
| 12529 | feg_time_vel | u8 | 0 |

### Filter LFO block (12531-12541):

| abs | Field | Encoding | Default |
|---|---|---|---|
| 12531 | filter_lfo_wave | u8 enum | 2 (Triangle=2, Square=1) |
| 12533 | filter_lfo_speed | u16le | 208 |
| 12537 | filter_lfo_phase | u8 enum 16-step | 0 |
| 12539 | filter_lfo_delay | u8 | 0 |
| 12541 | filter_lfo_fadein | u8 | 0 |

### Amp block (12543-12551):

| abs | Field | Encoding | Default |
|---|---|---|---|
| 12543 | amp_level | u16le | 431 |
| 12545 | amp_level_vel | u8 | 0 |
| 12547 | amp_lfo_depth | u8 c128 | 128 |
| 12549 | amp_level_key | u8 | 0 |
| 12551 | amp_drive | u8 | 0 |

### Amp AEG (12553-12561):

| abs | Field | Encoding | Default |
|---|---|---|---|
| 12553 | amp_aeg_attack | u8 | 0 |
| 12555 | amp_aeg_decay | u8 | 160 |
| 12557 | amp_aeg_sustain | u16le | 511 |
| 12559 | amp_aeg_release | u8 | 115 |
| 12561 | aeg_time_vel | u16le | 0 |

### Amp LFO block (12563-12573):

| abs | Field | Encoding | Default |
|---|---|---|---|
| 12563 | amp_lfo_wave | u8 enum | 2 (Triangle=2, Square=1) |
| 12565 | amp_lfo_speed | u16le | 208 |
| 12569 | amp_lfo_phase | u8 enum 16-step | 0 |
| 12571 | amp_lfo_delay | u8 | 0 |
| 12573 | amp_lfo_fadein | u8 | 0 |

### AN-X has FOUR LFO systems:

1. **Pitch LFO** (Pre-OSC 12499-12511, Speed=12503) — modulates pitch
2. **Filter LFO** (Pre-OSC 12531-12541, Speed=12533) — modulates Filter1/Filter2 cutoff
3. **Amp LFO** (Pre-OSC 12563-12573, Speed=12565) — modulates amp
4. **Mod LFO** (Post-OSC3, Speed=13140) — matrix-based, routes to 3 destinations

All 4 have: Wave, Speed (u16le), Phase, Delay, Fade In.
Filter1/Filter2 have individual LFO Depth fields (abs 13015 / 13092).

### Pitch LFO Phase enum vs AWM2:

- AWM2 LFO Element Matrix Phase: 6 steps (0=0°, 1=90°, 2=120°, 3=180°, 4=240°, 5=270°)
- AN-X Pitch/Filter/Amp LFO Phase: **16 steps** (0..15) at 22.5° per step
  - 90° → enum 4
  - 180° → enum 8
  - 270° → enum 12
  - 315° → enum 14

## 10.4 AN-X Filter 1 (abs 13005..13027) ★★★★★

| abs | Field | Encoding | Default |
|---|---|---|---|
| 13005 | filter1_type | enum | 1 (LPF12=3 verified) |
| 13007 | filter1_cutoff_lo | u16le | 255 |
| 13008 | filter1_cutoff_hi | u8 | 3 |
| 13009 | filter1_cutoff_vel | u8 | 0 |
| 13011 | filter1_feg_depth_lo | u16le | 0 |
| 13013 | filter1_feg_depth_vel | u8 | 0 |
| 13017 | filter1_cutoff_key | u8 | 0 |
| 13019 | filter1_resonance | u8 | 0 |
| 13021 | filter1_resonance_vel | u8 | 0 |
| 13023 | filter1_drive | u8 | 0 |
| 13025 | filter1_drive_vel | u8 | 0 |
| 13027 | filter1_out_level | u8 c64 | 64 |

## 10.5 AN-X Filter 2 (abs 13082..13104) ★★★★★

| abs | Field | Encoding | Default |
|---|---|---|---|
| 13081 | (pad/marker before filter2_type) | [INTERN] | 30 |
| 13082 | filter2_type | enum | 5 (HPF24) |
| 13084 | filter2_cutoff_lo | u16le | 0 |
| 13086 | filter2_cutoff_vel | u8 | 0 |
| 13088 | filter2_feg_depth_lo | u16le | 0 |
| 13090 | filter2_feg_depth_vel | u8 | 0 |
| 13092 | filter2_lfo_depth_lo | u16le | 0 |
| 13094 | filter2_cutoff_key | u8 | 0 |
| 13096 | filter2_resonance | u8 | 0 |
| 13098 | filter2_resonance_vel | u8 | 0 |
| 13100 | filter2_drive | u8 | 0 |
| 13102 | filter2_drive_vel | u8 | 0 |
| 13104 | filter2_out_level | u8 c64 | 64 |

### AN-X Filter trailers — CLOSED as [INTERN] ★★★★★

Immediately after Filter1 out_level (abs 13027) and Filter2 out_level (abs 13104), there are 3 bytes per filter with default 127. **Confirmed non-UI** via passive scanning of the entire AN-X test corpus.

| Filter1 abs | Filter2 abs | Default | Status |
|---:|---:|---:|---|
| 13029 | 13106 | 127 | [INTERN] |
| 13031 | 13108 | 127 | [INTERN] |
| 13033 | 13110 | 127 | [INTERN] |

Of **537 verified single-edit test files** in the AN-X corpus (files with ≤3 bytes changed beyond standard noise), **NONE** modified any of the 6 trailer bytes. This is **definitive proof** that they are not directly UI-mapped.

**Practical implementation:**
- READ: Ignore
- WRITE: Write the value 127 (safe default)

## 10.6 AN-X Wave Folder + Mod EG + Mod LFO ★★★★★

| abs | Field | Encoding | Default | Notes |
|---|---|---|---|---|
| 13116 | wavefolder_amount | u8 | 0 | UI: Modifier > Folder > Wave Folder |
| 13118 | wavefolder_vel | u8 | 0 | UI: Modifier > Folder > Folder/Vel |
| 13120 | wavefolder_eg_depth | u8 c128 | 128 | UI: Modifier > EG Depth |
| 13122 | modlfo_depth | u8 c128 | 128 | UI: Modifier > LFO > LFO Depth |
| 13124 | wavefolder_texture | u8 c128 | 128 | UI: Modifier > Folder > Texture |
| 13126 | wavefolder_type | enum | 1 | Hard=1, Soft=0 |
| 13128 | modeg_attack | u8 | 0 | |
| 13130 | modeg_decay | u8 | 160 | |
| 13132 | modeg_sustain | u8 | 0 | |
| 13134 | modeg_release | u8 | 160 | |
| 13138 | modlfo_wave | enum | 2 | Triangle=2, Square=1 |
| 13140 | modlfo_speed_lo | u16le | 208 | |
| 13146 | modlfo_delay | u8 | 0 | |
| 13148 | modlfo_fadein | u8 | 0 | |

The Modifier tab has **only ONE** "LFO Depth" knob (abs 13122) — there is no separate byte for "Wave Folder LFO Depth".

## 10.7 AN-X routing matrices ★★★★☆

5 × 40-byte matrices (200 bytes total) within the engine pool. Structurally identified as routing destinations for modulation but not UI-editable (controlled indirectly via Control Assign).

| Matrix | Rel range | Size |
|---|---|---:|
| Matrix 1 | +280..+319 | 40 |
| Matrix 2 | +320..+359 | 40 |
| Matrix 3 | +360..+399 | 40 |
| Matrix 4 | +400..+439 | 40 |
| Matrix 5 | +440..+479 | 40 |

Plus ~42 stray routing flag bytes scattered through the engine pool.

These are classified as [INTERN][STRUKT] — preserved as-is during editing.

## 10.8 AN-X Mod LFO Destination Matrix ★★★★★

Mod LFO has 3 destination rows, each row contains:
- Destination (enum) — Part Common field
- Depth — Part Common field
- 3 Oscillator Depth Ratios — one per OSC (in engine pool, OSC rel +67/+69/+71)

**Note:** The structure is **SHARED with AWM2 LFO Element Matrix**. Both engines use the same Part Common addresses. Only the destinations enum values vary per engine.

**Part Common fields:**
- `Part rel +498` (abs 7199) mod_lfo_phase
- `Part rel +516` mod_lfo_dest1 (default 2)
- `Part rel +518` mod_lfo_dest1_depth
- `Part rel +520` mod_lfo_dest2 (default 4)
- `Part rel +522` mod_lfo_dest2_depth
- `Part rel +524` mod_lfo_dest3 (default 4)
- `Part rel +526` mod_lfo_dest3_depth

**Destination enum values for AN-X:**
- Osc Level = 83
- InsAParam3 = 3, InsAParam5 = 5, InsAParam7 = 6
- (more, see `LFO_DESTINATIONS` in ysfc_enums)

Per OSC there are 3 "lane depths" that modulate different destinations:
- OSC rel +67 = mod_lfo_ratio_row1 (for dest1)
- OSC rel +69 = mod_lfo_ratio_row2 (for dest2)
- OSC rel +71 = mod_lfo_ratio_row3 (for dest3)

## 10.9 AWM2 Element Count architecture ★★★★★

### Two synchronized Element Count bytes

The Element Count is stored in TWO byte positions that must always match:
- `blob[+6695]` — sub-blob-relative position
- `blob[+12464]` — engine-header position

Both must be set to the same value (8, 16, 32, 64, or 128).

### Dynamic element array expansion

When Element Count changes, the file size grows linearly:
```
extra_bytes = (EC - 8) * 313
```

Each additional element adds 313 bytes to the engine pool.

### Consequences for editor architecture

- Element Count changes require buffer resize
- Hash/CRC bytes at certain positions update when EC changes
- Multi-Parts mode (Sw_ON_MultiplePartsElements) allows redistribution

### Hash/CRC bytes that scale with EC

```
abs 102, 103, 110, 111, 375, 673, 674, 685, 686
```

These must be filtered when comparing files with different Element Counts.

### Multi-Parts mode

When the user enables `Sw_ON_MultiplePartsElements`, the editor can distribute the EC across multiple Parts. The internal structure remains the same — the EC byte controls total allocation.

---

# 11. Engine data: AWM2 ★★★★★

## 11.1 Element architecture ★★★★★

AWM2 stores 8 elements per Part by default (expandable to 16, 32, 64 or 128).

**Per-element size:** 313 bytes
**Element 1 base (audit abs):** 12469
**Element N base:** 12469 + (N-1) × 313

The engine pool starts at audit abs 12466 with a 3-byte header, then Element 1 at audit abs 12469.

## 11.2 AWM2 Element fields (313 bytes per element) ★★★★★

For the complete per-element field table, see the AWM2 Engine section in REFERENCE.md.

### AMP Level Scaling block (rel 121-143) ★★★★★

| Rel | Field | Encoding | Default |
|---|---|---|---|
| +121 | amp_time_key | c64 | 64 |
| +123 | amp_scaling_center_key | MIDI | 24 |
| +125..+131 | amp_scaling_bp1..bp4 | MIDI | 36, 48, 60, 72 |
| +133..+139 | amp_scaling_offset1..offset4 | c128 | 128 |
| +141 | level_key | c64 | 64 |
| +143 | amp_release_adj | c64 | 64 |

### PEG block (rel 163-195) ★★★★★

| Rel | Field | Encoding | Default |
|---|---|---|---|
| +169 | peg_signature | u8 | 64 |
| +173 | peg_level_hold | c128 | 128 |
| +175..+181 | peg_level_attack..release | c128 | 128 |
| +185 | peg_segment | enum | 4 |
| +187 | peg_time_vel | c64 | 64 |
| +189 | peg_depth_vel | c64 | 64 |
| +191 | peg_curve | enum | 2 |
| +193 | peg_time_key | c64 | 64 |
| +195 | peg_center_key | MIDI | 60 |

### FEG block (rel 219-241) ★★★★★

| Rel | Field | Encoding | Default |
|---|---|---|---|
| +219 | filter_time_attack | u8 | 0 |
| +221..+225 | filter_time_decay1..release | various | various |
| +227..+235 | filter_level_hold..release | c128/u8 | various |
| +237 | filter_feg_depth | c104 | 104 |
| +239 | filter_segment | enum | 4 |
| +241 | filter_time_vel | c64 | 64 |
| +243 | feg_depth_vel | c64 | 64 |

### Filter Level Scaling (rel 247-265) ★★★★★

| Rel | Field | Encoding | Default |
|---|---|---|---|
| +247 | filter_time_key | c64 | 64 |
| +249 | filter_scaling_center_key | MIDI | 24 |
| +251..+257 | filter_scaling_bp1..bp4 | MIDI | 36, 48, 60, 72 |
| +259..+265 | filter_scaling_cutoff_offset1..offset4 | c128 | 128 |

### EQ block (rel 271-281) ★★★★★

| Rel | Field | Encoding | Default |
|---|---|---|---|
| +271 | eq_type | enum | 0 (2-band=0, P.EQ=1, Boost6=2) |
| +273 | eq_q_or_resonance | u8 | 0 |
| +275 | eq_low_freq | u8 | 54 |
| +277 | eq_low_gain | c64 | 64 |
| +279 | eq_high_freq | u8 | 231 |
| +281 | eq_high_gain | c64 | 64 |

### LFO Element Matrix ★★★★★

| Rel | Field | Encoding | Default |
|---|---|---|---|
| +299 | element_lfo_phase_offset | enum 6-step | 0 |
| +301 | element_lfo_dest1_depth | u8 | 127 |
| +303 | element_lfo_dest2_depth | u8 | 127 |
| +305 | element_lfo_dest3_depth | u8 | 127 |

LFO Phase Offset enum: 0=0°, 1=90°, 2=120°, 3=180°, 4=240°, 5=270°.

## 11.3 AWM2 Element [INTERN] bytes

The following positions are firmware constants (verified 100% constant across 408 AWM2 test files):

| Rel | Default | Description |
|---:|---:|---|
| +46 | 40 | Firmware constant |
| +90 | 54 | Firmware constant |
| +148 | 48 | Firmware constant |
| +200 | 108 | Firmware constant |
| +309..+311 | 0 | Padding |
| +312 | 43 (0x2B '+') | Inter-element separator |

### Binary-verified ★★★★★: Extended LFO and Speed bytes

The `extended_lfo` flag at rel +6 determines which LFO Speed byte is active:
- `extended_lfo=0`: rel +289 is active (u8, range 0..63, default 38)
- `extended_lfo=1`: rel +307 is active (u16le, range 0..415, default 60)

Default for Init Normal AWM2 is `extended_lfo=1`.

### AWM2 addressing conventions (3 different bases)

Three different "abs" conventions exist in the project:
- **audit abs** (this document): Element 1 base = 12469
- **AWM2_ELEM_LAYOUT** (serializer): Element 1 base = 12520 (audit_abs − 51)
- **AWM2_ELEM1_BASE** (serializer): 12532 (audit_abs + 63)

Always be explicit about which convention is in use when analyzing binary diffs.

---

# 12. Engine data: FM-X ★★★★★

## 12.1 OP architecture

FM-X has 8 operators (OP1..OP8) plus a Pre-OP block containing PEG, LFO, Algorithm, Feedback and Filter data.

**Pre-OP block:** rel +0..+147 (within FM-X engine pool starting at audit abs 12466)
**OP1 base:** audit abs 12676 (= engine rel +210)
**OP stride:** 123 bytes
**OP count:** 8

## 12.2 FM-X OP Layout (per OP, relative to OP_BASE) ★★★★★

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

## 12.3 FM-X Algorithm + Feedback (Part-level) ★★★★★

| Rel | Field | Encoding | Default |
|---:|---|---|---:|
| +59 | algo | u8 (raw = algo_no − 1) | 69 (=algo 70) |
| +61 | feedback | u8 | 0 |

## 12.4 FM-X 2nd LFO Global (Part-level) ★★★★★

| Rel | Field | Encoding | Default |
|---:|---|---|---:|
| +43 | lfo_wave | enum | 5 |
| +47 | second_lfo_phase | enum | 0 |
| +49 | second_lfo_delay | u8 | 0 |
| +51 | key_on_reset | bool | 1 |
| +63 | second_lfo_extended | bool | 1 |
| +65 | second_lfo_wave_speed | u8 | 50 |
| +69 | op1_fm_harmonics | u8 | 128 |

## 12.5 FM-X OP Mute/Solo — NOT IN BLOB ★★★★★

The OP Mute and Solo buttons in the UI are **UI state**, not persisted in the blob. Toggling them produces 0 diff bytes. The editor does not need to handle these.

---

# 13. Engine data: Drum ★★★★★

**Engine size:** 4963 bytes (4968 in pool with separator).

## 13.1 Drum file-offset convention ★★★★★

The Drum engine uses a different file-offset convention than AWM2/AN-X/FM-X:

| Engine | audit → filoffset conversion | DPFM size (baseline) | Baseline size |
|---|---|---:|---:|
| AWM2 / AN-X / FM-X | filoffset = audit + **687** | ~13162 | ~37166 |
| **Drum** | filoffset = audit + **669** | 17441 | 41427 |

**Verification:** The drumKeySW pattern `01 00 00 00 00 00 01 00` (8 bytes: SW=1, padding, AssignMode=1, padding) appears at 74 positions in the Drum Init Voice baseline, all with stride **68 bytes**. The first instance is at filoffset 13138 = audit 12469 + 669.

All 73 drum keys are traceable via stride 68. Key 1 = filoffset 13138, Key 36 = 15518, Key 73 = 18034.

## 13.2 Drum key architecture

```
DRUM_KEY1_BASE   = 12469   # Part 1 solo, key 1 = C0 (MIDI 12)
DRUM_KEY_STRIDE  = 68      # bytes per drum key
DRUM_KEY_COUNT   = 73      # C0..C6 inclusive (MIDI 12..84)
```

Drum keys area: `[12469:17433]` = 4964 bytes.

## 13.3 Per-Drum-Key fields (rel 0..62) ★★★★★

27 fields per key, all binary-verified.

| Rel | Field | Encoding | Default |
|---|---|---|---|
| 0 | drumKeySW | bool | 1=ON |
| 4 | drumKeyRcvNoteOff | bool | 0=Off |
| 6 | drumKeyAssignMode | enum (0=Single, 1=Multi) | 1 |
| 8 | drumKeyGroup | enum (0=Off, 1-26 = A-Z) | 0 |
| 10..11 | drumKeyWaveformNumber | u16le | 28 |
| 12 | drumKeyPan | c64 | 64 (Center) |
| 14 | drumKeyRandomPan | direct 0..127 | 0 |
| 16 | drumKeyAlternatePan | c64 | 64 |
| 22 | drumKeyConnect | enum (1=InsA, ...) | 1 |
| 26 | drumKeyLevel | direct | 127 |
| 28 | drumKeyLevelVel | c64 | 64 |
| 30 | drumKeyTimeAttack | direct | 0 |
| 32 | drumKeyTimeDecay1 | direct | 96 |
| 34 | drumKeyTimeDecay2 | direct | 80 |
| 36 | drumKeyLevelDecay1 | direct | 127 |
| 38 | drumKeyCoarse | c64 | 64 |
| 40 | drumKeyFine | c64 | 64 |
| 42 | drumKeyPitchVel | c64 | 64 |
| 44..45 | drumKeyFilterCutoff | u16le | 1023 (max) |
| 46 | drumKeyFilterCutoffVel | c64 | 64 |
| 48 | drumKeyFilterResonance | direct | 0 |
| 50..51 | drumKeyHpfCutoff | u16le | 0 |
| 52 | drumKeyEqType | enum (0=2-band, 1=P.EQ, 2=Boost6, 5=Thru) | 0 |
| 56 | drumKeyEqLowFreq | u8 logarithmic (~25 step/oct) | 54 (=62.5 Hz) |
| 58 | drumKeyEqLowGain | c64 ±24 dB | 64 |
| 60 | drumKeyEqHiFreq | u8 logarithmic | 231 (=7.4 kHz) |
| 62 | drumKeyEqHiGain | c64 ±24 dB | 64 |

**EQ Gain encoding:** raw = 64 + UI_dB × (64/24)
**EQ Freq encoding:** u8 logarithmic, ~25 step/octave. 54=62.5 Hz, 156=987 Hz, 231=7.4 kHz, 214=4.88 kHz.

**Non-UI offsets within key (firmware constants):**
- Rel +18 (default 90) — [INTERN]
- Rel +67 (default 64) — [INTERN]
- All other unused offsets are zero-padded [INTERN]

```python
def drum_key_abs(field_name, key_idx):
    """key_idx: 0..72 (C0..C6)"""
    return 12469 + key_idx * 68 + DRUM_KEY[field_name]
```

## 13.4 Drum Part Common ★★★★★

| abs (Part 1) | rel_part | Field | Encoding | Default |
|---|---|---|---|---|
| 6736 | 28 | drumPartElemPanToggle | bool | 1=ON |
| 6802 | 94 | drumPartArpPlayOnly | bool | 0 |
| 6815 | 107 | drumPartMainCategory | enum | 16 |
| 6819 | 111 | drumPartVelLimitLow | direct | 1 |
| 6821 | 113 | drumPartVelLimitHigh | direct | 127 |
| 6823 | 115 | drumPartNoteLimitLow | MIDI | 0 (C-2) |
| 6825 | 117 | drumPartNoteLimitHigh | MIDI | 127 (G8) |
| 6827 | 119 | drumPartVelDepth | c64 | 64 |
| 6829 | 121 | drumPartVelOffset | c64 | 64 |
| 6831 | 123 | drumPartVolume (= EF Part Output) | direct | 100 |
| 6833 | 125 | drumPartPan | c64 | 64 |
| 6835 | 127 | drumPartReverbSend | direct | 0 |
| 6837 | 129 | drumPartVariationSend | direct | 0 |
| 6839 | 131 | drumPartDryLevel | direct | 127 |
| 6847 | 139 | drumPartOutput | enum (0=Main, 9=USB1+2) | 0 |
| 6849 | 141 | drumPartFilterAegAttack | c64 | 64 |
| 6851 | 143 | drumPartFilterAegDecay | c64 | 64 |
| 6853 | 145 | drumPartFilterAegSustain | c64 | 64 |
| 6855 | 147 | drumPartFilterAegRelease | c64 | 64 |
| 6867 | 159 | drumPartFilterCutoff | c64 | 64 |
| 6869 | 161 | drumPartResonance | c64 | 64 |
| 6903 | 195 | drumPartControlGroup | enum | 0 |
| 6913 | 205 | drumPitchBendUpper | c64 | 66 (=+2) |
| 6915 | 207 | drumPitchBendLower | c64 | 62 (=−2) |
| 6917 | 209 | drumDetuneHz | u16le | 128 |
| 6919 | 211 | drumNoteShift | c64 | 64 |
| 6961 | 253 | drumPart2EqType | enum (0=2band, 2=HPF) | 0 |

## 13.5 Drum key collateral bytes ★★★★★

On each Drum-key edit, the following are automatically updated: `[6715, 6716, 6721]`. Added to `DRUM_COLLATERAL_BYTES` for correct round-trip — filtered during diff but must be matched on write.

The ESP UI's "Key" selector only changes navigation, not data. Per-key data is stored correctly in the blob (verified by the same SW=0x01 pattern repeating every 68 bytes).

## 13.6 Drum coverage summary ★★★★★

| Component | Status | UI fields | [INTERN] |
|---|---|---:|---:|
| DRUM_KEY (per key × 73) | ★★★★★ binary-verified | 27 | ~38/key (firmware constants + padding) |
| DRUM_PART_COMMON | ★★★★★ binary-verified | 27 | (rest of Part Common zone is AWM2-shared) |
| Insertions | Shares AWM2 structure | - | - |

**UI coverage for Drum: all known fields verified** ✅

All varying bytes are either UI-mapped or belong to Insertion FX / other universal Part Common fields. 4934 of 4964 drum-key bytes are firmware constants ([INTERN]).

---

# 13.9.1 Insertion Connection Type — binary verified ★★★★★

Y2L Part Common rel `+232` (Part 1 abs `6933`) stores the routing between the two insertion blocks: `0=Parallel`, `1=A_to_B`, `2=B_to_A`. This was isolated with three otherwise-identical MODX M/ESP `Init Normal` Y2L exports on 2026-08-08. It is distinct from per-element `elem_connect`. The classic-source mapping is still unknown and must not be guessed.

# 14. Insertion FX — COMPLETE (57 types) ★★★★★ / ★★★★☆

Insertion FX (InsA and InsB) is engine-independent.

## 14.1 Encoding

```
fxA: abs = PART + 275 (InsA), PART + 332 (InsB)
fxA[0] = lo byte of 7-bit type index
fxA[1] = hi byte of 7-bit type index
TypeIndex = hi * 128 + lo
```

## 14.2 FX_TYPE_INDEX (complete table)

★★★★★ = binary-verified with test file
★★★★☆ = derived from Effect Type List + MSB/LSB formula

```
THRU                 = 0      ★★★★★

REVERB:
SPX HALL             = 130    ★★★★★ (lo=2, hi=1)
SPX ROOM             = 146    ★★★★☆
SPX STAGE            = 176    ★★★★☆
GATED REVERB         = 208    ★★★★☆
REVERSE REVERB       = 216    ★★★★☆

DELAY:
CROSS DELAY          = 256    ★★★★★ (lo=0, hi=2)
TEMPO CROSS DELAY    = 272    ★★★★☆
TEMPO DELAY MONO     = 288    ★★★★☆
TEMPO DELAY STEREO   = 296    ★★★★☆
CONTROL DELAY        = 304    ★★★★☆
DELAY LR             = 320    ★★★★☆
DELAY LCR            = 336    ★★★★☆
ANALOG DELAY RETRO   = 352    ★★★★☆
ANALOG DELAY MODERN  = 360    ★★★★☆

CHORUS:
G CHORUS             = 384    ★★★★☆
2 MODULATOR          = 400    ★★★★☆
SPX CHORUS           = 416    ★★★★☆
SYMPHONIC            = 432    ★★★★★ (lo=48, hi=3)
ENSEMBLE DETUNE      = 448    ★★★★☆

FLANGER:
VCM FLANGER          = 512    ★★★★☆
CONTROL FLANGER      = 520    ★★★★☆
CLASSIC FLANGER      = 528    ★★★★★ (lo=16, hi=4)
TEMPO FLANGER        = 544    ★★★★☆
DYNAMIC FLANGER      = 560    ★★★★☆

PHASER:
VCM PHASER MONO      = 640    ★★★★☆
VCM PHASER STEREO    = 656    ★★★★☆
CONTROL PHASER       = 664    ★★★★☆
TEMPO PHASER         = 672    ★★★★★ (lo=32, hi=5)
DYNAMIC PHASER       = 688    ★★★★☆

TREMOLO & ROTARY:
AUTO PAN             = 768    ★★★★☆
TREMOLO              = 784    ★★★★★ (lo=16, hi=6)
ROTARY SPEAKER 1     = 800    ★★★★☆
ROTARY SPEAKER 2     = 816    ★★★★☆

DISTORTION:
AMP SIMULATOR 1      = 896    ★★★★☆
AMP SIMULATOR 2      = 912    ★★★★☆
COMP DISTORTION      = 928    ★★★★★ (lo=32, hi=7)
COMP DISTORTION DELAY= 944    ★★★★☆
US COMBO             = 960    ★★★★☆
JAZZ COMBO           = 961    ★★★★☆
US HIGH GAIN         = 962    ★★★★☆
BRITISH LEAD         = 963    ★★★★☆
MULTI FX             = 964    ★★★★☆
SMALL STEREO         = 965    ★★★★☆
BRITISH COMBO        = 966    ★★★★☆
BRITISH LEGEND       = 967    ★★★★☆

COMPRESSOR:
VCM COMPRESSOR 376   = 1024   ★★★★☆
CLASSIC COMPRESSOR   = 1040   ★★★★★ (lo=16, hi=8)
MULTI BAND COMP      = 1056   ★★★★☆
UNI COMP DOWN        = 1072   ★★★★☆
UNI COMP UP          = 1080   ★★★★☆
PARALLEL COMP        = 1088   ★★★★☆

WAH:
VCM AUTO WAH         = 1280   ★★★★★ (lo=0, hi=10)

LO-FI:
NOISY                = 1424   ★★★★★ (lo=16, hi=11)

TECH:
SLICE                = 1616   ★★★★★ (lo=80, hi=12)

MISC:
PRESENCE             = 1672   ★★★★★ (lo=8, hi=13)
WAVE FOLDER          = 1704   ★★★★★ (lo=40, hi=13)
```

**Helpers:**

```python
def fx_type_bytes(name):
    """Returns (lo, hi) for an InsertionFX name."""
    idx = FX_TYPE_INDEX.get(name.upper(), 0)
    return (idx & 0x7F, (idx >> 7) & 0x7F)

def fx_name_from_bytes(lo, hi):
    """Returns FX name from (lo, hi) bytes."""
    return FX_INDEX_TO_NAME.get(hi * 128 + lo, f'UNKNOWN({hi*128+lo})')
```

## 14.3 LFO Speed encoding (all FX) ★★★★★

`raw = round(Hz × 23.7045)`

Data points: 0.46 Hz→11, 0.80→19, 1.09→26, 1.30→31, 1.60→38, 1.98→47.

## 14.4 Symphonic + Classic Flanger parameters (specific)

**SYMPHONIC (12/12 ★★★★★):**

| fxA+ | Field | Encoding | Default |
|---|---|---|---|
| 4 | LFO Speed | raw=round(Hz×23.7) | 11 (=0.46 Hz) |
| 6 | LFO Depth | direct | 25 |
| 8 | Delay Offset | table index | 1 (≈0 ms) |
| 14 | EQ Low Freq | table index | 22 |
| 16 | EQ Low Gain | c64 | 64 |
| 18 | EQ High Freq | table index | 48 |
| 20 | EQ High Gain | c64 | 64 |
| 22 | Dry/Wet | direct | 64 |
| 24 | EQ Mid Freq | table index | 38 |
| 26 | EQ Mid Gain | c64 | 64 |
| 28 | EQ Mid Width | table index | 7 |

**CLASSIC FLANGER (16/16 ★★★★★):**

Like Symphonic + three specific fields:

| fxA+ | Field | Encoding | Default |
|---|---|---|---|
| 10 | Delay Offset | table index | 24 (=0.65 ms) |
| 12 | Feedback | raw = percent+100 | 151 (=51%) |
| 30 | Mod Phase | raw = phase_idx × 2 | (180°=16) |
| 32 | FB High Damp | raw = value × 10 | 9 (=0.9) |
| 34 | Analog Feel | direct | 0 |

(The remaining 49 FX types use the same 22-param template as Reverb/Variation FX in the Common area, with different interpretations per Type.)

---

# 15. Smart Morph ★★★★★

Smart Morph is not a parameter but a complete file-format extension.

## 15.1 Detection ★★★★★

Two separate indicators (yielding the same answer):

```python
def is_smart_morph(blob, file_data):
    # Indicator 1: byte in performance blob
    if blob[56] == 1:
        return True
    # Indicator 2: DSOM chunk in container
    return b'DSOM' in file_data[64:200]  # in directory
```

## 15.2 Container extension

Smart Morph adds **4 chunks** to the Y2L file:

| Chunk | Size (typical) | Function |
|---|---|---|
| ESPG | 71 b | Edit Smart Performance Group (header) |
| ESOM | 71 b | Edit Smart Morph (metadata) |
| DSPG | 794 b | Data Smart Performance Group |
| **DSOM** | **~900 KB** | Data Smart Morph — embedded YAMAHA-SOM file |

## 15.3 Performance blob changes when Smart Morph is enabled

Besides `blob[+56] = 1`:

| abs | NORMAL | SmartMorph | Interpretation |
|---|---|---|---|
| +56 | 0 | 1 | Smart Morph enable ★★★★★ |
| +66 | 0 | 16 | Side effect (correlates with SM activation) ★★★★★ |
| +728..+735 | 0 | u16le array | Index/pointer to morph keyframes ★★★★☆ |

## 15.4 DSOM payload structure

```
DSOM chunk payload:
  +0    u32be: count = 1
  +4    'Data' (4 bytes)
  +8    u32be: inner_size
  +12   embedded YAMAHA-SOM file
```

## 15.5 Embedded YAMAHA-SOM format ★★★☆☆

A separate format, not standard YSFC:

```
+0..11   "YAMAHA-SOM\0"  magic
+11..15  ?
+16..32  "2.1.0\0..."    version
+32..48  ?
+48..52  "FIRM"          (firmware identifier?)
+52..56  ?
+56..60  "MAPI"          (MIDI mapping?)
+60..    ... custom data ...
```

**Not mapped yet.** Separate reverse-engineering project.

## 15.6 Editor strategy (Opaque blob)

1. Detect Smart Morph at load
2. Show warning: "Smart Morph data preserved — engine parameters editable, but not morph keyframes"
3. Allow editing of regular parameters (Performance/Part fields)
4. On save: copy DSOM/ESPG/ESOM/DSPG **verbatim**, modify only the performance blob

This doesn't close the door for full Smart Morph support later when YAMAHA-SOM is reverse-engineered.

---

# 16. UI elements NOT IN BLOB ★★★★★

The following UI elements exist but are NOT saved in the performance blob:

## 16.1 Hardware Events (RcvSw)

- **Pitch Bend** — hardware-global
- **Ch. After Touch** — hardware-global
- **Poly. After Touch** — hardware-global

## 16.2 UI state

- **Performance Favorite (Star)** — stored separately (DFVT chunk)
- **MS Sequencer Lane Select** — UI state, not saved
- **OP Mute / OP Solo** (FM-X) — real-time state
- **Audio In Mute / Solo** — UI state

## 16.3 Hardware-global settings

- **Global Tuning**
- **MC Flag**
- **System FX**
- **Transmit Switch**

## 16.4 Hard-coded in firmware

- Scene CC (= 92)
- Super Knob CC (= 95)
- Footswitch Assign (= Arp Sw)

---

# 17. Modified / Noise flags ★★★★★

Bytes that change on save without representing parameter data. **Filtered during diff. Must be preserved on write.**

| Position | Function |
|---|---|
| `file[63]` | Save counter (outer container) |
| `file[399]` | Save counter (copy inside EPFM) |
| `blob[+22]` | Sub-blob 1 edit state (part of timestamp) |
| `blob[+23]`, `blob[+24]` | Sub-blob 1 (Common) timestamp/edit state |
| `blob[+66]` | Common-area side-effect flag |
| `blob[+232]`, `blob[+234]` | Common-area edit flags (parallel, 1→0) |
| `blob[+358]` | Arp/FX edit counter (2→0 in 25+ tests) |
| `blob[+376]` | Reverb edit state flag (coexists with Reverb Category) |
| `blob[+654]` | Multi-trigger side effect (9+ unrelated tests) |
| `blob[+6724]`, `blob[+6725]` | Sub-blob 2 (Part 1) timestamp |
| `blob[+7167]`, `blob[+7168]` | Arp-related edit flags (250→0 / 10→0) |
| `blob[+7419]` | Scene edit counter (per-Scene edit triggers 0→1) |
| Sub-blob N: +23, +24 | Per-part edit state (pattern repeats) |
| **CA+17** | MODX-internal byte in each CA slot |
| **Drum [6715, 6716, 6721]** | Drum-key collateral bytes |

```python
NOISE_BLOB = {
    22, 23, 24, 66,            # Sub-blob 1 timestamp + edit flags
    232, 234, 358, 376, 654,   # Common-area side-effect flags
    6724, 6725,                # Sub-blob 2 timestamp
    7167, 7168, 7419,          # Arp/Scene edit counters
}
NOISE_FILE = {63, 399}
DRUM_COLLATERAL = {6715, 6716, 6721}
```

⚠️ **Note:** Some NOISE offsets coexist with real parameters:
- `blob[+376]` = Reverb Category (real param) BUT also triggered as side effect
- `blob[+7419]` = per-Scene edit counter

Editor: write the correct UI value — MODX handles edit-flag updates automatically.

---

# 18. Remaining unmapped regions

~50 nz (non-zero) bytes are "really unknown" (after this analysis). Another ~201 nz bytes are confirmed OPAQUE — firmware-constant data not exposed in the UI.

## 18.1 OPAQUE internal regions (~201 nz bytes)

**Defining properties:**
- 0 test files in the 1626-file corpus modify these bytes
- Bit-for-bit identical across all 4 engines (AWM2/Drum/FMX/ANX)
- Contains repeating block structures (CA trailers, u16le patterns)

| Region | Size | nz | Engine-agnostic |
|---|---:|---:|:---:|
| `[487:525]` | 38 b | 17 | ✓ |
| `[732:766]` | 34 b | 14 | ✓ |
| `[788:840]` | 52 b | 17 | ✓ |
| `[5843:5893]` | 50 b | 21 | ✓ |
| `[6971:6983]` | 12 b | 4 | ✓ |
| `[7275:7290]` | 15 b | 7 | ✓ |
| Stride-106 Group 1 `[840:1710]` | 870 b | ~80 | ✓ |
| Stride-106 Group 2 `[3186:4043]` | 857 b | ~70 | ✓ |
| Stride-106 Group 3 `[4083:4943]` | 860 b | ~70 | ✓ |
| Stride-106 Group 4 `[4943:5826]` | 883 b | ~70 | ✓ |

**Practical consequence:** Editor MUST preserve these byte-for-byte. Do NOT try to interpret or modify them — this is Yamaha-internal firmware data.

```python
OPAQUE_INTERNAL_REGIONS = [
    (487, 525), (732, 766), (788, 840),
    (5843, 5893), (6971, 6983), (7275, 7290),
]
STRIDE_106_GROUPS = [
    (840, 1710), (3186, 4043), (4083, 4943),
    (4943, 5826), (5942, 6700),  # Group 5: Scene/Part-related
]
```

## 18.2 Stride-106 Group 5 — Scene/Part-related

Distinct from Groups 1-4: **updated automatically on multi-part write**. Specifically `blob[+6695]` (max active part) lies in Group 5.

Other bytes in Group 5 reflect internal state of part arrangement and should be copied verbatim without interpretation.

## 18.3 Truly unknown (~50 nz bytes)

Bytes that are neither mapped UI fields nor confirmed OPAQUE — potential future UI fields that need dedicated tests:

| Region | nz | Location |
|---|---:|---|
| `[70:104]` remaining | ~14 | Perf-level toggles (3 of 17 mapped) |
| `[130:153]` (besides 152=Ribbon CC) | 8 | Between Common toggles and Hardware Ribbon |
| `[232:246]` | 4 | Small Common region |
| `[357:377]` (besides NOISE 358, 376) | 4 | Between Master FX and Reverb FX |
| `[4043:4063]` (besides 4044) | 7 | Between Stride-106 groups |
| `[12453:12466]` (besides 12464-65) | 1 | Pre-engine padding |
| Scattered individual bytes | ~12 | Between known fields |

## 18.4 Unmapped toggle bytes

abs **32, 36** — 2 toggles where UI function is not definitively identified.

## 18.5 Byte coverage summary

```
Total bytes (ANX Init Base):     13150
Non-zero bytes:                   3766
UI-mapped (★★★★★/★★★★☆):       ~2523     (67.0% of nz)
Structurally mapped:             ~1041     (27.7% of nz)
OPAQUE (firmware-constant):       ~201     ( 5.3% of nz)
Truly unknown:                    ~50      ( 1.3% of nz)
```

**Practical implication:** ~98.7% non-zero coverage achieved. The remaining 1.3% is preserved verbatim — no functionality loss for the editor.

## 18.6 Recommended test files for full parameter coverage

Five dedicated tests would eliminate the last unknown bytes:

1. `TEST-PERF-TOGGLES-71-91.Y2L` — sequential toggles 71-91
2. `TEST-COMMON-131-152.Y2L` — Common bytes between 131-152
3. `TEST-PERF-EFX-EXTRA.Y2L` — bytes between Master FX and Reverb FX
4. `TEST-MS-LANE-INTERFACE.Y2L` — abs 4044 vs 8929 Lane interface
5. `TEST-CONTROL-NAMES-238.Y2L` — Common abs 232, 234, 238

The remaining ~196 bytes (Stride-106 + OPAQUE) **are confirmed not exposed** and need no further testing.

---

# 19. Helper functions (serializer API)

## 19.1 Address calculation ★★★★★

```python
SUBBLOB_HEADER_SIZE  = 27
SUBBLOB_COMMON_SIZE  = 6701
SUBBLOB_DEFAULT_SIZE = 5765
PART1_SUBBLOB_START  = 6701

def subblob_start(part_idx):       # part_idx = 0..15
    return 6701 + part_idx * 5765

def payload_start(part_idx):
    return subblob_start(part_idx) + 27

def part_field_abs(part_idx, payload_offset):
    return payload_start(part_idx) + payload_offset

# Volume: payload_offset=103, rel_part=130, Part 1 abs=6831
```

## 19.2 Engine pool ★★★★★

```python
ENGINE_POOL_SEP_SIZE = 5
ENGINE_DATA_SIZE = {
    'ANX':  684,
    'AWM2': 2503,
    'FMX':  1143,
    'Drum': 4963,
}

def get_engine_pool_start(num_parts):
    return 6701 + num_parts * 5765

def get_engine_addr(num_parts, part_engines, part_index):
    pool_start = get_engine_pool_start(num_parts)
    offset = 0
    for i in range(part_index):
        offset += ENGINE_DATA_SIZE[part_engines[i]] + 5
    return pool_start + offset

def parse_engine_type_from_name(blob, sub_blob_start):
    name_bytes = bytes(blob[sub_blob_start + 4 : sub_blob_start + 25])
    name = name_bytes.decode('latin-1', errors='replace')
    if '(AN-X)' in name: return 'ANX'
    if '(AWM2)' in name: return 'AWM2'
    if '(FM-X)' in name: return 'FMX'
    if 'Drum'   in name: return 'Drum'   # Note: without parentheses
    return 'Unknown'
```

## 19.3 AWM2 Element ★★★★★

```python
AWM2_HEADER_SIZE    = 27
AWM2_ELEMENT_STRIDE = 313
AWM2_ELEMENT_COUNT  = 8

def get_awm2_element_offset(element_idx):
    return 27 + element_idx * 313

def get_awm2_element_addr(engine_start_abs, element_idx):
    return engine_start_abs + get_awm2_element_offset(element_idx)
```

## 19.4 FM-X OP ★★★★★

```python
FMX_OP1_BASE  = 12676   # Part 1, solo
FMX_OP_STRIDE = 123

def fmx_op_base(op_idx, part_idx=0):
    """op_idx = 0..7"""
    return FMX_OP1_BASE + op_idx * FMX_OP_STRIDE + (part_idx * 5765)
```

## 19.5 AN-X OSC ★★★★★

```python
ANX_OSC1_BASE  = 12626
ANX_OSC_STRIDE = 125

def anx_osc_base(osc_idx, part_idx=0):
    """osc_idx = 0..2"""
    return ANX_OSC1_BASE + osc_idx * ANX_OSC_STRIDE + (part_idx * 5765)
```

## 19.6 Drum key ★★★★★

```python
DRUM_KEY1_BASE   = 12469
DRUM_KEY_STRIDE  = 68
DRUM_KEY_COUNT   = 73

def drum_key_abs(field_name, key_idx):
    """key_idx: 0..72 (C0..C6)"""
    return 12469 + key_idx * 68 + DRUM_KEY[field_name]
```

## 19.7 Receive Switch ★★★★★

```python
RCV_SWITCH_REL_OFFSET = 43
RCV_SWITCH_BLOCK_SIZE = 28

def get_rcv_switch_addr(sub_blob_start, switch_pos):
    return sub_blob_start + 43 + switch_pos

def get_rcv_switch_addr_by_name(sub_blob_start, name):
    return sub_blob_start + 43 + RCV_SWITCH_POS[name]
```

## 19.8 CA structures ★★★★★

```python
CA_STRIDE       = 22
CA_SLOT_COUNT   = 32
CA_TRAILER_SIZE = 24
CA_PERF_BASE    = 2451
CA_PART_BASE    = 8220
CA_PERF_TRAILER = 3155
CA_PART_TRAILER = 8924

def ca_slot_addr(scope, slot_idx):
    """scope: 'perf' or 'part'; slot_idx: 0..31"""
    base = 2451 if scope == 'perf' else 8220
    return base + slot_idx * 22
```

## 19.9 Scene ★★★★★

```python
SCENE_STRUCT1_BASE   = 1710
SCENE_STRUCT1_STRIDE = 71
SCENE_STRUCT2_BASE   = 7421
SCENE_STRUCT2_STRIDE = 84
SCENE_COUNT          = 8

def scene_struct1_abs(field_name, scene_idx):
    return 1710 + scene_idx * 71 + SCENE_STRUCT1_FIELDS[field_name]

def scene_struct2_abs(field_name, scene_idx):
    return 7421 + scene_idx * 84 + SCENE_STRUCT2_FIELDS[field_name]

def get_scene_superknob_addr(scene):
    """scene = 1..8"""
    return 184 + (scene - 1) * 2

def get_sk_link_addr(scene, mirror=False):
    """scene = 1..8"""
    base = 1717 if mirror else 40
    return base + (scene - 1)
```

## 19.10 Names ★★★★★

```python
COMMON_ASSIGN_NAMES_BASE   = 2279
COMMON_ASSIGN_NAMES_STRIDE = 21
COMMON_ASSIGN_NAMES_LEN    = 16
PART_ASSIGN_NAMES_BASE     = 8048
PART_ASSIGN_NAMES_STRIDE   = 21
PART_ASSIGN_NAMES_LEN      = 16

def get_assign_name_addr(slot, scope='common'):
    """slot: 1..8"""
    base = 2279 if scope == 'common' else 8048
    return base + 1 + (slot - 1) * 21
```

## 19.11 FX utilities ★★★★★

```python
def fx_type_bytes(name):
    idx = FX_TYPE_INDEX.get(name.upper(), 0)
    return (idx & 0x7F, (idx >> 7) & 0x7F)

def fx_name_from_bytes(lo, hi):
    return FX_INDEX_TO_NAME.get(hi * 128 + lo, f'UNKNOWN({hi*128+lo})')
```

## 19.12 Structural metadata bytes ★★★★★

During both read and write of a performance, these bytes must be correct.

```python
ENGINE_TYPE_BYTE = 6700  # 0=AWM2, 1=Drum, 2=FMX, 3=ANX
ENGINE_TYPE_VALUES = {0: 'AWM2', 1: 'Drum', 2: 'FMX', 3: 'ANX'}
ENGINE_TYPE_BY_NAME = {v: k for k, v in ENGINE_TYPE_VALUES.items()}

MAX_ACTIVE_PART_BYTE = 6695  # 1..16, highest active part number

def get_engine_type_byte(blob):
    return ENGINE_TYPE_VALUES.get(blob[ENGINE_TYPE_BYTE], 'Unknown')

def get_max_active_part(blob):
    return blob[MAX_ACTIVE_PART_BYTE]

def set_engine_type_byte(blob, engine_name):
    """engine_name: 'AWM2' | 'Drum' | 'FMX' | 'ANX'"""
    blob[ENGINE_TYPE_BYTE] = ENGINE_TYPE_BY_NAME[engine_name]

def set_max_active_part(blob, max_part_idx):
    """max_part_idx: 1..16 (HIGHEST active part number)"""
    blob[MAX_ACTIVE_PART_BYTE] = max_part_idx

def validate_engine_consistency(blob):
    """Verify that engine byte matches sub-blob 2 name suffix."""
    engine_byte_name = get_engine_type_byte(blob)
    engine_name_str = parse_engine_type_from_name(blob, 6701)
    if engine_name_str == 'Unknown':
        return True, f"OK (byte only): {engine_byte_name}"
    if engine_byte_name == engine_name_str:
        return True, f"OK: {engine_byte_name}"
    return False, f"Mismatch: byte says {engine_byte_name}, name says {engine_name_str}"
```

## 19.13 AWM2 Control Source ★★★★☆

```python
AWM2_CONTROL_SOURCE_BASE       = 7300   # Part 1, abs
AWM2_CONTROL_SOURCE_STRIDE     = 18
AWM2_CONTROL_SOURCE_SLOT_COUNT = 4

def get_awm2_control_source_addr(slot_idx, field_rel, sub_blob_start=6701):
    """slot_idx: 0..3, field_rel: rel-offset from slot base."""
    part_offset = sub_blob_start - 6701
    slot_base = AWM2_CONTROL_SOURCE_BASE + slot_idx * AWM2_CONTROL_SOURCE_STRIDE
    return slot_base + field_rel + part_offset
```

## 19.14 Motion Sequencer fields ★★★★★

The UI view "Motion Seq > Common / Lane" has TWO sections with 6 fields each:

**"Common" (Performance Common area, applies to all parts):**
```python
COMMON_MOTION_SEQ = dict(
    swing=100,        # u16le c128, default 128
    unit=102,         # u8 enum (3=1/16 default)
    amplitude=656,    # u16le c128, default 128
    shape=658,        # u16le c64, default 64
    smooth=660,       # u16le c128, default 128
    random=662,       # u16le c128, default 128
)
```

**"Part" (Part Common area, applies to all 4 Lanes in this Part):**
```python
PART_MOTION_SEQ_REL = dict(
    swing_rel=186,     # u16le c128 (abs 6887 = 6701 + 186)
    amplitude_rel=188, # u16le c128
    shape_rel=190,     # u16le c64
    smooth_rel=192,    # u16le c128
    random_rel=194,    # u8 direct 0..100
    unit_rel=396,      # u8 enum (abs 7097 = 6701 + 396)
)

def get_part_motion_seq_addr(part_idx, field):
    """Returns abs address for Part N's Motion Seq Part field."""
    sub_blob_start = 6701 + (part_idx - 1) * 5765
    return sub_blob_start + PART_MOTION_SEQ_REL[f'{field}_rel']
```

**The View Lane dropdown (1-4)** in the UI only controls which Lane is shown in the Edit Part Sequencer view — it does **NOT** change which bytes are affected by the Common/Part fields above. Both sections are Part-level (or Performance-level for Common), not per-Lane.

**Per-Lane data** (Lane Switch, Lane Velocity Limits, MS Grid, Pulse A/B, etc.) lies in the sub-blob 2 Lane data area [8929+, stride 884 per Lane]:
- Lane 1 LaneSwitch @ blob[+8929]
- Lane 2 LaneSwitch @ blob[+9813]
- Lane 3 LaneSwitch @ blob[+10697]
- Lane 4 LaneSwitch @ blob[+11581]

**Backward compatibility:** `LANE1_COMMON` is an alias for `COMMON_MOTION_SEQ`.

## 19.15 Multi-part pointer API ★★★★★

```python
SUBBLOB_POINTER_REL = (5763, 5764)
ENGINE_MAGIC_BYTES  = {'ANX': 110, 'AWM2': 8, 'FMX': 82, 'Drum': 73}
ENGINE_MAGIC_TO_NAME = {v: k for k, v in ENGINE_MAGIC_BYTES.items()}

def get_subblob_pointer_pos(part_idx):
    """Position for Part N's pointer (1-indexed)."""
    sub_blob_start = 6701 + (part_idx - 1) * 5765
    return (sub_blob_start + 5763, sub_blob_start + 5764)

def read_subblob_pointer(blob, part_idx):
    """Returns (is_last, next_or_part1_engine)."""
    pos0, pos1 = get_subblob_pointer_pos(part_idx)
    marker = blob[pos0]
    if marker == 1:
        return False, ENGINE_TYPE_VALUES[blob[pos1]]
    return True, ENGINE_MAGIC_TO_NAME[marker]

def write_subblob_pointer_continuation(blob, part_idx, next_engine_name):
    pos0, pos1 = get_subblob_pointer_pos(part_idx)
    blob[pos0] = 1
    blob[pos1] = ENGINE_TYPE_BY_NAME[next_engine_name]

def write_subblob_pointer_last(blob, part_idx, part1_engine_name):
    """Note: part1_engine_name = first engine in pool (= Part 1's engine)."""
    pos0, pos1 = get_subblob_pointer_pos(part_idx)
    blob[pos0] = ENGINE_MAGIC_BYTES[part1_engine_name]
    blob[pos1] = 0

def get_entr_bitmask(max_active_part):
    """(1 << N) - 1 where N = max_active_part."""
    return (1 << max_active_part) - 1
```

## 19.16 Opaque regions registry ★★★★★

```python
# Regions that MUST be preserved byte-for-byte. 0 test files modify them.
OPAQUE_INTERNAL_REGIONS = [
    (487, 525),    # 38 b
    (732, 766),    # 34 b — 14 × u16le firmware-constant
    (788, 840),    # 52 b — CA-like + 14b end-marker
    (5843, 5893),  # 50 b
    (6971, 6983),  # 12 b — Part Common
    (7275, 7290),  # 15 b — Part Common after Tx Rx Channel
]

STRIDE_106_GROUPS = [
    (840, 1710),   # Group 1 — opaque
    (3186, 4043),  # Group 2 — opaque
    (4083, 4943),  # Group 3 — opaque
    (4943, 5826),  # Group 4 — opaque
    (5942, 6700),  # Group 5 — Scene/Part-related
]

def is_opaque_byte(offset):
    """Returns True if offset is in an opaque region."""
    for start, end in OPAQUE_INTERNAL_REGIONS:
        if start <= offset < end:
            return True
    for start, end, *_ in STRIDE_106_GROUPS[:4]:  # Groups 1-4 are fully opaque
        if start <= offset < end:
            return True
    return False
```

## 19.17 File-level constants & save counter ★★★★★

```python
FILE_SAVE_COUNTER_POS = 60         # u32be, increments +1 per save
FILE_INNER_SAVE_COUNTER_POS = 396  # u32be, = file[60:64] - 1
CHUNK_CATALOG_POS = 64             # 6 × 8 bytes
CHUNK_NAMES = ['EPFM', 'ESYS', 'EFVT', 'DPFM', 'DSYS', 'DFVT']

def read_save_counter(file_data):
    """Returns u32be save counter from file[60:64]."""
    import struct
    return struct.unpack('>I', file_data[60:64])[0]

def write_save_counter(file_data, value):
    """Write save counter to file[60:64] AND inner counter file[396:400]=value-1."""
    import struct
    file_data[60:64] = struct.pack('>I', value)
    file_data[396:400] = struct.pack('>I', max(0, value - 1))
```

## 19.18 EPFM Entr-record builder ★★★★★

```python
ENTR_PART_BITMASK_OFFSET = 18      # rel Entr payload start
ENTR_INNER_COUNTER_OFFSET = 23

def build_entr_payload(perf_name, part1_name, max_active_part,
                       save_counter, dpfm_size):
    import struct
    name_str = f"256:{perf_name}:{part1_name}\0"
    name_bytes = name_str.encode('latin-1')
    payload = bytearray(27 + len(name_bytes))
    payload[0:4]   = struct.pack('>I', dpfm_size)
    payload[4:8]   = struct.pack('>I', 0x0000000C)
    payload[8:12]  = struct.pack('>I', 0x00400000)
    payload[12:16] = struct.pack('>I', 0x00000004)
    payload[16:18] = b'\x02\x00'
    payload[18]    = get_entr_bitmask(max_active_part)  # (1<<N)-1
    payload[19:23] = b'\x00\x00\x00\x00'
    payload[23:27] = struct.pack('>I', save_counter - 1)
    payload[27:]   = name_bytes
    return payload
```

---

# 20. Verification status and test file registry

## 20.1 Summary per engine

| Engine / Section | Status | Verified |
|---|---|---|
| Container (EPFM/DPFM/ESYS/EFVT/DSYS/DFVT) | COMPLETE | ★★★★★ |
| Sub-blob universal model | COMPLETE | ★★★★★ (all 16 parts × all 4 engines) |
| Engine-pool structure | COMPLETE | ★★★★★ |
| Performance Common (~30 fields) | COMPLETE | ★★★★★ |
| Part Common (~25 fields) | COMPLETE | ★★★★★ |
| Receive Switch (26/26) | COMPLETE | ★★★★★ (except pos 22 = INTERN) |
| Common Assigns (CA_PERF + CA_PART, 32 slots) | COMPLETE | ★★★★★ |
| Scene Struct 1 (9 fields × 8 scenes) | COMPLETE | ★★★★★ |
| Scene Struct 2 (11 fields × 8 scenes) | COMPLETE | ★★★★★ (hypothesis: active-part) |
| Master EQ (15 fields) | COMPLETE | 13 × ★★★★★ + 2 × ★★★★☆ (LoMid/HiMid Freq) |
| Reverb FX (26 fields) | COMPLETE | ★★★★★ |
| Variation FX (28 fields) | COMPLETE | ★★★★★ |
| Master FX (26 fields) | COMPLETE | ★★★★★ |
| Common CC + Hardware Ribbon | COMPLETE | ★★★★★ |
| Audio In + Envelope Follower | COMPLETE | ★★★★★ |
| Per-Part 3-band EQ (7 fields) | COMPLETE | ★★★★★ |
| Per-Part 2-band EQ (9 fields) | COMPLETE | ★★★★★ |
| AN-X engine (684 b) | COMPLETE | ★★★★★ mapped & verified (171 fields + 458 [INTERN]) |
| AWM2 engine (2503 b) | COMPLETE | ★★★★★ mapped & verified (128 fields + 8 [INTERN]) |
| FM-X engine (1143 b) | COMPLETE | ★★★★★ mapped & verified (141 fields + 863 [INTERN]) |
| Drum engine (4963 b) | COMPLETE | ★★★★★ mapped & verified (27 fields × 73 keys + 27 Part Common) |
| Multi/GM 16-part files | COMPLETE | ★★★★★ verified DPFM=141536 bytes |
| Insertion FX (57 types) | COMPLETE | 12 × ★★★★★ + 45 × ★★★★☆ |
| Smart Morph | DETECTION COMPLETE | ★★★★★ (DSOM payload not mapped) |
| MS Sequencer (4 lanes) | COMPLETE | ★★★★★ Lane base + 29 fields/lane |

## 20.2 List of fields claimed complete but without dedicated test reference

Areas that are documented but where no clean test file was found in the corpus. Candidates for future verification:

- **Master EQ Lo Mid Freq (570)** — predicted from stride
- **Master EQ Hi Mid Freq (582)** — predicted from stride
- **FS Assign destination encoding (abs 164)** — ★★★☆☆
- **AN-X OSC2 / OSC3 EG fields** — stride-extrapolated from OSC1, not directly tested per-field
- **AN-X Filter 2 fields** — stride-extrapolated from Filter 1
- **FMX LFO Destinations 71, 73, 76** — UI-deduced from enum position
- **CA Sources 2-7, 11-15** — only PB/MW/Knob1-3 binary-verified
- **AWM2 Element 2-8** — stride-verified but not per-field per element

Practical consequence: these fields follow established patterns and can be used in the editor but should be marked ★★★★☆ until explicitly verified.

## 20.3 Statistics from test corpus

```
Total Y2L test files analyzed:        2010+
Clean 1-byte diff tests:               385
2-byte (u16le) diff tests:             293
Multi-byte diff tests (params + side effects):  ~700
Empty/identical tests:                 ~248

AWM2 corpus:    408 files (full observed coverage)
AN-X corpus:    799 files (full observed coverage)
FM-X corpus:    425 files (full observed coverage)
Drum corpus:     84 files (full observed coverage)
Multi/GM:         1 file  (baseline verified)

Unique offsets binary-verified with ≥1 clean test:  ~200 (u8) + ~21 (u16le) = 221
Unique offsets verified with ≥3 independent tests:  ~25
Offset with max test count (Detune):  37 independent tests
```

## 20.4 Patch Editor — implementation status

Recommended architecture:

1. **Read performance** from Y2L → parse via EPFM directory → DPFM → blob
2. **Decode parameters** via offset tables + encoding functions
3. **UI layer** per engine/section (FM-X OP, AWM2 Elem, AN-X OSC, Drum-key)
4. **Encode + write** changed bytes back to blob
5. **Export** new Y2L via `buildYSFC` function

**Editor read path needs:**
- Detect number of sub-blobs (search for `00 00 00 15 "Init …"` headers)
- For Part N ≥ 2: use `part_field_abs(N-1, payload_offset)`
- Engine data always lies in the last sub-blob (solo) or in the engine pool (multi-part)

**Editor write path needs:**
- When editing Part N: ensure that sub-blob N exists
- Create empty sub-blob placeholders for all parts up to N
- Engine data is moved to the last sub-blob / engine pool

**Preserved data (preserve verbatim):**
- ESYS/DSYS/EFVT/DFVT chunks (engine-independent)
- Smart Morph chunks (ESPG/ESOM/DSPG/DSOM)
- Stride-106 Zone/Control blocks (Common region)
- Region [732:766] (14 × u16le)
- Region [788:840], [5843:5893], [7300:7419] (not UI-mapped)
- Modified-flag bytes (copied from source on merge)
- CA+17 byte in each CA slot (MODX-internal)
- Drum collateral bytes [6715, 6716, 6721]

---

# 21. Lessons learned and process

## 21.1 UI aliasing (one byte → multiple UI labels)

Some bytes have two UI labels depending on the UI view:

| Byte | UI Label 1 | UI Label 2 |
|---|---|---|
| `blob[+68]` | Performance Volume | EF Master Output |
| `blob[+6831]` | Part Volume | EF Part Output |
| `blob[+766]` | Audio In Volume | EF AD Output Level |

The editor must present both labels in their respective UI sections but understand that they write to the same physical byte.

## 21.2 Side-effect flags

Some bytes are changed by many unrelated UI operations:

| Byte | Behavior |
|---|---|
| `blob[+66]` | Common-area side-effect flag — changes on many Common edits |
| `blob[+654]` | Multi-trigger — at least 9 different edit types change this |
| `blob[+23/24]`, sub-blob `+23/24` per N | Timestamp/edit counter |

These ARE NOISE — should be filtered during diff analysis, but must be written correctly on round-trip.

## 21.3 Verification methodology

A controlled test (change X in UI, export, diff) is the gold standard. At least 3-4 data points are needed for encoding certainty (center=64 vs center=128 vs direct, etc.). Statistical correlation across the corpus without targeted tests can produce false positives.

Star ratings are assigned only when evidence exists:
- **★★★★★** = binary-verified with specific test file
- **★★★★☆** = derived from official source data or established pattern
- **★★★☆☆** = predicted without empirical confirmation
- **[INTERN]** = MODX-internal, not user-editable (ignored during editing)
- **[STRUKT]** = structurally characterized but UI function not identified

## 21.4 Address convention discipline

Three different "abs" conventions exist in the project — keep them distinct:

- **audit abs** (this document, parameter rating file): Element 1 base = 12469
- **AWM2_ELEM_LAYOUT** (serializer): Element 1 base = 12520 (= audit_abs − 51)
- **AWM2_ELEM1_BASE** (serializer): 12532 (= audit_abs + 63)

For Drum, the filoffset-to-audit conversion is also different:
- AWM2 / AN-X / FM-X: filoffset = audit + 687
- Drum: filoffset = audit + 669

Always be explicit about which convention is in use when analyzing binary diffs or reading parameter documentation.

## 21.5 Engine-specific divergence

Most byte positions in Part Common have the same meaning across all 4 engines. The exceptions are:

- **Drum Part Common rel +144/+146** are filter fields, not AEG offsets
- **Drum file-offset convention** differs (+669 vs +687)
- **FM-X has Pre-OP fields** at engine-pool rel +0..+147 (not present in other engines)
- **AN-X has 5 routing matrices** in the engine pool (200 bytes, [INTERN])

When implementing an editor, dispatch on engine_type before interpreting these regions.

---

# Appendix A: Step 1 — Header verification ★★★★★

*Added 2026-05-20. This appendix is the result of an isolated verification
pass of the Y2L/Y2U header against arachsys/montage-documented
YSFC 4.0.5 (Montage classic) and 5.0.1 (MODX classic). Sections 1.1–1.7
in the main document were written prior to this verification; this
appendix takes precedence in case of any conflicts.*

## A.1 Corpus and methodology

**Corpus:** 1930 test files (1928 .Y2L + 2 .Y2U) exported from MODX M
across test steps 1–113, plus the baseline pair
`AWM2_00_Init_Normal.Y2L/.Y2U` and `SmartMorph.Y2L/.Y2U`.

**Methodology:** Isolate one hypothesis per field. Read expected value via
big-endian unpack from specific abs offset, compare against expected
pattern from X7/X8/YSFC 5.0.1, aggregate across corpus.

**Tools:** `test_step1_header.py` (per-file report) + `step1_aggregate.py`
(corpus statistics) + `investigate_libinfo.py` (libinfo detail).

## A.2 Per-hypothesis results

| ID | Hypothesis | Status | Result |
|----|------------|:------:|--------|
| H1.1 | Magic = "YAMAHA-YSFC" @ 0x00..0x0F | 🟢 | 1930/1930 pass |
| H1.2 | Version string @ 0x10..0x1F | 🟢 | All `5.1.2` |
| H1.3 | Catalogue size (BE32) @ 0x20 | 🟢 | All divisible by 8 |
| H1.4 | Padding 0x24..0x2F = 12 × 0xff | 🟢 | 1930/1930 |
| H1.5 | Library-info length (BE32) @ 0x30 | 🟢 | Fits-in-file, but new baseline |
| H1.6 | Padding 0x34..0x3B = 8 × 0xff | 🟢 | 1930/1930 |
| H1.7 | Timestamp (BE32) @ 0x3C | 🟢 | Counter model, not Unix epoch |
| H1.8 | Catalogue @ 0x40 starts with 'E'/'D' ID | 🟢 | All EPFM |
| H1.9 | Catalogue = {4-byte ID, BE32 offset} entries | 🟢 | All offsets valid + sorted |
| H1.10 | Library-info follows directly after catalogue | 🟢 | 1930/1930 |
| H1.11 | Empty library-info = 80×0xff + 0x00 = 81 b | 🔴 | **241 b** (240×0xff + 1×0x00) |

**Overall outcome: 🟢 Green with one calibration.** 10 of 11 hypotheses
confirmed word-for-word. The H1.11 deviation is a *parameter* change
within the same structure, not a structural change — the test plan
explicitly predicted this as a possible outcome ("Montage M has probably
extended this for 16 libraries or similar").

## A.3 Verified header layout

```
abs    field                                value / note
─────────────────────────────────────────────────────────────────
0x00   magic + null-pad (16 b)              b'YAMAHA-YSFC\x00\x00\x00\x00\x00'
0x10   version string + null-pad (16 b)     b'5.1.2'
0x20   catalogue size  (u32 BE)             = block_count × 8
0x24   reserved padding (12 b)              all 0xff
0x30   library-info length (u32 BE)         baseline 241 b
0x34   reserved padding (8 b)               all 0xff
0x3C   timestamp / save counter (u32 BE)    monotonically increasing counter
0x40   catalogue entries                    N × (4-byte ID + u32 BE offset)
0x40 + cat_size
       library-info area
0x40 + cat_size + libinfo_len
       first block chunk (always EPFM)
```

## A.4 Central findings

### A.4.1 Version string: `5.1.2`

All 1930 files report the exact same version string:
```
b"5.1.2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
```

This is **not 6.0.0** — Yamaha has bumped YSFC from 5.0.1 (MODX) to 5.1.2
for Montage M / MODX M, a minor version step. The structure is
fundamentally backward-compatible.

### A.4.2 Library-info baseline went from 81 to 241 bytes

| Platform | Empty library-info area |
|----------|-------------------------|
| Montage classic (X7L) / MODX (Y2L 5.0.1) | 80×0xff + 1×0x00 = **81 b** |
| Montage M / MODX M (Y2L/Y2U 5.1.2) | 240×0xff + 1×0x00 = **241 b** |

Interpretation: Yamaha has extended the library slot count from **8 to 24**
(240/10 = 24 reserved 10-byte slots), consistent with Montage M's
expanded hardware capacity. Cook's slot-block structure is confirmed in
files with populated library-info (see A.4.5).

### A.4.3 Timestamp is a counter, not RTC

Values lie in the range `0x00003e00 – 0x00003e1d` (15872–15901) across
the test corpus — too small for Unix epoch. Values increase monotonically
per export operation. Y2L and Y2U exports of "the same" performance
produce close but not identical counter values (typically differing by
1–2). Montage M has **not** added an RTC timestamp.

### A.4.4 Block-ID universe

Distinct block IDs across all 1930 files:

| ID | File count | Interpretation |
|----|-----------:|----------------|
| `EPFM` / `DPFM` | 1930 | Performance — standard, always present |
| `ESYS` / `DSYS` | 1930 | System settings |
| `EFVT` / `DFVT` | 1930 | Favorites |
| `ESPG` / `DSPG` | 4 | SmartMorph Performance Grid + 32×32 PNG |
| `ESOM` / `DSOM` | 4 | SmartMorph Original Morph (1024×876) |
| `ELST` / `DLST` | 2 | Live Set (matches section 1.6) |
| `ESON` / `DSON` | 1 | **NOT previously documented** — only in Analysis_Set_v1.Y2L |

### A.4.5 Catalogue size distribution

| Catalogue size | Block count | File count | Note |
|---------------:|------------:|-----------:|------|
| 48 b | 6 | 1924 | Baseline (EPFM/DPFM, ESYS/DSYS, EFVT/DFVT) |
| 64 b | 8 | 2 | Step 72 — contains ELST/DLST |
| 80 b | 10 | 3 | SmartMorph (adds 4 SM blocks) |
| 96 b | 12 | 1 | Analysis_Set_v1.Y2L — SmartMorph + ESON/DSON |

### A.4.6 Y2L vs Y2U — header identical, payload differs minimally

The header structure is identical between file extensions. Raw byte
comparison:

| Pair | Bytes differing | Detail |
|------|----------------:|--------|
| `AWM2_00_Init_Normal.Y2L/.Y2U` | 6 | 1 in timestamp + 5 in payload (separate export) |
| `SmartMorph.Y2L/.Y2U` | 2 | Only timestamp LSB + one counter |

The SmartMorph pair confirms that Y2L and Y2U *can* be near-identical
byte-for-byte copies; the AWM2 pair shows that two separate exports of
"the same performance" produce more differences (separate save-counter
states). The relevant conclusion is that **a parser for Y2L can read Y2U
unchanged**.

## A.5 Implications for parser and serializer

### A.5.1 New constants in serializer

Added to `ysfc_serializer.py` (Step 1 verified):

```python
YSFC_MAGIC_POS         = 0x00    # 16 bytes magic + null-pad
YSFC_VERSION_POS       = 0x10    # 16 bytes version + null-pad
YSFC_CAT_SIZE_POS      = 0x20    # u32be: catalogue size (= entries × 8)
YSFC_LIBINFO_LEN_POS   = 0x30    # u32be: library-info area length
YSFC_TIMESTAMP_POS     = 0x3C    # u32be: save counter
YSFC_CATALOG_POS       = 0x40    # first catalogue entry
YSFC_VERSION_M_SERIES  = b'5.1.2'
YSFC_LIBINFO_EMPTY_LEN = 241     # empty library-info: 240 × 0xff + 1 × 0x00
```

Existing `FILE_SAVE_COUNTER_POS = 60` (= 0x3C) and `CHUNK_CATALOG_POS = 64`
(= 0x40) are unchanged — Step 1 confirmed these were already correct.

### A.5.2 Differences from documented layout in section 1.1

**Section 1.1 has been corrected** (as of this revision) to match the verified layout in A.3. The original table was written before Step 1 verification and contained the following errors — listed here for historical reference:

- Magic described as 8 bytes, version as 8 bytes at offset 8 — correct is 16+16 bytes
- "Library type @ offset 16" — that field is the version string
- "Catalog offset @ offset 20" — that field is `catalogue size`; the catalogue is always at 0x40
- "Date stamp @ offset 24" — timestamp / save counter is at offset 0x3C
- Library-info area (offset 0x30) was not mentioned

The constants in the serializer were always correct (right offsets 0x3C/0x40). Only the documentation comments were wrong.

### A.5.3 Header reading can be shared between generations

Our parser's header reading only needs two parameterizations:
1. Add `"5.1.2"` to acceptable version strings (in addition to `"4.0.5"`,
   `"5.0.1"`).
2. Remove the hardcoded `EMPTY_LIBINFO_SIZE = 81`; always read from
   offset 0x30 without pre-validation (`YSFC_LIBINFO_LEN_POS`).

No other changes are needed for catalogue parsing, magic validation, or
timestamp reading.

## A.6 Questions left for Step 4 and 5

- **MAX_LIBRARY_SLOTS = 24?** — Preliminary, based on 240/10. To be
  confirmed in Step 4 against the two Step 72 files with populated
  library-info area (4230 bytes).
- **ESON/DSON block semantics** — Only one file (Analysis_Set_v1.Y2L)
  contains these. To be mapped in Step 5.
- **The 5 payload byte differences between the AWM2 pair Y2L/Y2U** — at
  offsets 0x18e–0x18f, 0x2c6, 0x1cf3–0x1cf4. Section 1.7 mentions similar
  noise bytes in the range 6715..6725 and 7167–7168, 7419. 0x1cf3–0x1cf4
  (=7411–7412) lies close to the 7419 noise position and is likely the
  same phenomenon.

---

**End of YSFC Forge Full Context.**
