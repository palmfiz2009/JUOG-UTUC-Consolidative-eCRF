import copy,hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent
work=root.parents[2]; old=work/'session-b2/uat_evidence/uat67_execution_20261113'
source=Path('/workspace/shared/juog_auth04_editor_v5.gs').read_text()
assert hashlib.sha256(source.encode()).hexdigest()=='99b602bb7cbfd8672f0478c1eb0a21daa68891ae746428e2ae7d082b4d7504a5'
base=json.loads((old/'surgical_fixture_candidate.json').read_text())['payload'];base['submission_id']='B971-30D-V1'
other=json.loads((old/'fixture_candidate.json').read_text())['crfs'][1:]
for p in other:
 p['registration_id']='JUOG-971';p['record_key']=p['record_key'].replace('970','971');p['submission_id']=('B971-90D-V1' if p['visit']=='90d' else 'B971-FUP-V1')
 p['data']['surgery_performed']='実施した';p['data']['source_30d_submission_id']='B971-30D-V1'
other[0]['data']['new_surgical_complication_day31_90']='なし'
steps=[]
def add(name,ids,p,error=None):
 steps.append(dict(name=name,uat_ids=ids,payload=copy.deepcopy(p),expected_error=error))
event=dict(cd_grade_30='Grade IIIa',cd_event_date_30='2026-05-13',cd_detail_30='完全架空処置イベント',cd_surgery_relation='関連する')
normal=copy.deepcopy(base);normal['data'].update(event)
bad=copy.deepcopy(normal);bad['data']['cd_event_date_30']='2026-05-14';bad['submission_id']='B971-30D-DAY31-REFUSED'
add('30日CRFの31日イベント拒否',['POST-02'],bad,'VALIDATION_FAILED')
add('30日イベント初回保存',['POST-01','POST-03'],normal)
bad=copy.deepcopy(normal);bad.update(submission_id='B971-PATH-REFUSED',submission_kind='訂正報告',expected_record_version=1,correction_reason='完全架空病理訂正');bad['data']['pathology']['ypt']='評価不能'
add('病理理由欠落拒否',['POST-04'],bad,'VALIDATION_FAILED')
fixed=copy.deepcopy(bad);fixed['submission_id']='B971-30D-V2';fixed['data']['pathology']['eval_failed_reason']='完全架空評価不能理由';fixed['data']['pathology']['size_mm']=0
add('病理理由復元と数値0保持',['POST-04'],fixed)
d90=copy.deepcopy(other[0]);d90['submission_id']='B971-90D-STALE-REFUSED'
add('旧30日参照版拒否',['POST-06'],d90,'VALIDATION_FAILED')
d90['submission_id']='B971-90D-V1';d90['data'].update(source_30d_record_version=2,source_30d_submission_id='B971-30D-V2',new_surgical_complication_day31_90='あり',cd_grade_day31_90='Grade IIIa',cd_event_date='2026-05-14',cd_detail='完全架空31日イベント',cd_surgery_relation='関連する')
add('正しい参照版と31日イベント保存',['POST-02','POST-06'],d90)
fu=copy.deepcopy(other[1]);fu['data'].update(source_30d_record_version=2,source_30d_submission_id='B971-30D-V2',intraluminal_recurrence_status='今回新規あり');fu['submission_id']='B971-FUP-RECUR-REFUSED'
add('再発詳細欠落拒否',['FUP-02'],fu,'VALIDATION_FAILED')
fu['submission_id']='B971-FUP-V1';fu['data'].update(intraluminal_recurrence_date='2026-10-01',intraluminal_sites=['膀胱'],intraluminal_treatment=['経過観察'])
add('再発情報復元と保存',['FUP-01','FUP-02'],fu)
pd=copy.deepcopy(fu);pd.update(submission_id='B971-FUP-PD-REFUSED',submission_kind='訂正報告',expected_record_version=1,correction_reason='完全架空進行情報訂正');pd['data'].update(recist_progression_status='今回PDあり',progression_date='2026-10-14',progression_sites=['肺'],progression_detail='完全架空進行')
add('評価日後のPD拒否',['FUP-02'],pd,'VALIDATION_FAILED')
pd['submission_id']='B971-FUP-V2';pd['data']['progression_date']='2026-10-12';add('PD日復元と保存',['FUP-01','FUP-02'],pd)
death=copy.deepcopy(pd);death.update(submission_id='B971-FUP-DEATH-REFUSED',expected_record_version=2,correction_reason='完全架空死亡情報訂正');death['data'].update(vital_status='死亡',death_date='2026-10-13')
add('死亡原因欠落拒否',['FUP-02'],death,'VALIDATION_FAILED')
death['submission_id']='B971-FUP-V3';death['data']['death_cause']='他病死';add('死亡情報復元と保存',['FUP-01','FUP-02'],death)
manifest={'fixture_id':'JUOG-971','facility_code':'TEST01','fictional_only':True,'crfs':[base,*other],'steps':steps,'preserve_existing_970':True}
raw=json.dumps(manifest,ensure_ascii=False,indent=2)+'\n';(root/'uat_auth04_fixture.json').write_text(raw);sha=hashlib.sha256(raw.encode()).hexdigest()
start=source.index('function juogAuth04ScopeConfigured_');end=source.index('// SOURCE: provision_auth04_keys.gs',start)
scope=source[start:end].replace('JUOG-970','JUOG-971').replace('0747f9ac3f59a6e230cc6cc6debaebde3138578ec82741567e995ab1e2d0d126',sha)
scope=scope.replace('return c.auth04ScopeReviewed===true',"return Number.isFinite(c.b971ExecutionUntil) && Date.now()<c.b971ExecutionUntil && c.auth04ScopeReviewed===true")
candidate=source[:start]+scope+source[end:]
candidate=candidate.replace("function guard(){\n  if(now()>=a.deadline", "function guard(){\n  if(c.sessionExecutionStage==='AUTH04_APPROVED'&&(!Number.isFinite(c.b971ExecutionUntil)||Date.now()>=c.b971ExecutionUntil))throw Error('AUTH04_SCOPE_DENIED');\n  if(now()>=a.deadline")
candidate=candidate.replace("if(now()>=a.deadline||now()>=auth.expires)throw Error('AUTH_EXPIRED');\n }\n if(revoke)","if(now()>=a.deadline||now()>=auth.expires)throw Error('AUTH_EXPIRED');\n  if(c.sessionExecutionStage==='AUTH04_APPROVED'&&Date.now()>=c.b971ExecutionUntil)throw Error('AUTH04_SCOPE_DENIED');\n }\n if(revoke)")
candidate+='\nconst B971_FIXTURE_SHA='+json.dumps(sha)+';\n'+(root/'provision971.gs').read_text()
(root/'bundle_candidate.gs').write_text(candidate)
cfg=(work/'auth-connect/auth04_config.py').read_text().replace('JUOG-970','JUOG-971').replace('0747f9ac3f59a6e230cc6cc6debaebde3138578ec82741567e995ab1e2d0d126',sha)
(root/'auth04_config.py').write_text(cfg)
runtime=json.loads((work/'auth-connect/auth04_runtime.json').read_text());runtime.update(enabled=False,fixture_id='JUOG-971',fixture_sha256=sha,approval_ref='PI_B971_CONDITIONAL_EXECUTION_20261113',review_ref='',prerequisites_verified=False)
(root/'auth04_runtime.json').write_text(json.dumps(runtime,ensure_ascii=False,indent=2)+'\n')
ident={'base_gas_sha256':hashlib.sha256(source.encode()).hexdigest(),'candidate_gas_sha256':hashlib.sha256(candidate.encode()).hexdigest(),'fixture_sha256':sha,'state':'CANDIDATE_NOT_DEPLOYED_REVIEW_PENDING','operations':len(steps)}
(root/'source_identity.json').write_text(json.dumps(ident,indent=2)+'\n');print(json.dumps(ident))
