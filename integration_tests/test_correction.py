"""Fictional UI correction coordinator; signed GAS enforcement is tested separately."""
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from isolated_correction_ui import snapshot_form, start_correction
from juog_crf_save_ui import attempt_key


class Correction(unittest.TestCase):
    def fixture(self, page='peri', typ='perioperative_30d', visit='30d'):
        p=dict(registration_id='JUOG-901', facility_code='TEST01', crf_type=typ,
               visit=visit, submission_id='fictional-v1', record_key=f'JUOG-901|{typ}|{visit}')
        p['data']=dict(source_30d_record_version=5,source_30d_submission_id='fictional-30d-v5',reference_date='2026-01-01',surgery_performed='実施した')
        form={page+'_registration_id':'JUOG-901',page+'_reporter_email':'fictional@example.invalid'}
        if page=='fu':form['fu_visit_month']=visit.replace('m','ヶ月')+('（終了）' if visit=='24m' else '')
        if page=='peri':form['peri_op_date']=date(2026,1,1)
        attempt=dict(status='complete', actor_key='verified-actor', payload=p,
                     record_version='1', form_state=snapshot_form(page,form))
        st=SimpleNamespace(session_state={attempt_key(page):attempt,page+'_sent':True,
                                          '_autosave_'+page:{'version':0}})
        reply=dict(ok=True,recovery=dict(state='SAVED',record_key=p['record_key'],
                      operations=[dict(state='SAVED',uuid=p['submission_id'],version=1,audit_verified=True)]))
        checked=dict(ok=True,record_versions={p['record_key']:1})
        return st,reply,checked

    def execute(self, st, reply, checked, page='peri', actor='verified-actor', linkage_override=None):
        def restore(form):
            for k,v in form.items():st.session_state[k]=date.fromisoformat(v['value']) if v['type']=='date' else v['value']
        linkage=dict(ok=True,source_found=True,registration_id='JUOG-901',facility_code='TEST01',record_version=5,submission_id='fictional-30d-v5',reference_date='2026-01-01',surgery_performed='実施した')
        if linkage_override:linkage.update(linkage_override)
        with patch('isolated_crf_adapter.actor_key',return_value=actor), \
             patch('isolated_crf_adapter.call',side_effect=lambda st,action,q:linkage if action=='get_crf_linkage' else reply) as call, \
             patch('isolated_crf_adapter.begin_edit',return_value=checked) as begin, \
             patch('juog_common.restore_draft_state',side_effect=restore):
            error=start_correction(st,page)
            self.assertTrue(all(x.args[1] in ('recovery_status','get_crf_linkage') for x in call.call_args_list))
            return error,begin.call_count

    def test_all_nine_visits_restore_then_new_correction_without_writes(self):
        for page,typ,visits in [('peri','perioperative_30d',['30d']),('d90','day90',['90d']),('fu','followup',['6m','9m','12m','15m','18m','21m','24m'])]:
            for visit in visits:
                with self.subTest(visit=visit):
                    st,r,c=self.fixture(page,typ,visit)
                    self.assertEqual(self.execute(st,r,c,page),(None,1))
                    self.assertFalse(st.session_state[page+'_sent'])
                    self.assertEqual(st.session_state[page+'_submission_kind'],'訂正報告')
                    self.assertEqual(st.session_state[page+'_correction_reason'],'')
                    self.assertNotIn(attempt_key(page),st.session_state)
                    self.assertNotIn('_autosave_'+page,st.session_state)
                    self.assertEqual(st.session_state[page+'_registration_id'],'JUOG-901')
                    if page in ('d90','fu'):
                        self.assertEqual(st.session_state[page+'_linkage']['submission_id'],'fictional-30d-v5')
                        self.assertEqual(st.session_state[page+'_linkage']['record_version'],5)

    def test_unknown_audit_wrong_uuid_newer_version_and_concurrent_edit_preserve_attempt(self):
        for fault in ('unknown','audit','uuid','newer','race','denied','actor','bad_date','identifier'):
            with self.subTest(fault=fault):
                st,r,c=self.fixture();actor='verified-actor'
                if fault=='unknown':r['ok']=False
                if fault=='audit':r['recovery']['operations'][0]['audit_verified']=False
                if fault=='uuid':r['recovery']['operations'][0]['uuid']='other-uuid'
                if fault=='newer':r['recovery']['operations'][0]['version']=2
                if fault=='race':c['record_versions'][r['recovery']['record_key']]=2
                if fault=='denied':c['ok']=False
                if fault=='actor':actor='another-person'
                if fault=='bad_date':st.session_state[attempt_key('peri')]['form_state']['peri_op_date']['value']='2026-02-30'
                if fault=='identifier':st.session_state[attempt_key('peri')]['form_state']['peri_correction_reason']={'type':'value','value':'患者氏名 テスト太郎'}
                before=deepcopy(st.session_state)
                error,_=self.execute(st,r,c,actor=actor)
                self.assertIsInstance(error,str)
                self.assertEqual(st.session_state,before)

    def test_expired_native_auth_does_not_call_server(self):
        st,r,c=self.fixture()
        with patch('isolated_crf_adapter.actor_key',side_effect=PermissionError()),patch('isolated_crf_adapter.call') as call:
            self.assertIsInstance(start_correction(st,'peri'),str)
            call.assert_not_called()

    def test_snapshot_only_allowlisted_values_and_no_alias(self):
        state={'peri_registration_id':' juog-901 ','auth_token':'not-a-real-secret','fu_registration_id':'JUOG-902','peri_op_date':date(2026,1,1)}
        snap=snapshot_form('peri',state)
        self.assertEqual(set(snap),{'peri_registration_id','peri_op_date'})
        self.assertEqual(snap['peri_op_date'],{'type':'date','value':'2026-01-01'})
        state['peri_registration_id']='JUOG-902'
        self.assertEqual(snap['peri_registration_id']['value'],'JUOG-901')

    def test_linkage_failure_change_or_cross_case_preserves_saved_attempt(self):
        for page,typ,visit in [('d90','day90','90d'),('fu','followup','9m')]:
            for override in ({'ok':False},{'source_found':False},{'registration_id':'JUOG-902'},{'facility_code':'OTHER'},{'record_version':6},{'record_version':True},{'submission_id':'other'},{'reference_date':'2026-02-01'},{'surgery_performed':'未実施'}):
                with self.subTest(page=page,override=override):
                    st,r,c=self.fixture(page,typ,visit);before=deepcopy(st.session_state)
                    error,_=self.execute(st,r,c,page,linkage_override=override)
                    self.assertIsInstance(error,str)
                    self.assertEqual(st.session_state,before)
