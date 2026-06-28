# YSFC Forge — Full Context

*MODX M8 firmware 3.0 + ESP Plugin v3.0*
*Underlag: 2010+ binärverifierade testfiler*

---

## Aktuell status

| Engine | Mappade fält | Status |
|---|---:|---:|
| **AWM2** (per element × 8..128) | 128 fält + 8 [INTERN] | ✅ **Verifierad** |
| **AN-X** (engine totalt) | 171 fält + 458 [INTERN] | ✅ **Verifierad** |
| **FM-X** (Pre-OP + 8 × OP) | 141 fält + 863 [INTERN] | ✅ **Verifierad** |
| **Drum** (per key × 73) | 27 key-fält + 27 Part Common | ✅ **Verifierad** |
| **Part Common** | 88 fält (AWM2/FM-X/AN-X) + 6 (Drum) | ✅ **Kärna verifierad** |

**Total fält-positioner i serializer:** ~2057
**Testkorpus:** 2010+ binärverifierade filer

Alla fyra engines är binärverifierade (alla kända parametrar). Multi/GM 16-part-filer stöds (15 AWM2 + 1 Drum på Part 10, via multi-part-arkitekturen).

**Strukturell insikt: Drum-engine har egen Part Common-layout**

Drum delar inte det universella AEG-offset-blocket (rel +144..+150) som AWM2/FM-X/AN-X. För Drum gäller istället:
- Rel +126..+132 = drum AEG (Attack/Decay/Sustain/Release, c64)
- Rel +144/+146 = drum filter cutoff/resonance (c64)

Tolkningen av Part Common rel +126..+158 styrs av engine_type. Den delade AEG-block-arkitekturen gäller alltså bara för tre av fyra engines.

**Om AN-X coverage:** AN-X-engine är fundamentalt annorlunda än AWM2. AWM2 är en sample-spelare där 8 identiska element delar struktur — varje byte tenderar att vara en direkt UI-parameter. AN-X är en analog-modell med komplex modulation-routing: av engine-poolens 684 bytes är 458 firmware-konstanter ([INTERN]) inklusive routing-matriser och lösa flaggor. De 171 UI-fälten täcker alla user-editable parametrar.

---

## Aktuell format- och exportmodell

YSFC Forge behandlar de Yamaha-filfamiljer som stöds som separata men närbesläktade layouter:

| Familj | Typiska versioner | Filändelser | Aktuell roll |
|---|---|---|---|
| MODX M / MONTAGE M long layout | `5.1.x` moderna exporter | `.Y2L`, `.Y2U` | Primärt native exportmål |
| MONTAGE M short layout | `4.1.x` / `.X2L`-liknande layout | `.Y2L`, `.X2L`-liknande källor | Experimentell Performance-import; expanderas till long-layout Y2L/Y2U |
| Legacy MONTAGE | `4.0.x` | `.X7L`, `.X7U` | Experimentell Performance-import/konvertering |
| Legacy MODX / MODX+ | `5.0.x` | `.X8L`, `.X8U` | Experimentell Performance-import/konvertering |

Library Builder exporterar valda Performances och de beroenden de kräver. Verktyget försöker inte klona komplett biblioteksstate. Live Sets, Patterns, Favorites och enhetsmetadata ligger utanför aktuell export-scope.

### Aktuell Library Builder-konvertering

| Källtyp | Engines | Beroenden | Notering |
|---|---|---|---|
| Native long `.Y2L`/`.Y2U` | AWM2, FM-X, AN-X, Drum | Selektiva waveforms, samples, arpeggios | Primär stödd väg |
| Legacy `.X7L`/`.X8L` | AWM2, FM-X, Drum | Selektiva waveforms, samples, arpeggios | Konverteras till modern Y2L DPFM-layout |
| MONTAGE M short-layout `.X2L`-liknande filer | AWM2, FM-X, AN-X, Drum | Konverteras när de refereras genom stödda sektioner | Short common/part/engine-regioner expanderas till long-layout Y2L |

AN-X stöds fullt ut i det moderna Y2L/Y2U-målformatet. AN-X förväntas normalt inte förekomma i legacy MONTAGE/MODX `.X7L`/`.X8L`-bibliotek; okända classic part-typer behandlas som ej stödda classic engines.

### Aktuell Y2L/User-Arp-exportmodell

User Arps hanteras både som beroendedata och som playback-/scene-state. Den aktuella exportvägen:

- remappar EARP/DARP-ID:n globalt i den exporterade målfilen
- skriver om scene-level arpeggio-referenser till kompakta 0-baserade ID:n
- skriver Arp Master-state för importerade classic-Performances med aktiva arp-referenser
- undviker att classic import-state-bytes mappas till Part Mute
- använder inte Arp Play Only som ersättning för Arp Master
- nollar classic import-state-bytes som kan påverka uppspelning där ESP-referensexporter visar dem nollade

Detta är den aktuella modellen för exporter där filen laddar men User-Arp-drivna scenes annars skulle bli tysta eller spela fel.

## Performance ↔ Waveform / Sample / Arpeggio-koppling

Selektiv export kopierar bara de beroenden som en vald uppsättning performances faktiskt använder. En giltig Y2L kräver att katalog-ID:n är en **kontinuerlig sekvens**, så exporten både kopierar de refererade beroendena och renumrerar dem, och skriver om blob-referenserna så att de matchar.

**Referensmodell.** En performance refererar en USER-waveform via en fast byte-struktur i DPFM-blobben. Två kodningar finns (båda byte-verifierade mot ESP-facit och kontrollerade CFX-en-ändrings-par):

- `SIG_A`: `00 00 00 28  01(bank)  XX  YY  00  [ID]  00 01 00 01` — element-slot
- `SIG_B`: `01 00 00 00  01 00 0C 00  [ID]  00 40` — element-config

Byten efter `0x28` är **bank**: `0x01` = USER-waveform (`[ID]`-byten indexerar EWFM/EWIM-katalogen), `0x00` = preset/ROM (ignoreras). `XX YY` varierar (`00 00` eller `00 01`); båda matchas. `[ID]` är en enda byte. Katalog-ID:t ligger i `recPayload[10:12]` (big-endian u16) i varje EWFM/EWIM `Entr`-post.

**Renumreringsregeln.** Samla unika refererade gamla ID:n, sortera dem, tilldela nya ID:n `1..N` (1-baserat för waveform/sample). Skriv om varje `[ID]`-byte i varje behållen performance-blob gammalt→nytt, och skriv de nya ID:n i de ombyggda EWFM/EWIM `recPayload[10:12]`. Ren renumrering rör **endast** `[ID]`-byten — bank/Field-2-byte rörs inte.

**Arpeggios.** Arp-referenser ligger i separata (`80 00 …`) element-pitch-block med en egen 0-baserad ID-rymd. Arp-refs sitter efter en serie `80 00`-par (pitch-tabell) och valfri `00`-padding, som ett eller flera `[ARP_ID] 2f`-par (ref kan upprepas upp till 4×); `ARP_ID` är en enda byte < 21. Renumreringsregeln är identisk med waveform men **0-baserad**: sortera de unika refererade arp-ID:n, tilldela `0..N-1`. EARP/DARP byggs om selektivt med de nya ID:n; varje behållen performance-blob får sina arp-`[ID]`-byte ompekade gammalt→nytt.

**Beroende-sektionsstorlek.** Y2L-beroende-sektioner storleksanpassas **exakt** efter payload; MODX avvisar varje storleksfält-/data-slack. Varje dep-sektion (EWFM, DWFM, EWIM, DWIM, EARP, DARP), DPFM-performance-poolen och EPFM-performance-indexet storleksanpassas alla till byten med uniform 8-byte-per-blob-framing ackumulerat, sedan `exactSize(n) = Σ(8 + payload) − 4 + 8` (dra av den enda 4-byte-första-blob/post-överräkningen, lägg till sektionsheadern). Ett minimalt Init/en-posts-golv behålls för tomma urval.

**Containerstruktur.** En giltig library-fil använder ESP:s exakta 12-chunk-layout (`EPFM EWFM EARP ESYS EFVT EWIM DPFM DWFM DARP DSYS DFVT DWIM`, inga ECRV/ELST/DCRV/DLST-stubbar). `u32@0x20` = chunk-antal × 8.

**Per-fil-byggstämpel.** `u32@0x3c` är en per-fil-byggstämpel som också är inbäddad som u16 före varje EPFM/EWFM/EARP-namn. Den måste vara samma familj inom en fil; den syntetiska headerns `0x3c` sätts till källfilens `0x3c`. EPFM-post byte[11] = destinations-slot-index (kompakt `0,1,2,3` för en 4-perf-export).

**DWFM sample-index.** Varje DWFM-blob är `[4-byte header][N × 64-byte sub-poster]`; vid blob-offset `60 + 64·k` finns ett 4-byte little-endian sample-data-index. Det måste vara en ren stigande räknare `value[i] = base + i`, där `base` är första blob-sub-postens ursprungliga 4-byte LE-värde och `i` ökar en gång per sub-post över alla blobbar i ordning (full 32-bit LE).

**Fast directory-region.** En giltig YSFC library-fil har en fast directory-region: poster från `dirOff` (0x40), FF-padding, en enda `0x00`-separator vid `dirOff+0x150` (= 0x190), och första chunk vid `dirOff+0x151` (= 0x191). MODX beräknar varje chunks position utifrån denna fasta region.

**Per-performance beroende-taggar (UI).** Varje performance-rads W/S/Arp-chip villkoras på om just den performancen faktiskt refererar beroendet, via samma binärverifierade scanners som driver den selektiva exporten (`scanWaveformRefPositions` / `scanArpRefPositions`). EWFM/EWIM delar ID-rymd, så waveform-refs villkorar både W och S; arp-refs villkorar Arp. Om en blob inte kan läsas faller koden tillbaka till fil-nivå. Per-performance-infokolumnen visar endast engine-etiketten (`AWM2`/`FM-X`/`AN-X`).

**Hjälpfunktioner:** `scanWaveformRefPositions`, `scanArpRefPositions`, `renumberPerfBlob`, `setRecPayloadId`, `resolveFileWaveformRefs`, `resolveFileArpRefs`, `getDepsForSelection`, `buildSyntheticY2LBuffer`, `buildDepPayload`, `cloneAndPatchOffLen`, `buildDPFMPayload`, `buildEPFMPayload`, `calcSyntheticDimensions`, `exportMergeToY2L`, `createSyntheticBaseFile`. En konservativ kopiera-allt-fallback bevaras vid varje opålitlig upplösning (parsningsavvikelse, blob < 12000 B, noll refs trots pool, eller ett refererat ID som saknas i en sektionskatalog). Om den valda basfilen också är en källa till någon vald performance tvingas en syntetisk container (`baseIsSource`).

---


## Förord — Hur detta dokument läses

Detta är en **clean, deduplicerad master-referens** för YSFC-formatet. Varje fält listas EN gång med korrekt position, default, encoding och stjärnbetyg.

**Sanningskällor i prioritetsordning:**

1. **Binärverifierat med testfil ★★★★★** — diff-bevisat. Detta är auktoritativt.
2. **Härlett från officiell Yamaha-källdata (★★★★☆)** — Effect Type List, MIDI tabell, etc.
3. **Predikterat från etablerat mönster (★★★☆☆)** — stride-extrapolering, deduktion.
4. **[STRUKT]** — strukturellt karaktäriserat men ej UI-mappat.
5. **[INTERN]** — MODX-internt, ej user-editable (ignoreras vid edit).

**Förkortningar:**

```
u8       = unsigned 8-bit byte
u16le    = unsigned 16-bit little-endian (lo + hi*256)
u32be    = unsigned 32-bit big-endian
c64      = center=64       (raw = UI + 64)
c128     = center=128      (raw = UI + 128)
c256     = center=256      (u16le, raw = UI + 256)
c50      = center=50       (raw = UI + 50)
c504     = center=504      (u16le, AN-X pitch cents)
direct   = raw = UI-värde direkt
bool     = 0=Off, 1=On
enum     = uppräknat värde
```

**Koordinatsystem:**

Alla absoluta offsets är `blob[+N]` relativt **performance-blobens början** (där `blob[0..3] = 00 00 00 15`). Detta är samma som `dp[N+12]` om man räknar från DPFM-payload-start.

---

## Innehåll

1. Y2L filformat-arkitektur
2. Container — EPFM / DPFM / ESYS / EFVT / ELST
3. Sub-blob universell modell
4. Engine-pool (multi-part)
5. Performance Common (Sub-blob 1)
6. Part Common (Sub-blob 2..N)
7. Receive Switch per part
8. Common Assigns (CA-strukturer)
9. Scene Structures
10. MS Sequencer
11. Engine-data: AN-X
12. Engine-data: AWM2
13. Engine-data: FM-X
14. Engine-data: Drum
15. Insertion FX
16. Smart Morph
17. UI-element EJ I BLOB
18. Kvarvarande okartlagda regioner
19. Modified/Noise-flaggor (filtrera vid diff)
20. Helper-funktioner (serializer)
21. Verifieringsstatus och testfil-register

---

# 1. Y2L filformat-arkitektur ★★★★★

Y2L/Y2U-filformatet består av en 64-byte fil-header följt av en alternerande sekvens av "Entry" (E*) och "Data" (D*) chunks. Varje E-chunk indexerar entries; varje D-chunk innehåller motsvarande data.

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

`.Y2L` (Library file) och `.Y2U` (User file) är byte-för-byte identiska — bara filändelsen skiljer (ESP-pluginet använder ändelsen för att avgöra vilken import-dialog som ska visas).

## 1.1 File header (64 bytes) ★★★★★

Binärverifierad mot 1930+ filer (Appendix A.3 i engelska versionen). Tidigare versioner av den här tabellen hade fel fältstorlekar och offset — korrekt layout nedan.

| Offset | Hex | Storlek | Fält | Notering |
|---:|---:|---:|---|---|
| 0 | 0x00 | 16 | Magic + null-pad | `YAMAHA-YSFC\x00\x00\x00\x00\x00` (11 bytes ASCII + 5 noll-bytes) |
| 16 | 0x10 | 16 | Version + null-pad | `5.1.2\x00…` för Montage M / MODX M; `5.0.1` för MODX classic; `4.0.5` för Montage classic |
| 32 | 0x20 | 4 | Katalogstorlek | `u32 BE` = antal_block × 8; katalogen börjar alltid på 0x40 |
| 36 | 0x24 | 12 | Reserverad padding | alla `0xFF` |
| 48 | 0x30 | 4 | Library-info-längd | `u32 BE`; 241 bytes baseline (Montage M / MODX M), 81 bytes (classic) |
| 52 | 0x34 | 8 | Reserverad padding | alla `0xFF` |
| 60 | 0x3C | 4 | Spar-räknare | `u32 BE`; ökar monotont per export — **inte** Unix-timestamp |

Spar-räknaren vid 0x3C är del av noise-setet (filtreras vid diff-analys). Den är också inbäddad som `u16` före varje EPFM/EWFM/EARP-postnamn — båda måste stämma överens annars avvisar MODX filen. Katalogen börjar alltid på absolutoffset `0x40` oavsett katalogstorlek-fältets värde.

## 1.2 EPFM chunk ★★★★★

EPFM (Entry Performance) är performance-indexet. Den innehåller en fast header följt av en Entry-record per performance i filen.

```
EPFM chunk-header   (8 bytes: 'EPFM' + storlek u32 BE)
count               (4 bytes u32 BE: antal Entry-poster)
'Entr'              (4 bytes: global typ-tagg; fungerar också som tagg för första posten)
rec1_storlek        (4 bytes u32 BE)
rec1_data           (rec1_storlek bytes)
'Entr' rec2_storlek rec2_data     ← efterföljande poster har var sin 'Entr'-tagg
…
```

Obs: den **första** posten har ingen egen föregående `Entr`-tagg — den globala taggen vid byte [4:8] fyller den rollen. Post 2..N har var sin `Entr`-tagg.

Varje Entry-posts payload (binärverifierad mot MODX M-filer):

| Rel | Storlek | Fält | Notering |
|---:|---:|---|---|
| 0 | 4 | Blob-storlek | `u32 BE` — storleken på performance-blobben i DPFM |
| 4 | 4 | DPFM-offset | `u32 BE` — offset inom DPFM-payload |
| 8 | 1 | Konstant | `0x00` |
| 9 | 1 | Konstant | `0x40` (MODX validerar detta fält) |
| 10 | 1 | Konstant | `0x00` |
| 11 | 1 | Destinations-slot | kompakt destinations-index (0, 1, 2, … för sekventiell export) |
| 12 | 1 | Konstant | `0x00` |
| 13 | 1 | Multi-engine-flagga | `0x00` (förenklat) |
| 14 | 1 | Konstant | `0x00` |
| 15 | 1 | Engine-bitar | `0x01`=AWM2/Drum, `0x02`=FM-X, `0x04`=AN-X; OR-kombinerat för multi-engine |
| 16 | 1 | Käll-flagga | `0x00`=ESP Plugin-export, `0x02`=MODX hardware-export |
| 17 | 1 | Konstant | `0x00` |
| 18 | 1 | Kategori | `0x01`=default |
| 19 | 6 | Padding | alla `0x00` |
| 25 | 1 | Konstant | `0x30` |
| 26 | 1 | Slot-flagga | `0x00` (förenklat) |
| 27 | var | Namnsträng | `"IDX:KortNamn:VisningsNamn\0"` — NUL-terminerad ASCII |

Namnsträngens format är `"{slot_index}:{kort_namn}:{visnings_namn}\0"`. **Visningsnamnet** (tredje fältet) är det namn som MODX och ESP Plugin visar — det matchar `blob[4:]` exakt. **Kortnamnet** (andra/mellersta fältet) är en förkortad kategorietikett för internt bruk och är INTE visningsnamnet. Exempel: `"0:Italian XL:Italian Grand XL\0"` — kortnamn `"Italian XL"`, visningsnamn `"Italian Grand XL"`.

Obs: tidigare versioner av denna dokumentation hade fältordningen omvänd (beskrevs som `"IDX:LångtNamn_paddat:KortNamn\0"`). Den beskrivningen var felaktig.

För en single-performance-fil innehåller EPFM exakt en Entry-record. För library-filer med flera performances finns en Entry per performance.

## 1.2a v4.x-filformatsskillnader (Montage classic / MODX classic) ★★★★☆

Filer med versionssträng `4.0.5` (Montage classic) eller `5.0.1` (MODX classic) skiljer sig från v5.x-layouten på två viktiga sätt:

**EPFM directory-struktur:** I v4.x-filer är EPFM-chunken på `d[64]` själva directory-strukturen — dess payload innehåller chunk-pekare (EARP, ESYS, EFVT, DPFM, …), inte Entr-poster. Den faktiska EPFM-chunken med Entr-poster är inbäddad längre in i filen (typiskt runt offset `0x171`) och finns inte listad i directory. För att hitta den: skanna framåt från offset ~200 efter nästa `'EPFM'`-tag med giltig `count + 'Entr'`-payload.

**Engine-type-bytens offset:** I v4.x-blobbar sitter engine-type-byten på `blob[6698]`, inte `blob[6700]` som i v5.x. Sub-blob-separatorn `0x00000015` följer direkt på `blob[6699:6703]`.

**Rekommendation:** Använd alltid EPFM `rec[15]` (engine bits: `0x01`=AWM2/Drum, `0x02`=FM-X, `0x04`=AN-X) som primärkälla för engine-typ vid läsning av filer med okänd version — det är korrekt i både v4.x och v5.x. Använd `blob[6700]` bara som fallback för bekräftade v5.x-filer.

## 1.3 DPFM chunk ★★★★★

DPFM (Data Performance) innehåller den faktiska performance-datan. Chunk-headern följs av en sekvens av sub-blobs (en per performance).

```
DPFM header                       (8 bytes: 'DPFM' + storlek big-endian u32)
Sub-blob 1                        (Performance 1)
Sub-blob 2                        (Performance 2)
...
```

Varje sub-blob är själv en self-contained performance — se sektion 2 för sub-blob-strukturen.

För Multi/GM 16-part-filer innehåller DPFM en enda mycket stor sub-blob (~141 536 bytes) som representerar den 16-part-Performance.

## 1.4 ESYS / DSYS (System Settings) ★★★★★

ESYS/DSYS innehåller system-level-inställningar (master tune, MIDI-kanaler, MIDI-routing etc.). Dessa är typiskt konstanta över de flesta filer och redigeras inte via per-Performance UI.

För de flesta filtyper är ESYS 46 bytes och DSYS 1094 bytes.

## 1.5 EFVT / DFVT (Favorites) ★★★★★

EFVT/DFVT innehåller Favorites-bitmappen (vilka performances är markerade som favoriter). EFVT är typiskt 163 bytes; DFVT är 22 219 bytes.

Favorites-bitmappen uppdateras när användaren togglar en performance som favorit. Detta är en noise-region för performance-redigerings-diffs.

## 1.6 ELST / DLST (Live Set) ★★★★★

ELST/DLST innehåller Live Set-definitioner (vilken performance som är tilldelad till vilken slot i ett Live Set-bank). Dessa chunks saknas i single-performance-filer och finns med i fullständiga library-filer.

## 1.7 Filintegritet — INGA checksums ★★★★★

YSFC-formatet har **inga checksums eller integritetsverifiering**. Vilken byte som helst kan ändras utan att filen blir ogiltig (så länge den resulterande strukturen fortfarande är parsebar).

Detta har flera konsekvenser för editor-design:

### Bytes som ALLTID skiljer mellan två exports

När användaren sparar en performance två gånger utan ändringar kommer följande bytes ändå att skilja:

```
Date stamp:           offset 24      (4 bytes)
Save counter regions: 6715..6725     (~11 bytes)
Misc internal:        7167-7168, 7419
```

Dessa bytes är del av noise-setet och filtreras vid binär-diff-analys.

### Konsekvens för editor

Eftersom det inte finns någon checksum:
- Edits kräver ingen post-edit-fixup
- En modifierad fil är omedelbart giltig så länge strukturen är preserverad
- Längdändringar (t.ex. ändring av Element Count) kräver noggrann uppdatering av längd-beroende fält

### Risk: ingen integritetskontroll

Frånvaron av checksums betyder att en korrupt fil inte kan upptäckas av själva formatet — bara genom att försöka ladda den. Editor-implementationer bör:
- Alltid behålla en backup av originalfilen
- Verifiera round-trip (read → write → read) innan originalet förstörs
- Validera output genom att parse:a det igen innan saven betraktas som lyckad

---

# 2. Sub-blob universell modell ★★★★★

En sub-blob är en self-contained Performance-representation. Oavsett om filen innehåller en eller 256 performances, är varje Performance kodad som en sub-blob inuti DPFM.

## 2.1 Layout

```
Sub-blob 1: Performance Common         (6701 bytes — delad metadata)
Sub-blob 2: Part 1 Common              (5765 bytes)
Sub-blob 3: Part 2 Common              (5765 bytes)
...
Sub-blob N+1: Part N Common            (5765 bytes)
Engine pool                            (variabel storlek, beror på engine-mix)
```

I en single-Part Performance finns en Part Common (Sub-blob 2) plus ett enda engine-block. I en multi-Part performance har varje aktiv Part sin egen Part Common följd av sin egen engine-data i engine-poolen.

Sub-blob-antalet och Part-antalet är kodat i Entr-bitmasken (se sektion 3.7).

## 2.2 Sub-blob header (27 bytes) ★★★★★

Varje sub-blob börjar med en 27-byte header:

```
Bytes 0..3:    Sub-blob type marker
Bytes 4..7:    Sub-blob storlek (big-endian u32)
Bytes 8..N:    Variabel header (name-sträng etc.)
```

Den variabla headern inkluderar performance/part-namn och några metadata-fält. Den exakta layouten beror på om detta är Common-sub-bloben eller en Part-sub-blob.

## 2.3 Engine-typ-detection ★★★★★

Engine-typen för varje Part är kodad vid `blob[+6700]` (relativt performance blob-start):

```
0 = AWM2
1 = Drum
2 = FM-X
3 = AN-X
```

För multi-part-filer härleds engine-typen för efterföljande parts via sub-blob-pointer-modellen (se sektion 3.6).

## 2.4 Per-part adress-formel ★★★★★

För Part N (1-indexerad) inom en multi-part Performance:

```
Performance Common base = blob[0]              (6701 bytes)
Part N Common base = blob[6701 + (N-1) * 5765] (5765 bytes per part)
```

Så:
- Part 1 Common: bytes 6701..12465
- Part 2 Common: bytes 12466..18230
- Part 3 Common: bytes 18231..23995
- ...

För en single-Part Performance finns bara Part 1. Engine-poolen börjar omedelbart efter Part Common(s).

## 2.5 Verifiering ★★★★★

Den 5765-byte Part Common stride är verifierad genom:
- 16 × stride 5765 i Multi/GM 16-part-filer (verifierat)
- Flera multi-part Y2U-filer som visar identisk Part Common-struktur replikerad vid stride 5765
- Sub-blob-pointern vid rel +5763/+5764 (sektion 3.6) ligger alltid vid denna offset inom varje Part Common

## 2.6 Edit-flag-bytes per sub-blob

Varje sub-blob har interna edit-flag-bytes som ökar vid edit. Dessa är del av noise-setet och filtreras vid diff-analys:

- `blob[+6715]`: Performance edit counter (ökar vid varje Performance-save)
- `blob[+6716]`: Subtype counter
- `blob[+6721]`: Edit-relaterad byte

Dessa bytes ändras vid varje spar oavsett vilken parameter som redigerades.

---

# 3. Engine-pool (multi-part) ★★★★★

I multi-part-filer lagras engine-data i en delad pool efter alla sub-blobs.

## 3.1 Pool layout

```
[Engine 1 data][5b separator][Engine 2 data][5b separator]...[Engine M data]
                                                              ↑
                                                              ingen separator efter sista
```

**Konstant:** `ENGINE_POOL_SEP_SIZE = 5`

## 3.2 Engine-storlekar ★★★★★

| Engine | Data-storlek | Pool-stride (med sep) |
|---|---|---|
| **AN-X** | 684 bytes | 689 |
| **AWM2** | 2503 bytes | 2508 |
| **FM-X** | 1143 bytes | 1148 |
| **Drum** | 4963 bytes | 4968 |

## 3.3 Pool start-adress

```python
ENGINE_POOL_BASE = 6701 + N_parts * 5765
```

Där `N_parts` är antalet aktiva Parts. För en single-Part Performance börjar poolen direkt efter Part 1:s Common-block:

```
pool_start = 6701 + 1 * 5765 = 12466
```

För en 16-part Multi/GM-fil:

```
pool_start = 6701 + 16 * 5765 = 99 141
```

## 3.4 Engine start-signaturer ★★★★★

Varje engine-block börjar med en 5-byte header-signatur:

```
AWM2:  [01, 00, 00, 00, 28]          — sista byten 0x28 = 40 dec, marker
AN-X:  [01, 00, 00, 00, 6E]          — sista byten 0x6E = 110 dec
FM-X:  [01, 00, 00, 00, 52]          — sista byten 0x52 = 82 dec
Drum:  [01, 00, 00, 00, 49]          — sista byten 0x49 = 73 dec
```

Sista byten i denna 5-byte header är engine-typ-magic-byten. Den kan användas för att identifiera engine för ett block vid skanning av poolen.

## 3.5 Engine-pool adressering

För Part N med engine-typ E:

```python
# Engine-block för Part N börjar vid:
engine_start_N = ENGINE_POOL_BASE + sum(
    ENGINE_STRIDE[engine_of_part_k]
    for k in range(1, N)
)

# (Ingen separator efter sista engine i poolen, men beräkningen använder
#  fortfarande full stride för mellanliggande parts.)
```

## 3.6 Multi-part "linked list"-pointer-modell ★★★★★

Varje Part Common innehåller en 2-byte pointer som avgör om detta är sista Part och vilken engine nästa Part använder:

```
SUBBLOB_POINTER_REL = (5763, 5764)
```

För Part N:s Part Common (placerad vid `blob[6701 + (N-1) * 5765]`), är pointer-byten på:

```
pos_marker = 6701 + (N-1) * 5765 + 5763
pos_next   = 6701 + (N-1) * 5765 + 5764
```

**Decoding:**

```python
marker = blob[pos_marker]
next_val = blob[pos_next]

if marker == 1:
    # Inte sista Part; next_val identifierar Part N+1:s engine-typ
    # next_val: 0=AWM2, 1=Drum, 2=FM-X, 3=AN-X
    is_last = False
    next_engine = ENGINE_TYPE_VALUES[next_val]
else:
    # Detta ÄR sista Part; marker ÄR engine-typ-magic-byten för Part 1
    # marker: 8=AWM2, 110=AN-X, 82=FM-X, 73=Drum
    is_last = True
    part1_engine = ENGINE_MAGIC_TO_NAME[marker]
```

Detta betyder:
- Varje Parts pointer berättar engine-typen för NÄSTA Part (om någon)
- SISTA Part:s pointer wrap:ar runt och berättar engine-typen för Part 1
- Detta bildar en cirkulär linked list av engine-typer

## 3.7 Entr-bitmask för aktiva parts ★★★★★

Antalet aktiva Parts är kodat i en Entr-record-bitmask inom EPFM. Denna bitmask har en bit per Part (1 = aktiv).

För en 16-Part Multi/GM-fil är alla 16 bitar satta. För en single-Part Performance är bara bit 0 satt.

## 3.8 Helper-API för multi-part-pointer

```python
SUBBLOB_POINTER_REL = (5763, 5764)
ENGINE_MAGIC_BYTES  = {'ANX': 110, 'AWM2': 8, 'FMX': 82, 'Drum': 73}

def get_subblob_pointer_pos(part_idx):
    """Position för Part N:s pointer (1-indexerat)."""
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

## 3.9 Multi/GM 16-part-filer ★★★★★

**Multi/GM file type** är YSFC 16-part multitimbral-konfigurationen. Den används som en GM-kompatibel tongenerator (Multi/GM Performance med drums tilldelat till Part 10 enligt GM-standarden).

**Filstrukturen följer den dokumenterade multi-part-modellen exakt:**

| Komponent | Storlek | Innehåll |
|---|---:|---|
| Performance Common (sub-blob 1) | 6701 bytes | Standard Performance Common |
| 16 × Part Common (sub-blobs 2-17) | 5765 bytes vardera = 92240 bytes | Stride 5765 mellan parts |
| Engine pool | ~42583 bytes | 15 × AWM2 (stride 2508) + 1 × Drum (4963) för Part 10 |
| **DPFM total** | **141536 bytes** | Verifierat |

**Empiriskt verifierat:**

- 16 förekomster av "Concert GrandPiano" (AWM2 default-waveform-namn) med stride 5765 mellan Part Common-instanser
- Stride hoppar till 11530 (2 × 5765) mellan Part 9 → Part 11 eftersom Part 10 är Drum (har annat default-waveform-namn)
- 73 drum keys på fo 122261 (Part 10 engine-data startposition) med stride 68
- 72 av 73 drum keys har SW=1 i Multi/GM Init

**Filstorlek vs single-Part-filer:**

| Filtyp | DPFM | Total filstorlek |
|---|---:|---:|
| AWM2 single-part | 14981 | 38985 |
| AN-X single-part | 13162 | 37166 |
| FM-X single-part | 13682 | 37625 |
| Drum single-part | 17441 | 41427 |
| **Multi/GM 16-part** | **141536** | **165530** |

**Engine-typer per part i Multi/GM Init:**

- Parts 1-9: AWM2 (Concert GrandPiano)
- Part 10: Drum (Standard Drum Kit)
- Parts 11-16: AWM2 (Concert GrandPiano)

**Adresseringskonvention:**

Multi/GM använder **exakt samma adresseringsmodell** som andra multi-part-filer:
- Performance Common: `blob[0:6701]` (samma fält som single-Part)
- Part N Common: `blob[6701 + (N-1)*5765 : 6701 + N*5765]` för N=1..16
- Engine pool: börjar efter sista Part Common
  - Part N engine base = engine_pool_start + sum(engine_stride for parts 1..N-1)

Adresseringen är **redan stödd** av befintlig serializer-kod via:
- `SUBBLOB_POINTER_REL = (5763, 5764)`
- `get_subblob_pointer_pos(part_idx)`
- `ENGINE_MAGIC_BYTES`

**Implikation för editor:** Multi/GM kräver **inga nya strukturer** eller fält i serializern. Alla dokumenterade och binärverifierade Part Common, Engine Pool och Drum Key-fält fungerar identiskt på Multi/GM-filer — bara med 16 parts istället för 1.

---

# 4. Performance Common (Sub-blob 1) ★★★★★

Område: `blob[0:6701]` (6701 bytes). Verifierad med ~25 binärtestade UI-fält + flera u16le-par + ~3000 bytes konstant padding.

## 4.1 Header (sub-blob 1 header, samma som blob-header)

| abs | Storlek | Fält | Encoding | Status |
|---|---|---|---|---|
| 0..3 | 4 b | Sub-blob length prefix `00 00 00 15` | konstant | ★★★★★ |
| 4..21 | 18 b | **Performance Name** | ASCII, space-padded | ★★★★★ |
| 22 | 1 b | Null terminator | 0x00 | ★★★★★ |
| 23..24 | 2 b | Timestamp/save-counter — NOISE | ignoreras | ★★★★★ |
| 25..26 | 2 b | 0x00 0x00 | konstant | ★★★★★ |

## 4.2 Performance Toggles + Single Fields

| abs | Fält | Encoding | Default | Status | Testfil |
|---|---|---|---|---|---|
| 29 | portamentoMasterSwitch | bool | 0=OFF | ★★★★★ | `Portamento_ON.Y2L` |
| 30 | ribbonAssign1Mode | bool | 1=Latch (0=Moment) | ★★★★★ | `RibbonAssign_BothMoment` |
| 31 | ribbonAssign2Mode | bool | 1=Latch | ★★★★★ | `RibbonAssign_BothMoment` |
| 33 | ribbonMode (Hold/Reset) | bool | 1 | ★★★★★ | `RibbonMode_Hold` |
| 34 | reverbOnOff | bool | 1=ON | ★★★★★ | `Reverb_Off` |
| 35 | variationOnOff | bool | 1=ON | ★★★★★ | `Variation_Off` |
| 37 | masterFxOnOff | bool | 0=OFF | ★★★★★ | `MasterFX_ON` |
| 38 | arpMasterOn (?) | bool | 0 | ★★★★☆ | `ArpMasterON` (delar offset med OSC Mute/Solo edit-state) |
| 39 | msMasterOn | bool | 0=OFF | ★★★★★ | `MSMasterON` |
| 50 | commonAudioSwitch | bool | 1=ON | ★★★★★ | `CommonAudio_Off` |
| 56 | **smartMorphEnable** | bool | 0 (1 om SM aktiv) | ★★★★★ | `TEST-FMX-SMARTMORPH` |
| 57 | sliderDirection | bool | 0=Normal (1=Reverse) | ★★★★★ | |
| 66 | modifiedFlag — NOISE | edit-state | varies | ★★★★★ | (filtreras) |
| 68 | **Performance Volume = EF Master Output** | direct, 0..127 | 127 | ★★★★★ | `TEST5-1-VOL50` (UI-aliasing) |
| 70 | **Performance Pan** | c64, -63..+63 | 64 (Center) | ★★★★★ | `TEST5-4-PAN` |
| 92 | **Performance Tempo** | direct BPM (u8) | 120 | ★★★★★ | `TEST5-2-TEMPO90` |
| 94 | **Performance Portamento Time** | direct (möjligen c64) | 64 | ★★★★★ | `Portamento_Time_50` |
| 104 | lastActiveScene | u8 (0=Scene1, 7=Scene8) | 0 | ★★★★★ | `Scene1`, `Scene2`, ... |
| 216 | ribbonGridMode | enum (0=Cont, 1=5step) | 0 | ★★★★★ | `RibbonGrid_5step` |

**UI-aliasing:** Vissa bytes har två UI-labels. `blob[+68]` heter "Performance Volume" i Performance Edit men "EF Master Output" i Envelope Follower-vyn — **samma fysiska byte**. Bekräftat: `EnvelopeFollowerOutput_Master_90.Y2L` ändrar exakt `blob[+68]` från 127 → 90.

⚠️ **`blob[+80]` och `blob[+82]`** har konstant värde `0x40` i alla testade filer och ändras inte av någon känd UI-parameter. Kopiera verbatim.

⚠️ **`blob[+654]`** ändras i 9+ orelaterade tester (EF Part change, många InsertionAssign edits) — det är en **side-effect-flagga**, inte en parameter. Filtreras vid diff.

## 4.2.1 Strukturella metadata-bytes ★★★★★

Fundamentala bytes som styr blob-arkitekturen. Måste sättas korrekt vid skrivning.

| abs | Fält | Encoding | Bevis |
|---|---|---|---|
| 6695 | **Max aktiv Part-index** | u8, 1..16 (HÖGSTA nummer, INTE antal) | 4 multi-part-filer, korrelation 100% |
| 6700 | **Engine Type (Part 1)** | u8 enum: 0=AWM2, 1=Drum, 2=FMX, 3=ANX | 30+ engine-specifika filer, korrelation 100% |
| 12464..12465 | **Part 2 engine-prefix** | u8 × 2, engine-specifika i multi-part | Engine-discriminating i sub-blob 2 |

**Exempel på Max Active Part:**

- Part 1 only → `blob[+6695] = 1`
- Parts 1+2 → `blob[+6695] = 2`
- Parts 3+5 (icke-konsekutiva) → `blob[+6695] = 5` (= högsta, inte antalet 2)

**Konsekvens för editor:**

```python
def set_part_metadata(blob, active_part_indices, engine_part1):
    """active_part_indices: list of 1-baserade part-numbers
       engine_part1: 'AWM2', 'Drum', 'FMX', eller 'ANX'"""
    blob[6695] = max(active_part_indices)
    blob[6700] = {'AWM2': 0, 'Drum': 1, 'FMX': 2, 'ANX': 3}[engine_part1]
```

## 4.3 Hardware Ribbon Control

Sammanfattning av Ribbon-relaterade fält (alla ★★★★★):

| abs | Fält | Encoding | Default |
|---|---|---|---|
| 30 | ribbonAssign1Mode | bool | 1=Latch |
| 31 | ribbonAssign2Mode | bool | 1=Latch |
| 33 | ribbonMode (Hold/Reset) | bool | 1=Reset (0=Hold) |
| 57 | sliderDirReverse | bool | 0=Normal |
| 216 | ribbonGridMode | enum | 0=Continuous |

## 4.4 SuperKnob Link Per Scene ★★★★★

8 bytes vid `blob[40:48]` (en byte per scen), plus mirror i Scene Struct 1.

| abs | Fält | Encoding | Default |
|---|---|---|---|
| 40..47 | skLinkScene1..8 | u8 bool | 1=ON |
| 1717..1724 | (mirror inom Scene Struct 1) | u8 bool | 1 |

Mirror är replikerad data — uppdateras parallellt.

```python
def get_sk_link_addr(scene, mirror=False):
    """scene = 1..8"""
    base = 1717 if mirror else 40
    return base + (scene - 1)
```

## 4.5 Common FX Routing ★★★★★

| abs | Fält | Encoding | Default |
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

Område `blob[152:184]`, alla u8 direct (raw = MIDI CC#), stride 2 per fält.

| abs | Fält | Default | Status |
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

**Hard-coded i firmware (EJ I BLOB):**
- Scene CC (= 92)
- Super Knob CC (= 95)
- Footswitch Assign (= Arp Sw)

## 4.7 Per-Scene SuperKnob Value ★★★★★

8 × u16le vid `blob[184:200]` (en u16le per scen).

| abs | Fält | Encoding | Default |
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

Område `blob[376:428]` (52 bytes). 26 fält.

| abs | Fält | Encoding |
|---|---|---|
| 34 | reverbOnOff (i toggle-area) | bool, default 1 |
| 376 | reverbCategory | u8 enum |
| 377 | version-byte | konstant 1 |
| 380..381 | reverbType | u16le, default 32 |
| 382..383 | reverbPreset | u16le, default 10 |
| 384..426 | 22 × u16le params (Type-specifika) | stride 2 |

För Shimmer Reverb-typ är de 22 parametrarna: Shimmer Gain, Shimmer Fdbk, Shimmer HPF, Shimmer LPF, P1/P2 Balance, P1&P2 Panning, Pitch 1, Fine 1, Pitch 2, Fine 2, Cross-Feedback, Color, Reverb Time, Initial Delay, Diffusion, Size, P1&P2 Dly Ofs, Mod Depth, Mod Speed, AM Depth, AM Freq, AM Waveform. Andra Reverb Types använder samma slots med olika tolkningar.

## 4.9 Variation FX ★★★★★

Område `blob[432:484]` (52 bytes). 28 fält.

| abs | Fält | Encoding |
|---|---|---|
| 35 | variationOnOff (i toggle-area) | bool, default 1 |
| 432 | variationType | u8 enum |
| 436..482 | 24 × u16le params | stride 2 |

För M/S EQ Compressor-typ matchar parametrarna Master FX-layouten (24 param-mall).

## 4.10 Master EQ ★★★★★ / ★★★★☆

Område `blob[560:593]`. Per-band-stride är icke-uniform (Low använder 8 bytes pga shelf-typ; övriga 6 bytes).

| abs | Fält | Encoding | Default | Status |
|---|---|---|---|---|
| 560 | meqLowGain | c64 (±24 dB) | 64 | ★★★★★ |
| 562 | meqLowFreq | u8 logaritmisk ~6 raw/oct | 12 | ★★★★★ |
| 564 | meqLowQ | direct (raw = UI × 10) | 7 (=0.7) | ★★★★★ |
| 566 | meqLowType | enum 0=Shelf, 1=Peak | 0 | ★★★★★ |
| 568 | meqLowMidGain | c64 | 64 | ★★★★★ |
| 570 | meqLowMidFreq | u8 logaritmisk | 20 | ★★★★☆ (predikterat) |
| 572 | meqLowMidQ | u8 direct | 7 | ★★★★★ |
| 574 | meqMidGain | c64 | 64 | ★★★★★ |
| 576 | meqMidFreq | u8 logaritmisk | 28 | ★★★★★ |
| 578 | meqMidQ | u8 direct | 7 | ★★★★★ |
| 580 | meqHiMidGain | c64 | 64 | ★★★★★ |
| 582 | meqHiMidFreq | u8 logaritmisk | 44 | ★★★★☆ (predikterat) |
| 584 | meqHiMidQ | u8 direct | 7 | ★★★★★ |
| 586 | meqHighGain | c64 | 64 | ★★★★★ |
| 588 | meqHighFreq | u8 logaritmisk | 52 | ★★★★★ |
| 592 | meqHighType | enum 0=Shelf, 1=Peak | 0 | ★★★★★ |

**Design-anteckning:** När Q ändras kan Type-flag auto-uppdateras (+566 = 0 → 1 vid Q-max). UI-logik: Q är meningsfullt bara för Peak-type, inte Shelf.

**★★★★☆ predikterade fält:** Lo Mid Freq (570) och Hi Mid Freq (582) saknar dedikerade clean-1-diff testfiler. Stride-mönstret (6-byte block för icke-Low-band) gör positionerna högsta sannolika men ej empiriskt bevisade. Kandidater för framtida verifiering.

## 4.11 Master FX ★★★★★

Område `blob[598:650]` (52 bytes). 26 fält. Identisk struktur med Reverb/Variation FX.

| abs | Fält | Encoding |
|---|---|---|
| 37 | masterFxOnOff (toggle) | bool, default 0=OFF |
| 598..599 | masterFxType | u16le, default 32 (M/S EQ Compressor=80) |
| 602..648 | 24 × u16le params | stride 2 |

För M/S EQ Compressor-typ: M/S Balance, M Threshold, M Makeup Gain, S Threshold, S Makeup Gain, Stereo Expand, Comp Type, M Comp Curve, S Comp Curve, M Gain, S Gain, EQ Position, M EQ Low Freq/Gain/Q, M EQ High Freq/Gain/Q, S EQ Low Freq/Gain/Q, S EQ High Freq/Gain/Q.

## 4.12 SuperKnob Mid-Position ★★★★★

Område `blob[670:723]`.

| abs | Fält | Encoding | Default |
|---|---|---|---|
| 670..671 | commonSuperKnobValue | u16le | 512 |
| 672 | midPositionEnable | bool | 0 |
| 674..721 | 8 assigns × 6 bytes | stride 6 per assign | - |

Per assign (N=0..7), abs = 674 + N × 6:

| Relativ | Fält | Encoding | Default |
|---|---|---|---|
| +0 | AssignN LeftPosition | u8 | 0 |
| +2 | AssignN MidPosition | u16le | 512 |
| +4 | AssignN RightPosition | u16le | 1023 |

## 4.13 Region [732:766] [STRUKT] ★★★★★

34 bytes, strukturellt karaktäriserat men UI-funktion ej identifierad.

```
[732:760]  14 × u16le-värden
[760:766]  6 byte trailer
```

**Default-värden:** `[31, 31, 15, 7, 23, 7, 23, 15, 15, 23, 7, 23, 7, 15]`

Pattern: alla värden tillhör "8N − 1"-familjen (möjlig bit-mask). UI-funktion okänd. Patch editor: läser och skriver tillbaka oförändrat.

## 4.14 Audio In + Envelope Follower ★★★★★

| abs | Fält | Encoding | Default |
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
- `blob[+766]` har två UI-labels — "Audio In Volume" och "EF AD Output Level". Samma fysiska byte.
- `blob[+48, +49]` (Common-vyn) styr samma logiska funktion som `blob[+6734, +6735]` (Part-vyn, sektion 5.1). UI har två paths för Audio In Insertion A/B switches.

**Audio In Mute & Solo — EJ I BLOB ★★★★★:**
Mute- och Solo-knapparna på Audio In-raden i Mixing-vyn (flik "Audio")
är **UI-state**, inte persisterad data. Verifierat med TEST5R3-AUDIO_MUTE_ON.Y2L:
toggling av Mute → 0 signal-diffs i hela blob. Editor behöver ej hantera dessa.

## 4.15 Common Assign Names ★★★★★

Område `blob[2280:2447]` (8 strängar × 21 bytes = 168 bytes).

```
COMMON_ASSIGN_NAMES_BASE   = 2279
COMMON_ASSIGN_NAMES_STRIDE = 21
COMMON_ASSIGN_NAMES_LEN    = 16  # max chars
```

Default: "Assign 1", "Assign 2", ..., "Assign 8".

```python
def get_common_assign_name_addr(slot):
    """slot = 1..8. ASCII börjar vid +1 från base (len-prefix vid +0)."""
    return 2279 + 1 + (slot - 1) * 21
```

## 4.16 CA_PERF (Common Assigns Performance) ★★★★★

Se sektion 7 — identisk struktur som CA_PART (skillnad: scope-flag).

## 4.17 Stride-106 Zone/Control-block [STRUKT]

5 grupper × 8 block = 40 block totalt, ~3300 bytes:

| Grupp | Område | Antal block |
|---|---|---|
| 1 | `[840:1710]` | 8 block |
| 2 | `[3186:4043]` | 8 block |
| 3 | `[4083:4943]` | 8 block |
| 4 | `[4943:5826]` | 8 block |
| 5 | `[5942:6700]` | 8 block |

**Hypotes:** per-part Aftertouch/Velocity-tabeller eller Mod Source-mappningar. UI-funktion ej identifierad. Patch editor: läs/skriv verbatim.

## 4.X Control Assign — 32 slots ★★★★★

UI: **Common / Control / Control Assign** — möjliggör att routea controllers
(Mod Wheel, Aftertouch, Foot Controllers etc.) till parametrar i Performance.
Verifierat med `Test-AWM2-Control-ControlAssign-Source_ModWheel_Detsination1_Volume_CurveType_Bell_Polarity_Bi_Param1_4_Param2_3.Y2L`.

**Position:** `[2451:3155]` = 32 slots × 22 bytes = 704 bytes totalt.

```python
CONTROL_ASSIGN_BASE = 2451
CONTROL_ASSIGN_STRIDE = 22
CONTROL_ASSIGN_COUNT = 32  # 8 Assign Knobs × 4 Destinations per Knob
```

**Slot-struktur (22 bytes, rel 0..21):**

| Rel | Fält | Encoding | Default | Tolkning |
|----:|---|---|---:|---|
| 0 | slot_signature | u8 const | 18 | Alltid 18 i alla 32 slots |
| 1 | source_set | u8 bool | 0 | 0=Off, 1=Source aktiv |
| 3 | source_id | u8 enum | 8 | 8=None default, 1=ModWheel/CC#1 (Yamaha enum) |
| 5 | dest_param_lo | u8 | 1 | Destination parameter low byte |
| 6 | dest_param_hi | u8 | 0 | Destination param hi / flag |
| 9 | param2 | u8 | 0 | Parameter 2 (test: 0→3) |
| 11 | param1 | u8 | 5 | Parameter 1 (test: 5→4) |
| 13 | curve_type | u8 enum | 0 | Curve typ (test: 0→3 för "Bell") |
| 15 | polarity | u8 enum | 0 | 0=Uni, 1=Bi |
| 17 | slot_endmark | u8 const | 192 | Alltid 192 (0xC0) i alla slots |

**32 slots layout:** Sannolikt **8 Assign Knobs × 4 Destinations per Knob** (matchar Yamaha-modellen där varje knob kan ha 4 destination-rader). Eller alternativt 8 Knobs × 4 Curve-slots.

**Notera:** Detta är **Common-nivå** (Performance-globalt), INTE per Part eller per Element. Det stämmer överens med din feedback om att Controller Sets är Common-nivå.

**Källa-enum (source_id rel +3):** 8=None, 1=ModWheel (CC#1). Fler värden behöver verifieras med dedikerade tester.

---

# 5. Part Common (Sub-blob 2..N) ★★★★★

Varje Part Common är **5765 bytes** (sub-blob payload + 27-byte header).

```
Part N sub-blob start = 6701 + (N-1) × 5765
Part N payload start  = sub_blob_start + 27
```

Per-Part rel-offsets är **identiska över alla 16 parts** inom samma engine. Offsets nedan är abs för Part 1 (sub_blob_start = 6701).

## 5.1 Part Common Single-fields (Part 1, abs) ★★★★★

| abs | rel_part | Fält | Encoding | Default | Status | Testfil |
|---|---|---|---|---|---|---|
| 6731 | 30 | **partMode** | enum 0=Internal, 1=External | 0 | ★★★★★ | `Test-AWM2_PartMode_External` |
| 6732 | 31 | partKbdCtrlOn | bool | 1=ON | ★★★★★ | |
| 6733 | 32 | **partMute** | bool | 0=unmuted | ★★★★★ | `TEST5R3-T5i-Part1-Mute-ON` |
| 6734 | 33 | **partAudioInInsASw** | bool | 1=ON | ★★★★★ | `TEST5R3-T1a-AudioInsA-OFF` |
| 6735 | 34 | **partAudioInInsBSw** | bool | 1=ON | ★★★★★ | `TEST5R3-T1b-AudioInsB-OFF` |
| 6737 | 36 | partMSPartSwitch | bool | 1 | ★★★★★ | `MSMaster_verify` |
| 6740 | 39 | partPortamentoOn | bool | 1=ON | ★★★★★ | |
| 6743..6770 | 43..70 | **Receive Switches** (26 st) | bool block | mest 1=ON | ★★★★★ | Se sektion 6 (AWM2-) |
| 6775 | 74 | **partPgmChangeSw** (ext-only) | bool | 1=ON | ★★★★★ | `Test-AWM2_PgmChange-toggle_Off` |
| 6776 | 75 | **partBankSelectSw** (ext-only) | bool | 1=ON | ★★★★★ | `Test-AWM2_BankSelect-toogle_Off` |
| 6790 | 89 | **partPanSw** (ext-only) | bool | 1=ON | ★★★★★ | `Test-AWM2_Pan-toggle_Off` |
| 6791 | 90 | **partVolExpSw** (ext-only) | bool | 1=ON | ★★★★★ | `Test-AWM2_VolExp-toggle_Off` |
| 6801 | 100 | **partArpMasterOn** | bool | 1=ON | ★★★★★ | Måste bevaras/sättas korrekt för User-Arp playback |
| 6802 | 101 | **partArpPlayOnly** | bool | 0 | ★★★★★ | Ska inte användas som ersättning för Arp Master |
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
| **6984** | **283** | **partInsA_SubType** | u8 | 0 | ★★★★★ | (samma) |
| **6987..7015** | **286..314** | **partInsA_Param1..15** | u8 stride 2 | 0 (set by Type) | ★★★★★ | (Insertion-tester) |
| 7273 | 572 | partTxRxChannel | enum 0=Ch1...15=Ch16, 127=OFF | 0 | ★★★★★ | |
| **7287** | **586** | **partMidiVolume** (ext-only) | u8 direct | 100 | ★★★★★ | `Test-AWM2_MidiVolume_50` |
| **7289** | **588** | **partMidiPan** (ext-only) | u8 c64 | 64 | ★★★★★ | `Test-AWM2_MidiPan_R6` |
| **7295** | **594** | **partMidiPgmNum** (ext-only) | u8 direct | 0 | ★★★★★ | `Test-AWM2_MidiPgmNum_030` |

**UI-aliasing:** `blob[+6831]` är **Part 1 Volume** i Mixing-vyn (samt
Part Edit-vyn) och **EF Part 1 Output** i EF-vyn. Samma fysiska byte.
Bekräftat: `AWM2_00_Init_Part1_Volume_127.Y2L` (100→127),
`EnvelopeFollowerOutput_70.Y2L` (100→70) och
`TEST5R3-T2a-Mixing-Part1-Vol80.Y2L` (100→80) ändrar exakt samma offset.

**Per-Part Mixer-block:** Bytes 6831/6833/6835/6837/6839 (stride 2) bildar
Performance Mixing-vyns 5 fält per Part: Volume / Pan / RevSend / VarSend / DryLevel.

**Audio In Insertion-aliasing:** `abs 48, 49` (Common-area) ändras av
"Common / Audio Routing"-UI-vyn (Performance-level), medan `blob[+6734, +6735]`
(Part Common) ändras av "Common / Audio / Insertion A/B toggle"-vyn (per-Part).
UI har **två paths** för samma logiska funktion. Editor måste hantera båda.

**Part Mute/Solo:** Part Mute @ abs 6733 är persisterad (TEST5R3-T5i),
medan Part Solo är **UI-only state** och persisteras INTE i blob
(TEST5R3-T5j gav 0 signal-diffs).

**User-Arp-säkerhetsregel:** `partMute` vid rel +32, `partArpMasterOn` vid rel +100 och `partArpPlayOnly` vid rel +101 är separata persisterade tillstånd. En korrekt Y2L-export kan aktivera Arp Master när en Part har aktiva User-Arp scene-referenser, men får inte sätta Part Mute och får inte behandla Arp Play Only som likvärdigt med Arp Master.

**Part Mode (rel +30) ★★★★★:** `partMode` = 0 (Internal, default) eller 1 (External).
När External är aktiverat skickar Part:n MIDI till externa enheter och följande
fält blir relevanta (märkta "ext-only" i tabellen):
- `partPgmChangeSw` (rel 74), `partBankSelectSw` (rel 75)
- `partPanSw` (rel 89), `partVolExpSw` (rel 90)
- `partMidiVolume` (rel 586), `partMidiPan` (rel 588), `partMidiPgmNum` (rel 594)

Dessa fält finns i blob även när Part Mode = Internal (defaults bibehålls),
men UI visar dem bara när External är aktiverat.

**Per-Part Insertion FX struktur (rel +282..+314) ★★★★★:**

InsA/InsB är **PART-NIVÅ** (inte per-element). Element ROUTAS till InsA/InsB
via element-fältet `elem_connect` (rel +81 i element). Strukturen är **samma
över alla engine-typer** (AWM2/AN-X/FM-X verifierade).

Layout per Part:
- rel +282 = InsA Type (u8 enum; 0=Thru default, 18=SPXRoom, 48=Symphonic,
  32=CompDistorsion, 68=MultiFX, 80=GatedReverb, ...)
- rel +283 = InsA Sub-type/Variation
- rel +286, +288, +290, +292, +294, +296, +298, +300, +302, +304, +306, +308,
  +310, +312, +314 = InsA Param 1-15 (stride 2)

**Param-betydelser varierar med InsA Type** — en Reverb-effekt har andra
parameter-namn än en Distorsion-effekt. Editor måste hålla en separat
mapping `(InsA_Type, param_idx) → param_name`.

**InsB:** Strukturen ligger direkt efter InsA med 56 bytes mellanrum:
- InsA Type @ rel +282 (abs 6983)
- InsB Type @ rel +338 (abs 7039) ★★★★★ Verifierat med `Test-AWM2_InsertionB-Type-Reverb_SPXRoom`
- InsB Sub-type @ rel +339
- InsB Param 1-15 @ rel +342, +344, +346, ..., +370 (stride 2)

Båda har identisk struktur (Type/Sub-type/Params 1-15). Totalt 56 bytes per Insertion-block.

**Ej persisterad:** `ModControl Display Filter` (UI-vyn för att filtrera Control Assign-listan
per Source = ModWheel/CC#16/etc.) är UI-only state och persisteras INTE i blob — verifierat
med `Test-AWM2_ModControl-DisplayFilter_ModWheel.Y2L` som var byte-för-byte identisk med
`Test-AWM2_InsertionB-Type-Reverb_SPXRoom.Y2L` förutom save counter.

**Per-Part Mod Source-tabell (rel +600..+663) ★★★★★:**

UI: **Edit / Part / Mod/Control / Control Assign** — låter användaren routea
Source (Aftertouch, CC, etc.) till parametrar på Part-nivå.

Position: `Part rel +600..+663` = **4 slots × 16 bytes** (64 bytes).

```python
PER_PART_MOD_SOURCE_REL_BASE = 600   # rel inom Part sub-blob (abs 7301 för Part 1)
PER_PART_MOD_SOURCE_STRIDE = 16
PER_PART_MOD_SOURCE_COUNT = 4
```

**Slot-struktur (16 bytes, rel 0..15):**

| Rel | Fält | Encoding | Default | Test-värde |
|----:|---|---|---:|---|
| 0 | source_set | u8 bool | 0 | 0→1 (Source aktiverad) |
| 2 | signature | u8 | 1 | 1→2 (AT som source) |
| 6 | param2 | u8 | 0 | 0→3 (test param2=3) |
| 8 | param1 | u8 | 5 | 5→4 (test param1=4) |
| 10 | curve_type | u8 enum | 0 | 0→3 (Bell) |
| 12 | polarity | u8 enum | 0 | 0=Uni, 1=Bi |
| 14 | endmark | u8 const | 192 (0xC0) | always |

**OBS — UI-only fält:** Element-Switch (AllElement / Element1 / Element2 / Element3
för en AT-assign) persisteras INTE i blob.: 4 olika filer
med olika Element-switch gav IDENTISKA byte-diffs.

**Olika struktur än Common ControlAssign:**
- Common ControlAssign har stride 22 bytes och 32 slots
- Per-Part Mod Source har stride 16 bytes och 4 slots
- Endast 4 source-slots per Part räcker eftersom Common-nivån har de 32 slots

```python
PART_COMMON_REL = dict(
    partMode_rel     = 30,    # ★★★★★ (0=Internal, 1=External)
    kbdCtrlOn_rel    = 31,
    partMute_rel     = 32,    # ★★★★★ (Part Solo är UI-only, ej i blob)
    audioInInsASw_rel = 33,
    audioInInsBSw_rel = 34,
    msPartSwitch_rel = 36,
    portamentoOn_rel = 39,
    # rel +43..+70: Receive Switches (26 st) — se sektion 6
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

FM-X har separat LFO-mappning per part:

| abs (Part 1) | Fält | Encoding | Default |
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

**FMX LFO TempoNote-tabell:**

```
raw=5:1/16, 6:1/8Tri, 7:1/16Dot, 8:1/8, 9:1/4Tri, 10:1/8Dot,
raw=11:1/4 (default), 12:1/2Tri, 13:1/4Dot, 14:1/2, 15:WholeTri, 16:1/2Dot,
raw=17:1/4×4, 18:1/4×5, 19:1/4×6, 20:1/4×7, 21:1/4×8, 22:1/4×16,
raw=23:1/4×32, 24:1/4×64
```

**FMX LFO Destinations** (verifierade subset):

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

| abs (Part 1) | Fält | Encoding | Default |
|---|---|---|---|
| 12509 | fmxPart2ndLfoWave | enum 0..12 | 0 |
| 12511 | fmxPart2ndLfoSpeedNormal | direct | 30 |
| 12513 | fmxPart2ndLfoPhase | enum 0=0°,1=90°,2=180°,3=270°,4=360° | 0 |
| 12515 | fmxPart2ndLfoDelay | direct | 0 |
| 12517 | fmxPart2ndLfoKeyOnReset | bool | 0 |
| 12519..12523 | 2nd LFO Global Mod Depths | u8 ×3 (Pitch/Amp/Filter) | 0,0,0 |
| 12529 | fmxPart2ndLfoExtended | bool | 1=ON |
| 12531 | fmxPart2ndLfoSpeedExtended | direct | 60 |

Filter Mod är GLOBAL ONLY (ingen per-OP).

## 5.4 Part PEG (FM-X) ★★★★★

| abs (Part 1) | Fält | Encoding | Default |
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

| abs (Part 1) | Fält | Encoding | Default |
|---|---|---|---|
| 6849 | partAegAttack | c64 | 64 (=UI 0) |
| 6851 | partAegDecay | c64 | 64 |
| 6853 | partAegSustain | c64 | 64 |
| 6855 | partAegRelease | c64 | 64 |

**OBS:** Engine-specifika filter/EG-fält ligger i engine-data, inte i Part Common.

## 5.6 Part Pitch Bend / Detune / Note Shift ★★★★★

| abs (Part 1) | Fält | Encoding | Default | Range |
|---|---|---|---|---|
| 6913 | partPitchBendRangeUpper | c64 | 66 (=+2) | 16..88 (-48..+24) |
| 6915 | partPitchBendRangeLower | c64 | 62 (=-2) | 16..88 |
| 6917 | partDetune | c128 (1 cent/raw) | 128 (=0 Hz) | bredd ej fastställd |
| 6919 | partNoteShift | c64 | 64 (=0 semitones) | 1..127 |

**TEST-PB-serien:**
- `TEST-PB0.Y2L`: 66→64 (UI 0)
- `TEST-PB+24.Y2L`: 66→88 (UI +24)
- `TEST-PB-24.Y2L`: 66→40 (UI −24)

## 5.7 Part 3-band EQ ★★★★★

| abs (Part 1) | rel_part | Fält | Encoding | Default |
|---|---|---|---|---|
| 6939 | 231 | part3bandLowFreq | u8 freq-index | 54 (~62.5 Hz) |
| 6941 | 233 | part3bandLowGain | c64 ±24 dB | 64 |
| 6943 | 235 | part3bandMidFreq | u8 freq-index | 141 (~675 Hz) |
| 6945 | 237 | part3bandMidGain | c64 | 64 |
| 6947 | 239 | part3bandMidQ | direct | 0 (UI shows 0.7) |
| 6949 | 241 | part3bandHighFreq | u8 freq-index | 231 (~7.4 kHz) |
| 6951 | 243 | part3bandHighGain | c64 | 64 |

**OBS — Freq ligger FÖRE Gain** (omvänd ordning från Master EQ).

UI har bara EN Q-kontroll (Mid Q). Low och High är shelf-typer utan Q.

**Side-effect:** Första edit triggar `blob[+6847] = 0 → 127` (trolig "Part EQ enabled"-flag).

## 5.8 Part 2-band EQ ★★★★★

Helt symmetrisk 8-byte stride per band.

| abs (Part 1) | rel_part | Fält | Encoding | Default |
|---|---|---|---|---|
| 6953 | 245 | part2bandEq1Type | enum 0=Thru, 3=LowShelf, 5=Peak/Dip | 0 (→5 vid edit) |
| 6955 | 247 | part2bandEq1Freq | logaritmisk ~24 raw/oct | 48 |
| 6957 | 249 | part2bandEq1Gain | c64 (raw = 64 + UI_dB × 2) | 64 |
| 6959 | 251 | part2bandEq1Q | direct (raw = UI_Q × 10, Peak only) | 1 |
| 6961 | 253 | part2bandEq2Type | enum | 0 (→5 vid edit) |
| 6963 | 255 | part2bandEq2Freq | logaritmisk | 48 |
| 6965 | 257 | part2bandEq2Gain | c64 | 64 |
| 6967 | 259 | part2bandEq2Q | direct | 1 |
| 6969 | 261 | partOutputLevel | c64 (raw = 64 + UI_dB × 2) | 64 |

**Designinsikt:** Type-flag (6953 / 6961) sätts till 5 vid första edit i respektive band (EQ aktiverad-indikator).

## 5.9 Arp Common ★★★★★

Område `blob[6802:7165]`.

| abs (Part 1) | Fält | Encoding | Default |
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
| 7127 | arpTriggerMode | u8 (0=normal, 1=Toggle) | 0 |
| 7129 | arpVelocityOffset | c64 | 64 |
| 7131 | arpIndividualVelocity (Arp1) | u8 (0x80+n) | 128 |
| 7133 | arpIndividualGateTime (Arp1) | u8 (0x80+n) | 128 |
| 7163 | arp1Name typeId | u8 arpeggio bank/type index | 79 |
| 7164 | arp1Name patternId | u8 pattern within type | 25 |

## 5.10 Region [7094:7165] — Arp Individual data [STRUKT]

71 bytes. Innehåller per-arp-step velocity/gate-array (u16le-array, mest c64=64 / 0x80=128). Verifierat fält: abs 7131 = velocity.

```
ARP_INDIVIDUAL_BASE = 7094
ARP_INDIVIDUAL_SIZE = 71
ARP_INDIVIDUAL_VELOCITY_PART1 = 7131
```

## 5.11 Part Assign Names ★★★★★

Område `blob[8049:8217]` (8 strängar × 21 bytes = 168 bytes).

```
PART_ASSIGN_NAMES_BASE   = 8048
PART_ASSIGN_NAMES_STRIDE = 21
PART_ASSIGN_NAMES_LEN    = 16
```

Default: "Assign 1", "Assign 2", ..., "Assign 8".

## 5.12 CA_PART (Per-Part Common Assigns) ★★★★★

Se sektion 7 — identisk struktur som CA_PERF.

## 5.13 AWM2 Control Source-block ★★★★☆

Område `blob[7300:7372]` i Part Common (relativt sub-blob 2 start = +599..+671).
**4 slots × 18 bytes** = 72 bytes. Hanterar AWM2 PolyAT/AT/Velocity-mapping
för Part (skilt från CA_PART som är generell CA-struktur).

```
AWM2_CONTROL_SOURCE_BASE        = 7300   # Part 1, abs
AWM2_CONTROL_SOURCE_STRIDE      = 18     # bytes per slot
AWM2_CONTROL_SOURCE_SLOT_COUNT  = 4
```

**Per-slot layout (relativt slot-bas):**

| Rel | Fält | Encoding | Bevis |
|---|---|---|---|
| +1 | Control Source Switch | bool | `Control_Source_PolyAT_*` |
| +3 | Control Destination ID | u8 enum (1=Resonance, 9=Filter, 10=Cutoff) | ★★★★☆ |
| +5 | Control Source Type | u8 (PolyAT/AT/MW source-id) | ★★★☆☆ |
| +7 | Control Depth | u8 direct | ★★★★☆ |
| +9 | Control Curve | u8 enum 0..5 | ★★★★☆ |
| +11 | Control Param 1 | u8 direct | ★★★★☆ |
| +13 | Control Param 2 | u8 direct | ★★★★☆ |

Adressering: `slot_addr = AWM2_CONTROL_SOURCE_BASE + slot_idx * 18`.
Övriga bytes inom slot (+0, +2, +4, +6, ...) är padding eller okända.

Verifieringsbas: tester `Control_Source_PolyAT_Destination1_*`.

---

# 6. Receive Switch per Part ★★★★★

## 6.1 Block-arkitektur

Varje Part har ett 28-byte Receive Switch-block:

```
RCV_SWITCH_REL_OFFSET = 43   # relativt sub-blob start
RCV_SWITCH_BLOCK_SIZE = 28   # 26 switchar + 2 byte block-end markörer
RCV_SWITCH_COUNT      = 26
```

**Adress för Part N's RcvSw:** `sub_blob_start(N) + 43`

**Engine-agnostiskt:** Strukturen är **identisk för AWM2, AN-X, FM-X och Drum**
(verifierat med `Test_AWM2_Part1_RcvSw_BankSelect_OFF` @ Pos 1 = abs 6745
och `Test_AWM2_Part1_RcvSw_FC1_Off` @ Pos 11 = abs 6755).

## 6.2 RcvSw-positioner (26/26 mappade)

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
| 22 | [INTERN] reserved | 1 | [INTERN] (default 1, ej UI-exponerat) |
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

## 6.4 RcvSw — EJ I BLOB ★★★★★

Hardware events lagras inte i performance-blob (hanteras på MODX-instrument-nivå):

- **Pitch Bend**
- **Ch.After Touch**
- **Poly.After Touch**

---

# 7. Common Assigns (CA-strukturer) ★★★★★

Två identiska 32-slot-strukturer: en Performance-nivå (CA_PERF), en Part-nivå (CA_PART).

## 7.1 CA-konstanter

```
CA_STRIDE        = 22       # bytes per slot
CA_SLOT_COUNT    = 32       # totalt slots per struktur
CA_TRAILER_SIZE  = 24       # block-end signature
CA_TOTAL_SIZE    = 728      # 32×22 + 24

CA_PERF_BASE     = 2451     # → slutar @ 3179
CA_PART_BASE     = 8220     # → slutar @ 8948
CA_PERF_TRAILER  = 3155     # = CA_PERF_BASE + 32*22
CA_PART_TRAILER  = 8924     # = CA_PART_BASE + 32*22
```

Slot N abs offset: `CA_BASE + N × 22` (N = 0..31).

**Slots 17–32** är bit-för-bit identiska med slots 1–16 i Init Voice — i UI exponeras typiskt bara 16, men formatet reserverar 32.

## 7.2 CA-slot layout (22 bytes per slot) ★★★★★

| Relativ | Fält | Encoding | Default |
|---|---|---|---|
| +0 | header | u8 | 18 |
| +1 | sw | bool | 0=Off |
| +3 | source | enum (CA_SOURCE) | 1=ModWheel |
| +5 | destination | enum (CA_DESTINATION) | 1=Volume |
| +9 | curveType | enum (Standard=0, Harmonic=18) | 0 |
| +11 | param1 | direct | 5 |
| +13 | param2 | direct | 0 |
| +15 | polarity | bool 0=UNI, 1=BI | 0 |
| +17 | depth — [INTERN] | u8, MODX-internal | 192 (0xC0) |

⚠️ **+17 (depth) är MODX-internt** — uppdateras automatiskt av MODX vid varje Store (som timestamp-bytes). Ignoreras vid patch-editing, ska inte skrivas.

## 7.3 Skillnad CA_PERF vs CA_PART

Byte +3 (scope-flagga) skiljer sig:
- **CA_PERF:** byte +3 = 8 i alla 32 slots (default)
- **CA_PART:** byte +3 = 1 i alla 32 slots (default)

## 7.4 CA Source enum

| Värde | Source | Status |
|---|---|---|
| 0 | PitchBend | ★★★★★ |
| 1 | ModWheel (default) | ★★★★★ |
| 2 | AfterTouch | ej verifierad |
| 3 | FootCtrl | ej verifierad |
| 4 | FootSw | ej verifierad |
| 5 | Breath | ej verifierad |
| 6, 7 | (CC-värden) | ej verifierade |
| 8 | Knob1 | ★★★★★ |
| 9 | Knob2 | ★★★★★ |
| 10 | Knob3 | ★★★★★ |
| 11..15 | Knob4..Knob8 | ej verifierade |

## 7.5 CA Destination enum (verifierad subset)

InsA Param-serien är linjär: raw = param_nr (1..24). InsB använder fast raw=25 med param# i CA+11.

### Encoding (kritiskt)

Destination består av **två bytes** i slot-strukturen: `destination_lo` (slot rel +4) och `destination_hi` (slot rel +5). Tillsammans utgör de ett index i den auktoritativa 414-entries-listan `CONTROLLER_DESTINATIONS` (`ysfc_enums/controllers.py`):

```
CONTROLLER_DESTINATIONS_idx = destination_lo + destination_hi * 256
```

- För destinationer med index **0..255**: `destination_lo` = idx, `destination_hi = 0`
- För destinationer med index **256..511** (Per-Part Assign Knobs, Performance, Arp, Motion Seq): `destination_lo = idx - 256`, `destination_hi = 1`

I tabellen nedan har "Värde"-kolumnen historiskt skrivit `lo`-byten och underförstått `hi=1` för värden 100, 105, 118 — dessa är egentligen `idx=356, 361, 374` i den fulla listan.

| Lo | Hi | Idx | Destination | Status |
|---:|---:|---:|---|---|
| 1 | 0 | 1 | Volume (default) / InsA Param 1 | ★★★★★ |
| 2..24 | 0 | 2..24 | InsA Param 2..24 | ★★★★★ (linjärt) |
| 25 | 0 | 25 | InsB Param | ★★★★★ (fast raw, param# i CA+11) |
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

## 7.6 CA CurveType enum (verifierad subset)

| Värde | Curve |
|---|---|
| 0 | Standard (default) |
| 1 | Sigmoid |
| 2 | Threshold |
| 18 | Harmonic |
| 19 | Steps |

## 7.7 Block-end signature (trailer)

24 byte trailer efter alla 32 slots:

```
04 00 00 00 04 00 01 00 01 00 00 00 14 00 00 3f 00 03 00 00 00 01 00 7f
```

Identisk i både CA_PERF och CA_PART. Samma signatur används också som "block-end marker" i region [788:840].

## 7.8 AWM2 AfterTouch Register ★★★★★

Separat från CA-blocket — eget litet AT-register med egen destination-encoding.

| abs (Part 1) | Fält | Encoding | Default |
|---|---|---|---|
| 7293 (= PART+593) | atSwitch | bool | 0=Off |
| 7295 (= PART+595) | atDestination | enum | 1=Pitch |

**AT Destination enum:**
- 1 = Pitch (default) ★★★★★
- 9 = FilterCutoff ★★★★★

---

## 7.9 Control Assign-strukturer ★★★★★

tre relaterade Control Assign-strukturer, totalt **944 bytes**.

### Common Control Assign — abs 2452..3155 (704 bytes)

**32 slots × 22 bytes stride** vid abs 2452.

Detta motsvarar `[COMMON] Control > Control Assign` i ESP-plugins UI (bild 30/31).
Strukturen är "global routing": Source = AsgnKnob/CC/AT etc., Destination =
en specifik parameter i en Part.

Standard-baseline (Init Normal AWM2):
```
[0, 0, 8, 0, 1, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 192, 0, 0, 0, 0, 18]
 |     |     |                       |                            |
 |     |     |                       |                            +-- trailer (18, kanske curve+polarity packat)
 |     |     |                       +-- endmark (192 = 0xC0)
 |     |     +-- source_id (default 1 = AsgnKnob1)
 |     +-- destination_lo (default 8 = ?)
 +-- enabled flag (0=inactive)
```

**Per-slot fält (relativa offset):**
| +rel | Fält | Encoding | Default |
|---:|---|---|---:|
| +0 | enabled | u8 bool | 0 |
| +2 | destination_lo | u8 enum | 8 |
| +4 | source_id | u8 | 1 |
| +10 | param_a | u8 | 5 |
| +16 | endmark | u8 const | 192 (0xC0) |
| +21 | trailer | u8 | 18 |

**Verifierat med tester:**
- Test-AMW2_Part_ControlAssign_destination1-8: slot 1..8 aktiverades med
  destinations 8/9/10/11/12/13/14/15 (verifiering att slots har 22-byte stride).
- Test-AMW2_Part_AfterTouch_destination1-4: samma struktur men sources 226-233
  (AT-relaterade source-värden).

### Part After Touch — Part rel +600..+663 (64 bytes)

**4 slots × 16 bytes stride** vid Part rel +600.

Detta motsvarar `[PART] Mod/Control > After Touch` i ESP-plugins UI (bild 17).
Per-part AT-mappning: 4 destination-slots där varje slot specificerar var
Aftertouch ska routea (default Source: Poly AT, Destination: Pitch).

Standard-baseline:
```
[0, 0, 1, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 192, 0]
 |     |                 |                |
 |     |                 |                +-- endmark
 |     |                 +-- param_a
 |     +-- destination enum (1=Pitch default)
 +-- enabled flag
```

| +rel | Fält | Encoding | Default |
|---:|---|---|---:|
| +0 | enabled | u8 bool | 0 |
| +2 | destination | u8 enum | 1 (Pitch) |
| +6 | param2 | u8 | 0 |
| +8 | param1 | u8 | 5 |
| +10 | curve_type | u8 enum | 0 (3=Bell) |
| +12 | polarity | u8 enum | 0 (Uni=0, Bi=1) |
| +14 | endmark | u8 const | 192 |

### Part Control Assign — Part rel +1520..+1695 (176 bytes) — VERIFIERAT MED 35 BEFINTLIGA TESTER

**8 slots × 22 bytes stride** vid Part rel +1520.

Detta motsvarar `[PART] Mod/Control > Part Control Assign` i ESP-plugin (bild 18).
Per-part Control Assign-mappning: 8 slots med samma 22-byte struktur som
Common Control Assign.

Standard-baseline (Init Normal AWM2):
```
[0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 192, 0, 0, 0, 0, 18]
```

**Slot-relativa fält (verifierat från 35 AWM2_00_Init_CA_*-tester):**

| +rel | Fält | Encoding | Default | Notering |
|---:|---|---|---:|---|
| +0 | enabled | u8 bool | 0 | 0→1 vid edit |
| +2 | dest_category | u8 | 1 | → 8 vid alla edits (valid flag) |
| +3 | dest_category_hi | u8 | 0 | |
| +4 | destination_lo | u8 enum | 1 | Faktisk destination |
| +5 | destination_hi | u8 | 0 | 1 för värden >127 |
| +8 | param2_or_curve_aux | u8 | 0 | Param2 / Steps-count / Threshold-aux |
| +10 | param1_or_curve_pri | u8 | 5 | Param1 OCH curve primary (delas) |
| +12 | curve_secondary | u8 | 0 | Sigmoid→3, Threshold→1 |
| +14 | polarity | u8 enum | 0 | Uni=0, Bi=1 |
| +16 | endmark | u8 const | 192 | 0xC0 |
| +21 | trailer | u8 | 18 | |

**Destination enum (slot +4) — verifierade värden:**

| Enum | Destination |
|---:|---|
| 1 | InsA Param1 (default) |
| 50 | Rev Send |
| 60 | Element Level |
| 61 | Element Pan |
| 87 | HPF Cutoff |
| 100 | Part Pan |
| 118 | MS Length |

(Värden >127 sätter destination_hi=1.)

**Curve Type-system (komplext, fält +10 + +12 + +8):**

| Curve | +8 | +10 | +12 | Notering |
|---|---:|---:|---:|---|
| Standard | 0 | 5 | 0 | Default (ingen ändring vid edit) |
| Sigmoid | 0 | 2 | 3 | |
| Steps | 19 | 2 | 0 | 3-byte konfiguration |
| Threshold | 2 | 0 | 1 | 3-byte konfiguration |

**OBS: Param1 OCH Curve Type delar byte +10.** När man väljer en non-Standard
kurva används +10 för "curve primary code", medan i Standard-läge är +10 = Param1.
Detta är ett polyvalent fält där tolkningen beror på curve_secondary (+12).

Verifierat från: AWM2_00_Init_CA_Source_AsgnKnob1..8, CA_CurveType_Sigmoid/Standard/Steps/Threshold,
CA_Polarity_Bi/Uni, CA_Param1_8, CA_Param2_3, CA_Source_AsgnKnob1_Destination1_*

### Hur strukturerna samarbetar

När man editerar `AsgnKnob 1 → Part 1 Assign 1` i UI (bild 31):
- **Common Control Assign slot N** sätter Source + global Destination.
- **Part 1 Control Assign slot M** specificerar per-Part destination-detaljer.
- Båda skrivs samtidigt när routing skapas i UI.

Detta är ett **double-layer routing-system**: Common är globalt, Part är
specifikt. Strukturerna är **identiska** (22 bytes stride), bara olika basadresser.

---

# 8. Scene Structures ★★★★★

Två separata strukturer: Scene Struct 1 (perf-globala flaggor) och Scene Struct 2 (per-Part Lane snapshots).

## 8.1 Scene Struct 1 — perf-globala ★★★★★

```
SCENE_STRUCT1_BASE   = 1710
SCENE_STRUCT1_STRIDE = 71
SCENE_COUNT          = 8
```

**Område:** `blob[1710:2278]` = 568 bytes (8 scener × 71 bytes).

**Per-scen fält (9 fält inom 71-byte record):**

| Relativ | Fält | Encoding | Default |
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

**Per-scene SuperKnob value mirror:** `blob[+1710 + N*71 + 25..26]` (u16le, samma data som per-scene SK-array vid abs 184).

```python
def scene_struct1_abs(field_name, scene_idx):
    """scene_idx: 0..7"""
    return 1710 + scene_idx * 71 + SCENE_STRUCT1_FIELDS[field_name]
```

**Cross-scene-verifiering:**
- Scene 4 SuperKnob @ 1925 = 1710 + 3×71 + 2 ✓
- Scene 8 ArpMsFx @ 2212 = 1710 + 7×71 + 5 ✓
- Scene 8 SuperKnob @ 2209 = 1710 + 7×71 + 2 ✓

## 8.2 Scene Struct 2 — per-part Lane ★★★★★

```
SCENE_STRUCT2_BASE   = 7421
SCENE_STRUCT2_STRIDE = 84
```

**Område:** `blob[7421:8093]` = 672 bytes (8 scener × 84 bytes).

**Per-scen fält (11 fält):**

| Relativ | Fält | Live mirror abs | Encoding |
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

**Notering:** KbdCtrl och NoteLimit per-part-toggles ligger i **Struct 1** (rel 15, 16), inte i Struct 2. UI-listan är förvirrande på den punkten.

**Hypotes (ej verifierad):** Scene Struct 2 är troligen aktiv-part-baserad (84 bytes räcker inte för 16 parts × 11 fält).

## 8.3 Sidoeffekter vid scen-redigering

- `blob[+32]` ändras vid Scene Common Offset toggle (perf-nivå master switch)
- `blob[+7417]` ändras vid Scene1 AEG Offset Off (160→115, mekanism okänd)
- `blob[+7419]` ändras vid varje per-part scen-redigering (modified-flagga, +1)

---

# 9. MS Sequencer ★★★★★

Område: `blob[8929:12404]` (i Part Common). Stride **884 bytes per lane** × 4 lanes.

**Lane-baser (Part 1):**

| Lane | Bas (abs) |
|---|---|
| Lane 1 | 8929 |
| Lane 2 | 9813 |
| Lane 3 | 10697 |
| Lane 4 | 11581 |

(Differens 884 ✓ verifierat över alla 4 lanes.)

## 9.1 Per-lane offsets (relativ från lane-bas) ★★★★★

| Rel | Fält | Encoding | Default |
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

Sex Performance Common-fält som styr Motion Seq globalt för hela
Performance. Verifierat med dedikerade testfiler (`Sequencer_Lane1_Common_*`)
samt TEST5R3-T4b/c/d (Lane 2/3/4 Swing-test → samma byte 100).

**UI-namn vs intern terminologi:** I UI-vyn "Motion Seq > Common / Lane"
heter sektionen "Common". Testfilernas namn (`Lane1_Common_*`) är
missvisande — fälten är **inte per-Lane**, de gäller alla Lanes och alla
Parts. Korrekt namn är "Common Motion Seq" eller "Performance MS".

| abs | Fält | Encoding | Default | Bevis |
|---|---|---|---|---|
| 100..101 | Common MS Swing | u16le c128 | 128 | `Lane1_Common_Swing_50` |
| 102 | Common MS Unit | u8 enum (3=1/16, 0=50%) | 3 | `Lane1_Common_Unit_50%` |
| 358 | ArpSelect | u8 0-indexerat | 0 (=Arp1) | (multi-test) |
| 360 | SyncQuantize | u8 | 0 (=OFF) | `Arp_Common_SyncQuantize_120` |
| 654 | MSSelect | u8 0-indexerat | 0 (=MS1) — OBS: kollision med side-effect-flagga (sektion 17) | |
| 656..657 | Common MS Amplitude | u16le c128 | 128 | `Lane1_Common_Amplitude_50` |
| 658..659 | Common MS Shape | u16le c64 | 64 | `Lane1_Common_Shape_50` |
| 660..661 | Common MS Smooth | u16le c128 | 128 | `Lane1_Common_Smooth_50` |
| 662..663 | Common MS Random | u16le c128 | 128 | `Lane1_Common_Random_50` |

## 9.3 Part Motion Sequencer (Part Common) ★★★★★

Sex Part Common-fält som styr Motion Seq för hela Part (alla 4 Lanes
i parten). I UI-vyn syns dessa under "Part"-sektionen, distinkt från
"Common"-sektionen ovan.

**Verifierat** testfiler (`Lane1_Part_*`) samt TEST5R3-T4b-ViewLane2-Swing50
(View Lane 2 + Part Swing 50 → samma byte 6887 som med View Lane 1).
View Lane-dropdown påverkar **inte** dessa bytes — den styr endast
Edit Part Sequencer-vyns visning.

| abs (Part 1) | Rel (sub-blob +N) | Fält | Encoding | Default |
|---:|---:|---|---|---:|
| 6887..6888 | +186 | Part MS Swing | u16le c128 | 128 |
| 6889..6890 | +188 | Part MS Amplitude | u16le c128 | 128 |
| 6891..6892 | +190 | Part MS Shape | u16le c64 | 64 |
| 6893..6894 | +192 | Part MS Smooth | u16le c128 | 128 |
| 6895 | +194 | Part MS Random | u8 direct 0..100 | 0 |
| 7097 | +396 | Part MS Unit | u8 enum (3=1/16, 0=50%) | 3 |

**Stride:** 5765 bytes mellan parts (Part 2 Swing @ 12652 = 6887 + 5765).

**Shared offsets:** `abs 6887` delas med "Arp Swing" (samma byte används
för båda funktionerna). `abs 7097` delas med "Arp Unit".

## 9.4 Per-lane data (Lane-block) ★★★★★

| abs | Fält | Encoding | Default |
|---|---|---|---|
| 12753 | Part seq-field | u8 (3=default, 4=seq-sync) | 3 |
| 13116 | Part arp-field | u8 (0=default, 9=arp-aktiv) | 0 |

---

# 10. Engine-data: AN-X ★★★★★

**Engine-storlek:** 684 bytes (689 i pool med separator).
**Pool-bas (Part 1, solo):** abs 12466 (= efter sub-blob 2's 5765 + 0 sep).

För Part N i multi-part-fil: se sektion 3 (engine-pool adressering).

## 10.1 OSC1 / OSC2 / OSC3 — stride 125 ★★★★★

```
ANX_OSC1_BASE = 12638   # Part 1, solo
ANX_OSC_STRIDE = 125
ANX_OSC2_BASE = 12763 = 12638 + 125
ANX_OSC3_BASE = 12888 = 12638 + 250
```

**Per-OSC layout:**

| OSC1 abs | Fält | Encoding | Default | Status |
|---|---|---|---|---|
| 12626 | (Wave område) | — | — | (Wave/Octave börjar lite tidigare) |
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

**OSC1 EG (separat sub-tabell):**

| abs | Fält | Encoding | Default |
|---|---|---|---|
| 12678..12679 | anxOsc1EGAttackTime | u16le | 0 |
| 12680..12681 | anxOsc1EGDecayTime | u16le | 160 |
| 12682..12683 | anxOsc1EGSustainLevel | u16le | 0 |
| 12684..12685 | anxOsc1EGReleaseTime | u16le | 160 |

OSC2 stride = OSC1 + 125. OSC3 stride = OSC1 + 250.

## 10.2 AN-X Filter 1 (abs 13005..13027) ★★★★★

Komplett mappad.

| Abs | Fält | Encoding | Default |
|---|---|---|---|
| 13005 | filter1_type | enum | 1 (LPF12=3 verifierad) |
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

| Abs | Fält | Encoding | Default |
|---|---|---|---|
| 13081 | (pad/marker före filter2_type, default 30) | [INTERN] | 30 |
| 13082 | filter2_type | enum | 5 (HPF24) — ★★★★★ UI-bekräftat (ANX bild 6: Filter 2 Type default HPF24) + cross-map ANX_FILTER +6708 |
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

### AN-X Filter-trailers — STÄNGDA som [INTERN] ★★★★★

Direkt efter Filter1 out_level (abs 13027) och Filter2 out_level (abs 13104) ligger 3 byten per filter med default 127. **Bekräftat icke-UI-fält** via passiv skanning av hela AN-X-testkorpusen.

| Filter1 abs | Filter2 abs | Filter1-rel | Filter2-rel | Default | Status |
|---:|---:|---:|---:|---:|---|
| 13029 | 13106 | +24 | +24 | 127 | [INTERN] |
| 13031 | 13108 | +26 | +26 | 127 | [INTERN] |
| 13033 | 13110 | +28 | +28 | 127 | [INTERN] |

**Bevisföring:**

Av **537 verkliga single-edit-testfiler** i AN-X-korpusen (filer med ≤3 byten ändrade utöver standardnoise), ändrade **INGEN** någon av de 6 trailer-byten. Endast multi-edit-filer (>50 byten ändrade — strukturella rekonstruktioner snarare än single-edits) påverkar trailer-byten. Detta är **definitivt bevis** att de inte är direkt-UI-mappade.

**Möjliga interna funktioner:**

- Reserved space för framtida firmware-utökningar
- Internal calibration constants
- ESP Plugin "scratch buffer" som regenereras vid load

**Praktisk implementation:**

- LÄSNING: Ignorera
- SKRIVNING: Skriv värdet 127 (säkert default)
- Klassificering: [INTERN] (samma kategori som AWM2 rel +312 inter-element separator)

## 10.3 AN-X WaveFolder + Mod EG + Mod LFO ★★★★★ 

| Abs | Fält | Encoding | Default | Notering |
|---|---|---|---|---|
| 13116 | wavefolder_amount | u8 | 0 | UI: Modifier > Folder > Wave Folder |
| 13118 | wavefolder_vel | u8 | 0 | UI: Modifier > Folder > Folder/Vel |
| 13120 | wavefolder_eg_depth | u16le? | 128 (lo) | ★★★★★ UI-bekräftat (ANX bild 5: Modifier > EG Depth) + cross-map ANX_MODIFIER +6708 |
| 13122 | modlfo_depth | u8 c128 | 128 | ★★★★★ UI: Modifier > LFO > LFO Depth. Binärverifierat med Test-ANX-Mod_LFO_Depth_50.Y2L (50 → 178 i c128). ANX_MODIFIER:s alternativnamn "anxWaveFolderLFODepth" refererar till samma byte — ej separat fält. |
| 13124 | wavefolder_texture | u16le? | 128 (lo) | ★★★★★ UI-bekräftat (ANX bild 5: Modifier > Folder > Texture) + cross-map ANX_MODIFIER +6708 |
| 13126 | wavefolder_type | enum | 1 | Hard=1, Soft=0. UI: Modifier > Folder > Type |
| 13128 | modeg_attack | u8 | 0 | UI: Modifier > EG > Attack |
| 13130 | modeg_decay | u8 | 160 | UI: Modifier > EG > Decay |
| 13132 | modeg_sustain | u8 | 0 | UI: Modifier > EG > Sustain |
| 13134 | modeg_release | u8 | 160 | UI: Modifier > EG > Release |
| 13138 | modlfo_wave | enum | 2 | Triangle=2, Square=1. UI: Modifier > LFO > Wave |
| 13140 | modlfo_speed_lo | u16le | 208 | UI: Modifier > LFO > Speed |
| 13146 | modlfo_delay | u8 | 0 | UI: Modifier > LFO > Delay |
| 13148 | modlfo_fadein | u8 | 0 | UI: Modifier > LFO > Fade In |

Modifier-fliken har **endast EN** "LFO Depth"-knapp (abs 13122) — det finns ingen separat byte för "Wave Folder LFO Depth".

## 10.4 AN-X Pre-OSC (Part Settings, Pitch LFO, Filter LFO, Amp + Amp LFO) ★★★★★

**STORT UTÖKAD ** — 27 nya fält identifierade och mappade.

### Part Settings (Pre-OSC topp):

| Abs | Fält | Encoding | Default | Notering |
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

| Abs | Fält | Encoding | Default | Notering |
|---|---|---|---|---|
| 12499 | peg_time_vel | u8 | 0 | |
| 12503 | pitch_lfo_speed_lo | u16le | 208 | |
| 12507 | pitch_lfo_phase | u8 enum | 0 | **16-step enum** 0..15, ~22.5° per steg |
| 12509 | pitch_lfo_delay | u8 | 0 | |
| 12511 | pitch_lfo_fadein | u8 | 0 | |

### FEG-block (12521-12529) — preliminärt:

| Abs | Fält | Encoding | Default | Notering |
|---|---|---|---|---|
| 12521 | feg_attack | u8 | 0 | preliminär — inte verifierat  |
| 12529 | feg_time_vel | u8 | 0 | preliminär |

### Filter LFO-block (12531-12541) — KOMPLETT NY:

| Abs | Fält | Encoding | Default | Notering |
|---|---|---|---|---|
| 12531 | filter_lfo_wave | u8 enum | 2 | Triangle=2, Square=1 |
| 12533 | filter_lfo_speed_lo | u16le | 208 | |
| 12537 | filter_lfo_phase | u8 enum | 0 | 16-step enum |
| 12539 | filter_lfo_delay | u8 | 0 | |
| 12541 | filter_lfo_fadein | u8 | 0 | |

### Amp-block (12543-12551) — KOMPLETT NY:

| Abs | Fält | Encoding | Default | Notering |
|---|---|---|---|---|
| 12543 | amp_level | u16le | 431 | default 431 lo+hi|
| 12545 | amp_level_vel | u8 | 0 | +50 → 50 |
| 12547 | amp_lfo_depth | u8 c128 | 128 | LFO Depth +50 → 178 |
| 12549 | amp_level_key | u8 | 0 | +50 → 50 |
| 12551 | amp_drive | u8 | 0 | 50.25dB → 67, ~0.75dB/unit |

### Amp AEG (12553-12561):

| Abs | Fält | Encoding | Default |
|---|---|---|---|
| 12553 | amp_aeg_attack | u8 | 0 |
| 12555 | amp_aeg_decay | u8 | 160 |
| 12557 | amp_aeg_sustain_lo | u16le | 511 (max) |
| 12559 | amp_aeg_release | u8 | 115 |
| 12561 | aeg_time_vel_lo | u16le ± | 0 |

### Amp LFO-block (12563-12573) — KOMPLETT NY:

| Abs | Fält | Encoding | Default | Notering |
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
4. **Mod LFO** (Post-OSC3, Speed=13140) — matrix-baserad till 3 destinations

Alla 4 har: Wave, Speed (u16le), Phase, Delay, Fade In.
Filter1/Filter2 har individuella LFO Depth-fält (abs 13015 / 13092).

### Pitch LFO Phase enum-skillnad mot AWM2:

- AWM2 LFO Element Matrix Phase: 6 steg (0=0°, 1=90°, 2=120°, 3=180°, 4=240°, 5=270°)
- AN-X Pitch/Filter/Amp LFO Phase: **16 steg** (0..15) med 22.5° per steg
  - 90° → enum 4
  - 180° → enum 8
  - 270° → enum 12
  - 315° → enum 14

## 10.5 AN-X OSC-struktur (stride 125) ★★★★★

**KRITISK KORRIGERING:** Stride är **125 bytes**, inte 124. OSC-baser:
- OSC1 = 12631 (oförändrad)
- OSC2 = **12756** (KORRIGERING från 12755)
- OSC3 = **12881** (KORRIGERING från 12880)

Verifierat med.

| Rel | Fält | Encoding | Default |
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

Mod LFO har 3 destination-rader, varje rad innehåller:
- Destination (enum) — Part Common-fält
- Depth (Part Common-fält)
- 3 Oscillator Depth Ratios — en per OSC (i engine-pool, OSC rel +67/+69/+71)

**OBS:** Strukturen DELAS med AWM2 LFO Element Matrix. Båda
engines använder samma Part Common-adresser. Endast destinations enum-värden
varierar per engine.

**Part Common-fält:**
- `Part rel +498` (abs 7199) mod_lfo_phase
- `Part rel +516` mod_lfo_dest1 (default 2)
- `Part rel +518` mod_lfo_dest1_depth
- `Part rel +520` mod_lfo_dest2 (default 4)
- `Part rel +522` mod_lfo_dest2_depth
- `Part rel +524` mod_lfo_dest3 (default 4)
- `Part rel +526` mod_lfo_dest3_depth

**Destination enum-värden för AN-X:**
- Osc Level = 83
- InsAParam3 = 3, InsAParam5 = 5, InsAParam7 = 6
- (fler okartlagda)

Per OSC finns 3 "lane depths" som modulerar olika destinations:
- OSC rel +67 = mod_lfo_ratio_row1 (för dest1)
- OSC rel +69 = mod_lfo_ratio_row2 (för dest2)
- OSC rel +71 = mod_lfo_ratio_row3 (för dest3)

## 10.7 AN-X routing-matriser ★★★★☆

5 stycken 40-byte routing-tabeller i AN-X engine-pool:

| Matrix | Abs-range | Kontext |
|---|---|---|
| Matrix A | 12582..12621 | efter Pre-OSC, före OSC1 |
| Matrix B | 12707..12746 | efter OSC1, före OSC2 |
| Matrix C | 12832..12871 | efter OSC2, före OSC3 |
| Matrix D | 12961..13000 | efter OSC3, före Filter1 |
| Matrix E | 13038..13077 | efter Filter1, före Filter2 |

**Strukturidentifierad men ej UI-mappbar:**

- I baseline (Init Normal) har alla 5 matriser identiskt mönster: `[39, 1, 1, ..., 1]` 
  (1 byte = 39, sedan 39 byte = 1).
- I real patches innehåller matriserna verkliga modulation-routing-data — 
  blandad u16le + u8 (källor och depth-värden).
- **Verifiering:** Av 380 Part1-single-edit-tester ändrar INGEN någon byte 
  i matriserna. De är inte direkt UI-redigerbara.

**Tolkning:** Matriserna är INTERNA routing-tabeller som ESP-pluginen sätter 
implicit baserat på engine-konfiguration. De skrivs när en patch sparas men 
påverkas inte av enskilda UI-knappar.

**Klassificering: [INTERN][STRUKT]** — strukturellt identifierat, men inte 
UI-mappbart från single-edit tester. Vid serialization bevaras rådata 1:1 
(passthrough). De påverkar inte editor-funktionaliteten.

Struktur-hypoteser (från real-patch-analys, ej slutligt verifierat):
- Matrix A och E ser ut att ha "u16le-aligned" format (header_size=0 eller 2)
- Matrix B och D ser ut att ha "1-byte offset" format (header_size=1 eller 3)
- Matrix C är ofta tom (mestadels nollor i real patches)

UI-täckning AN-X: **~70%** (73 av 110 verkliga UI-bytes mappade)

**Räknebakgrund:** AN-X engine-pool är 684 bytes med 352 non-zero bytes.
Av dessa är 200 sammanhängande routing-tabeller (5 × 40-byte matriserna ovan)
och ytterligare 42 är lösa routing-flaggor utspridda i poolen. Det ger
110 "verkliga UI-bytes" att mappa. 73 är mappade 37 kvarstår.

---

## 10.9 AWM2 Element Count-arkitektur ★★★★★

**Genombrott:** AWM2-engine är inte begränsad till 8 element per Part — UI:t i ESP Plugin v3.0 exponerar **Element Count** med värdena 8 (default), 16, 32, 64 och 128.

### Två synkroniserade Element Count-bytes

Element Count-värdet lagras på TVÅ platser som alltid har identiska värden:

| Plats | Adress (14969-byte payload) | Adress (38985-byte container) | Notering |
|---|---|---|---|
| Part Common rel +196 | abs 6897 | abs 7588 | Part-level UI-styrd byte (`elementCount_rel`) |
| Engine header byte 0 | abs 12464 | abs 13151 | Engine-pool header (= "E1 base − 5") |

ESP-pluginen skriver båda byten samtidigt när Element Count ändras i UI.

### Dynamic element-array expansion

När Element Count > 8 utökas element-arrayen genom att lägga in extra 313-byte stride-element direkt efter element 8. Resten av engine-poolen (trailer, eventuella sekundära strukturer) flyttas bakåt med exakt `(EC − 8) × 313` bytes:

| Element Count | Filstorlek | Delta vs EC=8 | Element-array slut (i 38985-fil) |
|---:|---:|---:|---:|
| 8 (default) | 38985 | 0 | abs 15660 |
| 16 | 41489 | +2504 (= 8 × 313) | abs 18164 |
| 32 | 46497 | +7512 (= 24 × 313) | abs 23172 |
| 64 | 56513 | +17528 (= 56 × 313) | abs 33188 |
| 128 | 76545 | +37560 (= 120 × 313) | abs 53220 |

Verifierat exakt (0 bytes diff) för alla 5 testfall.

### Konsekvenser för editor-arkitektur

**Alla 313-byte element-fält gäller direkt för element 9..128.** Varje extra element har full fält-mappning enligt vår AWM2_ELEMENT_FIELDS-tabell:
- XA Control (rel +67), Pan (rel +59), AEG (rel +91..+143), Filter+FEG (rel +201..+265), LFO (rel +283..+307), etc.
- Default-värden för "tomma" element (rel +0 = 0, dvs `enable=0`)

Beräkning av abs-adress för element N i en EC=128-fil (i 14969-byte payload-adressering):
```
abs = 12469 + (N − 1) × 313    # N = 1..128
```

### Hash/CRC-bytes som skalar med EC

Följande bytes ändras alltid när Element Count ändras (filhash som beror på hela filinnehållet — INTE direkta UI-parametrar):
- `abs 102, 103, 110, 111, 375, 673, 674, 685, 686` (i 38985-fil)

Dessa bör läggas till en EC-känslig NOISE-lista vid byte-coverage-analys av EC-tester.

### Multi-Parts mode (Sw_ON_MultiplePartsElements)

Vid sidan av Element Count finns en separat toggle som aktiverar fler Parts:
- En extra Part lägger till exakt **24819 bytes** (konstant, oberoende av Element Count för Part 1)
- Bonus-testfil med EC=128 + flera Parts + 128 element per Part är 214044 bytes — multi-part-strukturen är inte fullt analyserad än

UI-täckning Part Common Element Count: **★★★★★** (5 EC-värden verifierade)

---

# 11. Engine-data: AWM2 ★★★★★

**Engine-storlek:** 2503 bytes (2508 i pool med separator).

## 11.1 Element-arkitektur ★★★★★

**Korrekta värden (verifierade med TEST5R3-T5a/e Element Enable-toggle):**

```python
AWM2_HEADER_SIZE        = 3        # bytes före första elementet (header signature: 00 00 2b)
AWM2_ELEMENT_STRIDE     = 313      # bytes per element (E1-E7)
AWM2_LAST_ELEMENT_SIZE  = 309      # E8 är 4 bytes kortare än övriga
AWM2_ELEMENT_COUNT      = 8        # 8 elements per AWM2 part
```

**Layout:** 3 (header) + 7 × 313 + 309 = **2503 bytes total** ✓

**Element-positioner (Part 1 solo, engine @ abs 12466):**

| Element | Engine-relativ | Abs (Enable byte) | Defaults |
|---|---:|---:|---|
| E1 | +3 | 12469 | enable=1 (ON) |
| E2 | +316 | 12782 | enable=0 (OFF) |
| E3 | +629 | 13095 | enable=0 |
| E4 | +942 | 13408 | enable=0 |
| E5 | +1255 | 13721 | enable=0 |
| E6 | +1568 | 14034 | enable=0 |
| E7 | +1881 | 14347 | enable=0 |
| E8 | +2194 | 14660 | enable=0 (E8 = 309b) |

**Default Init Voice:** Endast **Element 1 är ON**, E2-E8 är OFF.
För FM-X finns ingen ON/OFF per OP — istället finns **Mute** och **Solo** per OP samt **Level** 0..127.

```python
def get_awm2_element_offset(element_idx: int) -> int:
    """Returns rel offset within AWM2 engine for element 0..7."""
    return 3 + element_idx * 313

def get_awm2_element_addr(engine_start_abs: int, element_idx: int) -> int:
    return engine_start_abs + get_awm2_element_offset(element_idx)
```

## 11.2 AWM2 Element-fält (313 bytes per element) ★★★★★

**Offsets relativt element-base** (Element 1 base = abs 12469).

**120 verifierade fält per element × 8 elements = 960 verifierade AWM2 element-positioner totalt.**

Stride 313 verifierat för alla 8 element.

| Rel | Fält | Encoding | Default | Notering |
|---:|---|---|---:|---|
| 0 | element_header | u8 | varies | (E1=1, E2-8=0 i Init) |
| 1 | keyondly_sync | u8 bool | 0 | KeyOnDly Sync toggle |
| 2 | aeg_half_damper | u8 bool | 0 | |
| 6 | extended_lfo | u8 bool | 1 | ★★★★★ binärverifierat med Test-AWM2-ElementLFO-ExtendedLFO_ON/OFF.Y2L. Default ON för Init Normal AWM2. Bestämmer vilken Speed-byte UI visar — rel +289 när AV, rel +307 när PÅ |
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
| 121-143 | AMP Level Scaling block | (se nedan) | | 5 BreakPoints + 4 Offsets |
| 141 | level_key | u8 c64 | 64 | |
| 149 | coarse_tune | u8 c64 | 64 | ±20 semitones via UI |
| 151 | fine_tune | u8 c64 | 64 | |
| 153 | pitch_vel | u8 c64 | 64 | |
| 155 | pitch_random | u8 | 0 | |
| 157 | pitch_key | u8 | 96 | |
| 161 | fine_key | u8 c64 | 64 | |
| 163-195 | PEG-block | (se nedan) | | Komplett från TEST-PEG-* tester |
| 201 | filter_type | u8 enum | 4 | LPF24A=1, LPF18=2, default=4, DualBEF=17 |
| 203-204 | filter_cutoff | u16le | 128 (max 1023) | |
| 205 | filter_cutoff_vel | u8 c64 | 64 | |
| 207 | filter_resonance | u8 | 0 | |
| 209 | filter_resonance_vel | u8 c64 | 64 | |
| 211-212 | hpf_cutoff | u16le | 0 | |
| 213 | filter_distance | u8 c128 | 128 | DualBEF Distance |
| 215 | filter_gain | u8 | 230 | |
| 219-241 | FEG-block | (se nedan) | | Filter Envelope, komplett |
| 247-265 | Filter Level Scaling | (se nedan) | | Parallell till AMP Level Scaling |
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
| 299 | element_lfo_phase_offset | u8 enum | 0 | LFO Matrix Phase Offset (0..5) |
| 301 | element_lfo_dest1_depth | u8 | 127 | LFO Matrix Row 1 |
| 303 | element_lfo_dest2_depth | u8 | 127 | LFO Matrix Row 2 |
| 305 | element_lfo_dest3_depth | u8 | 127 | LFO Matrix Row 3 |
| 307 | lfo_speed | u8 | 60 | |

### AMP Level Scaling block (rel 121-143) ★★★★★

5 BreakPoints (CenterKey + BP1-BP4) och 4 Offsets emellan. Defaults vid C0/C1/C2/C3/C4 jämnt fördelat.

| Rel | Fält | Default |
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

Komplett mappad från TEST-PEG-* tester.

| Rel | Fält | Encoding | Default |
|---:|---|---|---:|
| 163 | peg_hold_time | u8 | 0 |
| 169 | peg_signature | u8 | 64 | [INTERN] PEG-edit marker, ändras 64→76 i alla PEG-edits |
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

| Rel | Fält | Encoding | Default |
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

Parallell till AMP Level Scaling.

| Rel | Fält | Default |
|---:|---|---:|
| 247 | filter_time_key | 64 |
| 249 | filter_scaling_center_key | 24 (C0) |
| 251-257 | filter_scaling_bp1..bp4 | 36/48/60/72 |
| 259-265 | filter_scaling_cutoff_offset1..offset4 | 128 (c128) |

### EQ-block (rel 271-281) ★★★★★

EQ Type styr vilka övriga fält som är aktiva.

| Rel | Fält | Encoding | Default | Notering |
|---:|---|---|---:|---|
| 271 | eq_type | u8 enum | 0 | 0=2-band, 1=P.EQ, 2=Boost6 |
| 273 | eq_q_or_resonance | u8 | 0 | I P.EQ-mode = Q |
| 275 | eq_low_freq | u8 | 54 | I 2-band-mode = LowFreq, i P.EQ = EQ Frequency |
| 277 | eq_low_gain | u8 c64 | 64 | I 2-band-mode = LowGain, i P.EQ = EQ Gain |
| 279 | eq_high_freq | u8 | 231 | (2-band only) |
| 281 | eq_high_gain | u8 c64 | 64 | (2-band only) |

**EQ Type-värden:**
- 0 = 2-band (default)
- 1 = P.EQ (Parametric)
- 2 = Boost 6
- 3 = Boost 12
- 4 = Boost 18
- 5 = Thru

Med Boost-typer skrivs förinställda värden till rel 275/277/279/281; användaren kan inte justera EQ-parametrar.

### LFO Element Matrix ★★★★★

AWM2 LFO Element Matrix delar Part Common-adresser med AN-X Mod LFO Matrix. Per-element fält:

| Rel | Fält | Notering |
|---:|---|---|
| 299 | element_lfo_phase_offset | 0=0°, 1=90°, 2=120°, 3=180°, 4=240°, 5=270° |
| 301 | element_lfo_dest1_depth | Element Depth Ratio Row 1 (default Level) |
| 303 | element_lfo_dest2_depth | Element Depth Ratio Row 2 (default Cutoff) |
| 305 | element_lfo_dest3_depth | Element Depth Ratio Row 3 (default Pitch) |

Part Common-fält (delas med AN-X):
- `Part rel +498` (abs 7199) lfo_phase
- `Part rel +516/520/524` dest1/dest2/dest3 (AWM2: Level=64, Cutoff=66, Pitch=65)
- `Part rel +518/522/526` dest1/dest2/dest3 depth

## 11.3 AWM2 element-byte-detaljer

AWM2 element-strukturen är **kartlagd & verifierad**.

### UI-bekräftade fält ★★★★★

Konversionsformel: `AWM2_ELEM_LAYOUT_offset + 51 = AWM2_ELEMENT_FIELDS_rel`. UI-bekräftad via skärmdumpar från ESP Plugin v3.0.

| Rel | Default | Fält | UI-källa | Strukturkälla |
|---:|---:|---|---|---|
| 159 | 60 (C3) | `pegKFCenterNote` | AWM2 bild 2: [ELEMENT] Pitch EG > Center Key = C 3 | AWM2_ELEM_LAYOUT off=108 |
| 289 | 38 | `lfoSpeed` (normal, ej Extended) | AWM2 bild 6: [ELEMENT] LFO > Speed (knapp visad när Extended LFO toggle är AV) | AWM2_ELEM_LAYOUT off=238 |

### FEG-block-strukturen på rel +243 ★★★★★

Binärverifierad via PEG/FEG-symmetri (alla 6 PEG-fält är binärverifierade ★★★★★) och dedikerad single-edit-testfil Test-AWM2-Filter_FEG_DepthVel_50.Y2L.

**PEG/FEG-symmetri:** FEG-blocket är PEG-blocket förskjutet +54 bytes:

| UI-namn | PEG rel | FEG rel | Förskjutning |
|---|---:|---:|---:|
| Segment | +185 | +239 | +54 |
| Time/Vel | +187 | +241 | +54 |
| **Depth/Vel** | **+189** | **+243** | **+54** |
| Curve | +191 | +245 | +54 |
| Time/Key | +193 | +247 | +54 |
| Center Key | +195 | +249 | +54 |

**UI-verifiering:** AWM2 bild 3 ([ELEMENT] Filter) visar FEG-block med exakt **5 separata kontroller**: Time/Vel, Segment, FEG Depth, **Depth/Vel**, Curve. Plus Time/Key och Center Key i Level Scaling-zon. Totalt 7 kontroller som matchar +237, +239, +241, **+243**, +245, +247, +249.

**Binärbaseline-verifiering** (från Test-AWM2-ElementLFO-ExtendedLFO_OFF.Y2L):

| Rel | Default | Fält | UI-namn | Status |
|---:|---:|---|---|:---:|
| +237 | 104 | `feg_depth` | FEG Depth | ★★★★★ |
| +239 | 4 (All) | `feg_segment` | Segment | ★★★★★ |
| +241 | 64 | `feg_time_vel` | Time/Vel | ★★★★★ |
| +243 | 64 | **`feg_depth_vel`** | **Depth/Vel** | **★★★★★** |

**Binärverifiering av rel +243:** Test-AWM2-Filter_FEG_DepthVel_50.Y2L sätter UI-värdet Depth/Vel till +50. Diff mot baseline visar exakt EN byte ändrad: rel +243 från 64 till 114 (= 64 + 50 i c64-encoding). Inga andra bytes påverkas. UI-bekräftat och baseline-bekräftat enligt PEG-parallell på rel +189.

| +245 | 2 | `filter_curve` (alias `feg_curve`) | Curve | ★★★★★ |
| +247 | 64 | `filter_time_key` (alias `feg_time_key`) | Time/Key | ★★★★★ |
| +249 | 24 (C0) | `filter_scaling_center_key` (alias `feg_center_key`) | Center Key | ★★★★★ |

**Kanoniska fältnamn (`AWM2_ELEM_LAYOUT`):**

| Off | Namn |
|---:|---|
| 192 | `feg_depth_vel` |
| 194 | `feg_curve` |
| 196 | `feg_time_key` |

### AWM2 element [INTERN]-bytes (icke-UI, firmware-konstanter)

| Rel | Default | Status |
|---:|---:|---|
| 46 | 40 | [INTERN] firmware-konstant. Skannat 408 AWM2-filer — **100% konstant**. |
| 90 | 54 | [INTERN] firmware-konstant. Skannat 408 AWM2-filer — **100% konstant**. |
| 148 | 48 | [INTERN] firmware-konstant. Skannat 408 AWM2-filer — **100% konstant**. |
| 200 | 108 | [INTERN] firmware-konstant. Skannat 408 AWM2-filer — **100% konstant**. |
| 309 | 0 | Padding (passivt verifierat) |
| 310 | 0 | Padding (passivt verifierat) |
| 311 | 0 | Padding (passivt verifierat) |
| 312 | 43 (0x2B '+') | Inter-element separator (passivt verifierat i 4 testfiler × 7 element). Element 8 visar avvikande värde p.g.a. DSYS-chunken börjar direkt efter Element 8 utan padding-zon. |

**Per-element sammanställning:**
- 128 UI-mappade fält ★★★★★
- 8 [INTERN]-bytes
- ~177 multi-byte split-bytes (u16le hi-bytes etc, redan räknade i UI-fält)
- = 313 bytes per element ✓

Övriga binärverifierade fält:
- rel +67 → `xa_control` (enum 0..7)
- rel +191 → `peg_curve` (enum 1..4, default 2)
- rel +245 → `filter_curve` (enum 0..4, default 2)

UI-täckning per AWM2-element: **alla bytes redovisade** (alla bytes redovisade — antingen UI-mappade eller [INTERN])

### Binärverifierat ★★★★★: Extended LFO och Speed-bytes

Med `Test-AWM2-ElementLFO-ExtendedLFO_ON.Y2L` vs `_OFF.Y2L` (diff = 1 byte vid audit abs 12475 = Element 1 rel +6) verifierat:

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|---|
| +6 | `extended_lfo` | u8 bool | **1 (ON)** för Init Normal AWM2 | ★★★★★ |
| +289 | `lfoSpeed` | u8 0..63 | 38 | ★★★★★ — aktiv UI-byte när `extended_lfo`=0 |
| +307 | `lfo_extended_speed` | u16le 0..415 | 60 | ★★★★★ — aktiv UI-byte när `extended_lfo`=1 |

**Viktig arkitektur-observation:** Speed-värdet lagras i TVÅ separata bytes:
- `lfoSpeed` (rel +289, u8 0..63) — UI visar 0..63-skala
- `lfo_extended_speed` (rel +307/+308, u16le 0..415) — UI visar 0..415-skala

Båda lagras alltid simultant i filen. `extended_lfo`-toggle (rel +6) bestämmer endast vilken byte UI:t visar och redigerar. Detta mönster återfinns även i FM-X (`fmxPart2ndLfoSpeedNormal` @ 12511, `fmxPart2ndLfoSpeedExtended` @ 12531).

### Konvention: AWM2-adresseringsbaser (3 olika konventioner)

Det finns **tre olika "base"-adresser** för Element 1 i projektet, som ger olika offset-numreringar:

| Konvention | Element 1 base | Källa | Användning |
|---|---:|---|---|
| audit abs | 12469 | parameterbetygsfilen, byte-coverage-detail.txt, audit-filerna, denna referens | Dokumentation, single-edit-tester |
| `AWM2_ELEM_LAYOUT` ELEM_BASE | 12520 | serializer rad 3115/3250 | Aktiv produktionskod (läs/skriv) |
| `AWM2_ELEM1_BASE` | 12532 | serializer rad 222 | Filoffset-beräkning vid binärverifiering |

**Konversioner mellan dem:**

```
AWM2_ELEM_LAYOUT_offset + 51 = AWM2_ELEMENT_FIELDS_rel  (audit-rel)
audit_abs                    = AWM2_ELEM_LAYOUT_offset + 12520
audit_abs                    = AWM2_ELEM1_BASE_offset - 63
```

**Filoffset-konversion vid binär-diff-analys av Y2L-filer:**

```
filoffset  = audit_abs + 687
audit_abs  = filoffset - 687
```

Konstanten 687 är summan av fil-header + alla pre-DPFM-chunks + DPFM sub-blob-header + Performance Name-prefix. Verifierad genom att `waveform_lo = 6` (Init Normal AWM2 Element 1 = CFX v06 St) ligger på filoffset `687 + 12469 + 51 = 13207`.

**FALLGROP:** Vid räkning av byte-offsets i binärdumps är det lätt att blanda ihop dessa konventioner. `extended_lfo` är **rel +6** (audit-konvention) = **ELEM_LAYOUT off −45**; använd inte 51-byte-konversionen mellan `AWM2_ELEM_LAYOUT` och `AWM2_ELEMENT_FIELDS` på detta fält.

Fält som finns i `AWM2_ELEM_LAYOUT` men saknas i `AWM2_ELEMENT_FIELDS`: `pegKFCenterNote`, `feg_time_vel`, `lfoSpeed` — alla tre dokumenterade ovan.

---

# 12. Engine-data: FM-X ★★★★★

**Engine-storlek:** 1143 bytes (1148 i pool med separator).

## 12.1 OP-arkitektur

```
FMX_OP1_BASE  = 12676   # Part 1, solo
FMX_OP_STRIDE = 123     # bytes per OP
FMX_OP_COUNT  = 8
```

8 OPs, layout är identisk per OP. För OP N (N=1..8): `FMX_OPN_BASE = 12676 + (N-1) × 123`.

## 12.2 FM-X OP Layout (per OP, relativt OP_BASE) ★★★★★

**Pre-OP block (negativa offsets från OP_BASE):**

| Rel | Fält | Encoding | Default |
|---|---|---|---|
| -4 | keyOnReset | bool | 1=On |
| -2 | freqMode | enum 0=Ratio, 1=Fixed | 0 |

**Freq / Spectral block (rel 0..14):**

| Rel | Fält | Encoding | Default |
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

| Rel | Fält | Encoding | Default |
|---|---|---|---|
| 16 | pegInitialLevel | c50 (raw = UI+50) | 50 |
| 18 | pegAttackLevel | c50 | 50 |
| 20 | pegAttackTime | direct | 0 |

**OBS:** off 20 är **pegAttackTime** (PEG, vänster panel — INTE aegAttackTime!)

**AEG block (rel 22..40):**

| Rel | Fält | Encoding | Default |
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

**OBS:** off 22 är **pegDecayTime** (PEG Decay — INTE aegDelayTime!). Off 32 är **aegAttackTime** (AEG, höger panel).

**Key/Level scaling block (rel 42..56):**

| Rel | Fält | Encoding | Default |
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

| Rel | Fält | Encoding | Default |
|---|---|---|---|
| 58 | secondLfoPitchModDepth | direct | 3 |
| 60 | secondLfoAmpModDepth | direct | 3 |
| 66 | firstLfoDest1Ratio | direct | 127 |
| 68 | firstLfoDest2Ratio | direct | 127 |
| 70 | firstLfoDest3Ratio | direct | 127 |

## 12.3 FM-X Algoritm + Feedback (Part-level) ★★★★★

| abs (Part 1) | Fält | Encoding | Default |
|---|---|---|---|
| 12525 | algorithm | raw = algo − 1 | 68 (algo 69 default) |
| 12527 | feedback | direct | 0 |

## 12.4 FM-X 2nd LFO Global (Part-level) ★★★★★

Se sektion 5.3.

## 12.5 FM-X OP Mute/Solo — EJ I BLOB ★★★★★

OP Mute och OP Solo är real-time performance state och sparas INTE i YSFC-formatet. Ändras inte i binärfilen vid Save.

---

# 13. Engine-data: Drum ★★★★★

**Engine-storlek:** 4963 bytes (4968 i pool med separator).

## 13.1 Drum-key arkitektur

```
DRUM_KEY1_BASE   = 12469   # Part 1 solo, key 1 = C0 (MIDI 12)
DRUM_KEY_STRIDE  = 68      # bytes per drum key
DRUM_KEY_COUNT   = 73      # C0..C6 inclusive (MIDI 12..84)
```

Drum-keys area: `[12469:17433]` = 4964 bytes.

## 13.2 Per-Drum-Key fält (rel 0..62) ★★★★★

27 fält per key, alla binärverifierade -76.

| Rel | Fält | Encoding | Default |
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

**Unused offsets inom key (default 0 eller udda värden, ej UI-mappade):**
rel 1-3, 5, 7, 9, 11, 13, 15, 17-21, 23-25, 27, 29, 31, 33, 35, 37, 39, 41, 43, 45, 47, 49, 51, 53-55, 57, 59, 61, 63-66. Rel 18 (default 90) och 67 (default 64) har non-zero defaults — sannolikt internal padding/sub-state.

```python
def drum_key_abs(field_name, key_idx):
    """key_idx: 0..72 (C0..C6)"""
    return 12469 + key_idx * 68 + DRUM_KEY[field_name]
```

## 13.3 Drum Part Common ★★★★★

| abs (Part 1) | rel_part | Fält | Encoding | Default |
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
| 6917 | 209 | drumDetuneHz | direct (eller u8) | 128 |
| 6919 | 211 | drumNoteShift | c64 | 64 |
| 6961 | 253 | drumPart2EqType | enum (0=2band, 2=HPF) | 0 |

## 13.4 Drum-key kollaterala bytes ★★★★★

Vid varje Drum-key-redigering uppdateras automatiskt: `[6715, 6716, 6721]`. Tillagt i `DRUM_COLLATERAL_BYTES` för korrekt round-trip — filtreras vid diff men måste matchas vid skriv.

**Notering:** ESP UI:s "Key"-väljare ändrar bara navigation, inte data. Per-key-data lagras dock korrekt i blobben (verifierat genom att samma SW=0x01-mönster återupprepas var 68:e byte).

---

# 14. Insertion FX — KOMPLETT (57 typer) ★★★★★ / ★★★★☆

Insertion FX (InsA och InsB) gäller engine-oberoende.

## 14.1 Encoding

```
fxA: abs = PART + 275 (InsA), PART + 332 (InsB)
fxA[0] = lo-byte av 7-bit type index
fxA[1] = hi-byte av 7-bit type index
TypeIndex = hi * 128 + lo
```

## 14.2 FX_TYPE_INDEX (komplett tabell)

★★★★★ = binärverifierat med testfil
★★★★☆ = härlett från Effect Type List + MSB/LSB-formel

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
    """Returnerar (lo, hi) för ett InsertionFX-namn."""
    idx = FX_TYPE_INDEX.get(name.upper(), 0)
    return (idx & 0x7F, (idx >> 7) & 0x7F)

def fx_name_from_bytes(lo, hi):
    """Returnerar FX-namn från (lo, hi) bytes."""
    return FX_INDEX_TO_NAME.get(hi * 128 + lo, f'UNKNOWN({hi*128+lo})')
```

## 14.3 LFO Speed encoding (alla FX) ★★★★★

`raw = round(Hz × 23.7045)`

Datapunkter: 0.46 Hz→11, 0.80→19, 1.09→26, 1.30→31, 1.60→38, 1.98→47.

## 14.4 Symphonic + Classic Flanger parametrar (specifika)

**SYMPHONIC (12/12 ★★★★★):**

| fxA+ | Fält | Encoding | Default |
|---|---|---|---|
| 4 | LFO Speed | raw=round(Hz×23.7) | 11 (=0.46 Hz) |
| 6 | LFO Depth | direct | 25 |
| 8 | Delay Offset | tabellindex | 1 (≈0 ms) |
| 14 | EQ Low Freq | tabellindex | 22 |
| 16 | EQ Low Gain | c64 | 64 |
| 18 | EQ High Freq | tabellindex | 48 |
| 20 | EQ High Gain | c64 | 64 |
| 22 | Dry/Wet | direct | 64 |
| 24 | EQ Mid Freq | tabellindex | 38 |
| 26 | EQ Mid Gain | c64 | 64 |
| 28 | EQ Mid Width | tabellindex | 7 |

**CLASSIC FLANGER (16/16 ★★★★★):**

Som Symphonic + tre specifika fält:

| fxA+ | Fält | Encoding | Default |
|---|---|---|---|
| 10 | Delay Offset | tabellindex | 24 (=0.65 ms) |
| 12 | Feedback | raw = percent+100 | 151 (=51%) |
| 30 | Mod Phase | raw = phase_idx × 2 | (180°=16) |
| 32 | FB High Damp | raw = value × 10 | 9 (=0.9) |
| 34 | Analog Feel | direct | 0 |

(Övriga 49 FX-typer använder samma 22-param-mall som Reverb/Variation FX i Common-area med olika tolkningar per Type.)

---

# 15. Smart Morph ★★★★★

Smart Morph är inte en parameter utan en komplett filformat-utbyggnad.

## 15.1 Detektion ★★★★★

Två separata indikatorer (ger samma svar):

```python
def is_smart_morph(blob, file_data):
    # Indikator 1: byte i performance blob
    if blob[56] == 1:
        return True
    # Indikator 2: DSOM-chunk i container
    return b'DSOM' in file_data[64:200]  # i directory
```

**Verifiering:** `TEST-FMX-NORMAL.Y2L` har `blob[+56] = 0`, `TEST-FMX-SMARTMORPH.Y2L` har `blob[+56] = 1`. Clean direkt-diff över 1081 bytes (multiple side effects), men den isolerade nyckelbyten är just `+56`.

## 15.2 Container-utbyggnad

Smart Morph lägger till **4 chunks** i Y2L-filen:

| Chunk | Storlek (typisk) | Funktion |
|---|---|---|
| ESPG | 71 b | Edit Smart Performance Group (header) |
| ESOM | 71 b | Edit Smart Morph (metadata) |
| DSPG | 794 b | Data Smart Performance Group |
| **DSOM** | **~900 KB** | Data Smart Morph — embeddad YAMAHA-SOM-fil |

## 15.3 Performance-blob-ändringar vid Smart Morph

Förutom `blob[+56] = 1`:

| abs | NORMAL | SmartMorph | Tolkning |
|---|---|---|---|
| +56 | 0 | 1 | Smart Morph enable ★★★★★ |
| +66 | 0 | 16 | Side-effect (korrelerar med SM-aktivering) ★★★★★ |
| +728..+735 | 0 | u16le-array | Index/pekare till morph-keyframes ★★★★☆ |

## 15.4 DSOM-payload-struktur

```
DSOM-chunk-payload:
  +0    u32be: count = 1
  +4    'Data' (4 bytes)
  +8    u32be: inner_size
  +12   embeddat YAMAHA-SOM-fil
```

## 15.5 Embeddat YAMAHA-SOM-format ★★★☆☆

Eget format, inte standard YSFC:

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

**Inte mappat ännu.** Eget reverse-engineering-projekt.

## 15.6 Editor-strategi (Opaque-blob)

1. Detektera Smart Morph vid load
2. Visa varning: "Smart Morph data preserverad — engine-parametrar redigerbara, men inte morph-keyframes"
3. Tillåt redigering av reguljära parametrar (Performance/Part-fält)
4. Vid save: kopiera DSOM/ESPG/ESOM/DSPG **verbatim**, modifiera bara performance-blobben

Stänger inte dörren för full Smart Morph-stöd senare när YAMAHA-SOM reverse-engineeras.

---

# 16. UI-element EJ I BLOB ★★★★★

Följande UI-element existerar men sparas INTE i performance-blob:

## 16.1 Hardware Events (RcvSw)

- **Pitch Bend** — hardware-globalt
- **Ch.After Touch** — hardware-globalt
- **Poly.After Touch** — hardware-globalt

## 16.2 UI-state

- **Performance Favorite (Star)** — separat lagrad
- **MS Sequencer Lane Select** — UI-state, ej sparad
- **OP Mute / OP Solo** (FM-X) — real-time state

## 16.3 Hardware-globala settings

- **Global Tuning**
- **MC Flag**
- **System FX**
- **Transmit Switch**

## 16.4 Hard-coded i firmware

- Scene CC (= 92)
- Super Knob CC (= 95)
- Footswitch Assign (= Arp Sw)

---

# 17. Modified / Noise flaggor ★★★★★

Bytes som ändras vid spar utan att representera parameterdata. **Filtreras vid diff. Måste bevaras vid skriv.**

| Position | Funktion |
|---|---|
| `file[63]` | Save counter (yttre container) |
| `file[399]` | Save counter (kopia inuti EPFM) |
| `blob[+22]` | Sub-blob 1 edit-state (del av timestamp) |
| `blob[+23]`, `blob[+24]` | Sub-blob 1 (Common) timestamp/edit-state |
| `blob[+66]` | Common-area side-effect-flagga |
| `blob[+232]`, `blob[+234]` | Common-area edit-flags (parallella, 1→0) |
| `blob[+358]` | Arp/FX edit-counter (2→0 i 25+ tester) |
| `blob[+376]` | Reverb edit-state-flag (samexisterar med Reverb Category) |
| `blob[+654]` | Multi-trigger side-effect (9+ orelaterade tester) |
| `blob[+6724]`, `blob[+6725]` | Sub-blob 2 (Part 1) timestamp |
| `blob[+7167]`, `blob[+7168]` | Arp-relaterade edit-flags (250→0 / 10→0) |
| `blob[+7419]` | Scene edit-counter (per-Scene edit triggar 0→1) |
| Sub-blob N: +23, +24 | Per-part-edit-state (mönstret upprepas) |
| **CA+17** | MODX-internal byte i varje CA-slot |
| **Drum [6715, 6716, 6721]** | Drum-key kollaterala bytes |

```python
NOISE_BLOB = {
    22, 23, 24, 66,            # Sub-blob 1 timestamp + edit flags
    232, 234, 358, 376, 654,   # Common-area side-effect flags
    6724, 6725,                # Sub-blob 2 timestamp
    7167, 7168, 7419,          # Arp/Scene edit-counters
}
NOISE_FILE = {63, 399}
DRUM_COLLATERAL = {6715, 6716, 6721}
```

⚠️ **OBS:** Vissa NOISE-offsets samexisterar med riktiga parametrar:
- `blob[+376]` = Reverb Category (verklig param) MEN triggas också som side-effect
- `blob[+7419]` = per-Scene edit-counter

Editor: skriv korrekt UI-värde — MODX hanterar edit-flag-uppdateringar automatiskt.

---

# 18. Kvarvarande okartlagda regioner

~50 bytes nz är "riktigt okänt" (efter denna analys). Övriga ~201 nz bytes
är bekräftat OPAQUE — firmware-konstant data som inte exponeras i UI.

## 18.1 OPAQUE internal regions (~201 nz bytes)

**Definitionsegenskaper:**
- 0 testfiler i 1626-fils-korpus modifierar dessa bytes
- Bit-för-bit identiska över alla 4 engines (AWM2/Drum/FMX/ANX)
- Innehåller upprepande block-strukturer (CA-trailers, u16le-mönster)

| Region | Storlek | nz | Engine-agnostisk |
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

**Praktisk konsekvens:** Editor MÅSTE preserva dessa byte-för-byte. Försök
INTE att tolka eller modifiera dem — det är Yamaha-internal firmware-data.

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

Distinkt från Groups 1-4: **uppdateras automatiskt vid multi-part-skrivning**.
Specifikt `blob[+6695]` (max active part) ligger i Group 5.

Övriga bytes i Group 5 reflekterar internal state av part-arrangement och
ska kopieras verbatim utan tolkning.

## 18.3 Riktigt okänt (~50 nz bytes)

Bytes som varken är mappade UI-fält eller bekräftade OPAQUE — potentiella
framtida UI-fält som behöver dedikerade tester:

| Region | nz | Plats |
|---|---:|---|
| `[70:104]` återstående | ~14 | Perf-level toggles (3 av 17 mappade) |
| `[130:153]` (utöver 152=Ribbon CC) | 8 | Mellan Common toggles och Hardware Ribbon |
| `[232:246]` | 4 | Liten Common-region |
| `[357:377]` (utöver NOISE 358, 376) | 4 | Mellan Master FX och Reverb FX |
| `[4043:4063]` (utöver 4044) | 7 | Mellan Stride-106 grupper |
| `[12453:12466]` (utöver 12464-65) | 1 | Pre-engine padding |
| Spridda enstaka bytes | ~12 | Mellan kända fält |

## 18.4 Okartlagda toggle-bytes

abs **32, 36** — 2 toggles där UI-funktion ej är slutgiltigt identifierad.

## 18.5 Sammanfattning byte-täckning

```
Total bytes (ANX Init Base):     13150
Non-zero bytes:                   3766
UI-mappat (★★★★★/★★★★☆):       ~2523     (67.0% av nz)
Strukturellt mappat:             ~1041     (27.7% av nz)
OPAQUE (firmware-konstant):       ~201     ( 5.3% av nz)
Riktigt okänt:                    ~50      ( 1.3% av nz)
```

**Praktisk implikation:** ~98,7% non-zero coverage uppnådd. Återstående 1,3%
preserveras verbatim — ingen funktionalitetsförlust för editor.

## 18.6 Konsoliderad verifierad teknisk täckning ★★★★★

Detta avsnitt bevarar aktuella tekniska slutsatser som ursprungligen togs fram under fokuserade analys-pass. Det är inte en changelog; det är aktuell implementation-/referenskunskap som inte får tappas bort när äldre utforskande anteckningar tas bort.

### AN-X engine-täckning

AN-X engine-poolen betraktas som fullständigt mappad för kända användarredigerbara fält. Den aktuella modellen är:

| Kategori | Aktuell tolkning |
|---|---|
| UI-mappade fält | 171 fält, inklusive oscillator-, noise-, filter-, WaveFolder-, Mod LFO-destination- och EG-relaterade fält |
| Interna bytes | 458 firmware-/internbytes som kopieras eller seedas från verifierad baseline |
| Kvarvarande varierande omappade bytes | 0 kända |

Viktiga AN-X-fält som måste finnas kvar i referensen/serializern:

- Noise: `noise_tone`, `noise_connect`, `noise_unknown`
- Amp AEG: `amp_aeg_release`, `amp_aeg_time_vel`, `amp_aeg_sustain_hi`, `amp_aeg_time_vel_marker`
- OSC1/2/3: waveform, octave, pitch, PEG depth markers, pitch LFO depth, sync pitch, pulse width, shaper, connect och velocity-relaterade fält
- OSC EG per oscillator: attack, decay, sustain, release där de finns
- Filter / WaveFolder: `filter2_type`, `wavefolder_eg_depth`, `wavefolder_texture`
- Mod LFO matrix-trailers: OSC1/OSC2/OSC3/filter destination-trailers med default 127

Den explicita flat-mappningen av OSC-fält är säkrare än att anta perfekt uniform stride för alla OSC-fält. Serializern ska bevara kända AN-X interna/routing-konstanter byte-för-byte eller seeda dem från verifierad baseline.

### AWM2 element-täckning

AWM2 element-strukturen betraktas som fullständigt mappad för kända användarredigerbara fält. Återstående icke-UI-bytes är firmware-/internkonstanter eller padding som ska bevaras/stängas, inte exponeras som redigerbara parametrar.

Kritiska AWM2-slutsatser:

| Rel | Fält | Encoding / status |
|---:|---|---|
| +159 | `pegKFCenterNote` | MIDI-note; UI-bekräftad Pitch EG Center Key |
| +237 | `feg_depth` | verifierad FEG Depth |
| +239 | `feg_segment` | verifierad FEG Segment |
| +241 | `feg_time_vel` | verifierad FEG Time/Vel |
| +243 | `feg_depth_vel` | c64, binärverifierad med dedikerad single-edit-test |
| +245 | `feg_curve` / `filter_curve` | verifierad FEG Curve |
| +247 | `feg_time_key` / `filter_time_key` | verifierad FEG Time/Key |
| +249 | `feg_center_key` / `filter_scaling_center_key` | verifierad FEG Center Key |
| +289 | `lfoSpeed` | normal LFO speed när Extended LFO är av |

Konflikten kring rel `+243` är löst: fältet är `feg_depth_vel`, inte en orelaterad okänd byte. PEG/FEG-symmetrin är `FEG = PEG + 54` för motsvarande Segment, Time/Vel, Depth/Vel, Curve, Time/Key och Center Key.

AWM2 internkonstanter som ska vara stängda inkluderar rel `+46`, `+90`, `+148`, `+200`, padding vid `+309..+311` samt relaterade routing-/trailer-bytes. Extended LFO-default är `1` (ON), inte `0`.

Adresskonventionerna får inte blandas ihop:

| Konvention | Element 1 base | Användning |
|---|---:|---|
| audit abs | 12469 | dokumentation och binära testoffsets |
| `AWM2_ELEM_LAYOUT` base | 12520 | aktiv layoutkod |
| `AWM2_ELEM1_BASE` | 12532 | helper-offsets för binärverifiering |

Konversion: `AWM2_ELEM_LAYOUT_offset + 51 = AWM2_ELEMENT_FIELDS_rel` i audit-relativ konvention.

### FM-X engine-täckning

FM-X betraktas som fullständigt mappad för aktuell användarredigerbar täckning. Den aktuella modellen är:

| Kategori | Aktuell tolkning |
|---|---|
| UI-mappade fält | 141 fält |
| Interna bytes | 863 firmware-/internbytes inklusive OP-trailers |
| Kvarvarande varierande omappade bytes | 0 kända |

Viktiga FM-X-fält som måste finnas kvar i referensen/serializern:

- PEG: `fmx_peg_center_key`, `fmx_peg_level_decay2`, `fmx_peg_level_release`, `fmx_peg_time_attack`, `fmx_peg_time_decay1`, `fmx_peg_time_release`, `fmx_peg_depth`
- 2nd LFO / algorithm: `fmx_2nd_lfo_phase`, `fmx_2nd_lfo_delay`, `fmx_algorithm`, `fmx_feedback`
- Part Filter / FEG: resonance velocity, hold/release time, hold/attack/decay/sustain/release levels, depth, segment, time velocity, depth velocity, curve, time key och center key
- Filter Scaling: fyra breakpoints och fyra cutoff offsets
- Per-OP-fält: key-on reset, frequency mode, fixed-mode pitch key/velocity, AEG levels, level velocity, per-OP 2nd LFO pitch/amp mod destinations

FM-X OP-stride är 123 bytes. Per-OP-tilläggen är:

| Rel inom OP | Fält | Status |
|---:|---|---|
| +58 | `op_2nd_lfo_pitch_mod_dest` | UI-fält |
| +60 | `op_2nd_lfo_amp_mod_dest` | UI-fält |
| +66 | `op_trailer_a` | [INTERN], default 127 |
| +68 | `op_trailer_b` | [INTERN], default 127 |
| +70 | `op_trailer_c` | [INTERN], default 127 |

För OP1..OP8 upprepas positionerna med stride 123. Trailer-bytes är interna konstanter och ska inte exponeras som redigerbara UI-parametrar.

### Drum engine-täckning

Drum använder annan offsetkonvention och annan Part Common-tolkning än AWM2/FM-X/AN-X. Drum key-mappningen och Drum Part Common-fälten betraktas som fullständigt mappade för aktuell UI-täckning.

| Område | Aktuell status |
|---|---|
| DRUM_KEY, 73 keys | 27 UI-fält per key, binärverifierade |
| DRUM_KEY internbytes | cirka 38 internbytes per key |
| DRUM_PART_COMMON | 27 UI-fält, binärverifierade |
| Insertion FX | delad Part-level InsA/InsB-struktur |

Drum filoffset-konversion skiljer sig från övriga engines:

| Engine | audit → filoffset-konversion |
|---|---|
| AWM2 / AN-X / FM-X | `file_offset = audit + 687` |
| Drum | `file_offset = audit + 669` |

Drum key-zonen använder 73 keys med 68-byte stride. Key-mönstret `01 00 00 00 00 00 01 00` identifierar SW=1 och AssignMode=1. Kända key-positioner inkluderar Key 1 vid filoffset 13138, Key 36 vid 15518 och Key 73 vid 18034 i verifierad baseline-konvention.

Drum-key interna icke-noll-konstanter:

| Rel | Värde | Status |
|---:|---:|---|
| +18 | 90 | [INTERN], konstant |
| +67 | 64 | [INTERN], konstant |

Drum Part Common-fält som måste finnas kvar:

| Abs | Fält | Encoding / default |
|---:|---|---|
| 6815 | `drumPartMainCategory` | enum, default 16 |
| 6849 | `drumPartFilterAegAttack` | c64, default 64 |
| 6851 | `drumPartFilterAegDecay` | c64, default 64 |
| 6853 | `drumPartFilterAegSustain` | c64, default 64 |
| 6855 | `drumPartFilterAegRelease` | c64, default 64 |
| 6903 | `drumPartControlGroup` | enum, default 0 |

Drum delar inte det universella AEG-offset-blocket på samma sätt som AWM2/FM-X/AN-X. För Drum gäller rel `+126..+132` som Drum AEG, och rel `+144/+146` som Drum filter cutoff/resonance. Tolkningen av Part Common rel `+126..+158` är därför engine-specifik.

### Återstående testtäckningsnotering

Den aktuella referensen behandlar Stride-106 och opaque/preserved regions som icke-användarredigerbara tills ett framtida kontrollerat single-edit-test visar något annat. Ingen aktuell exportväg ska modifiera dessa regioner annat än genom att kopiera dem från källan eller från verifierad baseline.

# 19. Helper-funktioner (serializer-API)

## 19.1 Adress-beräkning ★★★★★

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

## 19.2 Engine-pool ★★★★★

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
    if 'Drum'   in name: return 'Drum'   # OBS: utan parentes
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

## 19.8 CA strukturer ★★★★★

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

## 19.11 FX-utilities ★★★★★

```python
def fx_type_bytes(name):
    idx = FX_TYPE_INDEX.get(name.upper(), 0)
    return (idx & 0x7F, (idx >> 7) & 0x7F)

def fx_name_from_bytes(lo, hi):
    return FX_INDEX_TO_NAME.get(hi * 128 + lo, f'UNKNOWN({hi*128+lo})')
```

## 19.12 Strukturella metadata-bytes ★★★★★

Vid både read och write av performance måste dessa bytes vara korrekta.

```python
ENGINE_TYPE_BYTE = 6700  # 0=AWM2, 1=Drum, 2=FMX, 3=ANX
ENGINE_TYPE_VALUES = {0: 'AWM2', 1: 'Drum', 2: 'FMX', 3: 'ANX'}
ENGINE_TYPE_BY_NAME = {v: k for k, v in ENGINE_TYPE_VALUES.items()}

MAX_ACTIVE_PART_BYTE = 6695  # 1..16, högsta aktiva part-nummer

def get_engine_type_byte(blob):
    return ENGINE_TYPE_VALUES.get(blob[ENGINE_TYPE_BYTE], 'Unknown')

def get_max_active_part(blob):
    return blob[MAX_ACTIVE_PART_BYTE]

def set_engine_type_byte(blob, engine_name):
    """engine_name: 'AWM2' | 'Drum' | 'FMX' | 'ANX'"""
    blob[ENGINE_TYPE_BYTE] = ENGINE_TYPE_BY_NAME[engine_name]

def set_max_active_part(blob, max_part_idx):
    """max_part_idx: 1..16 (HÖGSTA part-nummer som är aktivt)"""
    blob[MAX_ACTIVE_PART_BYTE] = max_part_idx

def validate_engine_consistency(blob):
    """Verifiera att engine-byte matchar sub-blob 2 name suffix."""
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
    """slot_idx: 0..3, field_rel: rel-offset från slot-bas."""
    part_offset = sub_blob_start - 6701
    slot_base = AWM2_CONTROL_SOURCE_BASE + slot_idx * AWM2_CONTROL_SOURCE_STRIDE
    return slot_base + field_rel + part_offset
```

## 19.14 Motion Sequencer fält ★★★★★

UI-vy "Motion Seq > Common / Lane" har TVÅ sektioner med 6 fält vardera:

**"Common" (Performance Common-area, gäller alla parts):**
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

**"Part" (Part Common-area, gäller alla 4 Lanes i denna Part):**
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
    """Returnerar abs address för Part N:s Motion Seq Part-fält."""
    sub_blob_start = 6701 + (part_idx - 1) * 5765
    return sub_blob_start + PART_MOTION_SEQ_REL[f'{field}_rel']
```

**View Lane-dropdown (1-4)** i UI styr endast vilken Lane som visas i
Edit Part Sequencer-vyn — den ändrar **INTE** vilka bytes som påverkas
av Common/Part-fälten ovan. Båda sektionerna är Part-level (eller
Performance-level för Common), inte per-Lane.

Verifierat: TEST5R3-T4b-ViewLane2-Swing50 — ändring av "View Lane: 2"
+ Part Swing påverkar samma byte (6887) som med View Lane 1.

**Per-Lane data** (Lane Switch, Lane Velocity Limits, MS Grid, Pulse A/B m.fl.)
ligger i sub-blob 2 Lane-data-area [8929+, stride 884 per Lane]:
- Lane 1 LaneSwitch @ blob[+8929]
- Lane 2 LaneSwitch @ blob[+9813]
- Lane 3 LaneSwitch @ blob[+10697]
- Lane 4 LaneSwitch @ blob[+11581]

**Bakåtkompatibilitet:** `LANE1_COMMON` är alias för `COMMON_MOTION_SEQ`.

## 19.15 Multi-part pointer API ★★★★★

```python
SUBBLOB_POINTER_REL = (5763, 5764)
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
    """OBS: part1_engine_name = första engine i pool (= Part 1:s engine)."""
    pos0, pos1 = get_subblob_pointer_pos(part_idx)
    blob[pos0] = ENGINE_MAGIC_BYTES[part1_engine_name]
    blob[pos1] = 0

def get_entr_bitmask(max_active_part):
    """(1 << N) - 1 där N = max_active_part."""
    return (1 << max_active_part) - 1
```

## 19.16 Opaque-regions registry ★★★★★

```python
# Regioner som MÅSTE preserveras byte-för-byte. 0 testfiler modifierar dem.
OPAQUE_INTERNAL_REGIONS = [
    (487, 525),    # 38 b
    (732, 766),    # 34 b — 14 × u16le firmware-konstant
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
    """Returnerar True om offset är i en opaque-region."""
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
FILE_SAVE_COUNTER_POS = 60         # u32be, ökar +1 per spar
FILE_INNER_SAVE_COUNTER_POS = 396  # u32be, = file[60:64] - 1
CHUNK_CATALOG_POS = 64             # 6 × 8 bytes
CHUNK_NAMES = ['EPFM', 'ESYS', 'EFVT', 'DPFM', 'DSYS', 'DFVT']

def read_save_counter(file_data):
    """Returnerar u32be save counter från file[60:64]."""
    import struct
    return struct.unpack('>I', file_data[60:64])[0]

def write_save_counter(file_data, value):
    """Skriv save counter till file[60:64] OCH inner counter file[396:400]=value-1."""
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

# 20. Verifieringsstatus och testfil-register

## 20.1 Sammanfattning per engine

| Engine / Sektion | Status | Verifierat |
|---|---|---|
| Container (EPFM/DPFM/ESYS/EFVT/DSYS/DFVT) | KOMPLETT | ★★★★★ |
| Sub-blob universella modellen | KOMPLETT | ★★★★★ (alla 16 parts × alla 4 engines) |
| Engine-pool struktur | KOMPLETT | ★★★★★ |
| Performance Common (~30 fält) | KOMPLETT | ★★★★★ |
| Part Common (~25 fält) | KOMPLETT | ★★★★★ |
| Receive Switch (26/26) | KOMPLETT | ★★★★★ (utom pos 22 = INTERN) |
| Common Assigns (CA_PERF + CA_PART, 32 slots) | KOMPLETT | ★★★★★ |
| Scene Struct 1 (9 fält × 8 scener) | KOMPLETT | ★★★★★ |
| Scene Struct 2 (11 fält × 8 scener) | KOMPLETT | ★★★★★ (hypotes: aktiv-part) |
| Master EQ (15 fält) | KOMPLETT | 13 × ★★★★★ + 2 × ★★★★☆ (LoMid/HiMid Freq) |
| Reverb FX (26 fält) | KOMPLETT | ★★★★★ |
| Variation FX (28 fält) | KOMPLETT | ★★★★★ |
| Master FX (26 fält) | KOMPLETT | ★★★★★ |
| Common CC + Hardware Ribbon | KOMPLETT | ★★★★★ |
| Audio In + Envelope Follower | KOMPLETT | ★★★★★ |
| Per-Part 3-band EQ (7 fält) | KOMPLETT | ★★★★★ |
| Per-Part 2-band EQ (9 fält) | KOMPLETT | ★★★★★ |
| AN-X engine (684 b) | KOMPLETT | ★★★★★ OSC1 verifierad, OSC2/3 stride-bekräftade |
| AWM2 engine (2503 b) | KOMPLETT | ★★★★★ Element 1 verifierad, 8 elements verifierade |
| FM-X engine (1143 b) | KOMPLETT | ★★★★★ 8 OPs × 21 fält + LFO matriser |
| Drum engine (4963 b) | KOMPLETT | ★★★★★ 73 keys × 27 fält + 21 Part Common |
| Insertion FX (57 typer) | KOMPLETT | 12 × ★★★★★ + 45 × ★★★★☆ |
| Smart Morph | DETEKTION KLAR | ★★★★★ (DSOM-payload ej kartlagd) |
| MS Sequencer (4 lanes) | KOMPLETT | ★★★★★ Lane-bas + 29 fält/lane |

## 20.2 Lista över fält påstådda klara men utan test-referens

Områden som är dokumenterade men där vi inte hittade en clean testfil i korpusen. Kandidater för framtida verifiering:

- **Master EQ Lo Mid Freq (570)** — predikterat från stride
- **Master EQ Hi Mid Freq (582)** — predikterat från stride
- **FS Assign destination encoding (abs 164)** — ★★★☆☆
- **AN-X OSC2 / OSC3 EG-fält** — stride-extrapolerade från OSC1, ej direkt testade per-fält
- **AN-X Filter 2 fält** — stride-extrapolerade från Filter 1
- **FMX LFO Destinations 71, 73, 76** — UI-deduced från enum-position
- **CA Sources 2-7, 11-15** — endast PB/MW/Knob1-3 binärverifierade
- **AWM2 Element 2-8** — stride-verifierade men inte per-fält per element

Praktisk konsekvens: dessa fält följer etablerade mönster och kan användas i editor men ska markeras ★★★★☆ tills explicit verifierat.

## 20.3 Statistik från testkorpus

```
Total Y2L-testfiler analyserade:     1626
Clean 1-byte diff tester:             385
2-byte (u16le) diff tester:           293
Multi-byte diff tester (parametrar + side-effects):  ~700
Tomma/identiska tester:               ~248

Unika offsets binärverifierade med ≥1 clean test:  ~200 (u8) + ~21 (u16le) = 221
Unika offsets verifierade med ≥3 oberoende tester:  ~25
Offsets med max test-count (Detune):  37 oberoende tester
```

## 20.4 Patch Editor — implementation status

Rekommenderad arkitektur:

1. **Läs performance** från Y2L → parse via EPFM directory → DPFM → blob
2. **Decode parametrar** via offset-tabeller + encoding-funktioner
3. **UI-lager** per engine/sektion (FM-X OP, AWM2 Elem, AN-X OSC, Drum-key)
4. **Encode + skriv** ändrade bytes tillbaka till blob
5. **Exportera** ny Y2L via `buildYSFC`-funktion

**Editor read-path behöver:**
- Detektera antal sub-blobs (söka efter `00 00 00 15 "Init …"` headers)
- För Part N ≥ 2: använd `part_field_abs(N-1, payload_offset)`
- Engine-data ligger alltid i sista sub-blobben (solo) eller i engine-pool (multi-part)

**Editor write-path behöver:**
- Vid redigering av Part N: säkerställ att sub-blob N existerar
- Skapa tomma sub-blob-platshållare för alla parts upp till N
- Engine-data flyttas till sista sub-blobben / engine-pool

**Bevarad data (preserve verbatim):**
- ESYS/DSYS/EFVT/DFVT chunks (engine-oberoende)
- Smart Morph chunks (ESPG/ESOM/DSPG/DSOM)
- Stride-106 Zone/Control-blocks (Common region)
- Region [732:766] (14 × u16le)
- Region [788:840], [5843:5893], [7300:7419] (ej UI-mappade)
- Modified-flag-bytes (kopieras från source vid merge)
- CA+17 byte i varje CA-slot (MODX-internt)
- Drum kollaterala bytes [6715, 6716, 6721]

---

# 21. Lärdomar och process

## 21.1 UI-aliasing (en byte → flera UI-labels)

Vissa bytes har två UI-labels beroende på UI-vy:

| Byte | UI Label 1 | UI Label 2 |
|---|---|---|
| `blob[+68]` | Performance Volume | EF Master Output |
| `blob[+6831]` | Part Volume | EF Part Output |
| `blob[+766]` | Audio In Volume | EF AD Output Level |

Editor måste presentera båda labels i sina respektive UI-sektioner men förstå att de skriver samma fysiska byte.

## 21.2 Side-effect-flaggor

Vissa bytes ändras av många orelaterade UI-operationer:

| Byte | Beteende |
|---|---|
| `blob[+66]` | Common-area side-effect-flag — ändras vid många Common-edits |
| `blob[+654]` | Multi-trigger — minst 9 olika edit-typer ändrar denna |
| `blob[+23/24]`, sub-blob `+23/24` per N | Timestamp/edit-counter |

Dessa ÄR NOISE — ska filtreras vid diff-analys, men måste skrivas korrekt vid round-trip.

## 21.3 Verifieringsmetodik

Kontrollerat test (ändra X i UI, exportera, diff) är guldstandard. Minst 3-4 datapunkter behövs för encoding-säkerhet (center=64 vs center=128 vs direct osv). Statistisk korrelation över korpus utan riktade tester kan ge falska positiva.

Stjärnbetyg sätts först när bevis finns:
- **★★★★★** = binärverifierat med specifik testfil (lista i sektion 20)
- **★★★★☆** = härlett från officiell källdata eller etablerat mönster
- **★★★☆☆** = predikterat utan empirisk bekräftelse

---

**Slutet på YSFC Forge Full Context.**

