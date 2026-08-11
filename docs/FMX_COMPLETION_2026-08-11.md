# FM-X completion integration note — 2026-08-11

This project snapshot incorporates the FM-X corrections learned during Soundmondo→Y2L v1.0.60–v1.0.76 work.

## Must-retain corrections

- OP +62: Pitch Controller Sensitivity
- OP +64: Level Controller Sensitivity
- OP +66/+68/+70: 1st-LFO Destination 1/2/3 Depth Ratio
- Do not classify +66/+68/+70 as [INTERN] trailers.
- 2nd-LFO global Pitch/Amp/Filter depth and per-OP Pitch/Amp depth are mapped.
- FM Color, full Filter/FEG core, Cutoff Scaling/Key Follow, Part PEG, Part offsets, 1st LFO User 18/18, Part Common Pan/Key-On-Delay and controller sensitivity are covered by the v1.0.77 matrix.

## Scope boundary

“FM-X complete” here means the Yamaha-documented FM-X parameter set tracked by the Soundmondo→Y2L coverage matrix is mapped and accepted through MODX M ESP testing. It does **not** mean the internal YAMAHA-SOM Smart Morph interpolation object has been generically reverse-engineered for arbitrary synthesis/editing. Smart Morph preservation/transport is verified; generic construction remains separate.
