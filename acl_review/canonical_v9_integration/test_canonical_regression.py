import ast,json,logging,sys,subprocess,hashlib
from pathlib import Path
from datetime import date
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
logging.disable(logging.CRITICAL)
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
source=P/'02_perioperative_30d_crf.py'
wrapper='''import runpy, ast, json
import streamlit as st
from pathlib import Path
ns=runpy.run_path(SOURCE)
ns['data']=ns['build_submission']()['data']
st.session_state['_probe']={'path':ns['path'],'missing':ns['missing'],'errors':ns['errors'],'data':json.loads(json.dumps(ns['data'],default=str))}
'''.replace('SOURCE',repr(str(source)))
results=[]
def record(name,check):
 assert check,name
 results.append({'condition':name,'pass':True})
with patch('urllib.request.urlopen',side_effect=AssertionError('REAL_NETWORK_FORBIDDEN')) as net:
 a=AppTest.from_string(wrapper).run();assert not a.exception
 probe=lambda:a.session_state['_probe']
 record('unselected surgery not N/A and required',any('適用可否は未確定' in str(x.value) for x in a.info) and '手術実施有無' in probe()['missing'])
 a.radio(key='peri_surgery_performed').set_value('実施した').run()
 a.selectbox(key='peri_path_ypt').set_value('ypT0').run();assert not a.exception
 record('unselected dissection cannot yield pCR',probe()['data']['pathology']['ypn']=='' and not probe()['data']['pathology']['pcr'] and 'ypN' in probe()['missing'])
 a.number_input(key='peri_path_size_mm').set_value(0.0).run()
 record('zero retained in actual save-data constructor',probe()['data']['pathology']['size_mm']==0 and '病理最大径' not in probe()['missing'])
 a.radio(key='peri_ln_dissection').set_value('実施しなかった').run()
 record('explicit no dissection preserves ypT0Nx pCR',probe()['data']['pathology']['ypn']=='ypNX（郭清なし）' and probe()['data']['pathology']['pcr'] and not probe()['data']['pathology']['pcr_ypt0n0'])
 a.radio(key='peri_ln_dissection').set_value('実施した').run()
 a.selectbox(key='peri_path_ypn').set_value('ypN0').run()
 record('ypT0N0 pCR payload retained',probe()['data']['pathology']['pcr'] and probe()['data']['pathology']['pcr_ypt0n0'])
 a.selectbox(key='peri_path_ypn').set_value('ypN1').run()
 record('ypT0N1 not pCR',not probe()['data']['pathology']['pcr'])
 a.selectbox(key='peri_path_histology').set_value('評価不能').run()
 record('unevaluable reason conditionally required','病理評価不能理由' in probe()['missing'])
 a.text_area(key='peri_path_eval_failed_reason').set_value('架空試験：検体不十分').run()
 record('reason preserved in actual save-data constructor','病理評価不能理由' not in probe()['missing'] and probe()['data']['pathology']['eval_failed_reason']=='架空試験：検体不十分')
 a.date_input(key='peri_op_date').set_value(date(2026,10,1)).run()
 a.selectbox(key='peri_cd_grade').set_value('Grade IIIa').run()
 a.date_input(key='peri_cd_date').set_value(date(2026,11,1)).run()
 record('day31 rejected in canonical validation',any('30日以内' in e for e in probe()['errors']))
 a.date_input(key='peri_cd_date').set_value(date(2026,10,31)).run()
 record('day30 clears boundary error',not any('30日以内' in e for e in probe()['errors']))
 a.radio(key='peri_surgery_performed').set_value('実施しなかった').run()
 record('explicit no surgery serializes empty pathology',probe()['data']['pathology']=={} and '病理評価不能理由' not in probe()['missing'] and any('病理項目はN/A' in str(x.value) for x in a.info))
 record('no actual business network',net.call_count==0)
assert not a.exception
out={'mode':'OFFLINE_REAL_STREAMLIT_CANONICAL_SOURCE_AND_SAVE_DATA_CONSTRUCTOR','conditions':results,'live_save_performed':False,'pCR_live_fixture_test':False,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'formal_pass_delta':0}
(P/'regression_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
