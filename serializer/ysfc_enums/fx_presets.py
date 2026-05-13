"""
YSFC Forge — Effect Preset Definitions

Officiell lista över factory presets per effekt-typ.
Källa: Effect Preset List (Yamaha officiell dokumentation)

Notera: Vissa preset-namn är hopslagna i källdata (multiline-celler)
och presenteras som en gemensam lista per effekt.
"""

# {effect_type_name: [preset_name, preset_name, ...]}
FX_PRESETS = {
    '2 Modulator': [
        'Basic Fast Deep Mist MultiPanning Mod Vibrator Wonder Shimmer',
    ],
    'Amp Simulator 1': [
        'Stack 1Stack 2 Twin Boost Old Amp Transistor Modern US-Clean J-Clean FuzzSmall Blues Buzzy Bottom Beat Crunch Beat Drive',
    ],
    'Amp Simulator 2': [
        'Stack 1Stack 2 Combo Crunch Hi Gain BritishTube Drive Tube Clean',
    ],
    'Analog Delay Modern': [
        'Urban Soft RockReel to Reel Dub Long Bucket Rev Clear Black Dub Short Lo-Fi Echo Dark Room New Wave',
    ],
    'Analog Delay Retro': [
        'Mellow Magical Dawn Reel to Reel Bright Dub Magical Dusk DeepLo-Fi Echo OilDark Room Smokey Dub',
    ],
    'Auto Pan': [
        'E.Piano Smooth Oval Right TurnSuper Slow',
    ],
    'Auto Synth': [
        'Nz Mod Delay 1 Nz Mod Delay 2 Nz Mod Delay 3 Nz Mod Delay 4 EchoSpace Walking Robot Delay',
    ],
    'Beat Repeat (even)': [
        '1/16 x 4  1/16 x 4 Rev. Trans GateTrans Gate + HPF Pitch Sweep PitchSweep+HPF Slow Attack Echo Broken',
    ],
    'Beat Repeat (evn+tri.)': [
        '1/16 x 4  1/16 x 4 Rev. Trans GateTrans Gate + HPF Pitch Sweep PitchSweep+HPF Slow Attack Echo Broken',
    ],
    'Beat Repeat (free)': [
        '1/16 x 4  1/16 x 4 Rev. Trans GateTrans Gate + HPF Pitch Sweep PitchSweep+HPF Slow Attack Echo Broken  Quintuplet',
    ],
    'Beat Repeat (triplet)': [
        'Triplet x 4 Triplet x 4 Rev. Trans GateTrans Gate + HPF Pitch Sweep PitchSweep+HPF Slow Attack Echo Broken',
    ],
    'Bit Crusher': [
        'Hard Soft12-bit Sampler Mid-Side 1Mid-Side 2Mid-Side 3 2-bit Dist',
    ],
    'British Combo': [
        'Classic Top Boost Custom Heavy',
    ],
    'British Lead': [
        'Dirty Drive Gainer Hard',
    ],
    'British Legend': [
        'Blues Heavy 1Heavy 2 Clean  Dirty Clean',
    ],
    'Classic Compressor': [
        'Basic AttackFor Vintage Keys Pack Comp  Gate TightPopRhythm Cutting Comp Basic BassOld Record Piano',
    ],
    'Classic Flanger': [
        'BasicFlange Chorus Psychedelic Jet',
    ],
    'Comp Distortion': [
        'Basic Booster School Boy Detroit Long Lead 80s Clean',
    ],
    'Comp Distortion Delay': [
        'Hard 1Hard 2 Grunge Voodoo Texas Rockabilly LA Session Thin Techno',
    ],
    'Control Delay': [
        'Basic Transition Slow Transition Fast',
    ],
    'Control Filter': [
        'LPF12 LPF18 LPF24 BPF HPF',
    ],
    'Control Flanger': [
        'Comb 1Comb 2Comb 3',
    ],
    'Control Phaser': [
        'Stage 4Stage 6Stage 8Stage 10',
    ],
    'Cross Delay': [
        'Basic',
        'Short',
        'Long',
        'Very Long',
    ],
    'Damper Resonance': [
        'Basic String Reso ShortLong',
    ],
    'Delay LCR': [
        'Bright Warm BounceAnalog Delay',
    ],
    'Delay LR': [
        'Basic Doubling Short Fast LongVery Long Analog Delay',
    ],
    'Digital Turntable': [
        'Digi Nz 78 rpm45 rpm 331/3 rpmOld Record 1Old Record 2 Short Wave Radio',
    ],
    'Dynamic Filter': [
        'Basic High Pass Low Pass Squish',
    ],
    'Dynamic Flanger': [
        'Follow Reverse Distorted Sync',
    ],
    'Dynamic Phaser': [
        'Up Down Follow Reverse Light',
    ],
    'Dynamic Ring Modulator': [
        'Basic Metallic Sputter Sharp Edge',
    ],
    'Early Reflection': [
        'Close Far Reverse Gate70s Gate',
    ],
    'Effect Type Name': [
        'Preset Name',
    ],
    'Ensemble Detune': [
        'Basic Soft WideDeep Wide Stereo Sim',
    ],
    'G Chorus': [
        'Basic Fast Deep Mist Bright',
    ],
    'Gated Reverb': [
        'Gated Reverb 1',
        'Gated Reverb 2',
        'Gate Delay 1',
        'Gate Delay 2',
    ],
    'HD Hall': [
        'Large Hall',
        'Medium Hall',
        'Bright Hall',
        'Warm',
        'Small',
    ],
    'HD Plate': [
        'Large Plate',
        'Medium Plate',
        'Bright Plate',
        'Warm Plate',
        'Rattle Plate',
    ],
    'HD Room': [
        'Small',
        'Medium',
        'Large',
        'Presence',
        'Warm',
        'Open',
    ],
    'Harmonic Enhancer': [
        'Presence Edge  High Edge Mid Edge',
    ],
    'Isolator': [
        'Lo/Hi Boost Hi CutLo Only Mid Only Lo Cut Near Flat',
    ],
    'Jazz Combo': [
        'BasicWarm Chorus Vibrato Keyboard Amp Kbd Amp Dist 1 Kbd Amp Dist 2',
    ],
    'Lo-Fi': [
        'Lo-FiOld Phone Overload Max Lo-Fi',
    ],
    'Multi FX': [
        'Distortion Solo Distortion Basic Overdrive Chorus Crunch Wah Oldies Delay Vintage Echo',
    ],
    'Multi-band Comp': [
        'Basic Maximizer Wild Attacky HardHip ClubSlap Bass (ch)',
    ],
    'NoiseGate + Comp + Eq': [
        'BasicSoft Comp Hard Comp Limiter',
    ],
    'Noisy': [
        'Nz DriveSoft Nz Tremolo Nz Rotary 1Nz Rotary 2 NoisyTremolo Noise Fuzz Noise',
    ],
    'Parallel Comp': [
        'Natural Rich Punchy Electronic LoudNatural for Mst Rich for Master Punchy for Mst ElectronicForMst Loud for Master',
    ],
    'Pitch Change': [
        'Detune Oct Echo Octaver Plus 4th Minus 4th Oval  Step UpStep Down',
    ],
    'Presence': [
        'Natural Heavy Bright',
    ],
    'R3 Hall': [
        'Basic',
        'Large Hall',
        'Backstage',
        'Ballad',
        'Light',
    ],
    'R3 Plate': [
        'Basic',
        'Bright Vocal',
        'Smooth Vocal',
        'Short Bright',
        'Metal Splash',
    ],
    'R3 Room': [
        'Basic',
        'Open',
        'Wide',
        'Tight',
    ],
    'REV-X Hall': [
        'Basic',
        'Small Hall',
        'Clean',
        'Church',
        'Bright Hall',
    ],
    'REV-X Room': [
        'Basic',
        'Basement',
        'Garage',
        'Bedroom',
    ],
    'Reverse Reverb': [
        'Basic',
        'Long',
        'Short',
        'Rvs Delay 1',
        'Rvs Delay 2',
    ],
    'Ring Modulator': [
        'Basic Slow Tremolo Crazy',
    ],
    'Rotary Speaker 1': [
        'Basic Horn Mic LightHeavy Rotor Fast First',
    ],
    'Rotary Speaker 2': [
        'Clean and Wide Vintage Mono Slow and Dirty Full Drive Broken Motors',
    ],
    'SPX Chorus': [
        'Basic Fast Deep Slow Flangy',
    ],
    'SPX Hall': [
        'Basic',
        'Large Hall',
        'Backstage',
        'Light',
        'Gymnasium',
    ],
    'SPX Room': [
        'Basic',
        'Open',
        'Wide',
        'Tight',
    ],
    'SPX Stage': [
        'Basic',
        'Small',
        'Large',
        'Warm',
        'Presence',
    ],
    'Shimmer Reverb': [
        'Basic',
        'Ambient',
        'AM',
        'Mod Reverb',
    ],
    'Slice': [
        'Basic Slice Beat 8th Pan 16th Mute Rock',
    ],
    'Small Stereo': [
        'Distortion Overdrive Vintage Amp Heavy Dist',
    ],
    'Space Simulator': [
        'Tunnel',
        'Basement',
        'Canyon',
        'White Room',
        'Small Room',
        'Live Room',
        'Three Walls',
    ],
    'Spiralizer F': [
        'Basic Step 1 Scale Step 2 Slow',
    ],
    'Spiralizer P': [
        'Basic Step 1 Scale Step 2 Slow',
    ],
    'Stereophonic Optimizer': [
        'Focus Bottom Top CenterAcoustic Piano DrumEP Tremolo OrganSax',
    ],
    'Symphonic': [
        'Basic Fast Deep Slow Analog',
    ],
    'Talking Modulator': [
        'Basic Slow',
    ],
    'Tech Modulation': [
        'Mod Chase Mod Dub Star Train Numerator Active Dist Astonish Drift Armor',
    ],
    'Tempo Cross Delay': [
        '1/8 & 1/32D',
        '1/16 Echo',
        '1/8T & 1/4T',
        '1/16T Echo',
        '1/4 Echo',
        'Dotted 1/8 Echo',
        '1/8 Echo',
        'Triplet Echo',
        '1/2 Echo',
    ],
    'Tempo Delay Mono': [
        '1/4T L/R Diff1/8T L/R Diff 1/4 Echo 1/4 MonoDotted 1/8 Echo 1/8 EchoDotted 1/8 Mono 1/8 MonoTriplet Echo Triplet Mono Analog Delay',
    ],
    'Tempo Delay Stereo': [
        '1/4T L/R Diff1/8T L/R Diff 1/4 EchoDotted 1/8 Echo 1/8 EchoTriplet Echo',
    ],
    'Tempo Flanger': [
        'Deep Mod Flange Chorus Metallic Psychedelic Jet',
    ],
    'Tempo Phaser': [
        'Stage 4Stage 6Stage 8Stage 10Stage 12Stage 18',
    ],
    'Tempo Spiralizer F': [
        'Basic Step 1 Scale Step 2 Slow',
    ],
    'Tempo Spiralizer P': [
        'Basic Step 1 Scale Step 2 Slow',
    ],
    'Tremolo': [
        'Fast SlowSuper Fast Stereo Vibrato SpringRelax',
    ],
    'U.S. Combo': [
        'TwinRich Clean Thin Clean Crunch',
    ],
    'U.S. High Gain': [
        'Dirty Riff Burn Solo',
    ],
    'Uni Comp Down': [
        'Basic Warm BrightSat CompComp + Hard Clip Master',
    ],
    'Uni Comp Up': [
        'Basic Warm BrightSat CompComp + Hard Clip Master',
    ],
    'VCM Auto Wah': [
        'Clean Mid Clean High Clean Low Clean Bass Overdrive Mid Overdrive High Overdrive Low Overdrive Bass',
    ],
    'VCM Compressor 376': [
        'BasicComp Sustainer 60s Drum Kit Natural Kick Old PianoValve Tone Bass Hard BasicFast Atk + Boost Soft Atk + Boost Attack & Tight Hard Atk + Boost Vocal Comp 117x Unplugged Attack Comp Punchy Master Pinched',
    ],
    'VCM EQ 501': [
        'Basic Bright Warm  Lo/Hi Boost Mid Boost LoudDance SD/BD Radio Speaker Flat',
    ],
    'VCM Flanger': [
        'Basic JetDeep Mod 1Deep Mod 2 Mad Mod',
    ],
    'VCM Mini Booster': [
        '1970s High Boost 1980s High Boost ModernHighBoost 1970s Low Boost 1980s Low Boost Modern LowBoost',
    ],
    'VCM Mini Filter': [
        '1970s LPF1980s LPFModern LPF 1970s HPF1980s HPFModern HPF',
    ],
    'VCM Pedal Wah': [
        'Clean Mid Clean High Clean Low Clean Bass Overdrive Mid Overdrive High Overdrive Low Overdrive Bass',
    ],
    'VCM Phaser Mono': [
        'Stage 4Stage 6Stage 8Stage 10Stage 12Stage 16 E.Piano Orange 90 Two Phase Deep Six Deep Eight Lite Eight Deep Sweeper Orange 100 Red Twelve Blue Sixteen Clavi 1Clavi 2E.Guitar 1E.Guitar 2E.Guitar 3Vibrato 1Vibrato 2Vibrato 3Ambience 1Ambience 2',
    ],
    'VCM Phaser Stereo': [
        'Stage 4Stage 6Stage 8Stage 10  Deep Sweeper E.Piano 1E.Piano 2Clavi 1Clavi 2E.Guitar 1E.Guitar 2E.Guitar 3 Deep Six Deep Eight Vibrato 1Vibrato 2Vibrato 3Ambience 1Ambience 2',
    ],
    'VCM Rotary Speaker Classic': [
        'Basic Warm Bright',
    ],
    'VCM Rotary Speaker Overdrive': [
        'Basic Warm Bright',
    ],
    'VCM Rotary Speaker Studio': [
        'Basic Warm Bright',
    ],
    'VCM Touch Wah': [
        'Clean Mid Clean High Clean Low Clean Bass Overdrive Mid Overdrive High Overdrive Low Overdrive Bass FollowHi QFor Bass Reverse',
    ],
    'Vinyl Break': [
        'Fast Middle Slow  Vinyl Stop Power off',
    ],
    'Vocoder': [
        'Basic Fast Slow',
    ],
    'Wave Folder': [
        'Soft 1Soft 2Hard 1Hard 2SEQ+LFO 01SEQ+LFO 02SEQ+LFO 03SEQ+LFO 04SEQ+LFO 05SEQ+LFO 06SEQ+LFO 07SEQ+LFO 08SEQ+LFO 09SEQ+LFO 10Saturator 1Saturator 2Saturator 3Saturator 4',
    ],
}


def get_presets(fx_name):
    """Returns list of presets for an effect (or empty list)."""
    return FX_PRESETS.get(fx_name, [])


if __name__ == '__main__':
    total = sum(len(p) for p in FX_PRESETS.values())
    print(f"Total effects with presets: {len(FX_PRESETS)}")
    print(f"Total preset entries: {total}")
