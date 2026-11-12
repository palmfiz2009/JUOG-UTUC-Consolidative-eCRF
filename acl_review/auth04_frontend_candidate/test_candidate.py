"""Execute exact candidate helper AST, never imports/runs application/network."""
import ast,copy,json,subprocess,sys,types,unittest,hashlib
from datetime import date,datetime,timezone
from pathlib import Path
ROOT=Path(__file__).parent
ID=json.loads((ROOT/'source_identity.json').read_text())
NAMES=set(ID['changed_functions'])
def nodes(path):return {n.name:n for n in ast.parse(Path(path).read_text()).body if isinstance(n,ast.FunctionDef)}
class TestCandidate(unittest.TestCase):
 def setUp(self):
  self.fake=types.ModuleType('streamlit');self.fake.session_state={}
  self.old=sys.modules.get('streamlit');sys.modules['streamlit']=self.fake
  self.ns={'date':date,'datetime':datetime}
  for name,node in nodes(ROOT/'juog_common.py').items():
   if name in NAMES:exec(compile(ast.Module(body=[node],type_ignores=[]),'candidate','exec'),self.ns)
 def tearDown(self):
  if self.old is None:sys.modules.pop('streamlit',None)
  else:sys.modules['streamlit']=self.old
 def test_only_four_functions_changed_and_proven_exact(self):
  before,after,proven=nodes(ID['base']),nodes(ROOT/'juog_common.py'),nodes(ID['proven'])
  for name in NAMES:self.assertEqual(ast.dump(after[name]),ast.dump(proven[name]))
  for name in set(before)-NAMES:self.assertEqual(ast.dump(before[name]),ast.dump(after[name]),name)
  self.assertEqual(hashlib.sha256(Path(ID['base']).read_bytes()).hexdigest(),ID['base_sha256'])
 def test_capture_identifier_keys_unicode_and_override(self):
  self.fake.session_state={'regDOB':'fictional','regＭＲＮ':'fictional','reg_birth_year_month':'1980-01','reg_age':46,'other_note':'untouched'}
  old=copy.deepcopy(self.fake.session_state)
  got=self.ns['capture_draft_state']('reg',overrides={'regFirstName':'fictional','reg_note':'患者氏名は架空検証者'})
  self.assertEqual(set(got),{'reg_birth_year_month','reg_age','reg_note'})
  self.assertEqual(got['reg_note']['value'],'[REDACTED]');self.assertEqual(old,self.fake.session_state)
 def test_roundtrip_clinical_types(self):
  values={'reg_birth_year_month':'1980-01','reg_age':46,'reg_date':date(2026,11,1),'reg_time':datetime(2026,11,1,tzinfo=timezone.utc),'reg_zero':0,'reg_false':False,'reg_null':None,'reg_list':[0,None,False,{'clinical_note':'手術日は2026年12月6日'}]}
  self.fake.session_state=copy.deepcopy(values);draft=self.ns['capture_draft_state']('reg_');self.fake.session_state={};self.ns['restore_draft_state'](draft)
  self.assertEqual(self.fake.session_state,values)
  for k,v in values.items():self.assertIs(type(self.fake.session_state[k]),type(v))
 def test_legacy_restore_sanitizes_without_mutating_source(self):
  draft={'regDOB':{'type':'date','value':'1980-01-02'},'reg_blob':{'type':'value','value':{'patient_name':'fictional','nested':[json.dumps({'regＭＲＮ':'fictional','age':46})]}},'reg_birth_year_month':{'type':'value','value':'1980-01'}}
  old=copy.deepcopy(draft);self.ns['restore_draft_state'](draft)
  self.assertNotIn('regDOB',self.fake.session_state);self.assertEqual(draft,old)
  self.assertEqual(json.loads(self.fake.session_state['reg_blob']['nested'][0]),{'age':46})
 def test_capture_prefix_exclusion_preserved(self):
  self.fake.session_state={'reg_age':46,'reg_skip_note':'clinical','fu_age':50}
  self.assertEqual(set(self.ns['capture_draft_state']('reg_',exclude_prefixes=('reg_skip_',))),{'reg_age'})
 def test_invalid_date_restore_skipped(self):
  self.ns['restore_draft_state']({'reg_visit':{'type':'date','value':'not-a-date'},'reg_age':{'value':46},'reg_bad':7})
  self.assertEqual(self.fake.session_state,{'reg_age':46})
 def test_gas_parity_twelve_existing_fixtures(self):
  fixtures=json.loads(Path('/workspace/scratch/426ea3aa0205/uat/integrated_core/final_uat_review/auth04_results.json').read_text())['fixtures']
  gas='/workspace/scratch/426ea3aa0205/uat/integrated_core/privacy_revision2.gs'
  script="const fs=require('fs');const f=new Function(fs.readFileSync(process.argv[1],'utf8')+';return stripDirectIdentifiers_;')();process.stdout.write(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(f)));"
  result=subprocess.run(['node','-e',script,gas],input=json.dumps(fixtures),capture_output=True,text=True,check=True)
  for fixture,expected in zip(fixtures,json.loads(result.stdout)):
   with self.subTest(fixture=fixture):self.assertEqual(self.ns['redact_draft_identifiers'](fixture),expected)
 def test_nested_capture_no_alias_or_mutation(self):
  self.fake.session_state={'reg_data':{'age':46,'patient_name':'fictional','items':[{'mrn':'fictional','value':0}]}}
  original=copy.deepcopy(self.fake.session_state);got=self.ns['capture_draft_state']('reg_')
  self.assertEqual(self.fake.session_state,original);self.assertEqual(got['reg_data']['value'],{'age':46,'items':[{'value':0}]})
  got['reg_data']['value']['items'][0]['value']=99;self.assertEqual(self.fake.session_state,original)
 def test_known_limits_not_overclaimed(self):
  self.assertEqual(self.ns['redact_draft_identifiers']('架空検証者'),'架空検証者')
  self.fake.session_state={'regDOB':'preexisting'};self.ns['restore_draft_state']({'regDOB':{'value':'old'}})
  self.assertEqual(self.fake.session_state['regDOB'],'preexisting')
if __name__=='__main__':unittest.main(verbosity=2)
