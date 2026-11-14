import json,sys,secrets,time,copy,unittest,base64,hmac,hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
P=Path(__file__).parent;sys.path.insert(0,str(P))
import canonical_v9_bridge as b
from juog_common import redact_draft_identifiers as redact
class User(dict):is_logged_in=True
now=int(time.time());key=secrets.token_hex(32)
u=User(iss='https://accounts.google.com',sub=secrets.token_hex(12),aud='offline-client',iat=now,exp=now+7200,nonce=secrets.token_hex(16))
cfg=dict(oidc_issuer=u['iss'],oidc_client_id=u['aud'],signing_key=key,bridge_issuer='offline-bridge',audience='offline-gas',session_policy='isolated_gas_session_b2',session_environment='JUOG_AUTH04_ISOLATED_TEST01',session_store_generation='offline-generation',session_b_safety_review_approved=True,session_b_limited_execution_approved=True)
native=SimpleNamespace(user=u,secrets={'juog_identity_bridge':cfg})
ctx=dict(ok=True,role='facility',facilities=['TEST01'],facility_code='TEST01',execution_stage='AUTH_CONNECT',business_writes_allowed=False)
p=dict(study_code='JUOG_UTUC_Consolidative',registration_id='JUOG-971',facility_code='TEST01',reporter_email='fictional@example.invalid',crf_type='perioperative_30d',visit='30d',submission_kind='初回報告',submission_id='changing-client-id',submitted_at='2026-11-14',data={'pathology':{'size_mm':0},'clinical_date':'2026-10-01'})
class Tests(unittest.TestCase):
 def test_signed_prepare_exact_request(self):
  e,op=b.build(native,'save_crf',{'payload':p},redact,{},{});a,s=e['identity_assertion'].split('.')
  self.assertTrue(hmac.compare_digest(base64.urlsafe_b64encode(hmac.new(key.encode(),a.encode(),hashlib.sha256).digest()).rstrip(b'=').decode(),s))
  claims=json.loads(base64.urlsafe_b64decode(a+'='*(-len(a)%4)));r=json.loads(e['request_json'])
  self.assertEqual(r,{'action':'prepare_request','payload':op});self.assertEqual(claims['request_hash'],hashlib.sha256(e['request_json'].encode()).hexdigest());self.assertEqual(claims['v'],2);self.assertLessEqual(claims['exp']-claims['iat'],15)
 def test_scope_denials(self):
  for field,value in [('registration_id','JUOG-970'),('facility_code','OTHER'),('role','admin'),('reporter_email','real@example.org')]:
   with self.assertRaises(b.BridgeError):b.build(native,'save_crf',{'payload':dict(p,**{field:value})},redact,{}, {})
 def test_acl_denials(self):
  for change in [{'role':'admin'},{'facilities':['OTHER']},{'ok':False},{'business_writes_allowed':True}]:
   with self.assertRaises(b.BridgeError):b.preview(native,dict(ctx,**change),'save_crf',{'payload':p},redact,{}, {})
 def test_unauth_expiry_issuer(self):
  for user in [User(u,exp=now-1),User(u,iat=now-4000),User(u,iss='invalid')]:
   with self.assertRaises(PermissionError):b.build(SimpleNamespace(user=user,secrets=native.secrets),'save_crf',{'payload':p},redact,{}, {})
  anon=User(u);anon.is_logged_in=False
  with self.assertRaises(PermissionError):b.build(SimpleNamespace(user=anon,secrets=native.secrets),'save_crf',{'payload':p},redact,{}, {})
 def test_privacy_rejected(self):
  for data in [{'patient_name':'FICTIONAL'},{'nested':'{"ＭＲＮ":"FICTIONAL"}'},{'note':'患者氏名は架空検証者'}]:
   with self.assertRaises(b.BridgeError):b.build(native,'save_crf',{'payload':dict(p,data=data)},redact,{}, {})
 def test_correction_observed_version_required(self):
  q=dict(p,submission_kind='訂正報告',correction_reason='架空訂正')
  with self.assertRaises(b.BridgeError):b.operation('save_crf',{'payload':q},redact,{})
  op=b.operation('save_crf',{'payload':q},redact,{'JUOG-971|perioperative_30d|30d':1});self.assertEqual(op['payload']['expected_record_version'],1)
  with self.assertRaises(b.BridgeError):b.operation('save_crf',{'payload':dict(q,correction_reason='')},redact,{'JUOG-971|perioperative_30d|30d':1})
 def test_stable_content_and_no_operation_invention(self):
  state={};_,a=b.build(native,'save_crf',{'payload':p},redact,{},state);_,c=b.build(native,'save_crf',{'payload':dict(p,submission_id='different',submitted_at='later')},redact,{},state)
  self.assertEqual(a,c);self.assertNotIn('operation_id',a)
 def test_reads_and_draft_shape(self):
  q={k:p[k] for k in ['registration_id','facility_code','reporter_email','crf_type','visit']};q['draft_state']={'peri_zero':{'type':'value','value':0}}
  _,op=b.build(native,'save_draft',q,redact,{},{});self.assertEqual(op['payload']['draft_state'],q['draft_state'])
  e,_=b.build(native,'get_draft',q,redact,{},{});self.assertEqual(json.loads(e['request_json'])['payload']['action'],'get_draft')
  e,_=b.build(native,'read_crf',dict(q,record_key='JUOG-971|perioperative_30d|30d'),redact,{},{});self.assertEqual(set(json.loads(e['request_json'])['payload']['payload']),{'registration_id','facility_code','record_key'})
 def test_preview_never_network(self):
  with patch('urllib.request.urlopen',side_effect=AssertionError('NETWORK')):
   r=b.preview(native,ctx,'save_crf',{'payload':p},redact,{},{});self.assertFalse(r['ok']);self.assertFalse(r['business_sent']);self.assertFalse(r['subject_registry_verified']);self.assertNotIn('identity_assertion',r)
 def test_legacy_projection_preserves_original(self):
  original={'ok':True,'draft_state':{'peri_patient_name':{'value':'FICTIONAL'},'peri_zero':{'value':0}}};before=copy.deepcopy(original);out=b.safe_read_result(original,redact);self.assertEqual(before,original);self.assertNotIn('peri_patient_name',out['draft_state']);self.assertEqual(out['draft_state']['peri_zero']['value'],0)
 def test_uncertain_prepare_blocks_duplicate(self):
  def call(a,p):raise TimeoutError()
  l=b.Lifecycle(call)
  with self.assertRaises(TimeoutError):l.write({})
  with self.assertRaises(b.BridgeError):l.write({})
 def test_execution_timeout_reconciles_same_id(self):
  calls=[]
  def call(a,p):
   calls.append((a,p))
   if a=='prepare_request':return {'ok':True,'operation_id':'offline-operation'}
   if a=='execute_request':raise TimeoutError()
   return {'ok':True,'state':'SAVED'}
  l=b.Lifecycle(call)
  with self.assertRaises(TimeoutError):l.write({})
  self.assertEqual(l.reconcile()['state'],'SAVED');self.assertEqual([a for a,p in calls].count('prepare_request'),1);self.assertEqual(calls[-1][1],{'operation_id':'offline-operation'})
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests);r=unittest.TextTestRunner().run(suite)
 (P/'bridge_results.json').write_text(json.dumps({'mode':'OFFLINE_SYNTHETIC_CLAIMS_NOT_REAL_OIDC_LOGIN','tests':r.testsRun,'passed':r.wasSuccessful(),'secrets_or_envelopes_saved':False,'business_network_calls':0,'formal_pass_delta':0},indent=2)+'\n')
 sys.exit(not r.wasSuccessful())
