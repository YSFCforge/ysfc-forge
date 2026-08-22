# YSFC conversion bridge mapping notes

## Architecture

The SysEx project remains independent of YSFC Forge's binary serializers. The
bridge's job is to provide a stable semantic seam.

The intended downstream roles are:

- classic serializer/writer: X7L-family destination structures
- modern serializer: MODX M / Y2L destination structures
- classic-to-modern transcoder: semantic transformations/defaults where source
  and target representations differ

Serializer byte offsets do not belong in `sysex_parser.py` or `ysfc_bridge.py`.

## Performance common

Normalized source fields are grouped under:

`performance.common`

including tempo, volume, pan, category codes, Arp Master and Motion Sequence
Master.

## Parts

Each Part exposes both:

- `part_index` — zero-based, intended for array/serializer indexing
- `part_number` — one-based Yamaha/UI number

Fields are grouped into identity, switches, mix, ranges, pitch, Arpeggio,
Insertion FX and engine-specific data.

## Scenes

Scenes similarly expose zero-based and one-based identity. Scene Part snapshots
are kept separate from current Part state.

## Arpeggios

The bridge keeps both bank-local semantic identity and original raw references.
Preset Arps are self-resolving references. User/Library Arps become external
`dependencies` because Performance Soundmondo SysEx does not itself carry the
referenced User Arp payload.

## AWM2 dependencies

When a decoded AWM2 element explicitly references a non-preset waveform, the
bridge emits an `external_waveform` dependency. This is currently strongest for
legacy AWM2 because its waveform selector is decoded more deeply than the current
M-generation AWM2 subset.

## Effects

Insertion A/B retain type identity, routing, side-chain and all 24 raw parameter
pairs. Per-effect semantic parameter names/units remain deferred. This is enough
for a lossless bridge record but not yet enough to claim semantic equivalence for
every effect when writing a different generation.

## Target assessment

`classic_x7l_4_0_5`
- AN-X => blocked
- unresolved external waveform/Arp dependencies => blocked
- otherwise => candidate

`modx_m_y2l`
- unresolved external dependencies => dependency_required
- otherwise => candidate

All statuses still report `serializer_integration: not_connected`.

## Next integration step

The next code layer should be a serializer adapter that consumes only this bridge
schema and maps it into the real YSFC serializer object model. That adapter should
be tested first with a very small set of Performances where a known-good X7L/Y2L
reference can be compared field-by-field or round-tripped in MODX M ESP.
