# Reverse Engineering Status

Detta dokument innehåller den detaljerade reverse-engineering-statusen och metodiken för YSFC Forge. För en översikt, se huvuddokumentet [README](../README.md).

## Innehåll

- [Metodik](#metodik)
- [Testkorpus](#testkorpus)
- [Engine-täckning](#engine-täckning)
- [Täckning per sektion](#täckning-per-sektion)
- [Viktiga fynd](#viktiga-fynd)
- [Filstruktur](#filstruktur)
- [Encoding-referens](#encoding-referens)
- [Vad som klassificeras som firmware-konstanter](#vad-som-klassificeras-som-firmware-konstanter)
- [Vad som inte är kartlagt ännu](#vad-som-inte-är-kartlagt-ännu)
- [Save Counter / Noise-bytes](#save-counter--noise-bytes)

---

## Metodik

YSFC-binärformatet (`.Y2L`, `.Y2U`) är inte officiellt dokumenterat av Yamaha. Varje parameter-offset i detta projekt har upptäckts genom binär differentialanalys:

1. Exportera en baseline-performance från MODX M-hårdvara eller ESP-pluginet (typiskt en avskalad "Init Voice" med en part)
2. Ändra exakt en parameter via UI
3. Exportera den modifierade filen
4. Jämför de två filerna byte-för-byte (efter filtrering av save-counter-brus)
5. Notera offset, encoding-typ och värdeintervall
6. Kors-verifiera över alla engine-typer för att skilja user-fält från firmware-konstanter

Denna metod har applicerats iterativt över **2010+ verifierade testfiler** för att nå nuvarande engine-täckning.

### Korpus-analys (avancerad metod)

För engines med stora testkorpor används en kraftfullare metod:

1. **Skanna alla testfiler efter byte-position-konstans** — bytes som är 100% konstanta över alla testfiler är firmware-konstanter ([INTERN])
2. **Identifiera varierande bytes** — dessa är UI-fält; matcha varje en mot den specifika testfilen som ändrade den
3. **Stride-mönsterigenkänning** — när flera varierande bytes delar en stride (t.ex. 123 bytes för FM-X-operatorer) är de del av en repeterande struktur

Denna korpus-metod möjliggjorde den slutliga kartläggningen av AN-X (50 fält identifierade i två sessioner) och FM-X (44 fält + 5-byte per-OP-gap).

### Verifieringsnivåer

Varje dokumenterat fält har ett stjärnbetyg:

- **★★★★★** — Binärverifierat med en eller flera testfiler (direkt A/B-diff-bevis)
- **★★★★☆** — Härlett från officiell källdata, högt förtroende
- **★★★☆☆** — Sannolikt korrekt, ej binärverifierat
- **★★☆☆☆** — Osäkert
- **[INTERN]** — MODX-intern firmware-konstant, ej user-editable
- **[STRUKT]** — Strukturellt identifierat, ingen UI-mappning ännu

---

## Testkorpus

Reverse-engineering-arbetet grundas på **2010+ binärverifierade testfiler** som genererats genom systematiska parameterändringar på riktig MODX M-hårdvara. Varje dokumenterad offset backas upp av minst en A/B-binär-diff.

| Engine | Filer | Andel |
|---|---:|---:|
| AN-X | 799 | 40% |
| FM-X | 425 | 21% |
| AWM2 | 408 | 20% |
| Drum | 84 | 4% |
| Övriga / multi-part | 294 | 15% |

---

## Engine-täckning

Alla fyra engines har **varje känt användarredigerbart parameterfält binärverifierat** genom A/B-diffanalys över de 2010+ testexporterna.

| Engine | UI-fält | [INTERN]-bytes | Status |
|---|---:|---:|---|
| AWM2 | 128 | 8 | ✅ Verifierad |
| AN-X | 171 | 458 | ✅ Verifierad |
| FM-X | 141 | 863 | ✅ Verifierad |
| Drum | 54 | 4934 | ✅ Verifierad |

### Anmärkningar per engine

**AWM2** — Sample-baserad engine med 8 element per part. Stride 313 bytes per element. Element 1 base = audit 12469. Per-element-fält inkluderar Waveform Number, AEG, PEG, EQ, Pan, Velocity Limits och Level Scaling.

**AN-X** — Analog modelling-engine med 3 OSC, 2 Filter, WaveFolder, Mod EG/LFO. 684 engine-pool-bytes, varav 458 är firmware-konstanter ([INTERN]) och 171 är direkta UI-fält (resten är routing-matriser).

**FM-X** — FM-syntes-engine med 8 operatorer, stride 123 bytes per OP. OP1 base = audit 12676. Inkluderar PEG, FEG, Filter, Algorithm, Feedback och 2nd LFO modulation-matriser.

**Drum** — Drum kit-engine med 73 drum keys (stride 68 bytes per key). Drum använder en annan filoffset-konvention: `filoffset = audit + 669` (vs +687 för AWM2/AN-X/FM-X). Alla 27 DRUM_KEY-fält binärverifierade.

### Bortom engines

Verifieringen ovan gäller de fyra synthesengines:arnas användarredigerbara parameterfält. Filnivåstrukturer utanför engines spåras separat:

| Struktur | Status |
|---|---|
| Multi/GM 16-part-container | ✅ Kartlagd |
| Insertion FX / Motion Sequencer / Arp / Control Assign | ✅ Kartlagd (se [Täckning per sektion](#täckning-per-sektion)) |
| Scene-snapshots | ⚠️ Struktur verifierad, ~10 fält/scen UI-bekräftade — se [Vad som inte är kartlagt ännu](#vad-som-inte-är-kartlagt-ännu) |
| Smart Morph-interpolationstabeller | ⚠️ Inte kartlagda än — se [Vad som inte är kartlagt ännu](#vad-som-inte-är-kartlagt-ännu) |
| FM-X 2nd LFO depth-matris | ⚠️ Partiell mappning — se [Vad som inte är kartlagt ännu](#vad-som-inte-är-kartlagt-ännu) |

---

## Täckning per sektion

### FM-X

| Sektion | Fält | Täckning | Notering |
|---|---:|---|---|
| Operatorer (8 × 22 fält) | 176 | ✅ Verifierad | OP1@12676, stride 123 bytes |
| Pre-OP (PEG, LFO, Algo, Filter) | 23 | ✅ Verifierad | |
| Part Common | 15 | ✅ Verifierad | Algorithm, Feedback, Filter, FM Color, Volume |
| Per-OP 2nd LFO-modulation | 16 | ✅ Verifierad | rel +58 (PitchMod), rel +60 (AmpMod) per OP |

### AWM2

| Sektion | Täckning | Notering |
|---|---|---|
| Element (8 × 124 fält = 992 positioner) | Verifierad (UI) | E1@12469, stride 313 bytes |
| PEG-block (rel +163..+195) | ✅ Verifierad | |
| FEG-block (rel +219..+241) | ✅ Verifierad | |
| EQ-block (rel +271..+281) | ✅ Verifierad | 2-band + P.EQ + Boost-lägen |
| LFO + LFO Element Matrix | ✅ Verifierad | Phase Offset + 3 Depth Ratios per element |
| Level Scaling (AMP + Filter) | ✅ Verifierad | 5 BreakPoints + 4 Offsets vardera |

### AN-X

| Sektion | Täckning | Notering |
|---|---|---|
| Oscillatorer (3 × 26 fält) | ✅ Verifierad | OSC1@12631, OSC2@12756, OSC3@12881 (stride 125) |
| Part Settings | ✅ Verifierad | Unison, OSC Reset, Voltage Drift, Ageing |
| Pitch LFO | ✅ Verifierad | Wave, Speed, Phase (16-step enum), Delay, FadeIn |
| Filter LFO | ✅ Verifierad | Wave, Speed, Phase, Delay, FadeIn, Depth F1/F2 |
| Amp + Amp LFO | ✅ Verifierad | Level, Vel, Key, Drive + full LFO |
| Filter 1 + Filter 2 | ✅ Verifierad | 12+13 fält vardera |
| WaveFolder + Mod EG + Mod LFO | ✅ Verifierad | Mod LFO har 5 fält |
| Mod LFO extras | ✅ Verifierad | Tempo Sync, Hold, Fade Out, Random Speed, Loop |
| AEG Offset-block | ✅ Verifierad | Part Common rel +148/150/152/154 |
| Filter Offset | ✅ Verifierad | Part Common rel +164/166/168 |
| Mod LFO Destination Matrix | ✅ Verifierad | Delas med AWM2 |
| Routing-matriser (5 × 40 bytes) | [INTERN][STRUKT] | Ej UI-editable, preserveras som-de-är |

### Drum

| Sektion | Täckning | Notering |
|---|---|---|
| Drum Key (per key × 73 keys) | ✅ Verifierad | 27 fält per key, stride 68 |
| Drum Part Common | ✅ Verifierad | 27 fält inklusive Filter AEG (audit 6849-6855) |
| Filter AEG (Part-level) | ✅ Verifierad | drumPartFilterAegAttack/Decay/Sustain/Release |

### Cross-engine-sektioner

| Sektion | Täckning | Notering |
|---|---|---|
| Insertion FX | ✅ Verifierad | 57 verifierade FX-typer; Part Common +232 routing: 0=Parallel, 1=A→B, 2=B→A |
| Motion Sequencer (4 lanes × 884 bytes) | ✅ Verifierad | 116 fält |
| Arp Common | ✅ Verifierad | 34 fält |
| Common Control Assign (32 slots × 22 bytes) | ✅ Verifierad | abs 2452..3155 |
| Part Control Assign (8 slots × 22 bytes) | ✅ Verifierad | Part rel +1520..+1695 |
| Part After Touch (4 slots × 16 bytes) | ✅ Verifierad | Part rel +600..+663 |
| SuperKnob Assign Positions | ✅ Verifierad | 8 knobs × 6 bytes u16le vid abs 674 |
| Assign Knob Names | ✅ Verifierad | 8 × 21 bytes ASCII vid abs 8049 |
| Receive Switch per Part | ✅ Verifierad | Identisk över alla 4 engines |
| Master EQ 5-band | ✅ Verifierad | abs 560-592 |
| Audio In Routing | ✅ Verifierad | inkl. Envelope Follower |
| Performance Common | ✅ Verifierad | Volume, Pan, Tempo, etc. |
| Part Common (Pitch Bend, Portamento, EQ, FX) | ✅ Kärna verifierad | Merparten binärverifierad; ett fåtal sällan använda fält strukturellt kartlagda, ännu ej A/B-bekräftade |

---

## Viktiga fynd

### Filformat

- `Y2L` och `Y2U` är byte-för-byte identiska — bara filändelsen ändrar hur ESP presenterar import-dialogen
- Performance-namn: börjar vid byte `perf[4]`, null-terminerat, max ~16 tecken printable ASCII
- Scene count: `perf[6695]`, intervall 1–8
- Engine-typ-byte: `perf[6700]`, värden 0=AWM2, 1=Drum, 2=FMX, 3=ANX
- Common-blob-storlek är 6701 bytes
- Part Common-stride är 5765 bytes

### Engine-pool-layout

- AWM2 engine-pool: 3 header-bytes + 8 element × 313 byte stride (E1@12469)
- AN-X engine-pool: 3 OSC × 124 byte stride (OSC1@12631, OSC2@12755, OSC3@12880)
- FM-X engine-pool: 8 OP × 123 byte stride (OP1@12676 ... OP8@13537)
- Drum engine-pool: 73 keys × 68 byte stride (Key 1 audit @ 12469)

### Adresseringskonventioner

- AWM2/AN-X/FM-X: `filoffset = audit + 687`
- Drum: `filoffset = audit + 669` (annan konvention)

### Multi-part / Multi/GM

- Pointer-baserad sub-blob-detection: `SUBBLOB_POINTER_REL = (5763, 5764)`
- Engine magic bytes: AWM2=8, ANX=110, FMX=82, Drum=73
- Multi/GM-filer (16 parts: 15 AWM2 + 1 Drum på Part 10) använder samma multi-part-arkitektur

### Noterbara encoding-detaljer

- AN-X PitchEGDepth encoding: `raw = round(UI_cent × 247/4800) + 247`, intervall ±4800 cents
- AN-X Filter FEGDepth: `raw = round(UI/50) + 256`, intervall ±12700 cents
- FM-X Algorithm: `raw = algo − 1`
- PEG Center Key för AWM2-element ligger vid rel +159
- Common Scene-block: 8 scener × 71 bytes vid abs **1710**
- Per-Part Scene-block: 8 scener × 84 bytes vid Part rel +682

---

## Filstruktur

### Chunk-layout

Alla YSFC-filer innehåller 6 chunks i denna ordning:

```
EPFM @ offset 64   — Performance-metadata
ESYS @ offset N    — System-data
EFVT @ offset N    — Favorite-data
DPFM @ offset N    — Performance-data (huvudpayload)
DSYS @ offset N    — System-tabeller
DFVT @ offset N    — Favorite-tabeller
```

### DPFM intern struktur

DPFM-chunken innehåller ett enda `Data`-block med performance-payloaden:

```
Sub-blob 1: Performance Common         (6701 bytes)
Sub-blob 2: Part 1 Common              (5765 bytes)
Sub-blob 3: Part 2 Common              (5765 bytes)
...
Sub-blob N+1: Part N Common            (5765 bytes)
Engine pool                            (variabel storlek, beror på engine-mix)
```

### Multi/GM 16-part-arkitektur

```
Performance Common              6701 bytes
16 × Part Common               92240 bytes (5765 × 16)
Engine pool                    42583 bytes (15 × AWM2_stride + 1 × Drum_stride)
DPFM total                    141536 bytes
```

---

## Encoding-referens

| Typ | Formel |
|---|---|
| direct u8 | `raw = value` |
| center=64 | `raw = value + 64` |
| center=128 | `raw = value + 128` |
| AN-X PulseWidth | `raw = round(pct × 256/100)` |
| AN-X SelfSyncPitch | `raw = round(UI/25) + 256` |
| AN-X Filter FEGDepth | `raw = round(UI/50) + 256`, intervall ±12700 cents |
| AN-X PitchEGDepth | `raw = round(UI_cent × 247/4800) + 247`, intervall ±4800 cents |
| AN-X Assign / SuperKnob value | u16 little-endian, default=512 |
| SuperKnob Assign-positioner | u16 little-endian, Left=0/Mid=512/Right=1023 |
| FM-X algorithm | `raw = algo − 1` |
| FM-X OP detune | `raw = value + 15` |
| InsA/B TypeIndex | `lo = idx & 0x7F`, `hi = (idx >> 7) & 0x7F` |
| Waveform-nummer | u16 little-endian, 1-baserat |
| Note MIDI-värde | u8, 0=C-2, 60=C3, 127=G8 |

---

## Vad som klassificeras som firmware-konstanter

Följande regioner är strukturellt kartlagda men verifierat **identiska över alla engine-typer** (AWM2 / AN-X / FM-X), vilket betyder att de är firmware-uppslagstabeller snarare än user-parametrar:

| Region | Storlek | Sannolikt syfte |
|---|---:|---|
| Common abs 357-394 | 38 bytes | Arp Common firmware-konstanter (inkluderar Sync Quantize @ 360) |
| Common abs 487-524 | 38 bytes | AN-X Pitch checksum (abs 488 ändras vid alla AN-X Pitch-edits) |
| Common abs 732-764 | 33 bytes | SmartMorph FM-X-data |
| Common abs 851-1680 | 830 bytes | 8 × 106-byte firmware-uppslagstabeller (16 c64-noder per block) — sannolikt velocity/aftertouch-kurvor |

Dessa bekräftades som firmware-konstanter genom byte-diff av Init Voice-baseline för alla tre engine-typer — bytena är identiska, så de kan inte vara user-parametrar knutna till en specifik engine.

### Drum [INTERN]-bytes

Inom drum keys (68 bytes × 73 keys = 4964 bytes) är 4934 bytes (99,4%) firmware-konstanter. Specifikt:

- Per drum key: 33 nollpaddade byte-positioner (rel +1, +2, +3, +5, +7, +9, +13, +15, +17, +19, +20, +21, +23, +24, +25, +27, +29, +31, +33, +35, +37, +39, +41, +43, +47, +49, +53, +54, +55, +57, +59, +61, +63)
- Per drum key: rel +18 (värde 90), rel +67 (värde 64) — konstanta icke-noll firmware-värden

---

## Vad som inte är kartlagt ännu

### Scene-parameter-snapshots

Scene-strukturen är verifierad (8 × 71 bytes Common vid abs 1710, 8 × 84 bytes per Part vid rel +682) men endast ~10 fält per scen har UI-bekräftade mappningar. Resterande bytes per scen är del av snapshot-mekanismen men specifik fält-nivå-mappning är ofullständig.

### Smart Morph

Interpolationstabellerna och FM-X morphing-state är ej kartlagda.

### FM-X 2nd LFO depth-matris

Partiell mappning vid `abs=12547+`. Behöver fler testfiler.

### Performance Editor-verktyg (UI-lucka)

Medan binärformatet är kartlagt (alla kända parametrar verifierade) exponerar Performance Editor-UI inte alla parametrar ännu:

- Multi-part-performances — endast Part 1:s engine visas för närvarande
- Drum parameter-editor — struktur kartlagd, UI ej byggt ännu
- Undo/redo-funktionalitet ej implementerad ännu

---

## Save Counter / Noise-bytes

Följande bytes ändras vid varje spar oavsett parameter-edits (timestamps, interna counters):

```
abs 22-24, 60-63, 66, 232, 234, 358, 376, 396-399, 488, 654,
abs 6715-6716, 6721, 6724-6725, 7167-7168, 7419
```

För Drum-specifik testning, lägg även till:

```
filoffset 680-720, 7380-7400
```

Dessa bytes filtreras bort från diff-analys för att undvika falska positiva.

---

## Vidare läsning

- [`YSFC_FORGE_REFERENCE_sv.md`](YSFC_FORGE_REFERENCE_sv.md) — Kompakt referensmanual med alla fält-positioner
- [`YSFC_FORGE_FULL_CONTEXT_sv.md`](YSFC_FORGE_FULL_CONTEXT_sv.md) — Fullständig teknisk dokumentation med test-bevis
- [`../serializer/ysfc_serializer.py`](../serializer/ysfc_serializer.py) — Python parameter-konstanter
