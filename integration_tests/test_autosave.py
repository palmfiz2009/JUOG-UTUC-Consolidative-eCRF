import unittest
from copy import deepcopy
from datetime import date
import isolated_autosave_ui as a

class Autosave(unittest.TestCase):
    def setUp(self):
        self.q=dict(registration_id='JUOG-901',facility_code='TEST01',crf_type='perioperative_30d',visit='30d')
        self.slot={}
        self.data={'peri_registration_id':{'type':'value','value':'JUOG-901'}}
    def receipt(self,op):
        return dict(ok=True,audit_verified=True,record_key='JUOG-901|perioperative_30d|30d',record_version=0,
                    receipt=dict(op,revision=op['expected_revision']+1))
    def test_debounce_resets_and_unchanged_never_sends(self):
        a.observe(self.slot,self.data,10)
        self.assertIsNone(a.prepare(self.slot,self.q,'1',0,11.99))
        changed=deepcopy(self.data);changed['peri_reporter_email']={'type':'value','value':'fictional@example.invalid'}
        a.observe(self.slot,changed,11)
        self.assertIsNone(a.prepare(self.slot,self.q,'1',0,12.99))
        op=a.prepare(self.slot,self.q,'1',0,13)
        self.assertTrue(a.acknowledge(self.slot,op,self.receipt(op)))
        self.assertIsNone(a.prepare(self.slot,self.q,'1',0,20))
    def test_uncertain_freezes_uuid_payload_and_manual_retry(self):
        a.observe(self.slot,self.data,0);op=a.prepare(self.slot,self.q,'1',0,2)
        self.assertFalse(a.acknowledge(self.slot,op,{}))
        a.observe(self.slot,{},3)
        self.assertIsNone(a.prepare(self.slot,self.q,'1',0,50))
        self.assertEqual(a.prepare(self.slot,self.q,'1',0,50,True),op)
        self.assertTrue(a.acknowledge(self.slot,op,self.receipt(op)))
        nextop=a.prepare(self.slot,self.q,'1',0,50)
        self.assertNotEqual(nextop['operation_id'],op['operation_id'])
        self.assertEqual(nextop['data'],{})
    def test_receipt_binding_and_audit_required(self):
        a.observe(self.slot,self.data,0);op=a.prepare(self.slot,self.q,'1',0,2)
        for key,value in [('record_key','other'),('record_version',1),('audit_verified',False),('ok',False)]:
            r=self.receipt(op);r[key]=value
            self.assertFalse(a.acknowledge(self.slot,op,r))
            self.assertEqual(self.slot['pending'],op)
        for key,value in [('operation_id','other'),('section','2'),('revision',8),('data',{})]:
            r=self.receipt(op);r['receipt'][key]=value
            self.assertFalse(a.acknowledge(self.slot,op,r))
    def test_sections_preserve_null_zero_false_empty_date_and_exclude_other_sections(self):
        s={'peri_op_completed':None,'peri_bleeding':0,'peri_op_other':'','peri_op_date':date(2026,1,1),'peri_day30_visit_date':date(2026,1,30),'unrelated':False}
        out=a.capture('peri','2',s)
        self.assertIsNone(out['peri_op_completed']['value'])
        self.assertEqual(out['peri_op_date'],{'type':'date','value':'2026-01-01'})
        self.assertNotIn('peri_day30_visit_date',out)
        key=a.SECTIONS['peri']['2']['keys'][0]
        for v in [None,0,False,'']:
            self.assertIs(a.capture('peri','2',{key:v})[key]['value'],v)
    def test_hidden_field_removal_is_a_change_not_false_or_zero(self):
        self.slot['saved']={'peri_surgery_performed':{'type':'value','value':None}}
        self.assertTrue(a.observe(self.slot,{},0))
    def test_dirty_section_only_and_no_state_alias(self):
        other={'saved':deepcopy(self.data),'observed':deepcopy(self.data)}
        self.assertIsNone(a.prepare(other,self.q,'1',0,10))
        a.observe(self.slot,self.data,0);op=a.prepare(self.slot,self.q,'1',0,2)
        op['data'].clear()
        self.assertTrue(self.slot['pending']['data'])
    def test_nonfinite_never_serializes(self):
        with self.assertRaises(ValueError):a.capture('peri','2',{'peri_bleeding':float('nan')})
    def test_restore_store_validation(self):
        r={'ok':True,'audit_verified':True,'record_key':'JUOG-901|perioperative_30d|30d','record_version':0,'sections':{}}
        self.assertTrue(a._read_ok(r,self.q))
        r['record_key']='JUOG-901|day90|90d'
        self.assertFalse(a._read_ok(r,self.q))


class TypedBoundaries(unittest.TestCase):
    def test_integral_float_receipt_is_equal_but_false_is_distinct(self):
        self.assertEqual(a.canonical({'v':0.0}),a.canonical({'v':0}))
        self.assertNotEqual(a.canonical({'v':False}),a.canonical({'v':0}))
    def test_malformed_response_never_acknowledges(self):
        slot={};q=dict(registration_id='JUOG-901',facility_code='TEST01',crf_type='perioperative_30d',visit='30d')
        a.observe(slot,{},0);op=a.prepare(slot,q,'1',0,2)
        for response in [None,[],{'receipt':None},{'ok':True,'receipt':'invalid'}]:
            self.assertFalse(a.acknowledge(slot,op,response))
            self.assertEqual(slot['pending'],op)

class RestoreBoundaries(unittest.TestCase):
    def test_server_response_cannot_restore_arbitrary_session_keys(self):
        q=dict(registration_id='JUOG-901',crf_type='perioperative_30d',visit='30d')
        r=dict(ok=True,audit_verified=True,record_key='JUOG-901|perioperative_30d|30d',record_version=0,
               sections={'1':{'revision':1,'data':{'auth_connect_halted':{'type':'value','value':False}}}})
        self.assertFalse(a._read_ok(r,q))
        r['sections']['1']['data']={'peri_registration_id':{'type':'value','value':'JUOG-901'}}
        self.assertTrue(a._read_ok(r,q))
        r['sections']['2']=r['sections'].pop('1')
        self.assertFalse(a._read_ok(r,q))

class StrictRecoveryBoundaries(unittest.TestCase):
    def test_boolean_versions_and_revisions_never_mark_saved(self):
        q=dict(registration_id='JUOG-901',crf_type='perioperative_30d',visit='30d')
        slot={};a.observe(slot,{},0);op=a.prepare(slot,q,'1',0,2)
        good=dict(ok=True,audit_verified=True,record_key='JUOG-901|perioperative_30d|30d',
                  record_version=0,receipt=dict(op,revision=1))
        for field, value in [('record_version', False),('record_version',0.0),('revision',True),('revision',1.0)]:
            r=deepcopy(good)
            if field=='revision':r['receipt'][field]=value
            else:r[field]=value
            self.assertFalse(a.acknowledge(slot,op,r))
            self.assertEqual(slot['pending'],op)
        self.assertTrue(a.acknowledge(slot,op,good))

    def test_restore_rejects_other_case_and_invalid_typed_dates(self):
        q=dict(registration_id='JUOG-901',crf_type='perioperative_30d',visit='30d')
        r=dict(ok=True,audit_verified=True,record_key='JUOG-901|perioperative_30d|30d',record_version=0,
               sections={'1':dict(revision=1,data={'peri_registration_id':{'type':'value','value':'JUOG-902'}})})
        self.assertFalse(a._read_ok(r,q))
        for kind, value in [('date','2026-02-30'),('date','20260101'),('date',None),('datetime','bad'),('value',float('nan'))]:
            r['sections']={'2':dict(revision=1,data={'peri_op_date':dict(type=kind,value=value)})}
            self.assertFalse(a._read_ok(r,q))
        r['sections']['2']['data']['peri_op_date']=dict(type='date',value='2026-02-28')
        self.assertTrue(a._read_ok(r,q))

    def test_restore_rejects_other_visit_and_extra_wrapper_keys(self):
        q=dict(registration_id='JUOG-901',crf_type='followup',visit='6m')
        section=next(k for k,v in a.SECTIONS['fu'].items() if 'fu_visit_month' in v['keys'])
        r=dict(ok=True,audit_verified=True,record_key='JUOG-901|followup|6m',record_version=0,
               sections={section:dict(revision=1,data={'fu_visit_month':dict(type='value',value='9ヶ月')})})
        self.assertFalse(a._read_ok(r,q))
        v=r['sections'][section]['data']['fu_visit_month'];v['value']='6ヶ月'
        self.assertTrue(a._read_ok(r,q));v['unexpected']='x'
        self.assertFalse(a._read_ok(r,q))


class IdentitySwitchPrivacy(unittest.TestCase):
    def test_resume_case_cleared_only_when_principal_changes(self):
        from types import SimpleNamespace
        session = {
            'peri_registration_id': 'JUOG-901',
            'widget_peri_lab': 'fictional',
            '_autosave_peri': {'identity': 'previous'},
            '_resume_case_peri': 'JUOG-901',
            '_resume_visit_peri': '30d',
            '_resume_action_peri': True,
            '_retry_peri_1': True,
            '_resume_case_d90': 'JUOG-902',
        }
        st = SimpleNamespace(session_state=session)
        a._clear(st, 'peri')
        self.assertIn('_resume_case_peri', session)  # Switching reports within one identity.
        self.assertNotIn('peri_registration_id', session)
        a._clear(st, 'peri', clear_resume=True)  # Identity lost or changed.
        for key in ('_resume_case_peri', '_resume_visit_peri',
                    '_resume_action_peri', '_retry_peri_1'):
            self.assertNotIn(key, session)
        self.assertEqual(session['_resume_case_d90'], 'JUOG-902')


if __name__=='__main__':unittest.main()

