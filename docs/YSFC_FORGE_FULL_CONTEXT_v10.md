# YSFC Forge — Full Context v10.1
*Updated: 2026-05-08 | Steps 1–74 | Serializer v6 | ~668 fields mapped (~99%)*

---

## Project Overview

**Goal:** Reverse-engineer the Y2L format, build a merge tool + patch editor.

**Forge app:** Fully functional merge tool, verified on MODX M / ESP plugin.
**Serializer:** v6, ~668 fields mapped (~99%). OSC1 100% complete.

---

## Mapping Status (Steps 1–74)

| Engine/Section | Fields | ★★★★★ | Coverage | Note |
|----------------|--------|--------|----------|------|
| FM-X OP (×8) | 31 | 31 | 100% | COMPLETE |
| FM-X Part PEG | 16 | 16 | 100% | COMPLETE |
| FM-X Part 1st LFO | 11 | 11 | 100% | COMPLETE |
| FM-X Part 2nd LFO | 7 | 7 | 100% | COMPLETE |
| FM-X Part Common | 15 | 15 | 100% | COMPLETE |
| AWM2 Element | ~35 | ~33 | ~95% | |
| AWM2 Part | 26 | 26 | 100% | COMPLETE |
| AN-X Part (OSC/Filter/WF/EG) | ~132 | ~130 | ~99% | OSC1 100% ★ |
| Insertion FX | 57 | 57 | 100% | COMPLETE (57 types) |
| Controller Assign | 8 | 8 | 100% | COMPLETE |
| Performance Common | 10 | 10 | 100% | COMPLETE |
| AT Register | 2 | 2 | 100% | COMPLETE |
| SuperKnob + Assign (values+sw) | 20 | 20 | 100% | COMPLETE ← Step 71 |
| Assign Positioners (L/M/R ×8) | 25 | 25 | 100% | COMPLETE ← Step 71 |
| ANX Arp Common + Arp1 | 34 | 34 | 100% | COMPLETE ← Step 71 |
| ANX Seq Lane ×4 (29/lane) | 116 | 116 | 100% | COMPLETE ← Step 71 |
| Metadata flags | 4 | 4 | 100% | COMPLETE |
| **TOTAL** | **~668** | **~643** | **~99%** | |

---

## Y2L / Y2U File Structure — COMPLETE ★★★★★

*(Binary-verified 2026-05-03 against AWM2/FM-X/AN-X init files + 1/2/4-perf files)*

**Timestamp bytes** (ignored in diffs): PERF+23, +24, +6724, +6725  
**CA+17** is MODX-internal (not a visible parameter, ignored)  
**OP Mute/Solo** is NOT saved in YSFC (real-time state only)

---

### 1. File header (64 bytes)

```
File[0:12]  = b'YAMAHA-YSFC\x00'
File[12:20] = version string (e.g. b'5.1.2\x00\x00\x00')
File[20:62] = padding
File[62]    = 0x2a (fixed constant)
File[63]    = checksum (not validated by MODX)
```

---

### 2. EPFM chunk (starts at File[64])

```
File[64:68]   = b'EPFM'
File[68:72]   = EPFM payload size (u32be) — always 353, even for multi-perf!
File[72:]     = EPFM payload
```

**EPFM payload layout:**

```
[0:64]    CHUNK DIRECTORY — 8 slots × 8 bytes
          Each slot: [4 bytes ASCII tag][4 bytes absolute file offset]
          Empty slots: 0xFF × 8
          
          Typical order (without Live Set):
            Slot 0: 'ESYS' + file_offset_ESYS
            Slot 1: 'EFVT' + file_offset_EFVT
            Slot 2: 'DPFM' + file_offset_DPFM
            Slot 3: 'DSYS' + file_offset_DSYS
            Slot 4: 'DFVT' + file_offset_DFVT
            Slots 5–7: 0xFF × 24
          
          With Live Set (Y2L library):
            Adds 'ELST' and 'DLST' slots.
          
          ⚠️ Other chunks CANNOT be found by sequential scan — always
             use the directory offsets!

[64:280]  PADDING — 0xFF × 216 (constant, regardless of number of performances)

[280]     0x00 (separator byte)

[281:]    PERFORMANCE CATALOG — grows with N
          Format:
            [0:4]  b'EPFM'         (sub-tag)
            [4:8]  catalog_size    (u32be) = 8 + Σ(8 + Entr_size) for all N
                   → 1 perf: 81, 2 perfs: 147, 4 perfs: 275
            [8:12] N               (perf count, u32be)
            [12:]  N × Entr records (packed with no gaps)
          
          ⚠️ The catalog may extend beyond the EPFM chunk boundary (size=353)
             for more than ~3 performances. The EPFM chunk size=353 is NOT
             updated — the absolute file offsets in the directory remain correct.
```

**Entr record (one per performance):**

```
[0:4]   b'Entr'
[4:8]   Entr record size (u32be) — varies with name length
[8:]    Entr record data:
  [0:4]   blob_size   — size of this perf's Data blob in DPFM (u32be)
  [4:8]   blob_dp_off — DPFM-payload-relative offset to blob[0] (u32be)
                        = 12 for blob0, 12+(8+sz0) for blob1, etc.
  [8]     0x00
  [9]     0x40 (= 64, constant)
  [10]    0x00
  [11]    entry_index (0-based index in this file)
  [12]    0x00
  [13]    unknown flag (0x01 or 0x00)
  [14]    0x00
  [15]    unknown flag (0x04 most common, 0x01 for ESYS)
  [16]    unknown flag (0x02 or 0x00)
  [17]    0x00
  [18:25] unknown bytes (mostly 0x00)
  [25]    0x30 (= 48, constant)
  [26:]   name field: [1 unknown byte][ASCII "SLOT:Long name:Short name\x00"]
                      SLOT = decimal slot number (e.g. "128")
                      Long name: up to 20 characters
                      Short name: up to 8 characters
```

---

### 3. DPFM chunk

**Located via EPFM directory** (absolute file offset).

```
DPFM_TAG[0:4]  = b'DPFM'
DPFM_TAG[4:8]  = payload size (u32be)
dp = raw[offset+8:]  ← dp[0] = DPFM payload start (= find_dpfm() return value)

dp[0:4]   = N (perf count, u32be)
dp[4:8]   = b'Data'  (first Data sub-entry tag)
dp[8:12]  = blob0_size (u32be)
dp[12:]   = blob0 data
dp[12+blob0_size:]   = b'Data' + blob1_size + blob1 data
... (N Data sub-entries total, packed)
```

**Performance blob structure:**

```
blob[0:4]   = 0x00000015 (format constant, always 21)
blob[4:N]   = performance name, null-terminated ASCII (variable length)
blob[N:24]  = zero padding to byte 24
blob[24:]   = performance parameter data
```

**COORDINATE SYSTEM for FIELD_REGISTRY:**

```
All offsets in FIELD_REGISTRY are dp-relative (relative to dp[0]):

dp[0:12]   = DPFM header (count + 'Data' + blob0_size)
dp[12]     = blob0[0] = 0x00 (part of the 0x00000015 constant)
dp[12+24]  = blob0[24] = first parameter byte

Examples:
  CA_PERF_BASE     = 2451   → dp[2451]
  PART_BLOCK_START = 6708   → dp[6708]
  AWM2_ELEM1_BASE  = 12532  → dp[12532]

find_dpfm() returns the dp[0] offset (= DPFM tag offset + 8) ✅
```

---

### 4. ESYS / DSYS (System Settings)

**Sizes are constant, content is engine-independent.**

```
ESYS payload (46 bytes, constant):
  [0:4]  count = 1
  [4:8]  b'Entr'
  [8:12] Entr record size = 34
  [12:]  Entr data:
    [0:4]  DSYS blob_size = 1082
    [4:8]  blob_dp_off = 12
    [26:]  b'\x00System\x00'

DSYS payload (1094 bytes, constant):
  [0:4]  count = 1
  [4:8]  b'Data'
  [8:12] blob_size = 1082
  [12:]  blob (1082 bytes, system parameters):
    blob[0:4] = 0x00000050 (format constant — differs from DPFM's 0x15!)
    blob[4:]  = system parameters (not mapped)
```

---

### 5. EFVT / DFVT (Favorites)

**Sizes are constant, content is engine-independent.**

```
EFVT payload (163 bytes, constant):
  [0:4]  count = 3
  Entr[0] PerformanceFavorite: blob_size=3621,  blob_dp_off=12
  Entr[1] ArpeggioFavorite:    blob_size=10922, blob_dp_off=3641
  Entr[2] WaveformFavorite:    blob_size=7648,  blob_dp_off=14571

DFVT payload (22219 bytes, constant):
  [0:4]  count = 3
  3 × Data sub-entries:
    Data[0] size=3621  (PerformanceFavorite, mostly zeros)
    Data[1] size=10922 (ArpeggioFavorite, mostly zeros)
    Data[2] size=7648  (WaveformFavorite, mostly zeros)
  Check: 12 + 3621 + 8 + 10922 + 8 + 7648 = 22219 ✅

⚠️ ESYS/DSYS/EFVT/DFVT are IDENTICAL across AWM2/FM-X/AN-X and
   across 1/2/4-perf files → always copy verbatim during merge.
```

---

### 6. ELST / DLST (Live Set — Library files)

Present in Y2L files with Live Set content. Mirrors the EPFM/DPFM pattern (Entr index + Data blobs). Low priority, not fully mapped.

---

---

## FM-X OP Layout — COMPLETE ★★★★★

**OP1_BASE=12676, stride=123, 8 OPs**

| off | Field | Encoding | Default |
|-----|-------|----------|---------|
| -4 | keyOnReset | bool | 1=On |
| -2 | freqMode | enum 0=Ratio,1=Fixed | 0 |
| 0 | coarse | direct | 1 |
| 2 | fine | direct | 0 |
| 4 | detune | center=15 | 0 |
| 6 | pitchKey | direct | 0 |
| 8 | pitchVel | center=7 | 0 |
| 10 | spectralForm | enum 0-6¹ | 0=Sine |
| 12 | spectralSkirt | direct | 0 |
| 14 | spectralResonance | direct | 0 |
| 16 | pegInitialLevel | direct | 50 |
| 18 | pegAttackLevel | direct | 50 |
| 20 | **pegAttackTime** | direct | 0 |
| 22 | **pegDecayTime** | direct | 0 |
| 24 | aegAttackLevel | direct | 99 |
| 26 | aegDecay1Level | direct | 99 |
| 28 | aegDecay2Level | direct | 99 |
| 30 | aegReleaseLevel | direct | 0 |
| 32 | **aegAttackTime** | direct | 0 |
| 34 | aegDecay1Time | direct | 0 |
| 36 | aegDecay2Time | direct | 0 |
| 38 | aegReleaseTime | direct | 40 |
| 40 | aegHoldTime | direct | 0 |
| 42 | aegTimeKeyFollow | direct | 0 |
| 44 | level | direct | 0 |
| 46 | aegBreakPoint | MIDI_note-9 | 39=C3 |
| 48 | lvlKeyLo | direct | 0 |
| 50 | lvlKeyHi | direct | 0 |
| 52 | curveLo | enum² | 0=-Linear |
| 54 | curveHi | enum² | 0=-Linear |
| 56 | levelVel | center=7 | 0 |

¹ spectralForm: 0=Sine,1=All1,2=All2,3=Odd1,4=Odd2,5=Res1,6=Res2  
² curve: 0=-Linear,1=-Exp,2=+Exp,3=+Linear

**Critical corrections:**
- off=20 = **pegAttackTime** (PEG, left panel — NOT AEG!)
- off=22 = **pegDecayTime** (PEG Decay — NOT aegDelayTime!)
- off=32 = **aegAttackTime** (AEG, right panel)

---

## FM-X Part Sections

### PEG Block (abs 12477–12507) — 16/16 ★★★★★
Encoding PEG Levels: `center=50` (`raw = ui + 50`)  
PEG Depth enum: raw 0-3 = [8oct, 2oct, 1oct, 0.5oct] (8oct=default!)  
PitchKeyFollow: `round(pct×64/200) + 64`

### 1st LFO Block — 11/11 ★★★★★
Wave enum: 0=Triangle...12=User (13 values)  
TempoNote: `raw = list_index + 5`, default=11=1/4  
FadeOut: center/default=64. Loop: INVERTED bool (0=On)

### 2nd LFO Block — 7/7 ★★★★★

| abs | PART+ | Field | Default |
|-----|-------|-------|---------|
| 12509 | +5801 | Wave (enum 0-12) | 0 |
| 12511 | +5803 | SpeedNormal | 30 (Ext=OFF) |
| 12513 | +5805 | Phase (enum 0=0°..4=360°) | 0 |
| 12515 | +5807 | Delay | 0 |
| 12517 | +5809 | KeyOnReset | 0 |
| 12529 | +5821 | Extended | 1=ON |
| 12531 | +5823 | SpeedExtended | 60 (Ext=ON) |

---

## Insertion FX — COMPLETE (57 types)

`FX_TYPE_INDEX` in `ysfc_fx_type_index.py` — applies identically to InsA and InsB.  
Encoding: `lo = idx & 0x7F`, `hi = (idx >> 7) & 0x7F`

Binary-verified ★★★★★ selection:  
`THRU=0, SPX HALL=130, CROSS DELAY=256, SYMPHONIC=432, CLASSIC FLANGER=528, TREMOLO=784, COMP DISTORTION=928, CLASSIC COMPRESSOR=1040, VCM AUTO WAH=1280, NOISY=1424, SLICE=1616, PRESENCE=1672, WAVE FOLDER=1704`

Symphonic + Classic Flanger parameters: see v8.0

---

## Controller Assign — ENGINE-INDEPENDENT ★★★★★

`CA_STRIDE=22, CA_PART_BASE=8220, CA_PERF_BASE=2451`

| CA+ | Field | Encoding | Default |
|-----|-------|----------|---------|
| +1 | SW | bool | 0=Off |
| +3 | Source | enum | 1=MW |
| +5 | Destination | enum | 1=Volume |
| +9 | CurveType | enum | 0=Standard |
| +11 | Param1 | direct | 5 |
| +13 | Param2 | direct | 0 |
| +15 | Polarity | bool | 0=UNI |
| +17 | *(MODX-internal)* | ignored | 192 |

**Source:** PB=0, MW=1, Knob1=8, Knob2=9, Knob3=10  
**Destination:** Volume=1, InsA Param2-24 (linear), InsB=25, Rev=50, Var=51, ElemLevel=60, ElemPan=61, Cut=85, HPF=87, PartPan=100, Arp=105, MSLen=118

**CurveType:** Standard=0, Sigmoid=1, Threshold=2, Harmonic=18, Steps=19

---

## AN-X — Corrections (Steps 60-61)

**OSC EG corrected offsets:**
- `anxOsc1EGAttackTime=5970` (was 5813)
- `anxOsc2EGAttackTime=6095` (was 5938)
- `anxOsc3EGAttackTime=6220` (was 6063)

**PulseWidth:** `anxOsc1PulseWidth=5938`, encoding: `raw=round(pct×256/100)`

**OSC2 EGDepth/LFODepth:** 6067/6069 (stride=125 from 5942/5944)

---

## AWM2 AfterTouch Register

```
AWM2_AT_ASSIGN = {atSwitch: PART+593, atDestination: PART+595}
AT_DESTINATION = {1: 'Pitch', 9: 'FilterCutoff'}
```
Separate from the CA block, with its own destination encoding.

---

## Encoding Table (complete)

| Type | Formula |
|------|---------|
| direct u8 | raw = value |
| center=50 | raw = value + 50 |
| center=64 | raw = value + 64 |
| center=128 | raw = value + 128 |
| center=15 (OP detune) | raw = value + 15 |
| keyfollow% | raw = round(pct×64/200) + 64 |
| AN-X Pitch | raw = cents + 504 |
| FX LFO Speed | raw = round(Hz × 23.7045) |
| FX Dry/Wet | raw = fader (0-127) |
| OP BreakPoint | raw = MIDI_note - 9 |
| LFO TempoNote | raw = list_index + 5 |
| PEG Depth FM-X | enum [8,2,1,0.5]oct |
| PEG CenterKey | Yamaha note (C-2=0) |
| AN-X PulseWidth | raw = round(pct × 256/100) |
| 2nd LFO Phase | enum 0=0°,1=90°,2=180°,3=270°,4=360° |
| InsA/B TypeIndex | lo=idx&0x7F, hi=(idx>>7)&0x7F |

---

## Remaining items (low priority)

| Area | Description |
|------|-------------|
| FM-X 2nd LFO Depth matrix | abs=12547+, PitchMod×8+AmpMod×8+FilterMod, default=0 |
| FM-X OP routing matrix | abs=6730-6793, 64 bytes default=1, never changed via UI |
| AWM2 ctrlSet element level | Offset not binary-verified |
| Performance Common 0:6708 | Scene/SuperKnob/MotionSeq — complex |
| Montage .X7L/.X8L | Likely identical, not tested |
| AN-X PART+5934 | RESOLVED: selfSyncPitchEGDepth ★★★★★ (Step 74) |

---

## Status: Patch Editor (in progress)

Recommended architecture for editor in the forge app:
1. **Read performance** from Y2L → parse DPFM → perf bytes
2. **Decode parameters** via serializer dict + encoding functions
3. **UI layer** per engine/section (FM-X OP, AWM2 Elem, AN-X OSC...)
4. **Encode + write** changed bytes back to perf buffer
5. **Export** new Y2L via the existing `buildYSFC` function

Simplest starting point: FM-X algorithm + feedback + OP levels (off=44) — visible sliders with direct encoding.

**Mapping complete as of Step 74.** ~668 fields (~99%) confirmed. Focus is now the patch editor.

---

## Changelog

### v10.1 (2026-05-08) — Steps 71–74, ~668 fields (~99%)
- Step 71 (111 files): SuperKnob, Assign 1-8, MidPos, Arp Common, Seq Lane ×4
- Step 72: WaveFolder encodings verified (VelSens=direct, Texture=direct, EGDepth/LFODepth=0x80+n)
  New CA destinations: Dest=142=FilterCutoff, Dest=118=ANXPan
- Step 73: shaperEGDepth(PART+5950) + shaperLFODepth(PART+5952) ★★★★★
  OSC1 EG/LFO matrix complete (Sync/SyncPitchVel/SyncPitchEG/PulseWidth/Shaper)
- Step 74: selfSyncPitchEGDepth(PART+5934) ★★★★★ via MODX M8 hardware export
  OSC1 now 100% mapped — no unknown fields remaining
  MODX M8 vs ESP file size explained: DLST/ELST (~84KB extra = entire user bank)
- Serializer bug fixed: anxOsc1SelfSyncLFODepth=5934 was wrong → correct=5936
- Serializer v6: all comments translated to English

### v10.0 (2026-05-03) — Container structure fully documented
- EPFM payload: directory (64 bytes) + padding (216 bytes) + catalog structure
- Catalog: sub-tag 'EPFM' + catalog_size + count + N×Entr records
- Entr record: all fields decoded (blob_size, blob_dp_off, entry_index, name format)
- DPFM: Data sub-entries, blob header (0x15 constant + name + padding to byte 24)
- FIELD_REGISTRY coordinate system confirmed: dp-relative (dp[0] = DPFM payload start)
- ESYS/DSYS: constant sizes (46/1094 bytes), system blob header = 0x50
- EFVT/DFVT: constant sizes (163/22219 bytes), 3 favorite categories
- Confirmed: ESYS/DSYS/EFVT/DFVT identical across all engines and perf counts

### v9.0 (Steps 53–62, 2026-04-26) — Mapping complete
- FM-X 2nd LFO: Phase+Delay added → 7/7 complete
- WaveFolder TypeIndex=1704 → FX table 57 types complete
- AN-X PulseWidth=5938 corrected + encoding raw=round(pct*256/100)
- AWM2 AT register: SW=593, Dest=595
- OP Mute: not saved in YSFC
- FM-X OP routing matrix identified (abs=6730-6793)
- 422/462 fields (91%) mapped at this step (Step 62)

### v8.0 (Steps 46–52)
FM-X OP 21/21, Symphonic FX, AN-X EG, CA engine-independent

### v7.0 (Steps 1–45)
Y2L format, AWM2, AN-X basics, FM-X OP foundation

---

### Blob header layout (blob[0:25])

```
blob[0:4]   = 0x00000015 (format version, always)
blob[4:24]  = 20-byte name field:
              blob[4:4+name_len] = ASCII name
              blob[4+name_len]   = 0x00 (null terminator)
              blob[4+name_len+1:20] = 0x00 (padding, MUST be zero)
              blob[20:24]        = flash address (0x15bcXXXX) if waveform requires it,
                                   otherwise 0x00000000
blob[24]    = first parameter byte (real performance data)
blob[25:]   = remaining performance parameters
```


### Forge fix: sanitizePerfBlob()

`sanitizePerfBlob()` runs on every blob in buildYSFC:
1. Zeroes blob[null_pos+1:20] (name padding)
2. Writes correct blob[20:24] from `BLOB_NAME_CORRECTIONS` table (based on ESP reference files)
3. For performances NOT in the table: blob[20:24] is zeroed (conservative fallback)


### Timestamp bytes (not validated)

blob[6722:6726] = timestamp/ID written by MODX on save. Varies per export.
These are NOT validated by MODX. Forge does not need to match them.

---

## ANX DPFM Blob Parameter Offsets — Step_71 (111 files, 2026-05-04)

All offsets are blob-absolute. The blob starts with `blob[0:4]=0x00000015`, `blob[4:24]=name`.  
**Noise/timestamp bytes (always ignore):** `{23, 24, 6722, 6723, 6724, 6725, 6726, 6727}`

### Performance level: Switches [24:52]

| Offset | Parameter | Type | Default | Values |
|--------|-----------|------|---------|--------|
| [38] | ArpMaster switch | bool | 0 | 0=off 1=on |
| [39] | MSMaster switch | bool | 0 | 0=off 1=on |
| [40] | Assign1 switch | bool | 1 | 0=off 1=on |
| [41] | Assign2 switch | bool | 1 | |
| [42] | Assign3 switch | bool | 1 | |
| [43] | Assign4 switch | bool | 1 | |
| [44] | Assign5 switch | bool | 1 | |
| [45] | Assign6 switch | bool | 1 | |
| [46] | Assign7 switch | bool | 1 | |
| [47] | Assign8 switch | bool | 1 | |
| [51] | SuperKnobMS switch | bool | 0 | 0=off 1=on |

### Seq Lane1 Common (performance level)

| Offset | Parameter | Type | Default | Note |
|--------|-----------|------|---------|------|
| [100] | Lane1 Common Swing | u8 | 0x80=128 | 0x80+n center, 0xb2=50% |
| [102] | Lane1 Common Unit | u8 | 3 | 0=100%, 3=1/16 |

### Assign values [184:200] and SuperKnob [670:672]

| Offset | Parameter | Type | Default | Note |
|--------|-----------|------|---------|------|
| [184:186] | Assign1 value | u16le | 512 | |
| [186:188] | Assign2 value | u16le | 512 | |
| [188:190] | Assign3 value | u16le | 512 | |
| [190:192] | Assign4 value | u16le | 512 | |
| [192:194] | Assign5 value | u16le | 512 | |
| [194:196] | Assign6 value | u16le | 512 | |
| [196:198] | Assign7 value | u16le | 512 | |
| [198:200] | Assign8 value | u16le | 512 | |
| [670:672] | SuperKnob value | u16le | 512 | |

### ArpSelect, SyncQuantize, MSSelect

| Offset | Parameter | Type | Default | Note |
|--------|-----------|------|---------|------|
| [358] | ArpSelect | u8 | 0 | 0-indexed: 0=1, 1=2, 7=8 |
| [360] | SyncQuantize | u8 | 0 | 0=OFF, 3=120 |
| [654] | MSSelect | u8 | 0 | 0-indexed: 0=1, 1=2, 7=8 |

### Seq Lane1 Common Params [656:664]

| Offset | Parameter | Type | Default | Note |
|--------|-----------|------|---------|------|
| [656] | Lane1 Common Amplitude | u8 | 0x80=128 | 0x80+n |
| [658] | Lane1 Common Shape | u8 | 0x40=64 | 0x40+n |
| [660] | Lane1 Common Smooth | u8 | 0x80=128 | 0x80+n |
| [662] | Lane1 Common Random | u8 | 0x80=128 | 0x80+n |

### MidPosition + Assign Positioners [672:722]

**Layout:** `[672]` = MidPos global enable (bool). AssignN positioners start at `[674]`, stride=6 per assign (N=0..7):
- `blob[674+N*6]` = AssignN LeftPosition (u8, default=0)
- `blob[676+N*6:+2]` = AssignN MidPosition (u16le, default=512)
- `blob[678+N*6:+2]` = AssignN RightPosition (u16le, default=1023)

| Offset | Parameter | Type | Default |
|--------|-----------|------|---------|
| [672] | MidPosition enable | bool | 0 |
| [674] | Assign1 LeftPosition | u8 | 0 |
| [676:678] | Assign1 MidPosition | u16le | 512 |
| [678:680] | Assign1 RightPosition | u16le | 1023 |
| [680] | Assign2 LeftPosition | u8 | 0 |
| [682:684] | Assign2 MidPosition | u16le | 512 |
| [684:686] | Assign2 RightPosition | u16le | 1023 |
| ... | (stride 6 per assign) | | |
| [716] | Assign8 LeftPosition | u8 | 0 |
| [718:720] | Assign8 MidPosition | u16le | 512 |
| [720:722] | Assign8 RightPosition | u16le | 1023 |

### Part level

| Offset | Parameter | Type | Default |
|--------|-----------|------|---------|
| [6737] | PartSwitch | bool | 1 |

### Arp Common [6802:7165]

| Offset | Parameter | Type | Default | Note |
|--------|-----------|------|---------|------|
| [6802] | ArpPlayOnly | bool | 0 | |
| [6804] | Arp Loop | bool | 1 | 0=off 1=on |
| [6805] | StartQuantize | bool | 1 | |
| [6806] | RandomSFX | bool | 1 | |
| [6807] | KeyOnControl | bool | 1 | |
| [6887] | Arp Swing / Lane1 Part Swing | u8 | 0x80 | 0x80+n, shared offset |
| [6889] | Lane1 Part Amplitude | u8 | 0x80 | 0x80+n |
| [6891] | Lane1 Part Shape | u8 | 0x40 | 0x40+n |
| [6893] | Lane1 Part Smooth | u8 | 0x80 | 0x80+n |
| [6895] | Lane1 Part Random | u8 | 0 | direct 0..100 |
| [6905] | ArpGroup | u8 | 0 | 0=off 1=A 0x10=P |
| [6917] | ArpEnable area | u8 | 0x80 | 0x80=idle 0x89=arp active |
| [7095] | Hold | u8 | 1 | 0=SyncOff 1=Off 2=On |
| [7097] | Arp Unit / Lane1 Part Unit | u8 | 3 | 0=100%, 3=1/16, shared offset |
| [7099] | ArpNoteLimit_Low | u8 | 0 | MIDI note |
| [7101] | ArpNoteLimit_High | u8 | 127 | MIDI note |
| [7103] | ArpVelLimit_Low | u8 | 1 | |
| [7105] | ArpVelLimit_High | u8 | 127 | |
| [7107] | KeyMode | u8 | 0 | 0=normal 1=Thru |
| [7109] | VelocityMode | u8 | 0 | 0=normal 1=Thru |
| [7111] | ChangeTiming | u8 | 1 | 1=beat 0=Real-Time |
| [7113] | QuantizeValue | u8 | 3 | 3=120, 2=80 |
| [7115] | QuantizeStrength | u8 | 0 | direct 0..100 |
| [7117] | VelocityRate | u8 | 100 | direct 0..200 |
| [7119] | GateTimeRate | u8 | 100 | direct 0..200 |
| [7121] | Accent_VelThreshold | u8 | 0 | direct 0..127 |
| [7123] | OctaveRange | u8 | 0x40 | 0x40+n (center=0=0x40, +2=0x42) |
| [7125] | OctaveShift | u8 | 0x40 | 0x40+n (center=0=0x40, +6=0x46) |
| [7127] | TriggerMode | u8 | 0 | 0=normal 1=Toggle |
| [7129] | VelocityOffset | u8 | 0x40 | 0x40+n (center=0=0x40, +5=0x45) |
| [7131] | Arp1 Velocity | u8 | 0x80 | 0x80+n, 10%=0x8a |
| [7133] | Arp1 GateTime | u8 | 0x80 | 0x80+n, 10%=0x8a |
| [7163] | Arp1 Name type_id | u8 | 79 | arpeggio bank/type index |
| [7164] | Arp1 Name pattern_id | u8 | 25 | pattern index within type |

### Seq Lane Block (stride=884 per lane)

Lane bases: Lane1=8929, Lane2=9813, Lane3=10697, Lane4=11581

| Relative offset | Parameter | Type | Default | Note |
|--------|-----------|------|---------|------|
| +0 | LaneSwitch | bool | 0 | 0=off 1=on |
| +1 | MSFXSwitch | bool | 1 | 0=off 1=on |
| +2 | Trigger | bool | 0 | |
| +3 | Loop | bool | 1 | 0=off 1=on |
| +8 | Sync switch | bool | 0 | 1=sync |
| +10 | Speed | u8 | 0x3f=63 | direct |
| +12 | Sync_Tempo_Unit | u8 | 3 | 3=default, 9=400% |
| +14 | KeyOnReset | u8 | 0 | 0=off, 2=1stOn |
| +16 | LaneVelLimit_Low | u8 | 1 | |
| +18 | LaneVelLimit_High | u8 | 127 | |
| +20 | DelayTime | u8 | 0 | |
| +22 | DelaySteps | u8 | 0 | |
| +24 | FadeInTime | u8 | 0 | |
| +26 | FadeInSteps | u8 | 0 | |
| +36 | Amp | u8 | 127 | |
| +38 | Smooth | u8 | 0 | |
| +42 | Polarity | bool | 0 | 0=unipolar 1=bipolar |
| +44 | MSGrid | u8 | 3 | 3=default, 1=60 |
| +116 | PulseA Type | u8 | 0 | 0=Standard 2=Threshold |
| +118 | PulseA Prm1 | u8 | 5 | |
| +120 | PulseA Prm2 | u8 | 0 | |
| +122 | ControlA Switch | bool | 1 | |
| +124 | ControlA ControlSwitch | bool | 0 | |
| +128 | PulseB Type | u8 | 0 | 0=Standard 2=Threshold |
| +130 | PulseB Prm1 | u8 | 5 | |
| +132 | PulseB Prm2 | u8 | 0 | |
| +134 | ControlB Switch | bool | 1 | |
| +136 | ControlB ControlSwitch | bool | 0 | |

### Metadata

| Offset | Parameter | Type | Default | Note |
|--------|-----------|------|---------|------|
| [12753] | Part seq-field | u8 | 3 | 3=default, 4=seq-sync active |
| [13116] | Part arp-field | u8 | 0 | 0=default, 9=arp active |

---

## AN-X OSC1 — Final Corrected Map (Steps 72–73, 2026-05-08)

### Corrected and new fields

| PART+ | abs | Name | Type | Default | Encoding | Status |
|-------|-----|------|------|---------|----------|--------|
| 5934 | 12642 | selfSyncPitchEGDepth | u16le | 256 | raw=UI+256 | ★★★★★ Step74 |
| 5950 | 12658 | shaperEGDepth | u8 | 128 | 0x80+n | ★★★★★ Step73 |
| 5952 | 12660 | shaperLFODepth | u8 | 128 | 0x80+n | ★★★★★ Step73 |

**Error in previous serializer:** `anxOsc1SelfSyncLFODepth=5934` was incorrect.
Real `selfSyncLFODepth = PART+5936`. Fixed in Serializer v6.

### EG/LFO depth matrix (complete)

```
Modulation target  │  EG Depth        │  LFO Depth
───────────────────┼──────────────────┼──────────────────
Sync               │  PART+5924 ✅    │  PART+5928 ✅
Sync Pitch/Vel     │  PART+5926 ✅    │  PART+5930 ✅
Sync Pitch EG      │  PART+5934 ✅    │  PART+5936 ✅
Pulse Width        │  PART+5942 ✅    │  PART+5944 ✅
Shaper             │  PART+5950 ✅    │  PART+5952 ✅
```

**OSC1 block is now 100% mapped.** No unknown fields remaining.

### WaveFolder encodings (Step 72, all now ★★★★★)

| Parameter | abs | Encoding | Default |
|-----------|-----|----------|---------|
| VelSens | 13118 | direct | 0 |
| EGDepth | 13120 | 0x80+n | 128 |
| LFODepth | 13122 | 0x80+n | 128 |
| Texture | 13124 | **direct** (NOT 0x80+n!) | 128 |

### New CA destinations (Step 72)

- Dest=142 = FilterCutoff
- Dest=118 = ANX Pan

---

## PART+5934 Confirmed + MODX M8 File Size (Step 74, 2026-05-08)

### PART+5934 = selfSyncPitchEGDepth ★★★★★

Confirmed via MODX M8 hardware export `eg_depth_sync.Y2L`:
- `PART+5934` changed from 256 → 356 (Δ=+100)
- `PART+5936` (selfSyncLFODepth) unchanged = 256
- → The parameter is independent and binary-verified ✅

**Encoding:** `raw = UI + 256` (center=256, range 0–512)
NOTE: DIFFERENT encoding from selfSyncLFODepth (`round(UI/25)+256`)

Complete OSC1 EG/LFO matrix:

```
                   EG Depth          LFO Depth
Sync (Pitch):      PART+5924 ✅      PART+5928 ✅
Sync Pitch/Vel:    PART+5926 ✅      PART+5930 ✅  (selfSyncPitch)
Sync Pitch EG:     PART+5934 ✅ NEW  PART+5936 ✅  (selfSyncLFODepth)
Pulse Width:       PART+5942 ✅      PART+5944 ✅
Shaper:            PART+5950 ✅      PART+5952 ✅
```

**No unknown fields remain in the OSC1 block.** OSC1 is now 100% mapped.

### Why MODX M8 files are larger than ESP Plugin files

M8 hardware exports 7 chunks, ESP Plugin exports 5:

| Chunk | ESP Plugin | MODX M8 | Size |
|-------|-----------|---------|------|
| ELST | ❌ | ✅ | ~54 bytes |
| ESYS | ✅ | ✅ | 46 bytes |
| EFVT | ✅ | ✅ | 163 bytes |
| DPFM | ✅ | ✅ | identical (the actual performance data) |
| **DLST** | ❌ | ✅ | **~84 KB** |
| DSYS | ✅ | ✅ | 1094 bytes |
| DFVT | ✅ | ✅ | 22219 bytes |

**DLST** = Live Set Data = the complete user bank (all User performances).
MODX M8 embeds its complete user bank in every Y2L export.
ESP Plugin exports only the selected performance.

Forge reads only DPFM → already handles M8 files correctly. No action needed.
