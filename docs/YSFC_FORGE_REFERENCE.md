# YSFC Forge — Kompakt referens

Patch-editor och reverse-engineering-projekt för Yamaha MODX M / Montage M binärformatet (Y2L/Y2U/X7L/X8L).

**Hårdvara:** MODX M8 firmware 3.0, ESP Plugin v3.0
**Källa:** Binärverifierade single-edit-testfiler mot Init Voice baselines (AWM2, AN-X, FM-X)

---

## Status

| Engine | Mappade fält | UI-täckning |
|---|---:|---:|
| AWM2 (per element × 8..128) | 128 fält + 8 [INTERN] | **100%** ✅ |
| AN-X (engine totalt) | 171 fält + 458 [INTERN] | **100%** ✅ |
| FM-X (Pre-OP + 8 × OP) | 141 fält + 863 [INTERN] | **100%** ✅ |
| Drum (per key × 73) | 27 keys + 27 PartCommon | **~100%** ✅ |
| Part Common | 88 fält (AWM2/FM-X/AN-X) + 6 (Drum) | ~97% |

Total fält-positioner i serializer: ~2057
Testkorpus: 1926 binärverifierade filer

**Senaste sessioners tillägg:**
- AWM2 +159 `pegKFCenterNote` ★★★★★ UI-bekräftat (AWM2 bild 2)
- AWM2 +6 `extended_lfo` ★★★★★ binärverifierat (defaultvärde-korrigering: 0 → 1)
- AWM2 +289 `lfoSpeed` ★★★★★ binärverifierat (u8 0..63, default 38)
- AWM2 +307 `lfo_extended_speed` ★★★★★ binärverifierat (u16le 0..415, default 60)
- AWM2 +243 `feg_depth_vel` ★★★★★ binärverifierat (Test-AWM2-Filter_FEG_DepthVel_50.Y2L; ersätter felaktig `fegTimeVelSegment`)
- AWM2 +309..+312 stängda som [INTERN] (padding + separator, passivt verifierat)
- **AWM2 +46/+90/+148/+200 stängda som [INTERN] (firmware-konstanter, 100% konstant över 408 testfiler) — AWM2 nu 100% KARTLAGT ✅**
- **AN-X Filter-trailers (6 bytes) stängda som [INTERN]** (bekräftat via skanning av 537 single-edit-testfiler — INGEN ändrar trailers)
- AN-X 13082 `filter2_type` ★★★★★ UI-bekräftat (ANX bild 6)
- AN-X 13120 `wavefolder_eg_depth` ★★★★★ UI-bekräftat (ANX bild 5)
- AN-X 13124 `wavefolder_texture` ★★★★★ UI-bekräftat (ANX bild 5)
- **AN-X: 32 nya UI-fält identifierade via korpus-analys ★★★★★** (Filter EG Sustain/Release, Amp AEG Release/Time/Vel, OSC1/OSC2/OSC3 Waveform/Octave/Pitch/Shaper/Pulse/Sync, OSC EG-fält)
- **AN-X: 452 omappade konstanta bytes stängda som [INTERN]** (firmware-konstanter, 100% konstanta över 799 AN-X-testfiler)
- AN-X engine-pool nu **~98% kartlagd** (153 UI + 458 [INTERN] av 686 bytes)
- **FM-X: 44 nya UI-fält identifierade via korpus-analys ★★★★★** (PEG-block, 2nd LFO, Algoritm/Feedback, Part Filter+FEG-block, Filter Scaling Break Points/Cutoff Offsets, per-OP fält)
- **FM-X: 839 omappade konstanta bytes stängda som [INTERN]** (firmware-konstanter, 100% konstanta över 425 FM-X-testfiler)
- FM-X engine-pool nu **~99% kartlagd** (300 UI + 839 [INTERN] av 1179 bytes)
- **AN-X: 18 ytterligare UI-fält identifierade via small-edit (sessions 2)** — Noise Tone/Connect, OSC1 Pulse Width Vel/Ring Level Vel/Connect, Mod LFO Destination matrix trailing-bytes, OSC3 markers — AN-X nu **100% kartlagd** ✅
- **FM-X: Strukturellt stride-fynd (session 2)** — per-OP `2nd_lfo_pitch_mod_dest` (rel +58) och `2nd_lfo_amp_mod_dest` (rel +60) saknades, plus 3 [INTERN]-trailers per OP (rel +66/+68/+70). 16 nya UI-fält + 24 nya [INTERN]-bytes — FM-X nu **100% kartlagd** ✅
- **Drum: filoffset-konventionen klargjord** — Drum använder `filoffset = audit + 669` (vs +687 för AWM2/AN-X/FM-X). 26 av 27 DRUM_KEY-fält bekräftade. Korpusen är dock otillräcklig för full täckning — kräver ny testfilssvit.
- **Drum: 84 nya testfiler (Steg 114) gav 100% verifiering ★★★★★** — Alla 27 DRUM_KEY-fält binärverifierade. 4 nya Filter AEG-fält (audit 6849-6855), MainCategory (6815), PartControlGroup (6903), och 21 tidigare-mappade Part Common-fält binärverifierade. Inom drum-keys är alla varierande positioner = mappade UI-fält (inga omappade UI-fält). 4934 av 4964 drum-key-bytes är firmware-konstanter ([INTERN]). Drum är nu **~100% kartlagd**.
- **Multi/GM (16-part) struktur verifierad ★★★★★** — Multi/GM använder samma multi-part-arkitektur som redan dokumenterad (sektion 3): Performance Common (6701) + 16 × Part Common (stride 5765) + Engine Pool (15 AWM2 + 1 Drum för Part 10). DPFM = 141536 bytes verifierat via storleksformel. 73 drum keys @ fo 122261 (Part 10 engine-zon) bekräftat. Inga nya fält eller strukturer behövs i serializern — befintlig kod stöder Multi/GM via `SUBBLOB_POINTER_REL` och `get_subblob_pointer_pos()`.

---

## Filstruktur (Y2L container)

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

**Container abs → payload-rel konvertering:** payload = file_abs − 691 (för Part Common-region; vissa baselines avviker beroende på chunk-layout)

---

## Part Common (payload rel +0..+469, abs 6701..7170)

### Identifierare & meta
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

Auditfilerna, parameterbetygsfilen, byte-coverage-detail.txt och denna referens använder en **"audit abs"-konvention** där Element 1 base = abs 12469. Vid binär-diff-analys av Y2L-filer är konversionen:

```
filoffset = audit_abs + 687
audit_abs = filoffset - 687
```

Konstanten 687 består av: 64 (fil-header) + 8 (EPFM-header) + 353 (EPFM-data) + 8 (ESYS-header) + 46 (ESYS-data) + 8 (EFVT-header) + 163 (EFVT-data) + 8 (DPFM-header) + 16 (DPFM sub-blob header inklusive "Data..." och Performance Name-prefix) + 13 (pre-Part-area). Exakt summering kan variera per filtyp.

**Verifiering:** Filoffset där `waveform_lo = 6` (Init Normal AWM2 Element 1 = CFX v06 St) ska vara `687 + 12469 + 51 = 13207`. Detta är ett tillförlitligt referenspunkt vid varje binäranalys.

**OBS:** Serializerns `AWM2_ELEM_LAYOUT` använder en *annan* konvention där `ELEM_BASE = abs 12520`. Konversion mot audit-abs:

```
audit_abs = AWM2_ELEM_LAYOUT_offset + 12520
audit_rel_inom_element = AWM2_ELEM_LAYOUT_offset + 51
```

Sammanfattning av tre olika "abs"-konventioner i projektet:
- **audit abs** (denna referens, parameterbetygsfilen): Element 1 base = 12469
- **AWM2_ELEM_LAYOUT** (serializer rad 3115): Element 1 base = 12520 (ELEM_BASE = audit_abs − 51)
- **AWM2_ELEM1_BASE** (serializer rad 222): 12532 (audit_abs + 63)

### Per-element fält — KOMPLETT (★★★★★ binärverifierat, ★★★★☆ strukturellt härlett)

Källor: parameterbetygsfilen (★★★★★) + AWM2_ELEM_LAYOUT cross-mapping (★★★★☆) + binärverifierade single-edit-testfiler.

Alla rel inom 313-byte element. Element 1 base = audit abs 12469.


#### Header & meta

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +0 | `element_header` | bool | E1=1, E2-8=0 | ★★★★★ |
| +1 | `keyondly_sync` | bool | 0 | ★★★★★ |
| +2 | `aeg_half_damper` | bool | 0 | ★★★★★ |
| +6 | `extended_lfo` | bool | 1 | ★★★★★ (binärverifierat med Test-AWM2-ElementLFO-ExtendedLFO_ON/OFF.Y2L: 0=OFF, 1=ON. Default för Init Normal AWM2 är PÅ. Bestämmer vilken Speed-byte UI visar — rel +289 när AV, rel +307 när PÅ) |
| +49 | `elem_group` | direct | 0 | ★★★★★ |
| +51 | `waveform_lo` | u8 | varies | ★★★★★ |
| +59 | `pan` | c64 | 64 | ★★★★★ (Element1_Pan_R20) |
| +61 | `aeg_random_pan` | u8 | 0 | ★★★★★ (AEG_RandomPan_127) |
| +63 | `aeg_alternate_pan` | c64 | 64 | ★★★★★ (AEG_AlternatePan_R63) |
| +65 | `aeg_scaling_pan` | c64 | 64 | ★★★★★ (AEG_ScalingPan_63) |
| +67 | `xa_control` | enum | 0 | ★★★★★ |
| +69 | `note_limit_low` | MIDI | 0 | ★★★★★ (Note_Limit_Low_A2) |
| +71 | `note_limit_high` | MIDI | 127 | ★★★★★ (Note_Limit_High_F7) |
| +73 | `vel_limit_low` | u8 | 1 | ★★★★★ (Velocity_Limit_Low_10) |
| +75 | `vel_limit_high` | u8 | 127 | ★★★★★ (Velocity_Limit_High_112) |
| +77 | `vel_xfade` | u8 | 0 | ★★★★★ (Velocity_Cross_Fade_14) |
| +79 | `delay_length` | u8 | 0 | ★★★★★ (DelayLength_50) |
| +81 | `elem_connect` | enum | 1 | ★★★★★ |
| +85 | `keyondly_sync_delay` | u8 | 11 | ★★★★★ |

#### AMP-block

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +91 | `level` | direct | 127 | ★★★★★ (Level_100) |
| +93 | `amp_level_vel` | c64 | 64 | ★★★★★ (Amp_LevelVel_50) |
| +95 | `aeg_offset` | c64 | 0 | ★★★★★ (AEG_Offset_+50/_127) |
| +97 | `amp_level_curve` | enum | 3 | ★★★★★ |
| +99 | `aeg_attack` | u8 | 0 | ★★★★★ (AEG_Attack_10) |
| +101 | `aeg_decay1` | c64 | 64 | ★★★★★ (AEG_Decay1_10) |
| +103 | `aeg_decay2` | c64 | 64 | ★★★★★ (AEG_Decay2_10) |
| +105 | `aeg_half_damper_time` | u8 | 127 | ★★★★★ |
| +107 | `aeg_release` | u8 | 50 | ★★★★★ (AEG_Release_10) |
| +109 | `aeg_initial_level` | u8 | 0 | ★★★★★ (AEG_Initial_Level_14) |
| +111 | `aeg_attack_level` | u8 | 127 | ★★★★★ (AEG_AttackLevel_50) |
| +113 | `aeg_decay1_level` | u8 | 127 | ★★★★★ (AEG_Decay1Level_50) |
| +115 | `aeg_decay2_level` | u8 | 127 | ★★★★★ |
| +117 | `amp_segment_decay` | u8 | 4 | ★★★★★ (AMP_Segment_Decay) |
| +119 | `amp_time_vel` | c64 | 64 | ★★★★★ (AMP_TimeVel_20 / AEG_TimeVel_50) |

#### Pitch-block

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +149 | `coarse_tune` | c64 | 64 | ★★★★★ (CoarseTune_+20) |
| +151 | `fine_tune` | c64 | 64 | ★★★★★ (FineTune_+20) |
| +153 | `pitch_vel` | c64 | 64 | ★★★★★ (PitchVel_+20) |
| +155 | `pitch_random` | u8 | 0 | ★★★★★ (Random_50) |
| +157 | `pitch_key` | u8 | 96 | ★★★★★ (PitchKey_+50) |
| +159 | `pegKFCenterNote` | MIDI | 60 | ★★★★★ (UI-bekräftat AWM2 bild 2: PEG Center Key = C 3) |
| +161 | `fine_key` | c64 | 64 | ★★★★★ (FineKey_+20) |
| +163 | `peg_hold_time` | u8 | 0 | ★★★★★ (PEG_HoldTime_50) |

#### PEG-block (komplett från single-edit-tester)

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +169 | `peg_signature` | u8 | 64 | ★★★★★ (PEG-edit marker, ändras 64→76) |
| +173 | `peg_level_hold` | c128 | 128 | ★★★★★ (PEG-LevelHold_50) |
| +175 | `peg_level_attack` | c128 | 128 | ★★★★★ (PEG-LevelAttack_50) |
| +177 | `peg_level_decay1` | c128 | 128 | ★★★★★ (PEG-LevelDecay1_50) |
| +179 | `peg_level_decay2` | c128 | 128 | ★★★★★ (PEG-LevelDecay2_50) |
| +181 | `peg_level_release` | c128 | 128 | ★★★★★ (PEG-LevelRelease_50) |
| +185 | `peg_segment` | enum | 4 | ★★★★★ |
| +187 | `peg_time_vel` | c64 | 64 | ★★★★★ (PEG-TimeVel_50) |
| +189 | `peg_depth_vel` | c64 | 64 | ★★★★★ (PEG-DepthVel_50) |
| +191 | `peg_curve` | enum | 2 | ★★★★★ |
| +193 | `peg_time_key` | c64 | 64 | ★★★★★ (PEG-TimeKey_20) |
| +195 | `peg_center_key` | MIDI | 60 | ★★★★★ (TEST-PEG-CenterKey_C2) |

#### Filter-block

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +201 | `filter_type` | enum | 4 | ★★★★★ (LPF24A=1, LPF18=2, default=4, DualBEF=17) |
| +203 | `filter_cutoff_lo` | u16le | 128 | ★★★★★ (Cutoff_1023 max; u16le lo+hi @ +203/+204) |
| +205 | `filter_cutoff_vel` | c64 | 64 | ★★★★★ (Filter_CutoffVel_20) |
| +207 | `filter_resonance` | u8 | 0 | ★★★★★ (Filter_Resonance_80) |
| +209 | `filter_resonance_vel` | c64 | 64 | ★★★★★ (FilterResonanceVel_+50) |
| +211 | `hpf_cutoff_lo` | u16le | 0 | ★★★★★ (HPFCutoff_400 → 144/1) |
| +213 | `filter_distance` | c128 | 128 | ★★★★★ (DualBEF_Distance_50) |
| +215 | `filter_gain` | u8 | 230 | ★★★★★ (Filter_Gain_0/130/255) |

#### FEG-block (Filter Envelope)

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +219 | `filter_time_attack` | u8 | 0 | ★★★★★ (Filter_Time_Attack_30) |
| +221 | `filter_time_decay1` | c64 | 64 | ★★★★★ (Filter_Time_Decay1_30) |
| +223 | `filter_time_decay2` | c64 | 64 | ★★★★★ (Filter_Time_Decay2_30) |
| +225 | `filter_time_release` | u8 | 80 | ★★★★★ (Filter_Time_Release_40) |
| +227 | `filter_level_hold` | c128 | 128 | ★★★★★ (Filter_Level_Hold_22) |
| +229 | `filter_level_attack` | u8 | 255 | ★★★★★ (Filter_Level_Attack_70) |
| +231 | `filter_level_decay1` | u8 | 255 | ★★★★★ (Filter_Level_Decay1_70) |
| +233 | `filter_level_decay2` | u8 | 255 | ★★★★★ (Filter_Level_Decay2_70) |
| +235 | `filter_level_release` | c128 | 128 | ★★★★★ (Filter_Level_Release_70) |
| +237 | `filter_feg_depth` | c104 | 104 | ★★★★★ (Filter_FEGDepth_20) |
| +239 | `filter_segment` | enum | 4 | ★★★★★ |
| +241 | `filter_time_vel` | c64 | 64 | ★★★★★ (Filter_TimeVel_20) |
| +243 | `feg_depth_vel` | c64 | 64 | ★★★★★ (binärverifierat med Test-AWM2-Filter_FEG_DepthVel_50.Y2L: baseline 64 → test 114 = +50 i c64-UI. UI: [ELEMENT] Filter > Depth/Vel. PEG-parallell: rel +189 `peg_depth_vel`. AWM2_ELEM_LAYOUT:s namn `fegTimeVelSegment` är fel — bör omdöpas till `feg_depth_vel`) |
| +245 | `filter_curve` | enum | 2 | ★★★★★ |

#### EQ-block

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +271 | `eq_type` | enum | 0 | ★★★★★ (P.EQ=1, Boost6=2) |
| +273 | `eq_q_or_resonance` | u8 | 0 | ★★★★★ (P.EQ Q=1.9 → 4) |
| +275 | `eq_low_freq` | u8 | 54 | ★★★★★ (EQ_Low_Frequency_84.0Hz) |
| +277 | `eq_low_gain` | c64 | 64 | ★★★★★ (EQ_Low_Gain_+6.00db) |
| +279 | `eq_high_freq` | u8 | 231 | ★★★★★ (EQ_High_Frequency_8.50kHz) |
| +281 | `eq_high_gain` | c64 | 64 | ★★★★★ (EQ_High_Gain_+10.13db) |

#### LFO-block

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +283 | `lfo_wave` | enum | 1 | ★★★★★ (Saw=0, Tri=1, Square=2) |
| +285 | `lfo_keyonreset` | bool | 1 | ★★★★★ (KeyOnReset_Off) |
| +287 | `lfo_delay` | u8 | 0 | ★★★★★ (LFO_Delay_50) |
| +289 | `lfoSpeed` | u8 0..63 | 38 | ★★★★★ (binärverifierat med Test-AWM2-ElementLFO-ExtendedLFO_OFF.Y2L: default 38. Aktiv när `extended_lfo`=0; UI visar denna byten. Range 0..63) |
| +291 | `lfo_amp_mod_depth` | u8 | 0 | ★★★★★ (LFO_AmpMod_50) |
| +293 | `lfo_pitch_mod_depth` | u8 | 0 | ★★★★★ (LFO_PitchMod_50) |
| +295 | `lfo_filter_mod_depth` | u8 | 0 | ★★★★★ (LFO_FilterMod_50) |
| +297 | `lfo_fade_in` | u8 | 0 | ★★★★★ (LFO_FadeIn_50) |
| +307 | `lfo_extended_speed` | u16le 0..415 | 60 | ★★★★★ (binärverifierat: u16le lo=60, hi=0 → totalt 60. Aktiv när `extended_lfo`=1; UI visar denna byten. Range 0..415 — större än u8) |

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
| +141 | `level_key` | c64 | 64 | ★★★★★ (LevelKey_+50) |
| +143 | `amp_release_adj` | c64 | 64 | ★★★★★ |

#### Filter Level Scaling (5 BP + 4 offsets)

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +247 | `filter_time_key` | c64 | 64 | ★★★★★ (FilterTimeKey_+50) |
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
| +269 | `hpf_cutoff_key` | c64 | 64 | ★★★★★ (HPFCutoffKey_50%) |

#### LFO Element Matrix

| Rel | Fält | Encoding | Default | Status |
|---:|---|---|---:|:---:|
| +299 | `element_lfo_phase_offset` | enum | 0 | ★★★★★ (Matrix-test, 0..5) |
| +301 | `element_lfo_dest1_depth` | u8 | 127 | ★★★★★ (Matrix-test, Level dest) |
| +303 | `element_lfo_dest2_depth` | u8 | 127 | ★★★★★ (Matrix-test, Cutoff dest) |
| +305 | `element_lfo_dest3_depth` | u8 | 127 | ★★★★★ (Matrix-test, Pitch dest) |

### XA Control enum (rel +67)
0=Normal, 1=Legato, 2=KeyOff, 3=Cycle, 4=Random, 5=A.Sw Off, 6=A.Sw1 On, 7=A.Sw2 On

### Kvarstående okartlagda AWM2 element-bytes — INGA UI-FÄLT KVAR ✅

Efter omfattande skanning av 408 AWM2-testfiler i korpusen är AWM2 element-strukturen **100% kartlagd**.

**Stängda som [INTERN] (icke-UI-fält, firmware-konstanter):**

| Rel | Default | Status | Bevis |
|---:|---:|---|---|
| +46 | 40 | [INTERN] firmware-konstant | 100% konstant över 408 testfiler |
| +90 | 54 | [INTERN] firmware-konstant | 100% konstant över 408 testfiler |
| +148 | 48 | [INTERN] firmware-konstant | 100% konstant över 408 testfiler |
| +200 | 108 | [INTERN] firmware-konstant | 100% konstant över 408 testfiler |
| +309..+311 | 0 | [INTERN] padding | passivt verifierat |
| +312 | 43 (0x2B '+') | [INTERN] inter-element separator | passivt verifierat |

**Per-element status:**
- 128 UI-mappade fält ★★★★★
- 8 [INTERN]-bytes
- ~177 multi-byte split-bytes (u16le hi-byte etc, redan räknade i UI-fält)

**Element 8 visar avvikande värde på rel +312** p.g.a. DSYS-chunken börjar direkt efter Element 8 utan padding-zon.

Tidigare även rel +159 och +289 — nu UI-bekräftade via ESP Plugin v3.0 skärmdumpar (★★★★★). Rel +243 nu binärverifierad som `feg_depth_vel` (★★★★★) via Test-AWM2-Filter_FEG_DepthVel_50.Y2L och PEG/FEG-symmetri.

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

#### Common LFO + Algo — rel +43..+65
- `+43` lfo_wave (enum, default 5)
- `+51` key_on_reset (bool)
- `+59` algo (u8, default 69)
- `+61` feedback (u8)
- `+63` second_lfo_extended (bool, default 1)
- `+65` second_lfo_wave_speed (u8, default 50)

#### Filter — rel +81..+91
| Rel | Fält | Encoding | Default |
|---:|---|---|---:|
| +81 | filter_type | enum (Thru=21, LPF12+HPF12=4) | 21 |
| +83 | filter_cutoff | u16le | 1023 |
| +85 | filter_cutoff_vel | c64 | 64 |
| +87 | filter_resonance | direct | 10 |
| +89 | filter_resonance_vel | direct | 64 |
| +91 | filter_hpf_cutoff | direct | 0 |

#### FEG (Filter EG) — rel +95..+125
16 fält, identisk struktur med AWM2 PEG-block.

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

### OP-block (123 bytes per operator, OP1..OP8)

Pre-OP-fält (negativa offsets relativt OP_BASE):
- `-4` key_on_reset (bool, default 1)
- `-2` freq_mode (enum 0=Ratio, 1=Fixed)

Operator-fält (positiva offsets):
- `+0` coarse, `+2` fine, `+4` detune (c16, default 15)
- `+6` pitch_key, `+8` pitch_vel (c7, default 0)
- `+10` spectral_form (enum 0..6)
- `+12` spectral_skirt, `+14` spectral_resonance
- `+16` peg_initial_level (c50, default 50)
- `+18` peg_attack_level (c50, default 50)
- `+20` peg_attack_time
- `+22` peg_decay_time
- `+24..+30` aeg_levels (Atk/Dec1/Dec2/Rel)
- `+32..+38` aeg_times (Atk/Dec1/Dec2/Rel)
- `+40` hold, `+42` time_key, `+44` level
- `+46` aeg_breakpoint (MIDI, default 39)
- `+48..+54` level_key + curve (lo/hi)
- `+56` level_vel (c7, default 0)

---

## Drum Engine

**Engine-pool start:** payload 12466 (Drum Key 1 base = payload 12469, abs 13160)
**Drum Key stride:** 68 bytes per key
**Drum Key count:** 73 (C0..C6, MIDI 12..84)

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

### Drum Key 1 (engine-pool, abs 13144..13180)

| Abs | Payload | Fält | Encoding | Default |
|---:|---:|---|---|---:|
| 13144 | 12453 | drum_key_assign_mode | bool | 1=Multi |
| 13160 | 12469 | drum_key_connect | enum (0=Thru, 1=InsA) | 1 |
| 13176 | 12485 | drum_key_coarse | c64 | 64 |
| 13178 | 12487 | drum_key_fine | c64 | 64 |
| 13180 | 12489 | drum_key_pitch_vel | c64 | 64 |

Övriga Drum Key-fält (Pan, Pitch Bend, Note Limit, Velocity Limit, Group, Waveform Number osv.) finns dokumenterade i `DRUM_KEY` och `DRUM_PART_COMMON` i serializern.

### UI-skillnader mot övriga engines

Drum har **inte** menyn Part Settings > AEG Offset som AWM2/FM-X/AN-X har. Istället exponeras AEG som **absolutvärden** under Filter/Amp-fliken. Det innebär att Drum-engine inte använder det delade AEG-offset-blocket (rel +144..+150) som övriga tre engines, utan har egen Part Common-layout på samma byte-positioner.

---

## AN-X Engine

**Engine-pool start:** payload 12466
**Pool size:** 684 bytes

### Pre-OSC block (payload 12466..12489)
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

### FEG (Filter EG) block (payload 12517..12529)
- `12517` feg_attack (direct, default 0)
- `12519` feg_decay (direct, default 160)
- `12521` feg_sustain (direct, default 0)
- `12523` feg_release (direct, default 160)
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

### Filter 1 (payload 13005..13027) ★★★★★
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

### Filter 2 (payload 13082..13104) ★★★★★
- `13081` (pad/marker, default 30) — [INTERN]
- `13082` filter2_type (enum, default 5 = HPF24) — ★★★★★ (UI-bekräftat ANX bild 6: Filter 2 Type = HPF24)
- `13084` filter2_cutoff_lo / `13085` filter2_cutoff_hi (u16le)
- `13086` filter2_cutoff_vel
- `13088` filter2_feg_depth_lo (u16le)
- `13090` filter2_feg_depth_vel
- `13092` filter2_lfo_depth_lo (u16le) — UI: Filter EG/LFO > Filter LFO Depth (Filter 2)
- `13094` filter2_cutoff_key
- `13096` filter2_resonance, `13098` filter2_resonance_vel
- `13100` filter2_drive, `13102` filter2_drive_vel
- `13104` filter2_out_level

### Wave Folder + Modifier LFO (payload 13116..13148) ★★★★★

UI: [PART] Modifier-fliken med tre under-sidor (Folder, EG, LFO). Modifier-fliken har **endast en** "LFO Depth"-knapp (abs 13122) — ingen separat byte för "Wave Folder LFO Depth".

- `13116` wavefolder_amount (u8, default 0) — UI: Modifier > Folder > Wave Folder
- `13118` wavefolder_vel (u8, default 0) — UI: Modifier > Folder > Folder/Vel
- `13120` wavefolder_eg_depth — ★★★★★ (UI-bekräftat ANX bild 5: Modifier > EG Depth)
- `13122` modlfo_depth (u8 c128, default 128) — ★★★★★ (UI: Modifier > LFO > LFO Depth; binärverifierat med Test-ANX-Mod_LFO_Depth_50.Y2L → 50 ger byte 178 i c128. ANX_MODIFIERs alternativnamn `anxWaveFolderLFODepth` refererar till samma byte)
- `13124` wavefolder_texture — ★★★★★ (UI-bekräftat ANX bild 5: Modifier > Folder > Texture)
- `13126` wavefolder_type (enum, default 1 = Hard) — UI: Modifier > Folder > Type (Soft/Hard)

### Modifier EG (payload 13128..13134) — UI: Modifier > EG
- `13128` modeg_attack, `13130` modeg_decay, `13132` modeg_sustain, `13134` modeg_release

### Modifier LFO (payload 13138..13148) — UI: Modifier > LFO
- `13138` modlfo_wave (enum, default 2 = Triangle) — UI: Wave
- `13140` modlfo_speed_lo (u16le, default 208) — UI: Speed
- `13146` modlfo_delay — UI: Delay
- `13148` modlfo_fadein — UI: Fade In

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

### Slot-struktur (22 bytes) ★★★★★ från 35 verifierade testfiler

Verifierat från `Test-AMW2_Part_ControlAssign_destination1-8`,
`AWM2_00_Init_CA_Source_AsgnKnob1..8`, `CA_CurveType_*`, `CA_Param1_8`, m.fl.

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

Destination består av **två bytes**: `destination_lo` (+4) och `destination_hi` (+5).
Tillsammans utgör de ett index i den auktoritativa 414-entries-listan
`CONTROLLER_DESTINATIONS` (`ysfc_enums/controllers.py`):

```
CONTROLLER_DESTINATIONS_idx = destination_lo + destination_hi * 256
```

- För destinationer med index **0..255**: skriv värdet i `destination_lo`, `destination_hi=0`
- För destinationer med index **256..511** (Performance, MS, Arp, Per-Part Assign Knobs):
  skriv `destination_lo = (idx - 256)`, `destination_hi = 1`

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
