# YSFC Forge — Full Context v10.0
*Uppdaterad: 2026-05-03 | Steg 1–62 + Container-analys | KARTLÄGGNING KOMPLETT*

---

## Startprompt för ny chatt

```
Vi fortsätter ett YSFC Forge-projekt — reverse-engineering av Yamaha MODX/Montage Y2L-format
och byggande av patch editor.

Deliverables (alla i outputs/):
  ysfc_serializer.py v5.5   — 422/462 fält kartlagda (91%)
  ysfc_forge_v1.10.html     — HTML/JS merge-verktyg (verifierat MODX M8x)
  ysfc_fx_type_index.py     — 57 InsertionFX TypeIndex-värden
  YSFC_PARAMETERBETYG_v5.txt
  YSFC_FORGE_FULL_CONTEXT_v10.md — denna fil

STATUS: Kartläggningsfasen avslutad + container-struktur fullt dokumenterad (v10).
Nästa fokus: PATCH EDITOR.
  - FM-X: OP 21/21 ★★★★★, Part PEG 16/16, 1st LFO 11/11, 2nd LFO 7/7
  - AWM2: Element ~87%, Part 100%
  - AN-X: ~85% (PulseWidth korrigerat, EG komplett)
  - CA: 100% engine-oberoende, FX-tabell komplett (57 typer)
  - Container: EPFM/DPFM/ESYS/DSYS/EFVT/DFVT fullt dokumenterade ★★★★★
```

---

## Projektöversikt

**Mål:** Reverse-engineera Y2L-format, bygga merge-verktyg + patch editor.

**Forge-app:** Fullt fungerande merge-verktyg, verifierat på MODX M8x.
**Serializer:** v5.5, 422 av 462 dokumenterade fält kartlagda (91%).

---

## Kartläggningsstatus (Steg 1–62)

| Engine/Sektion | Fält | ★★★★★ | ★★★★☆ | Täckning |
|----------------|------|--------|--------|----------|
| FM-X OP (×8) | 29 | 26 | 3 | 100% |
| FM-X Part PEG | 16 | 16 | 0 | 100% |
| FM-X Part 1st LFO | 11 | 11 | 0 | 100% |
| FM-X Part 2nd LFO | 8 | 7 | 1 | 100% |
| FM-X Part Common | 15 | 12 | 3 | 100% |
| AWM2 Element | 150 | 90 | 40 | 87% |
| AWM2 Part | 26 | 20 | 6 | 100% |
| AN-X Part | 130 | 85 | 25 | 85% |
| Insertion FX | 57 | 12 | 45 | 100% |
| Controller Assign | 8 | 7 | 1 | 100% |
| Performance Common | 10 | 6 | 4 | 100% |
| AT Register | 2 | 2 | 0 | 100% |
| **TOTALT** | **462** | **294** | **128** | **91%** |

---

## Y2L / Y2U Filstruktur — KOMPLETT ★★★★★

*(Binärverifierat 2026-05-03 mot AWM2/FM-X/AN-X init-filer + 1/2/4-perf filer)*

**Timestamp-bytes** (ignoreras i diffs): PERF+23, +24, +6724, +6725  
**CA+17** är MODX-internt (ej synlig parameter, ignoreras)  
**OP Mute/Solo** sparas INTE i YSFC (real-time state)

---

### 1. Fil-header (64 bytes)

```
File[0:12]  = b'YAMAHA-YSFC\x00'
File[12:20] = version string (e.g. b'5.1.2\x00\x00\x00')
File[20:62] = padding
File[62]    = 0x2a (fast konstant)
File[63]    = checksumma (ej validerad av MODX)
```

---

### 2. EPFM chunk (startar på File[64])

```
File[64:68]   = b'EPFM'
File[68:72]   = EPFM payload size (u32be) — alltid 353, även för multi-perf!
File[72:]     = EPFM payload
```

**EPFM payload-layout:**

```
[0:64]    CHUNK DIRECTORY — 8 slots × 8 bytes
          Varje slot: [4 bytes ASCII-tag][4 bytes absolut fil-offset]
          Tomma slots: 0xFF × 8
          
          Typisk ordning (utan Live Set):
            Slot 0: 'ESYS' + file_offset_ESYS
            Slot 1: 'EFVT' + file_offset_EFVT
            Slot 2: 'DPFM' + file_offset_DPFM
            Slot 3: 'DSYS' + file_offset_DSYS
            Slot 4: 'DFVT' + file_offset_DFVT
            Slot 5–7: 0xFF × 24
          
          Med Live Set (Y2L library):
            Lägger till 'ELST' och 'DLST' slots.
          
          ⚠️ Övriga chunks hittas INTE via sekventiell scan — alltid
             använd directory-offsettarna!

[64:280]  PADDING — 0xFF × 216 (konstant, oavsett antal performances)

[280]     0x00 (separator-byte)

[281:]    PERFORMANCE CATALOG — grows with N
          Format:
            [0:4]  b'EPFM'         (sub-tag)
            [4:8]  catalog_size    (u32be) = 8 + Σ(8 + Entr_size) för alla N
                   → 1 perf: 81, 2 perfs: 147, 4 perfs: 275
            [8:12] N               (perf-antal, u32be)
            [12:]  N × Entr-records (packade utan mellanrum)
          
          ⚠️ Katalogen kan överlappa EPFM-chunkens gräns (storlek=353)
             vid fler än ~3 performances. EPFM chunk size=353 uppdateras
             INTE — de absoluta fil-offsettarna i directory förblir korrekta.
```

**Entr-record (ett per performance):**

```
[0:4]   b'Entr'
[4:8]   Entr record size (u32be) — varierar med namnlängd
[8:]    Entr record data:
  [0:4]   blob_size   — storlek på detta perfs Data-blob i DPFM (u32be)
  [4:8]   blob_dp_off — DPFM-payload-relativt offset till blob[0] (u32be)
                        = 12 för blob0, 12+(8+sz0) för blob1, etc.
  [8]     0x00
  [9]     0x40 (= 64, konstant)
  [10]    0x00
  [11]    entry_index (0-baserat index i denna fil)
  [12]    0x00
  [13]    okänd flagga (0x01 eller 0x00)
  [14]    0x00
  [15]    okänd flagga (0x04 vanligast, 0x01 för ESYS)
  [16]    okänd flagga (0x02 eller 0x00)
  [17]    0x00
  [18:25] okända bytes (mestadels 0x00)
  [25]    0x30 (= 48, konstant)
  [26:]   namnfält: [1 okänd byte][ASCII "SLOT:Långt namn:Kort namn\x00"]
                    SLOT = decimalt slot-nr (t.ex. "128")
                    Långt namn: upp till 20 tecken
                    Kort namn: upp till 8 tecken
```

---

### 3. DPFM chunk

**Hittas via EPFM directory** (absolut fil-offset).

```
DPFM_TAG[0:4]  = b'DPFM'
DPFM_TAG[4:8]  = payload size (u32be)
dp = raw[offset+8:]  ← dp[0] = DPFM payload start (= find_dpfm()-returvärde)

dp[0:4]   = N (perf-antal, u32be)
dp[4:8]   = b'Data'  (första Data-subpost-tag)
dp[8:12]  = blob0_size (u32be)
dp[12:]   = blob0 data
dp[12+blob0_size:]   = b'Data' + blob1_size + blob1 data
... (N Data-subposter totalt, packade)
```

**Performance blob-struktur:**

```
blob[0:4]   = 0x00000015 (format-konstant, alltid 21)
blob[4:N]   = performance-namn, null-terminerad ASCII (variabel längd)
blob[N:24]  = nollpadding till byte 24
blob[24:]   = performance-parameterdata
```

**KOORDINATSYSTEM för FIELD_REGISTRY:**

```
Alla offset i FIELD_REGISTRY är dp-relativa (relativt dp[0]):

dp[0:12]   = DPFM-header (count + 'Data' + blob0_size)
dp[12]     = blob0[0] = 0x00 (del av 0x00000015-konstanten)
dp[12+24]  = blob0[24] = första parameterbyte

Exempel:
  CA_PERF_BASE     = 2451   → dp[2451]
  PART_BLOCK_START = 6708   → dp[6708]
  AWM2_ELEM1_BASE  = 12532  → dp[12532]

find_dpfm() returnerar dp[0]-offset (= DPFM tag-offset + 8) ✅
```

---

### 4. ESYS / DSYS (System Settings)

**Storlekarna är konstanta, innehållet engine-oberoende.**

```
ESYS payload (46 bytes, konstant):
  [0:4]  count = 1
  [4:8]  b'Entr'
  [8:12] Entr record size = 34
  [12:]  Entr data:
    [0:4]  DSYS blob_size = 1082
    [4:8]  blob_dp_off = 12
    [26:]  b'\x00System\x00'

DSYS payload (1094 bytes, konstant):
  [0:4]  count = 1
  [4:8]  b'Data'
  [8:12] blob_size = 1082
  [12:]  blob (1082 bytes, system-parametrar):
    blob[0:4] = 0x00000050 (format-konstant — skiljer sig från DPFMs 0x15!)
    blob[4:]  = system-parametrar (ej kartlagda)
```

---

### 5. EFVT / DFVT (Favorites)

**Storlekarna är konstanta, innehållet engine-oberoende.**

```
EFVT payload (163 bytes, konstant):
  [0:4]  count = 3
  Entr[0] PerformanceFavorite: blob_size=3621,  blob_dp_off=12
  Entr[1] ArpeggioFavorite:    blob_size=10922, blob_dp_off=3641
  Entr[2] WaveformFavorite:    blob_size=7648,  blob_dp_off=14571

DFVT payload (22219 bytes, konstant):
  [0:4]  count = 3
  3 × Data-subposter:
    Data[0] size=3621  (PerformanceFavorite, mestadels nollor)
    Data[1] size=10922 (ArpeggioFavorite, mestadels nollor)
    Data[2] size=7648  (WaveformFavorite, mestadels nollor)
  Kontroll: 12 + 3621 + 8 + 10922 + 8 + 7648 = 22219 ✅

⚠️ ESYS/DSYS/EFVT/DFVT är IDENTISKA mellan AWM2/FM-X/AN-X och
   mellan 1/2/4-perf filer → kopiera alltid verbatim vid merge.
```

---

### 6. ELST / DLST (Live Set — Library-filer)

Finns i Y2L-filer med Live Set-innehåll. Speglar EPFM/DPFM-mönstret (Entr-index + Data-blobbar). Lågprioriterat, ej fullständigt kartlagt.

---

---

## FM-X OP Layout — KOMPLETT ★★★★★

**OP1_BASE=12676, stride=123, 8 OPs**

| off | Fält | Encoding | Default |
|-----|------|----------|---------|
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

**Kritiska korrektioner:**
- off=20 = **pegAttackTime** (PEG, vänster panel — ej AEG!)
- off=22 = **pegDecayTime** (PEG Decay — ej aegDelayTime!)
- off=32 = **aegAttackTime** (AEG, höger panel)

---

## FM-X Part Sections

### PEG Block (abs 12477–12507) — 16/16 ★★★★★
Encoding PEG Levels: `center=50` (`raw = ui + 50`)  
PEG Depth enum: raw 0-3 = [8oct, 2oct, 1oct, 0.5oct] (8oct=default!)  
PitchKeyFollow: `round(pct×64/200) + 64`

### 1st LFO Block — 11/11 ★★★★★
Wave enum: 0=Triangle...12=User (13 värden)  
TempoNote: `raw = list_index + 5`, default=11=1/4  
FadeOut: center/default=64. Loop: INVERTERAT bool (0=On)

### 2nd LFO Block — 7/7 ★★★★★

| abs | PART+ | Fält | Default |
|-----|-------|------|---------|
| 12509 | +5801 | Wave (enum 0-12) | 0 |
| 12511 | +5803 | SpeedNormal | 30 (Ext=OFF) |
| 12513 | +5805 | Phase (enum 0=0°..4=360°) | 0 |
| 12515 | +5807 | Delay | 0 |
| 12517 | +5809 | KeyOnReset | 0 |
| 12529 | +5821 | Extended | 1=ON |
| 12531 | +5823 | SpeedExtended | 60 (Ext=ON) |

---

## Insertion FX — KOMPLETT (57 typer)

`FX_TYPE_INDEX` i `ysfc_fx_type_index.py` — gäller InsA och InsB identiskt.  
Encoding: `lo = idx & 0x7F`, `hi = (idx >> 7) & 0x7F`

Urval binärverifierade ★★★★★:
`THRU=0, SPX HALL=130, CROSS DELAY=256, SYMPHONIC=432, CLASSIC FLANGER=528, TREMOLO=784, COMP DISTORTION=928, CLASSIC COMPRESSOR=1040, VCM AUTO WAH=1280, NOISY=1424, SLICE=1616, PRESENCE=1672, WAVE FOLDER=1704`

Symphonic+Classic Flanger parametrar: se v8.0

---

## Controller Assign — ENGINE-OBEROENDE ★★★★★

`CA_STRIDE=22, CA_PART_BASE=8220, CA_PERF_BASE=2451`

| CA+ | Fält | Encoding | Default |
|-----|------|----------|---------|
| +1 | SW | bool | 0=Off |
| +3 | Source | enum | 1=MW |
| +5 | Destination | enum | 1=Volume |
| +9 | CurveType | enum | 0=Standard |
| +11 | Param1 | direct | 5 |
| +13 | Param2 | direct | 0 |
| +15 | Polarity | bool | 0=UNI |
| +17 | *(MODX-internt)* | ignoreras | 192 |

**Source:** PB=0, MW=1, Knob1=8, Knob2=9, Knob3=10  
**Destination:** Volume=1, InsA Param2-24 (linjärt), InsB=25, Rev=50, Var=51, ElemLevel=60, ElemPan=61, Cut=85, HPF=87, PartPan=100, Arp=105, MSLen=118

**CurveType:** Standard=0, Sigmoid=1, Threshold=2, Harmonic=18, Steps=19

---

## AN-X — Korrektioner (Steg 60-61)

**OSC EG korrigerade offsets:**
- `anxOsc1EGAttackTime=5970` (var 5813)
- `anxOsc2EGAttackTime=6095` (var 5938)
- `anxOsc3EGAttackTime=6220` (var 6063)

**PulseWidth:** `anxOsc1PulseWidth=5938`, encoding: `raw=round(pct×256/100)`

**OSC2 EGDepth/LFODepth:** 6067/6069 (stride=125 från 5942/5944)

---

## AWM2 AfterTouch Register

```
AWM2_AT_ASSIGN = {atSwitch: PART+593, atDestination: PART+595}
AT_DESTINATION = {1: 'Pitch', 9: 'FilterCutoff'}
```
Separat från CA-blocket, egen destination-encoding.

---

## Encoding-tabell (komplett)

| Typ | Formel |
|-----|--------|
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

## Kvarstående (lågprioriterade)

| Area | Beskrivning |
|------|-------------|
| FM-X 2nd LFO Depth-matris | abs=12547+, PitchMod×8+AmpMod×8+FilterMod, default=0 |
| FM-X OP routing matrix | abs=6730-6793, 64 bytes default=1, aldrig ändrat via UI |
| AWM2 ctrlSet element-nivå | Offset ej binärverifierat |
| Performance Common 0:6708 | Scene/SuperKnob/MotionSeq — komplex |
| Montage .X7L/.X8L | Sannolikt identiskt, ej testat |
| WaveFolder Fold encoding | 0.386→130, 0.5→244, formel oklar |

---

## Nästa fas: Patch Editor

Rekommenderad arkitektur för editor i forge-appen:
1. **Läs performance** från Y2L → parse DPFM → perf-bytes
2. **Decode parametrar** via serializer-dict + encoding-funktioner
3. **UI-lager** per engine/sektion (FM-X OP, AWM2 Elem, AN-X OSC...)
4. **Encode + skriv** ändrade bytes tillbaka till perf-buffer
5. **Exportera** ny Y2L via befintlig `buildYSFC`-funktion

Enklaste startpunkt: FM-X algorithm + feedback + OP levels (off=44) — synliga sliders med direkt encoding.

---

## Changelog

### v10.0 (2026-05-03) — Container-struktur fullt dokumenterad
- EPFM payload: directory (64 bytes) + padding (216 bytes) + katalog-struktur
- Katalog: sub-tag 'EPFM' + catalog_size + count + N×Entr-records
- Entr-record: alla fält avkodade (blob_size, blob_dp_off, entry_index, namn-format)
- DPFM: Data-subposter, blob-header (0x15-konstant + namn + padding till byte 24)
- FIELD_REGISTRY koordinatsystem bekräftat: dp-relativt (dp[0] = DPFM payload start)
- ESYS/DSYS: konstanta storlekar (46/1094 bytes), system-blob header = 0x50
- EFVT/DFVT: konstanta storlekar (163/22219 bytes), 3 favorit-kategorier
- Bekräftat: ESYS/DSYS/EFVT/DFVT identiska across alla engines och perf-antal

### v9.0 (Steg 53–62, 2026-04-26) — Kartläggning komplett
- FM-X 2nd LFO: Phase+Delay tillagda → 7/7 komplett
- WaveFolder TypeIndex=1704 → FX-tabell 57 typer komplett
- AN-X PulseWidth=5938 korrigerat + encoding raw=round(pct*256/100)
- AWM2 AT-register: SW=593, Dest=595
- OP Mute: sparas ej i YSFC
- FM-X OP routing matrix identifierad (abs=6730-6793)
- 422/462 fält (91%) kartlagda

### v8.0 (Steg 46–52)
FM-X OP 21/21, Symphonic FX, AN-X EG, CA engine-oberoende

### v7.0 (Steg 1–45)
Y2L-format, AWM2, AN-X grundläggande, FM-X OP-bas

---

## AWM2 Element Waveform Numbers — Expansion Pack Detection (Steg 70, 2026-05-03)

### Waveformtalets innebörd (binärverifierat mot Soundmondo.Y2L, 98 performances)

| Waveformtal | Typ | Tillgänglighet |
|---|---|---|
| 0 | Element inaktiverat | Alltid |
| 1–256 | Inbyggt ROM-ljud (preset) | Alltid tillgängligt |
| 257+ | Expansionspaket-sample | Kräver Y2E/X8L installerat |

**Offset:** `blob[12520 + elem * 313]` (u16le), elementindex 0-baserat (max 8 element)  
**Stride:** 313 bytes per AWM2-element (oförändrat från tidigare)  
**Regel:** `waveformNumber > 256` → performances kräver expansionspaket

### Felkoppling

`Storage read/write error` på MODX/ESP Plugin = expansionspaketet saknas.  
Detta är **inte** ett filformatfel. Containern och DPFM-strukturen kan vara helt korrekta.  
Enda lösningen: installera rätt expansionspaket (Y2E-fil) på MODX/ESP.

### Bekräftat från Soundmondo.Y2L

- 98 performances totalt
- 85 kräver expansion (wf > 256 i minst ett element)
- 13 fungerar med enbart inbyggda ljud (wf 1-256 i alla element):
  C7 Grand +, CFX Concert +, S700 for Montage +, CFX Stage +, C7 +,
  Mellow Hamburg Gra +, Concert GrandPiano +, Natural Grand S6 +,
  CFX Single Grand 1 +, Korg M1 Piano 16, CFX PopStudioGrand +,
  U1 Upright Bright +, Traditional Upright+

### waveformBank (blob[12522])

Värdet `1` för ALLA performances (både builtin och expansion) — kan EJ användas
för att skilja expansion från inbyggd. Använd waveformNumber-tröskeln 256 istället.

---

## Blob-format: Skillnad mellan Soundmondo.Y2L och fabriksfiler (2026-05-04)

### Bekräftad rotorsak till "Storage read/write error" för Soundmondo-performances

Problemet är **EXKLUSIVT** kopplat till `Soundmondo.Y2L`. Fabriksfiler (ESP_8_performances.Y2L,
Init-filer, Performance-filer) fungerar korrekt — Forge exporterar dem byte-identiska med originalet
(bortsett från kända timestamp-bytes blob[6722:6726]).

### Blob-header layout (blob[0:25])

```
blob[0:4]   = 0x00000015 (formatversion, alltid)
blob[4:24]  = 20-byte namnfält:
              blob[4:4+name_len] = ASCII-namn
              blob[4+name_len]   = 0x00 (null-terminering)
              blob[4+name_len+1:20] = 0x00 (padding, MÅSTE vara noll)
              blob[20:24]        = flash-adress (0x15bcXXXX) om waveform kräver det,
                                   annars 0x00000000
blob[24]    = första parameterbyte (real performance-data)
blob[25:]   = resterande performance-parametrar
```

### Soundmondo-specifika fel i blob-headern

Soundmondo.Y2L har ICKE-NOLLA värden i padding- och flash-adressfälten:

| Performance | null@blob | Soundmondo blob[null:24] | ESP (korrekt) blob[null:24] |
|---|---|---|---|
| CFX + FM EP + | 17 | `030001000000` | `000000000000` |
| Waterloo SM | 15 | `6431030001000000` | `00000015bcc9fe` (flash addr!) |
| Take on me SM | 17 | `0000810000` | `000015bccea1` (flash addr!) |
| Korg M1 Piano 16 | 20 | `0000` (i parameterarea) | `0000` |

ESP Plugin korrigerar dessa när det exporterar — skriver korrekt flash-adress för
waveforms som pekar på ROM-samplar. MODX validerar blob[20:24] vid inläsning →
fel värde = "Storage read/write error".

### Forge-fix: sanitizePerfBlob()

`sanitizePerfBlob()` körs på varje blob i buildYSFC:
1. Nollställer blob[null_pos+1:20] (name padding)
2. Skriver korrekt blob[20:24] från `BLOB_NAME_CORRECTIONS`-tabell (baserad på ESP-referensfiler)
3. För performances INTE i tabellen: blob[20:24] nollställs (konservativ fallback)

`BLOB_NAME_CORRECTIONS`-tabell (verifierad mot ESP_8_performances.Y2L):
- `CFX + FM EP +` → blob[17:24] = `00000000000000`
- `Waterloo SM` → blob[15:24] = `000000000015bcc9fe`
- `Take on me SM` → blob[17:24] = `00000015bccea1`
- `Korg M1 Piano 16` → blob[20:24] = `00000000`

### Varför fabriksfiler fungerar

ESP_8_performances.Y2L exporterades DIREKT av ESP Plugin → blobs har redan korrekta värden.
Forge kopierar dessa verbatim → output är identisk med ESP-export → fungerar perfekt.

Soundmondo.Y2L är exporterat av ett annat system (Soundmondo-webbsite) med legacy-format
där blob[null+1:24] innehåller annan metadata istället för korrekt MODX-format.

### Timestamp-bytes (ej validerade)

blob[6722:6726] = timestamp/ID skrivet av MODX vid sparning. Varierar per export.
Dessa valideras INTE av MODX. Forge behöver inte matcha dem.

---

## ANX DPFM Blob Parameter Offsets — Steg_71 (111 filer, 2026-05-04)

Alla offset är blob-absoluta. Blobben börjar med `blob[0:4]=0x00000015`, `blob[4:24]=namn`.
**Noise/timestamp-bytes (ignorera alltid):** `{23, 24, 6722, 6723, 6724, 6725, 6726, 6727}`

### Performance-nivå: Switchar [24:52]

| Offset | Parameter | Typ | Default | Värden |
|--------|-----------|-----|---------|--------|
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

### Seq Lane1 Common (perf-nivå)

| Offset | Parameter | Typ | Default | Notering |
|--------|-----------|-----|---------|---------|
| [100] | Lane1 Common Swing | u8 | 0x80=128 | 0x80+n center, 0xb2=50% |
| [102] | Lane1 Common Unit | u8 | 3 | 0=100%, 3=1/16 |

### Assign-värden [184:200] och SuperKnob [670:672]

| Offset | Parameter | Typ | Default | Notering |
|--------|-----------|-----|---------|---------|
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

| Offset | Parameter | Typ | Default | Notering |
|--------|-----------|-----|---------|---------|
| [358] | ArpSelect | u8 | 0 | 0-indexerat: 0=1, 1=2, 7=8 |
| [360] | SyncQuantize | u8 | 0 | 0=OFF, 3=120 |
| [654] | MSSelect | u8 | 0 | 0-indexerat: 0=1, 1=2, 7=8 |

### Seq Lane1 Common Params [656:664]

| Offset | Parameter | Typ | Default | Notering |
|--------|-----------|-----|---------|---------|
| [656] | Lane1 Common Amplitude | u8 | 0x80=128 | 0x80+n |
| [658] | Lane1 Common Shape | u8 | 0x40=64 | 0x40+n |
| [660] | Lane1 Common Smooth | u8 | 0x80=128 | 0x80+n |
| [662] | Lane1 Common Random | u8 | 0x80=128 | 0x80+n |

### MidPosition + Assign Positioner [672:722]

**Layout:** `[672]` = MidPos global enable (bool). AssignN positioner börjar vid `[674]`, stride=6 per assign (N=0..7):
- `blob[674+N*6]` = AssignN LeftPosition (u8, default=0)
- `blob[676+N*6:+2]` = AssignN MidPosition (u16le, default=512)
- `blob[678+N*6:+2]` = AssignN RightPosition (u16le, default=1023)

| Offset | Parameter | Typ | Default |
|--------|-----------|-----|---------|
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

### Part-nivå

| Offset | Parameter | Typ | Default |
|--------|-----------|-----|---------|
| [6737] | PartSwitch | bool | 1 |

### Arp Common [6802:7165]

| Offset | Parameter | Typ | Default | Notering |
|--------|-----------|-----|---------|---------|
| [6802] | ArpPlayOnly | bool | 0 | |
| [6804] | Arp Loop | bool | 1 | 0=off 1=on |
| [6805] | StartQuantize | bool | 1 | |
| [6806] | RandomSFX | bool | 1 | |
| [6807] | KeyOnControl | bool | 1 | |
| [6887] | Arp Swing / Lane1 Part Swing | u8 | 0x80 | 0x80+n, delad offset |
| [6889] | Lane1 Part Amplitude | u8 | 0x80 | 0x80+n |
| [6891] | Lane1 Part Shape | u8 | 0x40 | 0x40+n |
| [6893] | Lane1 Part Smooth | u8 | 0x80 | 0x80+n |
| [6895] | Lane1 Part Random | u8 | 0 | direkt 0..100 |
| [6905] | ArpGroup | u8 | 0 | 0=off 1=A 0x10=P |
| [6917] | ArpEnable area | u8 | 0x80 | 0x80=idle 0x89=arp active |
| [7095] | Hold | u8 | 1 | 0=SyncOff 1=Off 2=On |
| [7097] | Arp Unit / Lane1 Part Unit | u8 | 3 | 0=100%, 3=1/16, delad offset |
| [7099] | ArpNoteLimit_Low | u8 | 0 | MIDI note |
| [7101] | ArpNoteLimit_High | u8 | 127 | MIDI note |
| [7103] | ArpVelLimit_Low | u8 | 1 | |
| [7105] | ArpVelLimit_High | u8 | 127 | |
| [7107] | KeyMode | u8 | 0 | 0=normal 1=Thru |
| [7109] | VelocityMode | u8 | 0 | 0=normal 1=Thru |
| [7111] | ChangeTiming | u8 | 1 | 1=beat 0=Real-Time |
| [7113] | QuantizeValue | u8 | 3 | 3=120, 2=80 |
| [7115] | QuantizeStrength | u8 | 0 | direkt 0..100 |
| [7117] | VelocityRate | u8 | 100 | direkt 0..200 |
| [7119] | GateTimeRate | u8 | 100 | direkt 0..200 |
| [7121] | Accent_VelThreshold | u8 | 0 | direkt 0..127 |
| [7123] | OctaveRange | u8 | 0x40 | 0x40+n (center=0=0x40, +2=0x42) |
| [7125] | OctaveShift | u8 | 0x40 | 0x40+n (center=0=0x40, +6=0x46) |
| [7127] | TriggerMode | u8 | 0 | 0=normal 1=Toggle |
| [7129] | VelocityOffset | u8 | 0x40 | 0x40+n (center=0=0x40, +5=0x45) |
| [7131] | Arp1 Velocity | u8 | 0x80 | 0x80+n, 10%=0x8a |
| [7133] | Arp1 GateTime | u8 | 0x80 | 0x80+n, 10%=0x8a |
| [7163] | Arp1 Name type_id | u8 | 79 | arpeggio bank/type index |
| [7164] | Arp1 Name pattern_id | u8 | 25 | pattern index within type |

### Seq Lane Block (stride=884 per lane)

Lane-baser: Lane1=8929, Lane2=9813, Lane3=10697, Lane4=11581

| Relativ offset | Parameter | Typ | Default | Notering |
|--------|-----------|-----|---------|---------|
| +0 | LaneSwitch | bool | 0 | 0=off 1=on |
| +1 | MSFXSwitch | bool | 1 | 0=off 1=on |
| +2 | Trigger | bool | 0 | |
| +3 | Loop | bool | 1 | 0=off 1=on |
| +8 | Sync switch | bool | 0 | 1=sync |
| +10 | Speed | u8 | 0x3f=63 | direkt |
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

| Offset | Parameter | Typ | Default | Notering |
|--------|-----------|-----|---------|---------|
| [12753] | Part seq-field | u8 | 3 | 3=default, 4=seq-sync aktiv |
| [13116] | Part arp-field | u8 | 0 | 0=default, 9=arp aktiv |

