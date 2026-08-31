# YSFC Forge

> 🇬🇧 **English:** [README.md](README.md)

[![License: MIT + LGPL-3.0 components](https://img.shields.io/badge/License-MIT%20%2B%20LGPL--3.0%20components-blue.svg)](#licens)
[![Status: Active](https://img.shields.io/badge/Status-Active-brightgreen.svg)]()
[![Engines: 4/4](https://img.shields.io/badge/Engines-4%2F4%20mapped-blue.svg)]()
[![Test files: 2010+](https://img.shields.io/badge/Test%20files-2010%2B-blue.svg)]()

**Webbläsarbaserade open-source-verktyg för Yamaha MODX M / ESP Plugin / MONTAGE M performancefiler.**

MODX M / MONTAGE M-verktygen för `.Y2L` / `.Y2U` är reverse-engineerade från grunden genom binäranalys av Yamahas odokumenterade filformat. Library Builder innehåller även experimentellt import-/konverteringsstöd för valda legacy MONTAGE/MODX `.X7L` / `.X8L`-performances och MONTAGE M `.X2L`-liknande short-layout-bibliotek.

Öppna HTML-filerna i vilken modern webbläsare som helst — ingen installation, ingen molnuppladdning, allt körs lokalt.

> Ett hobbyprojekt som började som ett sätt att sammanfoga .Y2L-bibliotek utan ändlöst klickande på hårdvaran, och växte till en djupgående kartläggning av formatet.

![Forge Performance Merger skärmdump](screenshots/image_ysfc_forge_performance_merger.png)

---

## Innehåll

* [Funktioner](#funktioner)
* [Snabbstart](#snabbstart)
* [Verktyg](#verktyg)
* [Status](#status)
* [Kända begränsningar](#kända-begränsningar)
* [Dokumentation](#dokumentation)
* [Bidra](#bidra)
* [Licens](#licens)

---

## Funktioner

* **Sammanfoga** performances från flera `.Y2L` / `.Y2U`-filer
* **Bygga** nya bibliotek från valda performances och deras nödvändiga beroenden
* **Experimentellt importera** valda legacy `.X7L` / `.X8L` och `.X2L`-liknande performances
* **Redigera** FM-X, AWM2 och AN-X-parametrar i webbläsaren
* **Ingen installation** — fungerar i Chrome, Firefox och Safari
* **Ingen telemetri** — allt körs lokalt
* Plus experimentella verktyg — se [Experimentella / extra verktyg](#experimentella--extra-verktyg)

---

## Snabbstart

### Sammanfoga performances

1. Ladda ner [`tools/ysfc_forge_performance_merger_v1_23.html`](tools/ysfc_forge_performance_merger_v1_23.html)
2. Öppna filen i din webbläsare
3. Dra och släpp `.Y2L`- eller `.Y2U`-filer
4. Markera de performances du vill ha
5. Klicka på **Save as Y2L** eller **Save as Y2U**
6. Importera den exporterade filen i MODX M / ESP plugin / Montage M

### Sammanfoga performances inklusive beroenden

1. Ladda ner [`tools/ysfc_forge_library_builder_v15_53.html`](tools/ysfc_forge_library_builder_v15_53.html)
2. Öppna filen i din webbläsare
3. Dra och släpp `.Y2L`- eller `.Y2U`-filer
4. Markera de performances du vill ha
5. Klicka på **Save as Y2L** eller **Save as Y2U**
6. Importera den exporterade filen i MODX M / ESP plugin / Montage M

### Redigera en performance

1. Ladda ner [`tools/ysfc_forge_performance_editor_v5_6.html`](tools/ysfc_forge_performance_editor_v5_6.html)
2. Öppna filen i din webbläsare
3. Klicka på **Open Y2L** och välj en fil
4. Justera parametrar med reglage
5. Klicka på **Export Y2L** för att spara

### Konvertera Yamaha sysex till Y2L

1. Ladda ner [`tools/ysfc_forge_sysex_converter_v1_59.html`](tools/ysfc_forge_sysex_converter_v1_59.html)
2. Dra in en eller flera Soundmondo `.syx`.
3. Kontrollera detekterad plattform, engines, Parts och dependency-varningar.
4. Ladda vid behov en companion `.Y2L` / `.Y2U` för externa waveform-dependencies.
5. Konvertera en fil eller kör bulkexport.
6. Ladda resultatet i MODX M / MONTAGE M / ESP och verifiera.

---

## Verktyg

### Huvudverktyg

|Verktyg|Vad det gör|
|-|-|
|[**Performance Merger**](tools/ysfc_forge_performance_merger_v1_23.html)|Sammanfoga performances från flera Y2L/Y2U-filer|
|[**Library Builder**](tools/ysfc_forge_library_builder_v15_53.html)|Sammanfoga valda performances och beroenden från Y2L/Y2U, med experimentellt stöd för legacy X7L/X8L och X2L-liknande import|
|[**Performance Editor**](tools/ysfc_forge_performance_editor_v5_6.html)|Redigera FM-X, AWM2 och AN-X-parametrar i webbläsaren|
|[**Sysex Converter**](tools/ysfc_forge_sysex_converter_v1_59.html)|ConKonvertera Yamaha sysex filer till Y2L|

### Experimentella / extra verktyg

> ⚠️ Detta är hjälp- och approximationsverktyg — **inte** hållna till samma binärverifierade standard som kärnverktygen ovan.

|Verktyg|Vad det gör|
|-|-|
|[**Smart Name Compressor**](utilities/ysfc_smart_name_compressor.html)|Standardiserad namngivning för performances|

### Skärmdumpar

|||
|-|-|
|![Performance Editor](screenshots/image_ysfc_forge_performance_editor.png)|![Library Builder](screenshots/image_ysfc_forge_library_builder.png)|
|*Performance Editor — FM-X-operatorredigerare*|*Library Builder — performancelista med engine-detektering*|

---

## Status

Alla fyra synth-**engines** har **varje känt användarredigerbart parameterfält binärverifierat** genom systematisk A/B-diffanalys över 2010+ testexporter på riktig MODX M-hårdvara. Filnivåstrukturer som Smart Morph och Scene-snapshots är kartlagda separat — se [Kända begränsningar](#kända-begränsningar).

|Engine|UI-fält|Intern/firmware konstanter|Status|
|-|-:|-:|-|
|**AWM2**|128|8|✅ Verifierad|
|**AN-X**|171|458|✅ Verifierad|
|**FM-X**|141|863|✅ Verifierad|
|**Drum**|54|4934|✅ Verifierad|

> *Kartläggningen återspeglar alla parametrar som observerats över de 2010+ testexporterna. Formatet är odokumenterat, så det är möjligt att en sällan använd parameter existerar som ännu inte dykt upp i testning — hittar du en är en testfil som visar den det mest värdefulla du kan bidra med.*

> *"Intern/firmware konstanter" räknar de bytes i varje engines datablock som inte är användarredigerbara — firmware-konstanter, uppslagstabeller och padding som är identiska oavsett UI-inställningar. Ett högt tal är ingen lucka: det betyder att hela blocket är kartlagt och varje byte redovisad, inte bara parametrarna. (Drum keys är t.ex. en avsiktligt gles struktur — bara en handfull bytes per key är aktiva.)*

### Filtyper som stöds

|Typ|Beskrivning|Stöd|
|-|-|-|
|`.Y2L`|MODX M / MONTAGE M-biblioteksfil|✅|
|`.Y2U`|MODX M / MONTAGE M-användarfil (samma format som Y2L, annan filändelse)|✅|
|`.X7L` / `.X7U`|Legacy MONTAGE biblioteks-/användarfiler|🧪 Experimentell import/konvertering|
|`.X8L` / `.X8U`|Legacy MODX / MODX+ biblioteks-/användarfiler|🧪 Experimentell import/konvertering|
|`.X2L`-liknande layout|MONTAGE M short-layout bibliotekvariant|🧪 Experimentell performancekonvertering|
|**Multi/GM 16-part**|16 parts (15 AWM2 + 1 Drum på Part 10)|✅|

### Hårdvarukompatibilitet

|Hårdvara|Stöd|
|-|-|
|MODX M|✅ Primärt mål|
|ESP plugin|✅|
|MONTAGE M|⚠️ Testad via ESP/plugin; hårdvarutäckning utökas fortfarande|
|MONTAGE / MODX / MODX+|🧪 Endast experimentell import via Library Builder-konvertering|

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

### Library Builder

Library Builder är byggd för att exportera valda performances och deras nödvändiga beroenden. Den är inte avsedd att klona varje del av ett komplett bibliotek.

Bevaras inte i nuläget:

* Live Sets
* Patterns
* Favorites och viss enhets-/biblioteksmetadata
* Garanterat byte-identiska exporter för alla tredjepartsbibliotek

Legacy `.X7L` / `.X8L` och `.X2L`-liknande stöd är experimentellt. Håll alltid backuper på dina originalfiler och testa exporterade bibliotek noggrant i ESP eller på hårdvara innan de används skarpt.

### Performance Editor

* **Performance Editor** visar i nuläget bara den första partens engine; redigering av alla 16 parts är på roadmap
* **Smart Morph**-interpolationstabeller är inte kartlagda än
* **Scene-snapshots** — strukturen är verifierad, men endast ~10 fält per scen har UI-bekräftade mappningar
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

## Dataattribuering

Vissa referenstabeller i Python-enum-paketet är **härledda från Yamahas publicerade MODX M Data List** (© Yamaha Corporation). Endast funktionella fakta har extraherats, uteslutande för att möjliggöra tolkning av det odokumenterade .Y2L / .Y2U-filformatet för interoperabilitet. Andra referenstabeller i Python-enum-paketet bygger på projektets egna binärverifierade observationer av MODX M och ESP Plugin-gränssnittet.

Yamahas dokument **återdistribueras inte** i detta repo. Originalet finns hos Yamaha (sök efter "MODX M Data List").

---

## ConvertWithMoss-attribuering

Stödet för legacy MONTAGE/MODX `.X7L` / `.X8L` bygger delvis på, och är i vissa delar härlett från, open-source-projektet **ConvertWithMoss** av Jürgen Moßgraber.

ConvertWithMoss:
https://github.com/git-moss/ConvertWithMoss

ConvertWithMoss är licensierat under GNU Lesser General Public License v3.0. All YSFC Forge-kod, struktur eller logik som är härledd från ConvertWithMoss används och distribueras enligt villkoren i LGPL-3.0. Se [`licenses/LGPL-3.0.txt`](licenses/LGPL-3.0.txt).

`.Y2L` / `.Y2U`-research, MODX M / MONTAGE M-engine mapping, webbläsargränssnitt och icke-legacy-konverteringslogik i YSFC Forge bygger på egen reverse engineering, testning och binärjämförelse mot Yamaha-hårdvara och ESP plugin-exporter.

---

## Licens

Huvuddelen av YSFC Forge-projektet släpps under MIT License — se [LICENSE](LICENSE).

Vissa legacy MONTAGE/MODX `.X7L` / `.X8L`-komponenter bygger på eller är härledda från ConvertWithMoss och distribueras under GNU Lesser General Public License v3.0. Se [`licenses/LGPL-3.0.txt`](licenses/LGPL-3.0.txt) och relevanta filheaders i källkoden.
