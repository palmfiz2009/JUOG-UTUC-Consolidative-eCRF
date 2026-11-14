import sys,json,logging,subprocess
from pathlib import Path
from datetime import date
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
logging.disable(logging.CRITICAL)
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
seed={'peri_registration_id':'JUOG-971','peri_reporter_email':'fictional@example.invalid','peri_surgery_performed':'実施した','peri_last_evp_date':date(2026,3,16),'peri_op_admission_date':date(2026,4,12),'peri_op_date':date(2026,4,13),'peri_op_type':'根治的腎尿管全摘除術','peri_approaches':['ロボット支援'],'peri_op_completed':'はい','peri_op_time':180,'peri_bleeding':0,'peri_eau_grade':'Grade 0','peri_ln_dissection':'実施しなかった','peri_unrecovered_g2_relevant':'なし','peri_initial_hospital_outcome':'退院済み','peri_op_discharge_date':date(2026,4,20),'peri_readmission_30d':'なし','peri_day0_sbp':120,'peri_day0_dbp':70,'peri_day0_pulse':70,'peri_day0_temp':36.5,'peri_discharge_sbp':120,'peri_discharge_dbp':70,'peri_discharge_pulse':70,'peri_discharge_temp':36.5,'peri_discharge_lab_available':'なし','peri_path_histology':'Urothelial carcinoma','peri_path_subtype_presence':'なし','peri_path_size_mm':10.,'peri_path_locations':['腎盂'],'peri_path_ypt':'ypT1','peri_path_lvi':'なし','peri_path_r0':'R0','peri_path_trg':'TRG 2','peri_visit_date_30':date(2026,5,13),'peri_day30_lab_date':date(2026,5,13),'peri_day30_lab_CRP':'0','widget_peri_day30_lab_CRP':'0','peri_cd_grade':'Grade 0','peri_adj_plan':'無治療（経過観察）','peri_status_alive':'生存','peri_final_visit_date':date(2026,5,13)}
wrapper="import streamlit as st\nimport runpy\nns=runpy.run_path("+repr(str(P/'02_perioperative_30d_crf.py'))+")\nst.session_state['_payload']=ns['build_submission']()\nst.session_state['_validation']={'missing':ns['missing'],'errors':ns['errors']}\n"
a=AppTest.from_string(wrapper)
for k,v in seed.items():a.session_state[k]=v
with patch('urllib.request.urlopen',side_effect=AssertionError('NETWORK')):a.run()
assert not a.exception,[x.message for x in a.exception]
assert a.session_state['_validation']=={'missing':[],'errors':[]},a.session_state['_validation']
from canonical_v9_bridge import operation
from juog_common import redact_draft_identifiers
p=a.session_state['_payload'];op=operation('save_crf',{'payload':p},redact_draft_identifiers,{})
# Fixed synthetic submission fields only; no signature or personal principal.
op['payload']['submission_id']='OFFLINE-CANONICAL-971';op['payload']['submitted_at']='2026-11-14T00:00:00+09:00'
(P/'canonical_fixture.json').write_text(json.dumps(op,ensure_ascii=False,indent=2)+'\n')
result=subprocess.run(['node',str(P/'test_v9_validator.cjs')],input=json.dumps(op),text=True,capture_output=True)
print(result.stdout);assert result.returncode==0,result.stderr
# Exercise the SAME rendered canonical preview button; synthetic claims stay in memory.
from test_bridge import native,ctx
for key in ['draft30_save_button','draft30_load_button','draft30_submit_button']:
 assert a.button(key=key).disabled
with patch('uat_auth_connect.context',return_value=native), patch('urllib.request.urlopen',side_effect=AssertionError('NETWORK')):
 a.session_state['_canonical_acl_context']=ctx
 a.button(key='canonical_v9_preview').click().run()
assert not a.exception,[x.message for x in a.exception]
assert any('署名付き要求を生成しました' in x.value for x in a.info)
assert not any('保存しました' in x.value for x in a.success)
(P/'form_contract_results.json').write_text(json.dumps({'mode':'OFFLINE_REAL_STREAMLIT_WIDGETS_SYNTHETIC_IDENTITY','canonical_payload_validated_by_actual_v9':True,'preview_button_signs_without_http':True,'business_buttons_disabled':3,'missing':0,'errors':0,'formal_pass_delta':0},indent=2)+'\n')
