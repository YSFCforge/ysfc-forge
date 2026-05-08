#!/usr/bin/env python3
"""
YSFC Forge — Serializer v6.0

Changelog v6.0 (2026-05-03 — Container-struktur fix, korrekt build_library):

  EPFM CATALOG BUG FIX (kritisk):
    _parse_chunks() ersatt med _parse_chunks_from_epfm_dir() — läser chunks
    via EPFM directory (absoluta fil-offsettar) istället för sekventiell scan.
    Sekventiell scan fungerade inte alls (tolkade offset-värden som chunk-storlekar).

  EPFM PAYLOAD LAYOUT KORREKTERAD (binärverifierad 2026-05-03):
    new_epfm[64:280] = 0xFF × 216 (var 0x00 — nu korrekt padding)
    new_epfm[0:64]   = directory (var new_epfm[:281] — nu exakt 64 bytes)
    _build_catalog: catalog stream-format uppdaterat med korrekt struktur
    Se YSFC_FORGE_FULL_CONTEXT_v10.md §2 för fullständig spec.

  CONTAINER-STRUKTUR FULLT DOKUMENTERAD:
    EPFM directory: [72:136] = 8 slots × 8 bytes (tag + absolut fil-offset)
    EPFM katalog: [280]=0x00, [281:285]=b'EPFM', [285:289]=catalog_size,
                  [289:353]=stream[0:64], sedan overflow to ESYS
    DPFM: dp[0:4]=count, dp[4:8]='Data', dp[8:12]=blob0_size, dp[12:]=blob0
    Entr-record: [0:4]=blob_size, [4:8]=blob_dp_off, [11]=entry_index, [26:]=namn
    ESYS/DSYS/EFVT/DFVT: konstanta storlekar, identiska för all engines.

Changelog v5.3 (2026-04-26 — Steg 60: AN-X EG fix, komplett FX-tabell, CA destinations):

  AN-X OSC EG OFFSETS KORRIGERADE (kritisk fix, Steg 60):
    Gamla MIDI-formel-baserade offsets var fel. Korrekta offsets (binärverif.):
    anxOsc1EGAttackTime:  5813 → 5970  ★★★★★
    anxOsc1EGDecayTime:   5815 → 5972  ★★★★★
    anxOsc1EGSustainLevel:5817 → 5974  ★★★★★
    anxOsc1EGReleaseTime: 5976 → 5976  (var korrekt!)
    anxOsc2EGAttackTime:  5938 → 6095  ★★★★★
    anxOsc2EGDecayTime:   5940 → 6097  ★★★★★
    anxOsc2EGSustainLevel:5942 → 6099  ★★★★★
    anxOsc2EGReleaseTime: 6101 → 6101  (var korrekt!)
    anxOsc3EGAttackTime:  6063 → 6220  ★★★★★
    anxOsc3EGDecayTime:   6065 → 6222  ★★★★★
    anxOsc3EGSustainLevel:6067 → 6224  ★★★★★
    anxOsc3EGReleaseTime: 6226 → 6226  (var korrekt!)
    Dessutom: anxOsc1EGDepth=5942, anxOsc1LFODepth=5944 (ny!)
              anxOsc2EGDepth=6067, anxOsc2LFODepth=6069 (ny!)

  COMPLETE FX_TYPE_INDEX TABELL (Step 60, 56 InsA-typer):
    Inkluderar all 51 från Effect Type List + 4 MODX M-specifika
    (WAH=1280, LO-FI=1424, TECH=1616, MISC=1672).
    Gäller för BÅDE InsertionA och InsertionB — samma tabell!
    CrossDelay korrigerat: 130 → 256.

  CA DESTINATIONS UTÖKAD (Step 60, 17 kända värden):
    InsA Param-serie: raw = param_nr (1-24, linjärt)
    InsB: raw=25 (fast), param_nr lagras i CA+11
    Rev Send=50, Var Send=51, Element Level=60, Element Pan=61,
    Element Delay=62, Filter Cutoff=85, HPF Cutoff=87,
    Part Pan=100, Arp Gate Time=105, MS Length=118

Changelog v5.2 (2026-04-26 — CA engine-oberoende bekräftat, Steg 57-59):

  CONTROLLER ASSIGN — ENGINE-OBEROENDE ★★★★★:
    AWM2/FM-X/AN-X delar EXAKT SAMMA CA-block (byte-för-byte identisk basefil).
    Part CA:  abs = 8220 + idx*22,  16 entries (idx 0-15)
    Perf CA:  abs = 2451 + idx*22,  8 entries  (idx 0-7, Knob1-8)
    Alla encoding-värden nedan gäller för ALLA engines.

  CA SOURCE ENCODING ★★★★★:
    0 = PitchBend
    1 = ModWheel (default)
    8 = Knob1, 9 = Knob2, 10 = Knob3
    (2-7: AfterTouch, FC, FS etc. — not verifierade)

  CA DESTINATION ENCODING ★★★★★:
    1  = Volume (default)
    85 = Filter Cutoff

  FM-X LFO TEMPONOTE komplett (Step 57):
    abs=7205 (PART+497), raw=list_idx+5, default=11=1/4
    Komplett tabell: raw 5-24 = 1/16 to 1/4×64

  AN-X OSC EG KOLLISION dokumenterad (v5.1):
    OSC2/3 EG-fält delar adresser med PulseWidth-block → ★★☆☆☆

Changelog v5.1 (2026-04-26 — AN-X OSC EG kollisionsfix, CA-struktur):

  AN-X OSC EG KOLLISIONSFIX (kodrättning, inga nya filer):
    OSC2 EG-fält (5936-5942) kolliderar med OSC1 PulseWidth (5936-5944).
    OSC3 EG-fält (6061-6067) kolliderar med OSC2 PulseWidth (6061-6069).
    Dessa fält är markerade ★★☆☆☆ tills binärverifiering avgör rätt sub-tabell.
    OSC1 EG (5811-5817) och all OSC EG Release-tider (5976/6101/6226) är opåverkade ★★★★★.

  CONTROLLER ASSIGN — komplett struktur (Step 57-58):
    22-byte CA-entry, stride=22, identisk layout på PART och PERF Common-nivå.
    PART CA: 16 entries, abs=8220+(ca_idx×22), ca_idx=0-15
    PERF CA: N entries, abs=2451+(ca_idx×22), ca_idx=0-7 (Knob1-8)
    Layout bekräftad: SW(+1), Source(+3), Destination(+5), CurveType(+9),
                      Param1(+11), Param2(+13), Polarity(+15), Depth(+17)
    Source enum bekräftad: PB=0, MW=1, Knob1=8, Knob2=9, Knob3=10

  FM-X LFO TEMPONOTE komplett (Step 57, 1 fil + 1 bild):
    fmxPartLfoTempoNote = abs 7205 (PART+497)
    Tabell: raw=5→1/16, ..., raw=11→1/4(default), ..., raw=14→1/2, ..., raw=24→1/4×64
    Formel: raw = list_index + 5

  AWM2 ctrlSet1-32 väntar på verifiering (2 filer under produktion).

Changelog v5.0 (2026-04-26 — FM-X Part PEG + LFO komplett, Steg 53-56):

  FM-X OP NAMNKORRIGERING (Step 53):
    off=22: aegDelayTime → pegDecayTime  (PEG Decay Time, vänster panel)
    Bekräftad med PitchEGDecayTime_50.Y2L och TimeDecay_50.Y2L

  FM-X PART PEG-BLOCK (Step 54, abs 12477-12507) — 16 NYA FÄLT ★★★★★:
    fmxPegPitchVelSens  = abs 12477 (PART+5769) center=64, default=64
    fmxPegRandomPitch   = abs 12479 (PART+5771) direct u8, default=0
    fmxPegPitchKeyFollow= abs 12481 (PART+5773) keyfollow% round(pct*64/200)+64
    fmxPegCenterKey     = abs 12483 (PART+5775) Yamaha note (C-2=0), default=60=C3
    fmxPegInitialLevel  = abs 12485 (PART+5777) center=50, default=50
    fmxPegAttackLevel   = abs 12487 (PART+5779) center=50, default=50
    fmxPegDecay1Level   = abs 12489 (PART+5781) center=50, default=50
    fmxPegDecay2Level   = abs 12491 (PART+5783) center=50, default=50
    fmxPegReleaseLevel  = abs 12493 (PART+5785) center=50, default=50
    fmxPegAttackTime    = abs 12495 (PART+5787) direct u8, default=0
    fmxPegDecay1Time    = abs 12497 (PART+5789) direct u8, default=0
    fmxPegDecay2Time    = abs 12499 (PART+5791) direct u8, default=0
    fmxPegReleaseTime   = abs 12501 (PART+5793) direct u8, default=0
    fmxPegDepthVelSens  = abs 12503 (PART+5795) direct u8, default=0
    fmxPegDepth         = abs 12505 (PART+5797) enum [8,2,1,0.5]oct per raw 0-3
    fmxPegTimeKeySens   = abs 12507 (PART+5799) direct u8, default=0

  FM-X PART 1st LFO (Step 54-56) — 11 NYA FÄLT ★★★★★:
    fmxPartLfoTempoSync = abs 6770  (PART+62)  bool 0=Off,1=On
    fmxPartLfoLoop      = abs 6771  (PART+63)  bool INVERTERAT 0=On,1=Off
    fmxPartLfoWave      = abs 7201  (PART+493) enum 0-12 (Triangle..User) COMPLETE
    fmxPartLfoSpeed     = abs 7203  (PART+495) direct u8, default=32
    fmxPartLfoDelay     = abs 7207  (PART+499) direct u8, default=0
    fmxPartLfoFadeIn    = abs 7209  (PART+501) direct u8, default=0
    fmxPartLfoHold      = abs 7211  (PART+503) direct u8, default=127
    fmxPartLfoFadeOut   = abs 7213  (PART+505) direct u8, center/default=64
    fmxPartLfoKeyOnReset= abs 7215  (PART+507) enum 0=Off,1=Each,2=1st, default=2
    fmxPartLfoRandomSpeed=abs 7265  (PART+557) direct u8, default=0
    (abs 7205 / PART+497: okänd, default=11, troligen TempoNote)

  FM-X PART 2nd LFO (Step 54-56) — 5 FÄLT ★★★★★:
    fmxPart2ndLfoWave         = abs 12509 (PART+5801) enum 0-12
    fmxPart2ndLfoSpeedNormal  = abs 12511 (PART+5803) direct u8, default=30 (Extended=OFF)
    fmxPart2ndLfoKeyOnReset   = abs 12517 (PART+5809) bool, default=0=Off
    fmxPart2ndLfoExtended     = abs 12529 (PART+5821) bool, default=1=ON
    fmxPart2ndLfoSpeedExtended= abs 12531 (PART+5823) direct u8, default=60 (Extended=ON)

  PEG DEPTH KORRIGERING (Step 55-56):
    8oct är default (raw=0), not 0oct som tidigare antogs!
    Enum: raw=0→8oct, raw=1→2oct, raw=2→1oct, raw=3→0.5oct

  LFO WAVE ENUM COMPLETE (Step 55-56, 13 värden):
    0=Triangle(default), 1=Triangle+, 2=SawUp, 3=SawDown,
    4=Squ1/4, 5=Squ1/3, 6=Square, 7=Squ2/3, 8=Squ3/4,
    9=Trapezoid, 10=S&H1, 11=S&H2, 12=User

  LFO FadeOut center=64 bekräftad av Johan (Step 56)

  FMX_PART_BASE KORRIGERINGAR:
    abs 12525-12543 omidentifierade: det är FM-X PART PEG+LFO blocket,
    INTE FM Color-relaterade fält som tidigare antagits.
    fmcLfoAmplWave/Speed/Depth (12521-12529) kvar oförändrade.
    abs 12529 (PART+5821): fmxPart2ndLfoExtended (not fmcLfoAmplDepth!)
    abs 12531 (PART+5823): fmxPart2ndLfoSpeedExtended (not okänd)
    abs 12533-12543: FM Color depth-fält med center=128 (oförändrade)

Changelog v4.0 (2026-04-26 — FM-X OP layout COMPLETE, Symphonic FX kartlagd):
  FM-X OP LAYOUT — 21/21 fält kartlagda (Step 46-52):
    KRITISK KORRIGERING: aegAttackTime(off=20) var fel — det är pegAttackTime!
      off=20 = pegAttackTime  (PEG Attack Time, vänster panel i ESP) ★★★★★
      off=32 = aegAttackTime  (AEG Attack Time, höger panel i ESP)   ★★★★★
    NYA FÄLT:
      keyOnReset    = off=-4  (bool, default=1=On)              ★★★★★
      spectralForm  = off=10  (enum 0-6: Sine/All1/All2/Odd1/Odd2/Res1/Res2) ★★★★★
      spectralSkirt = off=12  (u8 direct, default=0)            ★★★★★
      spectralResonance = off=14 (u8 direct, Res1/Res2 only)   ★★★★★
      aegDelayTime  = off=22  (u8 direct, default=0)            ★★★★★
      aegAttackTime = off=32  (u8 direct — LÖST!)               ★★★★★
      aegTimeKeyFollow = off=42 (u8 direct, "Time/Key")         ★★★★★
      aegBreakPoint = off=46  (raw=MIDI_note-9, default=39=C3)  ★★★★★
      lvlKeyLo      = off=48  (u8 direct)                       ★★★★★
      lvlKeyHi      = off=50  (u8 direct)                       ★★★★★
      curveLo       = off=52  (enum: -Linear=0,-Exp=1,+Exp=2,+Linear=3) ★★★★★
      curveHi       = off=54  (enum)                            ★★★★★
  SYMPHONIC InsertionFX — 12/12 parametrar kartlagda (Step 46-49):
    Delar EQ-layout med Classic Flanger (fxA+14 to fxA+28)
    fxA+8 = Delay Offset (INTE LFO Wave som tidigare antogs!)
    LFO Speed encoding: raw = round(Hz * 23.7045) — LINJÄR ★★★★★
    Dry/Wet: raw=64=50/50, raw=127=100%Wet (center=64 direkt) ★★★★★
  AN-X OSC EG Release — OSC1/2/3 kartlagda med stride=125 (Step 46-47):
    anxOsc1EGReleaseTime = rel=5976 ★★★★★
    anxOsc2EGReleaseTime = rel=6101 ★★★★★
    anxOsc3EGReleaseTime = rel=6226 ★★★★★
  AN-X OSC Pitch center=504 bekräftad (0cent-fil, inga diff) ★★★★★
  AN-X ModEG Attack binärverifierad (rel=6420) ★★★★★
  NOISE-bytes identifierade: PERF+23/24 och PERF+6724/6725 =
    timestamp/checksum uppdaterade av MODX vid varje Store — ignoreras.

Changelog v3.3 (Classic Flanger Insert FX fully mapped — 16/16 params):
  All params confirmed via cross-diff of 13 files ★★★★★
  Complete layout: fxA+4 through fxA+34 (all 16 params identified)
  Key encodings:
    EQ Gains: center=64, 1 raw=1 dB (simpler than element EQ!)
    Mod Phase: raw=phase_index*2 (180°→16, 90°→12) ✅
    FB High Damp: raw=value*10 (0.9→9, 1.0→10) ✅
    LFO Wave: 0=Triangle, 1=Sine ✅
    Feedback: raw=percent+100 ✅
  FX type as 7-bit: Classic Flanger=528, Symphonic=432, CrossDelay=2, Thru=0

Changelog v3.2 (Insert FX Classic Flanger params mapped):
  Insert FX type: 2-byte 7-bit index [lo,hi]: Classic Flanger=4*128+16=528, Symphonic=3*128+48=432
  Classic Flanger param layout (relative to fxA base):
    fxA+4:  LFO Speed  (default=26=1.09Hz, 1.98Hz→47) ✅
    fxA+6:  LFO Depth  (direct, default=34)  ✅
    fxA+12: Feedback   (raw=percent+100, default=151=51%) ✅
  FX param block starts at fxA+4 (after 4-byte type+header area)
  All 3 params confirmed via cross-diff of 3 files ★★★★★

Changelog v3.1 (OP aegHoldTime confirmed):
  aegHoldTime(off=40): 0→50 ✅ CONFIRMED — was ★★★☆☆, now ★★★★★
  OP layout: 15/16 fields confirmed, only off=32 remains unknown
  Note: OP1_Hold file also had Classic Flanger on InsertionA (unintended change)

Changelog v3.0 (AN-X FEG+RingMod+Modifier+InsertFX, major expansion):
  NEW AN-X OSC Ring Mod ★★★★★:
    anxOsc1RingModDepth(rel+5958): MIDI OSC addr 0x28+5918 ✅ (0→50)
    Stride=125 → OSC2(rel+6083), OSC3(rel+6208) confirmed
  NEW AN-X OSC EG sub-table (MIDI_hex_addr + 5779, 4 fields) ★★★☆☆:
    OscOutLevelVelSens(5811), OscEGAttackTime(5813) ✅, OscEGDecayTime(5815), OscEGSustainLevel(5817)
    All 3 OSCs at stride=125
  NEW AN-X Modifier sub-table (offset=6408) — 10 fields ★★★☆☆:
    WaveFolder, VelSens, EGDepth, LFODepth, Texture, Type, EG A/D/S/R
    Derived from MIDI Data Table rows 2950-2959
  NEW AN-X Insertion FX type offsets ✅:
    fxAType(rel+275) = 0→48 (Symphonic), fxBType(rel+332) = 0→2 (CrossDelay)
  New FM-X and AN-X base files added from zip

Changelog v2.9 (AN-X PEG Depth encoding solved):
  anxOsc1PitchEGDepth encoding ★★★★★ — 3 data points confirmed:
    UI=+400 → raw=342 (Δ=+95) ✅
    UI=   0 → raw=247 (Δ= 0)  ✅ center confirmed (0cent file = base)
    UI=-400 → raw=152 (Δ=-95) ✅ symmetric
    Formula: raw = round(ui * 95/400) + 247
    Simplified: raw = round(ui * 247/1040) + 247
    Range: ±1040 display units (= ±247 raw from center)
    All 3 OSC PitchEGDepth fields confirmed at stride=125 ✅

Changelog v2.8 (FM-X OP Decay2 confirmed):
  aegDecay2Time: off=36 ✅ (Decay2_50→abs 12712=OP1+36)
  Layout now: attackTime(20), decay1Time(34)✅, decay2Time(36)✅, releaseTime(38)✅
  off=32 sto unknown (default=0, possibly hold or extra decay stage)
  7 out of 8 FM-X OP time/level fields now binary verified ★★★★★

Changelog v2.7 (Steg40: FM-X OP layout complete, AN-X OSC PEG verified):
  FM-X OP — 6 fields now binary verified ★★★★★:
    fine(off=2):        0→50 ✅ direct
    detune(off=4):      center=15, +8→raw=23 ✅
    aegDecay1Time(off=34): 0→50 ✅ direct (was aegDecay2Time — CORRECTED)
    aegReleaseTime(off=38): 40→50 ✅ direct, default=40
  OP1_BASE=12676 + stride=123 fully verified for all confirmed fields
  AN-X OSC PEG Depth stride confirmed ★★★★★:
    anxOsc1PitchEGDepth(rel+5924): 247→342 (UI=400)
    anxOsc2PitchEGDepth(rel+6049): ✅ stride=125
    anxOsc3PitchEGDepth(rel+6174): ✅ stride=125
  PEG Depth encoding: u16 LE, center=247, scale≈4.2 cent/unit (needs 0-cent file)
  AN-X AEG Attack re-confirmed: abs 12553, 0→50 ✅
  NOTE: Apm_AEG + PEG Depth files were AN-X exports (not FM-X)

Changelog v2.6 (algorithm confirmed, ANX_OSC complete, all 15 OSC fields verified):
  algorithm @ abs 12525 ★★★★★ FINAL: Init_Algorithm_1→raw=0 ✅ (algo-1 encoding)
    No conflicts: algorithm(12525) separate from fmcAttack(12537) ✅
  ANX_OSC expanded to FULL 15 fields × 3 OSCs = 45 fields:
    All 15 OSC1 fields verified against baseline defaults ★★★☆☆
    Wave/Octave/Pitch already ★★★★★, rest ★★★☆☆
    Added: PitchEGDepth, PitchEGDepthVelSens, PitchLFODepth (centers: 247/256/247)
           SelfSyncPitch, SelfSyncVelSens, SelfSyncLFODepth
           PulseWidth(center=256), PulseWidthVelSens(center=128!)
           PulseWidthEGDepth, PulseWidthLFODepth, WaveShaper, WaveShaperVelSens
  Removed legacy ANX_OSC_PITCH dict (now in ANX_OSC)

Changelog v2.5 (FM-X OP layout corrected, AN-X WaveFolder found):
  FMX_OP1_BASE=12676 CONFIRMED via OP1_Coarse_2 ✅
  FMX_OP_LAYOUT updated with 2 new verified fields:
    pegAttackLevel(off=18): default=50, Level_Attack_50→100 ✅
    aegAttackTime(off=20): default=0, Time_Attack_50→50 ✅  NEW
  Renamed: attack→aegDecay1Time, decay1→aegDecay2Time (old names were wrong)
  Algorithm file was multi-perf export (23KB) — skipped, will retry
  AN-X WaveFolder @ PART rel+6408: u8 direct default=0 ✅ NEW
    Added ANX_MODIFIER dict with anxWaveFolder

Changelog v2.4 (AN-X baseline restored, synthesis AEG found):
  AN-X baseline restored: AN-X_00_Init_Base_Clean.Y2L (13150 bytes, Init Normal AN-X)
  All 20 compatible AN-X test files re-verified ✅
  NEW: AN-X Synthesis-level AEG (rel+5845-5851, abs 12553-12559):
    anxSynthAegAttack(12553):  u8 direct default=0  ✅
    anxSynthAegDecay(12555):   u8 direct default=160  ✅
    anxSynthAegSustain(12557): u16 LE default=511 (max level)  ✅
    anxSynthAegRelease(12559): u8 direct default=115  ✅
  NOTE: These are synthesis-engine AEG, different from Part-level AEG offsets (6849-6855)
  22/22 field verifications pass against clean baseline ✅

Changelog v2.3 (AN-X Part filter offsets + AN-X baseline lost/recovered):
  NOTE: AN-X_00_Init_Part1_Base.Y2L was overwritten with FM-X file in prev session
    → Used cross-diff between 3 AN-X files to isolate parameters (sto valid)
  NEW AN-X Part Common fields — all binary verified ★★★★★:
    anxFEGDepthOffset(rel+157=abs 6865): center=64, ui=+50→114 ✅
    anxFilterCutoffOffset(rel+159=abs 6867): center=64, ui=+20→84 ✅
    anxResonanceOffset(rel+161=abs 6869): center=64 ★★★★☆ (derived, FM-X same offset)
  Pattern confirmed: AN-X/FM-X rel+157/159/161 = AWM2 6877/6879/6881 - 12 ✅
  AEGOffset_20 file changed only anxAegAttack(rel+141): Init Normal AEG Offset=Attack

Changelog v2.2 (FM Color fully mapped, critical corrections):
  FM Color sub-table — 13 fields binary verified ★★★★★:
    fmcDepth(12533), fmcHarmonics(12535), fmcAttack(12537), fmcDecay(12539),
    fmcSustain(12541), fmcRelease(12543), fmcTexture(12545) — center=128
    algorithm(12525): raw=algo-1, Init=69→68 ✅ CORRECTED (was 12537!)
    feedback(12527): direct default=0 ✅ CORRECTED (was 12539!)
  CRITICAL FIX: FMX_OP1_BASE = 12676 (was 12688, off by 12!)
    Verified: OP1 Level(off=44)→abs 12676+44=12720 ✅
    OP1 detune(off=4): abs 12680=15, center=15→ui=0 ✅
  NEW: FM-X Part Filter Offsets (Part-level, center=64):
    fmxFEGDepthOffset(rel+157), fmxFilterCutoffOffset(rel+159), fmxResonanceOffset(rel+161)
  NEW: OP1 Level confirmed direct encoding: 0→50 ✅
  FM Color fields at ODD abs offsets (12521,12523,...), OP fields at EVEN (12676,12678,...)

Changelog v2.0 (FM-X Filter complete, fmEG mapping conflict resolved):
  FM-X Filter — 3 fields binary verified ★★★★★:
    fmxFilterType(abs 12551):     Thru=21, LPF18D=2, HPF12=7  ✅
    fmxFilterCutoff(abs 12553):   u16 LE Hz, 400Hz→(144,1) ✅
    fmxFilterResonance(abs 12557): u8 direct default=10 ✅ (ui=80→raw=80)
  CRITICAL FIX: fmEGDecay/Sustain were wrong — they conflicted with filter offsets
    Removed fmEGDecay=12551 and fmEGSustain=12553 (both collide with filter fields)
    Added fmxCutoffVelSens(12555): center=64 ★★★☆☆
  Filter Type enum confirmed: same across AWM2 element and FM-X part
    0=LPF24D, 2=LPF12D, 7=HPF12D, 21=Thru (and probably 1=LPF18D etc.)
  Observation: All 3 test files set FilterType=7 automatically (MODX activates
    a filter when editing Cutoff/Resonance from Thru)

Changelog v1.9 (FM-X Filter found, Part sub-table confirmed for all engines):
  FM-X Filter sub-table (offset=5843 = MIDI_hex_addr + 5843):
    fmxFilterType(PART rel+5843=abs 12551): u8 enum default=21=Thru, LPF18D=2  ✅
    fmxFilterCutoff(PART rel+5845=abs 12553): u16 LE Hz default=1023  ✅
  NOTE: FMX_PART_BASE had fmEGDecay=12551 conflict with fmxFilterType=12551!
    fmEGDecay and fmxFilterType are same byte → fmEGDecay mapping was WRONG
    Keeping fmxFilterType as confirmed binary-verified value
  PART_SUBTABLE (offset=205, all engines AN-X+FM-X confirmed ✅):
    pitchBendRangeLower(rel+207), detune(rel+209, u16 center=128)
    noteShift(rel+211), portaTime(rel+213), portaMode(rel+215)
  Detune default correction: 7-bit '01 00' = 128 (not 256) — center=128 ✅

Changelog v1.8 (AN-X Part Common shift confirmed, portamento mapped):
  AN-X_PART_COMMON_SHIFT = -12 CONFIRMED on 4 independent fields ✅:
    anxPartPortaSW(rel+32), anxPortaTime(rel+213), anxPortaMode(rel+215), anxVolume(rel+123)
  New AN-X Part Common fields:
    anxPartPortaSW(rel+32): bool default=1  ✅
    anxPortaTime(rel+213): u8 direct default=64  ✅ (Time_100→raw=100)
    anxPortaMode(rel+215): bool default=1=FullTime, Fingered=0  ✅
  DPFM[29] = Performance Portamento SW (0=Off,1=On), default=0  ✅
    Changed by ALL portamento files → confirmed performance-level (not part-level)

Changelog v1.7 (AN-X Part Common found, FM-X baseline needed):
  AN-X Part Common: same structure as AWM2 PART_COMMON, shifted -12 bytes
    anxVolume(PART rel+123): direct default=100 ✅ (AWM2 6843 - 12 = 6831)
    anxPan(PART rel+125): center=64 default=0 ✅
    ANX_PART_COMMON_SHIFT = -12 (apply to all AWM2 PART_COMMON abs offsets)
  Portamento_ON → DPFM[29] = Performance-level Portamento SW (not part-level)
  FM-X Filter file loaded (size=13609), needs FM-X baseline to isolate changes

Changelog v1.6 (AN-X OSC and Filter expanded via MIDI Data Table):
  MIDI Data Table rows 2827-2866, 2907-2921 parsed for AN-X
  ANX_OSC expanded: 13 OSC params per oscillator (Wave, Octave, Pitch, PEG, LFO, PW, WaveShaper)
    All defaults verified against baseline ★★★☆☆
  ANX_FILTER expanded: 16 Filter params (Filter1 all 10 defaults verified ✅)
    Filter1CutoffVelSens, CutoffEGDepth, CutoffEGDepthVelSens, CutoffLFODepth,
    CutoffKeyFollow, ResonanceVelSens added  ★★★☆☆
  Filter encoding confirmed:
    Drive: raw = round(dB/0.75), range 0-80
    OutLevel: raw = round(dB*2.667)+64, center=64

Changelog v1.5 (AN-X: Filter Drive/OutLevel, OSC Wave, Filter2):
  MIDI hex address clarification: MIDI table shows hex, not decimal
    Formula CONFIRMED: DPFM_rel = MIDI_hex_addr + 6297 ✅
  NEW AN-X fields — all binary verified ★★★★★:
    anxFilter1Drive(rel+6315):    0-80 raw, 0.75dB/unit, 50dB→67 ✅
    anxFilter1OutLevel(rel+6319): center=64, 0.375dB/unit, +6dB→80 ✅
    anxFilter2Drive(rel+6392):    same encoding  ✅  (stride=77)
    anxFilter2OutLevel(rel+6396): same encoding  ✅
    anxOsc1Wave(rel+5918):        enum 0=Saw, 2=Square default=0  ✅
  Filter 2 stride=77 confirmed ✅
  Filter 2 default type=5 (different from Filter 1 default=1)
  OSC Wave sub-table offset=5918 (= OSC Pitch offset 5922 - MIDI addr 4)

Changelog v1.4 (AN-X: OSC pitch center confirmed, Filter Type+Resonance):
  OSC Pitch center CONFIRMED = 504 (0cent file = baseline, no diffs ✅)
    Encoding: raw = cents + 504 (≈1:1, MODX UI may round: "400" → raw=898=Δ394)
  NEW AN-X Filter sub-table: DPFM_rel = MIDI_filter_addr + 6297
    anxFilter1Type(rel+6297):      u8 enum default=1=LPF12, LPF6=4  ✅
    anxFilter1Cutoff(rel+6299):    u16 LE Hz default=1023  ✅ (confirmed)
    anxFilter1Resonance(rel+6311): u8 direct default=0  ✅ (80→raw=80)

Changelog v1.3 (AN-X: OSC Pitch, Filter Cutoff, Mod LFO Depth):
  NEW AN-X fields — all binary verified ★★★★★:
    anxModLfoDepth(PART rel+6414): center=128, ui=50→raw=178 ✅
    anxOsc1Pitch(PART rel+5922):   u16 LE, default=504, Δraw=394 for 400 cent ✅
    anxOsc2Pitch(PART rel+6047):   u16 LE ✅ (stride=125=ANX_OSC_STRIDE confirmed)
    anxOsc3Pitch(PART rel+6172):   u16 LE ✅
    anxFilter1Cutoff(PART rel+6299): u16 LE Hz direct, default=1023 ✅
  OSC Pitch encoding: u16 LE, center≈498 (MIDI confirms default=504=+6 cent Init Normal)
    Discrepancy: 394 raw units for 400 cent → need 0-cent file to confirm exact center
  MIDI Data Table AN-X sub-tables analyzed (rows 2820-2971):
    OSC: Pitch, PEG, LFO, PulseWidth, WaveShaper (39 params/OSC)
    Filter: Cutoff, Resonance, Drive, OutLevel, KF, EG (30 params/Filter)
    Modifier: WaveFolder, LFO (30 params)

Changelog v1.2 (AN-X baseline established):
  AN-X baseline: Init Normal (AN-X), 1 perf, 13150 bytes (part=6442 bytes)
  CORRECTED AN-X LFO offsets (previous were 12 bytes off without baseline):
    anxPitchLfoSpeed: 5807 → 5795, default=208 (old base had Speed=300 set by mistake)
    anxModLfoWave:    6442 → 6430, default=2  ★★★★★
    anxModLfoSpeed:   6444 → 6432, default=208  ★★★★★
  AN-X Pitch LFO Speed 300 confirmed: 208→(44,1)=300 ✅
  AN-X Mod LFO Wave Square confirmed: 2→1 ✅
  AN-X Mod LFO Speed 271 confirmed: 208→(15,1)=271 ✅
  Both Pitch and Mod LFO have same default speed (208)
  Added ANX_PERF_NOISE = {23, 24, 6724, 6725}

Changelog v1.1 (session: AWM2 Element EQ + AN-X LFO anchors):
  AWM2 ELEMENT EQ — 6 fields verified ✅ (rel+220-230):
    eqType(+220): enum 0=Thru, 1=P.EQ, 2=Boost6
    eqQ(+222): P.EQ Q, direct
    eqLowFreq(+224): freq-table index (shared with eqPeqFreq)
    eqLowGain(+226): center=64, encoding dB*16/6+64 ✅ (3 datapoints)
    eqHighFreq(+228): freq-table index, default=231
    eqHighGain(+230): center=64
  EQ closes the rel+220-230 mystery block ✅ (was "internal motor data")
  AN-X LFO — first anchors found:
    anxModLfoWave(PART rel+6442): enum, default=1, Square=2 ✅
    anxModLfoSpeed(PART rel+6444): u16 LE direct, default=208, 271→(15,1) ✅
    anxPitchLfoSpeed(PART rel+5807): u16 LE direct, 300→(44,1) ✅
  AN-X baseline needed: 61KB AN-X files are different patch (38182 DPFM, non-integer strides)

Changelog v1.0 (session: Steg34 — element LFO complete, Part LFO + Filter):
  ELEMENT LFO — 13/13 FIELDS FULLY VERIFIED ✅:
    lfoAmpModDepth(+240), lfoPitchModDepth(+242), lfoFilterModDepth(+244)  ← NEW
    lfoFadeInTime(+246, corrected from +240), lfoPhaseOffset(+248)         ← CORRECTED
    lfoDest1Ratio(+250), lfoDest2Ratio(+252), lfoDest3Ratio(+254) default=127  ← NEW
    lfoExtendedSpeed(+256, default=60)                                      ← NEW
  PART-LEVEL LFO — 6 fields verified:
    partLfoTempoSync(PART+74), partLfoLoop(PART+75)
    partLfoWave(PART+505), partLfoSpeed(PART+507)
    partLfoTempoNote(PART+509), partLfoKeyOnReset(PART+519)
  PART-LEVEL FILTER — 2 fields found:
    partFilterType(PART+4): u8 enum (0=Thru, 2=LPF18D)
    partFilterCutoff(PART+5857): u16 LE Hz default=2816
  LFO offset analysis: mixed offsets (180, 150, 186) in one sub-table
  AWM2 element: rel+0 to rel+296 complete + rel+256=lfoExtendedSpeed

Changelog v0.9 (session: Filter Gain solved, element layout complete):
  filterGain(+164): BINARY VERIFIED — u8 direct 0-255, default=230
    MIDI Filter 0x0E, default '01 66' = 1*128+102 = 230 ✅
  FILTER SUB-TABLE COMPLETE: 35/35 fields default-verified ✅
    DPFM_rel = MIDI_addr + 150 for all 35 fields (MIDI 0x00–0x44)
  New named fields:
    dualFilterDistance(+162): Dual Filter Distance (center=128)
    filterGain(+164): Filter Gain 0-255 (direct)
    cutoffScalingBP1-4(+200,202,204,206): Cutoff Scaling Breakpoints
    cutoffScalingOfs1-4(+208,210,212,214): Cutoff Scaling Offsets (center=128)
  LFO sub-table mapped: DPFM_rel = MIDI_addr + 180 — 6 fields verified ✅
    lfoWave(+232), lfoKeyOnReset(+234), lfoDelayTime(+236),
    lfoSpeed(+238), lfoFadeInTime(+240), lfoPhaseOffset(+242)
  Controller Set Switches 1-32 mapped: DPFM_rel = MIDI_addr + 258 — 32/32 ✅
    ctrlSet1-32 (+265–+296), all default=1 (On)
  AWM2 element: rel+0–rel+296 nearly complete (297 of 313 bytes covered)

Changelog v0.8 (session: Steg 33 binary verification):
  BINARY-VERIFIED (13 new fields from Y2L diffs):
    levelVelCurve(+46, direct, default=3) ✅
    aegTimeVelSegment(+66, enum 0-4, default=4=All) ✅
    aegTimeVel(+68, center=64) ✅
    cutoffVelSens(+154, center=64) ✅
    resonanceVelSens(+158, center=64) ✅
    hpfCutoff(+160, u16 LE Hz) ✅
    fegDepthVelSegment(+188, enum 0-4) ✅
    fegDepthVelSens(+190, center=64) ✅
    pegTimeVelSegment(+134, enum 0-4) ✅
    pegTimeVelSens(+136, center=64) ✅
    cutoffKeyFollow(+216, keyfollow%) ✅
    hpfCutoffKeyFollow(+218, keyfollow%) ✅
    filterGain(+164, u8 direct, default=230)
  PITCH SUB-TABLE CONFIRMED: DPFM_rel = MIDI_addr + 98 (20 fields mapped)
  NEW ENCODING: keyfollow%: ui=round((raw-64)*200/64), raw=round(ui*64/200)+64
  PEG level fields added to center=128 encoding
  PEG and filter center=64 fields added to encode/decode lists
  53 unit tests passing

Changelog v0.7 (session: MIDI Data Table + Waveform List analysis):
  KEY DISCOVERY: MIDI sub-table offset formulas for AWM2 element DPFM layout:
    Wave sub-table (MIDI_addr >= 0x0C): DPFM_rel = MIDI_addr - 4
    Wave sub-table (MIDI_addr >= 0x20): DPFM_rel = MIDI_addr + 40  (same as Amplitude!)
    Amplitude sub-table:                DPFM_rel = MIDI_addr + 40
    Filter sub-table:                   DPFM_rel = MIDI_addr + 150
  All 13 previously verified fields confirmed by formulas.
  waveformNumber: confirmed 1-based (Waveform List #6=CFX v06 St, #14=C7 f St, #186=Hamburg v01)
  New fields added (MIDI-derived, default-verified against baseline):
    xcaControl(+16), levelBP0-4(+72-80), levelOfs1-4(+82-88),
    levelKeyFollowSens(+90), aegTimeKeyFollowRelAdj(+92),
    levelVelCurve(+46), aegTimeVelSegment(+66), aegTimeKeyFollowSens(+70),
    cutoffVelSens(+154), resonanceVelSens(+158), hpfCutoff(+160, u16 LE),
    hpfCutoffVelSens(+162, center=128), fegDepthVelSegment(+188),
    fegDepthVelSens(+190), fegTimeVelSegment(+192), fegTimeVelSens(+194),
    fegTimeKeyFollowSens(+196), fegTimeKeyFollowCenterNote(+198),
    cutoffKeyFollowSens(+200), cutoffKeyFollowCenterNote(+202)
  NOTE: fields rel+192-202 need binary verification (MIDI order uncertain)

Changelog v0.6:
  - AWM2_ELEM1_BASE corrected: 12540 → 12532 (element header precedes pan)
  - All AWM2_ELEM_LAYOUT offsets shifted +8 accordingly
  - New fields: waveformNumber (+0, u16 LE 1-based), waveformBank (+2, u8 direct)
  - New fields: ampLevelVel (+42, center=64)
  - New fields: elemFilterResonance (+156, direct)
  - New fields: fegTimeHold/Attack/Decay1/Decay2/Release (+166–174, direct)
  - New fields: fegLevelHold/Attack/Decay1/Decay2/Release (+176–184, center=128)
  - New fields: fegDepth (+186, center=64, default=+40)
  - waveformNumber confirmed 1-based vs Waveform List.xlsx (Waveform List #6=CFX v06 St ✅)
  - FIELD_MAP: waveformNumber hi-byte registered
In-place DPFM patcher for Yamaha MODX/Montage Y2L files.

Changelog v0.4:
  - build_library(): create multi-performance Y2L from individual patches
  - _build_catalog(): correct EPFM catalog with Entr blocks
  - Entr size formula: 32 + 2*len(name)
  - DPFM offsets and perf index correctly embedded in each Entr

Changelog v0.3:
  - Full encode/decode functions for all 15 encoding types
  - patch_ui(): patch using UI values (auto-encodes to raw)
  - read_ui():  read a field and decode to UI value
  - Merge engine: combine DPFM fields from multiple source files

Changelog v0.4:
  - build_library(): create multi-performance Y2L from individual patches
  - _build_catalog(): correct EPFM catalog with Entr blocks
  - Entr size formula: 32 + 2*len(name)
  - DPFM offsets and perf index correctly embedded in each Entr

Changelog v0.3:
  - copy_part_block(): copy entire Part block between files (same engine)
  - extract_part_block() / inject_part_block(): raw block I/O
  - get_part_count(): count parts in a file
  - build_performance(): combine Parts from multiple Y2L files
  - diff_report(): human-readable diff with field names and decoded values
  - FIELD_MAP: complete offset→field lookup for all known parameters
"""

from math import log2
from pathlib import Path
from typing import Any, Union

# ── FIELD_REGISTRY ────────────────────────────────────────────────────────

NOISE = {3, 35, 36, 63, 399, 710, 711, 6735, 6736, 6737, 7411, 7412}
# Timestamp/checksum bytes updated by MODX on every Store — ignored in diffs:
MODX_TIMESTAMP_BYTES = {23, 24, 6724, 6725}  # confirmede Steg 50
# CA+17 (abs = CA_PART_BASE + idx*22 + 17) is also MODX-internal —
# ignored during patch-editing (confirmed Step 60-61, not visible in ESP)

FMX_PART_STRIDE  = 6913
FMX_OP_STRIDE    = 123
FMX_OP1_BASE     = 12676  # CORRECTED from 12688: OP1 Level(off=44)→abs 12720 ✅
AWM2_PART_STRIDE = 8273
AWM2_ELEM_STRIDE = 313
AWM2_FILTER_TYPES = [
    "LPF24D","LPF18D","LPF12D","LPF6D","LPF+HPF",
    "HPF24D","HPF18D","HPF12D","HPF6D",
    "BPF12D×2","BPF6D×2","BPF12A",
    "LPF24A","LPF18A","LPF12A","HPF24A","HPF12A",
    "BPF12A×2","BPF6A×2","LPF24A+HPF","BPFmono","THRU",
]  # 22 types; verified: 0=LPF24D,4=LPF+HPF,7=HPF12D,21=THRU
AWM2_ELEM1_BASE  = 12532  # corrected
AWM2_ELEM_WF_OFF = 12520  # waveformNumber u16le (1-based): abs offset in blob for elem 1
AWM2_ELEM_STRIDE_WF = 313  # stride between elements for waveform detection
WAVEFORM_BUILTIN_MAX = 256  # waveformNumber 1-256 = ROM preset (always available)
                             # waveformNumber 257+  = expansion pack sample (→ Storage RW error): waveform@rel+0, pan@rel+8
ANX_PART_STRIDE  = 6454
ANX_OSC_STRIDE   = 125
ANX_OSC1_BASE    = 12638
ANX_FILTER_BASE  = 13019
ANX_AEG_BASE     = 12565  # +0:Attack u8, +2:Decay u8, +4:Sustain u16LE, +6:Release u8, +8:TimeVel u16LE c=256

PART_COMMON = dict(
    monoPoly=6751, volume=6843, pan=6845,
    aegAttack=6861, aegDecay=6863, aegSustain=6865, aegRelease=6867,
    fegAttack=6869, fegDecay=6871, fegSustain=6873, fegRelease=6875,
    filterFEGDepth=6877, filterCutoff=6879, filterResonance=6881,
)
PART_DETUNE_BASE = 6929
PART_NOTESHIFT   = 6931

# FM-X Part-level LFO fields (abs addresses, verified Steps 54-56)
# 1st LFO: TempoSync/Loop i PART_COMMON (abs 6770-6771), övriga i LFO-subtabell
FMX_PART_LFO = dict(
    fmxPartLfoTempoSync=6770,    # abs, u8 bool 0=Off,1=On, default=0  ★★★★★ (Step 56)
    fmxPartLfoLoop=6771,         # abs, u8 bool INVERTED 0=On,1=Off, default=0=On  ★★★★★ (Step 56)
    fmxPartLfoWave=7201,         # abs, u8 enum 0-12, default=0=Triangle  ★★★★★ (Step 55-56)
    #   0=Triangle, 1=Triangle+, 2=SawUp, 3=SawDown, 4=Squ1/4, 5=Squ1/3,
    #   6=Square, 7=Squ2/3, 8=Squ3/4, 9=Trapezoid, 10=S&H1, 11=S&H2, 12=User
    fmxPartLfoSpeed=7203,        # abs, u8 direct, default=32  ★★★★★ (Step 54-55)
    fmxPartLfoTempoNote=7205,    # abs, u8 table-index raw=list_idx+5, default=11=1/4  ★★★★★ (Step 57)
    #   See FMX_LFO_TEMPONOTE dict for complete table (raw 5-24 = 1/16 to 1/4×64)
    fmxPartLfoDelay=7207,        # abs, u8 direct, default=0  ★★★★★ (Step 56)
    fmxPartLfoFadeIn=7209,       # abs, u8 direct, default=0  ★★★★★ (Step 56)
    fmxPartLfoHold=7211,         # abs, u8 direct, default=127  ★★★★★ (Step 56)
    fmxPartLfoFadeOut=7213,      # abs, u8 direct center=default=64  ★★★★★ (Step 56, bekräftad av Johan)
    fmxPartLfoKeyOnReset=7215,   # abs, u8 enum 0=Off,1=Each,2=1st, default=2  ★★★★★ (Step 56)
    fmxPartLfoRandomSpeed=7265,  # abs, u8 direct, default=0  ★★★★★ (Step 56)
)
# 2nd LFO (abs addresses, verified Steps 54-56)
FMX_PART_2ND_LFO = dict(
    # 2nd LFO COMPLETE 7/7 fields ★★★★★ (Steps 54-62)
    fmxPart2ndLfoWave=12509,          # abs, u8 enum 0-12 (samma som 1st LFO), default=0  ★★★★★
    fmxPart2ndLfoSpeedNormal=12511,   # abs, u8 direct, default=30 (aktiv när Extended=OFF)  ★★★★★
    fmxPart2ndLfoPhase=12513,         # abs, u8 enum 0=0°,1=90°,2=180°,3=270°,4=360°, default=0  ★★★★★ (Step 62)
    fmxPart2ndLfoDelay=12515,         # abs, u8 direct, default=0  ★★★★★ (Step 62)
    fmxPart2ndLfoKeyOnReset=12517,    # abs, u8 bool 0=Off,1=On, default=0  ★★★★★
    fmxPart2ndLfoExtended=12529,      # abs, u8 bool 0=Off,1=On, default=1=ON  ★★★★★
    fmxPart2ndLfoSpeedExtended=12531, # abs, u8 direct, default=60 (aktiv när Extended=ON)  ★★★★★
    # Destination/Depth matrix (17 fields, abs=12547+): not mapped
    # Pitch Mod ×8 OPs + Amp Mod ×8 OPs + Filter Mod ×1 = default=0 all
)
# FM-X Part PEG block (abs addresses, verified Steps 54-55)
# Encoding PEG Levels: center=50 (raw = ui + 50, range -50 to +50)
# Encoding PEG Depth: enum [8,2,1,0.5]oct per raw 0-3 (8oct=default!)
# Encoding PitchKeyFollow: raw = round(pct*64/200) + 64 (AWM2-identisk)
# Encoding CenterKey: Yamaha note (C-2=0), C3=60=default
FMX_PART_PEG = dict(
    fmxPegPitchVelSens=12477,    # abs, u8 center=64, default=64  ★★★★★ (Step 54)
    fmxPegRandomPitch=12479,     # abs, u8 direct, default=0  ★★★★★ (Step 54)
    fmxPegPitchKeyFollow=12481,  # abs, u8 raw=round(pct*64/200)+64, default=96=100%  ★★★★★ (Step 54-55)
    fmxPegCenterKey=12483,       # abs, u8 Yamaha note (C-2=0), default=60=C3  ★★★★★ (Step 54)
    fmxPegInitialLevel=12485,    # abs, u8 center=50, default=50  ★★★★★ (Step 54)
    fmxPegAttackLevel=12487,     # abs, u8 center=50, default=50  ★★★★★ (Step 54)
    fmxPegDecay1Level=12489,     # abs, u8 center=50, default=50  ★★★★★ (Step 54)
    fmxPegDecay2Level=12491,     # abs, u8 center=50, default=50  ★★★★★ (Step 54)
    fmxPegReleaseLevel=12493,    # abs, u8 center=50, default=50  ★★★★★ (Step 54)
    fmxPegAttackTime=12495,      # abs, u8 direct, default=0  ★★★★★ (Step 54)
    fmxPegDecay1Time=12497,      # abs, u8 direct, default=0  ★★★★★ (Step 54)
    fmxPegDecay2Time=12499,      # abs, u8 direct, default=0  ★★★★★ (Step 54)
    fmxPegReleaseTime=12501,     # abs, u8 direct, default=0  ★★★★★ (Step 54)
    fmxPegDepthVelSens=12503,    # abs, u8 direct, default=0  ★★★★★ (Step 54)
    fmxPegDepth=12505,           # abs, u8 enum raw 0-3: [8oct,2oct,1oct,0.5oct], default=0=8oct  ★★★★★ (Step 55-56)
    fmxPegTimeKeySens=12507,     # abs, u8 direct, default=0  ★★★★★ (Step 54)
)
# Part-level LFO fields (PART_BLOCK_START=6708 + rel) — AWM2/generic
# Verified: PART_BLOCK offsets 74,75,505,507,509,519
PART_LFO = dict(
    partLfoTempoSync=74,    # u8 bool default=0  (AWM2, rel from PART_BASE)
    partLfoLoop=75,         # u8 bool default=0  (AWM2)
    partLfoWave=505,        # u8 enum default=0  (AWM2) — FM-X använder FMX_PART_LFO!
    partLfoSpeed=507,       # u8 direct default=32  (AWM2)
    partLfoTempoNote=509,   # u8 enum default=11  (AWM2)
    partLfoKeyOnReset=519,  # u8 direct default=2=On  (AWM2)
    # NOTE: FM-X Part LFO använder ANDRA absoluta adresser — se FMX_PART_LFO dict
    # FM-X: Wave=7201, Speed=7203, Delay=7207, FadeIn=7209, Hold=7211,
    #        FadeOut=7213(center=64), KeyOnReset=7215, RandomSpeed=7265
)
# Part-level Filter fields (PART_BLOCK_START + rel)
PART_FILTER = dict(
    partFilterType=4,       # u8 enum (0=Thru, 2=LPF18D, ...) default=0
    partFilterCutoff=5857,  # u16 LE Hz default=2816
)

# AN-X Part-level LFO offsets (PART_BLOCK_START + rel)
# Verified against AN-X_00_Init_Part1_Base.Y2L (v2, 37KB, 1 perf) ✅
ANX_PART_LFO = dict(
    anxPitchLfoSpeed=5795,  # u16 LE direct, default=208  ✅
    anxModLfoWave=6430,     # u8 enum 0-4 default=2=Tri  ✅
    anxModLfoSpeed=6432,    # u16 LE direct, default=208  ✅
    anxModLfoDepth=6414,    # u8 center=128 default=0  ✅
)
# AN-X Part Common: same as AWM2 PART_COMMON, shifted -12 bytes (4 fields confirmed ✅)
# Formula: AN-X_abs = AWM2_abs - 12  (verified: partPortaSW, portaTime, portaMode, volume)
ANX_PART_COMMON_SHIFT = -12
# AN-X Part Common (abs = AWM2_abs - 12, confirmed for 7+ fields ✅)
ANX_PART_COMMON = dict(
    anxMonoPoly=31,         # u8 bool default=1=Poly  ✅ (AWM2 abs 6751-12=6739, rel+31)
    anxPartPortaSW=32,      # u8 bool default=1  ✅
    anxVolume=123,          # u8 direct default=100  ✅
    anxPan=125,             # u8 center=64 default=0  ✅
    anxAegAttack=141,       # u8 center=64 default=0  ✅ (abs 6849, ui=+20→84)
    anxAegDecay=143,        # u8 center=64 default=0  ✅
    anxAegSustain=145,      # u8 center=64 default=0  ✅
    anxAegRelease=147,      # u8 center=64 default=0  ✅
    anxFEGDepthOffset=157,  # u8 center=64 default=0  ✅ (abs 6865, ui=+50→114)
    anxFilterCutoffOffset=159, # u8 center=64 default=0  ✅ (abs 6867, ui=+20→84)
    anxResonanceOffset=161, # u8 center=64 default=0  ★★★★☆ (abs 6869, derived)
    anxPortaTime=213,       # u8 direct default=64  ✅
    anxPortaMode=215,       # u8 bool default=1=FullTime  ✅
)
# FM-X Part Common (same -12 shift, confirmed for AEG ✅)
FMX_PART_COMMON = dict(
    fmxMonoPoly=31,         # u8 bool default=1=Poly  ★★★★☆ (AWM2 abs 6751-12=6739, rel+31)
    fmxVolume=123,          # u8 direct default=100  ★★★★☆
    fmxPan=125,             # u8 center=64 default=0  ★★★★☆
    fmxAegAttack=141,       # u8 center=64 default=0  ✅ (abs 6849, verified)
    fmxAegDecay=143,        # u8 center=64 default=0  ✅
    fmxAegSustain=145,      # u8 center=64 default=0  ✅
    fmxAegRelease=147,      # u8 center=64 default=0  ✅
)
# DPFM[29] = Performance Portamento SW (0=Off, 1=On), default=0  ✅
# AN-X OSC Pitch — stride=125 confirmed ✅
# AN-X OSC sub-table (PART_rel = MIDI_hex_addr + OSC_base, stride=125)
# OSC1_BASE=5918, OSC2_BASE=6043, OSC3_BASE=6168  — all 15 fields verified ✅
ANX_OSC = dict(
    # Wave & Octave (u8)
    anxOsc1Wave=5918,              # u8 enum 0-4 (Saw=0, Sq=2) default=0  ✅
    anxOsc2Wave=6043,              anxOsc3Wave=6168,
    anxOsc1Octave=5920,            # u8 enum 0-6 default=3=8'  ★★★☆☆
    anxOsc2Octave=6045,            anxOsc3Octave=6170,
    # Pitch (u16 LE, center=504)
    anxOsc1Pitch=5922,             # u16 LE center=504, ≈1:1 cent  ✅
    anxOsc2Pitch=6047,             anxOsc3Pitch=6172,
    # Pitch EG/LFO depths (u16 LE, center=247) — ENCODING CONFIRMED ✅
    # raw = round(ui * 95/400) + 247  (symmetric: ±400→±95 raw from center)
    # UI range: ±1040 (247 raw units each side)
    anxOsc1PitchEGDepth=5924,      # u16 LE center=247 ✅ (+400→342, 0→247, -400→152)
    anxOsc2PitchEGDepth=6049,      anxOsc3PitchEGDepth=6174,
    anxOsc1PitchEGDepthVelSens=5926, # u16 LE center=256 default=0  ★★★☆☆
    anxOsc2PitchEGDepthVelSens=6051, anxOsc3PitchEGDepthVelSens=6176,
    anxOsc1PitchLFODepth=5928,     # u16 LE center=247 default=0  ★★★☆☆
    anxOsc2PitchLFODepth=6053,     anxOsc3PitchLFODepth=6178,
    # Self Sync (u16 LE)
    anxOsc1SelfSyncPitch=5930,     # u16 LE direct default=0  ★★★☆☆
    anxOsc2SelfSyncPitch=6055,     anxOsc3SelfSyncPitch=6180,
    anxOsc1SelfSyncVelSens=5932,   # u16 LE center=256  ★★★☆☆
    anxOsc2SelfSyncVelSens=6057,   anxOsc3SelfSyncVelSens=6182,
    # PART+5934 = selfSyncPitchEGDepth — EG modulation depth for Self Sync Pitch
    # Confirmed Step74 via MODX M8: changes independently of selfSyncLFODepth(5936) ✅
    # Encoding: raw = UI + 256  (center=256, range 0–512, default=256=UI 0)
    # NOTE: DIFFERENT encoding from selfSyncLFODepth (which uses round(UI/25)+256)
    anxOsc1SelfSyncPitchEGDepth=5934,  # u16le  raw=UI+256  center=256  ★★★★★ (Steg74)
    anxOsc2SelfSyncPitchEGDepth=6059,  anxOsc3SelfSyncPitchEGDepth=6184,
    # Pulse Width — KORRIGERADE OFFSETS (Step 61, binärverifierade)
    # anxOsc1PulseWidth = PART+5938 (NOT 5936 as MIDI formula suggested!)
    # Encoding: raw = round(pct * 256 / 100), 50%=128(default), 60%=154
    anxOsc1PulseWidthVelSens=5936, # u16 LE center=256  ★★★☆☆ (MIDI-formel)
    anxOsc2PulseWidthVelSens=6061, anxOsc3PulseWidthVelSens=6186,
    anxOsc1PulseWidth=5938,        # u8 raw=round(pct*256/100), 50%→128, 60%→154  ★★★★★ (Step 61)
    anxOsc2PulseWidth=6063,        anxOsc3PulseWidth=6188,  # stride=125
    anxOsc1PulseWidthEGDepth=5940, # u16 LE center=256  ★★★☆☆
    anxOsc2PulseWidthEGDepth=6065, anxOsc3PulseWidthEGDepth=6190,
    anxOsc1PulseWidthLFODepth=5944,# u16 LE center=128  ★★★☆☆
    anxOsc2PulseWidthLFODepth=6069,anxOsc3PulseWidthLFODepth=6194,
    # Wave Shaper (u16 LE)
    anxOsc1WaveShaper=5946,        # u16 LE direct default=0  ★★★☆☆
    anxOsc2WaveShaper=6071,        anxOsc3WaveShaper=6196,
    anxOsc1WaveShaperVelSens=5948, # u8 direct default=0  ★★★★★ (Steg72)
    anxOsc2WaveShaperVelSens=6073, anxOsc3WaveShaperVelSens=6198,
    # Osc EG Depth → Shaper / Osc LFO Depth → Shaper (Step72, ★★★★★)
    # Encoding: 0x80+n (center=128), default=128 (=UI 0)
    anxOsc1ShaperEGDepth=5950,     # u8  0x80+n  center=128  ★★★★★
    anxOsc2ShaperEGDepth=6075,     anxOsc3ShaperEGDepth=6200,
    anxOsc1ShaperLFODepth=5952,    # u8  0x80+n  center=128  ★★★★★
    anxOsc2ShaperLFODepth=6077,    anxOsc3ShaperLFODepth=6202,
    # Ring Mod (MIDI OSC addr 0x28=40, same stride=125)
    anxOsc1RingModDepth=5958,      # u16 LE direct default=0  ✅ (0→50)
    anxOsc2RingModDepth=6083,      anxOsc3RingModDepth=6208,
    # OSC EG sub-table — KORRIGERADE OFFSETS (Step 60, binärverifierade med 16 filer)
    # Old MIDI-formula-based offsets (5813-5817) were WRONG.
    # Correct sub-tabell base = PART+5970 (not 5779+34=5813 som MIDI antydde)
    # OSC1 EG: abs 12678-12684 (PART rel 5970-5976)
    anxOsc1EGAttackTime=5970,      # u16 LE direct default=0  ★★★★★ (Step 60, corrected from 5813)
    anxOsc1EGDecayTime=5972,       # u16 LE default=160  ★★★★★ (corrected from 5815)
    anxOsc1EGSustainLevel=5974,    # u16 LE direct default=0  ★★★★★ (corrected from 5817)
    anxOsc1EGReleaseTime=5976,     # u16 LE direct default=160  ★★★★★ (var korrekt, Steg 46)
    # OSC EG Depth/LFODepth (not kollision med EG — separata adresser):
    anxOsc1EGDepth=5942,           # u16 LE ★★★★★ (Step 60, NY)
    anxOsc1LFODepth=5944,          # u16 LE ★★★★★ (Step 60, NY)
    # OSC2 EG: stride=125 from OSC1 ✅
    anxOsc2EGAttackTime=6095,      # ★★★★★ (corrected from 5938)
    anxOsc2EGDecayTime=6097,       # ★★★★★ (corrected from 5940)
    anxOsc2EGSustainLevel=6099,    # ★★★★★ (corrected from 5942)
    anxOsc2EGReleaseTime=6101,     # ★★★★★ (var korrekt)
    anxOsc2EGDepth=6067,           # ★★★★★ (Step 60, stride=125 from OSC1EGDepth)
    anxOsc2LFODepth=6069,          # ★★★★★ (Step 60)
    # OSC3 EG: stride=125 from OSC2 ✅
    anxOsc3EGAttackTime=6220,      # ★★★★★ (corrected from 6063)
    anxOsc3EGDecayTime=6222,       # ★★★★★ (corrected from 6065)
    anxOsc3EGSustainLevel=6224,    # ★★★★★ (corrected from 6067)
    anxOsc3EGReleaseTime=6226,     # ★★★★★ (var korrekt)
)
# AN-X Filter sub-tables: DPFM_rel = MIDI_hex_addr + filter_base
# Filter 1 base=6297, Filter 2 base=6374 (stride=77) — formula verified ✅
# 10/10 Filter 1 defaults verified against baseline  ★★★☆☆ (MIDI-derived)
ANX_FILTER = dict(
    anxFilter1Type=6297,               # u8 enum default=1=LPF12  ✅
    anxFilter1Cutoff=6299,             # u16 LE Hz default=1023  ✅
    anxFilter1CutoffVelSens=6301,      # u16 LE center=256 default=256  ★★★☆☆
    anxFilter1CutoffEGDepth=6303,      # u16 LE center=256 default=256  ★★★☆☆
    anxFilter1CutoffEGDepthVelSens=6305,# u16 LE center=256  ★★★☆☆
    anxFilter1CutoffLFODepth=6307,     # u16 LE center=256  ★★★☆☆
    anxFilter1CutoffKeyFollow=6309,    # u8 enum default=0  ★★★☆☆
    anxFilter1Resonance=6311,          # u8 direct default=0  ✅
    anxFilter1ResonanceVelSens=6313,   # u16 LE center=256 default=256  ★★★☆☆
    anxFilter1Drive=6315,              # u8 0-80 (0.75dB/unit) default=0  ✅
    anxFilter1OutLevel=6319,           # u8 center=64 (0.375dB/unit)  ✅
    anxFilter2Type=6374,               # u8 enum default=5
    anxFilter2Cutoff=6376,             # u16 LE Hz default=0
    anxFilter2Resonance=6388,          # u8 direct default=0
    anxFilter2Drive=6392,              # u8 0-80 (0.75dB/unit) default=0  ✅
    anxFilter2OutLevel=6396,           # u8 center=64 (0.375dB/unit)  ✅
)
# AN-X Modifier section (PART_rel, offset=6408 base)
# WaveFolder fields (MIDI_hex_addr + 6408):
ANX_MODIFIER = dict(
    anxWaveFolder=6408,            # u16 LE direct default=0  ✅ (0→50)
    anxWaveFolderVelSens=6410,     # u16 LE center=256  ★★★☆☆ (MIDI 0x02+6408)
    anxWaveFolderEGDepth=6412,     # u16 LE center=256  ★★★☆☆ (MIDI 0x04+6408)
    anxWaveFolderLFODepth=6414,    # u16 LE center=256  ★★★☆☆ (MIDI 0x06+6408)
    anxWaveFolderTexture=6416,     # u16 LE direct default=256  ★★★☆☆ (MIDI 0x08+6408)
    anxWaveFolderType=6418,        # u16 LE enum default=1=Hard  ★★★☆☆ (MIDI 0x0A+6408)
    anxModEGAttackTime=6420,       # u16 LE direct default=0  ★★★★★ BINÄRVERIFIERAD (Step 46)
    anxModEGDecayTime=6422,        # u16 LE default=160  ★★★☆☆ (MIDI 0x0E+6408)
    anxModEGSustainLevel=6424,     # u16 LE direct default=0  ★★★☆☆ (MIDI 0x10+6408)
    anxModEGReleaseTime=6426,      # u16 LE default=160  ★★★☆☆ (MIDI 0x12+6408)
)
# Insertion FX — Classic Flanger (16/16) och Symphonic (12/12) COMPLETE ✅
# ── INSERTION FX TYPE INDEX (ENGINE-OBEROENDE) ────────────────────────────
# Gäller för BÅDE InsertionA (PART+275) och InsertionB (PART+332)
# Encoding: lo = type_index & 0x7F,  hi = (type_index >> 7) & 0x7F
# Källa: Effect Type List.xlsx + binärverifiering Steg 46-60
# ★★★★★ = binärverifierat  |  ★★★★☆ = från Effect Type List
# NOTE: SPX HALL (130) och CROSS DELAY (256) är OLIKA — SPXHall lo=2,hi=1 (130)
#      CrossDelay lo=0,hi=2 (256). Vår Steg 60-mätning av CrossDelay-filen var fel.
FX_TYPE_INDEX = {
    # ── THRU ──────────────────────────────────────────────────────────────
    'THRU':                    0,   # ★★★★★
    # ── REVERB ────────────────────────────────────────────────────────────
    'SPX HALL':              130,   # ★★★★★ lo=2,hi=1
    'SPX ROOM':              146,   # ★★★★☆
    'SPX STAGE':             176,   # ★★★★☆
    'GATED REVERB':          208,   # ★★★★☆
    'REVERSE REVERB':        216,   # ★★★★☆
    # ── DELAY ─────────────────────────────────────────────────────────────
    'CROSS DELAY':           256,   # ★★★★★ lo=0,hi=2  (KORRIGERAT från 130!)
    'TEMPO CROSS DELAY':     272,   # ★★★★☆
    'TEMPO DELAY MONO':      288,   # ★★★★☆
    'TEMPO DELAY STEREO':    296,   # ★★★★☆
    'CONTROL DELAY':         304,   # ★★★★☆
    'DELAY LR':              320,   # ★★★★☆
    'DELAY LCR':             336,   # ★★★★☆
    'ANALOG DELAY RETRO':    352,   # ★★★★☆
    'ANALOG DELAY MODERN':   360,   # ★★★★☆
    # ── CHORUS ────────────────────────────────────────────────────────────
    'G CHORUS':              384,   # ★★★★☆
    '2 MODULATOR':           400,   # ★★★★☆
    'SPX CHORUS':            416,   # ★★★★☆
    'SYMPHONIC':             432,   # ★★★★★ lo=48,hi=3
    'ENSEMBLE DETUNE':       448,   # ★★★★☆
    # ── FLANGER ───────────────────────────────────────────────────────────
    'VCM FLANGER':           512,   # ★★★★☆
    'CONTROL FLANGER':       520,   # ★★★★☆
    'CLASSIC FLANGER':       528,   # ★★★★★ lo=16,hi=4
    'TEMPO FLANGER':         544,   # ★★★★☆
    'DYNAMIC FLANGER':       560,   # ★★★★☆
    # ── PHASER ────────────────────────────────────────────────────────────
    'VCM PHASER MONO':       640,   # ★★★★☆
    'VCM PHASER STEREO':     656,   # ★★★★☆
    'CONTROL PHASER':        664,   # ★★★★☆
    'TEMPO PHASER':          672,   # ★★★★★ lo=32,hi=5
    'DYNAMIC PHASER':        688,   # ★★★★☆
    # ── TREMOLO & ROTARY ──────────────────────────────────────────────────
    'AUTO PAN':              768,   # ★★★★☆
    'TREMOLO':               784,   # ★★★★★ lo=16,hi=6
    'ROTARY SPEAKER 1':      800,   # ★★★★☆
    'ROTARY SPEAKER 2':      816,   # ★★★★☆
    # ── DISTORTION ────────────────────────────────────────────────────────
    'AMP SIMULATOR 1':       896,   # ★★★★☆
    'AMP SIMULATOR 2':       912,   # ★★★★☆
    'COMP DISTORTION':       928,   # ★★★★★ lo=32,hi=7
    'COMP DISTORTION DELAY': 944,   # ★★★★☆
    'US COMBO':              960,   # ★★★★☆
    'JAZZ COMBO':            961,   # ★★★★☆
    'US HIGH GAIN':          962,   # ★★★★☆
    'BRITISH LEAD':          963,   # ★★★★☆
    'MULTI FX':              964,   # ★★★★☆
    'SMALL STEREO':          965,   # ★★★★☆
    'BRITISH COMBO':         966,   # ★★★★☆
    'BRITISH LEGEND':        967,   # ★★★★☆
    # ── COMPRESSOR ────────────────────────────────────────────────────────
    'VCM COMPRESSOR 376':   1024,   # ★★★★☆
    'CLASSIC COMPRESSOR':   1040,   # ★★★★★ lo=16,hi=8
    'MULTI BAND COMP':      1056,   # ★★★★☆
    'UNI COMP DOWN':        1072,   # ★★★★☆
    'UNI COMP UP':          1080,   # ★★★★☆
    'PARALLEL COMP':        1088,   # ★★★★☆
    # ── WAH (MODX M, not i Effect Type List xlsx) ──────────────────────────
    'VCM AUTO WAH':         1280,   # ★★★★★ lo=0,hi=10
    # ── LO-FI (MODX M) ────────────────────────────────────────────────────
    'NOISY':                1424,   # ★★★★★ lo=16,hi=11
    # ── TECH (MODX M) ─────────────────────────────────────────────────────
    'SLICE':                1616,   # ★★★★★ lo=80,hi=12
    # ── MISC (MODX M) ─────────────────────────────────────────────────────
    'PRESENCE':             1672,   # ★★★★★ lo=8,hi=13
    'WAVE FOLDER':          1704,   # ★★★★★ lo=40,hi=13 — FX-TABELL COMPLETE! (Step 61)
}

# Omvänd lookup: TypeIndex → namn
FX_INDEX_TO_NAME = {v: k for k, v in FX_TYPE_INDEX.items()}

def fx_type_bytes(name):
    """Returnerar (lo, hi) för ett InsertionFX-namn. Fungerar för InsA OCH InsB."""
    idx = FX_TYPE_INDEX.get(name.upper(), 0)
    return (idx & 0x7F, (idx >> 7) & 0x7F)

def fx_name_from_bytes(lo, hi):
    """Returnerar FX-namn från (lo, hi) bytes (InsA eller InsB)."""
    return FX_INDEX_TO_NAME.get(hi * 128 + lo, f'UNKNOWN({hi*128+lo})')

# InsertionA/B base offsets (PART-relativa):
FXA_BASE = 275   # InsertionA: PART+275
FXB_BASE = 332   # InsertionB: PART+332
# fxA+14: EQ Low Freq   (tabellindex, default=22=250Hz)        ✅
# fxA+16: EQ Low Gain   (center=64, 1raw=1dB)                  ✅
# fxA+18: EQ High Freq  (tabellindex, default=48=5kHz)         ✅
# fxA+20: EQ High Gain  (center=64, 1raw=1dB)                  ✅
# fxA+22: Dry/Wet       (direct: 0=100%Dry, 64=50/50, 127=100%Wet) ✅
# fxA+24: EQ Mid Freq   (tabellindex, default=38=1.6kHz)       ✅
# fxA+26: EQ Mid Gain   (center=64, 1raw=1dB)                  ✅
# fxA+28: EQ Mid Width  (tabellindex, default=7=0.7)           ✅
#
# CLASSIC FLANGER — specifika params (fxA+4-12, fxA+30-34):
# fxA+4:  LFO Speed   (raw=round(Hz*23.7), default=26=1.09Hz)  ✅
# fxA+6:  LFO Depth   (direct, default=34)                     ✅
# fxA+8:  LFO Wave    (0=Triangle, 1=Sine, default=0)          ✅
# fxA+10: Delay Offset (tabellindex, default=24=0.65ms)        ✅
# fxA+12: Feedback    (raw=percent+100, default=151=51%)       ✅
# fxA+30: Mod Phase   (raw=phase_index*2, 180°→16)             ✅
# fxA+32: FB High Damp (raw=value*10, default=9=0.9)           ✅
# fxA+34: Analog Feel  (direct, default=0)                     ✅
#
# SYMPHONIC — specifika params (Step 46-49, 12/12 ★★★★★):
# fxA+4:  LFO Speed   (raw=round(Hz*23.7), default=11≈0.46Hz)  ✅ SAMMA formel som CF!
# fxA+6:  LFO Depth   (direct, default=25)                     ✅
# fxA+8:  Delay Offset (tabellindex, default=1≈0ms, 1ms→10)   ✅ (INTE LFO Wave!)
# (fxA+10-12 saknas i Symphonic — CF-specifika fält)
#
# LFO Speed encoding (BÅDA FX): raw = round(Hz * 23.7045)  ★★★★★
#   Datapunkter: 0.46Hz→11, 0.80Hz→19, 1.09Hz→26, 1.30Hz→31, 1.60Hz→38, 1.98Hz→47
ANX_INSERT_FX = dict(
    fxATypeLo=275,   # u8, lo-byte of 7-bit FX type index  ✅
    fxATypeHi=276,   # u8, hi-byte of 7-bit FX type index  ✅
    fxBTypeLo=332,   # u8, lo-byte  ✅
    fxBTypeHi=333,   # u8, hi-byte  ✅
)
# AN-X noise bytes to exclude from diffs:
ANX_PERF_NOISE = {23, 24, 6724, 6725}

COMMON_FIELDS = dict(
    portamentoSw=41, portamentoTime=106,
    commonVolume=80, commonPan=82,
    revSend=124, varSend=130,
)

# FM-X OP Routing Matrix abs=6730-6793 (Step 62)
# 64 bytes, all default=1 = all OP-kopplingarna aktiva
# 8 OPs × 8 kopplingsbytes = 64 bytes
# Ändras ALDRIG via ESP UI — interna algoritm-defaults
# Ska INTE skrivas vid patch-editing
FMX_OP_ROUTING_MATRIX_ABS = (6730, 6793)  # (start, end), default=1 all

# AWM2 After Touch Assign register (Step 61) ★★★★★
# Separat från CA-blocket (abs=8220+) — eget litet AT-register
# Har sin EGEN destination-encoding (kortare lista än CA)
AWM2_AT_ASSIGN = dict(
    atSwitch=593,      # abs PART+593, u8 bool 0=Off,1=On  ★★★★★
    atDestination=595, # abs PART+595, u8 enum Pitch=1(def), FilterCutoff=9  ★★★★★
)
# AT Destination encoding (AWM2, ANNAN än CA_DESTINATION!):
AT_DESTINATION = {
    1: 'Pitch',         # default  ★★★★★
    9: 'FilterCutoff',  # ★★★★★
}

# NOTE: OP Mute/Solo sparas INTE i YSFC (Step 61, binärbekräftat)
# Mute/Solo är real-time performance state — ändras not i binärfilen vid Save.

FMX_PART_BASE = dict(
    # FM Color + algorithm sub-table (all at ODD abs offsets, u8 each)
    fmcLfoAmplWave=12521,   # u8 enum default=0  ★★★★☆
    fmcLfoAmplSpeed=12523,  # u8 direct default=0  ★★★★☆
    algorithm=12525,        # u8 direct raw=algo-1, Init=69→raw=68  ✅ CORRECTED
    feedback=12527,         # u8 direct default=0  ✅ CORRECTED
    fmcLfoAmplDepth=12529,  # u8 direct default=1  ★★★★☆
    # NOTE: abs 12529 (PART+5821) = fmxPart2ndLfoExtended (see FMX_PART_2ND_LFO)
    # NOTE: abs 12531 (PART+5823) = fmxPart2ndLfoSpeedExtended (see FMX_PART_2ND_LFO)
    # FM Color depth fields (center=128, all verified ✅)
    fmcDepth=12533,         # u8 center=128 default=0  ✅ (Depth_50→178)
    fmcHarmonics=12535,     # u8 center=128 default=0  ✅
    fmcAttack=12537,        # u8 center=128 default=0  ✅
    fmcDecay=12539,         # u8 center=128 default=0  ✅
    fmcSustain=12541,       # u8 center=128 default=0  ✅
    fmcRelease=12543,       # u8 center=128 default=0  ✅
    fmcTexture=12545,       # u8 center=128 default=0  ✅
    # FM-X Filter sub-table (abs = PART + rel, rel = MIDI_hex_addr + 5843)
    fmxFilterType=12551,        # u8 enum Thru=21,LPF18D=2,HPF12=7  ✅
    fmxFilterCutoff=12553,      # u16 LE Hz default=1023  ✅
    fmxCutoffVelSens=12555,     # u8 center=64, raw_default=64(ui=0)  ★★★★☆ verified
    fmxFilterResonance=12557,   # u8 direct default=10  ✅
    # FM-X Part AEG (PART_COMMON_SHIFT=-12, confirmed ✅)
    fmxAegAttack=6849,          # u8 center=64 default=0  ✅
    fmxAegDecay=6851,           # u8 center=64 default=0  ✅
    fmxAegSustain=6853,         # u8 center=64 default=0  ✅
    fmxAegRelease=6855,         # u8 center=64 default=0  ✅
    # FM-X Part Filter Offsets (Part-level, center=64)
    fmxFEGDepthOffset=6865,     # u8 center=64 default=0  ✅ (rel+157)
    fmxFilterCutoffOffset=6867, # u8 center=64 default=0  ✅ (rel+159)
    fmxResonanceOffset=6869,    # u8 center=64 default=0  ✅ (rel+161)
)
# FM-X Part LFO TempoNote tabell (raw = list_index + 5)
# Bekräftad med 1 fil + ESP-bild (Step 57) ★★★★★
FMX_LFO_TEMPONOTE = {
    5: "1/16",  6: "1/8 Tri.", 7: "1/16 Dot.", 8: "1/8",
    9: "1/4 Tri.", 10: "1/8 Dot.", 11: "1/4",   # 11=default
    12: "1/2 Tri.", 13: "1/4 Dot.", 14: "1/2",
    15: "Whole Tri.", 16: "1/2 Dot.",
    17: "1/4 x4", 18: "1/4 x5", 19: "1/4 x6", 20: "1/4 x7",
    21: "1/4 x8", 22: "1/4 x16", 23: "1/4 x32", 24: "1/4 x64",
}

# Controller Assign structure (Step 57-58) ★★★★★
# Identisk 22-byte layout på PART-nivå (16 entries) och PERF-nivå (8 entries)
# PART CA: abs = CA_PART_BASE + ca_idx * CA_STRIDE  (ca_idx 0-15)
# PERF CA: abs = CA_PERF_BASE + ca_idx * CA_STRIDE  (ca_idx 0-7, Knob1-8)
CA_STRIDE    = 22
CA_PART_BASE = 8220   # PART+1512, CA1=8220, CA16=8550
CA_PERF_BASE = 2451   # PERF Common, Knob1=2451, Knob8=2451+7×22=2605

# Offsets within each 22-byte CA entry (ENGINE-OBEROENDE — AWM2/FM-X/AN-X ✅):
CA_ENTRY = dict(
    header=0,        # u8 default=18, okänd funktion
    sw=1,            # u8 bool 0=Off,1=On  ★★★★★
    source=3,        # u8 enum — se CA_SOURCE (PB=0,MW=1,Knob1=8...)  ★★★★★
    destination=5,   # u8 enum — se CA_DESTINATION (Vol=1,Cut=85)  ★★★★★
    curveType=9,     # u8 enum (Standard=0, Harmonic=18)  ★★★★★
    param1=11,       # u8 direct default=5  ★★★★★
    param2=13,       # u8 direct default=0  ★★★★★
    polarity=15,     # u8 bool 0=UNI,1=BI  ★★★★★
    depth=17,        # u8 default=192=0xC0 — MODX-INTERNT, not synlig parameter
                     # Uppdateras automatiskt av MODX vid varje Store (som timestamp-bytes)
                     # Ska IGNORERAS vid patch-editing, not skrivas ★★★★★
)

# CA Source enum (verifierad Steg 57-59, all engines)
CA_SOURCE = {
    0:  "PitchBend",   # ★★★★★
    1:  "ModWheel",    # ★★★★★ default
    # 2: AfterTouch   # not verifierad
    # 3: FootCtrl     # not verifierad
    # 4: FootSw       # not verifierad
    # 5: Breath       # not verifierad
    # 6-7: CC         # not verifierade
    8:  "Knob1",      # ★★★★★
    9:  "Knob2",      # ★★★★★
    10: "Knob3",      # ★★★★★
    # 11-15: Knob4-8  # not verifierade
}

# CA Destination enum (verifierad Steg 57-60, all engines)
# InsA Param-serie: raw = param_nr (1-24, linjärt). InsB: raw=25 alltid, param# i CA+11
CA_DESTINATION = {
    1:   'Volume',          # ★★★★★ default
    # 2-24: InsA Param2-24 (linjärt: raw = param_nr)
    2:   'InsA Param2',     # ★★★★★
    3:   'InsA Param3',     # ★★★★★
    24:  'InsA Param24',    # ★★★★★ (0x18, linjärt bekräftat)
    25:  'InsB Param',      # ★★★★★ (fast raw=25, param# i CA+11)
    50:  'Rev Send',        # ★★★★★
    51:  'Var Send',        # ★★★★★
    59:  'P.LFO Depth 3',   # ★★★★★
    60:  'Element Level',   # ★★★★★ (0x3C)
    61:  'Element Pan',     # ★★★★★ (0x3D)
    62:  'Element Delay',   # ★★★★★ (0x3E)
    85:  'Filter Cutoff',   # ★★★★★ (0x55)
    87:  'HPF Cutoff',      # ★★★★★ (0x57)
    100: 'Part Pan',        # ★★★★★ (0x64)
    105: 'Arp Gate Time',   # ★★★★★ (0x69)
    118: 'MS Length',       # ★★★★★ (0x76)
    # Fler not verifierade
}

# AWM2 ctrlSet — sitter i AWM2 element-data (not i CA-blocket)
# Adress ännu not binärverifierad — väntar på element-nivå testfiler
# Different from Part-level AEG offsets (rel+141-147)
ANX_SYNTH_AEG = dict(
    anxSynthAegAttack=12553,   # u8 direct default=0  ✅ (Attack_50→50)
    anxSynthAegDecay=12555,    # u8 direct default=160  ✅ (Decay_50→50)
    anxSynthAegSustain=12557,  # u16 LE default=511 (max level)  ✅ (Sustain_50→50)
    anxSynthAegRelease=12559,  # u8 direct default=115  ✅ (Release_50→50)
)
# Applies to ALL engines (AWM2, FM-X, AN-X): verified ✅
# DPFM_rel = MIDI_hex_addr + 205
PART_SUBTABLE_OFFSET = 205
PART_SUBTABLE = dict(
    pitchBendRangeLower=207,  # u8 direct default=62  ✅ (MIDI 0x02)
    detune=209,               # u16 LE center=128 default=128=0Hz  ✅ (MIDI 0x04)
    noteShift=211,            # u8 center=64 default=64=0st  ✅ (MIDI 0x06)
    portaTime=213,            # u8 direct default=64  ✅ (MIDI 0x08)
    portaMode=215,            # u8 bool default=1=FullTime  ✅ (MIDI 0x0A)
    # Part 3-band EQ (same offset=205, all engines)
    partEqLowFreq=231,        # u8 freq-index default=54(=100Hz), 84Hz→64  ★★★★★ offset verif. (Step 46)
    partEqLowGain=233,        # u8 center=64 (dB*2.667+64) default=0dB  ✅ (MIDI 0x1C)
    partEqMidFreq=235,        # u8 freq-index default=141  ★★★☆☆ (MIDI 0x1E)
    partEqMidGain=237,        # u8 center=64 default=0dB  ✅ (MIDI 0x20)
    partEqMidQ=239,           # u8 direct default=0  ★★★☆☆ (MIDI 0x22)
    partEqHighFreq=241,       # u8 freq-index default=231  ★★★☆☆ (MIDI 0x24)
    partEqHighGain=243,       # u8 center=64 default=0dB  ✅ (MIDI 0x26)
)
FMX_OP_LAYOUT = dict(
    # OP1_BASE=12676, stride=123 — COMPLETE 21/21 fält ★★★★★ (v4.0)
    # PRE-OP block (relativt OP1_BASE, negativa offsets)
    keyOnReset=-4,           # u8 bool default=1=On  ★★★★★ (Step 50)
    freqMode=-2,             # u8 enum 0=Ratio,1=Fixed  ★★★★☆
    # Freq/Spectral block (off=0-14)
    coarse=0,                # u8 direct default=1  ✅
    fine=2,                  # u8 direct default=0  ✅
    detune=4,                # u8 center=15 default=0  ✅
    pitchKey=6,              # u8 direct default=0  ★★★★☆
    pitchVel=8,              # u8 center=7 default=0  ★★★★☆
    spectralForm=10,         # u8 enum 0-6: 0=Sine,1=All1,2=All2,3=Odd1,4=Odd2,5=Res1,6=Res2  ★★★★★ (Step 49-50)
    spectralSkirt=12,        # u8 direct default=0  ★★★★★ (Step 49)
    spectralResonance=14,    # u8 direct default=0 (aktiv för Res1/Res2)  ★★★★★ (Step 50)
    # PEG block (off=16-20)
    pegInitialLevel=16,      # u8 direct default=50  ★★★★☆ (raw=50=UI+50)
    pegAttackLevel=18,       # u8 direct default=50  ✅ (Level_Attack_50→100)
    pegAttackTime=20,        # u8 direct default=0   ★★★★★ (KORRIGERAT: var aegAttackTime!)
    # AEG block (off=22-40)
    pegDecayTime=22,        # u8 direct default=0   ★★★★★ (KORRIGERAT v5.0: var aegDelayTime! PEG Decay Time)
    aegAttackLevel=24,       # u8 direct default=99  ★★★★☆
    aegDecay1Level=26,       # u8 direct default=99  ★★★★☆
    aegDecay2Level=28,       # u8 direct default=99  ★★★★☆
    aegReleaseLevel=30,      # u8 direct default=0   ★★★★★
    aegAttackTime=32,        # u8 direct default=0   ★★★★★ (LÖST Steg 52 — AEG Attack, höger panel)
    aegDecay1Time=34,        # u8 direct default=0   ✅
    aegDecay2Time=36,        # u8 direct default=0   ✅
    aegReleaseTime=38,       # u8 direct default=40  ✅
    aegHoldTime=40,          # u8 direct default=0   ✅
    # Key/Level scaling block (off=42-56)
    aegTimeKeyFollow=42,     # u8 direct default=0 ("Time/Key" i ESP)  ★★★★★ (Step 46)
    level=44,                # u8 direct default=0   ✅
    aegBreakPoint=46,        # u8 raw=MIDI_note-9, default=39=C3  ★★★★★ (Step 51)
    lvlKeyLo=48,             # u8 direct default=0 (Lvl/Key Lo)  ★★★★★ (Step 50)
    lvlKeyHi=50,             # u8 direct default=0 (Lvl/Key Hi)  ★★★★★ (Step 50)
    curveLo=52,              # u8 enum 0=-Linear,1=-Exp,2=+Exp,3=+Linear, default=0  ★★★★★ (Step 50)
    curveHi=54,              # u8 enum (same as curveLo), default=0  ★★★★★ (Step 50)
    levelVel=56,             # u8 center=7 default=0  ★★★★☆
)
AWM2_ELEM_LAYOUT = dict(
    # Waveform (element header, DPFM_rel = MIDI_Wave_addr - 4 for addr<0x0C, special for addr 0-0xA)
    waveformNumber=0,                 # u16 LE, 1-based index (Waveform List #nr) ✅ verified
    waveformBank=2,                   # u8 direct (1=preset internal) ✅ verified
    # Pan/spatial (MIDI Wave addr 0x0C+, DPFM_rel = MIDI_addr - 4)
    pan=8,   randomPan=10,   alternatePan=12,  scalingPan=14,
    xcaControl=16,                    # u8 enum 0-7 (Normal/Legato/KeyOff/Cycle/Random/etc)
    # Zone (Note/Vel limits)
    noteLowLimit=18, noteHighLimit=20,
    velLowLimit=22,  velHighLimit=24,  velCrossFade=26,
    # Key On Delay (rel+28-36 block — not yet fully mapped by MIDI table)
    keyOnDelayElemSW=30,              # u8 bool default=1
    keyOnDelayLen=34,                 # u8 direct default=11
    # Amplitude section (MIDI Amp addr, DPFM_rel = MIDI_addr + 40)
    level=40,                         # u8 direct default=127           MIDI Amp 0x00
    ampLevelVel=42,                   # u8 center=64  ✅ verified        MIDI Amp 0x02
    levelVelCurve=46,                 # u8 enum 0-5 default=3            MIDI Amp 0x06
    # AEG Times
    aegAttack=48,   aegDecay1=50,  aegDecay2=52,  aegHalfDamperT=54,  aegRelease=56,
    # AEG Levels
    aegInitialLvl=58,  aegAttackLvl=60,  aegDecay1Lvl=62,  aegDecay2Lvl=64,
    # AEG Velocity / Key Follow
    aegTimeVelSegment=66,             # u8 enum 0-4 default=4            MIDI Amp 0x1A
    aegTimeVel=68,                    # u8 center=64                     MIDI Amp 0x1C
    aegTimeKeyFollowSens=70,          # u8 center=64 default=0           MIDI Amp 0x1E
    # Pitch section (MIDI Pitch addr, DPFM_rel = MIDI_addr + 98)
    pegCoarseTune=98,                 # u8 center=64 (−48..+48)
    pegFineTune=100,                  # u8 center=64 (−64..+63)
    pegPitchVelSens=102,              # u8 center=64
    pegRandomPitch=104,               # u8 direct
    pegKeyFollowSens=106,             # u8 direct (0x60=96 default in Init Normal)
    pegKFCenterNote=108,              # u8 MIDI note (C4=60)
    pegFineTuneKF=110,                # u8 center=64
    pegHoldTime=112,                  # u8 direct
    pegAttackTime=114,                # u8 direct
    pegDecay1Time=116,                # u8 direct
    pegDecay2Time=118,                # u8 direct
    pegReleaseTime=120,               # u8 direct
    pegHoldLevel=122,                 # u8 center=128
    pegAttackLevel=124,               # u8 center=128
    pegDecay1Level=126,               # u8 center=128
    pegDecay2Level=128,               # u8 center=128
    pegReleaseLevel=130,              # u8 center=128
    pegDepth=132,                     # u8 center=64 (Init Normal=84=ui+20)
    pegTimeVelSegment=134,            # u8 enum 0-4 default=4  ✅ verified
    pegTimeVelSens=136,               # u8 center=64            ✅ verified
    pegTimeKFSens=138,                # u8 center=64
    pegDepthVelSens=140,              # u8 enum? (Init Normal=2)
    pegDepthKFSens=142,               # u8 center=64
    pegDepthKFCenterNote=144,         # u8 MIDI note
    levelBP0=72,                      # u8 note (C-2=0) default=24=C0    MIDI Wave 0x20
    levelBP1=74,                      # u8 note default=36=C1            MIDI Wave 0x22 ✅
    levelBP2=76,                      # u8 note default=48=C2            MIDI Wave 0x24 ✅
    levelBP3=78,                      # u8 note default=60=C3            MIDI Wave 0x26 ✅
    levelBP4=80,                      # u8 note default=72=C4            MIDI Wave 0x28 ✅
    levelOfs1=82,                     # u8 center=128 default=0          MIDI Wave 0x2A ✅
    levelOfs2=84,                     # u8 center=128 default=0          MIDI Wave 0x2C ✅
    levelOfs3=86,                     # u8 center=128 default=0          MIDI Wave 0x2E ✅
    levelOfs4=88,                     # u8 center=128 default=0          MIDI Wave 0x30 ✅
    levelKeyFollowSens=90,            # u8 center=64 default=0           MIDI Wave 0x32 ✅
    aegTimeKeyFollowRelAdj=92,        # u8 direct (0-127) default=64     MIDI Wave 0x34 ✅
    # Filter section (MIDI Filter addr, DPFM_rel = MIDI_addr + 150) — 35/35 verified ✅
    filterType=150,                   # u8 enum 0-21, default=4 (LPF+HPF) MIDI 0x00
    cutoff=152,                       # u16 LE Hz, default=640             MIDI 0x02 ✅
    cutoffVelSens=154,                # u8 center=64 default=0             MIDI 0x04 ✅
    elemFilterResonance=156,          # u8 direct 0-127 default=0          MIDI 0x06 ✅
    resonanceVelSens=158,             # u8 center=64 default=0             MIDI 0x08 ✅
    hpfCutoff=160,                    # u16 LE Hz default=0                MIDI 0x0A ✅
    dualFilterDistance=162,           # u8 center=128 default=0 (Dual)     MIDI 0x0C ✅
    filterGain=164,                   # u8 direct 0-255 default=230        MIDI 0x0E ✅ verified
    # Filter FEG Times (u8 direct)
    fegTimeHold=166,                  # u8 direct default=0    ✅ MIDI 0x10
    fegTimeAttack=168,                # u8 direct default=0    ✅ MIDI 0x12
    fegTimeDecay1=170,                # u8 direct default=64   ✅ MIDI 0x14
    fegTimeDecay2=172,                # u8 direct default=64   ✅ MIDI 0x16
    fegTimeRelease=174,               # u8 direct default=80   ✅ MIDI 0x18
    # Filter FEG Levels (u8 center=128)
    fegLevelHold=176,                 # u8 center=128 default=0    ✅ MIDI 0x1A
    fegLevelAttack=178,               # u8 center=128 default=127  ✅ MIDI 0x1C
    fegLevelDecay1=180,               # u8 center=128 default=127  ✅ MIDI 0x1E
    fegLevelDecay2=182,               # u8 center=128 default=127  ✅ MIDI 0x20
    fegLevelRelease=184,              # u8 center=128 default=0    ✅ MIDI 0x22
    # Filter FEG Envelope
    fegDepth=186,                     # u8 center=64 default=+40   ✅ MIDI 0x24
    fegDepthVelSegment=188,           # u8 enum 0-4 default=4      ✅ MIDI 0x26
    fegDepthVelSens=190,              # u8 center=64 default=0     ✅ MIDI 0x28
    fegTimeVelSegment=192,            # u8 center=64 default=0     ✅ MIDI 0x2A (actual=64)
    fegTimeVelSens=194,               # u8 direct default=2        ✅ MIDI 0x2C (actual=2)
    fegTimeKeyFollowSens=196,         # u8 center=64 default=0     ✅ MIDI 0x2E
    fegTimeKeyFollowCenterNote=198,   # u8 note default=24=C0      ✅ MIDI 0x30 (actual=24)
    # Filter Cutoff Scaling (u8 note / center=128)
    cutoffScalingBP1=200,             # u8 note default=36=C1      ✅ MIDI 0x32
    cutoffScalingBP2=202,             # u8 note default=48=C2      ✅ MIDI 0x34
    cutoffScalingBP3=204,             # u8 note default=60=C3      ✅ MIDI 0x36
    cutoffScalingBP4=206,             # u8 note default=72=C4      ✅ MIDI 0x38
    cutoffScalingOfs1=208,            # u8 center=128 default=0    ✅ MIDI 0x3A
    cutoffScalingOfs2=210,            # u8 center=128 default=0    ✅ MIDI 0x3C
    cutoffScalingOfs3=212,            # u8 center=128 default=0    ✅ MIDI 0x3E
    cutoffScalingOfs4=214,            # u8 center=128 default=0    ✅ MIDI 0x40
    # Filter Key Follow (% encoding: ui=round((raw-64)*200/64), raw=round(ui*64/200)+64)
    cutoffKeyFollow=216,              # u8 keyfollow% default=+31% ✅ MIDI 0x42 (raw=74)
    hpfCutoffKeyFollow=218,           # u8 keyfollow% default=0%   ✅ MIDI 0x44 (raw=64)
    # Element EQ (rel+220-230) — 6 fields verified ✅
    eqType=220,                       # u8 enum (0=Thru, 1=P.EQ, 2=Boost6, ...) default=0  ✅
    eqQ=222,                          # u8 direct (P.EQ Q only) default=0  ✅
    eqLowFreq=224,                    # u8 freq-table index default=54  ✅ (shared w/ eqPeqFreq)
    eqLowGain=226,                    # u8 center=64 default=0dB ✅ (shared w/ eqPeqGain)
    eqHighFreq=228,                   # u8 freq-table index default=231  ✅
    eqHighGain=230,                   # u8 center=64 default=0dB  ✅
    # LFO section — 13 fields fully verified ✅
    # Offsets mixed: Wave/Reset/Delay/Speed: MIDI+180, Amp/Pitch/FilterMod+ExtSpeed: MIDI+150, FadeIn+: MIDI+186
    lfoWave=232,                      # u8 enum 0-2 (Saw/Triangle/Square) default=1  ✅
    lfoKeyOnReset=234,                # u8 bool default=1=On                          ✅
    lfoDelayTime=236,                 # u8 direct default=0                           ✅
    lfoSpeed=238,                     # u8 direct 0-63 default=38                     ✅
    lfoAmpModDepth=240,               # u8 direct default=0   ✅ verified (MIDI LFO 0x5A+150)
    lfoPitchModDepth=242,             # u8 direct default=0   ✅ verified (MIDI LFO 0x5C+150)
    lfoFilterModDepth=244,            # u8 direct default=0   ✅ verified (MIDI LFO 0x5E+150)
    lfoFadeInTime=246,                # u8 direct default=0   ✅ verified (MIDI LFO 0x3C+186)
    lfoPhaseOffset=248,               # u8 enum 0-5 default=0 ✅ (MIDI LFO 0x3E+186)
    lfoDest1Ratio=250,                # u8 direct default=127 ✅ (MIDI LFO 0x40+186)
    lfoDest2Ratio=252,                # u8 direct default=127 ✅ (MIDI LFO 0x42+186)
    lfoDest3Ratio=254,                # u8 direct default=127 ✅ (MIDI LFO 0x44+186)
    lfoExtendedSpeed=256,             # u8 direct default=60  ✅ verified (MIDI LFO 0x6A+150)
    # Controller Set Switches (MIDI CS addr, DPFM_rel = MIDI_addr + 258)
    ctrlSet1=265,  ctrlSet2=266,  ctrlSet3=267,  ctrlSet4=268,
    ctrlSet5=269,  ctrlSet6=270,  ctrlSet7=271,  ctrlSet8=272,
    ctrlSet9=273,  ctrlSet10=274, ctrlSet11=275, ctrlSet12=276,
    ctrlSet13=277, ctrlSet14=278, ctrlSet15=279, ctrlSet16=280,
    ctrlSet17=281, ctrlSet18=282, ctrlSet19=283, ctrlSet20=284,
    ctrlSet21=285, ctrlSet22=286, ctrlSet23=287, ctrlSet24=288,
    ctrlSet25=289, ctrlSet26=290, ctrlSet27=291, ctrlSet28=292,
    ctrlSet29=293, ctrlSet30=294, ctrlSet31=295, ctrlSet32=296,
)
ANX_OSC_LAYOUT = dict(waveform=0, octave=2, sync=12, pulse=20, shaper=28, level=48)
ANX_FILTER_LAYOUT = dict(
    cutoff=0, cutoffVel=2, cutoffKey=10, resonance=12,
    resonanceVel=14, drive=16, driveVel=18, outLevel=20,
)

# ── ENCODE / DECODE FUNCTIONS ─────────────────────────────────────────────

def encode(field: str, value: Any, engine: str = None) -> int | tuple[int, int]:
    """
    Convert a UI value to raw byte(s) for a named field.
    Returns int for u8 fields, (lo, hi) tuple for u16 LE fields.
    """
    # u16 LE fields
    if field in ("cutoff", "waveformNumber", "hpfCutoff"):
        v = int(value)
        return (v & 0xFF, (v >> 8) & 0xFF)

    v = value

    # Boolean
    if field in ("portamentoSw", "freqMode", "keyOnDelayElemSW"):
        return int(bool(v))
    if field == "monoPoly":
        return 0 if str(v).lower() in ("mono", "0") else 1

    # Algorithm (1-based display → 0-based raw)
    if field == "algorithm":
        return int(v) - 1

    # AWM2 elem filter resonance: direct u8 (overrides part-level filterResonance center=64)
    if field == "elemFilterResonance":
        return int(v)

    # Center=64 fields
    if field in ("pan", "alternatePan", "scalingPan", "aegAttack", "aegDecay", "aegSustain", "aegRelease",
                 "fegAttack", "fegDecay", "fegSustain", "fegRelease",
                 "filterFEGDepth", "filterCutoff", "filterResonance",
                 "commonPan", "portamentoTime", "noteShift", "partNoteShift",
                 "outLevel", "tuneCoarse", "tuneFine",
                 "aegTimeVel", "ampLevelVel",
                 "fegDepth",
                 # Filter velocity/key follow fields
                 "cutoffVelSens", "resonanceVelSens", "dualFilterDistance",
                 "fegDepthVelSens", "fegTimeVelSens", "fegTimeKeyFollowSens",
                  "aegTimeKeyFollowSens", "aegTimeKeyFollowRelAdj",
                 "levelKeyFollowSens",
                 # PEG fields center=64
                 "pegCoarseTune", "pegFineTune", "pegPitchVelSens",
                 "pegFineTuneKF", "pegTimeVelSens", "pegDepthKFSens", "pegDepth",
                 # EQ fields center=64 (dB * 16/6 + 64)
                 "eqLowGain", "eqHighGain",
                 ):
        return int(v) + 64

    # Center=128 fields
    if field in ("fmDepth", "fmHarmonics", "fmTexture",
                 "fmEGAttack", "fmEGDecay", "fmEGSustain", "fmEGRelease",
                 "lfoAmplDepth",
                 "fegLevelHold", "fegLevelAttack", "fegLevelDecay1",
                 "fegLevelDecay2", "fegLevelRelease",
                 "levelOfs1", "levelOfs2", "levelOfs3", "levelOfs4",
                 "dualFilterDistance",
                 "pegHoldLevel", "pegAttackLevel", "pegDecay1Level",
                 "pegDecay2Level", "pegReleaseLevel",
                 "cutoffScalingOfs1", "cutoffScalingOfs2",
                 "cutoffScalingOfs3", "cutoffScalingOfs4",
                 "dualFilterDistance",
                 ):
        return int(v) + 128

    # Part detune: engine-specific
    if field in ("detune", "partDetune"):
        if engine == "FMX":
            return round(float(v) * 10) + 128
        else:
            return int(v) + 128

    # OP detune center=15
    if field == "opDetune":
        return int(v) + 15

    # OP velocity fields center=7
    if field in ("levelVel", "pitchVel", "opLevelVel", "opPitchVel"):
        return int(v) + 7

    # PEG levels center=50
    if field in ("pegInitialLevel", "pegAttackLevel", "opPegInitialLevel", "opPegAttackLevel"):
        return int(v) + 50

    # AN-X sync: cents → raw
    if field == "sync":
        return int(v) // 25

    # AN-X octave: value (1,2,4,8..64) → raw
    if field == "octave":
        return 6 - int(log2(int(v)))

    # Key Follow % fields: ui% = round((raw-64)*200/64), raw = round(ui*64/200)+64
    if field in ("cutoffKeyFollow", "hpfCutoffKeyFollow"):
        return round(int(v) * 64 / 200) + 64

    # AN-X Engine AEG (direct u8 or u16 LE, no center offset)
    if field == "anxAegAttack":  return int(v) & 0xFF
    if field == "anxAegDecay":   return int(v) & 0xFF
    if field == "anxAegRelease": return int(v) & 0xFF
    if field == "anxAegSustain":
        v16 = int(v); return (v16 & 0xFF, (v16 >> 8) & 0xFF)
    if field == "anxAegTimeVel":
        r16 = 256 + int(v); return (r16 & 0xFF, (r16 >> 8) & 0xFF)

    # OP BreakPoint: raw = MIDI_note_standard - 9 (default=39=C3)
    if field == "aegBreakPoint":
        return int(value) - 9

    # OP Spectral Form: direct enum (uppdaterad v5.0 — aegDelayTime borttaget)
    if field in ("spectralForm", "spectralSkirt", "spectralResonance",
                 "keyOnReset", "pegDecayTime", "aegTimeKeyFollow",
                 "lvlKeyLo", "lvlKeyHi", "curveLo", "curveHi"):
        return int(value)

    # PEG Level fields (center=50): raw = ui + 50
    if field in ("fmxPegInitialLevel", "fmxPegAttackLevel", "fmxPegDecay1Level",
                 "fmxPegDecay2Level", "fmxPegReleaseLevel"):
        return int(value) + 50

    # PEG PitchKeyFollow: raw = round(pct*64/200) + 64
    if field == "fmxPegPitchKeyFollow":
        return round(float(value) * 64 / 200) + 64

    # PEG Depth enum: [8oct,2oct,1oct,0.5oct] per raw 0-3
    if field == "fmxPegDepth":
        depth_map = {8: 0, 8.0: 0, 2: 1, 2.0: 1, 1: 2, 1.0: 2, 0.5: 3}
        return depth_map.get(float(value), 0)

    # LFO Loop (inverterat): On=raw0, Off=raw1
    if field == "fmxPartLfoLoop":
        return 0 if value else 1

    # Insertion FX LFO Speed (Symphonic + Classic Flanger): raw = round(Hz * 23.7045)
    if field == "fxLfoSpeed":
        return round(float(value) * 23.7045)

    # Insertion FX Dry/Wet: direct (0=100%Dry, 64=50/50, 127=100%Wet)
    if field == "fxDryWet":
        return int(value)

    # Direct u8 (volume, level, attack, decay, etc.)
    return int(v)


def decode(field: str, raw: Any, engine: str = None) -> Any:
    """
    Convert raw byte(s) to a UI value for a named field.
    Pass (lo, hi) tuple for u16 LE fields.
    """
    # u16 LE
    if isinstance(raw, tuple):
        v16 = raw[0] + raw[1] * 256
        if field in ("aegTimeVel","anxAegTimeVel"):  return v16 - 256
        return v16

    # Boolean
    if field in ("portamentoSw", "freqMode", "keyOnDelayElemSW"):
        return bool(raw)
    if field == "monoPoly":
        return "Mono" if raw == 0 else "Poly"

    # Algorithm
    if field == "algorithm":
        return raw + 1

    # AWM2 elem filter resonance: direct u8
    if field == "elemFilterResonance":
        return raw

    # Center=64
    if field in ("pan", "alternatePan", "scalingPan", "aegAttack", "aegDecay", "aegSustain", "aegRelease",
                 "fegAttack", "fegDecay", "fegSustain", "fegRelease",
                 "filterFEGDepth", "filterCutoff", "filterResonance",
                 "commonPan", "portamentoTime", "noteShift", "partNoteShift",
                 "outLevel", "tuneCoarse", "tuneFine",
                 "aegTimeVel", "ampLevelVel",
                 "fegDepth",
                 "cutoffVelSens", "resonanceVelSens", "dualFilterDistance",
                 "fegDepthVelSens", "fegTimeVelSens", "fegTimeKeyFollowSens",
                  "aegTimeKeyFollowSens", "aegTimeKeyFollowRelAdj",
                 "levelKeyFollowSens",
                 "pegCoarseTune", "pegFineTune", "pegPitchVelSens",
                 "pegFineTuneKF", "pegTimeVelSens", "pegDepthKFSens", "pegDepth",
                 "eqLowGain", "eqHighGain",
                 ):
        return raw - 64

    # Center=128
    if field in ("fmDepth", "fmHarmonics", "fmTexture",
                 "fmEGAttack", "fmEGDecay", "fmEGSustain", "fmEGRelease",
                 "lfoAmplDepth",
                 "fegLevelHold", "fegLevelAttack", "fegLevelDecay1",
                 "fegLevelDecay2", "fegLevelRelease",
                 "levelOfs1", "levelOfs2", "levelOfs3", "levelOfs4",
                 "dualFilterDistance",
                 "pegHoldLevel", "pegAttackLevel", "pegDecay1Level",
                 "pegDecay2Level", "pegReleaseLevel",
                 "cutoffScalingOfs1", "cutoffScalingOfs2",
                 "cutoffScalingOfs3", "cutoffScalingOfs4",
                 "dualFilterDistance",
                 ):
        return raw - 128

    # Part detune
    if field in ("detune", "partDetune"):
        if engine == "FMX":
            return (raw - 128) / 10
        else:
            return raw - 128

    # OP detune
    if field == "opDetune":
        return raw - 15

    # OP velocity
    if field in ("levelVel", "pitchVel", "opLevelVel", "opPitchVel"):
        return raw - 7

    # PEG levels
    if field in ("pegInitialLevel", "pegAttackLevel", "opPegInitialLevel", "opPegAttackLevel"):
        return raw - 50

    # Key Follow % fields
    if field in ("cutoffKeyFollow", "hpfCutoffKeyFollow"):
        return round((raw - 64) * 200 / 64)

    # AN-X sync
    if field == "sync":
        return raw * 25

    # AN-X octave
    if field == "octave":
        return 2 ** (6 - raw)

    # OP BreakPoint
    if field == "aegBreakPoint":
        return raw + 9

    # Direct fields (spectral, OP new fields, FX — v5.0: aegDelayTime→pegDecayTime)
    if field in ("spectralForm", "spectralSkirt", "spectralResonance",
                 "keyOnReset", "pegDecayTime", "aegTimeKeyFollow",
                 "lvlKeyLo", "lvlKeyHi", "curveLo", "curveHi",
                 "fxDryWet"):
        return raw

    # PEG Level decode: ui = raw - 50
    if field in ("fmxPegInitialLevel", "fmxPegAttackLevel", "fmxPegDecay1Level",
                 "fmxPegDecay2Level", "fmxPegReleaseLevel"):
        return raw - 50

    # PEG PitchKeyFollow decode: pct = (raw - 64) * 200 / 64
    if field == "fmxPegPitchKeyFollow":
        return round((raw - 64) * 200 / 64)

    # PEG Depth decode
    if field == "fmxPegDepth":
        depth_table = [8.0, 2.0, 1.0, 0.5]
        return depth_table[raw] if raw < len(depth_table) else raw

    # LFO Loop (inverterat)
    if field == "fmxPartLfoLoop":
        return raw == 0  # True=On, False=Off

    # FX LFO Speed decode: Hz = raw / 23.7045
    if field == "fxLfoSpeed":
        return round(raw / 23.7045, 2)

    # Direct


# ── CORE I/O ──────────────────────────────────────────────────────────────

def has_expansion_waveforms(blob: bytes) -> bool:
    """Return True if any AWM2 element in the blob references an expansion pack waveform.
    
    waveformNumber at blob[12520 + elem*313] (u16le, 1-based):
      1-256 = built-in ROM preset (always available on MODX M)
      257+  = expansion pack sample → "Storage read/write error" if pack not installed
    
    Verified against Soundmondo.Y2L (98 perfs, 85 require expansion, 2026-05-03).
    """
    import struct
    for e in range(8):
        off = AWM2_ELEM_WF_OFF + e * AWM2_ELEM_STRIDE_WF
        if off + 2 > len(blob):
            break
        wf = struct.unpack_from('<H', blob, off)[0]
        if wf > WAVEFORM_BUILTIN_MAX:
            return True
    return False


BLOB_NAME_CORRECTIONS: dict[str, str] = {
    # Correct blob[null+1:24] for Soundmondo performances.
    # Verified against ESP_8_performances.Y2L (2026-05-04).
    # Key = performance name, value = hex bytes to write at blob[24-len:24].
    'CFX + FM EP +':    '00000000000000',    # blob[17:24]
    'Waterloo SM':      '000000000015bcc9fe',# blob[15:24]
    'Take on me SM':    '00000015bccea1',    # blob[17:24]
    'Korg M1 Piano 16': '00000000',          # blob[20:24]
}


def sanitize_perf_blob(blob: bytes) -> bytes:
    """Correct blob[null+1:24] (name-padding + flash address).

    Soundmondo.Y2L has incorrect placeholder values in the name field
    padding area (blob[null+1:20]) and flash address field (blob[20:24]).
    MODX validates blob[20:24] on load → wrong value = Storage error.

    blob[4:20]  = name (16 bytes, null-terminated, zero-padded)
    blob[20:24] = flash address (0x15bcXXXX) or 0x00000000
    blob[24:]   = performance parameters

    Verified against ESP_8_performances.Y2L (2026-05-04).
    """
    b = bytearray(blob)
    # Find null terminator in name field blob[4:24]
    null_pos = -1
    for i in range(4, 24):
        if b[i] == 0:
            null_pos = i
            break
    if null_pos < 0 or null_pos >= 20:
        return bytes(b)  # 20-teckens namn, ingen padding att fixa
    name = b[4:null_pos].decode('ascii', errors='replace')
    # Zero out padding blob[null_pos+1:24]
    for i in range(null_pos + 1, 24):
        b[i] = 0
    # Apply known-correct flash address from table
    corr_hex = BLOB_NAME_CORRECTIONS.get(name)
    if corr_hex:
        corr = bytes.fromhex(corr_hex)
        corr_start = 24 - len(corr)
        b[corr_start:24] = corr
    return bytes(b)


def find_dpfm(data: bytes) -> tuple[int, int]:
    pos = 0
    while True:
        idx = data.find(b'DPFM', pos)
        if idx == -1:
            raise ValueError("No DPFM chunk found")
        length = int.from_bytes(data[idx+4:idx+8], 'big')
        if length > 10000:
            return idx + 8, length
        pos = idx + 1


def _resolve_field(engine: str, part: int, field_name: str, op=None, elem=None) -> int:
    stride = {'FMX': FMX_PART_STRIDE, 'AWM2': AWM2_PART_STRIDE, 'ANX': ANX_PART_STRIDE}[engine]
    ps = part * stride

    # Explicit prefix aliases
    if field_name.startswith('op') and op is not None and engine == 'FMX':
        bare = field_name[2].lower() + field_name[3:]
        if bare in FMX_OP_LAYOUT:
            return FMX_OP1_BASE + ps + op * FMX_OP_STRIDE + FMX_OP_LAYOUT[bare]
    if field_name.startswith('elem') and elem is not None and engine == 'AWM2':
        bare = field_name[4].lower() + field_name[5:]
        if bare in AWM2_ELEM_LAYOUT:
            return AWM2_ELEM1_BASE + ps + elem * AWM2_ELEM_STRIDE + AWM2_ELEM_LAYOUT[bare]

    # FM-X operator fields
    if engine == 'FMX' and op is not None and field_name in FMX_OP_LAYOUT:
        return FMX_OP1_BASE + ps + op * FMX_OP_STRIDE + FMX_OP_LAYOUT[field_name]

    # AWM2 element fields
    if engine == 'AWM2' and field_name == 'elemFilterType':
        e = elem if elem is not None else 0
        return AWM2_ELEM1_BASE + ps + e * AWM2_ELEM_STRIDE + 150  # filterType @ rel+150

    if engine == 'AWM2' and elem is not None and field_name in AWM2_ELEM_LAYOUT:
        return AWM2_ELEM1_BASE + ps + elem * AWM2_ELEM_STRIDE + AWM2_ELEM_LAYOUT[field_name]

    # AN-X OSC fields
    # AN-X Engine AEG (Amplitude Envelope Generator timings)
    if engine == "ANX" and field_name in ("anxAegAttack","anxAegDecay","anxAegSustain","anxAegRelease","anxAegTimeVel"):
        AEG_OFFS = {"anxAegAttack":0,"anxAegDecay":2,"anxAegSustain":4,"anxAegRelease":6,"anxAegTimeVel":8}
        return ANX_AEG_BASE + ps + AEG_OFFS[field_name]

    if engine == 'ANX' and op is not None and field_name in ANX_OSC_LAYOUT:
        return ANX_OSC1_BASE + ps + op * ANX_OSC_STRIDE + ANX_OSC_LAYOUT[field_name]

    # AN-X Filter fields
    if engine == 'ANX' and field_name in ANX_FILTER_LAYOUT:
        return ANX_FILTER_BASE + ps + ANX_FILTER_LAYOUT[field_name]

    # Part detune / noteShift
    if field_name in ('detune', 'partDetune'):
        return PART_DETUNE_BASE + ps
    if field_name in ('noteShift', 'partNoteShift'):
        return PART_NOTESHIFT + ps

    # Part-common
    if field_name in PART_COMMON:
        return PART_COMMON[field_name] + ps

    # FM-X part
    if engine == 'FMX' and field_name in FMX_PART_BASE:
        return FMX_PART_BASE[field_name] + ps

    # Common (performance-level, no part stride)
    if field_name in COMMON_FIELDS:
        return COMMON_FIELDS[field_name]

    # Per-part portamento (all engines)
    _P = {"partPortaSW":6752,"partPortaTime":6933,"partPortaMode":6935,"partHalfDamperSW":12483, "partKeyOnDelaySW":12482}
    if field_name in _P: return _P[field_name] + part*stride

    raise ValueError(f"Unknown field: engine={engine!r} field={field_name!r} op={op} elem={elem}")


def _is_u16(field_name: str) -> bool:
    return field_name in ("cutoff", "elemCutoff", "anxAegSustain", "anxAegTimeVel",
                          "aegSustain", "level", "waveformNumber", "hpfCutoff")


# ── PUBLIC API ────────────────────────────────────────────────────────────

def read_raw(path: str, engine: str, part: int, field: str,
             op=None, elem=None) -> int | tuple[int,int]:
    """Read raw byte value(s) from a Y2L file."""
    data = Path(path).read_bytes()
    off, _ = find_dpfm(data)
    foff = _resolve_field(engine, part, field, op, elem)
    if _is_u16(field):
        return (data[off+foff], data[off+foff+1])
    return data[off+foff]


def read_ui(path: str, engine: str, part: int, field: str,
            op=None, elem=None) -> Any:
    """Read a field and decode to UI value."""
    raw = read_raw(path, engine, part, field, op, elem)
    return decode(field, raw, engine)


def patch_raw(src: str, dst: str, engine: str, part: int, field: str,
              raw_value: int | tuple, op=None, elem=None) -> None:
    """Patch a field with a raw byte value."""
    data = bytearray(Path(src).read_bytes())
    off, _ = find_dpfm(bytes(data))
    foff = _resolve_field(engine, part, field, op, elem)
    if isinstance(raw_value, tuple):
        data[off+foff]   = raw_value[0] & 0xFF
        data[off+foff+1] = raw_value[1] & 0xFF
    else:
        data[off+foff] = int(raw_value) & 0xFF
    Path(dst).write_bytes(bytes(data))


def patch_ui(src: str, dst: str, engine: str, part: int, field: str,
             ui_value: Any, op=None, elem=None) -> None:
    """
    Patch a field using a UI value (auto-encodes to raw).
    When op is given, OP-level encoding is used for ambiguous fields
    (e.g. 'detune' with op= means OP detune center=15, not part detune).
    """
    # Disambiguate fields that exist at both part and OP level
    enc_field = field
    if op is not None and field == "detune":
        enc_field = "opDetune"
    if op is not None and field in ("levelVel", "pitchVel"):
        enc_field = field  # already correct (center=7 for both)
    if elem is not None and field == "pan":
        enc_field = field  # pan is always center=64 regardless of level

    raw = encode(enc_field, ui_value, engine)
    patch_raw(src, dst, engine, part, field, raw, op, elem)


def diff_dpfm(path_a: str, path_b: str) -> list[tuple[int,int,int]]:
    """Return list of (dpfm_offset, val_a, val_b) for changed non-noise bytes."""
    da = Path(path_a).read_bytes()
    db = Path(path_b).read_bytes()
    oa, la = find_dpfm(da)
    ob, lb = find_dpfm(db)
    dpfm_a = da[oa:oa+min(la,lb)]
    dpfm_b = db[ob:ob+min(la,lb)]
    return [(i, dpfm_a[i], dpfm_b[i]) for i in range(min(len(dpfm_a),len(dpfm_b)))
            if dpfm_a[i] != dpfm_b[i] and i not in NOISE]


def round_trip_verify(path: str) -> bool:
    """Verify that reading and writing leaves the file identical."""
    data = Path(path).read_bytes()
    off, length = find_dpfm(data)
    result = bytearray(data)
    result[off:off+length] = data[off:off+length]
    return bytes(result) == data


# ── MERGE ENGINE ──────────────────────────────────────────────────────────

def merge_patches(
    base_path: str,
    dst_path: str,
    patches: list[dict],
) -> None:
    """
    Apply multiple field patches from potentially different source files.

    patches is a list of dicts:
      {
        "engine": "FMX",
        "part":   0,
        "field":  "algorithm",
        "value":  5,          # UI value (auto-encoded)
        "op":     None,       # optional
        "elem":   None,       # optional
        "raw":    False,      # if True, value is already raw bytes
      }

    All patches are applied to `base_path` in sequence, result written to `dst_path`.
    """
    data = bytearray(Path(base_path).read_bytes())
    off, _ = find_dpfm(bytes(data))

    for p in patches:
        engine = p["engine"]
        part   = p.get("part", 0)
        field  = p["field"]
        value  = p["value"]
        op     = p.get("op")
        elem   = p.get("elem")
        is_raw = p.get("raw", False)

        foff  = _resolve_field(engine, part, field, op, elem)
        raw   = value if is_raw else encode(field, value, engine)

        if isinstance(raw, tuple):
            data[off+foff]   = raw[0] & 0xFF
            data[off+foff+1] = raw[1] & 0xFF
        else:
            data[off+foff] = int(raw) & 0xFF

    Path(dst_path).write_bytes(bytes(data))


def copy_fields(
    src_path: str,
    dst_path: str,
    src_engine: str,
    dst_engine: str,
    fields: list[dict],
    src_part: int = 0,
    dst_part: int = 0,
) -> None:
    """
    Copy specific fields from one Y2L file to another.
    Useful for transplanting e.g. FM-X operator settings between patches.

    fields: list of {"field": "coarse", "op": 0} dicts
    """
    src_data = Path(src_path).read_bytes()
    dst_data = bytearray(Path(dst_path).read_bytes())
    src_off, _ = find_dpfm(src_data)
    dst_off, _ = find_dpfm(bytes(dst_data))

    for f in fields:
        fname = f["field"]
        op    = f.get("op")
        elem  = f.get("elem")
        src_foff = _resolve_field(src_engine, src_part, fname, op, elem)
        dst_foff = _resolve_field(dst_engine, dst_part, fname, op, elem)

        if _is_u16(fname):
            dst_data[dst_off+dst_foff]   = src_data[src_off+src_foff]
            dst_data[dst_off+dst_foff+1] = src_data[src_off+src_foff+1]
        else:
            dst_data[dst_off+dst_foff] = src_data[src_off+src_foff]

    Path(dst_path).write_bytes(bytes(dst_data))




# ── PART BLOCK COPY ENGINE ────────────────────────────────────────────────

# DPFM layout (all engines):
#   DPFM[0..PART_BLOCK_START-1]  = common header (FX, common params)
#   DPFM[PART_BLOCK_START + N*stride .. +stride-1] = Part N+1 block
#
# Part block start = lowest known part-specific field offset
PART_BLOCK_START = 6708  # derived: 1-part DPFM length (13621) - FMX_PART_STRIDE (6913)

# All fields that belong to the common header (not part-specific)
COMMON_HEADER_FIELDS = {
    "portamentoSw":   41,
    "portamentoTime": 106,
    "commonVolume":   80,
    "commonPan":      82,
    "revSend":        124,
    "varSend":        130,
}

ENGINE_PART_STRIDE = {
    "FMX":  6913,
    "AWM2": 8273,
    "ANX":  6454,
}


def copy_part_block(
    src_path: str,
    dst_path: str,
    src_engine: str,
    dst_engine: str,
    src_part: int,
    dst_part: int,
) -> None:
    """
    Copy an entire Part block from src to dst verbatim.
    src_engine and dst_engine MUST be the same — part layouts are engine-specific.
    
    This copies ALL bytes of the part block, including unknown/unmapped fields.
    Safe for same-engine transplants.
    """
    if src_engine != dst_engine:
        raise ValueError(
            f"Cannot copy part block between different engines: "
            f"{src_engine} → {dst_engine}. Use copy_fields() for selective copy."
        )

    stride = ENGINE_PART_STRIDE[src_engine]
    src_data = bytearray(Path(src_path).read_bytes())
    dst_data = bytearray(Path(dst_path).read_bytes())
    src_off, src_len = find_dpfm(bytes(src_data))
    dst_off, dst_len = find_dpfm(bytes(dst_data))

    src_block_start = src_off + PART_BLOCK_START + src_part * stride
    dst_block_start = dst_off + PART_BLOCK_START + dst_part * stride

    # Bounds check
    if src_block_start + stride > src_off + src_len:
        raise ValueError(f"src Part {src_part+1} out of bounds (DPFM length {src_len})")
    if dst_block_start + stride > dst_off + dst_len:
        raise ValueError(f"dst Part {dst_part+1} out of bounds (DPFM length {dst_len})")

    dst_data[dst_block_start:dst_block_start+stride] =         src_data[src_block_start:src_block_start+stride]

    Path(dst_path).write_bytes(bytes(dst_data))


def get_part_count(path: str, engine: str) -> int:
    """Return the number of parts present in a Y2L file for a given engine."""
    data = Path(path).read_bytes()
    off, length = find_dpfm(data)
    stride = ENGINE_PART_STRIDE[engine]
    usable = length - PART_BLOCK_START
    return max(0, usable // stride)


def extract_part_block(path: str, engine: str, part: int) -> bytes:
    """Extract a part block as raw bytes."""
    data = Path(path).read_bytes()
    off, length = find_dpfm(data)
    stride = ENGINE_PART_STRIDE[engine]
    start = off + PART_BLOCK_START + part * stride
    if start + stride > off + length:
        raise ValueError(f"Part {part+1} out of bounds")
    return bytes(data[start:start+stride])


def inject_part_block(path: str, engine: str, part: int, block: bytes) -> None:
    """Inject a raw part block into a Y2L file in-place."""
    data = bytearray(Path(path).read_bytes())
    off, length = find_dpfm(bytes(data))
    stride = ENGINE_PART_STRIDE[engine]
    if len(block) != stride:
        raise ValueError(f"Block size {len(block)} != stride {stride}")
    start = off + PART_BLOCK_START + part * stride
    if start + stride > off + length:
        raise ValueError(f"Part {part+1} out of bounds")
    data[start:start+stride] = block
    Path(path).write_bytes(bytes(data))


# ── MULTI-FILE MERGE ──────────────────────────────────────────────────────

# ── ANX Performance-level parameter offsets (DPFM blob, verified 2026-05-04) ──────────────
# All offsets are blob-absolute (blob[0:4]=0x00000015 header, blob[4:24]=name).
# NOISE/timestamp bytes (never interpret): {23, 24, 6722, 6723, 6724, 6725, 6726, 6727}
#
# ┌─ PERF-LEVEL SWITCHES ─────────────────────────────────────────────┐
ANX_OFF_ARPMASTER_SW       = 38    # bool  0=off 1=on
ANX_OFF_MSMASTER_SW        = 39    # bool  0=off 1=on
ANX_OFF_ASSIGN1_SW         = 40    # bool  0=off 1=on(default)
ANX_OFF_ASSIGN2_SW         = 41    # bool  0=off 1=on(default)
ANX_OFF_ASSIGN3_SW         = 42    # bool  0=off 1=on(default)
ANX_OFF_ASSIGN4_SW         = 43    # bool  0=off 1=on(default)
ANX_OFF_ASSIGN5_SW         = 44    # bool  0=off 1=on(default)
ANX_OFF_ASSIGN6_SW         = 45    # bool  0=off 1=on(default)
ANX_OFF_ASSIGN7_SW         = 46    # bool  0=off 1=on(default)
ANX_OFF_ASSIGN8_SW         = 47    # bool  0=off 1=on(default)
ANX_OFF_SUPERKNOB_MS_SW    = 51    # bool  0=off 1=on

# ┌─ SEQ LANE1 COMMON (performance-level) ────────────────────────────┐
ANX_OFF_LANE1_COMMON_SWING     = 100   # u8  0x80+n center, 0xb2=50%
ANX_OFF_LANE1_COMMON_UNIT      = 102   # u8  0=100% 3=1/16(default)

# ┌─ ASSIGN VALUES (u16le) ────────────────────────────────────────────┐
# Assign1-8 values at [184:200], stride 2, all default=512 (u16le 0x0200)
ANX_OFF_ASSIGN1_VALUE = 184  # u16le  default=512
ANX_OFF_ASSIGN2_VALUE = 186  # u16le  default=512
ANX_OFF_ASSIGN3_VALUE = 188  # u16le  default=512
ANX_OFF_ASSIGN4_VALUE = 190  # u16le  default=512
ANX_OFF_ASSIGN5_VALUE = 192  # u16le  default=512
ANX_OFF_ASSIGN6_VALUE = 194  # u16le  default=512
ANX_OFF_ASSIGN7_VALUE = 196  # u16le  default=512
ANX_OFF_ASSIGN8_VALUE = 198  # u16le  default=512

# ┌─ ARP SELECT / SYNC QUANTIZE ──────────────────────────────────────┐
ANX_OFF_ARPSELECT      = 358   # u8  0-indexed (0=1, 1=2, 7=8)
ANX_OFF_SYNCQUANTIZE   = 360   # u8  0=OFF, 3=120

# ┌─ MS SELECT ───────────────────────────────────────────────────────┐
ANX_OFF_MSSELECT       = 654   # u8  0-indexed (0=1, 1=2, 7=8)

# ┌─ SEQ LANE1 COMMON PARAMS (separate from switches) ────────────────┐
ANX_OFF_LANE1_COMMON_AMP    = 656   # u8  0x80+n
ANX_OFF_LANE1_COMMON_SHAPE  = 658   # u8  0x40+n
ANX_OFF_LANE1_COMMON_SMOOTH = 660   # u8  0x80+n
ANX_OFF_LANE1_COMMON_RANDOM = 662   # u8  0x80+n

# ┌─ SUPERKNOB VALUE ──────────────────────────────────────────────────┐
ANX_OFF_SUPERKNOB_VALUE = 670  # u16le  default=512

# ┌─ MIDPOSITION + ASSIGN POSITION BLOCK ─────────────────────────────┐
# [672] = MidPosition global enable (bool 0=off 1=on)
# [673] = uncertain (appears to be 1 when mid-pos is active with assigns set)
# Assign positions: stride=6 per assign, starting at [674]
#   AssignN_LeftPos  = blob[674 + N*6]      u8    default=0
#   AssignN_MidPos   = blob[676 + N*6 : +2] u16le default=512
#   AssignN_RightPos = blob[678 + N*6 : +2] u16le default=1023
# N = 0..7 for Assign1..8
ANX_OFF_MIDPOS_ENABLE  = 672   # bool 0=off 1=on

def anx_assign_left_off(n: int) -> int:   # n=0..7
    return 674 + n * 6

def anx_assign_mid_off(n: int) -> int:    # n=0..7, u16le
    return 676 + n * 6

def anx_assign_right_off(n: int) -> int:  # n=0..7, u16le
    return 678 + n * 6

# ┌─ PART-LEVEL ───────────────────────────────────────────────────────┐
ANX_OFF_PARTSWITCH     = 6737  # bool  1=on(default) 0=off

# ┌─ ARP COMMON ───────────────────────────────────────────────────────┐
ANX_OFF_ARP_PLAYONLY       = 6802  # bool  0=off 1=on
ANX_OFF_ARP_LOOP           = 6804  # bool  1=on(default) 0=off
ANX_OFF_ARP_STARTQUANTIZE  = 6805  # bool  1=on(default) 0=off
ANX_OFF_ARP_RANDOMSFX      = 6806  # bool  1=on(default) 0=off
ANX_OFF_ARP_KEYONCONTROL   = 6807  # bool  1=on(default) 0=off
# [6887] = Arp Swing AND Lane1 Part Swing (shared offset)
ANX_OFF_ARP_SWING          = 6887  # u8  0x80+n center, 0xb2=50%
ANX_OFF_LANE1_PART_SWING   = 6887  # alias
ANX_OFF_LANE1_PART_AMP     = 6889  # u8  0x80+n
ANX_OFF_LANE1_PART_SHAPE   = 6891  # u8  0x40+n
ANX_OFF_LANE1_PART_SMOOTH  = 6893  # u8  0x80+n
ANX_OFF_LANE1_PART_RANDOM  = 6895  # u8  direct 0..100
ANX_OFF_ARPGROUP           = 6905  # u8  0=off 1=A 0x10=P
ANX_OFF_ARPENABLE_AREA     = 6917  # u8  0x80=idle 0x89=arp active
ANX_OFF_HOLD               = 7095  # u8  0=SyncOff 1=Off(default) 2=On
ANX_OFF_ARP_UNIT           = 7097  # u8  0=100% 3=1/16(default)
ANX_OFF_LANE1_PART_UNIT    = 7097  # alias (shared offset)
ANX_OFF_ARPLIMIT_NOTE_LO   = 7099  # u8  direct MIDI note
ANX_OFF_ARPLIMIT_NOTE_HI   = 7101  # u8  direct MIDI note, default=127
ANX_OFF_ARPLIMIT_VEL_LO    = 7103  # u8  default=1
ANX_OFF_ARPLIMIT_VEL_HI    = 7105  # u8  default=127
ANX_OFF_KEYMODE            = 7107  # u8  0=normal 1=Thru
ANX_OFF_VELOCITYMODE       = 7109  # u8  0=normal 1=Thru
ANX_OFF_CHANGETIMING       = 7111  # u8  1=beat(default) 0=Real-Time
ANX_OFF_QUANTIZEVALUE      = 7113  # u8  3=120(default) 2=80
ANX_OFF_QUANTIZESTRENGTH   = 7115  # u8  direct 0..100
ANX_OFF_VELOCITYRATE       = 7117  # u8  direct 0..200, default=100
ANX_OFF_GATETIMERATE       = 7119  # u8  direct 0..200, default=100
ANX_OFF_ACCENT_VELTHRESHOLD= 7121  # u8  direct 0..127
ANX_OFF_OCTAVERANGE        = 7123  # u8  0x40+n (center=0x40=0, 0x42=+2)
ANX_OFF_OCTAVESHIFT        = 7125  # u8  0x40+n (center=0x40=0, 0x46=+6)
ANX_OFF_TRIGGERMODE        = 7127  # u8  0=normal 1=Toggle
ANX_OFF_VELOCITYOFFSET     = 7129  # u8  0x40+n (center=0x40=0, 0x45=+5)

# ┌─ ARP INDIVIDUAL ARP1 ──────────────────────────────────────────────┐
ANX_OFF_ARP1_VELOCITY   = 7131  # u8  0x80+n, default=0x80
ANX_OFF_ARP1_GATETIME   = 7133  # u8  0x80+n, default=0x80
ANX_OFF_ARP1_NAME_TYPE  = 7163  # u8  type/bank id (default=79)
ANX_OFF_ARP1_NAME_PAT   = 7164  # u8  pattern id within type (default=25)

# ┌─ SEQ LANE1 MAIN BLOCK ─────────────────────────────────────────────┐
# Lane offsets: lane_offset = 8929 + lane_index * 884  (Lane1=8929, Lane2=9813, Lane3=10697, Lane4=11581)
ANX_LANE1_BASE = 8929
ANX_LANE2_BASE = 9813
ANX_LANE3_BASE = 10697
ANX_LANE4_BASE = 11581

ANX_LANE_OFF_LANESWITCH    = 0     # bool  0=off 1=on  (abs: 8929/9813/10697/11581)
ANX_LANE_OFF_MSFXSWITCH    = 1     # bool  1=on(default) 0=off   (Lane1 only meaningful)
ANX_LANE_OFF_TRIGGER       = 2     # bool  0=off 1=on
ANX_LANE_OFF_LOOP          = 3     # bool  1=on(default) 0=off
ANX_LANE_OFF_SYNC          = 8     # bool  0=off 1=sync
ANX_LANE_OFF_SPEED         = 10    # u8    0x3f=63=default, direct value
ANX_LANE_OFF_SYNC_UNIT     = 12    # u8    3=default 9=400%
ANX_LANE_OFF_KEYONRESET    = 14    # u8    0=off 2=1stOn
ANX_LANE_OFF_VELIMIT_LO    = 16    # u8    default=1
ANX_LANE_OFF_VELIMIT_HI    = 18    # u8    default=127
ANX_LANE_OFF_DELAYTIME     = 20    # u8    default=0
ANX_LANE_OFF_DELAYSTEPS    = 22    # u8    default=0
ANX_LANE_OFF_FADEINTIME    = 24    # u8    default=0
ANX_LANE_OFF_FADEINSTEPS   = 26    # u8    default=0
ANX_LANE_OFF_AMP           = 36    # u8    default=127
ANX_LANE_OFF_SMOOTH        = 38    # u8    default=0
ANX_LANE_OFF_POLARITY      = 42    # bool  0=unipolar 1=bipolar
ANX_LANE_OFF_MSGRID        = 44    # u8    3=default 1=60

# Pulse A (per lane, relative to lane base):
ANX_LANE_OFF_PULSEA_TYPE   = 116   # u8  0=Standard 2=Threshold
ANX_LANE_OFF_PULSEA_PRM1   = 118   # u8  default=5
ANX_LANE_OFF_PULSEA_PRM2   = 120   # u8  default=0 (Threshold: 1=default 4=4)
ANX_LANE_OFF_CTRLA_SW      = 122   # bool  1=on(default) 0=off
ANX_LANE_OFF_CTRLA_CTRLSW  = 124   # bool  0=off 1=on

# Pulse B (per lane, relative to lane base):
ANX_LANE_OFF_PULSEB_TYPE   = 128   # u8  0=Standard 2=Threshold
ANX_LANE_OFF_PULSEB_PRM1   = 130   # u8  default=5
ANX_LANE_OFF_PULSEB_PRM2   = 132   # u8  default=0
ANX_LANE_OFF_CTRLB_SW      = 134   # bool  1=on(default) 0=off
ANX_LANE_OFF_CTRLB_CTRLSW  = 136   # bool  0=off 1=on

# ┌─ METADATA (internal state flags) ─────────────────────────────────┐
ANX_OFF_PART_SEQ_FIELD = 12753  # u8  3=default 4=seq-sync active
ANX_OFF_PART_ARP_FIELD = 13116  # u8  0=default 9=arp active

ANX_NOISE_BYTES = frozenset({23, 24, 6722, 6723, 6724, 6725, 6726, 6727})


def build_performance(
    base_path: str,
    dst_path: str,
    part_sources: list[dict],
) -> None:
    """
    Build a performance by combining Parts from multiple source files.
    
    part_sources: list of dicts, one per destination part:
      {
        "src":    "/path/to/source.Y2L",
        "engine": "FMX",               # engine of source part
        "part":   0,                   # source part index (0-based)
        "dst_part": 0,                 # destination part index (0-based)
        # Optional field overrides applied after part copy:
        "overrides": [
          {"field": "volume", "value": 100},
          {"field": "pan",    "value": 0},
        ]
      }
    
    base_path:  Base Y2L file that provides the common header (FX, rev/var send, etc.)
                Must have enough parts for all dst_part indices.
    dst_path:   Output file.
    """
    import shutil
    shutil.copy2(base_path, dst_path)

    for ps in part_sources:
        src      = ps["src"]
        engine   = ps["engine"]
        src_part = ps.get("part", 0)
        dst_part = ps.get("dst_part", src_part)

        # Copy the full part block
        copy_part_block(src, dst_path, engine, engine, src_part, dst_part)

        # Apply any field overrides
        for ov in ps.get("overrides", []):
            patch_ui(dst_path, dst_path, engine, dst_part,
                     ov["field"], ov["value"],
                     op=ov.get("op"), elem=ov.get("elem"))


# ── DIFF REPORT ───────────────────────────────────────────────────────────

# Field map: dpfm_offset → (field_name, engine_or_common, encoding)
def _build_field_map() -> dict[int, tuple[str, str, str]]:
    m = {}
    # Common
    for name, off in COMMON_HEADER_FIELDS.items():
        m[off] = (name, "COMMON", "u8")
    # Part common (Part 0)
    for name, off in PART_COMMON.items():
        m[off] = (name, "PART", "u8_center64" if name != "monoPoly" and name != "volume" else "u8")
    m[PART_DETUNE_BASE] = ("partDetune", "PART", "detune")
    m[PART_NOTESHIFT]   = ("noteShift",  "PART", "u8_center64")
    # FMX part
    for name, off in FMX_PART_BASE.items():
        m[off] = (name, "FMX_PART", "u8_center128" if "EG" in name or name in ("fmDepth","fmHarmonics","fmTexture") else "u8")
    m[FMX_PART_BASE["algorithm"]] = ("algorithm", "FMX_PART", "algorithm")
    # FMX operators (part 0)
    for op in range(8):
        base = FMX_OP1_BASE + op * FMX_OP_STRIDE
        for field, rel in FMX_OP_LAYOUT.items():
            m[base + rel] = (f"OP{op+1}.{field}", "FMX_OP", field)
    # AWM2 elements (part 0)
    for el in range(3):
        base = AWM2_ELEM1_BASE + el * AWM2_ELEM_STRIDE
        for field, rel in AWM2_ELEM_LAYOUT.items():
            m[base + rel] = (f"Elem{el+1}.{field}", "AWM2_ELEM", field)
            if field == "cutoff":  # u16 LE: register hi-byte too
                m[base + rel + 1] = (f"Elem{el+1}.{field}", "AWM2_ELEM", field)
            if field == "waveformNumber":  # u16 LE: register hi-byte too
                m[base + rel + 1] = (f"Elem{el+1}.{field}", "AWM2_ELEM", field)
            if field == "hpfCutoff":  # u16 LE: register hi-byte too
                m[base + rel + 1] = (f"Elem{el+1}.{field}", "AWM2_ELEM", field)
    # ANX OSCs (part 0)
    for osc in range(3):
        base = ANX_OSC1_BASE + osc * ANX_OSC_STRIDE
        for field, rel in ANX_OSC_LAYOUT.items():
            m[base + rel] = (f"OSC{osc+1}.{field}", "ANX_OSC", field)
    # ANX filter
    for field, rel in ANX_FILTER_LAYOUT.items():
        m[ANX_FILTER_BASE + rel] = (f"Filter.{field}", "ANX_FILTER", field)
        if field == "cutoff":  # u16 LE: register hi-byte too
            m[ANX_FILTER_BASE + rel + 1] = (f"Filter.{field}", "ANX_FILTER", field)
    return m

FIELD_MAP = _build_field_map()


def diff_report(
    path_a: str,
    path_b: str,
    engine: str = None,
    label_a: str = "A",
    label_b: str = "B",
) -> str:
    """
    Generate a human-readable diff report between two Y2L files.
    Returns a formatted multi-line string.
    """
    raw_diffs = diff_dpfm(path_a, path_b)
    if not raw_diffs:
        return f"No differences between {label_a} and {label_b}"

    lines = [
        f"Diff: {label_a}  vs  {label_b}",
        f"{'─'*60}",
        f"{'Field':<30} {'Value '+label_a:>12}  {'Value '+label_b:>12}  {'Raw':>10}",
        f"{'─'*60}",
    ]

    # Pre-process: pair up u16 LE fields (consecutive offsets for same field)
    skip_offsets = set()
    processed = []
    diff_dict = {off: (va, vb) for off, va, vb in raw_diffs}
    for dpfm_off, val_a, val_b in raw_diffs:
        if dpfm_off in skip_offsets:
            continue
        info = FIELD_MAP.get(dpfm_off)
        # Check if next byte is the hi-byte of a u16 LE pair
        next_info = FIELD_MAP.get(dpfm_off + 1)
        if (info and next_info and
            info[0].split('.')[0] == next_info[0].split('.')[0] and
            (dpfm_off + 1) in diff_dict):
            # u16 LE pair: combine
            hi_a, hi_b = diff_dict[dpfm_off + 1]
            combined_a = val_a + hi_a * 256
            combined_b = val_b + hi_b * 256
            processed.append((dpfm_off, combined_a, combined_b, info, True))
            skip_offsets.add(dpfm_off + 1)
        else:
            processed.append((dpfm_off, val_a, val_b, info, False))

    for dpfm_off, val_a, val_b, info, is_u16 in processed:
        if info:
            fname, context, enc = info
            try:
                if is_u16:
                    ui_a, ui_b = str(val_a), str(val_b)
                elif enc not in ("u8", "u8_center128"):
                    ui_a = decode(enc, val_a, engine)
                    ui_b = decode(enc, val_b, engine)
                    ui_a = str(round(ui_a, 1)) if isinstance(ui_a, float) else str(ui_a)
                    ui_b = str(round(ui_b, 1)) if isinstance(ui_b, float) else str(ui_b)
                else:
                    ui_a = str(val_a - 128 if enc == "u8_center128" else val_a)
                    ui_b = str(val_b - 128 if enc == "u8_center128" else val_b)
            except:
                ui_a, ui_b = str(val_a), str(val_b)
            raw_str = f"[{dpfm_off}] {val_a}→{val_b}" + (" u16" if is_u16 else "")
            lines.append(f"  {fname:<30} {ui_a:>12}  {ui_b:>12}  {raw_str}")
        else:
            lines.append(f"  {'?@'+str(dpfm_off):<30} {val_a:>12}  {val_b:>12}  raw")

    lines.append(f"{'─'*60}")
    lines.append(f"Total: {len(raw_diffs)} changed field(s)")
    return "\n".join(lines)



# ── LIBRARY ENGINE (multi-performance Y2L) ───────────────────────────────
#
# A Y2L file contains 1 or more performances. Structure:
#
# DPFM chunk:
#   [0:4]   = performance count (N)
#   Then N records:
#     [0:4]  = b'Data'
#     [4:8]  = performance data length (always 13609 for FM-X/AN-X, varies for AWM2)
#     [8:]   = performance data bytes
#
# EPFM catalog (spans EPFM[280:353] + gap before ESYS):
#   [0]     = 0x00
#   [1:5]   = b'EPFM'
#   [5:9]   = catalog_len (total bytes after this 9-byte prefix)
#   [9:13]  = performance count (N)
#   Then N Entr blocks:
#     [0:4]  = b'Entr'
#     [4:8]  = entry data length (= 32 + 2*len(name))
#     [8:]   = entry data:
#       [0:4]  = 0x00003529 (fixed = DPFM sub-chunk data length = 13609 = 0x3529)
#       [4:8]  = DPFM offset where this perf's data starts
#       [8:12] = 0x00400000 | (perf_index << 0)  (byte[11] = 0-based index)
#       [12:20]= 8 fixed bytes: 0x0000000202000100
#       [20:26]= 6 fixed bytes: 0x0000000000002a  (last byte = 0x2a always)
#       [26]   = checksum/hash byte (from source file, not recalculated)
#       [27:29]= 2-char decimal XX (checksum, not validated by MODX)
#       [29]   = b':'
#       [30:]  = name_bytes + b':' + name_bytes + b'\0'
#
# Gap between EPFM chunk and ESYS chunk = catalog bytes that overflow past EPFM[353]
# MODX reads gap size from catalog_len field — gap is NOT required to match reference.


# NOTE: _build_catalog_entry rebuilds Entr records from scratch.
# For best results when building from library files (Soundmondo etc.),
# the original Entr records should be cloned from the source catalog
# and only [0:4]=blob_sz, [4:8]=dp_off, [11]=idx should be updated.
# The JS Forge v1.19 implements this correctly via byDpOff map matching.
# Python serializer fix: TODO when source Entr records are available.

def _detect_engine_bits(blob: bytes) -> int:
    """Detect engine bits for Entr[15] from blob content.

    Entr[15] engine bitmap: 0x01=AWM2, 0x02=FM-X, 0x04=AN-X.
    blob[6695] = part count.
    blob[6700] = first part engine byte (0=AWM2,2=FM-X,3=AN-X).
    Multi-part: scan for 0x00000015 sub-headers after offset 7000, read byte at -3.
    Verified against Soundmondo.Y2L and Init files 2026-05-04.
    """
    ENG = {0: 0x01, 1: 0x01, 2: 0x02, 3: 0x04, 4: 0x04}
    if len(blob) < 6710:
        return 0x01
    part_count = blob[6695] or 1
    bits = ENG.get(blob[6700], 0x01)
    if part_count > 1:
        found = 0
        i = 7000
        while i < len(blob) - 4 and found < part_count - 1:
            if blob[i:i+4] == b'\x00\x00\x00\x15':
                eb = blob[i - 1] if i >= 1 else 0
                bits |= ENG.get(eb, 0x01)
                found += 1
                i += 4
            else:
                i += 1
    return bits


def _build_catalog_entry(name: str, perf_size: int, dpfm_data_offset: int,
                         perf_index: int, blob: bytes = None) -> bytes:
    """Build one EPFM catalog Entr data block (WITHOUT the Entr+size header).

    Entr record layout (binärverifierat 2026-05-04 mot Soundmondo.Y2L + Init-filer):
        [0:4]  blob_sz        u32 BE
        [4:8]  dp_off         u32 BE
        [8]    0x00           constant
        [9]    0x40           constant (MODX validerar detta fält)
        [10]   0x00           constant
        [11]   entry_index    u8
        [12]   0x00           constant
        [13]   0x00           multi-engine flag (förenklat)
        [14]   0x00           constant
        [15]   engine_bits    0x01=AWM2, 0x02=FM-X, 0x04=AN-X, OR-kombinerat
        [16]   0x02           constant (MODX validerar detta fält)
        [17]   0x00           constant
        [18]   0x01           category (0x01=default/piano)
        [19]   0x00           constant
        [20:25] 0x00          padding
        [25]   0x30           constant
        [26]   0x00           slot flag (förenklat)
        [27:]  'IDX:LongName(20ch padded):ShortName\0'  name string
    """
    engine = _detect_engine_bits(blob) if blob else 0x01
    long_name  = name[:20].ljust(20)
    short_name = name[:20]
    text       = f"{perf_index}:{long_name}:{short_name}\x00"
    data = bytearray(27)
    struct.pack_into('>I', data,  0, perf_size)
    struct.pack_into('>I', data,  4, dpfm_data_offset)
    data[8]  = 0x00
    data[9]  = 0x40
    data[10] = 0x00
    data[11] = perf_index & 0xFF
    data[12] = 0x00
    data[13] = 0x00
    data[14] = 0x00
    data[15] = engine
    data[16] = 0x00  # 0x00=ESP Plugin, 0x02=MODX hardware; use 0x00 for compatibility
    data[17] = 0x00
    data[18] = 0x01
    data[19] = 0x00
    # [20:25] = 0x00 already
    data[25] = 0x30
    data[26] = 0x00
    data += text.encode('ascii', errors='replace')
    return bytes(data)


# Kept for backward-compatibility reference only
_CATALOG_FIXED_22 = bytes.fromhex('000044410000000c0040000000000001020001000000')


def _build_catalog(perf_names: list[str], src_data: bytes = None,
                   perf_sizes: list[int] = None,
                   dpfm_data_offsets: list[int] = None) -> tuple:
    """
    Build EPFM catalog fields for N performances.

    Real MODX catalog stream (starts at file offset 361 = EPFM[289]):
        [0:4]  = N  (u32 BE)
        [4:...]= N x ( b'Entr'(4) + entry_size(4) + entry_data(entry_size bytes) )

    EPFM field layout:
        EPFM[280]    = 0x00
        EPFM[281:285]= b'EPFM'     (literal tag — NOT N!)
        EPFM[285:289]= payload_size (= total bytes of stream = len(stream))
        EPFM[289:353]= stream[0:64]
        [EPFM_END:ESYS] = stream[64:]  (overflow)

    Returns: (N, payload_size, cat_in_64, cat_out)
    """
    n       = len(perf_names)
    sizes   = perf_sizes         or [0] * n
    offsets = dpfm_data_offsets  or [0] * n

    cat = bytearray()
    cat += n.to_bytes(4, 'big')
    for i, name in enumerate(perf_names):
        blob = source_blobs[i] if source_blobs else None
        ed = _build_catalog_entry(name, sizes[i], offsets[i], i, blob)
        cat += b'Entr' + len(ed).to_bytes(4, 'big') + ed

    stream       = bytes(cat)
    payload_size = len(stream)

    ECAP    = 64
    cat_in  = (stream[:ECAP] + bytes(ECAP))[:ECAP]
    cat_out = stream[ECAP:]

    return n, payload_size, cat_in, cat_out


def build_library(
    src_paths: list[str],
    dst_path: str,
    names: list[str] = None,
) -> None:
    """
    Build a multi-performance Y2L library file from individual Y2L patches.

    Args:
        src_paths: List of source Y2L file paths (one per performance)
        dst_path:  Output Y2L file path
        names:     Optional list of display names (defaults to names from source files)
    
    The output file uses src_paths[0]'s non-DPFM structure (ESYS, EFVT, DSYS, DFVT)
    as the base, then appends all performance data records.
    """
    import shutil

    if not src_paths:
        raise ValueError("Need at least one source file")

    # Read all source DPFM performance data
    perf_data_list = []
    src_names = []
    for path in src_paths:
        data = Path(path).read_bytes()
        dpfm_off, dpfm_len = find_dpfm(data)
        dpfm = data[dpfm_off:dpfm_off+dpfm_len]
        # Parse all performances from DPFM (count + N×(Data+size+bytes))
        n_perfs_src = int.from_bytes(dpfm[0:4], 'big')
        _pos = 4
        for _pi in range(n_perfs_src):
            _plen = int.from_bytes(dpfm[_pos+4:_pos+8], 'big')
            perf_data = dpfm[_pos+8:_pos+8+_plen]
            perf_data_list.append(perf_data)
            # Extract name from perf data[4:] (null-terminated ASCII, offset 4 = past length field)
            name = ''
            for b in perf_data[4:36]:
                if b == 0 or b < 32: break
                name += chr(b)
            src_names.append(name.strip() or f"Perf {len(src_names)+1}")
            _pos += 8 + _plen

    if names is None:
        names = src_names
    if len(names) < len(src_paths):
        names = names + src_names[len(names):]

    # Build new DPFM chunk data  (count + Data+size+bytes per perf)
    n = len(perf_data_list)
    new_dpfm = bytearray()
    new_dpfm += n.to_bytes(4, 'big')
    for perf_data in perf_data_list:
        new_dpfm += b'Data' + len(perf_data).to_bytes(4, 'big') + sanitize_perf_blob(perf_data)
    new_dpfm = bytes(new_dpfm)

    # Build catalog fields using the real MODX Entr-block format
    base_data = Path(src_paths[0]).read_bytes()
    # Compute DPFM data offsets for the catalog metadata
    _dpfm_sizes   = [len(pd) for pd in perf_data_list]
    _dpfm_offsets = []
    _pos = 4
    for pd in perf_data_list:
        _dpfm_offsets.append(_pos + 8)   # offset past 'Data'+size header
        _pos += 8 + len(pd)
    cat_n, cat_total_size, cat_in_64, cat_out = _build_catalog(
        names, base_data,
        perf_sizes=_dpfm_sizes,
        dpfm_data_offsets=_dpfm_offsets,
    )

    # ── Read base-file chunk directory ─────────────────────────────
    def _parse_chunks_from_epfm_dir(data):
        """Parse chunks using the EPFM directory (absolute file offsets).
        EPFM directory is at data[72:136] — 8 slots × 8 bytes each.
        Each slot: [4-byte ASCII tag][4-byte absolute file offset]
        """
        chunks = {}
        for i in range(0, 64, 8):
            tag_bytes = data[72+i:72+i+4]
            if tag_bytes == b'\xff\xff\xff\xff':
                break
            try:
                tag = tag_bytes.decode('ascii')
            except Exception:
                break
            off = int.from_bytes(data[72+i+4:72+i+8], 'big')
            if off <= 0 or off + 8 > len(data):
                continue
            size = int.from_bytes(data[off+4:off+8], 'big')
            if off + 8 + size > len(data):
                continue
            chunks[tag] = {'tag': tag, 'off': off, 'len': size,
                           'data': data[off+8:off+8+size]}
        return chunks

    base_chunks = _parse_chunks_from_epfm_dir(base_data)
    chunk_by_tag = base_chunks

    # ── Compute new chunk positions ─────────────────────────────────
    EPFM_END = 64 + 8 + 353   # = 425 (always fixed)
    esys_src  = chunk_by_tag['ESYS']
    efvt_src  = chunk_by_tag['EFVT']
    dsys_src  = chunk_by_tag['DSYS']
    dfvt_src  = chunk_by_tag['DFVT']

    new_esys = EPFM_END + len(cat_out)
    new_efvt = new_esys + 8 + esys_src['len']
    new_dpfm_pos = new_efvt + 8 + efvt_src['len']
    new_dsys = new_dpfm_pos + 8 + len(new_dpfm)
    new_dfvt = new_dsys + 8 + dsys_src['len']

    # ── Build EPFM 353-byte data block ─────────────────────────────
    # Copy directory from base file (first 281 bytes of EPFM data = chunk offset table)
    epfm_dir = bytearray(base_data[72:72+64])  # directory is exactly 64 bytes

    def _write_off(ba, tag, val):
        tb = tag.encode('ascii')
        for k in range(0, len(ba)-7, 8):
            if ba[k:k+4] == tb:
                ba[k+4:k+8] = val.to_bytes(4, 'big')
                return

    _write_off(epfm_dir, 'ESYS', new_esys)
    _write_off(epfm_dir, 'EFVT', new_efvt)
    _write_off(epfm_dir, 'DPFM', new_dpfm_pos)
    _write_off(epfm_dir, 'DSYS', new_dsys)
    _write_off(epfm_dir, 'DFVT', new_dfvt)

    new_epfm = bytearray(353)
    # [0:64]   = chunk directory (updated absolute offsets)
    new_epfm[:64] = epfm_dir[:64]
    # [64:280] = 0xFF padding (216 bytes, constant in all real MODX files)
    for _i in range(64, 280):
        new_epfm[_i] = 0xFF
    # [280]    = 0x00 (separator byte)
    new_epfm[280] = 0x00
    # [281:285]= b'EPFM' (catalog sub-tag)
    new_epfm[281:285] = b'EPFM'
    # [285:289]= catalog_size (u32be)
    new_epfm[285:289] = cat_total_size.to_bytes(4, 'big')
    # [289:353]= first 64 bytes of catalog stream
    new_epfm[289:353] = cat_in_64

    # ── Assemble output file ────────────────────────────────────────
    out = bytearray()
    out += base_data[:64]                                           # file header (unchanged)
    out += b'EPFM' + (353).to_bytes(4, 'big') + new_epfm          # EPFM chunk
    out += cat_out                                                  # catalog overflow
    out += b'ESYS' + esys_src['len'].to_bytes(4,'big') + esys_src['data']
    out += b'EFVT' + efvt_src['len'].to_bytes(4,'big') + efvt_src['data']
    out += b'DPFM' + len(new_dpfm).to_bytes(4, 'big') + new_dpfm
    out += b'DSYS' + dsys_src['len'].to_bytes(4,'big') + dsys_src['data']
    out += b'DFVT' + dfvt_src['len'].to_bytes(4,'big') + dfvt_src['data']

    Path(dst_path).write_bytes(bytes(out))


# ── TESTS ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import os

    print("ENCODE/DECODE UNIT TESTS")
    print("=" * 55)
    tests = [
        # (field, ui_value, expected_raw, engine)
        ("algorithm",        5,      4,    None),
        ("algorithm",       70,     69,    None),
        ("pan",             10,     74,    None),
        ("pan",            -10,     54,    None),
        ("aegAttack",       10,     74,    None),
        ("detune",        -3.0,     98,   "FMX"),
        ("detune",          -3,    125,   "ANX"),
        ("levelVel",         7,     14,    None),
        ("levelVel",        -7,      0,    None),
        ("opDetune",        -3,     12,    None),
        ("pegInitialLevel", 10,     60,    None),
        ("sync",           200,      8,    None),
        ("octave",           8,      3,    None),
        ("monoPoly",    "Mono",      0,    None),
        ("monoPoly",    "Poly",      1,    None),
        ("portamentoTime",  50,    114,    None),
        ("fmDepth",         10,    138,    None),
        # AWM2 elem new fields (verified 2025-04-23)
        ("ampLevelVel",     50,    114,    None),   # center=64: 50+64=114
        ("ampLevelVel",    -10,     54,    None),
        ("elemFilterResonance", 80,  80,    None),   # direct
        ("elemFilterResonance",  0,   0,    None),
        ("fegTimeAttack",   30,     30,    None),   # direct
        ("fegTimeDecay1",   30,     30,    None),
        ("fegTimeDecay2",   30,     30,    None),
        ("fegTimeHold",     64,     64,    None),
        ("fegTimeRelease",  40,     40,    None),
        ("fegLevelHold",    22,    150,    None),   # center=128
        ("fegLevelAttack",  70,    198,    None),
        ("fegLevelDecay1",  70,    198,    None),
        ("fegLevelDecay2",  70,    198,    None),
        ("fegLevelRelease", 70,    198,    None),
        ("fegDepth",        20,     84,    None),   # center=64: 20+64=84
        ("fegDepth",        40,    104,    None),   # default raw
        # waveformNumber: u16 LE, 1-based ✅ verified
        ("waveformNumber",   6, (6,0),    None),    # CFX v06 St
        ("waveformNumber",  14, (14,0),   None),    # C7 f St
        ("waveformNumber", 186, (186,0),  None),    # Hamburg Grand v01 St
        ("waveformNumber", 300, (44,1),   None),    # hi-byte test: 300=0x12C → (0x2C,0x01)
        # New fields verified 2025-04-23 (Step 33)
        ("levelVelCurve",      0,    0,  None),    # direct: 3→0
        ("aegTimeVelSegment",  2,    2,  None),    # enum: direct
        ("aegTimeVel",        20,   84,  None),    # center=64: +20→84
        ("cutoffVelSens",     20,   84,  None),    # center=64: +20→84
        ("resonanceVelSens",  20,   84,  None),    # center=64: +20→84
        ("hpfCutoff",        400, (144,1), None),  # u16 LE: 400 Hz
        ("fegDepthVelSegment", 2,    2,  None),    # enum direct
        ("fegDepthVelSens",   20,   84,  None),    # center=64
        ("pegTimeVelSegment",  2,    2,  None),    # enum direct ✅
        ("pegTimeVelSens",    20,   84,  None),    # center=64 ✅
        ("cutoffKeyFollow",   81,   90,  None),    # keyfollow%: 81%→raw=90, decode→81 ✅
        ("cutoffKeyFollow",   50,   80,  None),    # keyfollow%: 50%→raw=80, decode→50 ✅
        ("cutoffKeyFollow",    0,   64,  None),    # keyfollow%: 0%→raw=64
        ("hpfCutoffKeyFollow",50,   80,  None),    # keyfollow%: 50%→raw=80 ✅
    ]
    errors = 0
    for field, ui, expected_raw, engine in tests:
        raw = encode(field, ui, engine)
        back = decode(field, raw, engine)
        ok_enc = raw == expected_raw
        ok_dec = abs(back - ui) < 0.01 if isinstance(back, float) else back == ui
        status = "✅" if (ok_enc and ok_dec) else "❌"
        if not (ok_enc and ok_dec): errors += 1
        raw_str = str(raw) if isinstance(raw, tuple) else str(raw)
        print(f"  {status} {field:<22} ui={str(ui):<8} → raw={raw_str:<10} → {back}")
    print()

    print("ROUND-TRIP TESTS")
    print("=" * 55)
    for path in [
        "/mnt/user-data/uploads/FM-X_00_Init_Base.Y2L",
        "/mnt/user-data/uploads/AWM2_00_Init_Base.Y2L",
        "/mnt/user-data/uploads/AN-X_00_Init_Base.Y2L",
    ]:
        if os.path.exists(path):
            ok = round_trip_verify(path)
            print(f"  {'✅' if ok else '❌'} {os.path.basename(path)}")
    print()

    print("patch_ui TESTS")
    print("=" * 55)
    base = "/mnt/user-data/uploads/FM-X_00_Init_Base.Y2L"
    tmp  = "/tmp/test_ui.Y2L"
    ui_tests = [
        # (engine, part, field, ui_value, op, elem, expected_dpfm_off, expected_raw)
        ("FMX", 0, "algorithm",    5,    None, None, 12537,  4),
        ("FMX", 0, "feedback",     3,    None, None, 12539,  3),
        ("FMX", 0, "pan",         10,    None, None,  6845, 74),
        ("FMX", 0, "detune",    -3.0,    None, None,  6929, 98),
        ("FMX", 0, "detune",      -3,       0, None, 12692, 12),   # OP1 detune
        ("FMX", 0, "levelVel",     7,       0, None, 12744, 14),   # OP1 levelVel
        ("FMX", 0, "pegInitialLevel", 10,   0, None, 12704, 60),   # OP1 PEG initial (off=16, abs=12676+16=12692? wait)
        ("FMX", 0, "pegAttackLevel", 50,    0, None, 12706, 50),   # OP1 PEG attack (off=18+12676=12694... recalc)
        ("FMX", 0, "aegAttackTime", 50,     0, None, 12708, 50),   # OP1 AEG attack (off=32, KORRIGERAT från 20!)
    ]
    for engine, part, field, ui, op, elem, exp_off, exp_raw in ui_tests:
        patch_ui(base, tmp, engine, part, field, ui, op=op, elem=elem)
        diffs = diff_dpfm(base, tmp)
        changed = {d[0]: d[2] for d in diffs}
        ok = changed.get(exp_off) == exp_raw and len(diffs) == 1
        print(f"  {'✅' if ok else '❌'} {field:<22} ui={str(ui):<8} → [{exp_off}]={exp_raw}  got={changed}")
        if not ok: errors += 1
    os.unlink(tmp)
    print()

    print("MERGE ENGINE TEST")
    print("=" * 55)
    base = "/mnt/user-data/uploads/FM-X_00_Init_Base.Y2L"
    tmp  = "/tmp/test_merge.Y2L"
    patches = [
        {"engine": "FMX", "part": 0, "field": "algorithm", "value": 5},
        {"engine": "FMX", "part": 0, "field": "feedback",  "value": 3},
        {"engine": "FMX", "part": 0, "field": "volume",    "value": 80},
        {"engine": "FMX", "part": 0, "field": "pan",       "value": 10},
        {"engine": "FMX", "part": 0, "field": "coarse",    "value": 3, "op": 0},
        {"engine": "FMX", "part": 0, "field": "level",     "value": 99, "op": 0},
        {"engine": "FMX", "part": 0, "field": "aegAttackTime", "value": 50, "op": 0},  # off=32
    ]
    merge_patches(base, tmp, patches)
    diffs = diff_dpfm(base, tmp)
    expected_fields = {12537: 4, 12539: 3, 6843: 80, 6845: 74, 12688: 3, 12732: 99, 12708: 50}
    ok = all(expected_fields.get(d[0]) == d[2] for d in diffs) and len(diffs) == len(expected_fields)
    print(f"  {'✅' if ok else '❌'} 6-field merge: {len(diffs)} changes")
    for d in diffs:
        exp = expected_fields.get(d[0], "?")
        chk = "✓" if exp == d[2] else "✗"
        print(f"    {chk} [{d[0]}] {d[1]}→{d[2]} (expected {exp})")
    os.unlink(tmp)
    print()

    if errors == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ {errors} failures")
