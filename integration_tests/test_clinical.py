import unittest,json,copy,subprocess,ast,random
from pathlib import Path
from clinical_validation import validate_payload,CONTRACT
ROOT=Path(__file__).resolve().parents[1]
FIX=json.loads((ROOT/'clinical_contract/valid_fixtures.json').read_text())
def put(p,path,value):
 d=p
 for k in path[:-1]:
  if not isinstance(d.get(k),dict):d[k]={}
  d=d[k]
 d[path[-1]]=value

def corpus():
 cases=[]
 for kind,base in FIX.items():
  spec=CONTRACT['contracts'][kind];seeds=[copy.deepcopy(base)]
  operated=copy.deepcopy(base);operated['data']['surgery_performed']='実施した';operated['data']['operation_date']='2026-01-10';operated['data']['pathology']={};seeds.append(operated)
  full=copy.deepcopy(operated)
  for w in CONTRACT['widgets']:
   if not w['file'].startswith({'perioperative_30d':'02','day90':'03','followup':'04'}[kind]) or not w['path']:continue
   opts=w['constraints'].get('options');val=None
   if opts:val=next((v for v in opts if v!='選択してください'),'');val=[val] if w['widget']=='multiselect' else val
   elif w['widget']=='number_input':val=max(1,w['constraints'].get('min_value',1))
   elif w['widget']=='date_input':val='2026-02-09' if kind=='perioperative_30d' else '2026-04-10'
   elif w['widget']=='checkbox':val=False
   elif w['widget'] in ('text_input','text_area'):val='FICTIONAL'
   if val is not None:put(full,w['path'],val)
  full.update(registration_id='JUOG-901',reporter_email='fictional@example.invalid',facility_code='TEST01',facility_name='FICTIONAL');seeds.append(full)
  complex_case=copy.deepcopy(full)
  complex_case['data'].update(initial_hospital_outcome='退院済み',readmission_30d='あり',discharge_date='2026-01-15',readmission_date='2026-01-20',readmission_day30_status='再退院済み',intraluminal_recurrence='あり',intraluminal_recurrence_status='今回新規あり',intraluminal_treatment=['TURBT','BCG注入療法','その他'],intraluminal_treatment_status='実施済み・継続中',intraluminal_instillation_ongoing=False,intraluminal_recurrence_date='2026-02-01',intraluminal_instillation_start='2026-02-10',intraluminal_instillation_end='2026-02-09')
  seeds.append(complex_case)
  for seed in seeds:
   cases.append(seed)
   for name,path in spec['mapping'].items():
    vals=[None,'',0,False,True,'INVALID']
    for node in ast.walk(ast.parse(spec['source'])):
     if isinstance(node,ast.If) and any(isinstance(x,ast.Name) and x.id==name for x in ast.walk(node.test)):
      vals += [x.value for x in ast.walk(node.test) if isinstance(x,ast.Constant) and isinstance(x.value,(str,int,float))]
    if name in spec['dates']:vals+=['2027-01-01','2026-01-09','2026-01-10','2026-02-09','2026-04-10','2026-02-30']
    for w in CONTRACT['widgets']:
     if w['path']==path and w['file'].startswith({'perioperative_30d':'02','day90':'03','followup':'04'}[kind]):
      opts=w['constraints'].get('options')
      if opts:vals+= [[x] for x in opts] if w['widget']=='multiselect' else opts
      for k in ('min_value','max_value'):
       v=w['constraints'].get(k)
       if isinstance(v,(int,float)):vals += [v-1,v,v+1]
    for value in vals:
     p=copy.deepcopy(seed);put(p,path,value);cases.append(p)
   for w in CONTRACT['widgets']:
    if not w['path'] or not w['path'][:2]==['data','pathology'] or kind!='perioperative_30d':continue
    for value in [None,'',0]+(w['constraints'].get('options') or []):
     p=copy.deepcopy(seed);put(p,w['path'],[value] if w['widget']=='multiselect' and value else value);cases.append(p)
 # Multi-field clinical branches cannot be covered by one-field mutations alone.
  combos=[
   {'surgery_performed':'実施した','op_date':'2026-01-10','approaches':['開腹','腹腔鏡'],'approach_pattern':''},
   {'surgery_performed':'実施した','op_date':'2026-01-10','reference_date':'2026-01-10','cd_grade':'Grade II','new_complication':'あり','cd_date':'2026-01-09','renal_exception':True,'renal_exception_detail':''},
   {'surgery_performed':'実施した','op_date':'2026-01-10','reference_date':'2026-01-10','cd_grade':'Grade II','new_complication':'あり','cd_date':'2026-04-11'},
   {'surgery_performed':'実施した','op_date':'2026-01-10','status_alive':'死亡','death_date':'2027-01-01'},
   {'surgery_performed':'実施した','op_date':'2026-01-10','status_alive':'死亡','death_date':'2026-01-09'},
   {'imaging_status':'実施','recist_status':'PDあり' if kind=='day90' else '今回PDあり','progression_date':None,'progression_sites':[],'progression_detail':''},
   {'cystoscopy_status':'実施','cystoscopy_result':'腫瘍あり','cystoscopy_detail':''},
   {'intra_status':'あり' if kind=='day90' else '今回新規あり','intra_sites':['その他'],'intra_site_other':'','intra_tx':['経過観察','TURBT']},
   {'imaging_date':'2026-07-10','cystoscopy_date':'2026-07-10'},
  ]
  for changes in combos:
   p=copy.deepcopy(full)
   for name,value in changes.items():
    if name in spec['mapping']:put(p,spec['mapping'][name],value)
   cases.append(p)
  from juog_common import lab_payload
  for raw,parsed in ([('day30_labs_raw','day30_labs'),('discharge_labs_raw','inpatient_labs')] if kind=='perioperative_30d' else [('labs_raw','labs')]):
   for value in ('','NA','0','NaN','Infinity','0x10','1_0','1e2',False,None):
    p=copy.deepcopy(full);p['data'][raw]={'WBC':value};p['data'][parsed]=lab_payload(p['data'][raw]);cases.append(p)
  if kind=='perioperative_30d':cases.append(json.loads((ROOT/'clinical_contract/operated_fixture.json').read_text()))
  for field,values in [('registration_id',[' juog-901 ','JUOG-９０１','JUOG-00001']),('reporter_email',[' fictional@example.invalid ','a@b','a@@b.c'])]:
   for value in values:
    p=copy.deepcopy(base);p[field]=value;cases.append(p)
 return cases
class Clinical(unittest.TestCase):
 def test_unselected_visit_rejected_before_rule_04_394(self):
  p=copy.deepcopy(FIX['followup']);p['data']['visit_month']='選択してください'
  self.assertIn('VISIT_LABEL_MISMATCH',validate_payload(p)['errors'])
 def test_operated_positive(self):
  p=json.loads((ROOT/'clinical_contract/operated_fixture.json').read_text())
  self.assertTrue(validate_payload(p,'2026-11-16')['ok'])
 def test_positive_all_visits(self):
  for kind,p in FIX.items():
   for visit in (['6m','9m','12m','15m','18m','21m','24m'] if kind=='followup' else [p['visit']]):
    p=copy.deepcopy(p);p['visit']=visit;p['record_key']='JUOG-901|'+kind+'|'+visit
    if kind=='followup':p['data']['visit_month']=visit.replace('m','ヶ月')+('（終了）' if visit=='24m' else '')
    self.assertTrue(validate_payload(p,'2026-11-16')['ok'],(kind,visit,validate_payload(p,'2026-11-16')))
 def test_differential_ui_gas(self):
  cases=corpus();result=subprocess.run(['node','integration_tests/clinical_differential.cjs'],input=json.dumps(cases),text=True,capture_output=True,cwd=ROOT,check=True)
  js=json.loads(result.stdout);coverage={};witness={};diff=[]
  self.assertEqual(len(js),len(cases))
  for i,(p,r) in enumerate(zip(cases,js)):
   py=validate_payload(p,'2026-11-16')
   if py!=r['result']:diff.append({'index':i,'type':p['crf_type'],'payload':p,'python':py,'gas':r['result']})
   for key,values in r['trace'].items():
    for value in values:
     coverage.setdefault(key,set()).add(value);witness.setdefault(key,{}).setdefault(str(value),i)
  (ROOT/'integration_evidence/clinical_witnesses.json').write_text(json.dumps(witness,indent=2))
  report={'cases':len(cases),'differences':len(diff),'conditions':len(CONTRACT['rules']),'covered_conditions':len(coverage),'both_outcomes':sum(len(v)==2 for v in coverage.values()),'uncovered':[r['id'] for r in CONTRACT['rules'] if r['id'] not in coverage],'single_outcome':[k for k,v in coverage.items() if len(v)<2],'formal_uat_pass_delta':0}
  (ROOT/'integration_evidence/clinical_coverage.json').write_text(json.dumps(report,indent=2))
  (ROOT/'integration_evidence/clinical_differences.json').write_text(json.dumps(diff,ensure_ascii=False,indent=2))
  self.assertEqual(len(diff),0,report)
 def test_missing_dates_and_false_are_not_valid_numbers(self):
  p=copy.deepcopy(FIX['perioperative_30d']);p['data']['day30_visit_date']=None;self.assertFalse(validate_payload(p)['ok'])
  p=copy.deepcopy(FIX['perioperative_30d']);p['data']['operation_time_min']=False;self.assertFalse(validate_payload(p)['ok'])
class LiveApproachRegression(unittest.TestCase):
 def test_unselected_multiple_approach_ui_and_server_both_reject(self):
  from clinical_validation import context
  p=json.loads((ROOT/'clinical_contract/operated_fixture.json').read_text())
  p['data']['approaches']=['開腹','腹腔鏡']
  for selection in (None, ''):
   p['data']['approach_pattern']=selection
   # Simulate actual st.radio(index=None), without the payload adapter's
   # legacy normalization from None to empty string.
   v=context(p,'2026-11-27');v['approach_pattern']=selection
   exec(compile(CONTRACT['contracts']['perioperative_30d']['source'],'<ui-rule>','exec'),v)
   missing=v['validate_all']()[0]
   self.assertIn('複数アプローチの区分',missing)
   self.assertFalse(validate_payload(p,'2026-11-27')['ok'])
  p['data']['approach_pattern']='予定されたハイブリッド'
  self.assertTrue(validate_payload(p,'2026-11-27')['ok'])

if __name__=='__main__':unittest.main()
