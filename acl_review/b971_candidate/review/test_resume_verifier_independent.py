import copy,hashlib,importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('resume',ROOT/'resume_checkpoint_candidate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
STEPS=json.loads((ROOT/'uat_auth04_fixture.json').read_text())['steps']
KEYS=['JUOG-971|perioperative_30d|30d','JUOG-971|day90|90d','JUOG-971|followup|6m']
class Tests(unittest.TestCase):
 def setup_data(self,cursor=3):
  histories={key:[] for key in KEYS};completed=[];statuses=[]
  for i,step in enumerate(STEPS[:cursor]):
   error=step['expected_error'];state='FAILED' if error else 'SAVED';op='offline-operation-'+str(i)
   completed.append(dict(index=i,operation_id=op,expected_state=state,expected_error=error))
   statuses.append(dict(ok=True,state=state,operation_id=op,action='save_crf',**({'error':error} if error else {})))
   if not error:
    p=copy.deepcopy(step['payload']);histories[p['record_key']].append(dict(record_key=p['record_key'],record_version=p['expected_record_version']+1,payload=p))
  c=dict(scope='TEST01/JUOG-971',recorded_source_sha256=m.RECORDED_SOURCE,gas_sha256=m.GAS_SOURCE,fixture_sha256=m.FIXTURE_SOURCE,cursor=cursor,completed=completed,histories={k:dict(sha256=m.digest(v),versions=[r['record_version'] for r in v]) for k,v in histories.items()},evidence_ref='offline-synthetic-evidence',unresolved_operations=[])
  return c,histories,statuses
 def invoke(self,c,h,s):
  raw=json.dumps(c).encode();return m.verify_checkpoint(raw,hashlib.sha256(raw).hexdigest(),STEPS,h,s)
 def test_valid_contiguous_checkpoint(self):
  for cursor in [1,2,3,4,6,12]:
   c,h,s=self.setup_data(cursor);self.assertEqual(self.invoke(c,h,s),(cursor,'offline-synthetic-evidence'))
 def test_hash_tampering_rejected(self):
  c,h,s=self.setup_data();raw=json.dumps(c).encode()
  with self.assertRaises(PermissionError):m.verify_checkpoint(raw,b'bad',STEPS,h,s)
 def test_empty_histories_rejected(self):
  c,h,s=self.setup_data();c['histories']={}
  with self.assertRaises(PermissionError):self.invoke(c,{},s)
 def test_missing_one_history_rejected(self):
  c,h,s=self.setup_data();del c['histories'][KEYS[1]];del h[KEYS[1]]
  with self.assertRaises(PermissionError):self.invoke(c,h,s)
 def test_wrong_status_operation_rejected(self):
  c,h,s=self.setup_data();s[0]['operation_id']='unrelated'
  with self.assertRaises(PermissionError):self.invoke(c,h,s)
 def test_wrong_status_action_rejected(self):
  c,h,s=self.setup_data();s[0]['action']='save_draft'
  with self.assertRaises(PermissionError):self.invoke(c,h,s)
 def test_correlated_wrong_record_version_rejected(self):
  c,h,s=self.setup_data();h[KEYS[0]][0]['record_version']=7;c['histories'][KEYS[0]]=dict(sha256=m.digest(h[KEYS[0]]),versions=[7])
  with self.assertRaises(PermissionError):self.invoke(c,h,s)
 def test_bool_proof_index_rejected(self):
  c,h,s=self.setup_data();c['completed'][1]['index']=True
  with self.assertRaises(PermissionError):self.invoke(c,h,s)
 def test_duplicate_operation_rejected(self):
  c,h,s=self.setup_data();c['completed'][1]['operation_id']=c['completed'][0]['operation_id']
  with self.assertRaises(PermissionError):self.invoke(c,h,s)
 def test_wrong_expected_error_rejected(self):
  c,h,s=self.setup_data();c['completed'][0]['expected_error']='ACL_DENIED'
  with self.assertRaises(PermissionError):self.invoke(c,h,s)
 def test_live_negative_error_mismatch_rejected(self):
  c,h,s=self.setup_data();s[0]['error']='AUTH_EXPIRED'
  with self.assertRaises(PermissionError):self.invoke(c,h,s)
 def test_unresolved_operation_rejected(self):
  c,h,s=self.setup_data();c['unresolved_operations']=['pending']
  with self.assertRaises(PermissionError):self.invoke(c,h,s)
 def test_payload_mismatch_rejected_even_with_matching_pin(self):
  c,h,s=self.setup_data();h[KEYS[0]][0]['payload']['facility_code']='TEST02';c['histories'][KEYS[0]]['sha256']=m.digest(h[KEYS[0]])
  with self.assertRaises(PermissionError):self.invoke(c,h,s)
 def test_unknown_history_pin_field_rejected(self):
  c,h,s=self.setup_data();c['histories'][KEYS[0]]['unapproved']='extra'
  with self.assertRaises(PermissionError):self.invoke(c,h,s)
 def test_no_inputs_mutated(self):
  c,h,s=self.setup_data();old=copy.deepcopy((c,h,s));self.invoke(c,h,s);self.assertEqual(old,(c,h,s))
if __name__=='__main__':unittest.main(verbosity=2)
