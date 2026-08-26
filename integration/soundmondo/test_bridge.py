import unittest
import ysfc_bridge as yb


def base_perf(engine='AWM2'):
    return {
        'schema_version': 4, 'source_profile': 'MODX/MODX+', 'model_id': '07',
        'name': 'Bridge Test', 'tempo_bpm': 120, 'volume': 100, 'pan': 0,
        'main_category_code': 0, 'sub_category_code': 0,
        'arp_master_on': True, 'motion_seq_master_on': False,
        'transport_invalid_message_count': 0, 'normalization_warnings': [], 'provenance': {},
        'scenes': [],
        'parts': [{
            'number': 1, 'name': 'Part 1', 'engine': engine, 'part_type': 'normal',
            'enabled': True, 'mode': 'internal', 'keyboard_control': True, 'mute': False,
            'volume': 100, 'pan': 0, 'main_category_code': 0, 'sub_category_code': 0,
            'velocity_limit': {'low':1,'high':127}, 'note_limit': {'low':0,'high':127},
            'pitch': {'note_shift_semitones':0},
            'effects': {'reverb_send':12,'variation_send':0,'dry_level':127,'insertion':{}},
            'arpeggio': {'switch_on':True,'play_only':False,'loop_on':True,
                         'slots':[{'slot':1,'status':'assigned','bank':'preset','arp_number':4321,'raw_number':4321,'provenance':{}}]},
            'engine_data': {'elements': []} if engine=='AWM2' else {},
            'observed_block_categories': [], 'provenance': {}
        }]
    }

class BridgeTests(unittest.TestCase):
    def test_slot_identity_is_not_arp_number(self):
        b=yb.build_ysfc_intermediate(base_perf())
        s=b['performance']['parts'][0]['arpeggio']['slots'][0]
        self.assertEqual(s['slot_number'],1)
        self.assertEqual(s['slot_index'],0)
        self.assertEqual(s['number'],4321)

    def test_preset_arp_is_not_external_dependency(self):
        b=yb.build_ysfc_intermediate(base_perf())
        self.assertEqual(b['dependencies'],[])

    def test_library_arp_is_dependency(self):
        p=base_perf(); a=p['parts'][0]['arpeggio']['slots'][0]
        a.update(bank='library2',arp_number=12,raw_number=10763)
        b=yb.build_ysfc_intermediate(p)
        self.assertEqual(b['dependencies'][0]['kind'],'external_arpeggio')

    def test_anx_blocks_classic_only(self):
        b=yb.build_ysfc_intermediate(base_perf('AN-X'))
        self.assertEqual(b['target_assessment']['classic_x7l_4_0_5']['bridge_status'],'blocked')
        self.assertEqual(b['target_assessment']['modx_m_y2l']['bridge_status'],'candidate')

    def test_external_waveform_dependency(self):
        p=base_perf(); p['parts'][0]['engine_data']={'elements':[{'number':1,'wave_bank':'User','wave_bank_code':1,'wave_number':7}]}
        b=yb.build_ysfc_intermediate(p)
        self.assertEqual(b['dependencies'][0]['kind'],'external_waveform')
        self.assertEqual(b['target_assessment']['modx_m_y2l']['bridge_status'],'dependency_required')

    def test_coverage_is_explicitly_partial(self):
        b=yb.build_ysfc_intermediate(base_perf())
        self.assertEqual(b['coverage']['semantics'],'partial_but_provenance_preserving')
        self.assertIn('binary serializer field offsets and final X7L/Y2L emission', b['coverage']['deferred'])

if __name__=='__main__': unittest.main()
