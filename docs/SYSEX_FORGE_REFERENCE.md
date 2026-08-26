# SysEx Forge — Technical Reference / Master Byte Map

**Scope:** Yamaha Soundmondo/WebMIDI SysEx → normalized bridge → MODX M / MONTAGE M Y2L  
**Primary verification target:** MODX M / MODX M ESP  


> This document is the compact **parameter-by-parameter recovery map**. It records both source Soundmondo/WebMIDI coordinates and target Y2L coordinates wherever the project has explicit evidence. A dash (`—`) means the current recovery sources do not support a precise coordinate; it must not be guessed.

## Coordinate systems

- **Soundmondo source**: Yamaha bulk block address plus byte offset inside that block, e.g. `3p 00 00 00 +0x0C`.
- **Y2L blob**: offset inside the DPFM Performance blob.
- **Part rel**: offset relative to Part Common start (`Part 1` starts at blob `6708` in the mapped modern layout).
- **Engine rel**: offset relative to the relevant engine body.
- **Element/Operator/Key rel**: offset relative to a repeated engine record; base + stride formulas are shown.
- **File abs**: evidence-only coordinate for one exact test container. Never hard-code it in production.

## Evidence rule

`ESP_VERIFIED` > controlled binary verification > Yamaha-documented source > current mapped implementation > inferred.  
**Fail closed:** absence of a coordinate is not permission to invent one.


## 1. Cross-generation normalized Performance/Part map

| Scope | Field | Legacy Soundmondo | M-generation Soundmondo | Status |
| --- | --- | --- | --- | --- |
| Performance | arp_master_on | `30 47 00 +0x03` / 1B / `bool` | `06 00 01 00 +0x09` / 1B / `bool` | Parser normalized map |
| Performance | main_category | — | `06 00 02 00 +0x00` / 2B / `u14` | Parser normalized map |
| Performance | motion_seq_master_on | `30 48 00 +0x00` / 1B / `bool` | `06 00 01 00 +0x0A` / 1B / `bool` | Parser normalized map |
| Performance | name | `30 40 00 +0x00` / 20B / `ascii` | `06 00 00 00 +0x00` / 20B / `ascii` | Parser normalized map |
| Performance | pan | `30 40 00 +0x1F` / 1B / `pan_l63_r63` | `06 00 02 00 +0x08` / 2B / `pan_u14_l63_r63` | Parser normalized map |
| Performance | sub_category | — | `06 00 02 00 +0x02` / 2B / `u14` | Parser normalized map |
| Performance | tempo | `30 40 00 +0x2C` / 2B / `u14` | `06 00 02 00 +0x1E` / 2B / `u14` | Parser normalized map |
| Performance | volume | `30 40 00 +0x38` / 1B / `u7` | `06 00 02 00 +0x06` / 2B / `u14` | Parser normalized map |
| Part | enabled | `31 0p 00 +0x16` / 1B / `bool` | `1p 00 01 00 +0x00` / 1B / `bool` | Parser normalized map |
| Part | keyboard_control | `31 0p 00 +0x17` / 1B / `bool` | `1p 00 01 00 +0x02` / 1B / `bool` | Parser normalized map |
| Part | main_category | `31 0p 00 +0x14` / 1B / `u7` | `1p 00 02 00 +0x00` / 2B / `u14` | Parser normalized map |
| Part | mode | — | `1p 00 01 00 +0x01` / 1B / `part_mode` | Parser normalized map |
| Part | mute | `31 0p 00 +0x18` / 1B / `bool` | `1p 00 01 00 +0x03` / 1B / `bool` | Parser normalized map |
| Part | name | `31 0p 00 +0x00` / 20B / `ascii` | `1p 00 00 00 +0x00` / 20B / `ascii` | Parser normalized map |
| Part | note_high | `31 0p 00 +0x1F` / 1B / `note` | `1p 00 02 00 +0x0A` / 2B / `note_u14` | Parser normalized map |
| Part | note_low | `31 0p 00 +0x1E` / 1B / `note` | `1p 00 02 00 +0x08` / 2B / `note_u14` | Parser normalized map |
| Part | pan | `31 0p 00 +0x25` / 1B / `pan_l63_r63` | `1p 00 02 00 +0x12` / 2B / `pan_u14_l63_r63` | Parser normalized map |
| Part | sub_category | `31 0p 00 +0x15` / 1B / `u7` | `1p 00 02 00 +0x02` / 2B / `u14` | Parser normalized map |
| Part | velocity_high | `31 0p 00 +0x1D` / 1B / `u7` | `1p 00 02 00 +0x06` / 2B / `u14` | Parser normalized map |
| Part | velocity_low | `31 0p 00 +0x1C` / 1B / `u7` | `1p 00 02 00 +0x04` / 2B / `u14` | Parser normalized map |
| Part | volume | `31 0p 00 +0x24` / 1B / `u7` | `1p 00 02 00 +0x10` / 2B / `u14` | Parser normalized map |

---

## 2. Additional explicit Soundmondo/WebMIDI source offsets

These are source coordinates explicitly decoded by the current parser/recovery material. They are not fabricated from target offsets.

| Area | Parameter | Source coordinate | Generation | Encoding |
| --- | --- | --- | --- | --- |
| AWM2 Element | Enable | `41 ep 00 +0x00` | legacy | 1B bool |
| AWM2 Element | Wave bank | `41 ep 00 +0x01` | legacy | 1B u7 |
| AWM2 Element | Element group | `41 ep 00 +0x02` | legacy | 1B u7 |
| AWM2 Element | Wave number | `41 ep 00 +0x03` | legacy | 2B u14 |
| AWM2 Element | Pan | `41 ep 00 +0x08` | legacy | 1B pan |
| AWM2 Element | Random Pan | `41 ep 00 +0x09` | legacy | 1B u7 |
| AWM2 Element | Alternate Pan | `41 ep 00 +0x0A` | legacy | 1B center64 |
| AWM2 Element | Scaling Pan | `41 ep 00 +0x0B` | legacy | 1B center64 |
| AWM2 Element | XA Control | `41 ep 00 +0x0C` | legacy | 1B enum |
| AWM2 Element | Note Low | `41 ep 00 +0x0D` | legacy | 1B note |
| AWM2 Element | Note High | `41 ep 00 +0x0E` | legacy | 1B note |
| AWM2 Element | Velocity Low | `41 ep 00 +0x0F` | legacy | 1B u7 |
| AWM2 Element | Velocity High | `41 ep 00 +0x10` | legacy | 1B u7 |
| AWM2 Element | Velocity XFade | `41 ep 00 +0x11` | legacy | 1B u7 |
| AWM2 Element | Connection | `41 ep 00 +0x17` | legacy | 1B enum |
| AWM2 Element | Level | `41 ep 00 +0x28` | legacy | 1B u7 |
| AWM2 Element | Coarse Tune | `41 ep 00 +0x49` | legacy | 1B center64 |
| AWM2 Element | Fine Tune | `41 ep 00 +0x4A` | legacy | 1B center64 |
| AWM2 Filter | Filter Type | `42 ep 00 +0x00` | legacy | 1B enum |
| AWM2 Filter | Cutoff | `42 ep 00 +0x01` | legacy | 2B u14 |
| AWM2 Filter | Resonance | `42 ep 00 +0x05` | legacy | 1B u7 |
| AWM2 Filter | HPF Cutoff | `42 ep 00 +0x07` | legacy | 2B u14 |
| AWM2 Filter | FEG Depth | `42 ep 00 +0x1D` | legacy | 1B center64 |
| AWM2 LFO | Wave | `42 ep 00 +0x3A` | legacy | 1B enum |
| AWM2 LFO | Speed | `42 ep 00 +0x3D` | legacy | 1B u7 |
| AWM2 LFO | Amplitude Depth | `42 ep 00 +0x3E` | legacy | 1B u7 |
| AWM2 LFO | Pitch Depth | `42 ep 00 +0x3F` | legacy | 1B u7 |
| AWM2 LFO | Filter Depth | `42 ep 00 +0x40` | legacy | 1B u7 |
| AWM2 Element | Level | `2p 02 ee 00 +0x00` | M-gen | 2B u14 |
| AWM2 Element | Coarse Tune | `2p 03 ee 00 +0x00` | M-gen | 2B center64 |
| AWM2 Element | Fine Tune | `2p 03 ee 00 +0x02` | M-gen | 2B center64 |
| AN-X Oscillator | Wave | `4p 02 0o 00 +0x00` | M-gen | 2B u14 enum |
| AN-X Oscillator | Octave | `4p 02 0o 00 +0x02` | M-gen | 2B u14 enum |
| AN-X Oscillator | Pitch raw | `4p 02 0o 00 +0x04` | M-gen | 2B u14 |
| AN-X Oscillator | Out Level | `4p 02 0o 00 +0x30` | M-gen | 2B u14 |
| Insertion A | Sidechain source | `31 2p 00 +0x43` | legacy | 1B raw source code |
| Insertion B | Sidechain source | `31 3p 00 +0x43` | legacy | 1B raw source code |
| Insertion A | Sidechain source | `1p 00 03 00 +0x3A` | M-gen | 2B u14 |
| Insertion B | Sidechain source | `1p 00 03 00 +0x3C` | M-gen | 2B u14 |
| Insertion Routing | Connection | `31 0p 00 +0x3B` | legacy | 1B enum |
| Insertion Routing | Connection | `1p 00 03 00 +0x14` | M-gen | 2B u14 enum |
| Arpeggio | Slot 1 number | `31 6p 00 +0x45` | legacy | 2B u14 |
| Arpeggio | Slot 1 number | `1p 00 06 00 +0x44` | M-gen | 2B u14 |
| Arpeggio | Slot 1 extra bank | `1p 00 06 00 +0x54` | M-gen | 2B u14 |
| Arpeggio | Slot 2 number | `31 6p 00 +0x48` | legacy | 2B u14 |
| Arpeggio | Slot 2 number | `1p 00 06 00 +0x46` | M-gen | 2B u14 |
| Arpeggio | Slot 2 extra bank | `1p 00 06 00 +0x56` | M-gen | 2B u14 |
| Arpeggio | Slot 3 number | `31 6p 00 +0x4B` | legacy | 2B u14 |
| Arpeggio | Slot 3 number | `1p 00 06 00 +0x48` | M-gen | 2B u14 |
| Arpeggio | Slot 3 extra bank | `1p 00 06 00 +0x58` | M-gen | 2B u14 |
| Arpeggio | Slot 4 number | `31 6p 00 +0x4E` | legacy | 2B u14 |
| Arpeggio | Slot 4 number | `1p 00 06 00 +0x4A` | M-gen | 2B u14 |
| Arpeggio | Slot 4 extra bank | `1p 00 06 00 +0x5A` | M-gen | 2B u14 |
| Arpeggio | Slot 5 number | `31 6p 00 +0x51` | legacy | 2B u14 |
| Arpeggio | Slot 5 number | `1p 00 06 00 +0x4C` | M-gen | 2B u14 |
| Arpeggio | Slot 5 extra bank | `1p 00 06 00 +0x5C` | M-gen | 2B u14 |
| Arpeggio | Slot 6 number | `31 6p 00 +0x54` | legacy | 2B u14 |
| Arpeggio | Slot 6 number | `1p 00 06 00 +0x4E` | M-gen | 2B u14 |
| Arpeggio | Slot 6 extra bank | `1p 00 06 00 +0x5E` | M-gen | 2B u14 |
| Arpeggio | Slot 7 number | `31 6p 00 +0x57` | legacy | 2B u14 |
| Arpeggio | Slot 7 number | `1p 00 06 00 +0x50` | M-gen | 2B u14 |
| Arpeggio | Slot 7 extra bank | `1p 00 06 00 +0x60` | M-gen | 2B u14 |
| Arpeggio | Slot 8 number | `31 6p 00 +0x5A` | legacy | 2B u14 |
| Arpeggio | Slot 8 number | `1p 00 06 00 +0x52` | M-gen | 2B u14 |
| Arpeggio | Slot 8 extra bank | `1p 00 06 00 +0x62` | M-gen | 2B u14 |

---

## 3. Control Assign target record

Array base in the clean single-Performance evidence blob: **8220 (`0x201C`)**, stride **22**, **32 active records demonstrated**. File absolute `0x22CB` applies only to that exact evidence file.

| Field | Record rel | Y2L target | Encoding/value | Status |
| --- | --- | --- | --- | --- |
| Enable | +1 | `8220 + n*22 +1` | boolean | verified clean tests |
| Source | +3 | `8220 + n*22 +3` | MW=1; Aftertouch=2; FootCtrl1=3 | ESP_VERIFIED |
| Destination | +5 | `8220 + n*22 +5` | Rev Send=50; Pitch=54; Volume=55 | ESP_VERIFIED |
| Unknown/reserved | +7 | `8220 + n*22 +7` | no UI meaning assigned | UNKNOWN/RESERVED |
| CURVE TYPE | +9 | `8220 + n*22 +9` | Standard=0; Bell=3; FM=5; Square=11; Harmonics=18 | ESP_VERIFIED |
| Param1 | +11 | `8220 + n*22 +11` | raw | mapped field |
| Param2 | +13 | `8220 + n*22 +13` | raw | mapped field |
| Polarity | +15 | `8220 + n*22 +15` | UNI=0; BI=1 | ESP_VERIFIED |
| Depth | +17 | `8220 + n*22 +17` | raw = UI + 128; +55→183; -55→73 | ESP_VERIFIED |

---

## 4. Insertion sidechain target

| Parameter | Part-relative | Blob evidence | File evidence | Verified values | Status |
| --- | --- | --- | --- | --- | --- |
| Insertion A Side Chain Source | Part rel `+263` | test blob rel `6971` | file abs `0x1DEA` | 127=Off; 0=Part1; 1=Part2 | ESP_VERIFIED |
| Insertion B Side Chain Source | Part rel `+265` | test blob rel `6973` | file abs `0x1DEC` | 127=Off; 0=Part1; 1=Part2 | ESP_VERIFIED |

Other raw sidechain codes must be preserved until classified; do not assume every code is a Part number.

---

## 5. AWM2 modern Y2L Element map

Target formula: `ElementN base = 12469 + (N-1)*313` for the mapped Part-1 modern blob coordinate system.

| Parameter | Target formula | E1 coordinate | Status |
| --- | --- | --- | --- |
| enable | `E(n) = 12469 + (n-1)*313 + 0` | E1 `12469` / rel `+0` | Editor v5.6 / mapped target |
| keyondly_sync | `E(n) = 12469 + (n-1)*313 + 1` | E1 `12470` / rel `+1` | Editor v5.6 / mapped target |
| aeg_half_damper | `E(n) = 12469 + (n-1)*313 + 2` | E1 `12471` / rel `+2` | Editor v5.6 / mapped target |
| extended_lfo | `E(n) = 12469 + (n-1)*313 + 6` | E1 `12475` / rel `+6` | Editor v5.6 / mapped target |
| elem_group | `E(n) = 12469 + (n-1)*313 + 49` | E1 `12518` / rel `+49` | Editor v5.6 / mapped target |
| waveform_lo | `E(n) = 12469 + (n-1)*313 + 51` | E1 `12520` / rel `+51` | Editor v5.6 / mapped target |
| pan | `E(n) = 12469 + (n-1)*313 + 59` | E1 `12528` / rel `+59` | Editor v5.6 / mapped target |
| aeg_random_pan | `E(n) = 12469 + (n-1)*313 + 61` | E1 `12530` / rel `+61` | Editor v5.6 / mapped target |
| aeg_alternate_pan | `E(n) = 12469 + (n-1)*313 + 63` | E1 `12532` / rel `+63` | Editor v5.6 / mapped target |
| aeg_scaling_pan | `E(n) = 12469 + (n-1)*313 + 65` | E1 `12534` / rel `+65` | Editor v5.6 / mapped target |
| xa_control | `E(n) = 12469 + (n-1)*313 + 67` | E1 `12536` / rel `+67` | Editor v5.6 / mapped target |
| note_limit_low | `E(n) = 12469 + (n-1)*313 + 69` | E1 `12538` / rel `+69` | Editor v5.6 / mapped target |
| note_limit_high | `E(n) = 12469 + (n-1)*313 + 71` | E1 `12540` / rel `+71` | Editor v5.6 / mapped target |
| vel_limit_low | `E(n) = 12469 + (n-1)*313 + 73` | E1 `12542` / rel `+73` | Editor v5.6 / mapped target |
| vel_limit_high | `E(n) = 12469 + (n-1)*313 + 75` | E1 `12544` / rel `+75` | Editor v5.6 / mapped target |
| vel_xfade | `E(n) = 12469 + (n-1)*313 + 77` | E1 `12546` / rel `+77` | Editor v5.6 / mapped target |
| delay_length | `E(n) = 12469 + (n-1)*313 + 79` | E1 `12548` / rel `+79` | Editor v5.6 / mapped target |
| elem_connect | `E(n) = 12469 + (n-1)*313 + 81` | E1 `12550` / rel `+81` | Editor v5.6 / mapped target |
| keyondly_sync_delay | `E(n) = 12469 + (n-1)*313 + 85` | E1 `12554` / rel `+85` | Editor v5.6 / mapped target |
| level | `E(n) = 12469 + (n-1)*313 + 91` | E1 `12560` / rel `+91` | Editor v5.6 / mapped target |
| amp_level_vel | `E(n) = 12469 + (n-1)*313 + 93` | E1 `12562` / rel `+93` | Editor v5.6 / mapped target |
| aeg_offset | `E(n) = 12469 + (n-1)*313 + 95` | E1 `12564` / rel `+95` | Editor v5.6 / mapped target |
| amp_level_curve | `E(n) = 12469 + (n-1)*313 + 97` | E1 `12566` / rel `+97` | Editor v5.6 / mapped target |
| aeg_attack | `E(n) = 12469 + (n-1)*313 + 99` | E1 `12568` / rel `+99` | Editor v5.6 / mapped target |
| aeg_decay1 | `E(n) = 12469 + (n-1)*313 + 101` | E1 `12570` / rel `+101` | Editor v5.6 / mapped target |
| aeg_decay2 | `E(n) = 12469 + (n-1)*313 + 103` | E1 `12572` / rel `+103` | Editor v5.6 / mapped target |
| aeg_half_damper_time | `E(n) = 12469 + (n-1)*313 + 105` | E1 `12574` / rel `+105` | Editor v5.6 / mapped target |
| aeg_release | `E(n) = 12469 + (n-1)*313 + 107` | E1 `12576` / rel `+107` | Editor v5.6 / mapped target |
| aeg_initial_level | `E(n) = 12469 + (n-1)*313 + 109` | E1 `12578` / rel `+109` | Editor v5.6 / mapped target |
| aeg_attack_level | `E(n) = 12469 + (n-1)*313 + 111` | E1 `12580` / rel `+111` | Editor v5.6 / mapped target |
| aeg_decay1_level | `E(n) = 12469 + (n-1)*313 + 113` | E1 `12582` / rel `+113` | Editor v5.6 / mapped target |
| aeg_decay2_level | `E(n) = 12469 + (n-1)*313 + 115` | E1 `12584` / rel `+115` | Editor v5.6 / mapped target |
| amp_segment_decay | `E(n) = 12469 + (n-1)*313 + 117` | E1 `12586` / rel `+117` | Editor v5.6 / mapped target |
| amp_time_vel | `E(n) = 12469 + (n-1)*313 + 119` | E1 `12588` / rel `+119` | Editor v5.6 / mapped target |
| amp_time_key | `E(n) = 12469 + (n-1)*313 + 121` | E1 `12590` / rel `+121` | Editor v5.6 / mapped target |
| amp_scaling_center_key | `E(n) = 12469 + (n-1)*313 + 123` | E1 `12592` / rel `+123` | Editor v5.6 / mapped target |
| amp_scaling_bp1 | `E(n) = 12469 + (n-1)*313 + 125` | E1 `12594` / rel `+125` | Editor v5.6 / mapped target |
| amp_scaling_bp2 | `E(n) = 12469 + (n-1)*313 + 127` | E1 `12596` / rel `+127` | Editor v5.6 / mapped target |
| amp_scaling_bp3 | `E(n) = 12469 + (n-1)*313 + 129` | E1 `12598` / rel `+129` | Editor v5.6 / mapped target |
| amp_scaling_bp4 | `E(n) = 12469 + (n-1)*313 + 131` | E1 `12600` / rel `+131` | Editor v5.6 / mapped target |
| amp_scaling_offset1 | `E(n) = 12469 + (n-1)*313 + 133` | E1 `12602` / rel `+133` | Editor v5.6 / mapped target |
| amp_scaling_offset2 | `E(n) = 12469 + (n-1)*313 + 135` | E1 `12604` / rel `+135` | Editor v5.6 / mapped target |
| amp_scaling_offset3 | `E(n) = 12469 + (n-1)*313 + 137` | E1 `12606` / rel `+137` | Editor v5.6 / mapped target |
| amp_scaling_offset4 | `E(n) = 12469 + (n-1)*313 + 139` | E1 `12608` / rel `+139` | Editor v5.6 / mapped target |
| level_key | `E(n) = 12469 + (n-1)*313 + 141` | E1 `12610` / rel `+141` | Editor v5.6 / mapped target |
| amp_release_adj | `E(n) = 12469 + (n-1)*313 + 143` | E1 `12612` / rel `+143` | Editor v5.6 / mapped target |
| coarse_tune | `E(n) = 12469 + (n-1)*313 + 149` | E1 `12618` / rel `+149` | Editor v5.6 / mapped target |
| fine_tune | `E(n) = 12469 + (n-1)*313 + 151` | E1 `12620` / rel `+151` | Editor v5.6 / mapped target |
| pitch_vel | `E(n) = 12469 + (n-1)*313 + 153` | E1 `12622` / rel `+153` | Editor v5.6 / mapped target |
| pitch_random | `E(n) = 12469 + (n-1)*313 + 155` | E1 `12624` / rel `+155` | Editor v5.6 / mapped target |
| pitch_key | `E(n) = 12469 + (n-1)*313 + 157` | E1 `12626` / rel `+157` | Editor v5.6 / mapped target |
| peg_center_key | `E(n) = 12469 + (n-1)*313 + 159` | E1 `12628` / rel `+159` | Editor v5.6 / mapped target |
| fine_key | `E(n) = 12469 + (n-1)*313 + 161` | E1 `12630` / rel `+161` | Editor v5.6 / mapped target |
| peg_hold_time | `E(n) = 12469 + (n-1)*313 + 163` | E1 `12632` / rel `+163` | Editor v5.6 / mapped target |
| peg_signature | `E(n) = 12469 + (n-1)*313 + 169` | E1 `12638` / rel `+169` | Editor v5.6 / mapped target |
| peg_level_hold | `E(n) = 12469 + (n-1)*313 + 173` | E1 `12642` / rel `+173` | Editor v5.6 / mapped target |
| peg_level_attack | `E(n) = 12469 + (n-1)*313 + 175` | E1 `12644` / rel `+175` | Editor v5.6 / mapped target |
| peg_level_decay1 | `E(n) = 12469 + (n-1)*313 + 177` | E1 `12646` / rel `+177` | Editor v5.6 / mapped target |
| peg_level_decay2 | `E(n) = 12469 + (n-1)*313 + 179` | E1 `12648` / rel `+179` | Editor v5.6 / mapped target |
| peg_level_release | `E(n) = 12469 + (n-1)*313 + 181` | E1 `12650` / rel `+181` | Editor v5.6 / mapped target |
| peg_segment | `E(n) = 12469 + (n-1)*313 + 185` | E1 `12654` / rel `+185` | Editor v5.6 / mapped target |
| peg_time_vel | `E(n) = 12469 + (n-1)*313 + 187` | E1 `12656` / rel `+187` | Editor v5.6 / mapped target |
| peg_depth_vel | `E(n) = 12469 + (n-1)*313 + 189` | E1 `12658` / rel `+189` | Editor v5.6 / mapped target |
| peg_curve | `E(n) = 12469 + (n-1)*313 + 191` | E1 `12660` / rel `+191` | Editor v5.6 / mapped target |
| peg_time_key | `E(n) = 12469 + (n-1)*313 + 193` | E1 `12662` / rel `+193` | Editor v5.6 / mapped target |
| filter_type | `E(n) = 12469 + (n-1)*313 + 201` | E1 `12670` / rel `+201` | Editor v5.6 / mapped target |
| filter_cutoff_lo | `E(n) = 12469 + (n-1)*313 + 203` | E1 `12672` / rel `+203` | Editor v5.6 / mapped target |
| filter_cutoff_vel | `E(n) = 12469 + (n-1)*313 + 205` | E1 `12674` / rel `+205` | Editor v5.6 / mapped target |
| filter_resonance | `E(n) = 12469 + (n-1)*313 + 207` | E1 `12676` / rel `+207` | Editor v5.6 / mapped target |
| filter_resonance_vel | `E(n) = 12469 + (n-1)*313 + 209` | E1 `12678` / rel `+209` | Editor v5.6 / mapped target |
| hpf_cutoff_lo | `E(n) = 12469 + (n-1)*313 + 211` | E1 `12680` / rel `+211` | Editor v5.6 / mapped target |
| filter_distance | `E(n) = 12469 + (n-1)*313 + 213` | E1 `12682` / rel `+213` | Editor v5.6 / mapped target |
| filter_gain | `E(n) = 12469 + (n-1)*313 + 215` | E1 `12684` / rel `+215` | Editor v5.6 / mapped target |
| filter_time_attack | `E(n) = 12469 + (n-1)*313 + 219` | E1 `12688` / rel `+219` | Editor v5.6 / mapped target |
| filter_time_decay1 | `E(n) = 12469 + (n-1)*313 + 221` | E1 `12690` / rel `+221` | Editor v5.6 / mapped target |
| filter_time_decay2 | `E(n) = 12469 + (n-1)*313 + 223` | E1 `12692` / rel `+223` | Editor v5.6 / mapped target |
| filter_time_release | `E(n) = 12469 + (n-1)*313 + 225` | E1 `12694` / rel `+225` | Editor v5.6 / mapped target |
| filter_level_hold | `E(n) = 12469 + (n-1)*313 + 227` | E1 `12696` / rel `+227` | Editor v5.6 / mapped target |
| filter_level_attack | `E(n) = 12469 + (n-1)*313 + 229` | E1 `12698` / rel `+229` | Editor v5.6 / mapped target |
| filter_level_decay1 | `E(n) = 12469 + (n-1)*313 + 231` | E1 `12700` / rel `+231` | Editor v5.6 / mapped target |
| filter_level_decay2 | `E(n) = 12469 + (n-1)*313 + 233` | E1 `12702` / rel `+233` | Editor v5.6 / mapped target |
| filter_level_release | `E(n) = 12469 + (n-1)*313 + 235` | E1 `12704` / rel `+235` | Editor v5.6 / mapped target |
| filter_feg_depth | `E(n) = 12469 + (n-1)*313 + 237` | E1 `12706` / rel `+237` | Editor v5.6 / mapped target |
| filter_segment | `E(n) = 12469 + (n-1)*313 + 239` | E1 `12708` / rel `+239` | Editor v5.6 / mapped target |
| filter_time_vel | `E(n) = 12469 + (n-1)*313 + 241` | E1 `12710` / rel `+241` | Editor v5.6 / mapped target |
| feg_depth_vel | `E(n) = 12469 + (n-1)*313 + 243` | E1 `12712` / rel `+243` | Editor v5.6 / mapped target |
| filter_curve | `E(n) = 12469 + (n-1)*313 + 245` | E1 `12714` / rel `+245` | Editor v5.6 / mapped target |
| filter_time_key | `E(n) = 12469 + (n-1)*313 + 247` | E1 `12716` / rel `+247` | Editor v5.6 / mapped target |
| filter_scaling_center_key | `E(n) = 12469 + (n-1)*313 + 249` | E1 `12718` / rel `+249` | Editor v5.6 / mapped target |
| filter_scaling_bp1 | `E(n) = 12469 + (n-1)*313 + 251` | E1 `12720` / rel `+251` | Editor v5.6 / mapped target |
| filter_scaling_bp2 | `E(n) = 12469 + (n-1)*313 + 253` | E1 `12722` / rel `+253` | Editor v5.6 / mapped target |
| filter_scaling_bp3 | `E(n) = 12469 + (n-1)*313 + 255` | E1 `12724` / rel `+255` | Editor v5.6 / mapped target |
| filter_scaling_bp4 | `E(n) = 12469 + (n-1)*313 + 257` | E1 `12726` / rel `+257` | Editor v5.6 / mapped target |
| filter_scaling_cutoff_offset1 | `E(n) = 12469 + (n-1)*313 + 259` | E1 `12728` / rel `+259` | Editor v5.6 / mapped target |
| filter_scaling_cutoff_offset2 | `E(n) = 12469 + (n-1)*313 + 261` | E1 `12730` / rel `+261` | Editor v5.6 / mapped target |
| filter_scaling_cutoff_offset3 | `E(n) = 12469 + (n-1)*313 + 263` | E1 `12732` / rel `+263` | Editor v5.6 / mapped target |
| filter_scaling_cutoff_offset4 | `E(n) = 12469 + (n-1)*313 + 265` | E1 `12734` / rel `+265` | Editor v5.6 / mapped target |
| hpf_cutoff_key | `E(n) = 12469 + (n-1)*313 + 269` | E1 `12738` / rel `+269` | Editor v5.6 / mapped target |
| eq_type | `E(n) = 12469 + (n-1)*313 + 271` | E1 `12740` / rel `+271` | Editor v5.6 / mapped target |
| eq_q_or_resonance | `E(n) = 12469 + (n-1)*313 + 273` | E1 `12742` / rel `+273` | Editor v5.6 / mapped target |
| eq_low_freq | `E(n) = 12469 + (n-1)*313 + 275` | E1 `12744` / rel `+275` | Editor v5.6 / mapped target |
| eq_low_gain | `E(n) = 12469 + (n-1)*313 + 277` | E1 `12746` / rel `+277` | Editor v5.6 / mapped target |
| eq_high_freq | `E(n) = 12469 + (n-1)*313 + 279` | E1 `12748` / rel `+279` | Editor v5.6 / mapped target |
| eq_high_gain | `E(n) = 12469 + (n-1)*313 + 281` | E1 `12750` / rel `+281` | Editor v5.6 / mapped target |
| lfo_wave | `E(n) = 12469 + (n-1)*313 + 283` | E1 `12752` / rel `+283` | Editor v5.6 / mapped target |
| lfo_keyonreset | `E(n) = 12469 + (n-1)*313 + 285` | E1 `12754` / rel `+285` | Editor v5.6 / mapped target |
| lfo_delay | `E(n) = 12469 + (n-1)*313 + 287` | E1 `12756` / rel `+287` | Editor v5.6 / mapped target |
| lfo_speed_legacy | `E(n) = 12469 + (n-1)*313 + 289` | E1 `12758` / rel `+289` | Editor v5.6 / mapped target |
| lfo_amp_mod_depth | `E(n) = 12469 + (n-1)*313 + 291` | E1 `12760` / rel `+291` | Editor v5.6 / mapped target |
| lfo_pitch_mod_depth | `E(n) = 12469 + (n-1)*313 + 293` | E1 `12762` / rel `+293` | Editor v5.6 / mapped target |
| lfo_filter_mod_depth | `E(n) = 12469 + (n-1)*313 + 295` | E1 `12764` / rel `+295` | Editor v5.6 / mapped target |
| lfo_fade_in | `E(n) = 12469 + (n-1)*313 + 297` | E1 `12766` / rel `+297` | Editor v5.6 / mapped target |
| element_lfo_phase_offset | `E(n) = 12469 + (n-1)*313 + 299` | E1 `12768` / rel `+299` | Editor v5.6 / mapped target |
| element_lfo_dest1_depth | `E(n) = 12469 + (n-1)*313 + 301` | E1 `12770` / rel `+301` | Editor v5.6 / mapped target |
| element_lfo_dest2_depth | `E(n) = 12469 + (n-1)*313 + 303` | E1 `12772` / rel `+303` | Editor v5.6 / mapped target |
| element_lfo_dest3_depth | `E(n) = 12469 + (n-1)*313 + 305` | E1 `12774` / rel `+305` | Editor v5.6 / mapped target |
| lfo_speed_extended | `E(n) = 12469 + (n-1)*313 + 307` | E1 `12776` / rel `+307` | Editor v5.6 / mapped target |

---

## 6. FM-X verified source → target coverage (complete v1.0.77 matrix)

This section deliberately carries the complete recovery coverage matrix rather than a summary. It contains **153 tracked parameter points**.

| Area | Parameter | Soundmondo source | Y2L destination | Status | Evidence note |
| --- | --- | --- | --- | --- | --- |
| FM-X Part Common prefix | Random Pan Depth | `3p 00 00 00 +0x00` | `FM-X engine -1` | ESP_VERIFIED | v1.0.75 common-prefix geometry; Smart Brass value unchanged; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X Part Common prefix | Alternate Pan Depth | `3p 00 00 00 +0x02` | `FM-X engine +1` | ESP_VERIFIED | v1.0.75 common-prefix geometry; Smart Brass value unchanged; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X Part Common prefix | Scaling Pan Depth | `3p 00 00 00 +0x04` | `FM-X engine +3` | ESP_VERIFIED | v1.0.75 common-prefix geometry; Smart Brass value unchanged; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X Part Common prefix | Key On Delay Time | `3p 00 00 00 +0x06` | `FM-X engine +5` | ESP_VERIFIED | v1.0.75 common-prefix geometry; Smart Brass value unchanged; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X Part Common prefix | Key On Delay Tempo Sync | `3p 00 00 00 +0x08` | `FM-X engine +7` | ESP_VERIFIED | v1.0.75 common-prefix geometry; Smart Brass value unchanged; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X Part Common prefix | Key On Delay Note Length | `3p 00 00 00 +0x0A` | `FM-X engine +9` | ESP_VERIFIED | Source code 11 → Y2L code 14 established from historical FM-X Init default pattern; Parts 9/10 patched in v1.0.75; ESP-verified by Johan on 2026-08-11 in MODX M ESP (v1.0.75/v1.0.76 lineage). |
| FM-X Part PEG | Pitch Velocity Sensitivity | `3p 00 00 00 +0x0C` | `FM-X engine +11` | ESP_VERIFIED | v1.0.57/v1.0.70 lineage |
| FM-X Part PEG | Random Pitch Depth | `3p 00 00 00 +0x0E` | `FM-X engine +13` | ESP_VERIFIED | v1.0.57/v1.0.70 lineage |
| FM-X Part PEG | Pitch Key Follow | `3p 00 00 00 +0x10` | `FM-X engine +15` | ESP_VERIFIED | v1.0.57/v1.0.70 lineage |
| FM-X Part PEG | Pitch Key Follow Center Note | `3p 00 00 00 +0x12` | `FM-X engine +17` | ESP_VERIFIED | v1.0.57/v1.0.70 lineage |
| FM-X Part PEG | PEG Initial Level | `3p 00 00 00 +0x14` | `FM-X engine +19` | ESP_VERIFIED | v1.0.57/v1.0.70 lineage |
| FM-X Part PEG | PEG Attack Level | `3p 00 00 00 +0x16` | `FM-X engine +21` | ESP_VERIFIED | v1.0.57/v1.0.70 lineage |
| FM-X Part PEG | PEG Decay1 Level | `3p 00 00 00 +0x18` | `FM-X engine +23` | ESP_VERIFIED | v1.0.57/v1.0.70 lineage |
| FM-X Part PEG | PEG Decay2 Level | `3p 00 00 00 +0x1A` | `FM-X engine +25` | ESP_VERIFIED | v1.0.57/v1.0.70 lineage |
| FM-X Part PEG | PEG Release Level | `3p 00 00 00 +0x1C` | `FM-X engine +27` | ESP_VERIFIED | v1.0.57/v1.0.70 lineage |
| FM-X Part PEG | PEG Attack Time | `3p 00 00 00 +0x1E` | `FM-X engine +29` | ESP_VERIFIED | v1.0.57/v1.0.70 lineage |
| FM-X Part PEG | PEG Decay1 Time | `3p 00 00 00 +0x20` | `FM-X engine +31` | ESP_VERIFIED | v1.0.57/v1.0.70 lineage |
| FM-X Part PEG | PEG Decay2 Time | `3p 00 00 00 +0x22` | `FM-X engine +33` | ESP_VERIFIED | v1.0.57/v1.0.70 lineage |
| FM-X Part PEG | PEG Release Time | `3p 00 00 00 +0x24` | `FM-X engine +35` | ESP_VERIFIED | v1.0.57/v1.0.70 lineage |
| FM-X Part PEG | PEG Depth Velocity | `3p 00 00 00 +0x26` | `FM-X engine +37` | ESP_VERIFIED | v1.0.57/v1.0.70 lineage |
| FM-X Part PEG | PEG Depth | `3p 00 00 00 +0x28` | `FM-X engine +39` | ESP_VERIFIED | v1.0.57/v1.0.70 lineage |
| FM-X Part PEG | PEG Time Key Follow | `3p 00 00 00 +0x2A` | `FM-X engine +41` | ESP_VERIFIED | v1.0.57/v1.0.70 lineage |
| FM-X Part Common | 2nd LFO Wave | `3p 00 00 00 +0x2C` | `historically mapped` | ESP_VERIFIED | v1.0.57 |
| FM-X Part Common | 2nd LFO Speed Normal | `3p 00 00 00 +0x2E` | `historically mapped` | ESP_VERIFIED | v1.0.57 |
| FM-X Part Common | 2nd LFO Phase | `3p 00 00 00 +0x30` | `historically mapped` | ESP_VERIFIED | v1.0.57 |
| FM-X Part Common | 2nd LFO Delay | `3p 00 00 00 +0x32` | `historically mapped` | ESP_VERIFIED | v1.0.57 |
| FM-X Part Common | 2nd LFO Key On Reset | `3p 00 00 00 +0x34` | `historically mapped` | ESP_VERIFIED | v1.0.57 |
| FM-X Part Common | 2nd LFO Pitch Mod Depth | `3p 00 00 00 +0x36` | `verified matrix` | ESP_VERIFIED | v1.0.64 |
| FM-X Part Common | 2nd LFO Amplitude Mod Depth | `3p 00 00 00 +0x38` | `verified matrix` | ESP_VERIFIED | v1.0.64 |
| FM-X Part Common | 2nd LFO Filter Mod Depth | `3p 00 00 00 +0x3A` | `verified matrix` | ESP_VERIFIED | v1.0.64 |
| FM-X Part Common | Algorithm | `3p 00 00 00 +0x3C` | `engine +59` | ESP_VERIFIED | v1.0.65 |
| FM-X Part Common | Feedback | `3p 00 00 00 +0x3E` | `engine +61` | ESP_VERIFIED | v1.0.65 |
| FM-X Part Common | 2nd LFO Speed Range | `3p 00 00 00 +0x40` | `historically mapped` | ESP_VERIFIED | v1.0.57 |
| FM-X Part Common | 2nd LFO Extended Speed | `3p 00 00 00 +0x42` | `historically mapped` | ESP_VERIFIED | v1.0.57 |
| FM-X Part Common | FM Color Depth | `3p 00 00 00 +0x44` | `engine +79` | ESP_VERIFIED | v1.0.61 |
| FM-X Part Common | FM Color Harmonics | `3p 00 00 00 +0x46` | `engine +81` | ESP_VERIFIED | v1.0.61 |
| FM-X Part Common | FM Color Attack | `3p 00 00 00 +0x48` | `engine +83` | ESP_VERIFIED | v1.0.61 |
| FM-X Part Common | FM Color Decay | `3p 00 00 00 +0x4A` | `engine +85` | ESP_VERIFIED | v1.0.61 |
| FM-X Part Common | FM Color Sustain | `3p 00 00 00 +0x4C` | `engine +87` | ESP_VERIFIED | v1.0.61 |
| FM-X Part Common | FM Color Release | `3p 00 00 00 +0x4E` | `engine +89` | ESP_VERIFIED | v1.0.61 |
| FM-X Part Common | FM Color Texture | `3p 00 00 00 +0x50` | `engine +91` | ESP_VERIFIED | v1.0.61 |
| FM-X Filter/FEG | Filter Type | `3p 00 01 00 +0x00` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | Cutoff | `3p 00 01 00 +0x02` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | Cutoff Velocity | `3p 00 01 00 +0x04` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | Resonance | `3p 00 01 00 +0x06` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | Resonance Velocity | `3p 00 01 00 +0x08` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | HPF Cutoff | `3p 00 01 00 +0x0A` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | Distance | `3p 00 01 00 +0x0C` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | Gain | `3p 00 01 00 +0x0E` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Hold Time | `3p 00 01 00 +0x10` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Attack Time | `3p 00 01 00 +0x12` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Decay1 Time | `3p 00 01 00 +0x14` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Decay2 Time | `3p 00 01 00 +0x16` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Release Time | `3p 00 01 00 +0x18` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Hold Level | `3p 00 01 00 +0x1A` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Attack Level | `3p 00 01 00 +0x1C` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Decay1 Level | `3p 00 01 00 +0x1E` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Decay2 Level | `3p 00 01 00 +0x20` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Release Level | `3p 00 01 00 +0x22` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Depth | `3p 00 01 00 +0x24` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Time Velocity Segment | `3p 00 01 00 +0x26` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Time Velocity | `3p 00 01 00 +0x28` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Depth Velocity | `3p 00 01 00 +0x2A` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Depth Velocity Curve | `3p 00 01 00 +0x2C` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Time Key Follow | `3p 00 01 00 +0x2E` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | FEG Time Key Center Note | `3p 00 01 00 +0x30` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | Cutoff Key Follow | `3p 00 01 00 +0x32` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | Scaling BP1 | `3p 00 01 00 +0x34` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | Scaling BP2 | `3p 00 01 00 +0x36` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | Scaling BP3 | `3p 00 01 00 +0x38` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | Scaling BP4 | `3p 00 01 00 +0x3A` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | Scaling Offset1 | `3p 00 01 00 +0x3C` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | Scaling Offset2 | `3p 00 01 00 +0x3E` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | Scaling Offset3 | `3p 00 01 00 +0x40` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | Scaling Offset4 | `3p 00 01 00 +0x42` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Filter/FEG | HPF Cutoff Key Follow | `3p 00 01 00 +0x44` | `verified modern re-anchor` | ESP_VERIFIED | v1.0.62/v1.0.63 |
| FM-X Operator | Key On Reset | `3p 02 0o 00 +0x00` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | Frequency Mode | `3p 02 0o 00 +0x02` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | Tune Coarse | `3p 02 0o 00 +0x04` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | Tune Fine | `3p 02 0o 00 +0x06` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | Detune | `3p 02 0o 00 +0x08` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | Pitch Key | `3p 02 0o 00 +0x0A` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | Pitch Velocity | `3p 02 0o 00 +0x0C` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | Spectral Form | `3p 02 0o 00 +0x0E` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | Spectral Skirt | `3p 02 0o 00 +0x10` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | Spectral Resonance | `3p 02 0o 00 +0x12` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | PEG Initial Level | `3p 02 0o 00 +0x14` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | PEG Attack Level | `3p 02 0o 00 +0x16` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | PEG Attack Time | `3p 02 0o 00 +0x18` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | PEG Decay Time | `3p 02 0o 00 +0x1A` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | AEG Attack Level | `3p 02 0o 00 +0x1C` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | AEG Decay1 Level | `3p 02 0o 00 +0x1E` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | AEG Decay2 Level | `3p 02 0o 00 +0x20` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | AEG Release Level | `3p 02 0o 00 +0x22` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | AEG Attack Time | `3p 02 0o 00 +0x24` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | AEG Decay1 Time | `3p 02 0o 00 +0x26` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | AEG Decay2 Time | `3p 02 0o 00 +0x28` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | AEG Release Time | `3p 02 0o 00 +0x2A` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | AEG Hold Time | `3p 02 0o 00 +0x2C` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | AEG Time Key Follow | `3p 02 0o 00 +0x2E` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | Level | `3p 02 0o 00 +0x30` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | Level Scaling Break Point | `3p 02 0o 00 +0x32` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | Level Scaling Low Depth | `3p 02 0o 00 +0x34` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | Level Scaling High Depth | `3p 02 0o 00 +0x36` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | Level Scaling Low Curve | `3p 02 0o 00 +0x38` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | Level Scaling High Curve | `3p 02 0o 00 +0x3A` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | Level Velocity | `3p 02 0o 00 +0x3C` | `operator record verified; stride 123` | ESP_VERIFIED | v1.0.55-v1.0.69 |
| FM-X Operator | 2nd LFO Pitch Mod Depth | `3p 02 0o 00 +0x3E` | `operator matrix` | ESP_VERIFIED | v1.0.64 |
| FM-X Operator | 2nd LFO Amplitude Mod Depth | `3p 02 0o 00 +0x40` | `operator matrix` | ESP_VERIFIED | v1.0.64 |
| FM-X Operator | Pitch Controller Sensitivity | `3p 02 0o 00 +0x42` | `FM-X operator coarse +62` | ESP_VERIFIED | Source UI 0/code 7; historical FM-X Init destination default 0 at coarse+62; v1.0.75 had 127 in Smart Brass, patched 127→0 for all 32 FM-X operators in v1.0.76; ESP-verified by Johan on 2026-08-11 in MODX M ESP (v1.0.75/v1.0.76 lineage). |
| FM-X Operator | Level Controller Sensitivity | `3p 02 0o 00 +0x44` | `FM-X operator coarse +64` | ESP_VERIFIED | Source UI 0/code 7; historical FM-X Init destination default 0 at coarse+64; v1.0.75 had 127 in Smart Brass, patched 127→0 for all 32 FM-X operators in v1.0.76; ESP-verified by Johan on 2026-08-11 in MODX M ESP (v1.0.75/v1.0.76 lineage). |
| FM-X Operator | 1st LFO Dest1 Depth Ratio | `Yamaha documented +0x46; omitted by Soundmondo 1.0.0` | `operator +66` | ESP_VERIFIED | Default 127 written and ESP verified in v1.0.72; default-derived source omission accepted in final ESP-verified lineage. |
| FM-X Operator | 1st LFO Dest2 Depth Ratio | `Yamaha documented +0x48; omitted by Soundmondo 1.0.0` | `operator +68` | ESP_VERIFIED | Default 127 written and ESP verified in v1.0.72; default-derived source omission accepted in final ESP-verified lineage. |
| FM-X Operator | 1st LFO Dest3 Depth Ratio | `Yamaha documented +0x4A; omitted by Soundmondo 1.0.0` | `operator +70` | ESP_VERIFIED | Default 127 written and ESP verified in v1.0.72; default-derived source omission accepted in final ESP-verified lineage. |
| FM-X 1st LFO | Phase | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Wave | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Speed | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Tempo Note | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Delay | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Fade In | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Hold | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Fade Out | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Key On Reset | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Destination1 | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Destination1 Depth | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Destination2 | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Destination2 Depth | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Destination3 | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Destination3 Depth | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Random Speed | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Tempo Sync | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO | Loop | `1p 00 07 00 / 1p 00 01 00` | `historically absolute-mapped` | ESP_VERIFIED | v1.0.59/v1.0.71 |
| FM-X 1st LFO User | User Cycle | `1p 00 07 00 +0x1E` | `Part1 blob+7229; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Slope | `1p 00 07 00 +0x20` | `Part1 blob+7231; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Step 1 | `1p 00 07 00 +0x22` | `Part1 blob+7233; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Step 2 | `1p 00 07 00 +0x24` | `Part1 blob+7235; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Step 3 | `1p 00 07 00 +0x26` | `Part1 blob+7237; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Step 4 | `1p 00 07 00 +0x28` | `Part1 blob+7239; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Step 5 | `1p 00 07 00 +0x2A` | `Part1 blob+7241; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Step 6 | `1p 00 07 00 +0x2C` | `Part1 blob+7243; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Step 7 | `1p 00 07 00 +0x2E` | `Part1 blob+7245; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Step 8 | `1p 00 07 00 +0x30` | `Part1 blob+7247; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Step 9 | `1p 00 07 00 +0x32` | `Part1 blob+7249; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Step 10 | `1p 00 07 00 +0x34` | `Part1 blob+7251; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Step 11 | `1p 00 07 00 +0x36` | `Part1 blob+7253; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Step 12 | `1p 00 07 00 +0x38` | `Part1 blob+7255; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Step 13 | `1p 00 07 00 +0x3A` | `Part1 blob+7257; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Step 14 | `1p 00 07 00 +0x3C` | `Part1 blob+7259; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Step 15 | `1p 00 07 00 +0x3E` | `Part1 blob+7261; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| FM-X 1st LFO User | User Step 16 | `1p 00 07 00 +0x40` | `Part1 blob+7263; +5765*(part-1)` | ESP_VERIFIED | Historical Steg 56 Init base confirms contiguous layout/defaults; v1.0.74 checks source vs current Y2L for Parts 1/9/10/11. Y2L unchanged from ESP-verified v1.0.72/73.; inherited into final ESP-verified v1.0.76/v1.0.77 lineage. |
| Part-level FM-X control | FEG Depth Offset | `1p 00 02 00 +0x32` | `Part Common +164` | ESP_VERIFIED | v1.0.60 |
| Part-level FM-X control | Filter Cutoff Offset | `1p 00 02 00 +0x34` | `Part Common +166` | ESP_VERIFIED | v1.0.60 |
| Part-level FM-X control | Resonance Offset | `1p 00 02 00 +0x36` | `Part Common +168` | ESP_VERIFIED | v1.0.60 |

---

## 7. FM-X target helper maps from current editor

### Part/engine pre-operator fields

| Parameter | Blob target | Engine relative | Status |
| --- | --- | --- | --- |
| peg_pitch_velocity | blob `12477` | FM-X engine rel `+11` | Editor v5.6 / mapped target |
| peg_random_pitch | blob `12479` | FM-X engine rel `+13` | Editor v5.6 / mapped target |
| peg_pitch_key | blob `12481` | FM-X engine rel `+15` | Editor v5.6 / mapped target |
| peg_center_key | blob `12483` | FM-X engine rel `+17` | Editor v5.6 / mapped target |
| peg_level_initial | blob `12485` | FM-X engine rel `+19` | Editor v5.6 / mapped target |
| peg_level_attack | blob `12487` | FM-X engine rel `+21` | Editor v5.6 / mapped target |
| peg_level_decay1 | blob `12489` | FM-X engine rel `+23` | Editor v5.6 / mapped target |
| peg_level_decay2 | blob `12491` | FM-X engine rel `+25` | Editor v5.6 / mapped target |
| peg_level_release | blob `12493` | FM-X engine rel `+27` | Editor v5.6 / mapped target |
| peg_time_attack | blob `12495` | FM-X engine rel `+29` | Editor v5.6 / mapped target |
| peg_time_decay1 | blob `12497` | FM-X engine rel `+31` | Editor v5.6 / mapped target |
| peg_time_decay2 | blob `12499` | FM-X engine rel `+33` | Editor v5.6 / mapped target |
| peg_time_release | blob `12501` | FM-X engine rel `+35` | Editor v5.6 / mapped target |
| peg_depth_velocity | blob `12503` | FM-X engine rel `+37` | Editor v5.6 / mapped target |
| peg_depth | blob `12505` | FM-X engine rel `+39` | Editor v5.6 / mapped target |
| peg_time_key | blob `12507` | FM-X engine rel `+41` | Editor v5.6 / mapped target |
| lfo_wave | blob `12509` | FM-X engine rel `+43` | Editor v5.6 / mapped target |
| key_on_reset | blob `12517` | FM-X engine rel `+51` | Editor v5.6 / mapped target |
| algo | blob `12525` | FM-X engine rel `+59` | Editor v5.6 / mapped target |
| feedback | blob `12527` | FM-X engine rel `+61` | Editor v5.6 / mapped target |
| second_lfo_extended | blob `12529` | FM-X engine rel `+63` | Editor v5.6 / mapped target |
| second_lfo_wave_speed | blob `12531` | FM-X engine rel `+65` | Editor v5.6 / mapped target |
| filter_type | blob `12547` | FM-X engine rel `+81` | Editor v5.6 / mapped target |
| filter_cutoff_lo | blob `12549` | FM-X engine rel `+83` | Editor v5.6 / mapped target |
| filter_cutoff_vel | blob `12551` | FM-X engine rel `+85` | Editor v5.6 / mapped target |
| filter_resonance | blob `12553` | FM-X engine rel `+87` | Editor v5.6 / mapped target |
| filter_resonance_vel | blob `12555` | FM-X engine rel `+89` | Editor v5.6 / mapped target |
| filter_hpf_cutoff | blob `12557` | FM-X engine rel `+91` | Editor v5.6 / mapped target |
| feg_gain | blob `12561` | FM-X engine rel `+95` | Editor v5.6 / mapped target |
| feg_hold_time | blob `12563` | FM-X engine rel `+97` | Editor v5.6 / mapped target |
| feg_attack_time | blob `12565` | FM-X engine rel `+99` | Editor v5.6 / mapped target |
| feg_decay_time | blob `12567` | FM-X engine rel `+101` | Editor v5.6 / mapped target |
| feg_sustain_time | blob `12569` | FM-X engine rel `+103` | Editor v5.6 / mapped target |
| feg_release_time | blob `12571` | FM-X engine rel `+105` | Editor v5.6 / mapped target |
| feg_hold_level | blob `12573` | FM-X engine rel `+107` | Editor v5.6 / mapped target |
| feg_attack_level | blob `12575` | FM-X engine rel `+109` | Editor v5.6 / mapped target |
| feg_decay_level | blob `12577` | FM-X engine rel `+111` | Editor v5.6 / mapped target |
| feg_sustain_level | blob `12579` | FM-X engine rel `+113` | Editor v5.6 / mapped target |
| feg_release_level | blob `12581` | FM-X engine rel `+115` | Editor v5.6 / mapped target |
| feg_depth | blob `12583` | FM-X engine rel `+117` | Editor v5.6 / mapped target |
| feg_segment | blob `12585` | FM-X engine rel `+119` | Editor v5.6 / mapped target |
| feg_time_vel | blob `12587` | FM-X engine rel `+121` | Editor v5.6 / mapped target |
| feg_depth_vel | blob `12589` | FM-X engine rel `+123` | Editor v5.6 / mapped target |
| feg_curve | blob `12591` | FM-X engine rel `+125` | Editor v5.6 / mapped target |
| time_key_scaling | blob `12593` | FM-X engine rel `+127` | Editor v5.6 / mapped target |
| center_key | blob `12595` | FM-X engine rel `+129` | Editor v5.6 / mapped target |
| break_point_1 | blob `12599` | FM-X engine rel `+133` | Editor v5.6 / mapped target |
| break_point_2 | blob `12601` | FM-X engine rel `+135` | Editor v5.6 / mapped target |
| break_point_3 | blob `12603` | FM-X engine rel `+137` | Editor v5.6 / mapped target |
| break_point_4 | blob `12605` | FM-X engine rel `+139` | Editor v5.6 / mapped target |
| cutoff_offset_1 | blob `12607` | FM-X engine rel `+141` | Editor v5.6 / mapped target |
| cutoff_offset_2 | blob `12609` | FM-X engine rel `+143` | Editor v5.6 / mapped target |
| cutoff_offset_3 | blob `12611` | FM-X engine rel `+145` | Editor v5.6 / mapped target |
| cutoff_offset_4 | blob `12613` | FM-X engine rel `+147` | Editor v5.6 / mapped target |

### Operator repeated record

`OP1 base = 12676`, `operator stride = 123`.

| Parameter | Target formula | OP1 coordinate | Status |
| --- | --- | --- | --- |
| coarse | `OP(n) = 12676 + (n-1)*123 + 0` | OP1 `12676` / rel `+0` | Editor v5.6; FM-X completion lineage |
| fine | `OP(n) = 12676 + (n-1)*123 + 2` | OP1 `12678` / rel `+2` | Editor v5.6; FM-X completion lineage |
| detune | `OP(n) = 12676 + (n-1)*123 + 4` | OP1 `12680` / rel `+4` | Editor v5.6; FM-X completion lineage |
| pitch_key_fixed | `OP(n) = 12676 + (n-1)*123 + 6` | OP1 `12682` / rel `+6` | Editor v5.6; FM-X completion lineage |
| pitch_vel_fixed | `OP(n) = 12676 + (n-1)*123 + 8` | OP1 `12684` / rel `+8` | Editor v5.6; FM-X completion lineage |
| spectral | `OP(n) = 12676 + (n-1)*123 + 10` | OP1 `12686` / rel `+10` | Editor v5.6; FM-X completion lineage |
| spectral_skirt | `OP(n) = 12676 + (n-1)*123 + 12` | OP1 `12688` / rel `+12` | Editor v5.6; FM-X completion lineage |
| spectral_resonance | `OP(n) = 12676 + (n-1)*123 + 14` | OP1 `12690` / rel `+14` | Editor v5.6; FM-X completion lineage |
| level_initial | `OP(n) = 12676 + (n-1)*123 + 16` | OP1 `12692` / rel `+16` | Editor v5.6; FM-X completion lineage |
| level_attack | `OP(n) = 12676 + (n-1)*123 + 18` | OP1 `12694` / rel `+18` | Editor v5.6; FM-X completion lineage |
| time_attack | `OP(n) = 12676 + (n-1)*123 + 20` | OP1 `12696` / rel `+20` | Editor v5.6; FM-X completion lineage |
| time_delay | `OP(n) = 12676 + (n-1)*123 + 22` | OP1 `12698` / rel `+22` | Editor v5.6; FM-X completion lineage |
| aeg_attack_level | `OP(n) = 12676 + (n-1)*123 + 24` | OP1 `12700` / rel `+24` | Editor v5.6; FM-X completion lineage |
| aeg_decay1_level | `OP(n) = 12676 + (n-1)*123 + 26` | OP1 `12702` / rel `+26` | Editor v5.6; FM-X completion lineage |
| aeg_decay2_level | `OP(n) = 12676 + (n-1)*123 + 28` | OP1 `12704` / rel `+28` | Editor v5.6; FM-X completion lineage |
| aeg_release_level | `OP(n) = 12676 + (n-1)*123 + 30` | OP1 `12706` / rel `+30` | Editor v5.6; FM-X completion lineage |
| attack | `OP(n) = 12676 + (n-1)*123 + 32` | OP1 `12708` / rel `+32` | Editor v5.6; FM-X completion lineage |
| decay1 | `OP(n) = 12676 + (n-1)*123 + 34` | OP1 `12710` / rel `+34` | Editor v5.6; FM-X completion lineage |
| decay2 | `OP(n) = 12676 + (n-1)*123 + 36` | OP1 `12712` / rel `+36` | Editor v5.6; FM-X completion lineage |
| release | `OP(n) = 12676 + (n-1)*123 + 38` | OP1 `12714` / rel `+38` | Editor v5.6; FM-X completion lineage |
| hold | `OP(n) = 12676 + (n-1)*123 + 40` | OP1 `12716` / rel `+40` | Editor v5.6; FM-X completion lineage |
| time_key | `OP(n) = 12676 + (n-1)*123 + 42` | OP1 `12718` / rel `+42` | Editor v5.6; FM-X completion lineage |
| level | `OP(n) = 12676 + (n-1)*123 + 44` | OP1 `12720` / rel `+44` | Editor v5.6; FM-X completion lineage |
| aeg_breakpoint | `OP(n) = 12676 + (n-1)*123 + 46` | OP1 `12722` / rel `+46` | Editor v5.6; FM-X completion lineage |
| lvl_key_lo | `OP(n) = 12676 + (n-1)*123 + 48` | OP1 `12724` / rel `+48` | Editor v5.6; FM-X completion lineage |
| lvl_key_hi | `OP(n) = 12676 + (n-1)*123 + 50` | OP1 `12726` / rel `+50` | Editor v5.6; FM-X completion lineage |
| curve_lo | `OP(n) = 12676 + (n-1)*123 + 52` | OP1 `12728` / rel `+52` | Editor v5.6; FM-X completion lineage |
| curve_hi | `OP(n) = 12676 + (n-1)*123 + 54` | OP1 `12730` / rel `+54` | Editor v5.6; FM-X completion lineage |
| level_vel | `OP(n) = 12676 + (n-1)*123 + 56` | OP1 `12732` / rel `+56` | Editor v5.6; FM-X completion lineage |
| lfo2_pitch_mod_dest | `OP(n) = 12676 + (n-1)*123 + 58` | OP1 `12734` / rel `+58` | Editor v5.6; FM-X completion lineage |
| lfo2_amp_mod_dest | `OP(n) = 12676 + (n-1)*123 + 60` | OP1 `12736` / rel `+60` | Editor v5.6; FM-X completion lineage |

---

## 8. AN-X modern Y2L target map

Oscillator bases: OSC1 `12626`, OSC2 `12751`, OSC3 `12876`; oscillator stride `125`.

| Area | Parameter | Target coordinate | Coordinate note | Status |
| --- | --- | --- | --- | --- |
| Part/pre-OSC | alternate_pan_anx | blob `12467` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | scaling_pan_anx | blob `12469` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | unison_voices | blob `12477` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | unison_detune | blob `12479` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | unison_spread | blob `12481` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | part_key_on_delay_sw | blob `12482` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | part_half_damper_sw | blob `12483` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | osc_reset_mode | blob `12485` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | voltage_drift | blob `12487` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | ageing | blob `12489` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | peg_time_vel | blob `12499` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | pitch_lfo_speed_lo | blob `12503` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | pitch_lfo_phase | blob `12507` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | pitch_lfo_delay | blob `12509` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | pitch_lfo_fadein | blob `12511` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | noise_tone | blob `12513` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | noise_connect | blob `12515` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | feg_attack | blob `12517` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | feg_decay | blob `12519` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | feg_sustain | blob `12521` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | feg_release | blob `12523` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | feg_time_vel | blob `12529` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | filter_lfo_wave | blob `12531` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | filter_lfo_speed_lo | blob `12533` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | filter_lfo_phase | blob `12537` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | filter_lfo_delay | blob `12539` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | filter_lfo_fadein | blob `12541` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | amp_level | blob `12543` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | amp_level_vel | blob `12545` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | amp_lfo_depth | blob `12547` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | amp_drive | blob `12551` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | amp_aeg_attack | blob `12549` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | amp_aeg_decay | blob `12551` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | amp_aeg_sustain_lo | blob `12553` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | amp_aeg_release | blob `12555` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | amp_aeg_time_vel | blob `12557` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | amp_lfo_wave | blob `12563` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | amp_lfo_speed_lo | blob `12565` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | amp_lfo_phase | blob `12569` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | amp_lfo_delay | blob `12571` | absolute performance-blob offset | Editor v5.6 |
| Part/pre-OSC | amp_lfo_fadein | blob `12573` | absolute performance-blob offset | Editor v5.6 |
| Oscillator | waveform | `OSC(n) base +0` | OSC1 `12626`; stride 125 | Editor v5.6 |
| Oscillator | octave | `OSC(n) base +2` | OSC1 `12628`; stride 125 | Editor v5.6 |
| Oscillator | pitch_lo | `OSC(n) base +4` | OSC1 `12630`; stride 125 | Editor v5.6 |
| Oscillator | peg_depth_lo | `OSC(n) base +6` | OSC1 `12632`; stride 125 | Editor v5.6 |
| Oscillator | peg_depth_vel | `OSC(n) base +8` | OSC1 `12634`; stride 125 | Editor v5.6 |
| Oscillator | pitch_lfo_depth_lo | `OSC(n) base +10` | OSC1 `12636`; stride 125 | Editor v5.6 |
| Oscillator | sync_pitch | `OSC(n) base +12` | OSC1 `12638`; stride 125 | Editor v5.6 |
| Oscillator | sync_vel | `OSC(n) base +14` | OSC1 `12640`; stride 125 | Editor v5.6 |
| Oscillator | sync_eg_depth | `OSC(n) base +16` | OSC1 `12642`; stride 125 | Editor v5.6 |
| Oscillator | sync_lfo_depth | `OSC(n) base +18` | OSC1 `12644`; stride 125 | Editor v5.6 |
| Oscillator | pulse_width | `OSC(n) base +20` | OSC1 `12646`; stride 125 | Editor v5.6 |
| Oscillator | pulse_width_vel | `OSC(n) base +22` | OSC1 `12648`; stride 125 | Editor v5.6 |
| Oscillator | pulse_width_eg_depth | `OSC(n) base +24` | OSC1 `12650`; stride 125 | Editor v5.6 |
| Oscillator | pulse_width_lfo_depth | `OSC(n) base +26` | OSC1 `12652`; stride 125 | Editor v5.6 |
| Oscillator | wave_shaper | `OSC(n) base +28` | OSC1 `12654`; stride 125 | Editor v5.6 |
| Oscillator | wave_shaper_vel | `OSC(n) base +30` | OSC1 `12656`; stride 125 | Editor v5.6 |
| Oscillator | shaper_eg_depth | `OSC(n) base +32` | OSC1 `12658`; stride 125 | Editor v5.6 |
| Oscillator | shaper_lfo_depth | `OSC(n) base +34` | OSC1 `12660`; stride 125 | Editor v5.6 |
| Oscillator | fm_level_vel | `OSC(n) base +38` | OSC1 `12664`; stride 125 | Editor v5.6 |
| Oscillator | ring_mod | `OSC(n) base +40` | OSC1 `12666`; stride 125 | Editor v5.6 |
| Oscillator | key_on_reset | `OSC(n) base +46` | OSC1 `12672`; stride 125 | Editor v5.6 |
| Oscillator | out_level_lo | `OSC(n) base +48` | OSC1 `12674`; stride 125 | Editor v5.6 |
| Oscillator | out_level_vel | `OSC(n) base +50` | OSC1 `12676`; stride 125 | Editor v5.6 |
| Oscillator | eg_attack | `OSC(n) base +52` | OSC1 `12678`; stride 125 | Editor v5.6 |
| Oscillator | eg_decay | `OSC(n) base +54` | OSC1 `12680`; stride 125 | Editor v5.6 |
| Oscillator | eg_sustain | `OSC(n) base +56` | OSC1 `12682`; stride 125 | Editor v5.6 |
| Oscillator | eg_release | `OSC(n) base +58` | OSC1 `12684`; stride 125 | Editor v5.6 |
| Filter 1 | type | blob `13005` | absolute | Editor v5.6 |
| Filter 1 | cutoff_lo | blob `13007` | absolute | Editor v5.6 |
| Filter 1 | cutoff_vel | blob `13009` | absolute | Editor v5.6 |
| Filter 1 | feg_depth_lo | blob `13011` | absolute | Editor v5.6 |
| Filter 1 | feg_depth_vel | blob `13013` | absolute | Editor v5.6 |
| Filter 1 | lfo_depth_lo | blob `13015` | absolute | Editor v5.6 |
| Filter 1 | cutoff_key | blob `13017` | absolute | Editor v5.6 |
| Filter 1 | resonance | blob `13019` | absolute | Editor v5.6 |
| Filter 1 | resonance_vel | blob `13021` | absolute | Editor v5.6 |
| Filter 1 | drive | blob `13023` | absolute | Editor v5.6 |
| Filter 1 | drive_vel | blob `13025` | absolute | Editor v5.6 |
| Filter 1 | out_level | blob `13027` | absolute | Editor v5.6 |
| Filter 2 | type | blob `13082` | absolute | Editor v5.6 |
| Filter 2 | cutoff_lo | blob `13084` | absolute | Editor v5.6 |
| Filter 2 | cutoff_vel | blob `13086` | absolute | Editor v5.6 |
| Filter 2 | feg_depth_lo | blob `13088` | absolute | Editor v5.6 |
| Filter 2 | feg_depth_vel | blob `13090` | absolute | Editor v5.6 |
| Filter 2 | lfo_depth_lo | blob `13092` | absolute | Editor v5.6 |
| Filter 2 | cutoff_key | blob `13094` | absolute | Editor v5.6 |
| Filter 2 | resonance | blob `13096` | absolute | Editor v5.6 |
| Filter 2 | resonance_vel | blob `13098` | absolute | Editor v5.6 |
| Filter 2 | drive | blob `13100` | absolute | Editor v5.6 |
| Filter 2 | drive_vel | blob `13102` | absolute | Editor v5.6 |
| Filter 2 | out_level | blob `13104` | absolute | Editor v5.6 |
| Wave Folder | amount | blob `13116` | absolute | Editor v5.6 |
| Wave Folder | vel | blob `13118` | absolute | Editor v5.6 |
| Wave Folder | eg_depth | blob `13120` | absolute | Editor v5.6 |
| Wave Folder | modlfo_depth | blob `13122` | absolute | Editor v5.6 |
| Wave Folder | texture | blob `13124` | absolute | Editor v5.6 |
| Wave Folder | type | blob `13126` | absolute | Editor v5.6 |
| Modifier EG | attack | blob `13128` | absolute | Editor v5.6 |
| Modifier EG | decay | blob `13130` | absolute | Editor v5.6 |
| Modifier EG | sustain | blob `13132` | absolute | Editor v5.6 |
| Modifier EG | release | blob `13134` | absolute | Editor v5.6 |
| Modifier LFO | wave | blob `13138` | absolute | Editor v5.6 |
| Modifier LFO | speed_lo | blob `13140` | absolute | Editor v5.6 |
| Modifier LFO | delay | blob `13146` | absolute | Editor v5.6 |
| Modifier LFO | fadein | blob `13148` | absolute | Editor v5.6 |

---

## 9. Drum modern Y2L target map

Part 1 begins at blob `6708`; Drum Key1 base `12469`, key stride `68`.

| Area | Parameter | Target coordinate | Relative/formula | Status |
| --- | --- | --- | --- | --- |
| Part Common | drumPartFilterCutoff | blob `6867` | Part1-relative `+159` | Editor v5.6 |
| Part Common | drumPartResonance | blob `6869` | Part1-relative `+161` | Editor v5.6 |
| Part Common | drumPitchBendUpper | blob `6913` | Part1-relative `+205` | Editor v5.6 |
| Part Common | drumPitchBendLower | blob `6915` | Part1-relative `+207` | Editor v5.6 |
| Part Common | drumDetuneHz | blob `6917` | Part1-relative `+209` | Editor v5.6 |
| Part Common | drumNoteShift | blob `6919` | Part1-relative `+211` | Editor v5.6 |
| Part Common | drumPartElemPanToggle | blob `6736` | Part1-relative `+28` | Editor v5.6 |
| Part Common | drumPartArpPlayOnly | blob `6802` | Part1-relative `+94` | Editor v5.6 |
| Part Common | drumPartMainCategory | blob `6815` | Part1-relative `+107` | Editor v5.6 |
| Part Common | drumPartVelLimitLow | blob `6819` | Part1-relative `+111` | Editor v5.6 |
| Part Common | drumPartVelLimitHigh | blob `6821` | Part1-relative `+113` | Editor v5.6 |
| Part Common | drumPartNoteLimitLow | blob `6823` | Part1-relative `+115` | Editor v5.6 |
| Part Common | drumPartNoteLimitHigh | blob `6825` | Part1-relative `+117` | Editor v5.6 |
| Part Common | drumPartVelDepth | blob `6827` | Part1-relative `+119` | Editor v5.6 |
| Part Common | drumPartVelOffset | blob `6829` | Part1-relative `+121` | Editor v5.6 |
| Part Common | drumPartVolume | blob `6831` | Part1-relative `+123` | Editor v5.6 |
| Part Common | drumPartPan | blob `6833` | Part1-relative `+125` | Editor v5.6 |
| Part Common | drumPartReverbSend | blob `6835` | Part1-relative `+127` | Editor v5.6 |
| Part Common | drumPartVariationSend | blob `6837` | Part1-relative `+129` | Editor v5.6 |
| Part Common | drumPartDryLevel | blob `6839` | Part1-relative `+131` | Editor v5.6 |
| Part Common | drumPartOutput | blob `6847` | Part1-relative `+139` | Editor v5.6 |
| Part Common | drumPartFilterAegAttack | blob `6849` | Part1-relative `+141` | Editor v5.6 |
| Part Common | drumPartFilterAegDecay | blob `6851` | Part1-relative `+143` | Editor v5.6 |
| Part Common | drumPartFilterAegSustain | blob `6853` | Part1-relative `+145` | Editor v5.6 |
| Part Common | drumPartFilterAegRelease | blob `6855` | Part1-relative `+147` | Editor v5.6 |
| Part Common | drumPartControlGroup | blob `6903` | Part1-relative `+195` | Editor v5.6 |
| Part Common | drumPart2EqType | blob `6961` | Part1-relative `+253` | Editor v5.6 |
| Drum Key | drumKeySW | `KEY(n) = 12469 + (n-1)*68 + 0` | Key1 `12469` / rel `+0` | Editor v5.6 |
| Drum Key | drumKeyRcvNoteOff | `KEY(n) = 12469 + (n-1)*68 + 4` | Key1 `12473` / rel `+4` | Editor v5.6 |
| Drum Key | drumKeyAssignMode | `KEY(n) = 12469 + (n-1)*68 + 6` | Key1 `12475` / rel `+6` | Editor v5.6 |
| Drum Key | drumKeyGroup | `KEY(n) = 12469 + (n-1)*68 + 8` | Key1 `12477` / rel `+8` | Editor v5.6 |
| Drum Key | drumKeyWaveformNumber | `KEY(n) = 12469 + (n-1)*68 + 10` | Key1 `12479` / rel `+10` | Editor v5.6 |
| Drum Key | drumKeyPan | `KEY(n) = 12469 + (n-1)*68 + 12` | Key1 `12481` / rel `+12` | Editor v5.6 |
| Drum Key | drumKeyRandomPan | `KEY(n) = 12469 + (n-1)*68 + 14` | Key1 `12483` / rel `+14` | Editor v5.6 |
| Drum Key | drumKeyAlternatePan | `KEY(n) = 12469 + (n-1)*68 + 16` | Key1 `12485` / rel `+16` | Editor v5.6 |
| Drum Key | drumKeyConnect | `KEY(n) = 12469 + (n-1)*68 + 22` | Key1 `12491` / rel `+22` | Editor v5.6 |
| Drum Key | drumKeyLevel | `KEY(n) = 12469 + (n-1)*68 + 26` | Key1 `12495` / rel `+26` | Editor v5.6 |
| Drum Key | drumKeyLevelVel | `KEY(n) = 12469 + (n-1)*68 + 28` | Key1 `12497` / rel `+28` | Editor v5.6 |
| Drum Key | drumKeyTimeAttack | `KEY(n) = 12469 + (n-1)*68 + 30` | Key1 `12499` / rel `+30` | Editor v5.6 |
| Drum Key | drumKeyTimeDecay1 | `KEY(n) = 12469 + (n-1)*68 + 32` | Key1 `12501` / rel `+32` | Editor v5.6 |
| Drum Key | drumKeyTimeDecay2 | `KEY(n) = 12469 + (n-1)*68 + 34` | Key1 `12503` / rel `+34` | Editor v5.6 |
| Drum Key | drumKeyLevelDecay1 | `KEY(n) = 12469 + (n-1)*68 + 36` | Key1 `12505` / rel `+36` | Editor v5.6 |
| Drum Key | drumKeyCoarse | `KEY(n) = 12469 + (n-1)*68 + 38` | Key1 `12507` / rel `+38` | Editor v5.6 |
| Drum Key | drumKeyFine | `KEY(n) = 12469 + (n-1)*68 + 40` | Key1 `12509` / rel `+40` | Editor v5.6 |
| Drum Key | drumKeyPitchVel | `KEY(n) = 12469 + (n-1)*68 + 42` | Key1 `12511` / rel `+42` | Editor v5.6 |
| Drum Key | drumKeyFilterCutoff | `KEY(n) = 12469 + (n-1)*68 + 44` | Key1 `12513` / rel `+44` | Editor v5.6 |
| Drum Key | drumKeyFilterCutoffVel | `KEY(n) = 12469 + (n-1)*68 + 46` | Key1 `12515` / rel `+46` | Editor v5.6 |
| Drum Key | drumKeyFilterResonance | `KEY(n) = 12469 + (n-1)*68 + 48` | Key1 `12517` / rel `+48` | Editor v5.6 |
| Drum Key | drumKeyHpfCutoff | `KEY(n) = 12469 + (n-1)*68 + 50` | Key1 `12519` / rel `+50` | Editor v5.6 |
| Drum Key | drumKeyEqType | `KEY(n) = 12469 + (n-1)*68 + 52` | Key1 `12521` / rel `+52` | Editor v5.6 |
| Drum Key | drumKeyEqLowFreq | `KEY(n) = 12469 + (n-1)*68 + 56` | Key1 `12525` / rel `+56` | Editor v5.6 |
| Drum Key | drumKeyEqLowGain | `KEY(n) = 12469 + (n-1)*68 + 58` | Key1 `12527` / rel `+58` | Editor v5.6 |
| Drum Key | drumKeyEqHiFreq | `KEY(n) = 12469 + (n-1)*68 + 60` | Key1 `12529` / rel `+60` | Editor v5.6 |
| Drum Key | drumKeyEqHiGain | `KEY(n) = 12469 + (n-1)*68 + 62` | Key1 `12531` / rel `+62` | Editor v5.6 |

---

## 10. Portamento cross-generation map

| Parameter | Legacy source | M-gen source | Y2L target | Encoding | Status |
| --- | --- | --- | --- | --- | --- |
| Performance Portamento Switch | `30 40 00 +0x3A` | `06 00 01 00 +0x00` | Common rel `+29` | 0/1 | verified |
| Performance Portamento Time | `30 40 00 +0x39` | `06 00 02 00 +0x20` | Common rel `+94` | mapped | verified |
| Part Portamento Switch | `31 0p 00 +0x31` | `1p 00 01 00 +0x0A` | Part rel `+39` | 0/1 | verified |
| Part Portamento Time | `31 0p 00 +0x32` | `1p 00 03 00 +0x08` | Part rel `+220` | mapped | verified |
| Part Portamento Mode | `31 0p 00 +0x33` | `1p 00 03 00 +0x0A` | Part rel `+222` | mapped enum | verified |

**Correction:** Common `+41` is Assignable Switch, **not Portamento**.

---

## 11. Arpeggio slot source map

| Slot | Legacy number | M-gen number | M-gen extra | Decoder |
| --- | --- | --- | --- | --- |
| Slot 1 | `31 6p 00 +0x45` | `1p 00 06 00 +0x44` | `1p 00 06 00 +0x54` | bank decoder below |
| Slot 2 | `31 6p 00 +0x48` | `1p 00 06 00 +0x46` | `1p 00 06 00 +0x56` | bank decoder below |
| Slot 3 | `31 6p 00 +0x4B` | `1p 00 06 00 +0x48` | `1p 00 06 00 +0x58` | bank decoder below |
| Slot 4 | `31 6p 00 +0x4E` | `1p 00 06 00 +0x4A` | `1p 00 06 00 +0x5A` | bank decoder below |
| Slot 5 | `31 6p 00 +0x51` | `1p 00 06 00 +0x4C` | `1p 00 06 00 +0x5C` | bank decoder below |
| Slot 6 | `31 6p 00 +0x54` | `1p 00 06 00 +0x4E` | `1p 00 06 00 +0x5E` | bank decoder below |
| Slot 7 | `31 6p 00 +0x57` | `1p 00 06 00 +0x50` | `1p 00 06 00 +0x60` | bank decoder below |
| Slot 8 | `31 6p 00 +0x5A` | `1p 00 06 00 +0x52` | `1p 00 06 00 +0x62` | bank decoder below |

Legacy raw-number banks:

```text
0                 Off
1..10239          Preset
10240..10495      User 1..256
10496..12543      Library 1..8, 256 each
```

M-generation decoder:

```text
0                 Off
1..10922          Preset
10923..12031      documented reserved gap
12032..12287      User 1..256
12288..16127      Library 1..15
16128..16382      Library 16, 1..255
16383 + extra=0   Library 16, 256
16383 + extra>0   Library 17+ extended banks
```

---

## 12. Modern EPFM container facts

### Performance ID

```text
bank = index // 128
slot = index % 128
ID   = 0x00400000 | (bank << 8) | slot
```

| Index | ID |
| ---: | ---: |
| 0 | `0x00400000` |
| 127 | `0x0040007F` |
| 128 | `0x00400100` |
| 255 | `0x0040017F` |
| 256 | `0x00400200` |
| 383 | `0x0040027F` |
| 384 | `0x00400300` |
| 512 | `0x00400400` |
| 639 | `0x0040047F` |

Old `rec[11]=index&0xff` and linear `0x00400000+index` logic is superseded.

### Tail

After the first NUL terminator in the modern EPFM name area, tail length must satisfy `tail_len % 4 == 0`. A final 1–3-byte remainder may be trimmed only if every trimmed byte is `00`; otherwise export must fail closed.

---

## 13. What this Reference does *not* claim

- A target coordinate extracted from the current Editor/serializer does **not** by itself prove the corresponding Soundmondo source coordinate.
- A Yamaha-documented source coordinate does **not** by itself prove the Y2L encoding.
- File-absolute offsets from controlled tests are evidence coordinates, not production constants.
- Fields marked only as current implementation/mapped target should be kept distinct from `ESP_VERIFIED` rows.

When a new controlled test identifies a source or target byte, add it here as a new row rather than filling a gap by analogy.
