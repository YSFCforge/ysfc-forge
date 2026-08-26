import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))
import ysfc_serializer_adapter as a

def test_adapter_contract():
    assert a.ADAPTER_SCHEMA_VERSION >= 4
    try:
        a.write_y2l_from_bridge({})
    except RuntimeError as e:
        assert 'fail-closed' in str(e)
    else:
        raise AssertionError('binary adapter must fail closed')

if __name__=='__main__':
    test_adapter_contract(); print('Soundmondo adapter contract: OK')
