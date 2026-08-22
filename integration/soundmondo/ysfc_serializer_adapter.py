#!/usr/bin/env python3
"""YSFC Forge Soundmondo integration adapter (development facade).

This module keeps the Python integration seam stable:
  Soundmondo .syx -> sysex_parser -> ysfc_bridge -> normalized YSFC intermediate.

The historical Python binary adapter was experimental. The current production-grade
Soundmondo writer is tools/ysfc_forge_sysex_converter_v1_27.html. This facade therefore
fails closed for binary emission instead of silently reintroducing older incomplete writer
logic. Core serializers and waveform remap helpers remain importable for controlled tests.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import ysfc_bridge

ADAPTER_SCHEMA_VERSION = 4

def build_intermediate(syx_path: str|Path, include_source_snapshot: bool=False):
    return ysfc_bridge.convert_sysex_file(Path(syx_path), include_source_snapshot=include_source_snapshot)

def preflight(bridge: dict):
    deps=bridge.get('dependencies') or []
    return {
        'ok_for_semantic_bridge': True,
        'dependency_count': len(deps),
        'dependencies': deps,
        'binary_writer': 'tools/ysfc_forge_sysex_converter_v1_27.html',
        'python_binary_emission': 'fail_closed',
        'reason': 'Historical Python Soundmondo binary adapter was experimental; use current browser writer or add a separately verified Python writer.'
    }

def write_y2l_from_bridge(*args, **kwargs):
    raise RuntimeError('Python Soundmondo binary emission is intentionally fail-closed in this development snapshot; use tools/ysfc_forge_sysex_converter_v1_27.html.')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('syx',type=Path)
    ap.add_argument('-o','--output',type=Path)
    ap.add_argument('--include-source-snapshot',action='store_true')
    args=ap.parse_args()
    bridge=build_intermediate(args.syx,args.include_source_snapshot)
    payload={'bridge':bridge,'preflight':preflight(bridge)}
    txt=json.dumps(payload,indent=2,ensure_ascii=False)
    if args.output: args.output.write_text(txt,encoding='utf-8')
    else: print(txt)
if __name__=='__main__': main()
