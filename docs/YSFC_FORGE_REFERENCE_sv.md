# YSFC Forge — Kompakt referens

Patch-editor och reverse-engineering-projekt för Yamaha MODX M / Montage M binärformatet (Y2L/Y2U).

**Hårdvara:** MODX M8 firmware 3.0, ESP Plugin v3.0<br>
**Källa:** Binärverifierade single-edit-testfiler mot Init Voice baselines (AWM2, AN-X, FM-X, Drum)<br>
**Dataattribuering:** Referenstabeller för är härledda ur Yamahas publicerade MODX M Data List (© Yamaha Corporation) för interoperabilitet; dokumentet återdistribueras inte. Se huvuddokumentet [README](../README_sv.md#dataattribuering ).

---

## Status

| Engine | Mappade fält | UI-täckning |
|---|---:|---:|
| AWM2 (per element × 8..128) | 128 fält + 8 [INTERN] | ✅ **Verifierad** |
| AN-X (engine totalt) | 171 fält + 458 [INTERN] | ✅ **Verifierad** |
| FM-X (Pre-OP + 8 × OP) | 141 fält + 863 [INTERN] | ✅ **Verifierad** |
| Drum (per key × 73) | 27 key-fält + 27 Part Common | ✅ **Verifierad** |
| Part Common | 88 fält (AWM2/FM-X/AN-X) + 6 (Drum) | ✅ Kärna verifierad |

**Total fält-positioner i serializer:** ~2057
**Testkorpus:** 2010+ binärverifierade filer

Alla fyra engines är binärverifierade (alla kända parametrar). Multi/GM 16-part-filer stöds via multi-part-arkitekturen (Performance Common + 16 × Part Common stride 5765 + Engine Pool med 15 AWM2 + 1 Drum på Part 10).

---

## Performance ↔ Waveform-koppling & selektiv export

En performance refererar en USER-waveform via fasta DPFM-blob-strukturer:
`SIG_A` = `00 00 00 28 01 XX YY 00 [ID] 00 01 00 01`, `SIG_B` =
`01 00 00 00 01 00 0C 00 [ID] 00 40`. Byten efter `0x28` är bank
(`01`=user → `[ID]` indexerar EWFM/EWIM-katalogen; `00`=preset, ignoreras).
Katalog-ID = `recPayload[10:12]` (BE u16).

**Renumreringsregel:** sortera unika refererade gamla ID:n → tilldela `1..N`
(1-baserat). Patcha varje `[ID]`-byte gammalt→nytt i behållna blobbar; skriv
nya ID:n i ombyggda EWFM/EWIM. Ren renumrering rör bara `[ID]`-byten.
Arp-refs sitter efter en `80 00`-pitch-serie + valfri `00`-pad som
`([ARP_ID] 2f)`-par (id<21, kan upprepas ≤4×); renumrering är identisk men
**0-baserad** (sortera unika refererade arp-ID:n → `0..N-1`). EARP/DARP byggs
om selektivt; blob-arp-`[ID]`-byte ompekas gammalt→nytt.

**Storlek.** Y2L-beroende-sektioner, DPFM-performance-poolen och
EPFM-performance-indexet storleksanpassas alla exakt efter payload (MODX
avvisar varje storleksfält-/data-slack): uniform 8-byte-per-blob-framing,
`exactSize = Σ(8 + payload) − 4 + 8`. Containern använder ESP:s exakta
12-chunk-layout (`EPFM EWFM EARP ESYS EFVT EWIM DPFM DWFM DARP DSYS DFVT
DWIM`); `u32@0x20` = chunk-antal·8. `u32@0x3c` är en per-fil-byggstämpel,
också inbäddad som u16 före varje EPFM/EWFM/EARP-namn (syntetisk header
`0x3c` = käll-`0x3c`); EPFM-post byte[11] = kompakt destinations-slot-index.
DWFM-blob-offset `60 + 64·k` är ett 4-byte LE sample-index = `base + i`
(base = första blob-sub-postens ursprungliga 4B LE-värde, i per sub-post
över alla blobbar). En giltig library-fil har en fast directory-region:
poster från `0x40`, FF-pad, `0x00`-separator @`0x190`, första chunk @`0x191`.

Hjälpfunktioner: `scanWaveformRefPositions`, `scanArpRefPositions`,
`renumberPerfBlob`, `setRecPayloadId`. Export-vägen renumrerar blobbar +
kataloger; en konservativ kopiera-allt-fallback bevaras vid opålitlig
upplösning. Per-performance W/S/Arp UI-chip villkoras av samma scanners.


## Filstruktur (Y2L container)

### Fil-header (64 bytes, binärverifierad — se Appendix A.3 i engelska YSFC_FORGE_FULL_CONTEXT.md)

| Offset | Hex | Storlek | Fält | Notering |
|---:|---:|---:|---|---|
| 0 | 0x00 | 16 | Magic + null-pad | `YAMAHA-YSFC\x00\x00\x00\x00\x00` |
| 16 | 0x10 | 16 | Version + null-pad | `5.1.2` (Montage M / MODX M); `5.0.1` (MODX); `4.0.5` (Montage) |
| 32 | 0x20 | 4 | Katalogstorlek | `u32 BE` = antal_block × 8; katalogen börjar på 0x40 |
| 36 | 0x24 | 12 | Reserverad | alla `0xFF` |
| 48 | 0x30 | 4 | Library-info-längd | `u32 BE`; 241 bytes (Montage M / MODX M), 81 bytes (classic) |
| 52 | 0x34 | 8 | Reserverad | alla `0xFF` |
| 60 | 0x3C | 4 | Spar-räknare | `u32 BE`; ökar monotont — **inte** Unix-timestamp |

### EPFM Entry-post payload (binärverifierad)

| Rel | Storlek | Fält | Notering |
|---:|---:|---|---|
| 0 | 4 | Blob-storlek | `u32 BE` — DPFM-blob-storlek |
| 4 | 4 | DPFM-offset | `u32 BE` — offset inom DPFM-payload |
| 9 | 1 | Konstant | `0x40` (MODX validerar) |
| 11 | 1 | Destinations-slot | kompakt sekventiellt index (0, 1, 2, …) |
| 15 | 1 | Engine-bitar | `0x01`=AWM2/Drum, `0x02`=FM-X, `0x04`=AN-X; OR-kombinerat |
| 16 | 1 | Käll-flagga | `0x00`=ESP Plugin, `0x02`=MODX hardware |
| 27 | var | Namnsträng | `"{idx}:{kort_namn}:{visnings_namn}\0"` NUL-terminerad ASCII |

Namnsträngsformat: `"{slot_index}:{kort_namn}:{visnings_namn}\0"`. **Tredje fältet** är det faktiska visningsnamnet som visas i MODX/ESP Plugin (matchar `blob[4:]`). Andra fältet är ett kort kategorinamn. Exempel: `"0:Italian XL:Italian Grand XL\0"`.

Obs: tidigare dokumentation beskrev detta som `"IDX:LångtNamn_paddat:KortNamn\0"` — fältordningen var omvänd och felaktig.

**v4.x-formatnotering (Montage classic `4.0.5` / MODX classic `5.0.1`):** Engine-type-byten sitter på `blob[6698]`, inte `blob[6700]`. EPFM directory-struktur skiljer sig — se avsnitt 1.2a i YSFC_FORGE_FULL_CONTEXT_sv.md. Använd alltid EPFM `rec[15]` som engine-källa före `blob[6700]` när filversion är okänd.

```
YAMAHA-YSFC header
├── EPFM  Performance index
├── DPFM  Performance data
├── ELST  Live Set index
├── DLST  Live Set data
├── ESYS  System index
├── DSYS  System data
├── EFVT  Favorite index
└── DFVT  Favorite data
```

**Container abs → payload-rel konvertering:** `payload = file_abs − 691` (för Part Common-regionen; vissa baselines avviker beroende på chunk-layout).

---

## Part Common (payload rel +0..+469, abs 6701..7170)

### Identifierare & metadata
- `+0..+21` partName (ASCII × 22)
- `+31` monoPoly (u8 bool, default 1=Poly)
- `+32` portamento_sw

### Volym/Pan/Routing
- `+142` volume (u8 direct, default 100)
- `+105` ex_elem_sw / arpRandomSfx (delar byte; UI exponerar som separata kontroller)

### Shared Part-level AEG Offset (rel +144..+150)
Delat block — AWM2, FM-X och AN-X skriver hit via UI:s "Part Settings > AEG Offset". **Drum-engine använder INTE detta block** — för Drum är rel +144/+146 filter-fält istället (se Drum-sektionen).

| Rel | Fält | Encoding | Default |
|---:|---|---|---:|
| +144 | aeg_offset_attack | c64 | 64 |
| +146 | aeg_offset_decay | c64 | 64 |
| +148 | aeg_offset_sustain | c64 | 64 |
| +150 | aeg_offset_release | c64 | 64 |

### AWM2-specifik FEG Offset (rel +152..+158)
Endast AWM2 — FM-X och AN-X har FEG-strukturer i engine-pool istället.

| Rel | Fält | Encoding | Default |
|---:|---|---|---:|
| +152 | feg_offset_attack | c64 | 64 |
| +154 | feg_offset_decay | c64 | 64 |
| +156 | feg_offset_sustain | c64 | 64 |
| +158 | feg_offset_release | c64 | 64 |

### Element Count (rel +196)
u8 enum: 8, 16, 32, 64, 128. Default 8. Speglad i Engine header byte 0 — samma värde lagras på två platser. Filstorlek växer linjärt: extra bytes = (EC − 8) × 313.

### Övriga Part Common-fält
- `+126` velocity_depth (AN-X), delar med Drum velDepth
- `+128` velocity_offset
- `+202` pitch_control_group
- `+212` pb_range_upper, `+214` pb_range_lower
- `+216` detune (u16le center)
- `+218` note_shift (c64)
- `+220` portamento_time
- `+222` portamento_mode (bool)
- `+224` portamento_time_mode (enum Rate1/Time1/Rate2/Time2)
- `+226` legato_slope (u8 0..7)

### Filter-offsets (rel +164..+168, AN-X UI-namn)
- `+164` filter_offset_fegdepth
- `+166` filter_offset_cutoff
- `+168` filter_offset_resonance

---

## Engine Header (5 bytes, abs 12464..12468)

| Abs | Fält | Default |
|---:|---|---:|
| 12464 | element_count | 8 (AWM2) |
| 12465 | unknown_b1 | 0 |
| 12466 | engine_type | 0=AWM2, 1=Drum, 2=FM-X, 3=AN-X |
| 12467 | unknown_b3 | 0 |
| 12468 | unknown_marker | 43 (AWM2) |

---

## AWM2 Engine (per-element, stride 313 bytes)

**Engine-pool start:** payload 12469
**Element N base:** 12469 + (N−1) × 313
**Stöd:** 8..128 element per Part

### Adresseringskonventioner (KRITISKT vid byte-analys)

Denna referens använder en **"audit abs"-konvention** där Element 1 base = abs 12469. Vid binär-diff-analys av Y2L-filer är konversionen:

```
filoffset = audit_abs + 687
audit_abs = filoffset − 687
```

Konstanten 687 består av: 64 (fil-header) + 8 (EPFM-header) + 353 (EPFM-data) + 8 (ESYS-header) + 46 (ESYS-data) + 8 (EFVT-header) + 163 (EFVT-data) + 8 (DPFM-header) + 16 (DPFM sub-blob header inklusive "Data..." och Performance Name-prefix) + 13 (pre-Part-area). Exakt summering kan variera per filtyp.

**Verifiering:** Filoffset där `waveform_lo = 6` (Init Normal AWM2 Element 1 = CFX v06 St) ska vara `687 + 12469 + 51 = 13207`. Detta är en tillförlitlig referenspunkt vid varje binäranalys.

**OBS:** Serializerns `AWM2_ELEM_LAYOUT` använder en *annan* konvention där `ELEM_BASE = abs 12520`. Konversion mot audit-abs:

```
audit_abs = AWM2_ELEM_LAYOUT_offset + 12520
audit_rel_inom_element = AWM2_ELEM_LAYOUT_offset + 51
```

Sammanfattning av tre olika "abs"-konventioner i projektet:
- **audit abs** (denna referens): Element 1 base = 12469
- **AWM2_ELEM_LAYOUT** (serializer): Element 1 base = 12520 (ELEM_BASE = audit_abs − 51)
- **AWM2_ELEM1_BASE** (serializer): 12532 (audit_abs + 63)

### Per-element fält — KOMPLETT

Alla rel inom 313-byte element. Element 1 base = audit abs 12469.

#### Header & metadata

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +0 | `element_header` | bool | E1=1, E2-8=0 | ★★★★★ |
| +1 | `keyondly_sync` | bool | 0 | ★★★★★ |
| +2 | `aeg_half_damper` | bool | 0 | ★★★★★ |
| +6 | `extended_lfo` | bool | 1 | ★★★★★ |
| +49 | `elem_group` | direct | 0 | ★★★★★ |
| +51 | `waveform_lo` | u8 | varierar | ★★★★★ |
| +59 | `pan` | c64 | 64 | ★★★★★ |
| +61 | `aeg_random_pan` | u8 | 0 | ★★★★★ |
| +63 | `aeg_alternate_pan` | c64 | 64 | ★★★★★ |
| +65 | `aeg_scaling_pan` | c64 | 64 | ★★★★★ |
| +67 | `xa_control` | enum | 0 | ★★★★★ |
| +69 | `note_limit_low` | MIDI | 0 | ★★★★★ |
| +71 | `note_limit_high` | MIDI | 127 | ★★★★★ |
| +73 | `vel_limit_low` | u8 | 1 | ★★★★★ |
| +75 | `vel_limit_high` | u8 | 127 | ★★★★★ |
| +77 | `vel_xfade` | u8 | 0 | ★★★★★ |
| +79 | `delay_length` | u8 | 0 | ★★★★★ |
| +81 | `elem_connect` | enum | 1 | ★★★★★ |
| +85 | `keyondly_sync_delay` | u8 | 11 | ★★★★★ |

`extended_lfo` vid rel +6 bestämmer vilken Speed-byte UI visar — rel +289 när AV, rel +307 när PÅ. Default är PÅ för Init Normal AWM2.

#### AMP-block

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +91 | `level` | direct | 127 | ★★★★★ |
| +93 | `amp_level_vel` | c64 | 64 | ★★★★★ |
| +95 | `aeg_offset` | c64 | 0 | ★★★★★ |
| +97 | `amp_level_curve` | enum | 3 | ★★★★★ |
| +99 | `aeg_attack` | u8 | 0 | ★★★★★ |
| +101 | `aeg_decay1` | c64 | 64 | ★★★★★ |
| +103 | `aeg_decay2` | c64 | 64 | ★★★★★ |
| +105 | `aeg_half_damper_time` | u8 | 127 | ★★★★★ |
| +107 | `aeg_release` | u8 | 50 | ★★★★★ |
| +109 | `aeg_initial_level` | u8 | 0 | ★★★★★ |
| +111 | `aeg_attack_level` | u8 | 127 | ★★★★★ |
| +113 | `aeg_decay1_level` | u8 | 127 | ★★★★★ |
| +115 | `aeg_decay2_level` | u8 | 127 | ★★★★★ |
| +117 | `amp_segment_decay` | u8 | 4 | ★★★★★ |
| +119 | `amp_time_vel` | c64 | 64 | ★★★★★ |

#### Pitch-block

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +149 | `coarse_tune` | c64 | 64 | ★★★★★ |
| +151 | `fine_tune` | c64 | 64 | ★★★★★ |
| +153 | `pitch_vel` | c64 | 64 | ★★★★★ |
| +155 | `pitch_random` | u8 | 0 | ★★★★★ |
| +157 | `pitch_key` | u8 | 96 | ★★★★★ |
| +159 | `pegKFCenterNote` | MIDI | 60 | ★★★★★ |
| +161 | `fine_key` | c64 | 64 | ★★★★★ |
| +163 | `peg_hold_time` | u8 | 0 | ★★★★★ |

#### PEG-block

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +169 | `peg_signature` | u8 | 64 | ★★★★★ |
| +173 | `peg_level_hold` | c128 | 128 | ★★★★★ |
| +175 | `peg_level_attack` | c128 | 128 | ★★★★★ |
| +177 | `peg_level_decay1` | c128 | 128 | ★★★★★ |
| +179 | `peg_level_decay2` | c128 | 128 | ★★★★★ |
| +181 | `peg_level_release` | c128 | 128 | ★★★★★ |
| +185 | `peg_segment` | enum | 4 | ★★★★★ |
| +187 | `peg_time_vel` | c64 | 64 | ★★★★★ |
| +189 | `peg_depth_vel` | c64 | 64 | ★★★★★ |
| +191 | `peg_curve` | enum | 2 | ★★★★★ |
| +193 | `peg_time_key` | c64 | 64 | ★★★★★ |
| +195 | `peg_center_key` | MIDI | 60 | ★★★★★ |

#### Filter-block

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +201 | `filter_type` | enum | 4 | ★★★★★ |
| +203 | `filter_cutoff_lo` | u16le | 128 | ★★★★★ |
| +205 | `filter_cutoff_vel` | c64 | 64 | ★★★★★ |
| +207 | `filter_resonance` | u8 | 0 | ★★★★★ |
| +209 | `filter_resonance_vel` | c64 | 64 | ★★★★★ |
| +211 | `hpf_cutoff_lo` | u16le | 0 | ★★★★★ |
| +213 | `filter_distance` | c128 | 128 | ★★★★★ |
| +215 | `filter_gain` | u8 | 230 | ★★★★★ |

Filter type-värden: LPF24A=1, LPF18=2, default=4, DualBEF=17.

#### FEG-block (Filter Envelope)

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +219 | `filter_time_attack` | u8 | 0 | ★★★★★ |
| +221 | `filter_time_decay1` | c64 | 64 | ★★★★★ |
| +223 | `filter_time_decay2` | c64 | 64 | ★★★★★ |
| +225 | `filter_time_release` | u8 | 80 | ★★★★★ |
| +227 | `filter_level_hold` | c128 | 128 | ★★★★★ |
| +229 | `filter_level_attack` | u8 | 255 | ★★★★★ |
| +231 | `filter_level_decay1` | u8 | 255 | ★★★★★ |
| +233 | `filter_level_decay2` | u8 | 255 | ★★★★★ |
| +235 | `filter_level_release` | c128 | 128 | ★★★★★ |
| +237 | `filter_feg_depth` | c104 | 104 | ★★★★★ |
| +239 | `filter_segment` | enum | 4 | ★★★★★ |
| +241 | `filter_time_vel` | c64 | 64 | ★★★★★ |
| +243 | `feg_depth_vel` | c64 | 64 | ★★★★★ |
| +245 | `filter_curve` | enum | 2 | ★★★★★ |

#### EQ-block

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +271 | `eq_type` | enum | 0 | ★★★★★ |
| +273 | `eq_q_or_resonance` | u8 | 0 | ★★★★★ |
| +275 | `eq_low_freq` | u8 | 54 | ★★★★★ |
| +277 | `eq_low_gain` | c64 | 64 | ★★★★★ |
| +279 | `eq_high_freq` | u8 | 231 | ★★★★★ |
| +281 | `eq_high_gain` | c64 | 64 | ★★★★★ |

EQ type-värden: 0=2-band, 1=P.EQ, 2=Boost6.

#### LFO-block

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +283 | `lfo_wave` | enum | 1 | ★★★★★ |
| +285 | `lfo_keyonreset` | bool | 1 | ★★★★★ |
| +287 | `lfo_delay` | u8 | 0 | ★★★★★ |
| +289 | `lfoSpeed` | u8 0..63 | 38 | ★★★★★ |
| +291 | `lfo_amp_mod_depth` | u8 | 0 | ★★★★★ |
| +293 | `lfo_pitch_mod_depth` | u8 | 0 | ★★★★★ |
| +295 | `lfo_filter_mod_depth` | u8 | 0 | ★★★★★ |
| +297 | `lfo_fade_in` | u8 | 0 | ★★★★★ |
| +307 | `lfo_extended_speed` | u16le 0..415 | 60 | ★★★★★ |

LFO wave: Saw=0, Tri=1, Square=2. `lfoSpeed` (+289) är aktiv när `extended_lfo`=0; `lfo_extended_speed` (+307) är aktiv när `extended_lfo`=1.

#### AMP Level Scaling (5 BP + 4 offsets)

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +121 | `amp_time_key` | c64 | 64 | ★★★★★ |
| +123 | `amp_scaling_center_key` | MIDI | 24 | ★★★★★ |
| +125 | `amp_scaling_bp1` | MIDI | 36 | ★★★★★ |
| +127 | `amp_scaling_bp2` | MIDI | 48 | ★★★★★ |
| +129 | `amp_scaling_bp3` | MIDI | 60 | ★★★★★ |
| +131 | `amp_scaling_bp4` | MIDI | 72 | ★★★★★ |
| +133 | `amp_scaling_offset1` | c128 | 128 | ★★★★★ |
| +135 | `amp_scaling_offset2` | c128 | 128 | ★★★★★ |
| +137 | `amp_scaling_offset3` | c128 | 128 | ★★★★★ |
| +139 | `amp_scaling_offset4` | c128 | 128 | ★★★★★ |
| +141 | `level_key` | c64 | 64 | ★★★★★ |
| +143 | `amp_release_adj` | c64 | 64 | ★★★★★ |

#### Filter Level Scaling (5 BP + 4 offsets)

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +247 | `filter_time_key` | c64 | 64 | ★★★★★ |
| +249 | `filter_scaling_center_key` | MIDI | 24 | ★★★★★ |
| +251 | `filter_scaling_bp1` | MIDI | 36 | ★★★★★ |
| +253 | `filter_scaling_bp2` | MIDI | 48 | ★★★★★ |
| +255 | `filter_scaling_bp3` | MIDI | 60 | ★★★★★ |
| +257 | `filter_scaling_bp4` | MIDI | 72 | ★★★★★ |
| +259 | `filter_scaling_cutoff_offset1` | c128 | 128 | ★★★★★ |
| +261 | `filter_scaling_cutoff_offset2` | c128 | 128 | ★★★★★ |
| +263 | `filter_scaling_cutoff_offset3` | c128 | 128 | ★★★★★ |
| +265 | `filter_scaling_cutoff_offset4` | c128 | 128 | ★★★★★ |
| +267 | `element_edit_counter` | u8 | 74 | ★★★★★ [INTERN] |
| +269 | `hpf_cutoff_key` | c64 | 64 | ★★★★★ |

#### LFO Element Matrix

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +299 | `element_lfo_phase_offset` | enum | 0 | ★★★★★ |
| +301 | `element_lfo_dest1_depth` | u8 | 127 | ★★★★★ |
| +303 | `element_lfo_dest2_depth` | u8 | 127 | ★★★★★ |
| +305 | `element_lfo_dest3_depth` | u8 | 127 | ★★★★★ |

### XA Control enum (rel +67)
0=Normal, 1=Legato, 2=KeyOff, 3=Cycle, 4=Random, 5=A.Sw Off, 6=A.Sw1 On, 7=A.Sw2 On

### [INTERN]-bytes inom AWM2-element

Följande positioner är firmware-konstanter (verifierat 100% konstanta över 408 AWM2-testfiler):

| Rel | Default | Beskrivning |
|---:|---:|---|
| +46 | 40 | Firmware-konstant |
| +90 | 54 | Firmware-konstant |
| +148 | 48 | Firmware-konstant |
| +200 | 108 | Firmware-konstant |
| +309..+311 | 0 | Padding |
| +312 | 43 (0x2B '+') | Inter-element separator |

**Per-element sammanställning:**
- 128 UI-mappade fält ★★★★★
- 8 [INTERN]-bytes
- ~177 multi-byte split-bytes (u16le hi-byte etc., redan räknade i UI-fält)

Element 8 visar avvikande värde på rel +312 p.g.a. att DSYS-chunken börjar direkt efter Element 8 utan padding-zon.

---

## FM-X Engine

**Engine-pool start:** payload 12466
**Pre-OP block:** rel +0..+147
**OP1 base:** payload 12676 (= engine rel +210)
**OP-stride:** 123 bytes, 8 operators

### Pre-OP block

#### PEG (Pitch EG) — rel +11..+41

| Rel | Fält | Encoding | Default |
|---:|---|---|---:|
| +11 | peg_pitch_velocity | c64 | 64 |
| +13 | peg_random_pitch | u8 | 0 |
| +15 | peg_pitch_key | c96 | 96 |
| +17 | peg_center_key | MIDI | 60 |
| +19 | peg_level_initial | c50 | 50 |
| +21 | peg_level_attack | c50 | 50 |
| +23 | peg_level_decay1 | c50 | 50 |
| +25 | peg_level_decay2 | c50 | 50 |
| +27 | peg_level_release | c50 | 50 |
| +29 | peg_time_attack | direct | 0 |
| +31 | peg_time_decay1 | direct | 0 |
| +33 | peg_time_decay2 | direct | 0 |
| +35 | peg_time_release | direct | 0 |
| +37 | peg_depth_velocity | direct | 0 |
| +39 | peg_depth | enum | 0 |
| +41 | peg_time_key | direct | 0 |

#### Common LFO + Algoritm — rel +43..+69
- `+43` lfo_wave (enum, default 5)
- `+47` second_lfo_phase (enum, default 0)
- `+49` second_lfo_delay (u8, default 0)
- `+51` key_on_reset (bool)
- `+59` algo (u8, default 69)
- `+61` feedback (u8)
- `+63` second_lfo_extended (bool, default 1)
- `+65` second_lfo_wave_speed (u8, default 50)
- `+69` op1_fm_harmonics (u8, default 128)

#### Filter — rel +81..+93

| Rel | Fält | Encoding | Default |
|---:|---|---|---:|
| +81 | filter_type | enum | 21 |
| +83 | filter_cutoff | u16le | 1023 |
| +85 | filter_cutoff_vel | c64 | 64 |
| +87 | filter_resonance | direct | 10 |
| +89 | filter_resonance_vel | direct | 64 |
| +91 | filter_hpf_cutoff | direct | 0 |
| +93 | filter_resonance_vel_v | c64 | 64 |

Filter type-värden: Thru=21, LPF12+HPF12=4.

#### FEG (Filter EG) — rel +95..+131

| Rel | Fält | Encoding | Default |
|---:|---|---|---:|
| +95 | feg_gain | u8 direct (0..255) | 255 |
| +97 | feg_hold_time | direct | 0 |
| +99 | feg_attack_time | direct | 0 |
| +101 | feg_decay_time | direct | 0 |
| +103 | feg_sustain_time | direct | 0 |
| +105 | feg_release_time | direct | 0 |
| +107 | feg_hold_level | c128 | 128 |
| +109 | feg_attack_level | c128 | 128 |
| +111 | feg_decay_level | c128 | 128 |
| +113 | feg_sustain_level | c128 | 128 |
| +115 | feg_release_level | c128 | 128 |
| +117 | feg_depth | c128 | 104 |
| +119 | feg_segment | enum 0..4 | 4=All |
| +121 | feg_time_vel | c64 | 64 |
| +123 | feg_depth_vel | c64 | 64 |
| +125 | feg_curve | enum 0..4 | 2 |
| +131 | feg_time_key_v | c64 | 64 |

#### Key Follow — rel +127..+147

| Rel | Fält | Encoding | Default |
|---:|---|---|---:|
| +127 | time_key_scaling | c64 | 64 |
| +129 | center_key | MIDI | 24=C2 |
| +133 | break_point_1 | MIDI | 36 |
| +135 | break_point_2 | MIDI | 48 |
| +137 | break_point_3 | MIDI | 60 |
| +139 | break_point_4 | MIDI | 72 |
| +141 | cutoff_offset_1 | c128 | 128 |
| +143 | cutoff_offset_2 | c128 | 128 |
| +145 | cutoff_offset_3 | c128 | 128 |
| +147 | cutoff_offset_4 | c128 | 128 |

#### OP1-specifika Pre-OP-fält
- `+206` op1_keyonreset (bool, default 1)
- `+208` op1_freq_mode (enum 0=Ratio, 1=Fixed)

### OP-block (123 bytes per operator, OP1..OP8)

Per-OP fält-layout (offsets relativa till OP_BASE):

| Rel | Fält | Encoding | Default |
|---:|---|---|---:|
| +0 | coarse | u8 | 1 |
| +2 | fine | u8 | 0 |
| +4 | detune | c16 | 15 |
| +6 | pitch_key_fixed | u8 | 0 |
| +8 | pitch_vel_fixed | u8 | 7 |
| +10 | spectral_form | enum 0..6 | 0 |
| +12 | spectral_skirt | u8 | 0 |
| +14 | spectral_resonance | u8 | 0 |
| +16 | level_initial | c50 | 50 |
| +18 | level_attack | c50 | 50 |
| +20 | time_attack | u8 | 0 |
| +22 | time_delay | u8 | 0 |
| +24 | aeg_attack_level | u8 | 99 |
| +26 | aeg_decay1_level | u8 | 99 |
| +28 | aeg_decay2_level | u8 | 99 |
| +30 | aeg_release_level | u8 | 0 |
| +32 | attack | u8 | 0 |
| +34 | decay1 | u8 | 0 |
| +36 | decay2 | u8 | 0 |
| +38 | release | u8 | 40 |
| +40 | hold | u8 | 0 |
| +42 | time_key | u8 | 0 |
| +44 | level | u8 | 0 |
| +46 | aeg_breakpoint | MIDI | 39 |
| +48 | lvl_key_lo | u8 | 0 |
| +50 | lvl_key_hi | u8 | 0 |
| +52 | curve_lo | enum | 0 |
| +54 | curve_hi | enum | 0 |
| +56 | level_vel | u8 | 7 |
| +58 | second_lfo_pitch_mod_dest | enum 0..7 | 3 |
| +60 | second_lfo_amp_mod_dest | enum 0..7 | 3 |
| +66 | trailer_a | u8 | 127 [INTERN] |
| +68 | trailer_b | u8 | 127 [INTERN] |
| +70 | trailer_c | u8 | 127 [INTERN] |

Per-OP-fälten `second_lfo_pitch_mod_dest` (+58) och `second_lfo_amp_mod_dest` (+60) är replicerade över alla 8 operatorer med stride 123. De tre trailer-bytes per OP är firmware-konstanter av samma kategori som AN-X filter-trailers.

---

## Drum Engine

**Engine-pool start:** payload 12466 (Drum Key 1 base = payload 12469, abs 13160)
**Drum Key stride:** 68 bytes per key
**Drum Key count:** 73 (C0..C6, MIDI 12..84)
**Adresseringskonvention:** Drum använder `filoffset = audit + 669` (vs +687 för AWM2/AN-X/FM-X)

### Drum har egen Part Common-layout

Drum Part Common rel +144/+146 är **filter-fält**, inte AEG-offsets. Tolkningen av Part Common rel +126..+158 styrs alltså av engine_type. För Drum gäller:

| Rel | Fält | Encoding | Default |
|---:|---|---|---:|
| +126 | drum_aeg_attack | c64 | 64 |
| +128 | drum_aeg_decay | c64 | 64 |
| +130 | drum_aeg_sustain | c64 | 64 |
| +132 | drum_aeg_release | c64 | 64 |
| +144 | drum_filter_cutoff | c64 | 64 |
| +146 | drum_filter_resonance | c64 | 64 |

### Drum Key-fält (per key, rel inom 68-byte key-block)

| Rel | Fält | Encoding | Default |
|---:|---|---|---:|
| +0 | drumKeySW | bool | 1 |
| +4 | drumKeyRcvNoteOff | bool | 0 |
| +6 | drumKeyAssignMode | enum | 1 |
| +8 | drumKeyGroup | enum | 0 |
| +10 | drumKeyWaveformNumber | u16le | 28 |
| +12 | drumKeyPan | c64 | 64 |
| +14 | drumKeyRandomPan | direct | 0 |
| +16 | drumKeyAlternatePan | c64 | 64 |
| +22 | drumKeyConnect | enum | 1 |
| +26 | drumKeyLevel | direct | 127 |
| +28 | drumKeyLevelVel | c64 | 64 |
| +30 | drumKeyTimeAttack | direct | 0 |
| +32 | drumKeyTimeDecay1 | direct | 96 |
| +34 | drumKeyTimeDecay2 | direct | 80 |
| +36 | drumKeyLevelDecay1 | direct | 127 |
| +38 | drumKeyCoarse | c64 | 64 |
| +40 | drumKeyFine | c64 | 64 |
| +42 | drumKeyPitchVel | c64 | 64 |
| +44 | drumKeyFilterCutoff | u16le | 1023 |
| +46 | drumKeyFilterCutoffVel | c64 | 64 |
| +48 | drumKeyFilterResonance | direct | 0 |
| +50 | drumKeyHpfCutoff | u16le | 0 |
| +52 | drumKeyEqType | enum | 0 |
| +56 | drumKeyEqLowFreq | direct | 54 |
| +58 | drumKeyEqLowGain | c64 | 64 |
| +60 | drumKeyEqHiFreq | direct | 231 |
| +62 | drumKeyEqHiGain | c64 | 64 |

### Drum Part Common (Part-nivå fält, absoluta adresser)

| Abs | Fält | Encoding | Default |
|---:|---|---|---:|
| 6736 | drumPartElemPanToggle | bool | 1 |
| 6802 | drumPartArpPlayOnly | bool | 0 |
| 6815 | drumPartMainCategory | enum | 16 |
| 6819 | drumPartVelLimitLow | u8 | 1 |
| 6821 | drumPartVelLimitHigh | u8 | 127 |
| 6823 | drumPartNoteLimitLow | MIDI | 0 |
| 6825 | drumPartNoteLimitHigh | MIDI | 127 |
| 6827 | drumPartVelDepth | c64 | 64 |
| 6829 | drumPartVelOffset | c64 | 64 |
| 6831 | drumPartVolume | u8 | 100 |
| 6833 | drumPartPan | c64 | 64 |
| 6835 | drumPartReverbSend | u8 | 0 |
| 6837 | drumPartVariationSend | u8 | 0 |
| 6839 | drumPartDryLevel | u8 | 127 |
| 6847 | drumPartOutput | enum | 0 |
| 6849 | drumPartFilterAegAttack | c64 | 64 |
| 6851 | drumPartFilterAegDecay | c64 | 64 |
| 6853 | drumPartFilterAegSustain | c64 | 64 |
| 6855 | drumPartFilterAegRelease | c64 | 64 |
| 6867 | drumPartFilterCutoff | c64 | 64 |
| 6869 | drumPartResonance | c64 | 64 |
| 6903 | drumPartControlGroup | enum | 0 |
| 6913 | drumPitchBendUpper | c64 | 66 |
| 6915 | drumPitchBendLower | c64 | 62 |
| 6917 | drumDetuneHz | u16le | 128 |
| 6919 | drumNoteShift | c64 | 64 |
| 6961 | drumPart2EqType | enum | 0 |

### UI-skillnader mot övriga engines

Drum har **inte** menyn Part Settings > AEG Offset som AWM2/FM-X/AN-X har. Istället exponeras AEG som **absolutvärden** under Filter/Amp-fliken. Det innebär att Drum-engine inte använder det delade AEG-offset-blocket (rel +144..+150) som övriga tre engines, utan har egen Part Common-layout på samma byte-positioner.

### [INTERN]-bytes inom Drum keys

Av de 4964 bytes i drum-key-zonen (68 × 73 keys) är 4934 (99,4%) firmware-konstanter. Specifikt:

- 33 nollpaddade byte-positioner per key (rel +1, +2, +3, +5, +7, +9, +13, +15, +17, +19, +20, +21, +23, +24, +25, +27, +29, +31, +33, +35, +37, +39, +41, +43, +47, +49, +53, +54, +55, +57, +59, +61, +63)
- rel +18 (värde 90) och rel +67 (värde 64) — konstanta icke-noll firmware-värden

---

## AN-X Engine

**Engine-pool start:** payload 12466
**Pool-storlek:** 684 bytes

### Pre-OSC block (payload 12466..12489)
- `12465` part_random_pan_anx (c64, default 0)
- `12467` alternate_pan_anx (c64, default 64)
- `12469` random_pan, `12471` scaling_pan
- `12482` part_key_on_delay_sw (bool)
- `12483` part_half_damper_sw (bool)
- `12485` osc_reset_mode (enum: Off=0, Phase=1, Tune=2, Full=3)
- `12487` voltage_drift (u8, default 64)
- `12489` ageing (u8, default 100)

### Pitch LFO (payload 12491..12511)
- `12491..12503` Pitch LFO-fält
- `12509` pitch_lfo_delay
- `12511` pitch_lfo_fadein

### Noise block (payload 12513..12518)
- `12513` noise_tone (u8, default 64)
- `12515` noise_connect (enum, default 0)
- `12518` noise_unknown_1 (u8, default 0)

### FEG (Filter EG) block (payload 12517..12529)
- `12517` feg_attack (direct, default 0)
- `12519` feg_decay (direct, default 160)
- `12521` feg_sustain (direct, default 0)
- `12523` feg_release (direct, default 160)
- `12525` feg_sustain_anx (u8, default 0)
- `12527` feg_release_anx (u8, default 160)
- `12529` feg_time_vel (preliminär)

### Filter LFO (payload 12531..12541)
- `12531` filter_lfo_wave (enum: Triangle=2, Square=1)
- `12533` filter_lfo_speed (u16le, default 208)
- `12537` filter_lfo_phase (enum 16-step)
- `12539` filter_lfo_delay
- `12541` filter_lfo_fadein

### Amp + AEG block (payload 12543..12557)
- `12543` amp_level (u16le)
- `12545` amp_level_vel
- `12547` amp_lfo_depth (c128, default 128)
- `12549` amp_aeg_attack (direct, default 0)
- `12551` amp_aeg_decay (direct, default 160)
- `12553` amp_aeg_sustain (u16le, default 511)
- `12555` amp_aeg_release (direct, default 115)
- `12557` amp_aeg_time_vel (direct, default 0)

### Amp LFO block (payload 12563..12573)
- `12563` amp_lfo_wave (enum)
- `12565` amp_lfo_speed (u16le, default 208)

### OSC1/OSC2/OSC3 fält (per OSC)

OSC1 base = audit abs 12626, OSC2 = 12751, OSC3 = 12876. Stride ~125 bytes per OSC. Utvalda fält:

| Fält | OSC1 abs | OSC2 abs | OSC3 abs |
|---|---:|---:|---:|
| waveform | 12626 | 12751 | 12876 |
| octave | 12628 | 12753 | 12878 |
| pitch_lo (u16le) | 12630 | — | 12881 |
| peg_depth_marker | 12633 | — | 12883 |
| pitch_lfo_marker | 12637 | — | — |
| sync_pitch | 12638 | 12763 | — |
| pulse_width_vel | 12648 | — | — |
| shaper | 12654 | 12779 | — |
| ring_level_vel | 12668 | — | — |
| connect | 12670 | — | — |
| pulse_width | — | 12771 | 12896 |

### Filter 1 (payload 13005..13027)
- `13005` filter1_type (enum, default 1 = LPF12)
- `13007` filter1_cutoff_lo / `13008` filter1_cutoff_hi (u16le, default 1023)
- `13009` filter1_cutoff_vel
- `13011` filter1_feg_depth_lo (u16le)
- `13013` filter1_feg_depth_vel
- `13015` filter1_lfo_depth_lo (u16le)
- `13017` filter1_cutoff_key
- `13019` filter1_resonance, `13021` filter1_resonance_vel
- `13023` filter1_drive, `13025` filter1_drive_vel
- `13027` filter1_out_level (c64, default 64)

### Filter 2 (payload 13082..13104)
- `13081` (pad/marker, default 30) — [INTERN]
- `13082` filter2_type (enum, default 5 = HPF24)
- `13084` filter2_cutoff_lo / `13085` filter2_cutoff_hi (u16le)
- `13086` filter2_cutoff_vel
- `13088` filter2_feg_depth_lo (u16le)
- `13090` filter2_feg_depth_vel
- `13092` filter2_lfo_depth_lo (u16le)
- `13094` filter2_cutoff_key
- `13096` filter2_resonance, `13098` filter2_resonance_vel
- `13100` filter2_drive, `13102` filter2_drive_vel
- `13104` filter2_out_level

### Wave Folder + Modifier LFO (payload 13116..13148)

UI: [PART] Modifier-fliken med tre under-sidor (Folder, EG, LFO). Modifier-fliken har **endast en** "LFO Depth"-knapp (abs 13122) — ingen separat byte för "Wave Folder LFO Depth".

- `13116` wavefolder_amount (u8, default 0)
- `13118` wavefolder_vel (u8, default 0)
- `13120` wavefolder_eg_depth
- `13122` modlfo_depth (u8 c128, default 128)
- `13124` wavefolder_texture
- `13126` wavefolder_type (enum, default 1 = Hard)

### Modifier EG (payload 13128..13134)
- `13128` modeg_attack, `13130` modeg_decay, `13132` modeg_sustain, `13134` modeg_release

### Modifier LFO (payload 13138..13148)
- `13138` modlfo_wave (enum, default 2 = Triangle)
- `13140` modlfo_speed_lo (u16le, default 208)
- `13146` modlfo_delay
- `13148` modlfo_fadein

### UI-kontroll-redundans i AN-X

AN-X exponerar AEG i två separata UI-kontroller med olika encoding:

| UI-plats | Adress | Encoding |
|---|---|---|
| Part Settings > AEG Offset | Part Common rel +144..+150 | c64 (offset adderas) |
| Filter/Amp > AMP > AEG | engine-pool 12549..12555 | direct (absolut värde) |

Båda existerar parallellt. Editor måste exponera båda.

---

## Control Assign

**Per-Part Control Assign:** 8 slots × 22 bytes stride, basadress varierar per Part
**Common Control Assign:** 32 slots × 22 bytes stride, abs 2452..3155 (944 bytes)

### Slot-struktur (22 bytes)

Verifierat från 35 testfiler inklusive `Test-AWM2_Part_ControlAssign_destination1-8`, `AWM2_00_Init_CA_Source_AsgnKnob1..8`, `CA_CurveType_*`, `CA_Param1_8`.

| Rel | Fält | Encoding | Default | Notering |
|---:|---|---|---:|---|
| +0 | enabled | bool | 0 | 0→1 vid edit |
| +2 | dest_category | u8 | 1 | → 8 vid aktiverad slot |
| +3 | dest_category_hi | u8 | 0 | |
| +4 | destination_lo | u8 | 1 | Faktisk destination (lo-byte) |
| +5 | destination_hi | u8 | 0 | 1 för index ≥128 |
| +8 | param2_or_curve_aux | u8 | 0 | Param2 / Steps-count / Threshold-aux |
| +10 | param1_or_curve_pri | u8 | 5 | Param1 OCH curve primary (delas) |
| +12 | curve_secondary | u8 | 0 | Sigmoid→3, Threshold→1 |
| +14 | polarity | enum | 0 | Uni=0, Bi=1 |
| +16 | endmark | u8 const | 192 | 0xC0 |
| +21 | trailer | u8 | 18 | |

### Destination encoding (kritiskt!)

Destination består av **två bytes**: `destination_lo` (+4) och `destination_hi` (+5). Tillsammans utgör de ett index i den auktoritativa 414-entries-listan `CONTROLLER_DESTINATIONS` (`ysfc_enums/controllers.py`):

```
CONTROLLER_DESTINATIONS_idx = destination_lo + destination_hi * 256
```

- För destinationer med index **0..255**: skriv värdet i `destination_lo`, `destination_hi=0`
- För destinationer med index **256..511** (Performance, MS, Arp, Per-Part Assign Knobs): skriv `destination_lo = (idx − 256)`, `destination_hi = 1`

### Destination-snabbreferens (verifierad subset)

För komplett lista, se `ysfc_enums/controllers.py` (CONTROLLER_DESTINATIONS, 414 entries).

| Lo | Hi | Idx | Destination | Status |
|---:|---:|---:|---|:---:|
| 1 | 0 | 1 | InsA Param 1 (default) | ★★★★★ |
| 2..24 | 0 | 2..24 | InsA Param 2..24 (linjärt) | ★★★★★ |
| 25 | 0 | 25 | InsB Param 1 (specifikt param# i CA+11) | ★★★★★ |
| 50 | 0 | 50 | Part Reverb Send | ★★★★★ |
| 51 | 0 | 51 | Part Variation Send | ★★★★★ |
| 59 | 0 | 59 | Part LFO Destination 3 Depth | ★★★★★ |
| 60 | 0 | 60 | Element Level | ★★★★★ |
| 61 | 0 | 61 | Element Pan | ★★★★★ |
| 62 | 0 | 62 | Element Key On Delay Time | ★★★★★ |
| 85 | 0 | 85 | Element Cutoff Frequency | ★★★★★ |
| 87 | 0 | 87 | Element HPF Cutoff Frequency | ★★★★★ |
| 100 | 1 | 356 | Part Pan | ★★★★★ |
| 105 | 1 | 361 | Arp Gate Time | ★★★★★ |
| 118 | 1 | 374 | Motion Seq Length ("MS Length") | ★★★★★ |
| 142 | 0 | 142 | (alt Filter Cutoff) | ★★★★★ |

### Part After Touch — Part rel +600..+663 (64 bytes)

Separat 4-slot register med egen 16-byte stride. Egen mindre destination-enum.

| Rel | Fält | Encoding | Default |
|---:|---|---|---:|
| +0 | enabled | bool | 0 |
| +2 | destination | enum | 1 (Pitch; 9=FilterCutoff) |
| +6 | param2 | u8 | 0 |
| +8 | param1 | u8 | 5 |
| +10 | curve_type | enum | 0 |
| +12 | polarity | enum | 0 (Uni=0, Bi=1) |
| +14 | endmark | const | 192 |

---

## Multi/GM 16-part-filer

Multi/GM-filer använder samma multi-part-arkitektur som standard multi-part-Y2L-filer:

```
Performance Common              6701 bytes
16 × Part Common               92240 bytes (stride 5765)
Engine pool                    42583 bytes (15 × AWM2_stride + 1 × Drum_stride)
DPFM total                    141536 bytes
```

I en Multi/GM Init-fil är Part 1–9 och 11–16 AWM2 (Concert GrandPiano), och Part 10 är Drum (Standard Drum Kit). De 73 drum keys för Part 10 startar på filoffset 122261.

Multi/GM stöds av befintlig multi-part-kod via `SUBBLOB_POINTER_REL = (5763, 5764)` och `get_subblob_pointer_pos()`. Inga nya fält eller strukturer behövs i serializern.

---

## Encoding-konventioner

| Notation | Beskrivning | Default |
|---|---|---:|
| direct | raw = UI-värde | varierar |
| c64 | UI = raw − 64 | 64 |
| c128 | UI = raw − 128 | 128 |
| c50 | UI = raw − 50 | 50 |
| MIDI | C-2 = 0, C-1 = 12, ..., C3 = 60, ..., G8 = 127 | varierar |
| bool | 0 = Off, 1 = On | varierar |
| enum | enum-mappad | varierar |
| u16le | little-endian 16-bit | varierar |

---

## NOISE-bytes (filtreras vid diff-analys)

Alltid:
`{22-24, 60-63, 66, 184-198, 232, 234, 358, 376, 396-399, 488, 654, 670, 6705-6725, 7167-7168, 7419}`

Plus CRC/save-bonus:
`{710-711, 7411-7412}`

EC-känsliga hash-bytes (vid Element Count-ändringar):
`{102, 103, 110, 111, 375, 673, 674, 685, 686}`

För Drum-specifik testning, filtrera även:
`{filoffset 680-720, filoffset 7380-7400}` (DPFM sub-blob header brus)
