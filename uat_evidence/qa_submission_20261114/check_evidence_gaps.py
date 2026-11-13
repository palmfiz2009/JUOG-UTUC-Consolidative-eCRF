"""Read-only evidence extraction and exact pinned frontend checks; no live calls."""
import ast, hashlib, json, sys, types
from datetime import date, datetime
from pathlib import Path
P=Path(__file__).parent
results=[]
def check(name, condition):
    assert condition, name
    results.append({'name':name,'passed':True})
common=(P/'pinned_juog_common.py').read_bytes()
check('current helper source matches prior privacy evidence', hashlib.sha256(common).hexdigest()=='2c420f1ebf5ae056846b6d500df69fd44dd8101d1973b2ee4b27209eb78e8f62')
fake=types.ModuleType('streamlit'); fake.session_state={};sys.modules['streamlit']=fake
ns={'date':date,'datetime':datetime}
names={'clear_session_state_prefixes','restore_draft_state','is_direct_identifier_key','redact_draft_identifiers'}
for n in ast.parse(common).body:
    if isinstance(n,ast.FunctionDef) and n.name in names:
        exec(compile(ast.Module(body=[n],type_ignores=[]),'pinned-helpers','exec'),ns)
page=ast.parse((P/'pinned_02_perioperative_30d_crf.py').read_text())
blocks=[n for n in ast.walk(page) if isinstance(n,ast.If) and any(isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and isinstance(x.value.func,ast.Name) and x.value.func.id=='clear_session_state_prefixes' for x in n.orelse)]
check('successful draft branch clears before restoration', any('clear_session_state_prefixes' in ast.unparse(n.orelse[0]) and 'restore_draft_state' in ast.unparse(n.orelse[2]) for n in blocks))
fake.session_state={'peri_patient_name':'SYNTHETIC-ONLY','widget_peri_patient_name':'SYNTHETIC-ONLY','peri_old_lab':99,'other_page_value':42}
ns['clear_session_state_prefixes'](('peri_','widget_peri_'))
ns['restore_draft_state']({'peri_age':{'value':0},'peri_birth_year_month':{'value':'2000-02'},'peri_operation_date':{'type':'date','value':'2026-04-13'},'peri_patient_name':{'value':'SYNTHETIC-ONLY'}})
check('caller pair removes stale backing/widget identifiers and stale clinical values', all(k not in fake.session_state for k in ['peri_patient_name','widget_peri_patient_name','peri_old_lab']))
check('caller pair preserves zero partial birth month clinical date and unrelated state',fake.session_state=={'other_page_value':42,'peri_age':0,'peri_birth_year_month':'2000-02','peri_operation_date':date(2026,4,13)})
branches=[n for n in ast.walk(page) if isinstance(n,ast.If) and ast.unparse(n.test)=="surgery_performed == '実施した'" and any("missing.append('病理評価不能理由')" in ast.unparse(x) for x in n.body)]
check('pathology requirements nested under surgery performed',len(branches)==1)
check('no surgery branch requires reason and conditional other detail',bool(branches[0].orelse) and '手術未施行理由その他詳細' in ast.unparse(branches[0].orelse[0]))
projection=json.loads((P/'clinical_projection.json').read_text())
records={(r['table'],r['version']):r['data'] for r in projection['records']}
a=records['CRF_30d',2];b=records['CRF_90d',1];f=records['CRF_Followup',3]
days=lambda d,r:(date.fromisoformat(d)-date.fromisoformat(r)).days
check('saved 30d event is day30 with Grade IIIa',days(a['cd_event_date_30'],a['reference_date'])==30 and a['cd_grade_30']=='Grade IIIa')
check('saved 90d event is day31 distinct from day30',days(b['cd_event_date'],b['reference_date'])==31 and b['cd_grade_day31_90']=='Grade IIIa')
check('saved 90d refers to 30d version2',b['source_30d_record_version']==2)
check('saved zero clinical values survive corrected record',a['blood_loss_ml']==0 and a['pathology']['size_mm']==0 and a['day30_labs']['CRP']==0)
check('followup prior recurrence version and later progression version retained',records['CRF_Followup',1]['recist_progression_status']=='PDなし' and records['CRF_Followup',2]['recist_progression_status']=='今回PDあり')
check('latest followup retains recurrence progression death dates',f['intraluminal_recurrence_date']=='2026-10-01' and f['progression_date']=='2026-10-12' and f['death_date']=='2026-10-13' and f['death_cause']=='他病死')
out={'scope':'OFFLINE_PINNED_SOURCE_AND_PRIOR_LIVE_SNAPSHOT_NOT_NEW_LIVE_EXPORT','passed':len(results),'results':results,'formal_pass_delta':0,'limitations':['Clinical projection is an independent evidence extraction, not the application aggregation/export path.','Page AST and helper execution do not establish live screen accessibility or host/GAS log non-exposure.','Prior live snapshot timestamp and provenance are in commit409ff69; no current cloud state remeasurement.']}
(P/'evidence_gap_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(str(len(results))+' evidence gap checks passed')
