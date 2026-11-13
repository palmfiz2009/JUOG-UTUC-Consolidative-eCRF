"""Exact local frontend helper checks; no claim of live logging coverage."""
import ast, copy, hashlib, io, json, sys, types
from contextlib import redirect_stdout, redirect_stderr
from datetime import date, datetime
from pathlib import Path

source=Path(__file__).with_name('pinned_juog_common.py')
raw=source.read_bytes(); sha=hashlib.sha256(raw).hexdigest()
assert sha=='2c420f1ebf5ae056846b6d500df69fd44dd8101d1973b2ee4b27209eb78e8f62'
names={'capture_draft_state','restore_draft_state','is_direct_identifier_key','redact_draft_identifiers'}
fake=types.ModuleType('streamlit');fake.session_state={};sys.modules['streamlit']=fake
ns={'date':date,'datetime':datetime}
for node in ast.parse(raw).body:
 if isinstance(node,ast.FunctionDef) and node.name in names: exec(compile(ast.Module(body=[node],type_ignores=[]),'exact-pinned-helpers','exec'),ns)
clinical={'reg_age':0,'reg_birth_year_month':'2000-02','reg_operation_date':date(2026,4,13),'reg_labs':{'CRP':0,'Hb':12.3,'missing':None},'reg_followup':[False,0,{'生年月':'2000-02','手術日':'2026-04-13'}],'reg_note':'術後31日。2026年5月14日、再入院。'}
out=io.StringIO();err=io.StringIO()
with redirect_stdout(out),redirect_stderr(err):
 fake.session_state=copy.deepcopy(clinical);captured=ns['capture_draft_state']('reg_')
 fake.session_state={};ns['restore_draft_state'](captured)
 assert fake.session_state==clinical
 assert type(fake.session_state['reg_followup'][0]) is bool
 original={'nested':json.dumps({'ＭＲＮ':'SYNTHETIC-MARKER','age':0,'birth_year_month':'2000-02'}),'clinical':clinical['reg_note']}
 clean=ns['redact_draft_identifiers'](original)
 assert 'SYNTHETIC-MARKER' not in json.dumps(clean)
 assert json.loads(clean['nested'])=={'age':0,'birth_year_month':'2000-02'}
 assert clean['clinical']==clinical['reg_note']
 assert ns['redact_draft_identifiers']('架空検証者')=='架空検証者'
assert not out.getvalue() and not err.getvalue()
result={'scope':'OFFLINE_PINNED_HELPERS_ONLY','source_sha256':sha,'checks':['zero_age_lab_and_false_roundtrip','partial_birth_month_and_clinical_dates_retained','nested_json_identifier_removed_clinical_values_retained','helpers_stdout_stderr_empty'],'passed':4,'known_limitation':'Unlabelled fictional name retained; helper stdout/stderr checks do not cover browser, Streamlit hosting, transport or GAS logs.','formal_pass_delta':0}
Path(__file__).with_name('privacy_supplement_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('4 offline privacy supplement checks passed')
