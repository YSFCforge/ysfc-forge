#!/usr/bin/env python3
"""Regenerate a compact JS lookup from the authoritative mapping master JSON.

The committed production JS remains the compatibility reference used by the browser
converter. This helper is intentionally schema-tolerant and emits only rows with an
explicit destination identifier.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
src=ROOT/'mapping'/'YSFC_waveform_mapping_master_v1.json'
out=ROOT/'mapping'/'legacy_to_modxm_generated.js'
data=json.loads(src.read_text(encoding='utf-8'))
records=data if isinstance(data,list) else data.get('records',data.get('mappings',[]))
lookup={}
for r in records if isinstance(records,list) else []:
    if not isinstance(r,dict): continue
    sid=r.get('legacy_id',r.get('source_id',r.get('source')))
    did=r.get('modxm_id',r.get('target_id',r.get('destination')))
    if isinstance(sid,int) and isinstance(did,int): lookup[sid]=did
out.write_text('const LEGACY_TO_MODXM_GENERATED = '+json.dumps(lookup,sort_keys=True,separators=(',',':'))+';\n',encoding='utf-8')
print(f'wrote {len(lookup)} mappings to {out}')
