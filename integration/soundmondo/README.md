# Soundmondo / SysEx development integration

This directory contains the recoverable Python development layer behind the Soundmondo work.

Pipeline:

`Soundmondo .syx -> sysex_parser.py -> normalized Performance -> ysfc_bridge.py -> YSFC intermediate`

The current full-fidelity binary writer is the standalone browser tool
`../../tools/ysfc_forge_sysex_converter_v1_27.html`.

## Included

- `sysex_parser.py` — MONTAGE, MODX, MODX+, MONTAGE M and MODX M parser/normalizer
- `ysfc_bridge.py` — semantic YSFC bridge and dependency detection
- `ysfc_serializer_adapter.py` — stable Python integration facade; binary emission fails closed
- `data/` — block tables, normalized parameter map and effect type map
- `test_bridge.py` — bridge regression inherited from the parser project
- `test_serializer_adapter.py` — adapter fail-closed regression
- waveform mapping generator/validator helpers

## Waveform mapping

Authoritative development assets live in `../../mapping/`:

- `waveforms_legacy.py` — 6,347 legacy preset waveform identities
- `waveform_remap_legacy_to_m.py` — Python legacy->MODX M remap logic
- `YSFC_waveform_mapping_master_v1.json/.csv` — mapping master/provenance
- `YSFC_waveform_mapping_production_v1.js` — production lookup used by browser development

Known intentionally unresolved legacy preset: **ID 3720 `Sagat2 Sw`**. It must not be guessed or substituted.

## Safety policy

Missing blocks, unresolved mappings and external User/Library Waveform/Arp dependencies are fail-closed. The repository deliberately does not restore old template-default substitution behavior.
