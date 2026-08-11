# YSFC Forge — Full Context

> **FM-X completion checkpoint — 2026-08-11 / parser v1.0.77**  
> The Soundmondo→Y2L FM-X mapping represented by `FMX_COVERAGE_MATRIX_v177.csv` is now complete for 153 tracked Yamaha-documented parameter points and has an ESP-verified lineage. Important correction: OP-relative `+62/+64` are Pitch/Level Controller Sensitivity and `+66/+68/+70` are 1st-LFO destination depth ratios. Older text that labels `+66/+68/+70` as internal trailer bytes is superseded. The FM-X 2nd-LFO depth matrix is no longer partial. Smart Morph **transport/preservation** is verified, while generic reconstruction/interpolation-table editing remains a separate open problem.


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

All four engines are binary-verified (all known parameters). Multi/GM 16-part-files are supported (15 AWM2 + 1 Drum on Part 10, through the multi-part architecture).

**Structural insight: The Drum engine has its own Part Common layout**

Drum does not share the universal AEG offset block (rel +144..+150) as AWM2/FM-X/AN-X. For Drum, the following applies instead:
- Rel +126..+132 = drum AEG (Attack/Decay/Sustain/Release, c64)
- Rel +144/+146 = drum filter cutoff/resonance (c64)

The interpretation of Part Common rel +126..+158 is governed by engine_type. The shared AEG-block-architecture therefore applies only to three of four engines.

**About AN-X coverage:** AN-X-engine is fundamentally different from AWM2. AWM2 is a sample player where 8 identical elements share a structure — each byte tends to be a direct UI parameter. AN-X is an analog model with complex modulation routing: of the engine pool's 684 bytes, 458 firmware constants ([INTERN]) including routing matrices and loose flags. The 171 UI fields cover all user-editable parameters.

---

## Current format and export model

YSFC Forge treats the supported Yamaha file families as separate but closely related layouts:

| Family | Typical versions | File extensions | Current role |
|---|---|---|---|
| MODX M / MONTAGE M long layout | `5.1.x` modern exports | `.Y2L`, `.Y2U` | Primary native export target |
| MONTAGE M short layout | `4.1.x` / `.X2L`-style layout | `.Y2L`, `.X2L`-style sources | Experimental Performance import; expanded to long-layout Y2L/Y2U |
| Legacy MONTAGE | `4.0.x` | `.X7L`, `.X7U` | Experimental Performance import/conversion |
| Legacy MODX / MODX+ | `5.0.x` | `.X8L`, `.X8U` | Experimental Performance import/conversion |

The Library Builder exports selected Performances and the dependencies they require. The tool does not attempt to clone full library state. Live Sets, Patterns, Favorites and device metadata are outside the current export scope.

### Current Library Builder conversion scope

| Source type | Engines | Dependencies | Note |
|---|---|---|---|
| Native long `.Y2L`/`.Y2U` | AWM2, FM-X, AN-X, Drum | Selective waveforms, samples, arpeggios | Primary supported path |
| Legacy `.X7L`/`.X8L` | AWM2, FM-X, Drum | Selective waveforms, samples, arpeggios | Converted to modern Y2L DPFM layout |
| MONTAGE M short-layout `.X2L`-style files | AWM2, FM-X, AN-X, Drum | Converted when referenced through supported sections | Short common/part/engine regions are expanded to long-layout Y2L |

AN-X is fully supported in the modern Y2L/Y2U target format. AN-X is not normally expected to occur in legacy MONTAGE/MODX `.X7L`/`.X8L` libraries; unknown classic part types are treated as unsupported classic engines.

### Current Y2L/User-Arp export model

User Arps are handled both as dependency data and playback/scene state. The current export path:

- remaps EARP/DARP IDs globally in the exported target file
- rewrites scene-level arpeggio references to compact 0-based IDs
- writes Arp Master state for imported classic Performances with active arp references
- avoids mapping classic import-state bytes to Part Mute
- does not use Arp Play Only as a substitute for Arp Master
- clears classic import-state bytes that can affect playback where ESP reference exports show them cleared

This the current model for exports where the file loads but User-Arp-driven scenes would otherwise be silent or play incorrectly.

## Performance ↔ Waveform / Sample / Arpeggio linkage

Selective export copies only the dependencies that a selected set of performances actually uses. A valid Y2L requires that catalog IDs are a **contiguous sequence**, so the export both copies the referenced dependencies and renumbers them, and rewrites the blob references so they match.

**Reference model.** A performance references a USER waveform through a fixed byte structure inside the DPFM blob. Two encodings exist (both byte-verified against ESP ground truth and controlled CFX single-edit pairs):

- `SIG_A`: `00 00 00 28  01(bank)  XX  YY  00  [ID]  00 01 00 01` — element slot
- `SIG_B`: `01 00 00 00  01 00 0C 00  [ID]  00 40` — element config

The byte after `0x28` is the **bank**: `0x01` = USER waveform (`[ID]` byte indexes EWFM/EWIM catalog), `0x00` = preset/ROM (ignored). `XX YY` vary (`00 00` or `00 01`); both are matched. `[ID]` is a single byte. The catalog ID lives in `recPayload[10:12]` (big-endian u16) in each EWFM/EWIM `Entr` record.

**Renumbering rule.** Collect the distinct referenced old IDs, sort them, assign new IDs `1..N` (1-based for waveform/sample). Rewrite every `[ID]` byte in every kept performance blob old→new, and write the new IDs in the rebuilt EWFM/EWIM `recPayload[10:12]`. Pure renumbering touches **only** `[ID]` byte — the bank/Field-2 bytes are not touched.

**Arpeggios.** Arp references live in separate (`80 00 …`) element-pitch-block with a distinct 0-based ID space. Arp-refs sit after a run of `80 00` pairs (pitch table) and optional `00` padding, as one or more `[ARP_ID] 2f` pairs (the ref may repeat up to 4×); `ARP_ID` is a single byte < 21. Renumbering rule is identical to waveform but **0-based**: sort the distinct referenced arp-IDs, assign `0..N-1`. EARP/DARP are rebuilt selectively with the new IDs; each kept performance blob gets its arp-`[ID]` byte repointed old→new.

**Dependency-section sizing.** Y2L dependency sections are sized **exactly** to payload; MODX rejects any size-field/data slack. Each dep section (EWFM, DWFM, EWIM, DWIM, EARP, DARP), DPFM performance pool and EPFM performance index are sized all to the byte using uniform 8-byte-per-blob framing accumulated, then `exactSize(n) = Σ(8 + payload) − 4 + 8` (subtract the single 4-byte first-blob/record over-count, add the section header). A minimal Init/one-record floor is kept for empty selections.

**Container structure.** A valid library file uses ESP's exact 12-chunk layout (`EPFM EWFM EARP ESYS EFVT EWIM DPFM DWFM DARP DSYS DFVT DWIM`, no ECRV/ELST/DCRV/DLST-stubs). `u32@0x20` = chunk count × 8.

**Per-file build stamp.** `u32@0x3c` is a per-file build stamp that is also embedded as u16 before every EPFM/EWFM/EARP name. It must be in the same family within a file; the synthetic header's `0x3c` is set to the source file's `0x3c`. EPFM record byte[11] = destination slot index (compact `0,1,2,3` for a 4-perf export).

**DWFM sample-index.** Each DWFM blob is `[4-byte header][N × 64-byte sub-entries]`; at blob offset `60 + 64·k` there is a 4-byte little-endian sample-data index. It must be a pure ascending counter `value[in] = base + in`, where `base` is the first blob sub-entry's original 4-byte LE value and `in` increments once per sub-entry across all blobs in order (full 32-bit LE).

**Fixed directory region.** A valid YSFC library file has a fixed-size directory region: entries from `dirOff` (0x40), FF-padding, a single `0x00`-separator at `dirOff+0x150` (= 0x190), and the first chunk at `dirOff+0x151` (= 0x191). MODX computes every chunk's position from this fixed region.

**Per-performance dependency tags (UI).** Each performance row's W/S/Arp-chip are gated on whether that specific performance actually references the dependency, using the same binary-verified scanners that drive the selective export (`scanWaveformRefPositions` / `scanArpRefPositions`). EWFM/EWIM share an ID space, so waveform refs gate both W and S; arp refs gate Arp. If a blob cannot be read the code falls back to file-level behavior. The per-performance info column shows only the engine label (`AWM2`/`FM-X`/`AN-X`).

**Helpers:** `scanWaveformRefPositions`, `scanArpRefPositions`, `renumberPerfBlob`, `setRecPayloadId`, `resolveFileWaveformRefs`, `resolveFileArpRefs`, `getDepsForSelection`, `buildSyntheticY2LBuffer`, `buildDepPayload`, `cloneAndPatchOffLen`, `buildDPFMPayload`, `buildEPFMPayload`, `calcSyntheticDimensions`, `exportMergeToY2L`, `createSyntheticBaseFile`. A conservative copy-all fallback is preserved for any untrusted resolution (parse anomaly, blob < 12000 B, zero refs despite a pool, or a referenced ID missing from a section catalog). If the chosen base file is also a source of any selected performance a synthetic container is forced (`baseIsSource`).

---


## Foreword — How to read this document

This a **clean, deduplicated master reference** for the YSFC format. Each field is listed ONCE with correct position, default, encoding and star rating.

**Sources of truth in priority order:**

1. **Binary-verified with test file ★★★★★** — diff-proven. This authoritative.
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

All absolute offsets are `blob[+N]` relative to **the performance blob's start** (where `blob[0..3] = 00 00 00 15`). This the same as `dp[N+12]` if counted from DPFM-payload start.

---

## Content

1. Y2L file format architecture
2. Container — EPFM / DPFM / ESYS / EFVT / ELST
3. Sub-blob universal model
4. Engine pool (multi-part)
5. Performance Common (Sub-blob 1)
6. Part Common (Sub-blob 2..N)
7. Receive Switch per Part
8. Common Assigns (CA-structures)
9. scene Structures
10. MS Sequencer
11. Engine data: AN-X
12. Engine data: AWM2
13. Engine data: FM-X
14. Engine data: Drum
15. Insertion FX
16. Smart Morph
17. UI elements NOT IN BLOB
18. Remaining unmapped regions
19. Modified/Noise-flags (filtrera at diff)
20. Helper-funktioner (serializer)
21. Verification status and test file registry

---

# 1. Y2L file format architecture ★★★★★

Y2L/Y2U-filthe format består of a 64-byte file-header följt of a alternerande sekvens of "Entry" (E*) and "Data" (D*) chunks. each E-chunk indexes entries; each D-chunk innehåller motsvarande data.

```
File header                 (64 bytes)
EPFM  Performance index     — entries pekande in i DPFM
DPFM  Performance data      — huvudpayload
ESYS  System index
DSYS  System data
EFVT  Favorite index
DFVT  Favorite data
ELST  Live Set index        (valfritt)
DLST  Live Set data         (valfritt)
```

`.Y2L` (Library file) and `.Y2U` (User file) is byte-for-byte identiska — bara fileändelsen skiljer (ESP-pluginet uses ändelsen for att avgöra vilken import-dialog that should visas).

## 1.1 File header (64 bytes) ★★★★★

Binary-verified against 1930+ files (Appendix A.3 in English versionen). Tidigare versioner of the här tabellen hade fel fältstorlekar and offset — korrekt layout nedan.

| offset | Hex | Size | Field | Note |
|---:|---:|---:|---|---|
| 0 | 0x00 | 16 | Magic + null-pad | `YAMAHA-YSFC\x00\x00\x00\x00\x00` (11 bytes ASCII + 5 zero-bytes) |
| 16 | 0x10 | 16 | Version + null-pad | `5.1.2\x00…` for Montage M / MODX M; `5.0.1` for MODX classic; `4.0.5` for Montage classic |
| 32 | 0x20 | 4 | Catalogue size | `u32 BE` = antal_block × 8; katalogen starts always on 0x40 |
| 36 | 0x24 | 12 | Reserved padding | all `0xFF` |
| 48 | 0x30 | 4 | Library-info length | `u32 BE`; 241 bytes baseline (Montage M / MODX M), 81 bytes (classic) |
| 52 | 0x34 | 8 | Reserved padding | all `0xFF` |
| 60 | 0x3C | 4 | Spairs-counter | `u32 BE`; increments monotonically per export — **not** Unix-timestamp |

Spairs-räknaren at 0x3C is del of noise set (filtered at diff-analys). It is också inbäddad that `u16` before every EPFM/EWFM/EARP-postname — båda must stämma overens annars rejects MODX the file. Katalogen starts always on absolutoffset `0x40` oavsett katalogstorlek-fältets value.

## 1.2 EPFM chunk ★★★★★

EPFM (Entry Performance) is performance index. It innehåller a fast header följt of a Entry-record per performance in the file.

```
EPFM chunk-header   (8 bytes: 'EPFM' + size u32 BE)
count               (4 bytes u32 BE: count Entry-poster)
'Entr'              (4 bytes: global typ-tagg; fungerar också som tagg för first posten)
rec1_storlek        (4 bytes u32 BE)
rec1_data           (rec1_storlek bytes)
'Entr' rec2_storlek rec2_data     ← efterföljande poster har var sin 'Entr'-tagg
…
```

note: the **first** posten har no own föregående `Entr`-tagg — the globala taggen at byte [4:8] fyller the rollen. Post 2..N har var sin `Entr`-tagg.

each Entry-posts payload (binärverifierad against MODX M-files):

| Rel | Size | Field | Note |
|---:|---:|---|---|
| 0 | 4 | Blob-size | `u32 BE` — storleken on performance blobben in DPFM |
| 4 | 4 | DPFM-offset | `u32 BE` — offset inom DPFM-payload |
| 8 | 1 | constant | `0x00` |
| 9 | 1 | constant | `0x40` (MODX validerar this field) |
| 10 | 1 | constant | `0x00` |
| 11 | 1 | Destinations-slot | compact destinations-index (0, 1, 2, … for sekventiell export) |
| 12 | 1 | constant | `0x00` |
| 13 | 1 | Multi-engine-flag | `0x00` (förenklat) |
| 14 | 1 | constant | `0x00` |
| 15 | 1 | Engine-bitar | `0x01`=AWM2/Drum, `0x02`=FM-X, `0x04`=AN-X; OR-kombinerat for multi-engine |
| 16 | 1 | Käll-flag | `0x00`=ESP Plugin-export, `0x02`=MODX hardware-export |
| 17 | 1 | constant | `0x00` |
| 18 | 1 | Kategori | `0x01`=default |
| 19 | 6 | Padding | all `0x00` |
| 25 | 1 | constant | `0x30` |
| 26 | 1 | Slot-flag | `0x00` (förenklat) |
| 27 | var | Namnsträng | `"IDX:KortNamn:VisningsNamn\0"` — NUL-terminerad ASCII |

Namnsträngens format is `"{slot_index}:{kort_name}:{visnings_name}\0"`. **Visningsthe name** (tredje the field) is it name that MODX and ESP Plugin visar — it matchar `blob[4:]` exactly. **Kortthe name** (second/mellersta the field) is a förkortad kategorietikett for internal bruk and is not visningsthe name. Example: `"0:Italian XL:Italian Grand XL\0"` — kortname `"Italian XL"`, visningsname `"Italian Grand XL"`.

note: tidigare versioner of denna dokumentation hade fältordningen omvänd (beskrevs that `"IDX:LångtNamn_paddat:KortNamn\0"`). It beskrivningen var felaktig.

För a single-performance-file innehåller EPFM exactly a Entry-record. För library fileer with flera performances exists a Entry per performance.

## 1.2a v4.x-filformatsdifferenceer (Montage classic / MODX classic) ★★★★☆

files with versionssträng `4.0.5` (Montage classic) or `5.0.1` (MODX classic) skiljer sig from v5.x-layouten on två important sätt:

**EPFM directory-structure:** I v4.x-files is EPFM-chunken on `d[64]` själva directory-structureen — dess payload innehåller chunk-pekare (EARP, ESYS, EFVT, DPFM, …), not Entr-poster. It faktiska EPFM-chunken with Entr-poster is inbäddad längre in in the file (typiskt runt offset `0x171`) and exists not listad in directory. För att hitta the: skanna framåt from offset ~200 efter next `'EPFM'`-tag with valid `count + 'Entr'`-payload.

**Engine-type-the bytes offset:** I v4.x-blobbar sitter engine-type-the byte on `blob[6698]`, not `blob[6700]` that in v5.x. Sub-blob-separatorn `0x00000015` follows direkt on `blob[6699:6703]`.

**Rekommendation:** used always EPFM `rec[15]` (engine bits: `0x01`=AWM2/Drum, `0x02`=FM-X, `0x04`=AN-X) that primärkälla for agine-typ at läsning of files with unknown version — it is korrekt in både v4.x and v5.x. used `blob[6700]` bara that fallback for bekräftade v5.x-files.

## 1.3 DPFM chunk ★★★★★

DPFM (Data Performance) innehåller the faktiska performance-datan. Chunk-headern följs of a sekvens of sub-blobs (a per performance).

```
DPFM header                       (8 bytes: 'DPFM' + size big-endian u32)
Sub-blob 1                        (Performance 1)
Sub-blob 2                        (Performance 2)
...
```

each sub-blob is själv a self-contained performance — se section 2 for sub-blob-structureen.

För Multi/GM 16-part-files innehåller DPFM a single mycket stor sub-blob (~141 536 bytes) that representerar the 16-part-Performance.

## 1.4 ESYS / DSYS (System Settings) ★★★★★

ESYS/DSYS innehåller system-level-inställnnor (master tune, MIDI-kanaler, MIDI-routing etc.). Dessa is typiskt konstanta over the flesta files and is edited not via per-Performance UI.

För the flesta filtyper is ESYS 46 bytes and DSYS 1094 bytes.

## 1.5 EFVT / DFVT (Favorites) ★★★★★

EFVT/DFVT innehåller Favorites-bitmappen (vilka performances is markerade that favoriter). EFVT is typiskt 163 bytes; DFVT is 22 219 bytes.

Favorites-bitmappen uppdateras when the user togglar a performance that favorit. This a noise-region for performance-redigerings-diffs.

## 1.6 ELST / DLST (Live Set) ★★★★★

ELST/DLST innehåller Live Set-definitioner (vilken performance that is assignd to vilken slot in a Live Set-bank). Dessa chunks is missing in single-performance-files and exists with in fullständiga library fileer.

## 1.7 File integrity — NO checksums ★★★★★

YSFC-the format has **no checksums or integritetsverifiering**. Vilken byte that helst can ändras without att the file blir ovalid (as long as the resulterande structureen fortfarande is parseable).

This har flera konsekvenser for editor-design:

### bytes that ALWAYS differ between two exports

När användaren spairsar a performance två gånger without ändrnor the following will bytes still att skilja:

```
Date stamp:           offset 24      (4 bytes)
Save counter regions: 6715..6725     (~11 bytes)
Misc internal:        7167-7168, 7419
```

Dessa bytes are del of noise set and filtered at binär-diff-analys.

### Consequence for editor

Eftersom it not exists någon checksum:
- Edits kräver no post-edit-fixup
- A modifierad file is omedelbart valid as long as structureen is preserverad
- Längdändrnor (t.ex. ändring of Element Count) require careful update of längd-dependency field

### Risk: no integrity check

Frånvaron of checksums betyder att a korrupt file not can upptäckas of själva the format — only by att attempting to load the. Editor-implementationer should:
- always keep a backup of original filen
- Verify round-trip (read → write → read) before originalet förstörs
- Validera output genom att parse:a it igen before saven is considered that lyckad

---

# 2. Sub-blob universal model ★★★★★

A sub-blob is a self-contained Performance-representation. Oavsett om the file innehåller a or 256 performances, is each Performance kodad that a sub-blob inuti DPFM.

## 2.1 layout

```
Sub-blob 1: Performance Common         (6701 bytes — shared metadata)
Sub-blob 2: Part 1 Common              (5765 bytes)
Sub-blob 3: Part 2 Common              (5765 bytes)
...
Sub-blob N+1: Part N Common            (5765 bytes)
Engine pool                            (variabel size, beror på engine-mix)
```

I a single-Part Performance exists a Part Common (Sub-blob 2) plus a enda engine-block. I a multi-Part performance har each active Part sin own Part Common följd of sin own engine-data in engine-poolen.

Sub-blob-antalet and Part-antalet is kodat in Entr-bitmasken (se section 3.7).

## 2.2 Sub-blob header (27 bytes) ★★★★★

each sub-blob starts with a 27-byte header:

```
bytes 0..3:    Sub-blob type marker
bytes 4..7:    Sub-blob size (big-endian u32)
bytes 8..N:    Variabel header (name-string etc.)
```

It variabla headern inkluderar performance/part-name and några metadata-field. It exactlya layouten beror on om this Common-sub-bloben or a Part-sub-blob.

## 2.3 Engine-typ-detection ★★★★★

Engine-typen for each Part is kodad at `blob[+6700]` (relative to performance blob-start):

```
0 = AWM2
1 = Drum
2 = FM-X
3 = AN-X
```

För multi-part-files härleds engine-typen for efterföljande parts via sub-blob-pointer-modellen (se section 3.6).

## 2.4 Per-part address-formel ★★★★★

För Part N (1-indexerad) inom a multi-part Performance:

```
Performance Common base = blob[0]              (6701 bytes)
Part N Common base = blob[6701 + (N-1) * 5765] (5765 bytes per Part)
```

Så:
- Part 1 Common: bytes 6701..12465
- Part 2 Common: bytes 12466..18230
- Part 3 Common: bytes 18231..23995
- ...

För a single-Part Performance exists bara Part 1. Engine-poolen starts omedelbart efter Part Common(s).

## 2.5 Verification ★★★★★

It 5765-byte Part Common stride is verified genom:
- 16 × stride 5765 in Multi/GM 16-part-files (verified)
- Flera multi-part Y2U-files that visar identisk Part Common-structure replikerad at stride 5765
- Sub-blob-pointern at rel +5763/+5764 (section 3.6) is located always at denna offset inom each Part Common

## 2.6 Edit-flag-bytes per sub-blob

each sub-blob har interna edit-flag-bytes that ökar at edit. Dessa is del of noise set and filtered at diff-analys:

- `blob[+6715]`: Performance edit counter (ökar at each Performance-save)
- `blob[+6716]`: Subtype counter
- `blob[+6721]`: Edit-relaterad byte

Dessa bytes ändras at each spairs oavsett vilken parameter that redigerades.

---

# 3. Engine pool (multi-part) ★★★★★

I multi-part-files lagras engine-data in a shared pool efter all sub-blobs.

## 3.1 Pool layout

```
[Engine 1 data][5b separator][Engine 2 data][5b separator]...[Engine M data]
                                                              ↑
                                                              no separator efter last
```

**constant:** `ENGINE_POOL_SEP_SIZE = 5`

## 3.2 Engine-sizes ★★★★★

| Engine | Data-size | Pool-stride (with sep) |
|---|---|---|
| **AN-X** | 684 bytes | 689 |
| **AWM2** | 2503 bytes | 2508 |
| **FM-X** | 1143 bytes | 1148 |
| **Drum** | 4963 bytes | 4968 |

## 3.3 Pool start-address

```python
ENGINE_POOL_BASE = 6701 + N_parts * 5765
```

Där `N_parts` is antalet active Parts. För a single-Part Performance starts poolen direkt efter Part 1:s Common-block:

```
pool_start = 6701 + 1 * 5765 = 12466
```

För a 16-part Multi/GM-file:

```
pool_start = 6701 + 16 * 5765 = 99 141
```

## 3.4 Engine start-signaturer ★★★★★

each engine-block starts with a 5-byte header-signatur:

```
AWM2:  [01, 00, 00, 00, 28]          — last the byte 0x28 = 40 dec, marker
AN-X:  [01, 00, 00, 00, 6E]          — last the byte 0x6E = 110 dec
FM-X:  [01, 00, 00, 00, 52]          — last the byte 0x52 = 82 dec
Drum:  [01, 00, 00, 00, 49]          — last the byte 0x49 = 73 dec
```

last the byte in denna 5-byte header is engine-typ-magic-the byte. It can användas for att identifiera engine for a block at skanning of poolen.

## 3.5 Engine pool addressing

För Part N with engine-typ E:

```python
# Engine-block för Part N starts vid:
engine_start_N = ENGINE_POOL_BASE + sum(
    ENGINE_STRIDE[engine_of_part_k]
    for k in range(1, N)
)

# (no separator efter last engine i poolen, men beräkningen uses
#  fortfarande full stride för betweenliggande parts.)
```

## 3.6 Multi-part "linked list"-pointer-modell ★★★★★

each Part Common innehåller a 2-byte pointer that avgör om this last Part and vilken engine next Part uses:

```
SUBBLOB_PONOTR_REL = (5763, 5764)
```

För Part N:s Part Common (placerad at `blob[6701 + (N-1) * 5765]`), is pointer-the byte on:

```
pos_marker = 6701 + (N-1) * 5765 + 5763
pos_next   = 6701 + (N-1) * 5765 + 5764
```

**Decoding:**

```python
marker = blob[pos_marker]
next_val = blob[pos_next]

if marker == 1:
    # not last Part; next_val identifierar Part N+1:s engine-typ
    # next_val: 0=AWM2, 1=Drum, 2=FM-X, 3=AN-X
    is_last = False
    next_engine = ENGINE_TYPE_VALUES[next_val]
else:
    # Detta ÄR last Part; marker ÄR engine-typ-magic-the byte för Part 1
    # marker: 8=AWM2, 110=AN-X, 82=FM-X, 73=Drum
    is_last = True
    part1_engine = ENGINE_MAGIC_TO_NAME[marker]
```

This betyder:
- each Parts pointer berättar engine-typen for next Part (om någon)
- last Part:s pointer wrap:ar runt and berättar engine-typen for Part 1
- This bildar a cirkulär linked list of engine-typer

## 3.7 Entr-bitmask for active parts ★★★★★

Antalet active Parts is kodat in a Entr-record-bitmask inom EPFM. Denna bitmask har a bit per Part (1 = active).

För a 16-Part Multi/GM-file is all 16 bitar satta. För a single-Part Performance is bara bit 0 satt.

## 3.8 Helper-API for multi-part-pointer

```python
SUBBLOB_PONOTR_REL = (5763, 5764)
ENGINE_MAGIC_BYTES  = {'ANX': 110, 'AWM2': 8, 'FMX': 82, 'Drum': 73}

def get_subblob_pointer_pos(part_idx):
    """position för Part N:s pointer (1-indexerat)."""
    sub_blob_start = 6701 + (part_idx - 1) * 5765
    return (sub_blob_start + 5763, sub_blob_start + 5764)

def read_subblob_pointer(blob, part_idx):
    """Returnerar (is_last, next_or_part1_engine)."""
    pos0, pos1 = get_subblob_pointer_pos(part_idx)
    marker, next_val = blob[pos0], blob[pos1]
    if marker == 1:
        return False, ENGINE_TYPE_VALUES[next_val]
    return True, ENGINE_MAGIC_TO_NAME[marker]
```

## 3.9 Multi/GM 16-part-files ★★★★★

**Multi/GM file type** is YSFC 16-part multitimbral-konfigurationen. It is used that a GM-kompatibel tongenerator (Multi/GM Performance with drums assigned to Part 10 enligt GM-standarden).

**Filstructureen follows the dokumenterade multi-part-modellen exactly:**

| Component | Size | Content |
|---|---:|---|
| Performance Common (sub-blob 1) | 6701 bytes | Default Performance Common |
| 16 × Part Common (sub-blobs 2-17) | 5765 bytes vardera = 92240 bytes | Stride 5765 between parts |
| Engine pool | ~42583 bytes | 15 × AWM2 (stride 2508) + 1 × Drum (4963) for Part 10 |
| **DPFM total** | **141536 bytes** | verified |

**Empiriskt verified:**

- 16 förekomster of "Concert GrandPiano" (AWM2 default-waveform-name) with stride 5765 between Part Common-instanser
- Stride hoppairs to 11530 (2 × 5765) between Part 9 → Part 11 because Part 10 is Drum (har annat default-waveform-name)
- 73 drum keys on fo 122261 (Part 10 engine-data startposition) with stride 68
- 72 of 73 drum keys har SW=1 in Multi/GM Init

**Filstorlek vs single-Part-files:**

| File type | DPFM | Total file size |
|---|---:|---:|
| AWM2 single-part | 14981 | 38985 |
| AN-X single-part | 13162 | 37166 |
| FM-X single-part | 13682 | 37625 |
| Drum single-part | 17441 | 41427 |
| **Multi/GM 16-part** | **141536** | **165530** |

**Engine-typer per Part in Multi/GM Init:**

- Parts 1-9: AWM2 (Concert GrandPiano)
- Part 10: Drum (Default Drum Kit)
- Parts 11-16: AWM2 (Concert GrandPiano)

**Addresseringskonvention:**

Multi/GM uses **exactly same addressingsmodell** that second multi-part-files:
- Performance Common: `blob[0:6701]` (same field that single-Part)
- Part N Common: `blob[6701 + (N-1)*5765 : 6701 + N*5765]` for N=1..16
- Engine pool: starts efter last Part Common
  - Part N engine base = engine_pool_start + sum(engine_stride for parts 1..N-1)

Addresseringen is **redan supported** of befintlig serializer-kod via:
- `SUBBLOB_PONOTR_REL = (5763, 5764)`
- `get_subblob_pointer_pos(part_idx)`
- `ENGINE_MAGIC_BYTES`

**Implikation for editor:** Multi/GM kräver **no new structures** or field in serializern. all dokumenterade and binärverifierade Part Common, Engine Pool and Drum Key-field fungerar identiskt on Multi/GM-files — bara with 16 parts istället for 1.

---

# 4. Performance Common (Sub-blob 1) ★★★★★

Region: `blob[0:6701]` (6701 bytes). Verified with ~25 binärtestade UI-fields + flera u16le-pairs + ~3000 bytes constant padding.

## 4.1 Header (sub-blob 1 header, same that blob-header)

| abs | Size | Field | Encoding | Status |
|---|---|---|---|---|
| 0..3 | 4 b | Sub-blob length prefix `00 00 00 15` | constant | ★★★★★ |
| 4..21 | 18 b | **Performance Name** | ASCII, space-padded | ★★★★★ |
| 22 | 1 b | Null terminator | 0x00 | ★★★★★ |
| 23..24 | 2 b | Timestamp/save-counter — NOISE | ignored | ★★★★★ |
| 25..26 | 2 b | 0x00 0x00 | constant | ★★★★★ |

## 4.2 Performance Toggles + Single Fields

| abs | Field | Encoding | Default | Status | Test file |
|---|---|---|---|---|---|
| 29 | portamentoMasterSwitch | bool | 0=OFF | ★★★★★ | `Portamento_ON.Y2L` |
| 30 | ribbonAssign1Mode | bool | 1=Latch (0=Moment) | ★★★★★ | `RibbonAssign_BothMoment` |
| 31 | ribbonAssign2Mode | bool | 1=Latch | ★★★★★ | `RibbonAssign_BothMoment` |
| 33 | ribbonMode (Hold/Reset) | bool | 1 | ★★★★★ | `RibbonMode_Hold` |
| 34 | reverbOnOff | bool | 1=ON | ★★★★★ | `Reverb_Off` |
| 35 | variationOnOff | bool | 1=ON | ★★★★★ | `Variation_Off` |
| 37 | masterFxOnOff | bool | 0=OFF | ★★★★★ | `MasterFX_ON` |
| 38 | arpMasterOn (?) | bool | 0 | ★★★★☆ | `ArpMasterON` (delar offset with OSC Mute/Solo edit-state) |
| 39 | msMasterOn | bool | 0=OFF | ★★★★★ | `MSMasterON` |
| 50 | commonAudioSwitch | bool | 1=ON | ★★★★★ | `CommonAudio_Off` |
| 56 | **smartMorphEnable** | bool | 0 (1 om SM active) | ★★★★★ | `TEST-FMX-SMARTMORPH` |
| 57 | sliderDirection | bool | 0=Normal (1=Reverse) | ★★★★★ | |
| 66 | modifiedFlag — NOISE | edit-state | varies | ★★★★★ | (filtered) |
| 68 | **Performance Volume = EF Master Output** | direct, 0..127 | 127 | ★★★★★ | `TEST5-1-VOL50` (UI-aliasing) |
| 70 | **Performance Pan** | c64, -63..+63 | 64 (Center) | ★★★★★ | `TEST5-4-PAN` |
| 92 | **Performance Tempo** | direct BPM (u8) | 120 | ★★★★★ | `TEST5-2-TEMPO90` |
| 94 | **Performance Portamento Time** | direct (possibly c64) | 64 | ★★★★★ | `Portamento_Time_50` |
| 104 | lastActiveScene | u8 (0=Scene1, 7=Scene8) | 0 | ★★★★★ | `Scene1`, `Scene2`, ... |
| 216 | ribbonGridMode | enum (0=Cont, 1=5step) | 0 | ★★★★★ | `RibbonGrid_5step` |

**UI-aliasing:** Vissa bytes har två UI-labels. `blob[+68]` heter "Performance Volume" in Performance Edit men "EF Master Output" in Envelope Follower-vyn — **same fysiska byte**. confirmed: `EnvelopeFollowerOutput_Master_90.Y2L` ändrar exactly `blob[+68]` from 127 → 90.

⚠️ **`blob[+80]` and `blob[+82]`** har constant value `0x40` in all testade files and ändras not of någon known UI-parameter. copy verbatim.

⚠️ **`blob[+654]`** ändras in 9+ orelaterade tester (EF Part change, många InsertionAssign edits) — it is a **side-effect-flag**, not a parameter. filtered at diff.

## 4.2.1 Structural metadata bytes ★★★★★

Fundamentala bytes that styr blob-architecture. must sättas korrekt at skrivning.

| abs | Field | Encoding | Bevis |
|---|---|---|---|
| 6695 | **Max active Part-index** | u8, 1..16 (highest nummer, not count) | 4 multi-part-files, korrelation 100% |
| 6700 | **Engine Type (Part 1)** | u8 enum: 0=AWM2, 1=Drum, 2=FMX, 3=ANX | 30+ engine-specifika files, korrelation 100% |
| 12464..12465 | **Part 2 engine-prefix** | u8 × 2, engine-specifika in multi-part | Engine-discriminating in sub-blob 2 |

**Example on Max Active Part:**

- Part 1 only → `blob[+6695] = 1`
- Parts 1+2 → `blob[+6695] = 2`
- Parts 3+5 (icke-konsekutiva) → `blob[+6695] = 5` (= highest, not antalet 2)

**Consequence for editor:**

```python
def set_part_metadata(blob, active_part_indices, engine_part1):
    """active_part_indices: list of 1-baserade part-numbers
       engine_part1: 'AWM2', 'Drum', 'FMX', or 'ANX'"""
    blob[6695] = max(active_part_indices)
    blob[6700] = {'AWM2': 0, 'Drum': 1, 'FMX': 2, 'ANX': 3}[engine_part1]
```

## 4.3 Hardware Ribbon Control

summary of Ribbon-relaterade field (all ★★★★★):

| abs | Field | Encoding | Default |
|---|---|---|---|
| 30 | ribbonAssign1Mode | bool | 1=Latch |
| 31 | ribbonAssign2Mode | bool | 1=Latch |
| 33 | ribbonMode (Hold/Reset) | bool | 1=Reset (0=Hold) |
| 57 | sliderDirReverse | bool | 0=Normal |
| 216 | ribbonGridMode | enum | 0=Continuous |

## 4.4 SuperKnob Link Per scene ★★★★★

8 bytes at `blob[40:48]` (a byte per scene), plus mirror in scene Struct 1.

| abs | Field | Encoding | Default |
|---|---|---|---|
| 40..47 | skLinkScene1..8 | u8 bool | 1=ON |
| 1717..1724 | (mirror inom scene Struct 1) | u8 bool | 1 |

Mirror is replikerad data — uppdateras pairsallellt.

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
| 164 | fsAssignDest | enum | ★★★☆☆ (untested encoding) |
| 166 | msTriggerCC | 89 | ★★★★★ |
| 168..182 | assignKnob1..8 CC | 17..24 (stride 2) | ★★★★★ |

**Hard-coded in firmware (NOT IN BLOB):**
- scene CC (= 92)
- Super Knob CC (= 95)
- Footswitch Assign (= Arp Sw)

## 4.7 Per-scene SuperKnob Value ★★★★★

8 × u16le at `blob[184:200]` (a u16le per scene).

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

Region `blob[376:428]` (52 bytes). 26 field.

| abs | Field | Encoding |
|---|---|---|
| 34 | reverbOnOff (in toggle-area) | bool, default 1 |
| 376 | reverbCategory | u8 enum |
| 377 | version-byte | constant 1 |
| 380..381 | reverbType | u16le, default 32 |
| 382..383 | reverbPreset | u16le, default 10 |
| 384..426 | 22 × u16le pairsams (Type-specifika) | stride 2 |

För Shimmer Reverb-typ is the 22 pairsametrarna: Shimmer Gain, Shimmer Fdbk, Shimmer HPF, Shimmer LPF, P1/P2 Balance, P1&P2 Panning, Pitch 1, Fine 1, Pitch 2, Fine 2, Cross-Feedback, Color, Reverb Time, Initial Delay, Diffusion, Size, P1&P2 Dly Ofs, Mod Depth, Mod Speed, AM Depth, AM Freq, AM Waveform. second Reverb Types uses same slots with different tolknnor.

## 4.9 Variation FX ★★★★★

Region `blob[432:484]` (52 bytes). 28 field.

| abs | Field | Encoding |
|---|---|---|
| 35 | variationOnOff (in toggle-area) | bool, default 1 |
| 432 | variationType | u8 enum |
| 436..482 | 24 × u16le pairsams | stride 2 |

För M/S EQ Compressor-typ matchar pairsametrarna Master FX-layouten (24 pairsam-mall).

## 4.10 Master EQ ★★★★★ / ★★★★☆

Region `blob[560:593]`. Per-band-stride is icke-uniform (Low uses 8 bytes pga shelf-typ; övriga 6 bytes).

| abs | Field | Encoding | Default | Status |
|---|---|---|---|---|
| 560 | meqLowGain | c64 (±24 dB) | 64 | ★★★★★ |
| 562 | meqLowFreq | u8 logaritmisk ~6 raw/oct | 12 | ★★★★★ |
| 564 | meqLowQ | direct (raw = UI × 10) | 7 (=0.7) | ★★★★★ |
| 566 | meqLowType | enum 0=Shelf, 1=Peak | 0 | ★★★★★ |
| 568 | meqLowMidGain | c64 | 64 | ★★★★★ |
| 570 | meqLowMidFreq | u8 logaritmisk | 20 | ★★★★☆ (predicted) |
| 572 | meqLowMidQ | u8 direct | 7 | ★★★★★ |
| 574 | meqMidGain | c64 | 64 | ★★★★★ |
| 576 | meqMidFreq | u8 logaritmisk | 28 | ★★★★★ |
| 578 | meqMidQ | u8 direct | 7 | ★★★★★ |
| 580 | meqHiMidGain | c64 | 64 | ★★★★★ |
| 582 | meqHiMidFreq | u8 logaritmisk | 44 | ★★★★☆ (predicted) |
| 584 | meqHiMidQ | u8 direct | 7 | ★★★★★ |
| 586 | meqHighGain | c64 | 64 | ★★★★★ |
| 588 | meqHighFreq | u8 logaritmisk | 52 | ★★★★★ |
| 592 | meqHighType | enum 0=Shelf, 1=Peak | 0 | ★★★★★ |

**Design-anteckning:** När Q ändras can Type-flag auto-uppdateras (+566 = 0 → 1 at Q-max). UI-logik: Q is meningsfullt bara for Peak-type, not Shelf.

**★★★★☆ predikterade field:** Lo Mid Freq (570) and Hi Mid Freq (582) saknar dedikerade clean-1-diff testfiler. Stride-mönstret (6-byte block for icke-Low-band) gör positionerna highest sannolika men not empiriskt bevisade. Kandidater for framtida verifiering.

## 4.11 Master FX ★★★★★

Region `blob[598:650]` (52 bytes). 26 field. Identisk structure with Reverb/Variation FX.

| abs | Field | Encoding |
|---|---|---|
| 37 | masterFxOnOff (toggle) | bool, default 0=OFF |
| 598..599 | masterFxType | u16le, default 32 (M/S EQ Compressor=80) |
| 602..648 | 24 × u16le pairsams | stride 2 |

För M/S EQ Compressor-typ: M/S Balance, M Threshold, M Makeup Gain, S Threshold, S Makeup Gain, Stereo Expand, Comp Type, M Comp Curve, S Comp Curve, M Gain, S Gain, EQ position, M EQ Low Freq/Gain/Q, M EQ High Freq/Gain/Q, S EQ Low Freq/Gain/Q, S EQ High Freq/Gain/Q.

## 4.12 SuperKnob Mid-position ★★★★★

Region `blob[670:723]`.

| abs | Field | Encoding | Default |
|---|---|---|---|
| 670..671 | commonSuperKnobValue | u16le | 512 |
| 672 | midPositionEnable | bool | 0 |
| 674..721 | 8 assigns × 6 bytes | stride 6 per assign | - |

Per assign (N=0..7), abs = 674 + N × 6:

| relative | Field | Encoding | Default |
|---|---|---|---|
| +0 | AssignN LeftPosition | u8 | 0 |
| +2 | AssignN MidPosition | u16le | 512 |
| +4 | AssignN RightPosition | u16le | 1023 |

## 4.13 Region [732:766] [STRUKT] ★★★★★

34 bytes, structureellt karaktäriserat men UI-funktion not identifierad.

```
[732:760]  14 × u16le-values
[760:766]  6 byte trailer
```

**Default-values:** `[31, 31, 15, 7, 23, 7, 23, 15, 15, 23, 7, 23, 7, 15]`

Pattern: all values tillhör "8N − 1"-familjen (possible bit-mask). UI-funktion unknown. Patch editor: reads and writes tillbaka oförändrat.

## 4.14 Audio In + Envelope Follower ★★★★★

| abs | Field | Encoding | Default |
|---|---|---|---|
| 48 | audioInInsASwitchCommon | bool | 1=ON |
| 49 | audioInInsBSwitchCommon | bool | 1=ON |
| 766 | **audioInVolume = EF AD Output Level** | direct (UI-aliasing) | 100 |
| 768 | audioInPan | c64 | 64 (Center) |
| 770 | audioInRevSend | direct | 0 |
| 772 | audioInVarSend | direct | 0 |
| 774 | audioInInsConnect | enum 1=A→B (default), 2=B→A | 1 |
| 778 | audioInDryLevel | direct | 127 |
| 780 | envFollowerGain | c64 | 64 (=0 dB) |
| 782 | envFollowerAttack | direct | 16 |
| 784 | envFollowerRelease | direct | 7 |

**UI-aliasing:**
- `blob[+766]` har två UI-labels — "Audio In Volume" and "EF AD Output Level". same fysiska byte.
- `blob[+48, +49]` (Common-vyn) styr same logiska funktion that `blob[+6734, +6735]` (Part-vyn, section 5.1). UI har två paths for Audio In Insertion A/B switches.

**Audio In Mute & Solo — NOT IN BLOB ★★★★★:**
Mute- and Solo-knappairsna on Audio In-raden in Mixing-vyn (flik "Audio")
is **UI-state**, not persisterad data. verified with TEST5R3-AUDIO_MUTE_ON.Y2L:
toggling of Mute → 0 signal-diffs in hela blob. Editor behover not hantera dessa.

## 4.15 Common Assign Names ★★★★★

Region `blob[2280:2447]` (8 strängar × 21 bytes = 168 bytes).

```
COMMON_ASSIGN_NAMES_BASE   = 2279
COMMON_ASSIGN_NAMES_STRIDE = 21
COMMON_ASSIGN_NAMES_LEN    = 16  # max chars
```

Default: "Assign 1", "Assign 2", ..., "Assign 8".

```python
def get_common_assign_name_addr(slot):
    """slot = 1..8. ASCII starts vid +1 from base (len-prefix vid +0)."""
    return 2279 + 1 + (slot - 1) * 21
```

## 4.16 CA_PERF (Common Assigns Performance) ★★★★★

Se section 7 — identisk structure that CA_PART (difference: scope-flag).

## 4.17 Stride-106 Zone/Control-block [STRUKT]

5 grupper × 8 block = 40 block totalt, ~3300 bytes:

| Group | Region | block count |
|---|---|---|
| 1 | `[840:1710]` | 8 block |
| 2 | `[3186:4043]` | 8 block |
| 3 | `[4083:4943]` | 8 block |
| 4 | `[4943:5826]` | 8 block |
| 5 | `[5942:6700]` | 8 block |

**Hypotes:** per-part Aftertouch/Velocity-tabeller or Mod Source-mappnnor. UI-funktion not identifierad. Patch editor: läs/write verbatim.

## 4.X Control Assign — 32 slots ★★★★★

UI: **Common / Control / Control Assign** — möjliggör att routea controllers
(Mod Wheel, Aftertouch, Foot Controllers etc.) to pairsametrar in Performance.
verified with `Test-AWM2-Control-ControlAssign-Source_ModWheel_Detsination1_Volume_CurveType_Bell_Polarity_Bi_Param1_4_Param2_3.Y2L`.

**position:** `[2451:3155]` = 32 slots × 22 bytes = 704 bytes totalt.

```python
CONTROL_ASSIGN_BASE = 2451
CONTROL_ASSIGN_STRIDE = 22
CONTROL_ASSIGN_COUNT = 32  # 8 Assign Knobs × 4 Destinations per Knob
```

**Slot-structure (22 bytes, rel 0..21):**

| Rel | Field | Encoding | Default | Interpretation |
|----:|---|---|---:|---|
| 0 | slot_signature | u8 const | 18 | always 18 in all 32 slots |
| 1 | source_set | u8 bool | 0 | 0=Off, 1=Source active |
| 3 | source_id | u8 enum | 8 | 8=None default, 1=ModWheel/CC#1 (Yamaha enum) |
| 5 | dest_pairsam_lo | u8 | 1 | Destination parameter low byte |
| 6 | dest_pairsam_hi | u8 | 0 | Destination pairsam hi / flag |
| 9 | pairsam2 | u8 | 0 | Parameter 2 (test: 0→3) |
| 11 | pairsam1 | u8 | 5 | Parameter 1 (test: 5→4) |
| 13 | curve_type | u8 enum | 0 | Curve typ (test: 0→3 for "Bell") |
| 15 | polarity | u8 enum | 0 | 0=Uni, 1=Bi |
| 17 | slot_endmark | u8 const | 192 | always 192 (0xC0) in all slots |

**32 slots layout:** likely **8 Assign Knobs × 4 Destinations per Knob** (matchar Yamaha-modellen where each knob can ha 4 destination-rows). or alternativt 8 Knobs × 4 Curve-slots.

**note:** This **Common-nivå** (Performance-globalt), not per Part or per Element. It stämmer overens with din feedback om att Controller Sets is Common-nivå.

**Source-enum (source_id rel +3):** 8=None, 1=ModWheel (CC#1). Fler values behover verifieras with dedikerade tester.

---

# 5. Part Common (Sub-blob 2..N) ★★★★★

each Part Common is **5765 bytes** (sub-blob payload + 27-byte header).

```
Part N sub-blob start = 6701 + (N-1) × 5765
Part N payload start  = sub_blob_start + 27
```

Per-Part rel-offsets is **identiska over all 16 parts** inom same engine. offsets nedan is abs for Part 1 (sub_blob_start = 6701).

## 5.1 Part Common Single-fields (Part 1, abs) ★★★★★

| abs | rel_part | Field | Encoding | Default | Status | Test file |
|---|---|---|---|---|---|---|
| 6731 | 30 | **partMode** | enum 0=Internal, 1=External | 0 | ★★★★★ | `Test-AWM2_PartMode_External` |
| 6732 | 31 | partKbdCtrlOn | bool | 1=ON | ★★★★★ | |
| 6733 | 32 | **partMute** | bool | 0=unmuted | ★★★★★ | `TEST5R3-T5i-Part1-Mute-ON` |
| 6734 | 33 | **partAudioInInsASw** | bool | 1=ON | ★★★★★ | `TEST5R3-T1a-AudioInsA-OFF` |
| 6735 | 34 | **partAudioInInsBSw** | bool | 1=ON | ★★★★★ | `TEST5R3-T1b-AudioInsB-OFF` |
| 6737 | 36 | partMSPartSwitch | bool | 1 | ★★★★★ | `MSMaster_verify` |
| 6740 | 39 | partPortamentoOn | bool | 1=ON | ★★★★★ | |
| 6743..6770 | 43..70 | **Receive Switches** (26 st) | bool block | mest 1=ON | ★★★★★ | Se section 6 (AWM2-) |
| 6775 | 74 | **partPgmChangeSw** (ext-only) | bool | 1=ON | ★★★★★ | `Test-AWM2_PgmChange-toggle_Off` |
| 6776 | 75 | **partBankSelectSw** (ext-only) | bool | 1=ON | ★★★★★ | `Test-AWM2_BankSelect-toogle_Off` |
| 6790 | 89 | **partPanSw** (ext-only) | bool | 1=ON | ★★★★★ | `Test-AWM2_Pan-toggle_Off` |
| 6791 | 90 | **partVolExpSw** (ext-only) | bool | 1=ON | ★★★★★ | `Test-AWM2_VolExp-toggle_Off` |
| 6801 | 100 | **partArpMasterOn** | bool | 1=ON | ★★★★★ | must is preserved/sättas korrekt for User-Arp playback |
| 6802 | 101 | **partArpPlayOnly** | bool | 0 | ★★★★★ | should not användas that ersättning for Arp Master |
| 6831 | 130 | **partVolume = EF Part Output** (UI-aliasing) | direct, 0..127 | 100 | ★★★★★ | `Part1_Volume_127`, `EnvelopeFollowerOutput_70` |
| 6833 | 132 | **partPan** | c64 | 64 (=C) | ★★★★★ | `TEST5R3-T2b-Mixing-Part1-PanL20` |
| 6835 | 134 | **partRevSend** | direct, 0..127 | 0 | ★★★★★ | `TEST5R3-T2c-Mixing-Part1-Rev50` |
| 6837 | 136 | **partVarSend** | direct, 0..127 | 0 | ★★★★★ | `TEST5R3-T2d-Mixing-Part1-Var50` |
| 6839 | 138 | **partDryLevel** | direct, 0..127 | 127 | ★★★★★ | `TEST5R3-T2e-Mixing-Part1-Dry80` |
| 6849 | 148 | partAEGOffset | c64 | 64 | ★★★★★ | `Part1_AEGOffSet_20` |
| 6865 | 164 | partFEGDepthOffset | c64 | 64 | ★★★★★ | `Filter_FEG_Depth_20`, `FEGDepth_50` |
| 6867 | 166 | partFilterCutoffOffset | c64 | 64 | ★★★★★ | `Filter_Cutoff_20`, `FilterOffset_20` |
| 6869 | 168 | partResonanceOffset | c64 | 64 | ★★★★★ | `Filter_Resonance_20` |
| 6913 | 212 | partPitchBendRangeUpper | c64 | 66 (= +2) | ★★★★★ | `TEST-PB+24`, `TEST-PB-24`, `TEST-PB0` |
| 6915 | 214 | partPitchBendRangeLower | c64 | 62 (= −2) | ★★★★★ | (Drum-test) |
| 6917 | 216 | partDetune | c128 | 128 (= 0 Hz) | ★★★★★ | 37 oberoende `Detune_*` tester |
| 6919 | 218 | partNoteShift | c64 | 64 (= 0 st) | ★★★★★ | (Drum-test) |
| **6983** | **282** | **partInsA_Type** ★★★★★ | u8 enum (0=Thru, ...) | 0 | ★★★★★ | `Test-AWM2_InsertionA-Type-SPXRoom` |
| **6984** | **283** | **partInsA_SubType** | u8 | 0 | ★★★★★ | (same) |
| **6987..7015** | **286..314** | **partInsA_Param1..15** | u8 stride 2 | 0 (set by Type) | ★★★★★ | (Insertion-tester) |
| 7273 | 572 | partTxRxChannel | enum 0=Ch1...15=Ch16, 127=OFF | 0 | ★★★★★ | |
| **7287** | **586** | **partMidiVolume** (ext-only) | u8 direct | 100 | ★★★★★ | `Test-AWM2_MidiVolume_50` |
| **7289** | **588** | **partMidiPan** (ext-only) | u8 c64 | 64 | ★★★★★ | `Test-AWM2_MidiPan_R6` |
| **7295** | **594** | **partMidiPgmNum** (ext-only) | u8 direct | 0 | ★★★★★ | `Test-AWM2_MidiPgmNum_030` |

**UI-aliasing:** `blob[+6831]` is **Part 1 Volume** in Mixing-vyn (samt
Part Edit-vyn) and **EF Part 1 Output** in EF-vyn. same fysiska byte.
confirmed: `AWM2_00_Init_Part1_Volume_127.Y2L` (100→127),
`EnvelopeFollowerOutput_70.Y2L` (100→70) and
`TEST5R3-T2a-Mixing-Part1-Vol80.Y2L` (100→80) ändrar exactly same offset.

**Per-Part Mixer-block:** bytes 6831/6833/6835/6837/6839 (stride 2) bildar
Performance Mixing-vyns 5 field per Part: Volume / Pan / RevSend / VarSend / DryLevel.

**Audio In Insertion-aliasing:** `abs 48, 49` (Common-area) ändras of
"Common / Audio Routing"-UI-vyn (Performance-level), medan `blob[+6734, +6735]`
(Part Common) ändras of "Common / Audio / Insertion A/B toggle"-vyn (per-Part).
UI har **två paths** for same logiska funktion. Editor must hantera båda.

**Part Mute/Solo:** Part Mute @ abs 6733 is persisterad (TEST5R3-T5i),
medan Part Solo is **UI-only state** and persisteras not in blob
(TEST5R3-T5j gav 0 signal-diffs).

**User-Arp-säkerhetsregel:** `partMute` at rel +32, `partArpMasterOn` at rel +100 and `partArpPlayOnly` at rel +101 is sepairsata persisterade tillstånd. A korrekt Y2L-export can aktivera Arp Master när a Part har active User-Arp scene-referenser, men får not sätta Part Mute and får not behandla Arp Play Only that likvärdigt with Arp Master.

**Part Mode (rel +30) ★★★★★:** `partMode` = 0 (Internal, default) or 1 (External).
När External is aktiverat skickar Part:n MIDI to externa enheter and följande
field blir relevanta (märkta "ext-only" in tabellen):
- `partPgmChangeSw` (rel 74), `partBankSelectSw` (rel 75)
- `partPanSw` (rel 89), `partVolExpSw` (rel 90)
- `partMidiVolume` (rel 586), `partMidiPan` (rel 588), `partMidiPgmNum` (rel 594)

Dessa field exists in blob also när Part Mode = Internal (defaults bibehålls),
men UI visar dem bara när External is aktiverat.

**Per-Part Insertion FX structure (rel +282..+314) ★★★★★:**

InsA/InsB is **PART-NIVÅ** (not per-element). Element ROUTAS to InsA/InsB
via element-the field `elem_connect` (rel +81 in element). Strukturen is **same
over all engine-typer** (AWM2/AN-X/FM-X verified).

layout per Part:
- rel +282 = InsA Type (u8 enum; 0=Thru default, 18=SPXRoom, 48=Symphonic,
  32=CompDistorsion, 68=MultiFX, 80=GatedReverb, ...)
- rel +283 = InsA Sub-type/Variation
- rel +286, +288, +290, +292, +294, +296, +298, +300, +302, +304, +306, +308,
  +310, +312, +314 = InsA Param 1-15 (stride 2)

**Param-betydelser vary with InsA Type** — a Reverb-effekt har second
parameter-name än a Distorsion-effekt. Editor must hålla sepairsat
mapping `(InsA_Type, pairsam_idx) → pairsam_name`.

**InsB:** Strukturen is located direkt efter InsA with 56 bytes betweenrum:
- InsA Type @ rel +282 (abs 6983)
- InsB Type @ rel +338 (abs 7039) ★★★★★ verified with `Test-AWM2_InsertionB-Type-Reverb_SPXRoom`
- InsB Sub-type @ rel +339
- InsB Param 1-15 @ rel +342, +344, +346, ..., +370 (stride 2)

Båda har identisk structure (Type/Sub-type/Params 1-15). Totalt 56 bytes per Insertion-block.

**Ej persisterad:** `ModControl Display Filter` (UI-vyn for att filtrera Control Assign-listan
per Source = ModWheel/CC#16/etc.) is UI-only state and persisteras not in blob — verified
with `Test-AWM2_ModControl-DisplayFilter_ModWheel.Y2L` that var byte-for-byte identisk with
`Test-AWM2_InsertionB-Type-Reverb_SPXRoom.Y2L` förutom save counter.

**Per-Part Mod Source-table (rel +600..+663) ★★★★★:**

UI: **Edit / Part / Mod/Control / Control Assign** — låter användaren routea
Source (Aftertouch, CC, etc.) to pairsametrar on Part-nivå.

position: `Part rel +600..+663` = **4 slots × 16 bytes** (64 bytes).

```python
PER_PART_MOD_SOURCE_REL_BASE = 600   # rel inom Part sub-blob (abs 7301 för Part 1)
PER_PART_MOD_SOURCE_STRIDE = 16
PER_PART_MOD_SOURCE_COUNT = 4
```

**Slot-structure (16 bytes, rel 0..15):**

| Rel | Field | Encoding | Default | Test-value |
|----:|---|---|---:|---|
| 0 | source_set | u8 bool | 0 | 0→1 (Source aktiverad) |
| 2 | signature | u8 | 1 | 1→2 (AT that source) |
| 6 | pairsam2 | u8 | 0 | 0→3 (test pairsam2=3) |
| 8 | pairsam1 | u8 | 5 | 5→4 (test pairsam1=4) |
| 10 | curve_type | u8 enum | 0 | 0→3 (Bell) |
| 12 | polarity | u8 enum | 0 | 0=Uni, 1=Bi |
| 14 | endmark | u8 const | 192 (0xC0) | always |

**note — UI-only field:** Element-Switch (AllElement / Element1 / Element2 / Element3
for a AT-assign) persisteras not in blob.: 4 different files
with different Element-switch gav IDENTISKA byte-diffs.

**different structure än Common ControlAssign:**
- Common ControlAssign har stride 22 bytes and 32 slots
- Per-Part Mod Source har stride 16 bytes and 4 slots
- only 4 source-slots per Part räcker because Common-nivån har the 32 slots

```python
PART_COMMON_REL = dict(
    partMode_rel     = 30,    # ★★★★★ (0=Internal, 1=External)
    kbdCtrlOn_rel    = 31,
    partMute_rel     = 32,    # ★★★★★ (Part Solo är UI-only, not i blob)
    audioInInsASw_rel = 33,
    audioInInsBSw_rel = 34,
    msPartSwitch_rel = 36,
    portamentoOn_rel = 39,
    # rel +43..+70: Receive Switches (26 st) — se section 6
    pgmChangeSw_rel  = 74,    # ★★★★★ ext-only
    bankSelectSw_rel = 75,    # ★★★★★ ext-only
    panSw_rel        = 89,    # ★★★★★ ext-only
    volExpSw_rel     = 90,    # ★★★★★ ext-only
    arpMasterOn_rel  = 100,
    volume_rel       = 130,   # = EF Part Output (UI-aliasing)
    pan_rel          = 132,
    revSend_rel      = 134,
    varSend_rel      = 136,
    dryLevel_rel     = 138,
    aegOffset_rel    = 148,
    feg_depth_offset_rel = 164,
    filter_cutoff_offset_rel = 166,
    resonance_offset_rel = 168,
    pbRangeUpper_rel = 212,
    pbRangeLower_rel = 214,
    detune_rel       = 216,
    noteShift_rel    = 218,
    insertionA_type_rel = 282, # ★★★★★ Per-Part InsA struct start
    txRxChannel_rel  = 572,
    midiVolume_rel   = 586,   # ★★★★★ ext-only
    midiPan_rel      = 588,   # ★★★★★ ext-only
    midiPgmNum_rel   = 594,   # ★★★★★ ext-only
)

def get_part_common_field(sub_blob_start, field_name):
    return sub_blob_start + PART_COMMON_REL[field_name + '_rel']
```

## 5.2 Part LFO (FM-X) ★★★★★

FM-X har sepairsat LFO-mapping per Part:

| abs (Part 1) | Field | Encoding | Default |
|---|---|---|---|
| 6770 | fmxPartLfoTempoSync | bool | 0=Off |
| 6771 | fmxPartLfoLoop | bool INVERTED (0=On, 1=Off) | 0=On |
| 7199 | fmxPartLfoPhase | enum 0=0°,1=90°,2=120°,3=180°,4=240°,5=270° | 0 |
| 7201 | fmxPartLfoWave | enum 0..12 (Triangle..User) | 0=Triangle |
| 7203 | fmxPartLfoSpeed | direct | 32 |
| 7205 | fmxPartLfoTempoNote | raw = list_idx + 5 | 11 (=1/4) |
| 7207 | fmxPartLfoDelay | direct | 0 |
| 7209 | fmxPartLfoFadeIn | direct | 0 |
| 7211 | fmxPartLfoHold | direct | 127 |
| 7213 | fmxPartLfoFadeOut | direct (center=64) | 64 |
| 7215 | fmxPartLfoKeyOnReset | enum 0=Off,1=Each,2=1st | 2 |
| 7217 | fmxPartLfoDest1 | enum | 2 |
| 7219 | fmxPartLfoDest1Depth | direct | 0 |
| 7221 | fmxPartLfoDest2 | enum | 4 |
| 7223 | fmxPartLfoDest2Depth | direct | 0 |
| 7225 | fmxPartLfoDest3 | enum | 4 |
| 7227 | fmxPartLfoDest3Depth | direct | 0 |
| 7265 | fmxPartLfoRandomSpeed | direct | 0 |

**FMX LFO TempoNote-table:**

```
raw=5:1/16, 6:1/8Tri, 7:1/16Dot, 8:1/8, 9:1/4Tri, 10:1/8Dot,
raw=11:1/4 (default), 12:1/2Tri, 13:1/4Dot, 14:1/2, 15:WholeTri, 16:1/2Dot,
raw=17:1/4×4, 18:1/4×5, 19:1/4×6, 20:1/4×7, 21:1/4×8, 22:1/4×16,
raw=23:1/4×32, 24:1/4×64
```

**FMX LFO Destinations** (verified subset):

```
70 = Pan          ★★★★★
72 = FilterCutoff ★★★★★
74 = Feedback     ★★★★★
75 = OpFreq       ★★★★★
77 = OpDetune     ★★★★★
78 = OpLevel      ★★★★★
71 = SecondLfoSpeed  (UI-deduced ★★★☆☆)
73 = Resonance       (UI-deduced ★★★☆☆)
76 = OpSpectral      (UI-deduced ★★★☆☆)
```

## 5.3 Part 2nd LFO (FM-X) ★★★★★

| abs (Part 1) | Field | Encoding | Default |
|---|---|---|---|
| 12509 | fmxPart2ndLfoWave | enum 0..12 | 0 |
| 12511 | fmxPart2ndLfoSpeedNormal | direct | 30 |
| 12513 | fmxPart2ndLfoPhase | enum 0=0°,1=90°,2=180°,3=270°,4=360° | 0 |
| 12515 | fmxPart2ndLfoDelay | direct | 0 |
| 12517 | fmxPart2ndLfoKeyOnReset | bool | 0 |
| 12519..12523 | 2nd LFO Global Mod Depths | u8 ×3 (Pitch/Amp/Filter) | 0,0,0 |
| 12529 | fmxPart2ndLfoExtended | bool | 1=ON |
| 12531 | fmxPart2ndLfoSpeedExtended | direct | 60 |

Filter Mod is GLOBAL ONLY (no per-OP).

## 5.4 Part PEG (FM-X) ★★★★★

| abs (Part 1) | Field | Encoding | Default |
|---|---|---|---|
| 12477 | fmxPegPitchVelSens | c64 | 64 |
| 12479 | fmxPegRandomPitch | direct | 0 |
| 12481 | fmxPegPitchKeyFollow | keyfollow% | 96 (=100%) |
| 12483 | fmxPegCenterKey | MIDI note (C-2=0) | 60 (=C3) |
| 12485 | fmxPegInitialLevel | c50 | 50 |
| 12487 | fmxPegAttackLevel | c50 | 50 |
| 12489 | fmxPegDecay1Level | c50 | 50 |
| 12491 | fmxPegDecay2Level | c50 | 50 |
| 12493 | fmxPegReleaseLevel | c50 | 50 |
| 12495 | fmxPegAttackTime | direct | 0 |
| 12497 | fmxPegDecay1Time | direct | 0 |
| 12499 | fmxPegDecay2Time | direct | 0 |
| 12501 | fmxPegReleaseTime | direct | 0 |
| 12503 | fmxPegDepthVelSens | direct | 0 |
| 12505 | fmxPegDepth | enum [8oct, 2oct, 1oct, 0.5oct] | 0=8oct |
| 12507 | fmxPegTimeKeySens | direct | 0 |

## 5.5 Part AEG / FEG (engine-oberoende, AN-X/FM-X/AWM2) ★★★★★

| abs (Part 1) | Field | Encoding | Default |
|---|---|---|---|
| 6849 | partAegAttack | c64 | 64 (=UI 0) |
| 6851 | partAegDecay | c64 | 64 |
| 6853 | partAegSustain | c64 | 64 |
| 6855 | partAegRelease | c64 | 64 |

**note:** Engine-specifika filter/EG-field is located in engine-data, not in Part Common.

## 5.6 Part Pitch Bend / Detune / Note Shift ★★★★★

| abs (Part 1) | Field | Encoding | Default | Range |
|---|---|---|---|---|
| 6913 | partPitchBendRangeUpper | c64 | 66 (=+2) | 16..88 (-48..+24) |
| 6915 | partPitchBendRangeLower | c64 | 62 (=-2) | 16..88 |
| 6917 | partDetune | c128 (1 cent/raw) | 128 (=0 Hz) | bredd not fastställd |
| 6919 | partNoteShift | c64 | 64 (=0 semitones) | 1..127 |

**TEST-PB-serien:**
- `TEST-PB0.Y2L`: 66→64 (UI 0)
- `TEST-PB+24.Y2L`: 66→88 (UI +24)
- `TEST-PB-24.Y2L`: 66→40 (UI −24)

## 5.7 Part 3-band EQ ★★★★★

| abs (Part 1) | rel_part | Field | Encoding | Default |
|---|---|---|---|---|
| 6939 | 231 | part3bandLowFreq | u8 freq-index | 54 (~62.5 Hz) |
| 6941 | 233 | part3bandLowGain | c64 ±24 dB | 64 |
| 6943 | 235 | part3bandMidFreq | u8 freq-index | 141 (~675 Hz) |
| 6945 | 237 | part3bandMidGain | c64 | 64 |
| 6947 | 239 | part3bandMidQ | direct | 0 (UI shows 0.7) |
| 6949 | 241 | part3bandHighFreq | u8 freq-index | 231 (~7.4 kHz) |
| 6951 | 243 | part3bandHighGain | c64 | 64 |

**note — Freq is located FÖRE Gain** (omvänd ordning from Master EQ).

UI har bara EN Q-kontroll (Mid Q). Low and High is shelf-typer without Q.

**Side-effect:** first edit triggar `blob[+6847] = 0 → 127` (trolig "Part EQ enabled"-flag).

## 5.8 Part 2-band EQ ★★★★★

Helt symmetrisk 8-byte stride per band.

| abs (Part 1) | rel_part | Field | Encoding | Default |
|---|---|---|---|---|
| 6953 | 245 | part2bandEq1Type | enum 0=Thru, 3=LowShelf, 5=Peak/Dip | 0 (→5 at edit) |
| 6955 | 247 | part2bandEq1Freq | logaritmisk ~24 raw/oct | 48 |
| 6957 | 249 | part2bandEq1Gain | c64 (raw = 64 + UI_dB × 2) | 64 |
| 6959 | 251 | part2bandEq1Q | direct (raw = UI_Q × 10, Peak only) | 1 |
| 6961 | 253 | part2bandEq2Type | enum | 0 (→5 at edit) |
| 6963 | 255 | part2bandEq2Freq | logaritmisk | 48 |
| 6965 | 257 | part2bandEq2Gain | c64 | 64 |
| 6967 | 259 | part2bandEq2Q | direct | 1 |
| 6969 | 261 | partOutputLevel | c64 (raw = 64 + UI_dB × 2) | 64 |

**Designinsikt:** Type-flag (6953 / 6961) sätts to 5 at first edit in respektive band (EQ aktiverad-indikator).

## 5.9 Arp Common ★★★★★

Region `blob[6802:7165]`.

| abs (Part 1) | Field | Encoding | Default |
|---|---|---|---|
| 6802 | arpPlayOnly | bool | 0 |
| 6804 | arpLoop | bool | 1=On |
| 6805 | arpStartQuantize | bool | 1 |
| 6806 | arpRandomSFX | bool | 1 |
| 6807 | arpKeyOnControl | bool | 1 |
| 6887 | arpSwing / lane1PartSwing | c128 | 128 |
| 6889 | lane1PartAmplitude | c128 | 128 |
| 6891 | lane1PartShape | c64 | 64 |
| 6893 | lane1PartSmooth | c128 | 128 |
| 6895 | lane1PartRandom | direct 0..100 | 0 |
| 6905 | arpGroup | u8 (0=Off, 1=A, 0x10=P) | 0 |
| 6917 | arpEnableArea | u8 (0x80=idle, 0x89=active) | 0x80 |
| 7095 | arpHold | u8 (0=SyncOff, 1=Off, 2=On) | 1 |
| 7097 | arpUnit / lane1PartUnit | enum (0=100%, 3=1/16) | 3 |
| 7099 | arpNoteLimit_Low | MIDI note | 0 |
| 7101 | arpNoteLimit_High | MIDI note | 127 |
| 7103 | arpVelLimit_Low | direct | 1 |
| 7105 | arpVelLimit_High | direct | 127 |
| 7107 | arpKeyMode | u8 (0=normal, 1=Thru) | 0 |
| 7109 | arpVelocityMode | u8 (0=normal, 1=Thru) | 0 |
| 7111 | arpChangeTiming | u8 (1=beat, 0=Real-Time) | 1 |
| 7113 | arpQuantizeValue | u8 (3=120, 2=80) | 3 |
| 7115 | arpQuantizeStrength | direct 0..100 | 0 |
| 7117 | arpVelocityRate | direct 0..200 | 100 |
| 7119 | arpGateTimeRate | direct 0..200 | 100 |
| 7121 | arpAccentVelThreshold | direct 0..127 | 0 |
| 7123 | arpOctaveRange | c64 | 64 |
| 7125 | arpOctaveShift | c64 | 64 |
| 7127 | arpTriggerMode | u8 (0=normal, 1=toggle) | 0 |
| 7129 | arpVelocityOffset | c64 | 64 |
| 7131 | arpIndividualVelocity (Arp1) | u8 (0x80+n) | 128 |
| 7133 | arpIndividualGateTime (Arp1) | u8 (0x80+n) | 128 |
| 7163 | arp1Name typeId | u8 arpeggio bank/type index | 79 |
| 7164 | arp1Name patternId | u8 pattern within type | 25 |

## 5.10 Region [7094:7165] — Arp Individual data [STRUKT]

71 bytes. Contenter per-arp-step velocity/gate-array (u16le-array, mest c64=64 / 0x80=128). verified field: abs 7131 = velocity.

```
ARP_INDIVIDUAL_BASE = 7094
ARP_INDIVIDUAL_SIZE = 71
ARP_INDIVIDUAL_VELOCITY_PART1 = 7131
```

## 5.11 Part Assign Names ★★★★★

Region `blob[8049:8217]` (8 strängar × 21 bytes = 168 bytes).

```
PART_ASSIGN_NAMES_BASE   = 8048
PART_ASSIGN_NAMES_STRIDE = 21
PART_ASSIGN_NAMES_LEN    = 16
```

Default: "Assign 1", "Assign 2", ..., "Assign 8".

## 5.12 CA_PART (Per-Part Common Assigns) ★★★★★

Se section 7 — identisk structure that CA_PERF.

## 5.13 AWM2 Control Source-block ★★★★☆

Region `blob[7300:7372]` in Part Common (relative to sub-blob 2 start = +599..+671).
**4 slots × 18 bytes** = 72 bytes. Hanterar AWM2 PolyAT/AT/Velocity-mapping
for Part (skilt from CA_PART that is generell CA-structure).

```
AWM2_CONTROL_SOURCE_BASE        = 7300   # Part 1, abs
AWM2_CONTROL_SOURCE_STRIDE      = 18     # bytes per slot
AWM2_CONTROL_SOURCE_SLOT_COUNT  = 4
```

**Per-slot layout (relative to slot-bas):**

| Rel | Field | Encoding | Bevis |
|---|---|---|---|
| +1 | Control Source Switch | bool | `Control_Source_PolyAT_*` |
| +3 | Control Destination ID | u8 enum (1=Resonance, 9=Filter, 10=Cutoff) | ★★★★☆ |
| +5 | Control Source Type | u8 (PolyAT/AT/MW source-id) | ★★★☆☆ |
| +7 | Control Depth | u8 direct | ★★★★☆ |
| +9 | Control Curve | u8 enum 0..5 | ★★★★☆ |
| +11 | Control Param 1 | u8 direct | ★★★★☆ |
| +13 | Control Param 2 | u8 direct | ★★★★☆ |

Addressering: `slot_addr = AWM2_CONTROL_SOURCE_BASE + slot_idx * 18`.
Övriga bytes inom slot (+0, +2, +4, +6, ...) is padding or unknown.

Verificationsbas: tester `Control_Source_PolyAT_Destination1_*`.

---

# 6. Receive Switch per Part ★★★★★

## 6.1 block-architecture

each Part har a 28-byte Receive Switch-block:

```
RCV_SWITCH_REL_OFFSET = 43   # relative to sub-blob start
RCV_SWITCH_BLOCK_SIZE = 28   # 26 switchar + 2 byte block-end markörer
RCV_SWITCH_COUNT      = 26
```

**Address for Part N's RcvSw:** `sub_blob_start(N) + 43`

**Engine-agnostiskt:** Strukturen is **identisk for AWM2, AN-X, FM-X and Drum**
(verified with `Test_AWM2_Part1_RcvSw_BankSelect_OFF` @ Pos 1 = abs 6745
and `Test_AWM2_Part1_RcvSw_FC1_Off` @ Pos 11 = abs 6755).

## 6.2 RcvSw-positions (26/26 mapped)

| Pos | Switch | Default | Status |
|---|---|---|---|
| 0 | PC | 1 | ★★★★★ |
| 1 | Bank Select | 1 | ★★★★★ |
| 2 | CC | 1 | ★★★★★ |
| 3 | A.Knob 1 | 1 | ★★★★★ |
| 4 | A.Knob 2 | 1 | ★★★★★ |
| 5 | A.Knob 3 | 1 | ★★★★★ |
| 6 | A.Knob 4 | 1 | ★★★★★ |
| 7 | A.Knob 5 | 1 | ★★★★★ |
| 8 | A.Knob 6 | 1 | ★★★★★ |
| 9 | A.Knob 7 | 1 | ★★★★★ |
| 10 | A.Knob 8 | 1 | ★★★★★ |
| 11 | FC1 | 1 | ★★★★★ |
| 12 | FC2 | 1 | ★★★★★ |
| 13 | MW | 1 | ★★★★★ |
| 14 | Sustain | 1 | ★★★★★ |
| 15 | Pan | 1 | ★★★★★ |
| 16 | Vol/Exp | 1 | ★★★★★ |
| 17 | RB | 1 | ★★★★★ |
| 18 | BC | 1 | ★★★★★ |
| 19 | FS | 1 | ★★★★★ |
| 20 | A.Sw 1 | 1 | ★★★★★ |
| 21 | A.Sw 2 | 1 | ★★★★★ |
| 22 | [INTERN] reserved | 1 | [INTERN] (default 1, not UI-exponerat) |
| 23 | MS Trigger | 1 | ★★★★★ |
| 24 | Porta Switch | 1 | ★★★★★ |
| 25 | Porta Time | 1 | ★★★★★ |
| 26..27 | block-end markers | 0 | ★★★★★ |

## 6.3 RcvSw helpers

```python
RCV_SWITCH_POS = {
    'PC':0, 'BankSelect':1, 'CC':2,
    'AKnob1':3, 'AKnob2':4, 'AKnob3':5, 'AKnob4':6,
    'AKnob5':7, 'AKnob6':8, 'AKnob7':9, 'AKnob8':10,
    'FC1':11, 'FC2':12, 'MW':13, 'Sustain':14, 'Pan':15,
    'VolExp':16, 'RB':17, 'BC':18, 'FS':19,
    'ASw1':20, 'ASw2':21,
    # pos 22: reserved/internal
    'MSTrigger':23, 'PortaSw':24, 'PortaTime':25,
}

def get_rcv_switch_addr(sub_blob_start, switch_pos):
    return sub_blob_start + 43 + switch_pos

def get_rcv_switch_addr_by_name(sub_blob_start, name):
    return sub_blob_start + 43 + RCV_SWITCH_POS[name]
```

## 6.4 RcvSw — NOT IN BLOB ★★★★★

Hardware events lagras not in performance blob (hanteras on MODX-instrument-nivå):

- **Pitch Bend**
- **Ch.After Touch**
- **Poly.After Touch**

---

# 7. Common Assigns (CA structures) ★★★★★

Två identiska 32-slot-structures: a Performance-nivå (CA_PERF), a Part-nivå (CA_PART).

## 7.1 CA-constants

```
CA_STRIDE        = 22       # bytes per slot
CA_SLOT_COUNT    = 32       # totalt slots per structure
CA_TRAILER_SIZE  = 24       # block-end signature
CA_TOTAL_SIZE    = 728      # 32×22 + 24

CA_PERF_BASE     = 2451     # → ends @ 3179
CA_PART_BASE     = 8220     # → ends @ 8948
CA_PERF_TRAILER  = 3155     # = CA_PERF_BASE + 32*22
CA_PART_TRAILER  = 8924     # = CA_PART_BASE + 32*22
```

Slot N abs offset: `CA_BASE + N × 22` (N = 0..31).

**Slots 17–32** is bit-for-bit identiska with slots 1–16 in Init Voice — in UI exponeras typiskt bara 16, men the format reserverar 32.

## 7.2 CA-slot layout (22 bytes per slot) ★★★★★

| relative | Field | Encoding | Default |
|---|---|---|---|
| +0 | header | u8 | 18 |
| +1 | sw | bool | 0=Off |
| +3 | source | enum (CA_SOURCE) | 1=ModWheel |
| +5 | destination | enum (CA_DESTINATION) | 1=Volume |
| +9 | curveType | enum (Default=0, Harmonic=18) | 0 |
| +11 | pairsam1 | direct | 5 |
| +13 | pairsam2 | direct | 0 |
| +15 | polarity | bool 0=UNI, 1=BI | 0 |
| +17 | depth — [INTERN] | u8, MODX-internal | 192 (0xC0) |

⚠️ **+17 (depth) is MODX-internal** — uppdateras automatiskt of MODX at each Store (that timestamp-bytes). ignored at patch-editing, should not be written.

## 7.3 Difference CA_PERF vs CA_PART

byte +3 (scope-flag) skiljer sig:
- **CA_PERF:** byte +3 = 8 in all 32 slots (default)
- **CA_PART:** byte +3 = 1 in all 32 slots (default)

## 7.4 CA Source enum

| value | Source | Status |
|---|---|---|
| 0 | PitchBend | ★★★★★ |
| 1 | ModWheel (default) | ★★★★★ |
| 2 | AfterTouch | not verified |
| 3 | FootCtrl | not verified |
| 4 | FootSw | not verified |
| 5 | Breath | not verified |
| 6, 7 | (CC-values) | not verified |
| 8 | Knob1 | ★★★★★ |
| 9 | Knob2 | ★★★★★ |
| 10 | Knob3 | ★★★★★ |
| 11..15 | Knob4..Knob8 | not verified |

## 7.5 CA Destination enum (verified subset)

InsA Param-serien is linjär: raw = pairsam_nr (1..24). InsB uses fast raw=25 with pairsam# in CA+11.

### Encoding (critical)

Destination består of **två bytes** in slot-structureen: `destination_lo` (slot rel +4) and `destination_hi` (slot rel +5). Tillsammans utgör the a index in the auktoritativa 414-entries-listan `CONTROLLER_DESTINATIONS` (`ysfc_enums/controllers.py`):

```
CONTROLLER_DESTINATIONS_idx = destination_lo + destination_hi * 256
```

- För destinationer with index **0..255**: `destination_lo` = idx, `destination_hi = 0`
- För destinationer with index **256..511** (Per-Part Assign Knobs, Performance, Arp, Motion Seq): `destination_lo = idx - 256`, `destination_hi = 1`

I tabellen nedan har "value"-kolumnen historiskt skrivit `lo`-the byte and underförstått `hi=1` for values 100, 105, 118 — dessa is egentligen `idx=356, 361, 374` in the fulla listan.

| Lo | Hi | Idx | Destination | Status |
|---:|---:|---:|---|---|
| 1 | 0 | 1 | Volume (default) / InsA Param 1 | ★★★★★ |
| 2..24 | 0 | 2..24 | InsA Param 2..24 | ★★★★★ (linjärt) |
| 25 | 0 | 25 | InsB Param | ★★★★★ (fast raw, pairsam# in CA+11) |
| 50 | 0 | 50 | Rev Send | ★★★★★ |
| 51 | 0 | 51 | Var Send | ★★★★★ |
| 59 | 0 | 59 | P.LFO Depth 3 | ★★★★★ |
| 60 | 0 | 60 | Element Level (0x3C) | ★★★★★ |
| 61 | 0 | 61 | Element Pan (0x3D) | ★★★★★ |
| 62 | 0 | 62 | Element Delay (0x3E) | ★★★★★ |
| 85 | 0 | 85 | Filter Cutoff (0x55) | ★★★★★ |
| 87 | 0 | 87 | HPF Cutoff (0x57) | ★★★★★ |
| 100 | 1 | 356 | Part Pan (0x64) | ★★★★★ |
| 105 | 1 | 361 | Arp Gate Time (0x69) | ★★★★★ |
| 118 | 1 | 374 | MS Length / Motion Seq Length (0x76) | ★★★★★ |
| 142 | 0 | 142 | Filter Cutoff (alt) | ★★★★★ |

För komplett lista (414 entries), se `ysfc_enums/controllers.py`.

## 7.6 CA CurveType enum (verified subset)

| value | Curve |
|---|---|
| 0 | Default (default) |
| 1 | Sigmoid |
| 2 | Threshold |
| 18 | Harmonic |
| 19 | Steps |

## 7.7 block-end signature (trailer)

24 byte trailer efter all 32 slots:

```
04 00 00 00 04 00 01 00 01 00 00 00 14 00 00 3f 00 03 00 00 00 01 00 7f
```

Identisk in både CA_PERF and CA_PART. same signatur is used också that "block-end marker" in region [788:840].

## 7.8 AWM2 AfterTouch Register ★★★★★

Sepairsat from CA-blocket — eget litet AT-register with own destination-encoding.

| abs (Part 1) | Field | Encoding | Default |
|---|---|---|---|
| 7293 (= PART+593) | atSwitch | bool | 0=Off |
| 7295 (= PART+595) | atDestination | enum | 1=Pitch |

**AT Destination enum:**
- 1 = Pitch (default) ★★★★★
- 9 = FilterCutoff ★★★★★

---

## 7.9 Control Assign-structures ★★★★★

tre relaterade Control Assign-structures, totalt **944 bytes**.

### Common Control Assign — abs 2452..3155 (704 bytes)

**32 slots × 22 bytes stride** at abs 2452.

This motsvarar `[COMMON] Control > Control Assign` in ESP-plugins UI (bild 30/31).
Strukturen is "global routing": Source = AsgnKnob/CC/AT etc., Destination =
a specifik parameter in a Part.

Default-baseline (Init Normal AWM2):
```
[0, 0, 8, 0, 1, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 192, 0, 0, 0, 0, 18]
 |     |     |                       |                            |
 |     |     |                       |                            +-- trailer (18, kanske curve+polarity packat)
 |     |     |                       +-- endmark (192 = 0xC0)
 |     |     +-- source_id (default 1 = AsgnKnob1)
 |     +-- destination_lo (default 8 = ?)
 +-- enabled flag (0=inactive)
```

**Per-slot field (relativa offset):**
| +rel | Field | Encoding | Default |
|---:|---|---|---:|
| +0 | enabled | u8 bool | 0 |
| +2 | destination_lo | u8 enum | 8 |
| +4 | source_id | u8 | 1 |
| +10 | pairsam_a | u8 | 5 |
| +16 | endmark | u8 const | 192 (0xC0) |
| +21 | trailer | u8 | 18 |

**verified with tester:**
- Test-AMW2_Part_ControlAssign_destination1-8: slot 1..8 aktiverades with
  destinations 8/9/10/11/12/13/14/15 (verifiering att slots har 22-byte stride).
- Test-AMW2_Part_AfterTouch_destination1-4: same structure men sources 226-233
  (AT-relaterade source-values).

### Part After Touch — Part rel +600..+663 (64 bytes)

**4 slots × 16 bytes stride** at Part rel +600.

This motsvarar `[PART] Mod/Control > After Touch` in ESP-plugins UI (bild 17).
Per-part AT-mapping: 4 destination-slots where each slot specificerar var
Aftertouch should routea (default Source: Poly AT, Destination: Pitch).

Default-baseline:
```
[0, 0, 1, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 192, 0]
 |     |                 |                |
 |     |                 |                +-- endmark
 |     |                 +-- pairsam_a
 |     +-- destination enum (1=Pitch default)
 +-- enabled flag
```

| +rel | Field | Encoding | Default |
|---:|---|---|---:|
| +0 | enabled | u8 bool | 0 |
| +2 | destination | u8 enum | 1 (Pitch) |
| +6 | pairsam2 | u8 | 0 |
| +8 | pairsam1 | u8 | 5 |
| +10 | curve_type | u8 enum | 0 (3=Bell) |
| +12 | polarity | u8 enum | 0 (Uni=0, Bi=1) |
| +14 | endmark | u8 const | 192 |

### Part Control Assign — Part rel +1520..+1695 (176 bytes) — verified with 35 BEFINTLIGA TESTER

**8 slots × 22 bytes stride** at Part rel +1520.

This motsvarar `[PART] Mod/Control > Part Control Assign` in ESP-plugin (bild 18).
Per-part Control Assign-mapping: 8 slots with same 22-byte structure that
Common Control Assign.

Default-baseline (Init Normal AWM2):
```
[0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 192, 0, 0, 0, 0, 18]
```

**Slot-relativa field (verified from 35 AWM2_00_Init_CA_*-tester):**

| +rel | Field | Encoding | Default | Note |
|---:|---|---|---:|---|
| +0 | enabled | u8 bool | 0 | 0→1 at edit |
| +2 | dest_category | u8 | 1 | → 8 at all edits (valid flag) |
| +3 | dest_category_hi | u8 | 0 | |
| +4 | destination_lo | u8 enum | 1 | Faktisk destination |
| +5 | destination_hi | u8 | 0 | 1 for values >127 |
| +8 | pairsam2_or_curve_aux | u8 | 0 | Param2 / Steps-count / Threshold-aux |
| +10 | pairsam1_or_curve_pri | u8 | 5 | Param1 and curve primary (delas) |
| +12 | curve_secondary | u8 | 0 | Sigmoid→3, Threshold→1 |
| +14 | polarity | u8 enum | 0 | Uni=0, Bi=1 |
| +16 | endmark | u8 const | 192 | 0xC0 |
| +21 | trailer | u8 | 18 | |

**Destination enum (slot +4) — verified values:**

| Enum | Destination |
|---:|---|
| 1 | InsA Param1 (default) |
| 50 | Rev Send |
| 60 | Element Level |
| 61 | Element Pan |
| 87 | HPF Cutoff |
| 100 | Part Pan |
| 118 | MS Length |

(values >127 sätter destination_hi=1.)

**Curve Type-system (komplext, fields +10 + +12 + +8):**

| Curve | +8 | +10 | +12 | Note |
|---|---:|---:|---:|---|
| Default | 0 | 5 | 0 | Default (no ändring at edit) |
| Sigmoid | 0 | 2 | 3 | |
| Steps | 19 | 2 | 0 | 3-byte konfiguration |
| Threshold | 2 | 0 | 1 | 3-byte konfiguration |

**note: Param1 and Curve Type delar byte +10.** När man väljer a non-Default
kurva is used +10 for "curve primary code", medan in Default-läge is +10 = Param1.
This a polyvalent field where tolkningen beror on curve_secondary (+12).

verified from: AWM2_00_Init_CA_Source_AsgnKnob1..8, CA_CurveType_Sigmoid/Default/Steps/Threshold,
CA_Polarity_Bi/Uni, CA_Param1_8, CA_Param2_3, CA_Source_AsgnKnob1_Destination1_*

### Hur structureerna samarbetar

När man editerar `AsgnKnob 1 → Part 1 Assign 1` in UI (bild 31):
- **Common Control Assign slot N** sätter Source + global Destination.
- **Part 1 Control Assign slot M** specificerar per-Part destination-detaljer.
- Båda skrivs samtidigt när routing skapas in UI.

This a **double-layer routing-system**: Common is globalt, Part is
specifikt. Strukturerna is **identiska** (22 bytes stride), bara different basaddresser.

---

# 8. scene Structures ★★★★★

Två sepairsata structures: scene Struct 1 (perf-globala flags) and scene Struct 2 (per-Part Lane snapshots).

## 8.1 scene Struct 1 — perf-globala ★★★★★

```
SCENE_STRUCT1_BASE   = 1710
SCENE_STRUCT1_STRIDE = 71
SCENE_COUNT          = 8
```

**Region:** `blob[1710:2278]` = 568 bytes (8 scenes × 71 bytes).

**Per-scene field (9 field inom 71-byte record):**

| relative | Field | Encoding | Default |
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

**Per-scene SuperKnob value mirror:** `blob[+1710 + N*71 + 25..26]` (u16le, same data that per-scene SK-array at abs 184).

```python
def scene_struct1_abs(field_name, scene_idx):
    """scene_idx: 0..7"""
    return 1710 + scene_idx * 71 + SCENE_STRUCT1_FIELDS[field_name]
```

**Cross-scene-verifiering:**
- scene 4 SuperKnob @ 1925 = 1710 + 3×71 + 2 ✓
- scene 8 ArpMsFx @ 2212 = 1710 + 7×71 + 5 ✓
- scene 8 SuperKnob @ 2209 = 1710 + 7×71 + 2 ✓

## 8.2 scene Struct 2 — per-part Lane ★★★★★

```
SCENE_STRUCT2_BASE   = 7421
SCENE_STRUCT2_STRIDE = 84
```

**Region:** `blob[7421:8093]` = 672 bytes (8 scenes × 84 bytes).

**Per-scene field (11 field):**

| relative | Field | Live mirror abs | Encoding |
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

**Note:** KbdCtrl and NoteLimit per-part-toggles is located in **Struct 1** (rel 15, 16), not in Struct 2. UI-listan is förvirrande on the punkten.

**Hypotes (not verified):** scene Struct 2 is troligen active-part-baserad (84 bytes räcker not for 16 parts × 11 field).

## 8.3 Side effects at scene-editing

- `blob[+32]` ändras at scene Common offset toggle (perf-nivå master switch)
- `blob[+7417]` ändras at Scene1 AEG offset Off (160→115, mekanism unknown)
- `blob[+7419]` ändras at each per-part scene-editing (modified-flag, +1)

---

# 9. MS Sequencer ★★★★★

Region: `blob[8929:12404]` (in Part Common). Stride **884 bytes per lane** × 4 lanes.

**Lane-baser (Part 1):**

| Lane | Bas (abs) |
|---|---|
| Lane 1 | 8929 |
| Lane 2 | 9813 |
| Lane 3 | 10697 |
| Lane 4 | 11581 |

(Differens 884 ✓ verified over all 4 lanes.)

## 9.1 Per-lane offsets (relative from lane-bas) ★★★★★

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
| +116 | PulseA Type | u8 (0=Default, 2=Threshold) | 0 |
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

Sex Performance Common-field that styr Motion Seq globalt for hela
Performance. verified with dedikerade testfiler (`Sequencer_Lane1_Common_*`)
samt TEST5R3-T4b/c/d (Lane 2/3/4 Swing-test → same byte 100).

**UI-name vs internal terminologi:** I UI-vyn "Motion Seq > Common / Lane"
heter sektionen "Common". Test fileernas name (`Lane1_Common_*`) is
missvisande — the fields is **not per-Lane**, the applies all Lanes and all
Parts. Korrekt name is "Common Motion Seq" or "Performance MS".

| abs | Field | Encoding | Default | Bevis |
|---|---|---|---|---|
| 100..101 | Common MS Swing | u16le c128 | 128 | `Lane1_Common_Swing_50` |
| 102 | Common MS Unit | u8 enum (3=1/16, 0=50%) | 3 | `Lane1_Common_Unit_50%` |
| 358 | ArpSelect | u8 0-indexerat | 0 (=Arp1) | (multi-test) |
| 360 | SyncQuantize | u8 | 0 (=OFF) | `Arp_Common_SyncQuantize_120` |
| 654 | MSSelect | u8 0-indexerat | 0 (=MS1) — note: kollision with side-effect-flag (section 17) | |
| 656..657 | Common MS Amplitude | u16le c128 | 128 | `Lane1_Common_Amplitude_50` |
| 658..659 | Common MS Shape | u16le c64 | 64 | `Lane1_Common_Shape_50` |
| 660..661 | Common MS Smooth | u16le c128 | 128 | `Lane1_Common_Smooth_50` |
| 662..663 | Common MS Random | u16le c128 | 128 | `Lane1_Common_Random_50` |

## 9.3 Part Motion Sequencer (Part Common) ★★★★★

Sex Part Common-field that styr Motion Seq for hela Part (all 4 Lanes
in parten). I UI-vyn syns dessa under "Part"-sektionen, distinkt from
"Common"-sektionen ovan.

**verified** testfiler (`Lane1_Part_*`) samt TEST5R3-T4b-ViewLane2-Swing50
(View Lane 2 + Part Swing 50 → same byte 6887 that with View Lane 1).
View Lane-dropdown påverkar **not** dessa bytes — the styr only
Edit Part Sequencer-vyns visning.

| abs (Part 1) | Rel (sub-blob +N) | Field | Encoding | Default |
|---:|---:|---|---|---:|
| 6887..6888 | +186 | Part MS Swing | u16le c128 | 128 |
| 6889..6890 | +188 | Part MS Amplitude | u16le c128 | 128 |
| 6891..6892 | +190 | Part MS Shape | u16le c64 | 64 |
| 6893..6894 | +192 | Part MS Smooth | u16le c128 | 128 |
| 6895 | +194 | Part MS Random | u8 direct 0..100 | 0 |
| 7097 | +396 | Part MS Unit | u8 enum (3=1/16, 0=50%) | 3 |

**Stride:** 5765 bytes between parts (Part 2 Swing @ 12652 = 6887 + 5765).

**Shared offsets:** `abs 6887` delas with "Arp Swing" (same byte is used
for båda funktionerna). `abs 7097` delas with "Arp Unit".

## 9.4 Per-lane data (Lane-block) ★★★★★

| abs | Field | Encoding | Default |
|---|---|---|---|
| 12753 | Part seq-field | u8 (3=default, 4=seq-sync) | 3 |
| 13116 | Part arp-field | u8 (0=default, 9=arp-active) | 0 |

---

# 10. Engine data: AN-X ★★★★★

**Engine-size:** 684 bytes (689 in pool with separator).
**Pool-bas (Part 1, solo):** abs 12466 (= efter sub-blob 2's 5765 + 0 sep).

För Part N in multi-part-file: se section 3 (engine-pool addressing).

## 10.1 OSC1 / OSC2 / OSC3 — stride 125 ★★★★★

```
ANX_OSC1_BASE = 12638   # Part 1, solo
ANX_OSC_STRIDE = 125
ANX_OSC2_BASE = 12763 = 12638 + 125
ANX_OSC3_BASE = 12888 = 12638 + 250
```

**Per-OSC layout:**

| OSC1 abs | Field | Encoding | Default | Status |
|---|---|---|---|---|
| 12626 | (Wave region) | — | — | (Wave/Octave starts lite tidigare) |
| 12626 | anxOsc1Wave | enum 0..4 (Saw, Sq, ...) | 0 | ★★★★★ |
| 12628 | anxOsc1Octave | enum 0..6 | 3 (=8') | ★★★★★ |
| 12630..12631 | anxOsc1Pitch | u16le c504 (cents) | 504 | ★★★★★ |
| 12632..12633 | anxOsc1PitchEGDepth | u16le c247 | 247 | ★★★★★ |
| 12634..12635 | anxOsc1PitchEGDepthVelSens | u16le c256 | 256 | ★★★☆☆ |
| 12636..12637 | anxOsc1PitchLFODepth | u16le c247 | 247 | ★★★★★ |
| 12638..12639 | anxOsc1SelfSyncPitch | u16le direct | 0 | ★★★☆☆ |
| 12640..12641 | anxOsc1SelfSyncVelSens | u16le c256 | 256 | ★★★★★ |
| 12642..12643 | anxOsc1SelfSyncPitchEGDepth | u16le (raw = UI + 256) | 256 | ★★★★★ |
| 12644..12645 | anxOsc1SelfSyncLFODepth | u16le c256 | 256 | ★★★★★ |
| 12646 | anxOsc1PulseWidth | u8 (raw = round(pct × 256/100)) | 128 (=50%) | ★★★★★ |
| 12646..12647 | anxOsc1PulseWidthVelSens | u16le c256 | 256 | ★★★☆☆ |
| 12650..12651 | anxOsc1PulseWidthEGDepth | u16le c256 | 256 | ★★★★★ |
| 12652..12653 | anxOsc1PulseWidthLFODepth | u16le c128 | 128 | ★★★★★ |
| 12654..12655 | anxOsc1WaveShaper | u16le direct | 0 | ★★★★★ |
| 12656 | anxOsc1WaveShaperVelSens | u8 direct | 0 | ★★★★★ |
| 12658 | anxOsc1ShaperEGDepth | u8 c128 (0x80+n) | 128 | ★★★★★ |
| 12660 | anxOsc1ShaperLFODepth | u8 c128 | 128 | ★★★★★ |
| 12664 | anxOsc1FMLevelVel | direct | 0 | ★★★★★ |
| 12666 | anxOsc1RingMod3 | direct | 0 | ★★★★★ |
| 12672 | anxOsc1KeyOnReset / Invert | bool | varies | ★★★★★ |
| 12674..12675 | anxOsc1Level | u16le | 0 | ★★★★★ |

**OSC1 EG (sepairsat sub-table):**

| abs | Field | Encoding | Default |
|---|---|---|---|
| 12678..12679 | anxOsc1EGAttackTime | u16le | 0 |
| 12680..12681 | anxOsc1EGDecayTime | u16le | 160 |
| 12682..12683 | anxOsc1EGSustainLevel | u16le | 0 |
| 12684..12685 | anxOsc1EGReleaseTime | u16le | 160 |

OSC2 stride = OSC1 + 125. OSC3 stride = OSC1 + 250.

## 10.2 AN-X Filter 1 (abs 13005..13027) ★★★★★

Komplett mappad.

| Abs | Field | Encoding | Default |
|---|---|---|---|
| 13005 | filter1_type | enum | 1 (LPF12=3 verified) |
| 13007 | filter1_cutoff_lo | u16le | 255 (max default) |
| 13008 | filter1_cutoff_hi | u8 | 3 |
| 13009 | filter1_cutoff_vel | u8 | 0 |
| 13011 | filter1_feg_depth_lo | u16le | 0 |
| 13013 | filter1_feg_depth_vel | u8 | 0 |
| 13017 | filter1_cutoff_key | u8 | 0 |
| 13019 | filter1_resonance | u8 | 0 |
| 13021 | filter1_resonance_vel | u8 | 0 |
| 13023 | filter1_drive | u8 | 0 |
| 13025 | filter1_drive_vel | u8 | 0 |
| 13027 | filter1_out_level | u8 c64 | 64 (=0 dB) |

## 10.2b AN-X Filter 2 (abs 13084..13104) ★★★★★

| Abs | Field | Encoding | Default |
|---|---|---|---|
| 13081 | (pad/marker före filter2_type, default 30) | [INTERN] | 30 |
| 13082 | filter2_type | enum | 5 (HPF24) — ★★★★★ UI-confirmed (ANX bild 6: Filter 2 Type default HPF24) + cross-map ANX_FILTER +6708 |
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

### AN-X Filter-trailers — CLOSED that [INTERN] ★★★★★

Direkt efter Filter1 out_level (abs 13027) and Filter2 out_level (abs 13104) is located 3 the byte per filter with default 127. **confirmed non-UI-field** via passiv skanning of hela AN-X-testkorpusen.

| Filter1 abs | Filter2 abs | Filter1-rel | Filter2-rel | Default | Status |
|---:|---:|---:|---:|---:|---|
| 13029 | 13106 | +24 | +24 | 127 | [INTERN] |
| 13031 | 13108 | +26 | +26 | 127 | [INTERN] |
| 13033 | 13110 | +28 | +28 | 127 | [INTERN] |

**Bevisföring:**

Av **537 verkliga single-edit-testfiler** in AN-X-korpusen (files with ≤3 the byte ändrade utover standardnoise), ändrade **no** någon of the 6 trailer-the byte. only multi-edit-files (>50 the byte ändrade — structureella rekonstruktioner snarare än single-edits) påverkar trailer-the byte. This **definitivt bevis** att the not is direkt-UI-mapped.

**Möjliga interna funktioner:**

- Reserved space for framtida firmware-utöknnor
- Internal calibration constants
- ESP Plugin "scratch buffer" that regenereras at load

**Praktisk implementation:**

- LÄSNING: Ignorera
- SKRIVNING: write the value 127 (säkert default)
- Klassificering: [INTERN] (same kategori as AWM2 rel +312 inter-element separator)

## 10.3 AN-X WaveFolder + Mod EG + Mod LFO ★★★★★ 

| Abs | Field | Encoding | Default | Note |
|---|---|---|---|---|
| 13116 | wavefolder_amount | u8 | 0 | UI: Modifier > Folder > Wave Folder |
| 13118 | wavefolder_vel | u8 | 0 | UI: Modifier > Folder > Folder/Vel |
| 13120 | wavefolder_eg_depth | u16le? | 128 (lo) | ★★★★★ UI-confirmed (ANX bild 5: Modifier > EG Depth) + cross-map ANX_MODIFIER +6708 |
| 13122 | modlfo_depth | u8 c128 | 128 | ★★★★★ UI: Modifier > LFO > LFO Depth. Binary-verified with Test-ANX-Mod_LFO_Depth_50.Y2L (50 → 178 in c128). ANX_MODIFIER:s alternativname "anxWaveFolderLFODepth" refererar to same byte — not sepairsat field. |
| 13124 | wavefolder_texture | u16le? | 128 (lo) | ★★★★★ UI-confirmed (ANX bild 5: Modifier > Folder > Texture) + cross-map ANX_MODIFIER +6708 |
| 13126 | wavefolder_type | enum | 1 | Hard=1, Soft=0. UI: Modifier > Folder > Type |
| 13128 | modeg_attack | u8 | 0 | UI: Modifier > EG > Attack |
| 13130 | modeg_decay | u8 | 160 | UI: Modifier > EG > Decay |
| 13132 | modeg_sustain | u8 | 0 | UI: Modifier > EG > Sustain |
| 13134 | modeg_release | u8 | 160 | UI: Modifier > EG > Release |
| 13138 | modlfo_wave | enum | 2 | Triangle=2, Square=1. UI: Modifier > LFO > Wave |
| 13140 | modlfo_speed_lo | u16le | 208 | UI: Modifier > LFO > Speed |
| 13146 | modlfo_delay | u8 | 0 | UI: Modifier > LFO > Delay |
| 13148 | modlfo_fadein | u8 | 0 | UI: Modifier > LFO > Fade In |

Modifier-fliken har **only EN** "LFO Depth"-knapp (abs 13122) — it exists no sepairsat byte for "Wave Folder LFO Depth".

## 10.4 AN-X Pre-OSC (Part Settings, Pitch LFO, Filter LFO, Amp + Amp LFO) ★★★★★

**STORT UTÖKAD ** — 27 new field identifierade and mapped.

### Part Settings (Pre-OSC topp):

| Abs | Field | Encoding | Default | Note |
|---|---|---|---|---|
| 12467 | alternate_pan_anx | u8 c64 | 64 | AlternatePan R50 → 114 |
| 12469 | scaling_pan_anx | u8 c64 | 64 | ScalingPan 50 → 114 |
| 12477 | unison_voices | u8 enum | 0 | Off=0, 2=1, 4=2 |
| 12479 | unison_detune | u8 | 0 | |
| 12481 | unison_spread | u8 | 0 | |
| 12485 | osc_reset_mode | u8 enum | 0 | Off=0, Phase=1, Tune=2, Full=3 |
| 12487 | voltage_drift | u8 | 64 | |
| 12489 | ageing | u8 | 100 | +50 → 150 |

### Pitch LFO + PEG-block (12499-12511):

| Abs | Field | Encoding | Default | Note |
|---|---|---|---|---|
| 12499 | peg_time_vel | u8 | 0 | |
| 12503 | pitch_lfo_speed_lo | u16le | 208 | |
| 12507 | pitch_lfo_phase | u8 enum | 0 | **16-step enum** 0..15, ~22.5° per step |
| 12509 | pitch_lfo_delay | u8 | 0 | |
| 12511 | pitch_lfo_fadein | u8 | 0 | |

### FEG-block (12521-12529) — preliminärt:

| Abs | Field | Encoding | Default | Note |
|---|---|---|---|---|
| 12521 | feg_attack | u8 | 0 | preliminär — not verified  |
| 12529 | feg_time_vel | u8 | 0 | preliminär |

### Filter LFO-block (12531-12541) — COMPLETE NEW:

| Abs | Field | Encoding | Default | Note |
|---|---|---|---|---|
| 12531 | filter_lfo_wave | u8 enum | 2 | Triangle=2, Square=1 |
| 12533 | filter_lfo_speed_lo | u16le | 208 | |
| 12537 | filter_lfo_phase | u8 enum | 0 | 16-step enum |
| 12539 | filter_lfo_delay | u8 | 0 | |
| 12541 | filter_lfo_fadein | u8 | 0 | |

### Amp-block (12543-12551) — COMPLETE NEW:

| Abs | Field | Encoding | Default | Note |
|---|---|---|---|---|
| 12543 | amp_level | u16le | 431 | default 431 lo+hi|
| 12545 | amp_level_vel | u8 | 0 | +50 → 50 |
| 12547 | amp_lfo_depth | u8 c128 | 128 | LFO Depth +50 → 178 |
| 12549 | amp_level_key | u8 | 0 | +50 → 50 |
| 12551 | amp_drive | u8 | 0 | 50.25dB → 67, ~0.75dB/unit |

### Amp AEG (12553-12561):

| Abs | Field | Encoding | Default |
|---|---|---|---|
| 12553 | amp_aeg_attack | u8 | 0 |
| 12555 | amp_aeg_decay | u8 | 160 |
| 12557 | amp_aeg_sustain_lo | u16le | 511 (max) |
| 12559 | amp_aeg_release | u8 | 115 |
| 12561 | aeg_time_vel_lo | u16le ± | 0 |

### Amp LFO-block (12563-12573) — COMPLETE NEW:

| Abs | Field | Encoding | Default | Note |
|---|---|---|---|---|
| 12563 | amp_lfo_wave | u8 enum | 2 | Triangle=2, Square=1 |
| 12565 | amp_lfo_speed_lo | u16le | 208 | |
| 12569 | amp_lfo_phase | u8 enum | 0 | 16-step enum |
| 12571 | amp_lfo_delay | u8 | 0 | |
| 12573 | amp_lfo_fadein | u8 | 0 | |

### AN-X har FYRA LFO-system :

1. **Pitch LFO** (Pre-OSC 12499-12511, Speed=12503) — modulerar pitch
2. **Filter LFO** (Pre-OSC 12531-12541, Speed=12533) — modulerar Filter1/Filter2 cutoff
3. **Amp LFO** (Pre-OSC 12563-12573, Speed=12565) — modulerar amp
4. **Mod LFO** (Post-OSC3, Speed=13140) — matrix-baserad to 3 destinations

all 4 har: Wave, Speed (u16le), Phase, Delay, Fade In.
Filter1/Filter2 har individuella LFO Depth-field (abs 13015 / 13092).

### Pitch LFO Phase enum-difference against AWM2:

- AWM2 LFO Element Matrix Phase: 6 step (0=0°, 1=90°, 2=120°, 3=180°, 4=240°, 5=270°)
- AN-X Pitch/Filter/Amp LFO Phase: **16 step** (0..15) with 22.5° per step
  - 90° → enum 4
  - 180° → enum 8
  - 270° → enum 12
  - 315° → enum 14

## 10.5 AN-X OSC-structure (stride 125) ★★★★★

**KRITISK KORRIGERING:** Stride is **125 bytes**, not 124. OSC-baser:
- OSC1 = 12631 (oförändrad)
- OSC2 = **12756** (KORRIGERING from 12755)
- OSC3 = **12881** (KORRIGERING from 12880)

verified with.

| Rel | Field | Encoding | Default |
|---:|---|---|---|
| 0 | osc_pitch | u8 | 1 |
| 1 | osc_peg_depth_lo | u8 | 247 |
| 3 | osc_peg_depth_vel | u8 | 0 |
| 5 | osc_pitch_lfo_depth_lo | u8 | 247 |
| 9 | osc_sync_pitch_vel | u8 | 0 |
| 11 | osc_eg_depth_sync | u8 | 0 |
| 13 | osc_lfo_sync_depth | u8 | 0 |
| 15 | osc_pulse_width | u8 c128 | 128 |
| 19 | osc_eg_depth_pulse_width | u16le c128 | 128 |
| 21 | osc_lfo_depth_pulse_width | u16le c128 | 128 |
| 25 | osc_wave_shaper_vel | u8 | 0 |
| 27 | osc_shaper_eg_depth | u16le c128 | 128 |
| 29 | osc_shaper_lfo_depth | u16le c128 | 128 |
| 31 | osc_fm_ringmod | u8 | 0 |
| 33 | osc_fm_level_vel | u8 | 0 |
| 35 | osc_self_sync_src | u8 | 0 |
| 41 | osc_invert | u8 bool | 0 |
| 43 | osc_out_level_lo | u16le | 511 (255+1) |
| 45 | osc_out_level_vel | u8 | 0 |
| 47 | osc_eg_attack | u8 | 0 |
| 49 | osc_eg_decay | u8 | 160 |
| 51 | osc_eg_sustain | u8 | 0 |
| 53 | osc_eg_release | u8 | 160 |
| 67 | mod_lfo_ratio_row1 | u8 | 127 |
| 69 | mod_lfo_ratio_row2 | u8 | 127 |
| 71 | mod_lfo_ratio_row3 | u8 | 127 |

## 10.6 AN-X Mod LFO Destination Matrix ★★★★★

Mod LFO har 3 destination-rows, each row innehåller:
- Destination (enum) — Part Common-field
- Depth (Part Common-field)
- 3 Oscillator Depth Ratios — a per OSC (in engine-pool, OSC rel +67/+69/+71)

**note:** Strukturen DELAS with AWM2 LFO Element Matrix. Båda
engines uses same Part Common-addresser. only destinations enum-values
vary per engine.

**Part Common-field:**
- `Part rel +498` (abs 7199) mod_lfo_phase
- `Part rel +516` mod_lfo_dest1 (default 2)
- `Part rel +518` mod_lfo_dest1_depth
- `Part rel +520` mod_lfo_dest2 (default 4)
- `Part rel +522` mod_lfo_dest2_depth
- `Part rel +524` mod_lfo_dest3 (default 4)
- `Part rel +526` mod_lfo_dest3_depth

**Destination enum-values for AN-X:**
- Osc Level = 83
- InsAParam3 = 3, InsAParam5 = 5, InsAParam7 = 6
- (fler unmapped)

Per OSC exists 3 "lane depths" that modulerar different destinations:
- OSC rel +67 = mod_lfo_ratio_row1 (for dest1)
- OSC rel +69 = mod_lfo_ratio_row2 (for dest2)
- OSC rel +71 = mod_lfo_ratio_row3 (for dest3)

## 10.7 AN-X routing-matriser ★★★★☆

5 stycken 40-byte routing-tabeller in AN-X engine-pool:

| Matrix | Abs-range | Kontext |
|---|---|---|
| Matrix A | 12582..12621 | efter Pre-OSC, före OSC1 |
| Matrix B | 12707..12746 | efter OSC1, före OSC2 |
| Matrix C | 12832..12871 | efter OSC2, före OSC3 |
| Matrix D | 12961..13000 | efter OSC3, före Filter1 |
| Matrix E | 13038..13077 | efter Filter1, före Filter2 |

**Strukturidentifierad men not UI-mappbar:**

- I baseline (Init Normal) har all 5 matriser identiskt mönster: `[39, 1, 1, ..., 1]` 
  (1 byte = 39, sedan 39 byte = 1).
- I real patches innehåller matriserna verkliga modulation-routing-data — 
  blandad u16le + u8 (sources and depth-values).
- **Verification:** Av 380 Part1-single-edit-tester ändrar no någon byte 
  in matriserna. The is not direkt UI-redigerbara.

**Interpretation:** Matriserna is NOTRNA routing-tabeller that ESP-pluginen sätter 
implicit baserat on engine-konfiguration. The skrivs när a patch spairsas men 
påverkas not of enskilda UI-knappairs.

**Klassificering: [INTERN][STRUKT]** — structureellt identifierat, men not 
UI-mappbart from single-edit tester. Vid serialization is preserved rådata 1:1 
(passthrough). The påverkar not editor-funktionaliteten.

structure-hypoteser (from real-patch-analys, not slutligt verified):
- Matrix A and E ser ut att ha "u16le-aligned" format (header_size=0 or 2)
- Matrix B and D ser ut att ha "1-byte offset" format (header_size=1 or 3)
- Matrix C is ofta tom (mestadels zeros in real patches)

UI-täckning AN-X: **~70%** (73 of 110 verkliga UI-bytes mapped)

**Räknebakgrund:** AN-X engine-pool is 684 bytes with 352 non-zero bytes.
Av dessa is 200 sammanhängande routing-tabeller (5 × 40-byte matriserna ovan)
and ytterligare 42 is lösa routing-flags utspridda in poolen. It ger
110 "verkliga UI-bytes" att mappa. 73 is mapped 37 kvarstår.

---

## 10.9 AWM2 Element Count-architecture ★★★★★

**Genombrott:** AWM2-engine is not begränsad to 8 element per Part — UI:t in ESP Plugin v3.0 exponerar **Element Count** with värdena 8 (default), 16, 32, 64 and 128.

### Två synkroniserade Element Count-bytes

Element Count-the value lagras on TVÅ platser that always har identiska values:

| Plats | Address (14969-byte payload) | Address (38985-byte container) | Note |
|---|---|---|---|
| Part Common rel +196 | abs 6897 | abs 7588 | Part-level UI-styrd byte (`elementCount_rel`) |
| Engine header byte 0 | abs 12464 | abs 13151 | Engine pool header (= "E1 base − 5") |

ESP-pluginen writes båda the byte samtidigt när Element Count ändras in UI.

### Dynamic element-array expansion

När Element Count > 8 utökas element-arrayen genom att lägga in extra 313-byte stride-element direkt efter element 8. Resten of engine-poolen (trailer, eventuella sekunwherea structures) flyttas bakåt with exactly `(EC − 8) × 313` bytes:

| Element Count | Filstorlek | Delta vs EC=8 | Element-array slut (in 38985-file) |
|---:|---:|---:|---:|
| 8 (default) | 38985 | 0 | abs 15660 |
| 16 | 41489 | +2504 (= 8 × 313) | abs 18164 |
| 32 | 46497 | +7512 (= 24 × 313) | abs 23172 |
| 64 | 56513 | +17528 (= 56 × 313) | abs 33188 |
| 128 | 76545 | +37560 (= 120 × 313) | abs 53220 |

verified exactly (0 bytes diff) for all 5 testfall.

### Consequenceer for editor-architecture

**all 313-byte element-field applies direkt for element 9..128.** each extra element har full field-mapping enligt vår AWM2_ELEMENT_FIELDS-table:
- XA Control (rel +67), Pan (rel +59), AEG (rel +91..+143), Filter+FEG (rel +201..+265), LFO (rel +283..+307), etc.
- Default-values for "tomma" element (rel +0 = 0, dvs `enable=0`)

Beräkning of abs-address for element N in a EC=128-file (in 14969-byte payload-addressing):
```
abs = 12469 + (N − 1) × 313    # N = 1..128
```

### Hash/CRC-bytes that skalar with EC

Följande bytes ändras always när Element Count ändras (filhash that beror on hela filinnehållet — not direkta UI-pairsametrar):
- `abs 102, 103, 110, 111, 375, 673, 674, 685, 686` (in 38985-file)

Dessa should läggas to a EC-känslig NOISE-lista at byte-coverage-analys of EC-tester.

### Multi-Parts mode (Sw_ON_MultiplePartsElements)

Vid sidan of Element Count exists a sepairsat toggle that aktiverar fler Parts:
- A extra Part lägger to exactly **24819 bytes** (constant, oberoende of Element Count for Part 1)
- Bonus-testfil with EC=128 + flera Parts + 128 element per Part is 214044 bytes — multi-part-structureen is not fullt analyserad än

UI-täckning Part Common Element Count: **★★★★★** (5 EC-values verified)

---

# 11. Engine data: AWM2 ★★★★★

**Engine-size:** 2503 bytes (2508 in pool with separator).

## 11.1 Element-architecture ★★★★★

**Korrekta values (verified with TEST5R3-T5a/e Element Enable-toggle):**

```python
AWM2_HEADER_SIZE        = 3        # bytes före first elementet (header signature: 00 00 2b)
AWM2_ELEMENT_STRIDE     = 313      # bytes per element (E1-E7)
AWM2_LAST_ELEMENT_SIZE  = 309      # E8 är 4 bytes kortare än övriga
AWM2_ELEMENT_COUNT      = 8        # 8 elements per AWM2 part
```

**layout:** 3 (header) + 7 × 313 + 309 = **2503 bytes total** ✓

**Element-positions (Part 1 solo, engine @ abs 12466):**

| Element | Engine-relative | Abs (Enable byte) | Defaults |
|---|---:|---:|---|
| E1 | +3 | 12469 | enable=1 (ON) |
| E2 | +316 | 12782 | enable=0 (OFF) |
| E3 | +629 | 13095 | enable=0 |
| E4 | +942 | 13408 | enable=0 |
| E5 | +1255 | 13721 | enable=0 |
| E6 | +1568 | 14034 | enable=0 |
| E7 | +1881 | 14347 | enable=0 |
| E8 | +2194 | 14660 | enable=0 (E8 = 309b) |

**Default Init Voice:** only **Element 1 is ON**, E2-E8 is OFF.
För FM-X exists no ON/OFF per OP — istället exists **Mute** and **Solo** per OP samt **Level** 0..127.

```python
def get_awm2_element_offset(element_idx: int) -> int:
    """Returns rel offset within AWM2 engine for element 0..7."""
    return 3 + element_idx * 313

def get_awm2_element_addr(engine_start_abs: int, element_idx: int) -> int:
    return engine_start_abs + get_awm2_element_offset(element_idx)
```

## 11.2 AWM2 Element-field (313 bytes per element) ★★★★★

**offsets relative to element-base** (Element 1 base = abs 12469).

**120 verified field per element × 8 elements = 960 verified AWM2 element-positions totalt.**

Stride 313 verified for all 8 element.

| Rel | Field | Encoding | Default | Note |
|---:|---|---|---:|---|
| 0 | element_header | u8 | varies | (E1=1, E2-8=0 in Init) |
| 1 | keyondly_sync | u8 bool | 0 | KeyOnDly Sync toggle |
| 2 | aeg_half_damper | u8 bool | 0 | |
| 6 | extended_lfo | u8 bool | 1 | ★★★★★ binärverifierat with Test-AWM2-ElementLFO-ExtendedLFO_ON/OFF.Y2L. Default ON for Init Normal AWM2. Bestämmer vilken Speed-byte UI visar — rel +289 när AV, rel +307 när PÅ |
| 49 | elem_group | u8 direct | 0 | Element Group 1..8 (0=Group 1) |
| 51 | waveform_lo | u8 | varies | Waveform index (lo) |
| 59 | pan | u8 c64 | 64 | |
| 61 | aeg_random_pan | u8 | 0 | max 127 |
| 63 | aeg_alternate_pan | u8 c64 | 64 | |
| 65 | aeg_scaling_pan | u8 c64 | 64 | |
| 69 | note_limit_low | u8 MIDI | 0 | |
| 71 | note_limit_high | u8 MIDI | 127 | |
| 73 | vel_limit_low | u8 | 1 | |
| 75 | vel_limit_high | u8 | 127 | |
| 77 | vel_xfade | u8 | 0 | |
| 79 | delay_length | u8 | 0 | |
| 81 | elem_connect | u8 enum | 1 | 0=Thru, 1=InsA, 2=InsB |
| 85 | keyondly_sync_delay | u8 | 11 | |
| 91 | level | u8 direct | 127 | |
| 93 | amp_level_vel | u8 c64 | 64 | |
| 95 | aeg_offset | u8 c64 | 0 | max 127 |
| 97 | amp_level_curve | u8 | 3 | |
| 99 | aeg_attack | u8 | 0 | |
| 101 | aeg_decay1 | u8 c64 | 64 | |
| 103 | aeg_decay2 | u8 c64 | 64 | |
| 105 | aeg_half_damper_time | u8 | 127 | |
| 107 | aeg_release | u8 | 50 | |
| 109 | aeg_initial_level | u8 | 0 | |
| 111 | aeg_attack_level | u8 | 127 | |
| 113 | aeg_decay1_level | u8 | 127 | |
| 115 | aeg_decay2_level | u8 | 127 | |
| 117 | amp_segment_decay | u8 | 4 | |
| 119 | amp_time_vel | u8 c64 | 64 | |
| 121-143 | AMP Level Scaling block | (se nedan) | | 5 BreakPoints + 4 offsets |
| 141 | level_key | u8 c64 | 64 | |
| 149 | coarse_tune | u8 c64 | 64 | ±20 semitones via UI |
| 151 | fine_tune | u8 c64 | 64 | |
| 153 | pitch_vel | u8 c64 | 64 | |
| 155 | pitch_random | u8 | 0 | |
| 157 | pitch_key | u8 | 96 | |
| 161 | fine_key | u8 c64 | 64 | |
| 163-195 | PEG-block | (se nedan) | | Komplett from TEST-PEG-* tester |
| 201 | filter_type | u8 enum | 4 | LPF24A=1, LPF18=2, default=4, DualBEF=17 |
| 203-204 | filter_cutoff | u16le | 128 (max 1023) | |
| 205 | filter_cutoff_vel | u8 c64 | 64 | |
| 207 | filter_resonance | u8 | 0 | |
| 209 | filter_resonance_vel | u8 c64 | 64 | |
| 211-212 | hpf_cutoff | u16le | 0 | |
| 213 | filter_distance | u8 c128 | 128 | DualBEF Distance |
| 215 | filter_gain | u8 | 230 | |
| 219-241 | FEG-block | (se nedan) | | Filter Envelope, komplett |
| 247-265 | Filter Level Scaling | (se nedan) | | Parallell to AMP Level Scaling |
| 267 | element_edit_counter | u8 | 74 | [INTERN] increments on edit |
| 269 | hpf_cutoff_key | u8 c64 | 64 | |
| 271-281 | EQ-block | (se nedan) | | |
| 283 | lfo_wave | u8 enum | 1 | Saw=0, Tri=1, Square=2 |
| 285 | lfo_keyonreset | u8 bool | 1 | |
| 287 | lfo_delay | u8 | 0 | |
| 291 | lfo_amp_mod_depth | u8 | 0 | |
| 293 | lfo_pitch_mod_depth | u8 | 0 | |
| 295 | lfo_filter_mod_depth | u8 | 0 | |
| 297 | lfo_fade_in | u8 | 0 | |
| 299 | element_lfo_phase_offset | u8 enum | 0 | LFO Matrix Phase offset (0..5) |
| 301 | element_lfo_dest1_depth | u8 | 127 | LFO Matrix Row 1 |
| 303 | element_lfo_dest2_depth | u8 | 127 | LFO Matrix Row 2 |
| 305 | element_lfo_dest3_depth | u8 | 127 | LFO Matrix Row 3 |
| 307 | lfo_speed | u8 | 60 | |

### AMP Level Scaling block (rel 121-143) ★★★★★

5 BreakPoints (CenterKey + BP1-BP4) and 4 offsets ebetween. Defaults at C0/C1/C2/C3/C4 jämnt fördelat.

| Rel | Field | Default |
|---:|---|---:|
| 121 | amp_time_key | 64 |
| 123 | amp_scaling_center_key | 24 (C0) |
| 125 | amp_scaling_bp1 | 36 (C1) |
| 127 | amp_scaling_bp2 | 48 (C2) |
| 129 | amp_scaling_bp3 | 60 (C3) |
| 131 | amp_scaling_bp4 | 72 (C4) |
| 133 | amp_scaling_offset1 | 128 (=0 dB) |
| 135 | amp_scaling_offset2 | 128 |
| 137 | amp_scaling_offset3 | 128 |
| 139 | amp_scaling_offset4 | 128 |
| 143 | amp_release_adj | 64 |

### PEG-block (rel 163-195) ★★★★★

Komplett mappad from TEST-PEG-* tester.

| Rel | Field | Encoding | Default |
|---:|---|---|---:|
| 163 | peg_hold_time | u8 | 0 |
| 169 | peg_signature | u8 | 64 | [INTERN] PEG-edit marker, ändras 64→76 in all PEG-edits |
| 173 | peg_level_hold | u8 c128 | 128 |
| 175 | peg_level_attack | u8 c128 | 128 |
| 177 | peg_level_decay1 | u8 c128 | 128 |
| 179 | peg_level_decay2 | u8 c128 | 128 |
| 181 | peg_level_release | u8 c128 | 128 |
| 187 | peg_time_vel | u8 c64 | 64 |
| 189 | peg_depth_vel | u8 c64 | 64 |
| 193 | peg_time_key | u8 c64 | 64 |
| 195 | peg_center_key | u8 MIDI | 60 (=C3) |

### FEG-block (rel 219-241) ★★★★★

Filter Envelope, mappat.

| Rel | Field | Encoding | Default |
|---:|---|---|---:|
| 219 | filter_time_attack | u8 | 0 |
| 221 | filter_time_decay1 | u8 c64 | 64 |
| 223 | filter_time_decay2 | u8 c64 | 64 |
| 225 | filter_time_release | u8 | 80 |
| 227 | filter_level_hold | u8 c128 | 128 |
| 229 | filter_level_attack | u8 | 255 |
| 231 | filter_level_decay1 | u8 | 255 |
| 233 | filter_level_decay2 | u8 | 255 |
| 235 | filter_level_release | u8 c128 | 128 |
| 237 | filter_feg_depth | u8 c104 | 104 |
| 239 | filter_segment | u8 | 4 |
| 241 | filter_time_vel | u8 c64 | 64 |

### Filter Level Scaling (rel 247-265) ★★★★★

Parallell to AMP Level Scaling.

| Rel | Field | Default |
|---:|---|---:|
| 247 | filter_time_key | 64 |
| 249 | filter_scaling_center_key | 24 (C0) |
| 251-257 | filter_scaling_bp1..bp4 | 36/48/60/72 |
| 259-265 | filter_scaling_cutoff_offset1..offset4 | 128 (c128) |

### EQ-block (rel 271-281) ★★★★★

EQ Type styr vilka övriga field that is active.

| Rel | Field | Encoding | Default | Note |
|---:|---|---|---:|---|
| 271 | eq_type | u8 enum | 0 | 0=2-band, 1=P.EQ, 2=Boost6 |
| 273 | eq_q_or_resonance | u8 | 0 | I P.EQ-mode = Q |
| 275 | eq_low_freq | u8 | 54 | I 2-band-mode = LowFreq, in P.EQ = EQ Frequency |
| 277 | eq_low_gain | u8 c64 | 64 | I 2-band-mode = LowGain, in P.EQ = EQ Gain |
| 279 | eq_high_freq | u8 | 231 | (2-band only) |
| 281 | eq_high_gain | u8 c64 | 64 | (2-band only) |

**EQ Type-values:**
- 0 = 2-band (default)
- 1 = P.EQ (Parametric)
- 2 = Boost 6
- 3 = Boost 12
- 4 = Boost 18
- 5 = Thru

with Boost-typer skrivs förinställda values to rel 275/277/279/281; användaren can not justera EQ-pairsametrar.

### LFO Element Matrix ★★★★★

AWM2 LFO Element Matrix delar Part Common-addresser with AN-X Mod LFO Matrix. Per-element field:

| Rel | Field | Note |
|---:|---|---|
| 299 | element_lfo_phase_offset | 0=0°, 1=90°, 2=120°, 3=180°, 4=240°, 5=270° |
| 301 | element_lfo_dest1_depth | Element Depth Ratio Row 1 (default Level) |
| 303 | element_lfo_dest2_depth | Element Depth Ratio Row 2 (default Cutoff) |
| 305 | element_lfo_dest3_depth | Element Depth Ratio Row 3 (default Pitch) |

Part Common-field (delas with AN-X):
- `Part rel +498` (abs 7199) lfo_phase
- `Part rel +516/520/524` dest1/dest2/dest3 (AWM2: Level=64, Cutoff=66, Pitch=65)
- `Part rel +518/522/526` dest1/dest2/dest3 depth

## 11.3 AWM2 element-byte-detaljer

AWM2 element-structureen is **kartlagd & verified**.

### UI-bekräftade field ★★★★★

Konversionsformel: `AWM2_ELEM_LAYOUT_offset + 51 = AWM2_ELEMENT_FIELDS_rel`. UI-confirmed via skärmdumpairs from ESP Plugin v3.0.

| Rel | Default | Field | UI-source | Strukturkälla |
|---:|---:|---|---|---|
| 159 | 60 (C3) | `pegKFCenterNote` | AWM2 bild 2: [ELEMENT] Pitch EG > Center Key = C 3 | AWM2_ELEM_LAYOUT off=108 |
| 289 | 38 | `lfoSpeed` (normal, not Extended) | AWM2 bild 6: [ELEMENT] LFO > Speed (knapp visad när Extended LFO toggle is AV) | AWM2_ELEM_LAYOUT off=238 |

### FEG-block-structureen on rel +243 ★★★★★

Binary-verified via PEG/FEG-symmetri (all 6 PEG-field is binärverifierade ★★★★★) and dedikerad single-edit-testfil Test-AWM2-Filter_FEG_DepthVel_50.Y2L.

**PEG/FEG-symmetri:** FEG-blocket is PEG-blocket förskjutet +54 bytes:

| UI-name | PEG rel | FEG rel | Förskjutning |
|---|---:|---:|---:|
| Segment | +185 | +239 | +54 |
| Time/Vel | +187 | +241 | +54 |
| **Depth/Vel** | **+189** | **+243** | **+54** |
| Curve | +191 | +245 | +54 |
| Time/Key | +193 | +247 | +54 |
| Center Key | +195 | +249 | +54 |

**UI-verifiering:** AWM2 bild 3 ([ELEMENT] Filter) visar FEG-block with exactly **5 sepairsata kontroller**: Time/Vel, Segment, FEG Depth, **Depth/Vel**, Curve. Plus Time/Key and Center Key in Level Scaling-zon. Totalt 7 kontroller that matchar +237, +239, +241, **+243**, +245, +247, +249.

**Binärbaseline-verifiering** (from Test-AWM2-ElementLFO-ExtendedLFO_OFF.Y2L):

| Rel | Default | Field | UI-name | Status |
|---:|---:|---|---|:---:|
| +237 | 104 | `feg_depth` | FEG Depth | ★★★★★ |
| +239 | 4 (All) | `feg_segment` | Segment | ★★★★★ |
| +241 | 64 | `feg_time_vel` | Time/Vel | ★★★★★ |
| +243 | 64 | **`feg_depth_vel`** | **Depth/Vel** | **★★★★★** |

**Binärverifiering of rel +243:** Test-AWM2-Filter_FEG_DepthVel_50.Y2L sätter UI-the value Depth/Vel to +50. Diff against baseline visar exactly EN byte ändrad: rel +243 from 64 to 114 (= 64 + 50 in c64-encoding). Inga second bytes påverkas. UI-confirmed and baseline-confirmed enligt PEG-pairsallell on rel +189.

| +245 | 2 | `filter_curve` (alias `feg_curve`) | Curve | ★★★★★ |
| +247 | 64 | `filter_time_key` (alias `feg_time_key`) | Time/Key | ★★★★★ |
| +249 | 24 (C0) | `filter_scaling_center_key` (alias `feg_center_key`) | Center Key | ★★★★★ |

**Kanoniska fältname (`AWM2_ELEM_LAYOUT`):**

| Off | name |
|---:|---|
| 192 | `feg_depth_vel` |
| 194 | `feg_curve` |
| 196 | `feg_time_key` |

### AWM2 element [INTERN]-bytes (non-UI, firmware constants)

| Rel | Default | Status |
|---:|---:|---|
| 46 | 40 | [INTERN] firmware-constant. Skannat 408 AWM2-files — **100% constant**. |
| 90 | 54 | [INTERN] firmware-constant. Skannat 408 AWM2-files — **100% constant**. |
| 148 | 48 | [INTERN] firmware-constant. Skannat 408 AWM2-files — **100% constant**. |
| 200 | 108 | [INTERN] firmware-constant. Skannat 408 AWM2-files — **100% constant**. |
| 309 | 0 | Padding (passivt verified) |
| 310 | 0 | Padding (passivt verified) |
| 311 | 0 | Padding (passivt verified) |
| 312 | 43 (0x2B '+') | Inter-element separator (passivt verified in 4 testfiler × 7 element). Element 8 visar avvikande value p.g.a. DSYS-chunken starts direkt efter Element 8 without padding-zon. |

**Per-element sammanställning:**
- 128 UI-mapped field ★★★★★
- 8 [INTERN]-bytes
- ~177 multi-byte split-bytes (u16le hi-bytes etc, redan räknade in UI-field)
- = 313 bytes per element ✓

Övriga binärverifierade field:
- rel +67 → `xa_control` (enum 0..7)
- rel +191 → `peg_curve` (enum 1..4, default 2)
- rel +245 → `filter_curve` (enum 0..4, default 2)

UI-täckning per AWM2-element: **all bytes redovisade** (all bytes redovisade — antingen UI-mapped or [INTERN])

### Binary-verified ★★★★★: Extended LFO and Speed-bytes

with `Test-AWM2-ElementLFO-ExtendedLFO_ON.Y2L` vs `_OFF.Y2L` (diff = 1 byte at audit abs 12475 = Element 1 rel +6) verified:

| Rel | Field | Encoding | Default | Status |
|---:|---|---|---:|---|
| +6 | `extended_lfo` | u8 bool | **1 (ON)** for Init Normal AWM2 | ★★★★★ |
| +289 | `lfoSpeed` | u8 0..63 | 38 | ★★★★★ — active UI-byte när `extended_lfo`=0 |
| +307 | `lfo_extended_speed` | u16le 0..415 | 60 | ★★★★★ — active UI-byte när `extended_lfo`=1 |

**important architecture-observation:** Speed-the value lagras in TVÅ sepairsata bytes:
- `lfoSpeed` (rel +289, u8 0..63) — UI visar 0..63-skala
- `lfo_extended_speed` (rel +307/+308, u16le 0..415) — UI visar 0..415-skala

Båda lagras always simultant in the file. `extended_lfo`-toggle (rel +6) bestämmer only vilken byte UI:t visar and redigerar. This mönster återfinns also in FM-X (`fmxPart2ndLfoSpeedNormal` @ 12511, `fmxPart2ndLfoSpeedExtended` @ 12531).

### Convention: AWM2-addressingsbaser (3 different konventioner)

It exists **tre different "base"-addresser** for Element 1 in projektet, that ger different offset-numrernor:

| Convention | Element 1 base | Source | Användning |
|---|---:|---|---|
| audit abs | 12469 | parameterbetygsfilen, byte-coverage-detail.txt, audit-filerna, denna referens | Dokumentation, single-edit-tester |
| `AWM2_ELEM_LAYOUT` ELEM_BASE | 12520 | serializer row 3115/3250 | active produktionskod (läs/write) |
| `AWM2_ELEM1_BASE` | 12532 | serializer row 222 | Filoffset-beräkning at binärverifiering |

**Konversioner between dem:**

```
AWM2_ELEM_LAYOUT_offset + 51 = AWM2_ELEMENT_FIELDS_rel  (audit-rel)
audit_abs                    = AWM2_ELEM_LAYOUT_offset + 12520
audit_abs                    = AWM2_ELEM1_BASE_offset - 63
```

**Filoffset-konversion at binär-diff-analys of Y2L-files:**

```
filoffset  = audit_abs + 687
audit_abs  = filoffset - 687
```

Konstanten 687 is summan of file-header + all pre-DPFM-chunks + DPFM sub-blob-header + Performance Name-prefix. Verified genom att `waveform_lo = 6` (Init Normal AWM2 Element 1 = CFX v06 St) is located on filoffset `687 + 12469 + 51 = 13207`.

**FALLGROP:** Vid räkning of byte-offsets in binärdumps is it lätt att blanda ihop dessa konventioner. `extended_lfo` is **rel +6** (audit-konvention) = **ELEM_LAYOUT off −45**; used not 51-byte-konversionen between `AWM2_ELEM_LAYOUT` and `AWM2_ELEMENT_FIELDS` on this field.

Field that exists in `AWM2_ELEM_LAYOUT` men is missing in `AWM2_ELEMENT_FIELDS`: `pegKFCenterNote`, `feg_time_vel`, `lfoSpeed` — all tre dokumenterade ovan.

---

# 12. Engine data: FM-X ★★★★★

**Engine-size:** 1143 bytes (1148 in pool with separator).

## 12.1 OP-architecture

```
FMX_OP1_BASE  = 12676   # Part 1, solo
FMX_OP_STRIDE = 123     # bytes per OP
FMX_OP_COUNT  = 8
```

8 OPs, layout is identisk per OP. För OP N (N=1..8): `FMX_OPN_BASE = 12676 + (N-1) × 123`.

## 12.2 FM-X OP layout (per OP, relative to OP_BASE) ★★★★★

**Pre-OP block (negativa offsets from OP_BASE):**

| Rel | Field | Encoding | Default |
|---|---|---|---|
| -4 | keyOnReset | bool | 1=On |
| -2 | freqMode | enum 0=Ratio, 1=Fixed | 0 |

**Freq / Spectral block (rel 0..14):**

| Rel | Field | Encoding | Default |
|---|---|---|---|
| 0 | coarse | direct | 1 |
| 2 | fine | direct | 0 |
| 4 | detune | c15 | 0 |
| 6 | pitchKey | direct | 0 |
| 8 | pitchVel | c7 | 0 |
| 10 | spectralForm | enum 0..6 | 0=Sine |
| 12 | spectralSkirt | direct | 0 |
| 14 | spectralResonance | direct | 0 |

**spectralForm enum:** 0=Sine, 1=All1, 2=All2, 3=Odd1, 4=Odd2, 5=Res1, 6=Res2

**PEG block (rel 16..20):**

| Rel | Field | Encoding | Default |
|---|---|---|---|
| 16 | pegInitialLevel | c50 (raw = UI+50) | 50 |
| 18 | pegAttackLevel | c50 | 50 |
| 20 | pegAttackTime | direct | 0 |

**note:** off 20 is **pegAttackTime** (PEG, left panel — not aegAttackTime!)

**AEG block (rel 22..40):**

| Rel | Field | Encoding | Default |
|---|---|---|---|
| 22 | pegDecayTime | direct | 0 |
| 24 | aegAttackLevel | direct | 99 |
| 26 | aegDecay1Level | direct | 99 |
| 28 | aegDecay2Level | direct | 99 |
| 30 | aegReleaseLevel | direct | 0 |
| 32 | aegAttackTime | direct | 0 |
| 34 | aegDecay1Time | direct | 0 |
| 36 | aegDecay2Time | direct | 0 |
| 38 | aegReleaseTime | direct | 40 |
| 40 | aegHoldTime | direct | 0 |

**note:** off 22 is **pegDecayTime** (PEG Decay — not aegDelayTime!). Off 32 is **aegAttackTime** (AEG, right panel).

**Key/Level scaling block (rel 42..56):**

| Rel | Field | Encoding | Default |
|---|---|---|---|
| 42 | aegTimeKeyFollow | direct | 0 |
| 44 | level | direct | 0 |
| 46 | aegBreakPoint | raw = MIDI_note − 9 | 39 (=C3) |
| 48 | lvlKeyLo | direct | 0 |
| 50 | lvlKeyHi | direct | 0 |
| 52 | curveLo | enum 0..3 | 0=-Linear |
| 54 | curveHi | enum 0..3 | 0 |
| 56 | levelVel | c7 | 0 |

**curve enum:** 0=-Linear, 1=-Exp, 2=+Exp, 3=+Linear

**LFO Mod Depths (per OP, rel 58..60 + 66..70):**

| Rel | Field | Encoding | Default |
|---|---|---|---|
| 58 | secondLfoPitchModDepth | direct | 3 |
| 60 | secondLfoAmpModDepth | direct | 3 |
| 66 | firstLfoDest1Ratio | direct | 127 |
| 68 | firstLfoDest2Ratio | direct | 127 |
| 70 | firstLfoDest3Ratio | direct | 127 |

## 12.3 FM-X Algoritm + Feedback (Part-level) ★★★★★

| abs (Part 1) | Field | Encoding | Default |
|---|---|---|---|
| 12525 | algorithm | raw = algo − 1 | 68 (algo 69 default) |
| 12527 | feedback | direct | 0 |

## 12.4 FM-X 2nd LFO Global (Part-level) ★★★★★

Se section 5.3.

## 12.5 FM-X OP Mute/Solo — NOT IN BLOB ★★★★★

OP Mute and OP Solo is real-time performance state and spairsas not in YSFC-the format. Ändras not in binärfilen at Save.

---

# 13. Engine data: Drum ★★★★★

**Engine-size:** 4963 bytes (4968 in pool with separator).

## 13.1 Drum-key architecture

```
DRUM_KEY1_BASE   = 12469   # Part 1 solo, key 1 = C0 (MIDI 12)
DRUM_KEY_STRIDE  = 68      # bytes per drum key
DRUM_KEY_COUNT   = 73      # C0..C6 inclusive (MIDI 12..84)
```

Drum-keys area: `[12469:17433]` = 4964 bytes.

## 13.2 Per-Drum-Key field (rel 0..62) ★★★★★

27 field per key, all binärverifierade -76.

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
| 56 | drumKeyEqLowFreq | u8 logaritmisk (~25 step/oct) | 54 (=62.5 Hz) |
| 58 | drumKeyEqLowGain | c64 ±24 dB | 64 |
| 60 | drumKeyEqHiFreq | u8 logaritmisk | 231 (=7.4 kHz) |
| 62 | drumKeyEqHiGain | c64 ±24 dB | 64 |

**EQ Gain encoding:** raw = 64 + UI_dB × (64/24)
**EQ Freq encoding:** u8 logaritmisk, ~25 step/oktav. 54=62.5 Hz, 156=987 Hz, 231=7.4 kHz, 214=4.88 kHz.

**Unused offsets inom key (default 0 or udda values, not UI-mapped):**
rel 1-3, 5, 7, 9, 11, 13, 15, 17-21, 23-25, 27, 29, 31, 33, 35, 37, 39, 41, 43, 45, 47, 49, 51, 53-55, 57, 59, 61, 63-66. Rel 18 (default 90) and 67 (default 64) har non-zero defaults — likely internal padding/sub-state.

```python
def drum_key_abs(field_name, key_idx):
    """key_idx: 0..72 (C0..C6)"""
    return 12469 + key_idx * 68 + DRUM_KEY[field_name]
```

## 13.3 Drum Part Common ★★★★★

| abs (Part 1) | rel_part | Field | Encoding | Default |
|---|---|---|---|---|
| 6736 | 28 | drumPartElemPanToggle | bool | 1=ON |
| 6802 | 94 | drumPartArpPlayOnly | bool | 0 |
| 6819 | 111 | drumPartVelLimitLow | direct | 1 |
| 6821 | 113 | drumPartVelLimitHigh | direct | 127 |
| 6823 | 115 | drumPartNoteLimitLow | MIDI note | 0 (C-2) |
| 6825 | 117 | drumPartNoteLimitHigh | MIDI note | 127 (G8) |
| 6827 | 119 | drumPartVelDepth | c64 | 64 |
| 6829 | 121 | drumPartVelOffset | c64 | 64 |
| 6831 | 123 | drumPartVolume (= EF Part Output) | direct | 100 |
| 6833 | 125 | drumPartPan | c64 | 64 |
| 6835 | 127 | drumPartReverbSend | direct | 0 |
| 6837 | 129 | drumPartVariationSend | direct | 0 |
| 6839 | 131 | drumPartDryLevel | direct | 127 |
| 6847 | 139 | drumPartOutput | enum (0=Main, 9=USB1+2) | 0 |
| 6867 | 159 | drumPartFilterCutoff | c64 | 64 |
| 6869 | 161 | drumPartResonance | c64 | 64 |
| 6913 | 205 | drumPitchBendUpper | c64 | 66 (=+2) |
| 6915 | 207 | drumPitchBendLower | c64 | 62 (=−2) |
| 6917 | 209 | drumDetuneHz | direct (or u8) | 128 |
| 6919 | 211 | drumNoteShift | c64 | 64 |
| 6961 | 253 | drumPart2EqType | enum (0=2band, 2=HPF) | 0 |

## 13.4 Drum-key kollaterala bytes ★★★★★

Vid each Drum-key-editing uppdateras automatiskt: `[6715, 6716, 6721]`. Tillagt in `DRUM_COLLATERAL_BYTES` for korrekt round-trip — filtered at diff men must matchas at write.

**Note:** ESP UI:s "Key"-väljare ändrar bara navigation, not data. Per-key-data lagras dock korrekt in blobben (verified genom att same SW=0x01-mönster återupprepas var 68:e byte).

---

# 14. Insertion FX — COMPLETE (57 typer) ★★★★★ / ★★★★☆

Insertion FX (InsA and InsB) applies engine-oberoende.

## 14.1 Encoding

```
fxA: abs = PART + 275 (InsA), PART + 332 (InsB)
fxA[0] = lo-byte av 7-bit type index
fxA[1] = hi-byte av 7-bit type index
TypeIndex = hi * 128 + lo
```

## 14.2 FX_TYPE_INDEX (komplett table)

★★★★★ = binärverifierat with testfil
★★★★☆ = härlett from Effect Type List + MSB/LSB-formel

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
ANALOG DELAY modern  = 360    ★★★★☆

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
    """Returnerar (lo, hi) för ett InsertionFX-name."""
    idx = FX_TYPE_INDEX.get(name.upper(), 0)
    return (idx & 0x7F, (idx >> 7) & 0x7F)

def fx_name_from_bytes(lo, hi):
    """Returnerar FX-name from (lo, hi) bytes."""
    return FX_INDEX_TO_NAME.get(hi * 128 + lo, f'UNKNOWN({hi*128+lo})')
```

## 14.3 LFO Speed encoding (all FX) ★★★★★

`raw = round(Hz × 23.7045)`

Datapunkter: 0.46 Hz→11, 0.80→19, 1.09→26, 1.30→31, 1.60→38, 1.98→47.

## 14.4 Symphonic + Classic Flanger pairsametrar (specifika)

**SYMPHONIC (12/12 ★★★★★):**

| fxA+ | Field | Encoding | Default |
|---|---|---|---|
| 4 | LFO Speed | raw=round(Hz×23.7) | 11 (=0.46 Hz) |
| 6 | LFO Depth | direct | 25 |
| 8 | Delay offset | tabellindex | 1 (≈0 ms) |
| 14 | EQ Low Freq | tabellindex | 22 |
| 16 | EQ Low Gain | c64 | 64 |
| 18 | EQ High Freq | tabellindex | 48 |
| 20 | EQ High Gain | c64 | 64 |
| 22 | Dry/Wet | direct | 64 |
| 24 | EQ Mid Freq | tabellindex | 38 |
| 26 | EQ Mid Gain | c64 | 64 |
| 28 | EQ Mid Width | tabellindex | 7 |

**CLASSIC FLANGER (16/16 ★★★★★):**

Som Symphonic + tre specifika field:

| fxA+ | Field | Encoding | Default |
|---|---|---|---|
| 10 | Delay offset | tabellindex | 24 (=0.65 ms) |
| 12 | Feedback | raw = percent+100 | 151 (=51%) |
| 30 | Mod Phase | raw = phase_idx × 2 | (180°=16) |
| 32 | FB High Damp | raw = value × 10 | 9 (=0.9) |
| 34 | Analog Feel | direct | 0 |

(Övriga 49 FX-typer uses same 22-pairsam-mall that Reverb/Variation FX in Common-area with different tolknnor per Type.)

---

# 15. Smart Morph ★★★★★

Smart Morph is not a parameter without a komplett filformat-utbyggnad.

## 15.1 Detektion ★★★★★

Två sepairsata indikatorer (ger same svar):

```python
def is_smart_morph(blob, file_data):
    # Indikator 1: byte i performance blob
    if blob[56] == 1:
        return True
    # Indikator 2: DSOM-chunk i container
    return b'DSOM' in file_data[64:200]  # i directory
```

**Verification:** `TEST-FMX-NORMAL.Y2L` har `blob[+56] = 0`, `TEST-FMX-SMARTMORPH.Y2L` har `blob[+56] = 1`. Clean direkt-diff over 1081 bytes (multiple side effects), men the isolerade nyckelthe byte is just `+56`.

## 15.2 Container-utbyggnad

Smart Morph lägger to **4 chunks** in Y2L-the file:

| Chunk | Size (typisk) | Function |
|---|---|---|
| ESPG | 71 b | Edit Smart Performance Group (header) |
| ESOM | 71 b | Edit Smart Morph (metadata) |
| DSPG | 794 b | Data Smart Performance Group |
| **DSOM** | **~900 KB** | Data Smart Morph — embeddad YAMAHA-SOM-file |

## 15.3 Performance-blob-ändrnor at Smart Morph

Förutom `blob[+56] = 1`:

| abs | NORMAL | SmartMorph | Interpretation |
|---|---|---|---|
| +56 | 0 | 1 | Smart Morph enable ★★★★★ |
| +66 | 0 | 16 | Side-effect (korrelerar with SM-aktivering) ★★★★★ |
| +728..+735 | 0 | u16le-array | Index/pekare to morph-keyframes ★★★★☆ |

## 15.4 DSOM-payload-structure

```
DSOM-chunk-payload:
  +0    u32be: count = 1
  +4    'Data' (4 bytes)
  +8    u32be: inner_size
  +12   embeddat YAMAHA-SOM-file
```

## 15.5 Embeddat YAMAHA-SOM-format ★★★☆☆

Eget format, not default YSFC:

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

**not mappat ännu.** Eget reverse-engineering-projekt.

## 15.6 Editor-strategi (Opaque-blob)

1. Detektera Smart Morph at load
2. Visa varning: "Smart Morph data preserverad — engine-pairsametrar redigerbara, men not morph-keyframes"
3. toåt editing of reguljära pairsametrar (Performance/Part-field)
4. Vid save: copy DSOM/ESPG/ESOM/DSPG **verbatim**, modifiera bara performance blobben

Stänger not dörren for full Smart Morph-support senare när YAMAHA-SOM reverse-engineeras.

---

# 16. UI elements NOT IN BLOB ★★★★★

Följande UI-element existerar men spairsas not in performance blob:

## 16.1 Hardware Events (RcvSw)

- **Pitch Bend** — hardware-globalt
- **Ch.After Touch** — hardware-globalt
- **Poly.After Touch** — hardware-globalt

## 16.2 UI-state

- **Performance Favorite (Star)** — sepairsat lagrad
- **MS Sequencer Lane Select** — UI-state, not spairsad
- **OP Mute / OP Solo** (FM-X) — real-time state

## 16.3 Hardware-globala settings

- **Global Tuning**
- **MC Flag**
- **System FX**
- **Transmit Switch**

## 16.4 Hard-coded in firmware

- scene CC (= 92)
- Super Knob CC (= 95)
- Footswitch Assign (= Arp Sw)

---

# 17. Modified / Noise flags ★★★★★

bytes that ändras at spairs without att representera parameterdata. **filtered at diff. must is preserved at write.**

| position | Function |
|---|---|
| `file[63]` | Save counter (yttre container) |
| `file[399]` | Save counter (kopia inuti EPFM) |
| `blob[+22]` | Sub-blob 1 edit-state (del of timestamp) |
| `blob[+23]`, `blob[+24]` | Sub-blob 1 (Common) timestamp/edit-state |
| `blob[+66]` | Common-area side-effect-flag |
| `blob[+232]`, `blob[+234]` | Common-area edit-flags (pairsallella, 1→0) |
| `blob[+358]` | Arp/FX edit-counter (2→0 in 25+ tester) |
| `blob[+376]` | Reverb edit-state-flag (samexisterar with Reverb Category) |
| `blob[+654]` | Multi-trigger side-effect (9+ orelaterade tester) |
| `blob[+6724]`, `blob[+6725]` | Sub-blob 2 (Part 1) timestamp |
| `blob[+7167]`, `blob[+7168]` | Arp-relaterade edit-flags (250→0 / 10→0) |
| `blob[+7419]` | scene edit-counter (per-scene edit triggar 0→1) |
| Sub-blob N: +23, +24 | Per-part-edit-state (mönstret upprepas) |
| **CA+17** | MODX-internal byte in each CA-slot |
| **Drum [6715, 6716, 6721]** | Drum-key kollaterala bytes |

```python
NOISE_BLOB = {
    22, 23, 24, 66,            # Sub-blob 1 timestamp + edit flags
    232, 234, 358, 376, 654,   # Common-area side-effect flags
    6724, 6725,                # Sub-blob 2 timestamp
    7167, 7168, 7419,          # Arp/scene edit-counters
}
NOISE_FILE = {63, 399}
DRUM_COLLATERAL = {6715, 6716, 6721}
```

⚠️ **note:** Vissa NOISE-offsets samexisterar with riktiga pairsametrar:
- `blob[+376]` = Reverb Category (verklig pairsam) MEN triggas också that side-effect
- `blob[+7419]` = per-scene edit-counter

Editor: write korrekt UI-value — MODX hanterar edit-flag-uppdaternor automatiskt.

---

# 18. Remaining unmapped regions

~50 bytes nz is "riktigt unknown" (efter denna analys). Övriga ~201 nz bytes
is confirmed OPAQUE — firmware-constant data that not exponeras in UI.

## 18.1 OPAQUE internal regions (~201 nz bytes)

**Definitionsegenskaper:**
- 0 testfiler in 1626-fils-korpus modifierar dessa bytes
- Bit-for-bit identiska over all 4 engines (AWM2/Drum/FMX/ANX)
- Contenter upprepande block-structures (CA-trailers, u16le-mönster)

| Region | Size | nz | Engine-agnostisk |
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

**Praktisk konsekvens:** Editor must preserva dessa byte-for-byte. Försök
not att tolka or modifiera dem — it is Yamaha-internal firmware-data.

```python
OPAQUE_NOTRNAL_REGIONS = [
    (487, 525), (732, 766), (788, 840),
    (5843, 5893), (6971, 6983), (7275, 7290),
]
STRIDE_106_GROUPS = [
    (840, 1710), (3186, 4043), (4083, 4943),
    (4943, 5826), (5942, 6700),  # Group 5: scene/Part-related
]
```

## 18.2 Stride-106 Group 5 — scene/Part-related

Distinkt from Groups 1-4: **uppdateras automatiskt at multi-part-skrivning**.
Specifikt `blob[+6695]` (max active part) is located in Group 5.

Övriga bytes in Group 5 reflekterar internal state of part-arrangement and
should is copied verbatim without tolkning.

## 18.3 Riktigt unknown (~50 nz bytes)

bytes that varken is mapped UI-field or bekräftade OPAQUE — potentiella
framtida UI-field that behover dedikerade tester:

| Region | nz | Plats |
|---|---:|---|
| `[70:104]` återstående | ~14 | Perf-level toggles (3 of 17 mapped) |
| `[130:153]` (utover 152=Ribbon CC) | 8 | Mellan Common toggles and Hardware Ribbon |
| `[232:246]` | 4 | Liten Common-region |
| `[357:377]` (utover NOISE 358, 376) | 4 | Mellan Master FX and Reverb FX |
| `[4043:4063]` (utover 4044) | 7 | Mellan Stride-106 grupper |
| `[12453:12466]` (utover 12464-65) | 1 | Pre-engine padding |
| Spridda enstaka bytes | ~12 | Mellan known field |

## 18.4 unmapped toggle-bytes

abs **32, 36** — 2 toggles where UI-funktion not is slutvalidt identifierad.

## 18.5 summary byte-täckning

```
Total bytes (ANX Init Base):     13150
Non-zero bytes:                   3766
UI-mappat (★★★★★/★★★★☆):       ~2523     (67.0% av nz)
Strukturellt mappat:             ~1041     (27.7% av nz)
OPAQUE (firmware-constant):       ~201     ( 5.3% av nz)
Riktigt unknown:                    ~50      ( 1.3% av nz)
```

**Praktisk implikation:** ~98,7% non-zero coverage uppnådd. Återstående 1,3%
preserveras verbatim — no funktionalitetsförlust for editor.

## 18.6 Konsoliderad verified teknisk täckning ★★★★★

This section bevarar aktuella tekniska slutsatser that ursprungligen togs fram under fokuserade analys-pass. It is not a changelog; it is aktuell implementation-/referenskunskap that not får tappas bort när äldre utforskande antecknnor tas bort.

### AN-X engine coverage

AN-X engine-poolen is considered that fullständigt mappad for known användarredigerbara field. It aktuella modellen is:

| Kategori | Current tolkning |
|---|---|
| UI-mapped field | 171 fields, inklusive oscillator-, noise-, filter-, WaveFolder-, Mod LFO-destination- and EG-relaterade field |
| Interna bytes | 458 firmware-/internbytes that is copied or seedas from verified baseline |
| Remaining varierande omappade bytes | 0 known |

important AN-X-field that must finnas kvar in referensen/serializern:

- Noise: `noise_tone`, `noise_connect`, `noise_unknown`
- Amp AEG: `amp_aeg_release`, `amp_aeg_time_vel`, `amp_aeg_sustain_hi`, `amp_aeg_time_vel_marker`
- OSC1/2/3: waveform, octave, pitch, PEG depth markers, pitch LFO depth, sync pitch, pulse width, shaper, connect and velocity-relaterade field
- OSC EG per oscillator: attack, decay, sustain, release where the exists
- Filter / WaveFolder: `filter2_type`, `wavefolder_eg_depth`, `wavefolder_texture`
- Mod LFO matrix-trailers: OSC1/OSC2/OSC3/filter destination-trailers with default 127

It explicita flat-mappningen of OSC-field is säkrare än att anta perfekt uniform stride for all OSC-field. Serializern should preserve known AN-X interna/routing-constants byte-for-byte or seeda dem from verified baseline.

### AWM2 element coverage

AWM2 element-structureen is considered that fullständigt mappad for known användarredigerbara field. Återstående non-UI-bytes are firmware-/internkonstanter or padding that should is preserved/stängas, not exponeras that redigerbara pairsametrar.

Kritiska AWM2-slutsatser:

| Rel | Field | Encoding / status |
|---:|---|---|
| +159 | `pegKFCenterNote` | MIDI-note; UI-confirmed Pitch EG Center Key |
| +237 | `feg_depth` | verified FEG Depth |
| +239 | `feg_segment` | verified FEG Segment |
| +241 | `feg_time_vel` | verified FEG Time/Vel |
| +243 | `feg_depth_vel` | c64, binärverifierad with dedikerad single-edit-test |
| +245 | `feg_curve` / `filter_curve` | verified FEG Curve |
| +247 | `feg_time_key` / `filter_time_key` | verified FEG Time/Key |
| +249 | `feg_center_key` / `filter_scaling_center_key` | verified FEG Center Key |
| +289 | `lfoSpeed` | normal LFO speed när Extended LFO is of |

Konflikten kring rel `+243` is löst: the field is `feg_depth_vel`, not a orelaterad unknown byte. PEG/FEG-symmetrin is `FEG = PEG + 54` for motsvarande Segment, Time/Vel, Depth/Vel, Curve, Time/Key and Center Key.

AWM2 internkonstanter that should vara closed inkluderar rel `+46`, `+90`, `+148`, `+200`, padding at `+309..+311` samt relaterade routing-/trailer-bytes. Extended LFO-default is `1` (ON), not `0`.

Addresskonventionerna får not blandas ihop:

| Convention | Element 1 base | Användning |
|---|---:|---|
| audit abs | 12469 | dokumentation and binära testoffsets |
| `AWM2_ELEM_LAYOUT` base | 12520 | active layoutkod |
| `AWM2_ELEM1_BASE` | 12532 | helper-offsets for binärverifiering |

Konversion: `AWM2_ELEM_LAYOUT_offset + 51 = AWM2_ELEMENT_FIELDS_rel` in audit-relative konvention.

### FM-X engine coverage

FM-X is considered that fullständigt mappad for aktuell användarredigerbar täckning. It aktuella modellen is:

| Kategori | Current tolkning |
|---|---|
| UI-mapped field | 141 fields |
| Interna bytes | firmware-/internbytes (OP +62..+70 excluded; these are now mapped UI/modulation fields) |
| Remaining varierande omappade bytes | 0 known |

important FM-X-field that must finnas kvar in referensen/serializern:

- PEG: `fmx_peg_center_key`, `fmx_peg_level_decay2`, `fmx_peg_level_release`, `fmx_peg_time_attack`, `fmx_peg_time_decay1`, `fmx_peg_time_release`, `fmx_peg_depth`
- 2nd LFO / algorithm: `fmx_2nd_lfo_phase`, `fmx_2nd_lfo_delay`, `fmx_algorithm`, `fmx_feedback`
- Part Filter / FEG: resonance velocity, hold/release time, hold/attack/decay/sustain/release levels, depth, segment, time velocity, depth velocity, curve, time key and center key
- Filter Scaling: fyra breakpoints and fyra cutoff offsets
- Per-OP-field: key-on reset, frequency mode, fixed-mode pitch key/velocity, AEG levels, level velocity, per-OP 2nd LFO pitch/amp mod destinations

FM-X OP-stride is 123 bytes. Per-OP-toäggen is:

| Rel inom OP | Field | Status |
|---:|---|---|
| +58 | `op_2nd_lfo_pitch_mod_dest` | UI-field |
| +60 | `op_2nd_lfo_amp_mod_dest` | UI-field |
| +62 | `op_pitch_controller_sensitivity` | UI/control field; neutral 0 |
| +64 | `op_level_controller_sensitivity` | UI/control field; neutral 0 |
| +66 | `op_1st_lfo_dest1_depth_ratio` | UI/modulation field; default 127 |
| +68 | `op_1st_lfo_dest2_depth_ratio` | UI/modulation field; default 127 |
| +70 | `op_1st_lfo_dest3_depth_ratio` | UI/modulation field; default 127 |

För OP1..OP8 upprepas positionerna with stride 123. These +62..+70 fields are verified user/modulation parameters and must not be classified as internal trailer bytes.

### Drum engine coverage

Drum uses annan offsetkonvention and annan Part Common-tolkning än AWM2/FM-X/AN-X. Drum key-mappningen and Drum Part Common-the fields is considered that fullständigt mapped for aktuell UI-täckning.

| Region | Current status |
|---|---|
| DRUM_KEY, 73 keys | 27 UI-field per key, binärverifierade |
| DRUM_KEY internbytes | cirka 38 internbytes per key |
| DRUM_PART_COMMON | 27 UI-field, binärverifierade |
| Insertion FX | shared Part-level InsA/InsB-structure |

Drum filoffset-konversion skiljer sig from övriga engines:

| Engine | audit → filoffset-konversion |
|---|---|
| AWM2 / AN-X / FM-X | `file_offset = audit + 687` |
| Drum | `file_offset = audit + 669` |

Drum key-zonen uses 73 keys with 68-byte stride. Key-mönstret `01 00 00 00 00 00 01 00` identifierar SW=1 and AssignMode=1. known key-positions inkluderar Key 1 at filoffset 13138, Key 36 at 15518 and Key 73 at 18034 in verified baseline-konvention.

Drum-key interna icke-zero-constants:

| Rel | value | Status |
|---:|---:|---|
| +18 | 90 | [INTERN], constant |
| +67 | 64 | [INTERN], constant |

Drum Part Common-field that must finnas kvar:

| Abs | Field | Encoding / default |
|---:|---|---|
| 6815 | `drumPartMainCategory` | enum, default 16 |
| 6849 | `drumPartFilterAegAttack` | c64, default 64 |
| 6851 | `drumPartFilterAegDecay` | c64, default 64 |
| 6853 | `drumPartFilterAegSustain` | c64, default 64 |
| 6855 | `drumPartFilterAegRelease` | c64, default 64 |
| 6903 | `drumPartControlGroup` | enum, default 0 |

Drum does not share the universal AEG offset block on same sätt as AWM2/FM-X/AN-X. För Drum applies rel `+126..+132` that Drum AEG, and rel `+144/+146` that Drum filter cutoff/resonance. The interpretation of Part Common rel `+126..+158` is wherefor agine-specifik.

### Remaining test-coverage note

It aktuella referensen behandlar Stride-106 and opaque/preserved regions that icke-användarredigerbara tills a framtida kontrollerat single-edit-test visar något annat. no aktuell exportväg should modifiera dessa regioner annat än genom att copy dem from källan or from verified baseline.

# 19. Helper-funktioner (serializer-API)

## 19.1 Address-beräkning ★★★★★

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
    if 'Drum'   in name: return 'Drum'   # note: without pairsentes
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
ANX_OSC1_BASE  = 12638
ANX_OSC_STRIDE = 125

def anx_osc_base(osc_idx, part_idx=0):
    """osc_idx = 0..2"""
    return ANX_OSC1_BASE + osc_idx * ANX_OSC_STRIDE + (part_idx * 5765)
```

## 19.6 Drum-key ★★★★★

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

## 19.9 scene ★★★★★

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

## 19.11 FX-utilities ★★★★★

```python
def fx_type_bytes(name):
    idx = FX_TYPE_INDEX.get(name.upper(), 0)
    return (idx & 0x7F, (idx >> 7) & 0x7F)

def fx_name_from_bytes(lo, hi):
    return FX_INDEX_TO_NAME.get(hi * 128 + lo, f'UNKNOWN({hi*128+lo})')
```

## 19.12 Structural metadata bytes ★★★★★

Vid både read and write of performance must dessa bytes vara korrekta.

```python
ENGINE_TYPE_BYTE = 6700  # 0=AWM2, 1=Drum, 2=FMX, 3=ANX
ENGINE_TYPE_VALUES = {0: 'AWM2', 1: 'Drum', 2: 'FMX', 3: 'ANX'}
ENGINE_TYPE_BY_NAME = {v: k for k, v in ENGINE_TYPE_VALUES.items()}

MAX_ACTIVE_PART_BYTE = 6695  # 1..16, highest active part-nummer

def get_engine_type_byte(blob):
    return ENGINE_TYPE_VALUES.get(blob[ENGINE_TYPE_BYTE], 'Unknown')

def get_max_active_part(blob):
    return blob[MAX_ACTIVE_PART_BYTE]

def set_engine_type_byte(blob, engine_name):
    """engine_name: 'AWM2' | 'Drum' | 'FMX' | 'ANX'"""
    blob[ENGINE_TYPE_BYTE] = ENGINE_TYPE_BY_NAME[engine_name]

def set_max_active_part(blob, max_part_idx):
    """max_part_idx: 1..16 (highest part-nummer som är active)"""
    blob[MAX_ACTIVE_PART_BYTE] = max_part_idx

def validate_engine_consistency(blob):
    """Verify att engine-byte matchar sub-blob 2 name suffix."""
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
    """slot_idx: 0..3, field_rel: rel-offset from slot-bas."""
    part_offset = sub_blob_start - 6701
    slot_base = AWM2_CONTROL_SOURCE_BASE + slot_idx * AWM2_CONTROL_SOURCE_STRIDE
    return slot_base + field_rel + part_offset
```

## 19.14 Motion Sequencer field ★★★★★

UI-vy "Motion Seq > Common / Lane" har TVÅ sections with 6 field vardera:

**"Common" (Performance Common-area, applies all parts):**
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

**"Part" (Part Common-area, applies all 4 Lanes in denna Part):**
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
    """Returnerar abs address för Part N:s Motion Seq Part-field."""
    sub_blob_start = 6701 + (part_idx - 1) * 5765
    return sub_blob_start + PART_MOTION_SEQ_REL[f'{field}_rel']
```

**View Lane-dropdown (1-4)** in UI styr only vilken Lane that visas in
Edit Part Sequencer-vyn — the ändrar **not** vilka bytes that påverkas
of Common/Part-the fields ovan. Båda sektionerna is Part-level (or
Performance-level for Common), not per-Lane.

verified: TEST5R3-T4b-ViewLane2-Swing50 — ändring of "View Lane: 2"
+ Part Swing påverkar same byte (6887) that with View Lane 1.

**Per-Lane data** (Lane Switch, Lane Velocity Limits, MS Grid, Pulse A/B m.fl.)
is located in sub-blob 2 Lane-data-area [8929+, stride 884 per Lane]:
- Lane 1 LaneSwitch @ blob[+8929]
- Lane 2 LaneSwitch @ blob[+9813]
- Lane 3 LaneSwitch @ blob[+10697]
- Lane 4 LaneSwitch @ blob[+11581]

**Bakåtkompatibilitet:** `LANE1_COMMON` is alias for `COMMON_MOTION_SEQ`.

## 19.15 Multi-part pointer API ★★★★★

```python
SUBBLOB_PONOTR_REL = (5763, 5764)
ENGINE_MAGIC_BYTES  = {'ANX': 110, 'AWM2': 8, 'FMX': 82, 'Drum': 73}
ENGINE_MAGIC_TO_NAME = {v: k for k, v in ENGINE_MAGIC_BYTES.items()}

def get_subblob_pointer_pos(part_idx):
    """Pos för Part N:s pointer (1-indexerat)."""
    sub_blob_start = 6701 + (part_idx - 1) * 5765
    return (sub_blob_start + 5763, sub_blob_start + 5764)

def read_subblob_pointer(blob, part_idx):
    """Returnerar (is_last, next_or_part1_engine)."""
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
    """note: part1_engine_name = first engine i pool (= Part 1:s engine)."""
    pos0, pos1 = get_subblob_pointer_pos(part_idx)
    blob[pos0] = ENGINE_MAGIC_BYTES[part1_engine_name]
    blob[pos1] = 0

def get_entr_bitmask(max_active_part):
    """(1 << N) - 1 where N = max_active_part."""
    return (1 << max_active_part) - 1
```

## 19.16 Opaque-regions registry ★★★★★

```python
# Regioner som must preserveras byte-för-byte. 0 testfiler modifierar dem.
OPAQUE_NOTRNAL_REGIONS = [
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
    (5942, 6700),  # Group 5 — scene/Part-related
]

def is_opaque_byte(offset):
    """Returnerar True om offset är i en opaque-region."""
    for start, end in OPAQUE_NOTRNAL_REGIONS:
        if start <= offset < end:
            return True
    for start, end, *_ in STRIDE_106_GROUPS[:4]:  # Groups 1-4 are fully opaque
        if start <= offset < end:
            return True
    return False
```

## 19.17 File-level constants & save counter ★★★★★

```python
FILE_SAVE_COUNTER_POS = 60         # u32be, ökar +1 per spairs
FILE_INNER_SAVE_COUNTER_POS = 396  # u32be, = file[60:64] - 1
CHUNK_CATALOG_POS = 64             # 6 × 8 bytes
CHUNK_NAMES = ['EPFM', 'ESYS', 'EFVT', 'DPFM', 'DSYS', 'DFVT']

def read_save_counter(file_data):
    """Returnerar u32be save counter from file[60:64]."""
    import struct
    return struct.unpack('>I', file_data[60:64])[0]

def write_save_counter(file_data, value):
    """write save counter to file[60:64] and inner counter file[396:400]=value-1."""
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

## 20.1 summary per engine

| Engine / section | Status | verified |
|---|---|---|
| Container (EPFM/DPFM/ESYS/EFVT/DSYS/DFVT) | COMPLETE | ★★★★★ |
| Sub-blob universala modellen | COMPLETE | ★★★★★ (all 16 parts × all 4 engines) |
| Engine pool structure | COMPLETE | ★★★★★ |
| Performance Common (~30 field) | COMPLETE | ★★★★★ |
| Part Common (~25 field) | COMPLETE | ★★★★★ |
| Receive Switch (26/26) | COMPLETE | ★★★★★ (utom pos 22 = internal) |
| Common Assigns (CA_PERF + CA_PART, 32 slots) | COMPLETE | ★★★★★ |
| scene Struct 1 (9 field × 8 scenes) | COMPLETE | ★★★★★ |
| scene Struct 2 (11 field × 8 scenes) | COMPLETE | ★★★★★ (hypotes: active-part) |
| Master EQ (15 field) | COMPLETE | 13 × ★★★★★ + 2 × ★★★★☆ (LoMid/HiMid Freq) |
| Reverb FX (26 field) | COMPLETE | ★★★★★ |
| Variation FX (28 field) | COMPLETE | ★★★★★ |
| Master FX (26 field) | COMPLETE | ★★★★★ |
| Common CC + Hardware Ribbon | COMPLETE | ★★★★★ |
| Audio In + Envelope Follower | COMPLETE | ★★★★★ |
| Per-Part 3-band EQ (7 field) | COMPLETE | ★★★★★ |
| Per-Part 2-band EQ (9 field) | COMPLETE | ★★★★★ |
| AN-X engine (684 b) | COMPLETE | ★★★★★ OSC1 verified, OSC2/3 stride-bekräftade |
| AWM2 engine (2503 b) | COMPLETE | ★★★★★ Element 1 verified, 8 elements verified |
| FM-X engine (1143 b) | COMPLETE | ★★★★★ 8 OPs × 21 fields + LFO matriser |
| Drum engine (4963 b) | COMPLETE | ★★★★★ 73 keys × 27 fields + 21 Part Common |
| Insertion FX (57 typer) | COMPLETE | 12 × ★★★★★ + 45 × ★★★★☆ |
| Smart Morph | DETEKTION KLAR | ★★★★★ (DSOM-payload not kartlagd) |
| MS Sequencer (4 lanes) | COMPLETE | ★★★★★ Lane-bas + 29 field/lane |

## 20.2 Lista over field påstådda complete men without test-referens

Regionn that is dokumenterade men where vi not hittade a clean testfil in korpusen. Kandidater for framtida verifiering:

- **Master EQ Lo Mid Freq (570)** — predicted from stride
- **Master EQ Hi Mid Freq (582)** — predicted from stride
- **FS Assign destination encoding (abs 164)** — ★★★☆☆
- **AN-X OSC2 / OSC3 EG-field** — stride-extrapolerade from OSC1, not direkt testade per-field
- **AN-X Filter 2 field** — stride-extrapolerade from Filter 1
- **FMX LFO Destinations 71, 73, 76** — UI-deduced from enum-position
- **CA Sources 2-7, 11-15** — only PB/MW/Knob1-3 binärverifierade
- **AWM2 Element 2-8** — stride-verified men not per-field per element

Praktisk konsekvens: dessa field follows etablerade mönster and can användas in editor men should markeras ★★★★☆ tills explicit verified.

## 20.3 Statistik from testkorpus

```
Total Y2L-testfiler analyserade:     1626
Clean 1-byte diff tester:             385
2-byte (u16le) diff tester:           293
Multi-byte diff tester (pairsametrar + side-effects):  ~700
Tomma/identiska tester:               ~248

Unika offsets binärverifierade with ≥1 clean test:  ~200 (u8) + ~21 (u16le) = 221
Unika offsets verified with ≥3 oberoende tester:  ~25
offsets with max test-count (Detune):  37 oberoende tester
```

## 20.4 Patch Editor — implementation status

Rekommenderad architecture:

1. **Läs performance** from Y2L → parse via EPFM directory → DPFM → blob
2. **Decode pairsametrar** via offset-tabeller + encoding-funktioner
3. **UI-lager** per engine/section (FM-X OP, AWM2 Elem, AN-X OSC, Drum-key)
4. **Encode + write** ändrade bytes tillbaka to blob
5. **Exportera** new Y2L via `buildYSFC`-funktion

**Editor read-path behover:**
- Detektera count sub-blobs (söka efter `00 00 00 15 "Init …"` headers)
- För Part N ≥ 2: used `part_field_abs(N-1, payload_offset)`
- Engine data is located always in last sub-blobben (solo) or in engine-pool (multi-part)

**Editor write-path behover:**
- Vid editing of Part N: säkerställ att sub-blob N existerar
- Skapa tomma sub-blob-platshållare for all parts up to N
- Engine data flyttas to last sub-blobben / engine-pool

**Bevarad data (preserve verbatim):**
- ESYS/DSYS/EFVT/DFVT chunks (engine-oberoende)
- Smart Morph chunks (ESPG/ESOM/DSPG/DSOM)
- Stride-106 Zone/Control-blocks (Common region)
- Region [732:766] (14 × u16le)
- Region [788:840], [5843:5893], [7300:7419] (not UI-mapped)
- Modified-flag-bytes (is copied from source at merge)
- CA+17 byte in each CA-slot (MODX-internal)
- Drum kollaterala bytes [6715, 6716, 6721]

---

# 21. Lessons and process

## 21.1 UI-aliasing (a byte → flera UI-labels)

Vissa bytes har två UI-labels dependency on UI-vy:

| byte | UI Label 1 | UI Label 2 |
|---|---|---|
| `blob[+68]` | Performance Volume | EF Master Output |
| `blob[+6831]` | Part Volume | EF Part Output |
| `blob[+766]` | Audio In Volume | EF AD Output Level |

Editor must presentera båda labels in sina respektive UI-sections men förstå att the writes same fysiska byte.

## 21.2 Side-effect-flags

Vissa bytes ändras of många orelaterade UI-operationer:

| byte | Beteende |
|---|---|
| `blob[+66]` | Common-area side-effect-flag — ändras at många Common-edits |
| `blob[+654]` | Multi-trigger — minst 9 different edit-typer ändrar denna |
| `blob[+23/24]`, sub-blob `+23/24` per N | Timestamp/edit-counter |

Dessa ÄR NOISE — should filtered at diff-analys, men must be written korrekt at round-trip.

## 21.3 Verificationsmetodik

Kontrollerat test (ändra X in UI, exportera, diff) is guldstandard. Minst 3-4 datapunkter behövs for acoding-säkerhet (center=64 vs center=128 vs direct osv). Statistisk korrelation over korpus without riktade tester can ge falska positiva.

Stjärnbetyg sätts först när bevis exists:
- **★★★★★** = binärverifierat with specifik testfil (lista in section 20)
- **★★★★☆** = härlett from officiell källdata or etablerat mönster
- **★★★☆☆** = predicted without empirisk bekräftelse

---

**Slutet on YSFC Forge Full Context.**

