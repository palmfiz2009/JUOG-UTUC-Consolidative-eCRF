"""Compile pinned UI validation AST to GAS. No eval of remotely supplied code.
Unsupported syntax fails generation; source hashes and every condition are exported.
"""
import ast,json,hashlib,csv
from pathlib import Path
ROOT=Path(__file__).parent
class Compiler:
 def __init__(self):self.rules=[];self.filename=''
 def e(self,n):
  if isinstance(n,ast.Constant):return json.dumps(n.value,ensure_ascii=False)
  if isinstance(n,ast.Name):return 'v.'+n.id
  if isinstance(n,(ast.List,ast.Tuple,ast.Set)):return '['+','.join(self.e(x) for x in n.elts)+']'
  if isinstance(n,ast.Dict):return '{'+','.join(self.e(k)+':'+self.e(v) for k,v in zip(n.keys,n.values))+'}'
  if isinstance(n,ast.Subscript):return self.e(n.value)+'['+self.e(n.slice)+']'
  if isinstance(n,ast.Attribute):return self.e(n.value)+'.'+n.attr
  if isinstance(n,ast.UnaryOp):return '!ctTruth('+self.e(n.operand)+')' if isinstance(n.op,ast.Not) else '-('+self.e(n.operand)+')'
  if isinstance(n,ast.BoolOp):return '('+(' && ' if isinstance(n.op,ast.And) else ' || ').join('ctTruth('+self.e(x)+')' for x in n.values)+')'
  if isinstance(n,ast.BinOp):return 'ctBin('+json.dumps(type(n.op).__name__)+','+self.e(n.left)+','+self.e(n.right)+')'
  if isinstance(n,ast.Compare):return '('+' && '.join('ctCmp('+json.dumps(type(o).__name__)+','+self.e(a)+','+self.e(b)+')' for a,o,b in zip([n.left]+n.comparators,n.ops,n.comparators))+')'
  if isinstance(n,ast.IfExp):return '(ctTruth('+self.e(n.test)+')?'+self.e(n.body)+':'+self.e(n.orelse)+')'
  if isinstance(n,ast.JoinedStr):return '('+'+'.join('String('+self.e(x.value)+')' if isinstance(x,ast.FormattedValue) else self.e(x) for x in n.values)+')'
  if isinstance(n,(ast.GeneratorExp,ast.ListComp)):
   assert len(n.generators)==1;g=n.generators[0];assert isinstance(g.target,ast.Name)
   test='&&'.join('ctTruth('+self.e(x)+')' for x in g.ifs) or 'true'
   return 'Array.from('+self.e(g.iter)+').flatMap(_x=>{let v2=Object.assign({},v);v2.'+g.target.id+'=_x;return ((v)=>'+test+')(v2)?[((v)=>'+self.e(n.elt)+')(v2)]:[]})'
  if isinstance(n,ast.Call):
   args=[self.e(x) for x in n.args]+[self.e(x.value) for x in n.keywords]
   if isinstance(n.func,ast.Name):return 'ctHelpers(v).'+n.func.id+'('+','.join(args)+')'
   if isinstance(n.func,ast.Attribute):
    obj=self.e(n.func.value);method=n.func.attr
    if method=='get':return 'ctGet('+obj+','+','.join(args)+')'
    if method=='values':return 'Object.values('+obj+')'
    if method=='append':return obj+'.push('+','.join(args)+')'
    if method=='extend':return obj+'.push(...'+args[0]+')'
    if method=='join':return args[0]+'.join('+obj+')'
    if method=='isdigit':return '/^[0-9]+$/.test('+obj+')'
   raise ValueError(ast.unparse(n))
  raise ValueError(type(n).__name__)
 def target(self,n):
  if isinstance(n,(ast.Tuple,ast.List)):return '['+','.join(self.target(x) for x in n.elts)+']'
  return self.e(n)
 def stmt(self,n):
  if isinstance(n,ast.Assign):return ';'.join(self.target(t)+'='+self.e(n.value) for t in n.targets)+';'
  if isinstance(n,ast.Expr):return self.e(n.value)+';'
  if isinstance(n,ast.Return):return 'return '+self.e(n.value)+';'
  if isinstance(n,ast.For):return 'for(const _item'+str(n.lineno)+' of '+self.e(n.iter)+'){'+self.target(n.target)+'=_item'+str(n.lineno)+';'+self.body(n.body)+'}'
  if isinstance(n,ast.If):
   rid=self.filename[:2]+'-'+str(n.lineno);self.rules.append({'id':rid,'file':self.filename,'line':n.lineno,'condition':ast.unparse(n.test),'test':'clinical differential corpus','approval':'UI implementation baseline; protocol original NOT VERIFIED'})
   return 'if(ctTrace(v,'+json.dumps(rid)+',ctTruth('+self.e(n.test)+'))){'+self.body(n.body)+'}else{'+self.body(n.orelse)+'}'
  raise ValueError(type(n).__name__)
 def body(self,nodes):return '\n'.join(self.stmt(n) for n in nodes)

def build():
 import juog_common as common
 comp=Compiler();contracts={};js=[];widgets=[]
 for filename,kind in [('02_perioperative_30d_crf.py','perioperative_30d'),('03_day90_crf.py','day90'),('04_followup_crf.py','followup')]:
  source=(ROOT/filename).read_text();tree=ast.parse(source);fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='validate_all')
  data=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='data' for x in n.targets) and isinstance(n.value,ast.Dict))
  mapping={};dates=[]
  def extract(d,path):
   for k,v in zip(d.keys,d.values):
    field=path+[k.value]
    if isinstance(v,ast.Dict):extract(v,field)
    elif isinstance(v,ast.Name):mapping[v.id]=field
    elif isinstance(v,ast.Call) and isinstance(v.func,ast.Name) and v.func.id in ('text','date_str') and isinstance(v.args[0],ast.Name):
     mapping[v.args[0].id]=field
     if v.func.id=='date_str':dates.append(v.args[0].id)
  extract(data,['data'])
  mapping.update({k:[k] for k in ['facility_code','facility_name','registration_id','reporter_email','submission_kind','correction_reason']})
  if kind=='perioperative_30d':mapping.update(path=['data','pathology'],reference_date=['data','reference_date'],no_op_reason=['data','no_operation_reason'],day30_labs_raw=['data','day30_labs_raw'],discharge_labs_raw=['data','discharge_labs_raw'])
  else:mapping['labs_raw']=['data','labs_raw']
  if kind=='followup':mapping['lab_status']=['data','lab_status']
  if 'reference_date' not in dates:dates.append('reference_date')
  # Capture exact UI widgets (including constraints that are not in validate_all).
  for n in ast.walk(tree):
   if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr in ['radio','selectbox','multiselect','number_input','date_input','checkbox','text_input','text_area']:
    call=n.value;target=ast.unparse(n.targets[0]);kw={x.arg:x.value for x in call.keywords};row={'file':filename,'line':n.lineno,'target':target,'widget':call.func.attr,'label':ast.unparse(call.args[0]) if call.args else '', 'path':mapping.get(target), 'constraints':{}}
    if target.startswith('path['):row['path']=['data','pathology',ast.literal_eval(n.targets[0].slice)]
    for k in ('min_value','max_value'):
     if k in kw:
      try:row['constraints'][k]=ast.literal_eval(kw[k])
      except:row['constraints'][k]='UNRESOLVED:'+ast.unparse(kw[k])
    if call.func.attr in ('radio','selectbox','multiselect') and len(call.args)>1:
     try:row['constraints']['options']=ast.literal_eval(call.args[1])
     except:
      try:row['constraints']['options']=eval(compile(ast.Expression(call.args[1]),'<static-options>','eval'),{'__builtins__':{},**vars(common)})
      except:row['constraints']['options']=None
    # Literal hidden defaults (e.g. ypNX without dissection) are valid representations.
    if isinstance(row['constraints'].get('options'),list):
     for assign in ast.walk(tree):
      if isinstance(assign,ast.Assign) and any(ast.unparse(t)==target for t in assign.targets) and isinstance(assign.value,ast.Constant) and isinstance(assign.value.value,str) and assign.value.value:
       if assign.value.value not in row['constraints']['options']:row['constraints']['options'].append(assign.value.value)
    widgets.append(row)
  comp.filename=filename;js.append('function ctRules_'+kind+'(v){'+comp.body(fn.body)+'}')
  contracts[kind]={'source':ast.unparse(fn),'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'mapping':mapping,'dates':dates}
 output={'helper_source_sha256':hashlib.sha256((ROOT/'juog_common.py').read_bytes()).hexdigest(),'contracts':contracts,'rules':comp.rules,'widgets':widgets,'labs':common.LAB_FIELDS,'diff_keys':sorted(common.DIFF_KEYS)}
 (ROOT/'clinical_contract/contract.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
 (ROOT/'clinical_contract_generated.gs').write_text('// GENERATED: python build_clinical_contract.py\nconst CT_CONTRACT='+json.dumps(output,ensure_ascii=False,separators=(',',':'))+';\n'+'\n'.join(js)+'\n')
 with (ROOT/'clinical_contract/validation_conditions.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(comp.rules[0]));w.writeheader();w.writerows(comp.rules)
 # Inventory every widget call, including unassigned session-state details and helper widgets.
 inventory=[]
 for filename in sorted({w['file'] for w in widgets}):
  tree=ast.parse((ROOT/filename).read_text());parent={child:node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
  for node in ast.walk(tree):
   if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute) or node.func.attr not in ('radio','selectbox','multiselect','number_input','date_input','checkbox','text_input','text_area'):continue
   row=next((x for x in widgets if x['file']==filename and x['line']==node.lineno),None);guards=[];current=node
   while current in parent:
    child=current;current=parent[current]
    if isinstance(current,ast.If):guards.append(('ELSE ' if child in current.orelse else '')+ast.unparse(current.test))
   key=next((ast.unparse(x.value) for x in node.keywords if x.arg=='key'),'')
   path=row['path'] if row else None
   special={"'peri_op_other'":['data','operation_type_other'],"'peri_g2_detail'":['data','unrecovered_ae_detail'],"'peri_noop_other'":['data','no_operation_other']}
   path=path or special.get(key)
   if key in ("'peri_registration_id'","'d90_registration_id'","'fu_registration_id'"):path=['registration_id']
   display_only=any(k.arg=='disabled' and isinstance(k.value,ast.Constant) and k.value.value is True for k in node.keywords)
   status='MAPPED' if path else ('DYNAMIC_LAB_HELPER' if row and row['target']=='out[key]' else 'LOOKUP_ONLY' if 'lookup' in key else 'DISPLAY_ONLY' if display_only else 'REVIEW_UNMAPPED')
   related=[r['id'] for r in comp.rules if r['file']==filename and row and row['target'] in r['condition']]
   inventory.append({'file':filename,'line':node.lineno,'label':ast.unparse(node.args[0]) if node.args else '', 'widget':node.func.attr,'session_key':key,'payload_path':'.'.join(path or []),'visibility_guards':' AND '.join(reversed(guards)),'constraints':json.dumps(row['constraints'] if row else {},ensure_ascii=False),'rule_ids':' '.join(related),'server':'juogClinicalValidate_ + generated ctRules','test':'test_clinical differential corpus; clinical_witnesses.json','mapping_status':status,'clinical_approval':'PRIMARY_PROTOCOL_NOT_VERIFIED'})
 with (ROOT/'clinical_contract/input_specification.csv').open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(inventory[0]));writer.writeheader();writer.writerows(inventory)
 print(len(comp.rules),'conditions;',len(widgets),'widgets')
if __name__=='__main__':build()
