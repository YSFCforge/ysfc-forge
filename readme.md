# YSFC Forge

**Open-source browser-based tools for Yamaha MODX M / ESP Plugin / Montage M performance files**

Reverse-engineered tools for Yamaha MODX M / ESP Plugin / Montage M performance files.

**Built from scratch through binary analysis of Yamaha's undocumented file format.**

Open the HTML files in any modern browser. Drag, drop, merge, edit and export `.Y2L` / `.Y2U` files directly in your browser.

No installation.
No cloud upload.
Everything runs locally on your computer.

---

## What is YSFC Forge?

YSFC Forge is an open-source ecosystem for exploring, editing and translating Yamaha MODX M / ESP Plugin / Montage M performance files.

The project combines:

- Librarian workflows
- Performance editing
- Binary reverse engineering
- Cross-synth translation
- Parameter mapping
- Browser-based tooling
- Offline-first workflows
- Technical documentation and preservation

YSFC Forge was built from scratch through binary analysis of Yamaha’s undocumented file formats.

---

## Why this project exists

Yamaha MODX M / ESP Plugin / Montage M file formats are largely undocumented.

YSFC Forge was created to:

- Understand the internal binary structures
- Build modern browser-based tooling
- Simplify performance management
- Explore cross-synth translation workflows
- Create tools Yamaha never released
- Make advanced editing accessible offline

---

## 🎛 Tools

> **No installation.** Download an HTML file, open it in Chrome, Firefox or Safari, and start working.

🎛 Core Tools

| Tool | File | What it does |
|------|------|-------------|
| **Forge Librarian** | `tools/ysfc_forge_v1.19.html` | Merge performances from multiple Y2L/Y2U files into one export |
| **Performance Editor** | `tools/ysfc_performance_editor_v3.html` | Edit FM-X, AWM2 and AN-X parameters directly in the browser |

🔄 Translators

| Tool | File | What it does |
|---------|-----|-------------|
| **DIVA Patch Translator** | `translators/ysfc_diva_h2p_converter_v2_15.html` | Analyze and convert DIVA patches to Y2L/Y2U files and load them into Yamaha MODX M / ESP Plugin / Montage M |
| **Vital Patch Translator** | `translators/ysfc_vital_converter_v4_12.html` | Analyze and convert Vital patches to Y2L/Y2U files and load them into Yamaha MODX M / ESP Plugin / Montage M |
| **Synth1 Patch Translator** | `translators/ysfc_synth1_converter_v5_12.html` | Analyze and convert Synth1 patches to Y2L/Y2U files and load them into Yamaha MODX M / ESP Plugin / Montage M |

🧰 Utilities

| Tool | File | What it does |
|---------|-----|-------------|
| **ESP Librarian** | `utilities/ysfc_esp_librarian_v7.html` | Standalone prototype librarian to merge performances |
| **Smart Performance Name Compressor** | `utilities/ysfc_smart_name_compressor.html` | Standalone prototype for easy standardized naming conventions of Yamaha MODX M performances |
| **Synth Converter** | `utilities/ysfc_synth_converter.html` | Convert DIVA, Vital and Synth1 patches between different formats (8+) |

---

## 📸 Screenshots

<!-- Add your screenshots here -->
*Forge Librarian — drag and drop Y2L files, select performances, export*
![Forge Librarian](screenshots/image_ysfc_forge_v1_19.png)

*Performance Editor — edit FM-X, AWM2 and AN-X parameters directly in the browser*
![Performance Editor](screenshots/image_ysfc_performance_editor_v4.png)

*ESP Librarian — performance list with engine detection and dependency summary*
![ESP Librarian](screenshots/image_ysfc_esp_librarian_v7.png)

*DIVA Patch Translator — analyze and convert DIVA patches to Y2L/Y2U files + other file formats (also see Vital Patch Translator and Synth1 Patch Translator)*
![DIVA Patch Translator](screenshots/ysfc_diva_h2p_converter_v2_16.png)

---

## 🚀 Quick Start

### Merge performances from multiple files
1. Download `tools/ysfc_forge_v1.19.html`
2. Open it in your browser
3. Drag and drop your `.Y2L` or `.Y2U` files
4. Select the performances you want
5. Click **Save as Y2L** or **Save as Y2U**
6. Import the exported file in MODX M / Montage M

### Edit a performance
1. Download `tools/ysfc_performance_editor_v3.html`
2. Open it in your browser
3. Click **Open Y2L** and choose a file
4. Select a section from the left panel (operators, filter, LFO, etc.)
5. Adjust parameters with sliders
6. Click **Export Y2L** to save

---

# 🔬 Reverse Engineering Status

| Area | Coverage |
|---|---|
| FM-X Operators | ~100% |
| FM-X PEG | 100% |
| FM-X LFO | 100% |
| AWM2 | ~95% |
| AN-X | ~99% |
| Motion Sequencer | 100% |
| Arp Common | 100% |
| FX Types | 57 verified |
| Total mapped parameters | ~665 |

Detailed parameter tables and binary documentation are available in:

`docs/YSFC_FORGE_FULL_CONTEXT_v10.md`

---

# ⚙ Supported Hardware and Formats

| | Support |
|-|---------|
| MODX M | ✅ Primary target |
| ESP plugin | ✅ |
| Montage M | Likely compatible — not fully tested |
| `.Y2L` (Library file) | ✅ |
| `.Y2U` (User file) | ✅ Identical binary format — only the extension differs |
| `.X7L` / `.X8L` | ✅ As merge source (not as export container) |

### Engines
| Engine | Librarian | Patch Editor |
|--------|-----------|--------------|
| FM-X | ✅ | ✅ All 8 operators, algorithm, PEG, LFO, Filter, FM Color |
| AWM2 | ✅ | ✅ Elements, filter, AEG, waveform number |
| AN-X | ✅ | ✅ OSC, Filter 1/2, WaveFolder, ModEG |
| DRUM | Detected | — |

---

# 🧠 Technical Highlights

- ~665 mapped parameters
- Binary-verified offsets
- Full Y2L/Y2U container documentation
- Browser-based serialization workflows
- Reverse-engineered FX index tables
- Multi-engine parameter parsing
- Offline-first architecture

---

# 🔒 Philosophy

YSFC Forge is designed around:

- Offline-first workflows
- No telemetry
- Browser-native tooling
- Open reverse engineering
- Human-readable tooling
- Local-only processing

---

## How it works

The YSFC binary format (`.Y2L`, `.Y2U`) is **not officially documented by Yamaha**. Every parameter offset in this project was discovered through binary differential analysis:

1. Export a test file from the MODX M hardware or ESP plugin with one known parameter changed
2. Compare it byte-by-byte against a baseline file
3. Record the offset, encoding and range
4. Repeat — 71+ rounds of testing, across 665 documented parameter fields

The result is **Serializer v6** — a verified parameter map covering approximately 99% of all editable parameters across FM-X, AWM2 and AN-X engines.

### Key findings
- `Y2L` and `Y2U` are byte-for-byte identical — only the file extension changes how ESP presents the import dialog
- Performance name: bytes `perf[4:20]`, null-terminated. Bytes `perf[20:24]` contain a flash address for waveform samples — do not zero-fill this area. See blob format note below
- Scene count: `perf[6695]`, range 1–8
- AWM2 Filter EG (Attack/Decay/Sustain/Release) exists **only at Part level**, not per element
- AN-X PitchEGDepth encoding: `raw = round(UI_cent × 247/4800) + 247`, range ±4800 cents
- Expansion pack detection: `waveformNumber > 256` in any AWM2 element means the performance requires a Y2E expansion pack installed on the synth

### Blob format note — third-party library files

The bytes immediately after the performance name (`blob[null_pos+1:24]`) must be correctly formatted for MODX to load the file without a "Storage read/write error". Specifically:

- `blob[null_pos+1:20]` must be zero-padded
- `blob[20:24]` must contain the correct waveform flash address (`0x15bcXXXX`) or `0x00000000` if no ROM sample is referenced

Files exported directly from Yamaha MODX M / ESP Plugin always have correct values. Library files from third-party sources may have legacy placeholder values in these bytes. The Forge Librarian and ESP Librarian both apply `sanitizePerfBlob()` to correct this automatically on export.

### Parameter coverage

The table below counts **individual parameter fields** across all sections.
FM-X OP fields are counted once (per operator) — the same 29 fields repeat across all 8 operators.
AWM2 Element fields are counted as the total across all 8 elements.

| Engine / Section | Fields | Notes | Coverage |
|-----------------|--------|-------|----------|
| FM-X — OP (per operator × 8) | 29 | Coarse, Fine, Detune, AEG, PEG, Level, Spectral Form… | 100% |
| FM-X — Part PEG | 16 | Pitch EG levels and times | 100% |
| FM-X — Part LFO 1st | 11 | Wave, Speed, Delay, Fade, KeyOnReset… | 100% |
| FM-X — Part LFO 2nd | 8 | Wave, Speed (Normal/Extended), Phase, Delay… | 100% |
| FM-X — Part Common | 15 | Algorithm, Feedback, Filter, FM Color, Volume… | 100% |
| AWM2 — Element (8 elements total) | 150 | Waveform, AEG, Filter, Pan, Vel limits per element | ~95% |
| AWM2 — Part | 26 | Filter EG, AEG Offset, Volume, AT Register… | 100% |
| AN-X — Part | 130 | OSC 1–3, Filter 1–2, WaveFolder, ModEG, EGs… | ~99% |
| Insertion FX | 57 | 57 verified FX types (THRU → Wave Folder) | 100% |
| Controller Assign | 8 | Source, Destination, Curve, Polarity (Part + Perf) | 100% |
| Performance Common | 10 | Name, Volume, Pan, Portamento… | 100% |
| Scene metadata | 2 | Scene count, last active scene | 100% |
| AfterTouch Register | 2 | Switch, Destination (Pitch / Filter Cutoff) | 100% |
| SuperKnob + Assign values | 20 | SuperKnob value, Assign1-8 values and switches | 100% |
| Assign positioners | 25 | Left/Mid/Right position per assign, MidPos enable | 100% |
| Arp Common | 34 | Loop, Hold, Unit, NoteLimit, VelLimit, Swing, Octave… | 100% |
| Motion Sequencer (4 lanes) | 116 | LaneSwitch, Speed, Sync, Delay, FadeIn, Pulse A/B… | 100% |
| Metadata flags | 4 | ArpMaster, MSMaster, Part seq/arp state fields | 100% |
| **Total** | **~665** | | **~99%** |

> **Note on counting:** "Fields" means distinct binary parameters in the DPFM chunk.
> A field like FM-X OP Level appears 8 times (once per operator) but is counted as 1 in the per-OP column.
> Insertion FX counts the number of verified FX types, not the number of per-FX parameter bytes.

**What is not yet mapped in detail:**
- Scene parameter snapshots (which parameter values each scene stores)
- Smart Morph
- FM-X 2nd LFO depth matrix (`abs=12547+`)
- Two unknown AN-X fields (`PART+5934`, `PART+5952`)

---

## Repository structure

```
ysfc-forge/
├── tools/
│   ├── ysfc_forge_v1.19.html               # Librarian / merge tool
│   ├── ysfc_performance_editor_v3.html     # Patch editor (FM-X, AWM2, AN-X)
├── translators/
│   └── ysfc_diva_h2p_converter_v2_15.html  # Convert DIVA patches
│   └── ysfc_vital_converter_v4_12.html     # Convert Vital patches
│   └── ysfc_synth1_converter_v5_12.html    # Convert Synth1 patches
├── utilities/
│   └── ysfc_esp_librarian_v7.html          # Prototype librarian
│   ├── ysfc_smart_name_compressor.html     # Easy standardized naming conventions
│   ├── ysfc_synth_converter.html           # Convert patches
├── serializer/
│   ├── ysfc_serializer_v6.py               # Python parameter constants (v6)
│   └── ysfc_fx_type_index.py               # Insertion FX type index
├── docs/
│   ├── readme_svensk_version.txt           # Information in Swedish
│   ├── YSFC_FORGE_FULL_CONTEXT_v10.md      # Full technical documentation 
│   ├── YSFC_FORGE_FULL_CONTEXT_v10_svensk_version.md  # Full technical documentation (Swedish)
│   ├── ysfc_parameterbetyg_v7_en.txt       # Parameter ratings and offsets
│   ├── ysfc_parameterbetyg_v7_svensk_version.txt       # Parameter ratings and offsets (Swedish)
└── README.md

```

---

## Technical documentation

Detailed parameter tables, encoding formulas and binary analysis notes are in [`docs/YSFC_FORGE_FULL_CONTEXT_v10.md`](docs/YSFC_FORGE_FULL_CONTEXT_v10.md).

The Python serializer (`serializer/ysfc_serializer_v6.py`) contains all verified absolute offsets, encoding types and defaults as named constants — useful if you want to build your own tools.

### Encoding reference (selected)

| Type | Formula |
|------|---------|
| direct u8 | `raw = value` |
| center=64 | `raw = value + 64` |
| center=128 | `raw = value + 128` |
| AN-X PulseWidth | `raw = round(pct × 256/100)` |
| AN-X SelfSyncPitch | `raw = round(UI/25) + 256` |
| AN-X Filter FEGDepth | `raw = round(UI/50) + 256`, range ±12700 cents |
| AN-X PitchEGDepth | `raw = round(UI_cent × 247/4800) + 247`, range ±4800 cents |
| AN-X Assign / SuperKnob value | u16 little-endian, default=512 |
| FM-X algorithm | `raw = algo − 1` |
| FM-X OP detune | `raw = value + 15` |
| InsA/B TypeIndex | `lo = idx & 0x7F`, `hi = (idx >> 7) & 0x7F` |
| Waveform number | u16 little-endian, 1-based |

---

# ⚠ Known Limitations

- **Samples and waveforms** — The tools merge performances. Standalone user waveform expansions are not handled automatically (though the ESP Librarian tracks EWFM/DWFM dependencies).
- **X7L / X8L as container** — These formats cannot be used as export containers. Load them into your synth and export as Y2L first.
- **Montage M (original)** — The format is likely identical to MODX M. Untested.
- **Scene parameter snapshots** — Scene count is detected (`perf[6695]`), but the per-scene parameter snapshot data is not yet fully mapped.
- **Smart Morph** — Not mapped.
- **Multi-part performances** — Engine detection handles mixed-engine parts (AWM2 + FM-X etc.) but the patch editor currently shows the first part's engine only.
- **Third-party library files** — Files from other sources may have non-standard blob header values. The Forge Librarian corrects known cases automatically via `sanitizePerfBlob()`, but performances not in the correction table may still fail to load if their waveform flash address is wrong.

---

# 🤝 Contributing

This repository contains several experimental tools. Active development and bug tracking is focused on Forge Librarian (ysfc_forge_v1.19.html). Issues and PRs for that tool are welcome. The other tools are provided as-is without active support.

The main active development focus is currently:
- Forge Librarian
- Reverse engineering documentation

Remaining unknowns (as of Serializer v6):
- `AN-X PART+5934` — unknown field (MIDI formula was incorrect)
- `AN-X PART+5952` — unknown field
- WaveFolder modulation parameters (VelSens, EGDepth, LFODepth) — offsets derived from MIDI spec, not binary-verified
- FM-X 2nd LFO depth matrix (`abs=12547+`)
- Scene parameter snapshots — we know how many scenes exist, but not which parameter values each scene stores
- Smart Morph — not mapped
- Performance Common `abs=0–6707` — most of these ~6700 bytes have not been systematically mapped beyond the fields listed above

---

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by Yamaha Corporation. MODX M, ESP plugin, Montage M and related product names are trademarks of Yamaha Corporation. The file format was reverse-engineered for interoperability purposes. Use at your own risk and always keep backups of your original files.

---

## License

MIT — see [LICENSE](LICENSE)
