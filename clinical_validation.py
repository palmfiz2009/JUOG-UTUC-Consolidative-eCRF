"""Execute generated UI rules on canonical submitted fields, before any write.
No clinical policy invented here. Original protocol approval is a separate gate.
"""
import json,copy,re,math
from pathlib import Path
from datetime import date,timedelta
from types import SimpleNamespace
import juog_common as c
CONTRACT=json.loads(Path(__file__).with_name('clinical_contract').joinpath('contract.json').read_text())
def getpath(p,path):
 for key in path:
  if not isinstance(p,dict):return None
  p=p.get(key)
 return p

def context(p,today):
 spec=CONTRACT['contracts'][p['crf_type']];v={k:getpath(p,path) for k,path in spec['mapping'].items()}
 for key in spec['dates']:
  x=v.get(key)
  v[key]=date.fromisoformat(x) if isinstance(x,str) and x else None
 for key in ('day30_labs_raw','discharge_labs_raw','labs_raw','path'):
  if key in v and v[key] is None:v[key]={}
 d=p['data'];v['lab_status']=d.get('lab_status');v['cytology_not_done_now']=d.get('urine_cytology')=='未実施'
 if 'approaches' in v and v['approaches'] is None:v['approaches']=[]
 if 'source_30d_record_version' in v and v['source_30d_record_version'] in (None,''):v['source_30d_record_version']=0
 for w in CONTRACT['widgets']:
  if w['file']!=spec.get('file',{'perioperative_30d':'02_perioperative_30d_crf.py','day90':'03_day90_crf.py','followup':'04_followup_crf.py'}[p['crf_type']]):continue
  target=w['target']
  if target in v and v[target] in (None,''):
   if w['widget']=='number_input':v[target]=None
   elif w['widget']=='multiselect':v[target]=[]
   elif w['widget']=='selectbox':v[target]='選択してください'
   elif w['widget']=='radio':v[target]='' if target=='approach_pattern' else None
 v['st']=SimpleNamespace(session_state={'peri_op_other':d.get('operation_type_other',''),'peri_g2_detail':d.get('unrecovered_ae_detail',''),'peri_noop_other':d.get('no_operation_other','')})
 v.update({n:getattr(c,n) for n in ['text','valid_registration_id','valid_email','unique_messages','window_info','validate_vitals','validate_lab_panel','validate_cytology','add_months']})
 def optional(raw):
  parsed,errors,_=c.validate_lab_panel(raw,False)
  return parsed,[x.replace('数値またはNAで入力してください','数値で入力してください（未測定・欠測は空欄）') for x in errors]
 v.update(validate_optional_lab_panel=optional,today_jst=lambda:date.fromisoformat(today),timedelta=timedelta)
 return v

def validate_payload(p,today=None):
 today=today or c.today_jst().isoformat()
 try:
  if p.get('crf_type') not in CONTRACT['contracts'] or not isinstance(p.get('data'),dict):raise ValueError()
  spec=CONTRACT['contracts'][p['crf_type']]
  for key in ('day30_labs_raw','discharge_labs_raw','labs_raw','pathology'):
   if key in p['data'] and p['data'][key] is not None and not isinstance(p['data'][key],dict):raise ValueError()
  shape=[]
  for field in ('registration_id','reporter_email','facility_code','facility_name','submission_kind','correction_reason'):
   if p.get(field) is not None and type(p[field]) is not str:shape.append('TEXT_TYPE:'+field)
  source=p['data'].get('source_30d_record_version')
  if source not in (None,'') and (type(source) is not int or source<0):shape.append('VERSION_TYPE')
  if p['crf_type']=='followup':
   expected=p.get('visit','').replace('m','ヶ月')+('（終了）' if p.get('visit')=='24m' else '')
   if p['data'].get('visit_month')!=expected:shape.append('VISIT_LABEL_MISMATCH')
  pairs=[('day30_labs_raw','day30_labs'),('discharge_labs_raw','inpatient_labs')] if p['crf_type']=='perioperative_30d' else [('labs_raw','labs')]
  for raw,parsed in pairs:
   if p['crf_type']=='followup' and p['data'].get('lab_status')!='実施あり':continue
   expected=c.validate_lab_panel(p['data'].get(raw) or {},False)[0]
   if p['data'].get(parsed)!=expected:shape.append('LAB_REPRESENTATION:'+parsed)
  for name in spec['dates']:
   x=getpath(p,spec['mapping'][name])
   if x is not None and x!='':
    if type(x) is not str or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',x):shape.append('DATE_TYPE:'+name)
    else:
     try:date.fromisoformat(x)
     except ValueError:shape.append('DATE_INVALID:'+name)
  for w in CONTRACT['widgets']:
   if not w['path'] or not w['file'].startswith({'perioperative_30d':'02','day90':'03','followup':'04'}[p['crf_type']]):continue
   x=getpath(p,w['path']);rules=w['constraints']
   if x is None or x=='' or x==[]:continue
   if w['widget']=='number_input':
    if type(x) not in (int,float) or not math.isfinite(x):shape.append('NUMBER_TYPE:'+'.'.join(w['path']));continue
    for k,cmp in [('min_value',lambda a,b:a<b),('max_value',lambda a,b:a>b)]:
     if type(rules.get(k)) in (int,float) and cmp(x,rules[k]):shape.append('RANGE:'+'.'.join(w['path']))
   if w['widget'] in ('text_input','text_area') and type(x) is not str:shape.append('TEXT_TYPE:'+'.'.join(w['path']))
   if w['widget']=='checkbox' and type(x) is not bool:shape.append('BOOL_TYPE:'+'.'.join(w['path']))
   opts=rules.get('options')
   if isinstance(opts,list):
    values=x if w['widget']=='multiselect' and isinstance(x,list) else [x]
    if w['widget']=='multiselect' and not isinstance(x,list):shape.append('LIST_TYPE:'+'.'.join(w['path']))
    if any(type(z) is not str or z not in opts for z in values):shape.append('OPTION:'+'.'.join(w['path']))
  if shape:return {'ok':False,'missing':[],'errors':sorted(set(shape)),'warnings':[]}
  v=context(p,today);exec(compile(spec['source'],'<pinned-ui-validator>','exec'),v)
  result=v['validate_all']()
  return {'ok':not result[0] and not result[1],'missing':result[0],'errors':result[1],'warnings':result[2]}
 except (TypeError,ValueError,KeyError,AttributeError,NameError):
  return {'ok':False,'missing':[],'errors':['CLINICAL_SCHEMA_INVALID'],'warnings':[]}
