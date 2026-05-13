"""
YSFC Forge — Enum Package v1.1

Komplett paket av Yamaha MODX M / Montage M enum-tabeller och konversioner.
Källa: Yamaha officiella listor (Effect Type List, Waveform List, etc.) +
binärverifierade enums från ESP UI.

Användning:
    from ysfc_enums import FX_TYPES, get_waveform_name, lookup
    from ysfc_enums import fx_types, waveforms, controllers
    
Eller importera specifika moduler:
    from ysfc_enums.fx_types import FX_TYPES, fx_for_slot
    from ysfc_enums.waveforms import get_waveform_name
"""

# Re-exportera alla submoduler
from . import fx_types
from . import fx_presets
from . import fx_parameters
from . import fx_tables
from . import waveforms
from . import controllers
from . import performance_categories
from . import arpeggios
from . import performances
from . import drum_kits
from . import fmx
from . import engine_enums

# Bekväm namnvy: huvuddata-strukturer
from .fx_types import (
    FX_TYPES, FX_TYPE_INDEX, FX_INDEX_TO_NAME,
    FX_REV_LIST, FX_VAR_LIST, FX_INSA_LIST, FX_INSB_LIST,
    FX_ADINS_LIST, FX_MAS_LIST, FX_VCM_LIST, FX_CATEGORIES,
    fx_type_index, fx_type_bytes, fx_name_from_bytes, fx_for_slot,
)
from .fx_presets import FX_PRESETS, get_presets
from .fx_parameters import FX_PARAMETERS, get_parameters, get_parameter, get_table_no
from .fx_tables import FX_DATA_TABLES, lookup, get_table_name, reverse_lookup
from .waveforms import (
    WAVEFORMS, get_waveform_name, get_waveform,
    waveforms_by_category, get_main_categories as get_waveform_main_categories,
)
from .controllers import (
    CONTROLLER_SOURCES, CONTROLLER_SOURCES_SHORT,
    CONTROLLER_DESTINATIONS, CONTROLLER_DESTINATIONS_SHORT,
    LFO_DESTINATIONS, KEY_CONTROLLER_DESTINATIONS,
    get_source_name, get_destination_name,
)
from .performance_categories import (
    PERFORMANCE_CATEGORIES, MAIN_CATEGORY_INDEX, INDEX_TO_MAIN_CATEGORY,
    get_main_categories, get_sub_categories,
)
from .arpeggios import ARPEGGIOS, get_arp_name, get_arpeggio
from .performances import PERFORMANCES, get_performance_name, get_performance
from .drum_kits import DRUM_KITS, get_kit_names, get_kit_mapping
from .fmx import FMX_ALGORITHM_COUNT, FMX_ALGORITHMS, get_algorithm_label

# Engine enums — uppdaterat efter skärmdump-genomgång
from .engine_enums import (
    # AN-X
    ANX_OSC_WAVEFORMS,
    ANX_FILTER_TYPES, ANX_FILTER_TYPE1, ANX_FILTER_TYPE2,
    ANX_LFO_SHAPES,
    ANX_FOLDER_TYPES, ANX_MODIFIER_WAVES,
    # AWM2
    AWM2_FILTER_TYPES,
    AWM2_ELEMENT_LFO_WAVES, AWM2_PART_LFO_WAVES, AWM2_LFO_WAVES,
    AWM2_ELEMENT_SWITCH,
    # FM-X
    FMX_SPECTRAL_FORM, FMX_OP_SWITCH,
    # Drum
    DRUM_KEY_RECEIVE_NOTE, DRUM_KEY_REVERSE, DRUM_KEY_SWITCH,
    # CA
    CA_CURVE_TYPE_MODE, CA_CURVE_PRESETS, CA_CURVE_USERS, CA_POLARITY,
    CURVE_TYPES, POLARITY,
    # Common
    ON_OFF, MIDI_CHANNELS, RECEIVE_SWITCH, SCENE_NUMBERS,
    EQ_TYPE, FX_ON_OFF, SIDE_CHAIN,
    RIBBON_MODE, SLIDER_DIRECTION, RIBBON_GRID_MODE, RIBBON_ASSIGN_MODE,
    # Pan helpers
    encode_pan, decode_pan, pan_label,
)


__version__ = '1.2.0'
__all__ = [
    # Modules
    'fx_types', 'fx_presets', 'fx_parameters', 'fx_tables',
    'waveforms', 'controllers', 'performance_categories',
    'arpeggios', 'performances', 'drum_kits', 'fmx', 'engine_enums',
]
