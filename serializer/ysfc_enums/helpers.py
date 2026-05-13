"""
YSFC Forge — High-level Helper Functions

Convenience-funktioner som kombinerar flera enum-tabeller för
typiska patch editor use-cases.
"""

from . import fx_types as _ft
from . import fx_tables as _tbl
from . import fx_parameters as _fp


def fx_param_value_label(fx_name, param_no, raw_value):
    """Convert raw FX parameter value to UI display string.
    
    Combines:
    - FX_PARAMETERS to find the table_no for parameter
    - FX_DATA_TABLES to convert raw → UI value
    
    Args:
        fx_name: 'SPX HALL', 'CROSS DELAY', etc.
        param_no: 1-26 (parameter index within effect)
        raw_value: raw byte value from blob
    
    Returns:
        str: UI display value (e.g. "0.04 Hz", "5.5 s")
    """
    table_no = _fp.get_table_no(fx_name, param_no)
    if table_no is None:
        return str(raw_value)
    return _tbl.lookup(table_no, raw_value)


def fx_byte_to_name(lo_byte, hi_byte):
    """Convert (lo, hi) bytes to FX name."""
    return _ft.fx_name_from_bytes(lo_byte, hi_byte)


def fx_name_to_bytes(name):
    """Convert FX name to (lo, hi) bytes."""
    return _ft.fx_type_bytes(name)


def get_dropdown_options(slot_or_field):
    """Returns list of (display_name, value) tuples for UI dropdowns.
    
    Args:
        slot_or_field: 'rev', 'var', 'insa', 'insb', 'mas', 
                       eller specific field name from engine_enums
    
    Returns:
        list of (display_name, raw_value) tuples
    """
    # FX slots
    if slot_or_field in ('rev', 'var', 'insa', 'insb', 'adins', 'mas', 'vcm'):
        return [(name, idx) for idx, name in _ft.fx_for_slot(slot_or_field)]
    
    # Generiska enums (kommer från engine_enums)
    from . import engine_enums as ee
    enum_dict = getattr(ee, slot_or_field.upper(), None)
    if enum_dict is not None and isinstance(enum_dict, dict):
        return [(name, val) for val, name in enum_dict.items()]
    
    return []


if __name__ == '__main__':
    # Demo
    print("fx_param_value_label('SPX HALL', 1, 30):")
    print(f"  → {fx_param_value_label('SPX HALL', 1, 30)}")
    
    print("\nfx_byte_to_name(2, 1):")
    print(f"  → {fx_byte_to_name(2, 1)}")
    
    print("\nget_dropdown_options('rev') (Reverb-slot dropdown):")
    opts = get_dropdown_options('rev')
    for name, val in opts[:5]:
        print(f"  {val}: {name}")
