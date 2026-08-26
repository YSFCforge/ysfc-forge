# YSFC Forge

> 🇸🇪 **Svenska:** [README_sv.md](README_sv.md)

[![License: MIT + LGPL-3.0 components](https://img.shields.io/badge/License-MIT%20%2B%20LGPL--3.0%20components-blue.svg)](#license)
[![Status: Active](https://img.shields.io/badge/Status-Active-brightgreen.svg)]()
[![Engines: 4/4](https://img.shields.io/badge/Engines-4%2F4%20mapped-blue.svg)]()
[![Test files: 2010+](https://img.shields.io/badge/Test%20files-2010%2B-blue.svg)]()

**Open-source browser-based tools for Yamaha MODX M / ESP Plugin / MONTAGE M performance files.**

The MODX M / MONTAGE M `.Y2L` / `.Y2U` tooling is reverse-engineered from scratch through binary analysis of Yamaha's undocumented file format. The Library Builder also includes experimental import/conversion support for selected legacy MONTAGE/MODX `.X7L` / `.X8L` Performances and MONTAGE M `.X2L`-style short-layout libraries.

Open the HTML files in any modern browser — no installation, no cloud upload, everything runs locally.

> A hobby project that started as a way to merge .Y2L libraries without endless clicking on the hardware, and grew into an in-depth mapping of the format.

![Forge Performance Merger screenshot](screenshots/image_ysfc_forge_performance_merger.png)

---

## Table of Contents

* [Features](#features)
* [Quick Start](#quick-start)
* [Tools](#tools)
* [Status](#status)
* [Known Limitations](#known-limitations)
* [Documentation](#documentation)
* [Contributing](#contributing)
* [License](#license)

---

## Features

* **Merge** performances from multiple `.Y2L` / `.Y2U` files
* **Build** new libraries from selected Performances and their required dependencies
* **Experimentally import** selected legacy `.X7L` / `.X8L` and `.X2L`-style Performances
* **Edit** FM-X, AWM2 and AN-X parameters in the browser
* **No installation** — works in Chrome, Firefox and Safari
* **No telemetry** — everything runs locally
* Plus experimental tools/utilities — see [Experimental / Extra Tools](#experimental--extra-tools)

---

## Quick Start

### Merge performances

1. Download [`tools/ysfc_forge_performance_merger_v1_23.html`](tools/ysfc_forge_performance_merger_v1_23.html)
2. Open it in your browser
3. Drag and drop `.Y2L` or `.Y2U` files
4. Select the performances you want
5. Click **Save as Y2L** or **Save as Y2U**
6. Import the exported file in MODX M / ESP plugin / Montage M

### Merge performances including dependencies

1. Download [`tools/ysfc_forge_library_builder_v15_48.html`](tools/ysfc_forge_library_builder_v15_48.html)
2. Open it in your browser
3. Drag and drop `.Y2L` or `.Y2U` files
4. Select the performances you want
5. Click **Save as Y2L** or **Save as Y2U**
6. Import the exported file in MODX M / ESP plugin / Montage M

### Edit a performance

1. Download [`tools/ysfc_forge_performance_editor_v5_6.html`](tools/ysfc_forge_performance_editor_v5_6.html)
2. Open it in your browser
3. Click **Open Y2L** and choose a file
4. Adjust parameters with sliders
5. Click **Export Y2L** to save

### Convert Yamaha sysex to Y2L

1. Download [`tools/ysfc_forge_sysex_converter_v1_59.html`](tools/ysfc_forge_sysex_converter_v1_59.html)
2. Drag one or more Soundmondo `.syx` files onto the import area.
3. Review detected platform, engines, Parts and dependency warnings.
4. Optionally load a companion `.Y2L` / `.Y2U` when external waveform dependencies must be resolved.
5. Convert one file or use bulk conversion.
6. Load the resulting Y2L in MODX M / MONTAGE M / ESP and verify the result. 

---

## Tools

### Core Tools

|Tool|What it does|
|-|-|
|[**Performance Merger**](tools/ysfc_forge_performance_merger_v1_23.html)|Merge performances from multiple Y2L/Y2U files|
|[**Library Builder**](tools/ysfc_forge_library_builder_v15_48.html)|Merge selected Performances and dependencies from Y2L/Y2U, with experimental legacy X7L/X8L and X2L-style import support|
|[**Performance Editor**](tools/ysfc_forge_performance_editor_v5_6.html)|Edit FM-X, AWM2 and AN-X parameters in the browser|
|[**Sysex Converter**](tools/ysfc_forge_sysex_converter_v1_59.html)|Convert Yamaha sysex files to Y2L|

### Experimental / Extra Tools

> ⚠️ These are convenience and approximation tools — **not** held to the same binary-verified standard as the core tools above.

|Tool|What it does|
|-|-|
|[**Smart Name Compressor**](utilities/ysfc_smart_name_compressor.html)|Standardized naming for performances|

### Screenshots

||||
|-|-|-|
|![Performance Editor](screenshots/image_ysfc_forge_performance_editor.png)|![Library Builder](screenshots/image_ysfc_forge_library_builder.png)||
|*Performance Editor — FM-X operator editor*|*Library Builder — performance list with engine detection*||

---

## Status

All four synthesizer **engines** have **every known user-editable parameter binary-verified** through systematic A/B diff analysis across 2010+ test exports on real MODX M hardware. File-level structures such as Smart Morph and Scene snapshots are mapped separately — see [Known Limitations](#known-limitations).

|Engine|UI fields|Internal/firmware constants|Status|
|-|-:|-:|-|
|**AWM2**|128|8|✅ Verified|
|**AN-X**|171|458|✅ Verified|
|**FM-X**|141|863|✅ Verified|
|**Drum**|54|4934|✅ Verified|

> *Mapping reflects all parameters observed across the 2010+ test exports. The format is undocumented, so it's possible a rarely-used parameter exists that hasn't appeared in testing yet — if you find one, a test file showing it is the single most useful thing you can contribute.*

> *"Internal/firmware constants" counts the bytes in each engine's data block that are not user-editable — firmware constants, lookup tables and padding that stay identical regardless of UI settings. A high number isn't a gap: it means the entire block was mapped and every byte accounted for, not just the parameters. (Drum keys, for example, are a deliberately sparse structure — only a handful of bytes per key are active.)*

### Supported file types

|Type|Description|Support|
|-|-|-|
|`.Y2L`|MODX M / MONTAGE M library file|✅|
|`.Y2U`|MODX M / MONTAGE M user file (same format as Y2L, different extension)|✅|
|`.X7L` / `.X7U`|Legacy MONTAGE library/user files|🧪 Experimental import/conversion|
|`.X8L` / `.X8U`|Legacy MODX / MODX+ library/user files|🧪 Experimental import/conversion|
|`.X2L`-style layout|MONTAGE M short-layout library variant|🧪 Experimental Performance conversion|
|**Multi/GM 16-part**|16 parts (15 AWM2 + 1 Drum on Part 10)|✅|

### Hardware compatibility

|Hardware|Support|
|-|-|
|MODX M|✅ Primary target|
|ESP plugin|✅|
|MONTAGE M|⚠️ Supported in ESP/plugin tests; hardware coverage still expanding|
|MONTAGE / MODX / MODX+|🧪 Experimental import only via legacy Library Builder conversion|

### Test corpus

**2010+ binary-verified test files** generated through systematic parameter changes on real MODX M hardware. Every documented offset is backed by at least one A/B binary diff.

|Engine|Files|
|-|-:|
|AN-X|799|
|AWM2|408|
|FM-X|425|
|Drum|84|
|Other|294|

See [`docs/REVERSE_ENGINEERING.md`](docs/REVERSE_ENGINEERING.md) for detailed methodology, coverage tables and field-level documentation.

---

## Documentation

|Document|Contents|
|-|-|
|[`docs/REVERSE_ENGINEERING.md`](docs/REVERSE_ENGINEERING.md)|Methodology, coverage tables, technical highlights|
|[`docs/YSFC_FORGE_REFERENCE.md`](docs/YSFC_FORGE_REFERENCE.md)|Compact reference manual|
|[`docs/YSFC_FORGE_FULL_CONTEXT.md`](docs/YSFC_FORGE_FULL_CONTEXT.md)|Complete technical reference (all field positions, evidence)|
|[`serializer/ysfc_serializer.py`](serializer/ysfc_serializer.py)|Python parameter constants — useful if you want to build your own tools|

### Verification levels

Throughout the documentation, fields are rated by evidence:

* **★★★★★** — Binary-verified with one or more test files
* **★★★★☆** — Derived from official source data, highly confident
* **★★★☆☆** — Likely correct, not binary-verified
* **[INTERN]** — MODX-internal firmware constant, not user-editable

---

## Known Limitations

### Library Builder

The Library Builder is designed to export selected Performances and their required dependencies. It is not intended to clone every part of a complete library.

Currently not preserved:

* Live Sets
* Patterns
* Favorites and some device-side library metadata
* Guaranteed byte-identical exports for every third-party library

Legacy `.X7L` / `.X8L` and `.X2L`-style support is experimental. Always keep backups of your original files and test exported libraries carefully in ESP or on hardware before using them in production.

### Performance Editor

* **Performance Editor** currently shows only the first part's engine; full 16-part editing is on the roadmap
* **Smart Morph** interpolation tables are not yet mapped
* **Scene snapshots** — structure verified, but only ~10 fields per scene have UI-confirmed mappings
* **No undo/redo** in Performance Editor yet — keep backups of your originals

See [`docs/REVERSE_ENGINEERING.md`](docs/REVERSE_ENGINEERING.md) for the full list.

---

## Contributing

Bug reports, test files and reverse engineering findings are very welcome.

* **Bug reports** — see [`.github/ISSUE_TEMPLATE/bug_report.md`](.github/ISSUE_TEMPLATE/bug_report.md)
* **Reverse engineering contributions** — see [`CONTRIBUTING.md`](CONTRIBUTING.md) for the methodology
* **Feature requests** — see [`.github/ISSUE_TEMPLATE/feature_request.md`](.github/ISSUE_TEMPLATE/feature_request.md)

The most valuable contributions right now: test files for Smart Morph, Scene snapshots, and verification on real Montage M hardware.

---

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by Yamaha Corporation. MODX M, ESP plugin, Montage M and related product names are trademarks of Yamaha Corporation. The file format was reverse-engineered for interoperability purposes. Use at your own risk and always keep backups of your original files.

---

## Data Attribution

Some reference tables in the Python enum package are **derived from Yamaha's publicly published MODX M Data List** (© Yamaha Corporation). Only functional facts have been extracted, solely to enable interpretation of the undocumented `.Y2L` / `.Y2U` file format for interoperability purposes. Other reference tables in the Python enum package are based on the project's own binary-verified observations of the MODX M and ESP Plugin interface.

Yamaha's document is **not redistributed** in this repository. The original is available from Yamaha (search for "MODX M Data List").

---

## ConvertWithMoss Attribution

The legacy MONTAGE/MODX `.X7L` / `.X8L` support is partly informed by, and in some areas derived from, the open-source **ConvertWithMoss** project by Jürgen Moßgraber.

ConvertWithMoss:
https://github.com/git-moss/ConvertWithMoss

ConvertWithMoss is licensed under the GNU Lesser General Public License v3.0. Any YSFC Forge code, structure or logic derived from ConvertWithMoss is used and distributed under the terms of the LGPL-3.0. See [`licenses/LGPL-3.0.txt`](licenses/LGPL-3.0.txt).

The `.Y2L` / `.Y2U` format research, MODX M / MONTAGE M engine mapping, browser UI and non-legacy conversion logic in YSFC Forge are based on independent reverse engineering, testing and binary comparison against Yamaha hardware and ESP plugin exports.

---

## License

The main YSFC Forge project is released under the MIT License — see [LICENSE](LICENSE).

Some legacy MONTAGE/MODX `.X7L` / `.X8L` support components are based on or derived from ConvertWithMoss and are distributed under the GNU Lesser General Public License v3.0. See [`licenses/LGPL-3.0.txt`](licenses/LGPL-3.0.txt) and the relevant source file headers.
