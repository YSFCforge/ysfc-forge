# SysEx Forge

**Lokal, reverse-engineerad Soundmondo → Y2L-konvertering för Yamaha MONTAGE / MODX / MODX+ / MONTAGE M / MODX M.**

SysEx Forge började som ett mappningsprojekt för att identifiera Yamahas SysEx-block och konvertera dem till den moderna MODX M / MONTAGE M Y2L-strukturen. Projektet omfattar nu källparsning, engine-detektion, parameternormalisering, waveform-remap, dependency-hantering och Y2L-emission.

All konvertering i webbläsaren sker lokalt. SysEx- och library-filer behöver inte laddas upp till någon server.

---

## Innehåll

- [Funktioner](#funktioner)
- [Snabbstart](#snabbstart)
- [Arkitektur](#arkitektur)
- [Aktuell status](#aktuell-status)
- [Plattformar](#plattformar)
- [Waveform-mappning](#waveform-mappning)
- [Y2L-integritetsfixar](#y2l-integritetsfixar)
- [Projektfiler](#projektfiler)
- [Verifieringspolicy](#verifieringspolicy)
- [Kända begränsningar](#kända-begränsningar)
- [Dokumentation](#dokumentation)
- [Utvecklingsflöde](#utvecklingsflöde)

---

## Funktioner

- Parsar Yamaha Soundmondo SysEx från legacy- och M-generationens instrument
- Identifierar source family från Yamaha model ID
- Normaliserar källparametrar till en gemensam bridge-modell
- Konverterar **AWM2**, **FM-X**, **AN-X** och **Drum**
- Bevarar multi-Part-struktur där källan innehåller den
- Remappar legacy preset-waveform-ID:n till MODX M
- Identifierar olösta User/Library-waveform-dependencies och failar stängt
- Bevarar/konverterar Performance Common, Part Common, engine-data, Scenes, Arps, Control Assign och valda FX-strukturer
- Exporterar modern `.Y2L` för MODX M / MONTAGE M / ESP
- Bulk-konverterar många `.syx` till separata Y2L-filer i en ZIP
- Validerar modern EPFM-container före export
- Ingen telemetry och ingen molnbehandling

---

## Snabbstart

### Webbläsarkonverteraren

1. Öppna `tools/ysfc_forge_sysex_converter_v1_58.html`.
2. Dra in en eller flera Soundmondo `.syx`.
3. Kontrollera detekterad plattform, engines, Parts och dependency-varningar.
4. Ladda vid behov en companion `.Y2L` / `.Y2U` för externa waveform-dependencies.
5. Konvertera en fil eller kör bulkexport.
6. Ladda resultatet i MODX M / MONTAGE M / ESP och verifiera.

### Python-integrationslagret

```text
Soundmondo .syx
      │
      ▼
sysex_parser.py
      │
      ▼
ysfc_bridge.py
      │
      ├── normaliserad parametermodell
      ├── source-family/model-id routing
      ├── waveform/dependency mapping
      └── engine-specifik bridge-data
      │
      ▼
ysfc_serializer_adapter.py / Y2L serializer
      │
      ▼
MODX M / MONTAGE M .Y2L
```

Webbläsarkonverteraren är för närvarande den mest kompletta end-to-end Soundmondo-writern. Python-adaptrar ska behandlas fail-closed om aktuell väg inte uttryckligen är verifierad.

---

## Arkitektur

| Lager | Uppgift |
|---|---|
| **Parser** | Läser Yamaha SysEx-paket, adresser, model ID och blockpayload |
| **Normalizer / Bridge** | Konverterar källspecifika parametrar till stabil intern representation |
| **Mapping / Dependencies** | Hanterar waveform-ID, Arps, engine-identitet och generationsskillnader |
| **Serializer / Writer** | Skapar modern Y2L Performance- och containerstruktur |

Projektet undviker medvetet “best guess”-konvertering. Okänd eller tvetydig data bevaras bara när det är strukturellt säkert; annars blockeras exporten eller en varning visas.

---

## Aktuell status

| Engine | SysEx Forge checkpoint | Status |
|---|---|---|
| **FM-X** | v1.0.75 | ✅ ESP-verifierad |
| **AWM2** | v1.1.26 | ✅ ESP verified |
| **Drum** | v1.2.7 | ✅ ESP verified |
| **AN-X** | v1.3.9 | ✅ ESP verified |

Exempel på ESP-verifierade delmål:

- FM-X core, operators, Smart Morph-preservation och utökad controller-täckning
- AWM2 element engine, Part Common, Control Assign, Arp slots, Motion Sequence, Zone och key-controller destinations
- Drum key engine, Part Common, Control Assign, Motion Sequence och Zone
- AN-X oscillator, synthesis/EG, filter, amp/AEG och LFO

Reverse-engineeringens v1.x-checkpoints och den produktionsinriktade Soundmondo-konverteraren versioneras separat. `ysfc_forge_sysex_converter_v1_27.html` är aktuell browser-app.

---

## Plattformar

Canonical routing baseras på Yamaha model ID:

| Model ID | Source family | Produkter |
|---:|---|---|
| `0x02` | `legacy_montage` | MONTAGE |
| `0x07` | `legacy_modx` | MODX / MODX+ |
| `0x0D` | `m_generation` | MONTAGE M / MODX M |

Source family ska härledas från model identity, inte gissas från filnamn eller UI-text.

### Soundmondo blockfamiljer

Legacy:

```text
30 40 00   Performance Common
31 0p 00   Performance Part
41 ep 00   AWM2 Oscillator / Amplitude / Pitch
42 ep 00   AWM2 Filter / EQ / LFO
48 0p 00   FM-X Common
49 op 00   FM-X Operator
5p kk 00   Drum Key
```

M-generation:

```text
06 00 00 00   Performance Name
06 00 01 00   Performance Common 1-byte
06 00 02 00   Performance Common 2-byte
1p 00 01 00   Part 1-byte
1p 00 02 00   Part 2-byte
2p xx ee 00   AWM2 Element
3p xx xx 00   FM-X
4p xx xx 00   AN-X
2p 10 kk 00   Drum Key
```

Se `SYSEX_FORGE_REFERENCE_sv.md` för kompakt blockreferens.

---

## Waveform-mappning

Legacy AWM2 preset-waveform-ID:n är inte numeriskt identiska med MODX M.

Aktuell master:

- **6347** legacy-waveforms analyserade
- **6346** mappade
- **1** avsiktligt unresolved: ID **3720 — `Sagat2 Sw`**

Confidence-klasser:

- `EXACT_NAME`
- `NORMALIZED_EXACT`
- `STRUCTURAL_MATCH`
- `UNRESOLVED`

Olösta preset- eller externa User/Library-waveforms får aldrig tyst kopplas till en annan waveform.

Rekommenderade repoartefakter:

```text
mapping/
  waveforms_legacy.py
  waveform_remap_legacy_to_m.py
  YSFC_waveform_mapping_master_v1.json
  YSFC_waveform_mapping_master_v1.csv
  YSFC_waveform_mapping_production_v1.js
```

---

## Y2L-integritetsfixar

### EPFM-tail

Tailen efter det NUL-terminerade EPFM-namnet måste bestå av kompletta 32-bitarsord:

```text
0, 4, 8, 12, 16, ... bytes → giltigt
1, 2, 3, 5, 6, 7, ...      → ogiltigt
```

En slutlig remainder på 1–3 bytes får trimmas **endast om samtliga bytes är noll**. Icke-noll data i ett ofullständigt ord ska blockera export.

### EPFM Performance ID — 5 × 128

Modern Y2L har 640 Performance-slots som fem banker × 128:

```text
bank = index // 128
slot = index % 128
id   = 0x00400000 | (bank << 8) | slot
```

```text
0   → 0x00400000
127 → 0x0040007F
128 → 0x00400100
255 → 0x0040017F
256 → 0x00400200
512 → 0x00400400
639 → 0x0040047F
```

Regeln isolerades vid exakt gränsen 128→129 och verifierades i MODX M ESP. Filer med **129, 130, 256 och 414 Performances** laddade efter korrigeringen.

Följande gamla antaganden är förkastade:

```text
rec[11] = index & 0xFF
0x00400000 + index
```

SysEx Converter skapar normalt en Performance per Y2L, men v1.27 använder ändå den gemensamma regeln för att framtidssäkra koden.

---

## Projektfiler

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
  waveform-källor och genererade tabeller

serializer/
  ysfc_serializer.py
  ysfc_transcoder_classic_to_y2l.py
  ysfc_source_family.py
  enums / helpers

docs/
  SYSEX_FORGE_FULL_CONTEXT.md
  SYSEX_FORGE_FULL_CONTEXT_sv.md
  SYSEX_FORGE_REFERENCE.md
  SYSEX_FORGE_REFERENCE_sv.md
```

Privata Soundmondo-korpusfiler och Yamaha-PDF:er bör inte distribueras i publikt repo.

---

## Verifieringspolicy

| Märkning | Betydelse |
|---|---|
| **ESP_VERIFIED** | Resultatet har laddats och kontrollerats i MODX M ESP |
| **★★★★★** | Binärverifierat med kontrollerade A/B-testfiler |
| **★★★★☆** | Härlett från officiell Yamaha-data / stark strukturell evidens |
| **★★★☆☆** | Sannolik mappning, ännu inte direkt verifierad |
| **[STRUKT]** | Strukturen identifierad men UI-semantiken ofullständig |
| **[UNKNOWN]** | Ska inte skrivas eller infereras |

Grundprincip:

> **Fail closed i stället för att hitta på defaults eller mappings.**

En saknad source family, olöst dependency eller tvetydigt block får aldrig tyst ersättas med orelaterade template-defaults bara för att exporten ska lyckas.

---

## Kända begränsningar

- Externa User/Library-waveforms kräver explicit resolution eller companion library.
- Smart Morph transport/preservation är inte samma sak som generell rekonstruktion av interpolationstabeller.
- Effect-parametrar får inte blindt raw-kopieras mellan generationer när layouten skiljer sig.
- Vissa M-generation Soundmondo-versioner har observerade payload-längder som skiljer sig från Yamahas dokumenterade bulk-dump-längder; overrides hålls separat.
- Hårdvaruverifieringen är främst MODX M / ESP. MONTAGE M bör fortsätta verifieras på hårdvara.
- Python-adaptrar är inte automatiskt likvärdiga med browser-konverteraren; kontrollera verifieringsstatus innan produktionsanvändning.

---

## Dokumentation

| Dokument | Innehåll |
|---|---|
| [`README.md`](README.md) | Engelsk projektöversikt |
| [`README_sv.md`](README_sv.md) | Svensk projektöversikt |
| [`SYSEX_FORGE_REFERENCE.md`](SYSEX_FORGE_REFERENCE.md) | Parameter-för-parameter master byte map: Soundmondo/WebMIDI source → Y2L target |
| [`SYSEX_FORGE_REFERENCE_sv.md`](SYSEX_FORGE_REFERENCE_sv.md) | Svensk parameter-för-parameter master byte map |
| [`SYSEX_FORGE_FULL_CONTEXT.md`](SYSEX_FORGE_FULL_CONTEXT.md) | Full teknisk/recovery-kontext |
| [`SYSEX_FORGE_FULL_CONTEXT_sv.md`](SYSEX_FORGE_FULL_CONTEXT_sv.md) | Full svensk teknisk/recovery-kontext |

För själva target-formatet Y2L är YSFC Forge-dokumentationen fortsatt auktoritativ för target-blob-offsets och containerstruktur.

---

## Utvecklingsflöde

1. Skapa en ren baseline-Performance.
2. Ändra exakt en UI-parameter.
3. Exportera/fånga Soundmondo SysEx.
4. Diffa källblocken och identifiera ändrade bytes.
5. Verifiera encoding med minst ett ytterligare värde när det är praktiskt.
6. Lägg till parser/bridge-mapping.
7. Generera Y2L.
8. Testa i MODX M ESP.
9. Märk `ESP_VERIFIED` först när filen laddar och UI/ljud stämmer.
10. Uppdatera Full Context + Reference och lägg till regressionstest.

En mappning ska inte uppgraderas till verifierad enbart för att filen går att parsa.
