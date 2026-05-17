# YSFC Forge

> 🇬🇧 **English:** [README.md](README.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Active](https://img.shields.io/badge/Status-Active-brightgreen.svg)]()
[![Engines: 4/4](https://img.shields.io/badge/Engines-4%2F4%20mapped-blue.svg)]()
[![Test files: 2010+](https://img.shields.io/badge/Test%20files-2010%2B-blue.svg)]()

**Webbläsarbaserade open-source-verktyg för Yamaha MODX M / ESP Plugin / Montage M performancefiler.**

Reverse-engineerad från grunden genom binäranalys av Yamahas odokumenterade `.Y2L` / `.Y2U`-filformat. Öppna HTML-filerna i vilken modern webbläsare som helst — ingen installation, ingen molnuppladdning, allt körs lokalt.

![Forge Performance Merger skärmdump](screenshots/image_ysfc_forge_performance_merger.png)

---

## Innehåll

* [Funktioner](#funktioner)
* [Snabbstart](#snabbstart)
* [Verktyg](#verktyg)
* [Status](#status)
* [Dokumentation](#dokumentation)
* [Bidra](#bidra)
* [Licens](#licens)

---

## Funktioner

* **Sammanfoga** performances från flera `.Y2L` / `.Y2U`-filer
* **Redigera** FM-X, AWM2, AN-X och Drum-parametrar i webbläsaren
* **Översätt** patchar från DIVA, Vital och Synth1 till Yamaha-format
* **Ingen installation** — fungerar i Chrome, Firefox och Safari
* **Ingen telemetri** — allt körs lokalt

---

## Snabbstart

### Sammanfoga performances

1. Ladda ner [`tools/ysfc_forge_performance_merger_v1_19.html`](tools/ysfc_forge_performance_merger_v1_19.html)
2. Öppna filen i din webbläsare
3. Dra och släpp `.Y2L`- eller `.Y2U`-filer
4. Markera de performances du vill ha
5. Klicka på **Save as Y2L** eller **Save as Y2U**
6. Importera den exporterade filen i MODX M / ESP plugin / Montage M

### Sammanfoga performances inklusive beroenden

1. Ladda ner [`tools/ysfc_forge_library_builder_v13_17.html`](tools/ysfc_forge_library_builder_v13_17.html)
2. Öppna filen i din webbläsare
3. Dra och släpp `.Y2L`- eller `.Y2U`-filer
4. Markera de performances du vill ha
5. Klicka på **Save as Y2L** eller **Save as Y2U**
6. Importera den exporterade filen i MODX M / ESP plugin / Montage M

### Redigera en performance

1. Ladda ner [`tools/ysfc_forge_performance_editor_v5_1.html`](tools/ysfc_forge_performance_editor_v5_1.html)
2. Öppna filen i din webbläsare
3. Klicka på **Open Y2L** och välj en fil
4. Justera parametrar med reglage
5. Klicka på **Export Y2L** för att spara

---

## Verktyg

### Huvudverktyg

|Verktyg|Vad det gör|
|-|-|
|[**Performance Merger**](tools/ysfc_forge_performance_merger_v1_19.html)|Sammanfoga performances från flera Y2L/Y2U-filer|
|[**Library Builder**](tools/ysfc_forge_library_builder_v13_17.html)|Library builder prototyp (sammanfoga performances inklusive beroenden från flera Y2L/Y2U filer)|
|[**Performance Editor**](tools/ysfc_forge_performance_editor_v5_1.html)|Redigera FM-X, AWM2 och AN-X-parametrar i webbläsaren|

### Översättare

|Verktyg|Vad det gör|
|-|-|
|[**DIVA Patch Translator**](translators/ysfc_diva_h2p_converter_v2_15.html)|Konvertera DIVA-patchar till Y2L/Y2U|
|[**Vital Patch Translator**](translators/ysfc_vital_converter_v4_12.html)|Konvertera Vital-patchar till Y2L/Y2U|
|[**Synth1 Patch Translator**](translators/ysfc_synth1_converter_v5_12.html)|Konvertera Synth1-patchar till Y2L/Y2U|

### Tilläggsverktyg

|Verktyg|Vad det gör|
|-|-|
|[**Smart Name Compressor**](utilities/ysfc_smart_name_compressor.html)|Standardiserad namngivning för performances|
|[**Synth Converter**](utilities/ysfc_synth_converter.html)|Konvertera patchar mellan 8+ format|

### Skärmdumpar

||||
|-|-|-|
|![Performance Editor](screenshots/image_ysfc_forge_performance_editor.png)|![Library Builder](screenshots/image_ysfc_forge_library_builder.png)|![DIVA Patch Translator](screenshots/image_ysfc_diva_h2p_translator.png)|
|*Performance Editor — FM-X-operatorredigerare*|*Library Builder — performancelista med engine-detektering*|*DIVA Patch Translator — Konvertera DIVA patches till Y2L/Y2U*|

---

## Status

Alla fyra synth-**engines** är **100% binärverifierat kartlagda** genom systematisk A/B-diffanalys på riktig MODX M-hårdvara. Detta omfattar varje användarredigerbart parameterfält per engine; filnivåstrukturer som Smart Morph och Scene-snapshots är kartlagda separat — se [Kända begränsningar](#kända-begränsningar).

|Engine|UI-fält|Intern/firmware|Status|
|-|-:|-:|-|
|**AWM2**|128|8|✅ 100%|
|**AN-X**|171|458|✅ 100%|
|**FM-X**|141|863|✅ 100%|
|**Drum**|54|4934|✅ 100%|

> *"100%" avser de användarredigerbara parameterfälten i de fyra synthesengines:arna. Filnivåstrukturer utanför engines — Smart Morph-interpolationstabeller och Scene-snapshots — spåras separat under [Kända begränsningar](#kända-begränsningar).*

### Filtyper som stöds

|Typ|Beskrivning|Stöd|
|-|-|-|
|`.Y2L`|Bibliotekfil|✅|
|`.Y2U`|Användarfil (identiskt format som Y2L, bara annan filändelse)|✅|
|**Multi/GM 16-part**|16 parts (15 AWM2 + 1 Drum på Part 10)|✅|

### Hårdvarukompatibilitet

|Hårdvara|Stöd|
|-|-|
|MODX M|✅ Primärt mål|
|ESP plugin|✅|
|Montage M|⚠️ Sannolikt kompatibel — inte fullständigt testad|
|MODX (icke-M)|❌ Annat format|

### Testkorpus

**2010+ binärverifierade testfiler** genererade genom systematiska parameterändringar på riktig MODX M-hårdvara. Varje dokumenterad offset stöds av minst en A/B-binärdiff.

|Engine|Filer|
|-|-:|
|AN-X|799|
|AWM2|408|
|FM-X|425|
|Drum|84|
|Övrigt|294|

Se [`docs/REVERSE_ENGINEERING.md`](docs/REVERSE_ENGINEERING.md) för detaljerad metodik, täckningstabeller och fältnivådokumentation.

---

## Dokumentation

|Dokument|Innehåll|
|-|-|
|[`docs/REVERSE_ENGINEERING.md`](docs/REVERSE_ENGINEERING.md)|Metodik, täckningstabeller, tekniska detaljer|
|[`docs/YSFC_FORGE_REFERENCE.md`](docs/YSFC_FORGE_REFERENCE.md)|Kompakt referensmanual|
|[`docs/YSFC_FORGE_FULL_CONTEXT.md`](docs/YSFC_FORGE_FULL_CONTEXT.md)|Komplett teknisk referens (alla fältpositioner, evidens)|
|[`serializer/ysfc_serializer.py`](serializer/ysfc_serializer.py)|Python-parameterkonstanter — användbart om du vill bygga egna verktyg|

### Verifieringsnivåer

I dokumentationen klassificeras varje fält efter evidens:

* **★★★★★** — Binärverifierad med en eller flera testfiler
* **★★★★☆** — Härledd från officiell källdata, hög konfidens
* **★★★☆☆** — Sannolikt korrekt, ej binärverifierad
* **[INTERN]** — MODX-intern firmware-konstant, inte användarredigerbar

---

## Kända begränsningar

* **Performance Editor** visar i nuläget bara den första partens engine; redigering av alla 16 parts är på roadmap
* **Smart Morph**-interpolationstabeller är inte kartlagda än
* **Scene-snapshots** — strukturen är verifierad, men endast \~10 fält per scen har UI-bekräftade mappningar
* **Patch-översättare är approximationer** — källsyntarna använder fundamentalt olika synthesteknik, så resultatet är en utgångspunkt för ljuddesign snarare än en exakt portering
* **Ingen undo/redo** i Performance Editor än — håll alltid backuper på dina original

Se [`docs/REVERSE_ENGINEERING.md`](docs/REVERSE_ENGINEERING.md) för fullständig lista.

---

## Bidra

Buggrapporter, testfiler och reverse engineering-fynd är mycket välkomna.

* **Buggrapporter** — se [`.github/ISSUE_TEMPLATE/bug_report.md`](.github/ISSUE_TEMPLATE/bug_report.md)
* **Reverse engineering-bidrag** — se [`CONTRIBUTING.md`](CONTRIBUTING.md) för metodiken
* **Funktionsförslag** — se [`.github/ISSUE_TEMPLATE/feature_request.md`](.github/ISSUE_TEMPLATE/feature_request.md)

Mest värdefulla bidrag just nu: testfiler för Smart Morph, Scene-snapshots, och verifiering på riktig Montage M-hårdvara.

---

## Friskrivning

Detta projekt är inte associerat med, godkänt eller sponsrat av Yamaha Corporation. MODX M, ESP plugin, Montage M och relaterade produktnamn är varumärken som tillhör Yamaha Corporation. Filformatet har reverse-engineerats för interoperabilitetsändamål. Använd på egen risk och håll alltid backuper på dina originalfiler.

---

## Licens

MIT — se [LICENSE](LICENSE)

