"""Read a private existing snapshot; write only counts/booleans, never raw values."""
import json,hashlib,copy,sys,types
from pathlib import Path
from datetime import date
P=Path(__file__).parent
sys.path.insert(0,str(P))
import juog_common as common
raw=Path('/tmp/juog_private_normalized_rows.json').read_bytes()
rows=json.loads(raw)
canonical=json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()
assert hashlib.sha256(canonical).hexdigest()=='1414934e5e059e3cc7882486fa7cf5ee14afe99b4ab5dce9736a3c665d0b0797'
groups={}
for r in rows[1:]:
 if r[2]!='SEALED':groups.setdefault(r[0],[]).append(r)
intents=[]
for g in groups.values():
 if g[0][1]=='intents':intents.append(json.loads(''.join(r[5] for r in sorted(g,key=lambda r:r[2]))))
snapshot=max(intents,key=lambda x:x['revision'])['after']['CRF_Drafts']
examined=removed=0
for r in snapshot[1:]:
 if len(r)>9 and 'SYNTHETIC-ID' in str(r[9]):
  examined+=1; original=json.loads(r[9]); before=copy.deepcopy(original)
  clean=common.redact_draft_identifiers(original)
  assert original==before
  assert 'SYNTHETIC-ID' not in json.dumps(clean,ensure_ascii=False)
  removed+=1
assert examined>0
# New draft capture and legacy restore use the same pinned common code; no transport.
st=types.ModuleType('streamlit');st.session_state={'peri_patient_name':'SYNTHETIC-ID','peri_age':64,'peri_birth_month':'1962-06','peri_clinical_date':date(2026,10,1),'peri_zero':0,'peri_nested':'{"patient_name":"SYNTHETIC-ID","grade":"IIIa"}','peri_note':'患者氏名は架空検証者'}
sys.modules['streamlit']=st
captured=common.capture_draft_state('peri_')
assert 'peri_patient_name' not in captured
assert 'SYNTHETIC-ID' not in json.dumps(captured,ensure_ascii=False)
assert captured['peri_age']['value']==64 and captured['peri_birth_month']['value']=='1962-06' and captured['peri_zero']['value']==0
assert captured['peri_clinical_date']['value']=='2026-10-01'
assert captured['peri_note']['value']=='[REDACTED]'
st.session_state={};common.restore_draft_state(captured)
assert st.session_state['peri_zero']==0 and st.session_state['peri_clinical_date']==date(2026,10,1)
assert common.redact_draft_identifiers('架空検証者')=='架空検証者'  # Known unlabeled-text detection limit, NOT a protection pass.
assert Path('/tmp/juog_private_normalized_rows.json').read_bytes()==raw
result={'mode':'OFFLINE_PINNED_COMMON_ON_EXISTING_PRIVATE_SNAPSHOT','legacy_drafts_with_marker':examined,'sanitized_projection_without_marker':removed,'original_snapshot_unchanged':True,'raw_values_exported':False,'capture_and_restore_preserve_age_birth_month_clinical_date_zero':True,'structured_nested_and_labelled_identifier_removed':True,'unlabelled_name_detection_limit_remains':True,'native_sheets_xlsx_is_not_sanitized':True,'live_read_export_route_verified':False,'formal_pass_delta':0}
(P/'privacy_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
