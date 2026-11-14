import logging,json,sys
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
logging.disable(logging.CRITICAL)
p=Path(__file__).parent
results={}
with patch('urllib.request.urlopen',side_effect=AssertionError('BUSINESS_NETWORK_FORBIDDEN')) as network:
 a=AppTest.from_file(str(p/'uat_readonly_30d.py')).run()
 assert not a.exception
 assert len(a.button)==3 and all(x.disabled for x in a.button)
 results['three_business_buttons_disabled']=True
 assert not any('病理項目はN/A' in str(x.value) for x in a.info)
 results['unselected_surgery_not_NA']=True
 a.session_state['peri_sent']=True;a.session_state['draft30_flash']={'kind':'success','message':'OLD_SYNTHETIC_MARKER'};a.session_state['peri_registration_id']='OLD_SYNTHETIC_MARKER'
 a.run();assert not a.exception
 assert a.text_input(key='inspect_peri_registration_id').value==''
 assert all('OLD_SYNTHETIC_MARKER' not in str(x.value) for x in a.markdown)
 results['legacy_state_not_rendered']=True
 a.radio(key='inspect_peri_surgery_performed').set_value('実施した').run();assert not a.exception
 assert a.selectbox(key='inspect_peri_path_ypt')
 results['surgery_yes_pathology_visible']=True
 assert any('郭清の実施有無を選択' in str(x.value) for x in a.info)
 assert not any('郭清なしのためypN' in str(x.value) for x in a.info)
 results['unselected_dissection_not_NX']=True
 a.number_input(key='inspect_peri_path_size_mm').set_value(0.0).run();assert not a.exception
 assert a.number_input(key='inspect_peri_path_size_mm').value==0.0
 results['pathology_zero_retained']=True
 a.selectbox(key='inspect_peri_path_histology').set_value('評価不能').run();assert not a.exception
 assert a.text_area(key='inspect_peri_path_eval_failed_reason')
 results['unevaluable_pathology_reason_visible']=True
 a.radio(key='inspect_peri_surgery_performed').set_value('実施しなかった').run();assert not a.exception
 assert not any(x.key=='inspect_peri_path_ypt' for x in a.selectbox)
 assert any('病理項目はN/A' in str(x.value) for x in a.info)
 results['no_surgery_pathology_NA']=True
 assert all(x.disabled for x in a.button);assert network.call_count==0
 results['business_http_calls']=network.call_count
results['mode']='OFFLINE_REAL_STREAMLIT_WIDGET_TEST_NOT_LIVE_UAT'
(p/'widget_results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(results,ensure_ascii=False))
