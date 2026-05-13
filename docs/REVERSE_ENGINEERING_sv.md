# Reverse Engineering Status

> 🇬🇧 **English:** [REVERSE_ENGINEERING.md](REVERSE_ENGINEERING.md)

Detta dokument innehåller detaljerad reverse engineering-status och metodik för YSFC Forge. För en översikt, se huvud-README:n.

## Innehållsförteckning

- [Methodology](#methodology)
- [Test Corpus](#test-corpus)
- Engine Coverage
- Coverage by Section
- Key Findings
- File Structure
- Encoding Reference
- What is Classified as Firmware Constants
- What is Not Yet Mapped
- Save Counter / Noise Bytes

- [Methodology](#methodology)
- [Test Corpus](#test-corpus)
- [Engine Coverage](#engine-coverage)
- [Coverage by Section](#coverage-by-section)
- [Key Findings](#key-findings)
- [File Structure](#file-structure)
- [Encoding Reference](#encoding-reference)
- [What is Classified as Firmware Constants](#what-is-classified-as-firmware-constants)
- [What is Not Yet Mapped](#what-is-not-yet-mapped)
- [Save Counter / Noise Bytes](#save-counter--noise-bytes)

---

## Methodology

YSFC-binärformatet (`.Y2L`, `.Y2U`) är inte officiellt dokumenterat av Yamaha. Varje parameter-offset i detta projekt har upptäckts genom binär differentialanalys:

1. Exportera en baseline-Performance från MODX M-hårdvara eller ESP plugin (vanligtvis en nedskalad "Init Voice" med en Part)
2. Ändra exakt en parameter via UI:t
3. Exportera den modifierade filen
4. Jämför de två filerna byte-för-byte (efter filtrering av save-counter-noise)
5. Registrera offset, encoding-typ och värdeintervall
6. Korsverifiera mellan alla Engine-typer för att skilja user fields från firmware constants

Denna metod har tillämpats iterativt över **2010+ verifierade testfiler** för att nå nuvarande 100% Engine coverage.

## Corpus analysis (advanced method)

För Engines med stora testkorpusar används en kraftfullare metod:

1. **Skanna alla testfiler efter byte-position constancy** — bytes som är 100% konstanta över alla testfiler klassificeras som firmware constants ([INTERN])
2. **Identifiera varierande bytes** — dessa är UI-fält; matcha varje byte mot den specifika testfil som ändrade den
3. **Stride pattern recognition** — när flera varierande bytes delar samma stride (t.ex. 123 bytes för FM-X Operators) tillhör de en repeterande struktur

Denna corpus-metod möjliggjorde den slutliga 100%-mappningen av AN-X och FM-X.

## Verification levels

Varje dokumenterat field har en stjärnklassning:

- **★★★★★** — Binärverifierad med en eller flera testfiler
- **★★★★☆** — Härledd från officiell source-data
- **★★★☆☆** — Troligen korrekt
- **★★☆☆☆** — Osäker
- **[INTERN]** — MODX-intern firmware constant
- **[STRUKT]** — Strukturellt identifierad

---

# Test Corpus

Reverse engineering-arbetet baseras på **2010+ binärverifierade testfiler** genererade genom systematiska parameterändringar på riktig MODX M-hårdvara.

| Engine | Filer | Andel |
|---|---:|---:|
| AN-X | 799 | 40% |
| FM-X | 425 | 21% |
| AWM2 | 408 | 20% |
| Drum | 84 | 4% |
| Other / multi-part | 294 | 15% |

---

# Engine Coverage

Alla fyra Engines är nu **100% binary-verified mapped**.

| Engine | UI fields | [INTERN] bytes | Status |
|---|---:|---:|---|
| AWM2 | 128 | 8 | 100% ✅ |
| AN-X | 171 | 458 | 100% ✅ |
| FM-X | 141 | 863 | 100% ✅ |
| Drum | 54 | 4934 | 100% ✅ |

---

# Key Findings

## File format

- `Y2L` och `Y2U` är byte-för-byte identiska
- Performance name börjar vid byte `perf[4]`
- Scene count: `perf[6695]`
- Engine type byte: `perf[6700]`
- Common-blob size är 6701 bytes
- Part Common stride är 5765 bytes

## Engine pool layout

- AWM2 engine pool: 3 header bytes + 8 Elements × 313-byte stride
- AN-X engine pool: 3 OSC × 124-byte stride
- FM-X engine pool: 8 OP × 123-byte stride
- Drum engine pool: 73 keys × 68-byte stride

---

# Encoding Reference

| Typ | Formel |
|---|---|
| direct u8 | `raw = value` |
| center=64 | `raw = value + 64` |
| center=128 | `raw = value + 128` |
| FM-X algorithm | `raw = algo − 1` |
| FM-X OP detune | `raw = value + 15` |
| Waveform number | u16 little-endian |
| Note MIDI value | u8 |

---

# What is Not Yet Mapped

## Scene parameter snapshots

Scene-strukturen är verifierad men endast cirka 10 fields per Scene har UI-bekräftade mappningar.

## Smart Morph

Interpolation tables och FM-X morphing state är inte mappade.

## Performance Editor tool (UI gap)

Även om binärformatet är 100% mappat exponeras ännu inte alla parametrar i Performance Editor UI:t.

---

# Save Counter / Noise Bytes

Följande bytes ändras vid varje save oavsett parameterändringar:

```text
abs 22-24, 60-63, 66, 232, 234, 358, 376, 396-399, 488, 654
```

Dessa bytes filtreras bort från diff-analys för att undvika false positives.
