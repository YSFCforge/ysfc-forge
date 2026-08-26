#!/usr/bin/env python3
import json, csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
mp=ROOT/'mapping'/'YSFC_waveform_mapping_master_v1.json'
data=json.loads(mp.read_text(encoding='utf-8'))
# master may be list or object; normalize records
records=data if isinstance(data,list) else data.get('records', data.get('mappings', []))
if not isinstance(records,list): raise SystemExit('Unsupported mapping JSON shape')
print(f'mapping records: {len(records)}')
text=mp.read_text(encoding='utf-8')
assert 'Sagat2 Sw' in text, 'Known unresolved waveform 3720 missing from master evidence'
print('known unresolved evidence: Sagat2 Sw present')
print('waveform mapping validation: OK')
