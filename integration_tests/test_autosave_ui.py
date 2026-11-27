"""Actual three Streamlit pages; only signed transport/identity are fictional doubles.
No local server, new app, live Sheets or network. GAS auth is exercised separately.
"""
from pathlib import Path
from copy import deepcopy
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import isolated_autosave_ui as a

ROOT=Path(__file__).resolve().parents[1]
PAGES={'peri':'02_perioperative_30d_crf.py','d90':'03_day90_crf.py','fu':'04_followup_crf.py'}
class UI(unittest.TestCase):
    def setUp(self):
        self.clock=0;self.saved={};self.calls=[];self.fail=False
        self.identity=patch('isolated_autosave_ui._identity',return_value='fictional-identity')
        self.identity.start();self.addCleanup(self.identity.stop)
        p=patch('isolated_autosave_ui._clock',side_effect=lambda:self.clock);p.start();self.addCleanup(p.stop)
        p=patch('isolated_crf_adapter.call',side_effect=self.call);p.start();self.addCleanup(p.stop)
    def call(self,st,action,q=None,**kwargs):
        self.calls.append((action,deepcopy(q)))
        if action in ('get_sections','save_section'):
            key='|'.join(q[k] for k in ('registration_id','crf_type','visit'))
            sections=self.saved.setdefault(key,{})
            if action=='save_section':
                if self.fail:return {'ok':False,'error':'RESULT_UNCONFIRMED'}
                e=deepcopy(q);e['revision']=q['expected_revision']+1
                sections[q['section']]=e
            return dict(ok=True,audit_verified=True,record_key=key,record_version=0,sections=deepcopy(sections),receipt=deepcopy(sections.get(q.get('section'),{})))
        if action=='get_crf_linkage':return self.link()
        return {'ok':False,'error':'OFFLINE_UNCONFIGURED'}
    def link(self):
        return dict(ok=True,source_found=True,registration_id='JUOG-901',facility_code='TEST01',facility_name='FICTIONAL',surgery_performed='実施した',reference_date='2026-01-01',record_version=1,submission_id='fictional')
    def app(self,page,seed=True):
        app=AppTest.from_file(str(ROOT/PAGES[page]),default_timeout=20)
        if seed:
            app.session_state[page+'_registration_id']='JUOG-901'
            app.session_state[page+'_reporter_email']='fictional@example.invalid'
            if page in ('d90','fu'):app.session_state[page+'_linkage']=self.link()
            if page=='fu':app.session_state['fu_visit_month']='6ヶ月'
        app.run();self.assertFalse(list(app.exception))
        return app
    def saves(self):return [q for action,q in self.calls if action=='save_section']
    def test_retired_fragment_emits_nothing_and_never_contacts_server(self):
        for flag in ('_show_recovery', 'auth_connect_halted'):
            with self.subTest(flag=flag):
                self.calls=[]
                app=AppTest.from_string('import streamlit as st\nfrom isolated_autosave_ui import section_feedback\nsection_feedback("peri", "1")',default_timeout=20)
                app.session_state[flag]=True
                app.session_state['peri_registration_id']='JUOG-901'
                self.clock=10
                app.run()
                self.assertFalse(list(app.exception))
                self.assertEqual(self.calls,[])
                self.assertFalse(list(app.caption))
                self.assertFalse(list(app.error))
                self.assertFalse(list(app.warning))
                self.assertFalse(list(app.markdown))
    def test_expired_section_assertion_returns_to_full_page_gate_with_input(self):
        original=self.call
        def expired(st,action,q=None,**kwargs):
            if action=='save_section':
                st.session_state['_assertion_recheck_required']=True
                st.session_state['_connection_unconfirmed']=True
                return {'ok':False,'error':'ASSERTION_RECONFIRMATION_REQUIRED'}
            return original(st,action,q,**kwargs)
        script='import streamlit as st\nfrom isolated_autosave_ui import section_feedback\nif st.session_state.get("_assertion_recheck_required"):\n st.error("fresh signed ACL required")\nelse:\n section_feedback("peri", "1")'
        app=AppTest.from_string(script,default_timeout=20)
        app.session_state['_integration_actor']='fictional-identity'
        app.session_state['peri_registration_id']='JUOG-901'
        app.session_state['peri_reporter_email']='fictional@example.invalid'
        with patch('isolated_crf_adapter.call',side_effect=expired):
            app.run();self.clock=3;app.run()
        self.assertFalse(list(app.exception))
        self.assertTrue(any(x.value=='fresh signed ACL required' for x in app.error))
        self.assertEqual(app.session_state['_connection_input_backup']['values']['peri_registration_id'],'JUOG-901')
        self.assertFalse(list(app.success))

    def test_previous_page_timer_cannot_write_after_visit_switch(self):
        for selected, retired in [('90日', 'peri'), ('6〜24か月', 'd90'), ('30日', 'fu')]:
            with self.subTest(selected=selected):
                self.calls=[]
                app=AppTest.from_string('import streamlit as st\nfrom isolated_autosave_ui import section_feedback\nsection_feedback('+repr(retired)+', "1")',default_timeout=20)
                app.session_state['_integration_page']=selected
                app.session_state[retired+'_registration_id']='JUOG-901'
                app.run()
                self.assertFalse(list(app.exception))
                self.assertEqual(self.calls,[])
                for element in ('caption','error','warning','markdown','success'):
                    self.assertFalse(list(getattr(app,element)))

    def test_all_three_debounce_and_only_changed_section(self):
        for page in PAGES:
            with self.subTest(page=page):
                self.clock=0;self.saved={};self.calls=[]
                app=self.app(page);self.assertEqual(self.saves(),[])
                self.clock=2.1;app.run();self.assertFalse(list(app.exception));self.assertEqual(len(self.saves()),len(a.SECTIONS[page]))
                self.calls=[];self.clock=5;app.run();self.assertEqual(self.saves(),[])
                app.radio(key=page+'_submission_kind').set_value('訂正報告').run()
                self.clock=7.1;app.run();self.assertEqual([x['section'] for x in self.saves()],['1'])
                self.assertTrue(any('保存しました' in x.value for x in app.success))
    def test_completed_and_uncertain_save_feedback_without_draft_writes(self):
        for page in PAGES:
            for status in ('complete', 'uncertain'):
                with self.subTest(page=page, status=status):
                    self.calls=[]
                    app=AppTest.from_string('from isolated_autosave_ui import section_feedback\nsection_feedback('+repr(page)+', "1")',default_timeout=20)
                    app.session_state[page+'_registration_id']='JUOG-901'
                    app.session_state['fu_visit_month']='9ヶ月'
                    app.session_state[page+'_sent']=True
                    app.session_state['_juog_'+page+'_save_attempt']={'status':status}
                    app.run()
                    self.assertFalse(list(app.exception))
                    self.assertEqual(self.calls,[])
                    message=''.join(x.value for x in app.caption)
                    self.assertIn('正式保存済み' if status=='complete' else '照合中',message)
                    if status=='uncertain':self.assertNotIn('正式保存済み',message)
    def test_close_browser_new_session_resume_uses_server_sections(self):
        app=self.app('peri');app.radio(key='peri_surgery_performed').set_value('実施しなかった').run()
        self.clock=3;app.run();self.assertTrue(self.saves())
        reopened=self.app('peri',seed=False)
        reopened.text_input(key='_resume_case_peri').set_value('JUOG-901').run()
        reopened.button(key='_resume_action_peri').click().run()
        self.assertFalse(list(reopened.exception))
        self.assertEqual(reopened.radio(key='peri_surgery_performed').value,'実施しなかった')
    def test_failed_save_no_false_success_or_automatic_retry_overlay_removed(self):
        app=self.app('peri');self.fail=True;self.clock=3;app.run()
        self.assertTrue(any('保存できませんでした' in x.value for x in app.error));n=len(self.saves())
        self.clock=10;app.run();self.assertEqual(len(self.saves()),n)
        self.assertFalse(any('::after' in x.value for x in app.markdown))
        original=deepcopy(self.saves()[0]);self.fail=False
        app.button(key='_retry_peri_1').click().run()
        self.assertEqual(self.saves()[-1],original)
    def test_identity_change_purges_previous_form_and_never_sends(self):
        app=self.app('peri');self.clock=3;app.run();n=len(self.saves())
        with patch('isolated_autosave_ui._identity',return_value='different-person'):
            app.run()
        self.assertEqual(len(self.saves()),n)
        self.assertTrue(any('以前の入力を破棄' in x.value for x in app.error))

    def test_all_nine_visits_new_browser_restores_exact_report(self):
        for page,visits in [('peri',['30d']),('d90',['90d']),('fu',a.VISITS)]:
            for visit in visits:
                with self.subTest(page=page,visit=visit):
                    self.clock=0;self.saved={};self.calls=[]
                    app=self.app(page)
                    if page=='fu':
                        label=visit.replace('m','ヶ月')+('（終了）' if visit=='24m' else '')
                        # Start clean for this visit, not by silently rebinding a loaded draft.
                        app=AppTest.from_file(str(ROOT/PAGES[page]),default_timeout=20)
                        app.session_state['fu_registration_id']='JUOG-901'
                        app.session_state['fu_reporter_email']='fictional@example.invalid'
                        app.session_state['fu_linkage']=self.link()
                        app.session_state['fu_visit_month']=label;app.run()
                    app.radio(key=page+'_submission_kind').set_value('訂正報告').run()
                    app.text_area(key=page+'_correction_reason').set_value('架空の再開試験').run()
                    self.clock=3;app.run();self.assertTrue(self.saves())
                    reopened=self.app(page,seed=False)
                    reopened.text_input(key='_resume_case_'+page).set_value('JUOG-901').run()
                    if page=='fu':reopened.selectbox(key='_resume_visit_fu').set_value(visit).run()
                    reopened.button(key='_resume_action_'+page).click().run()
                    self.assertFalse(list(reopened.exception))
                    self.assertEqual(reopened.radio(key=page+'_submission_kind').value,'訂正報告')
                    self.assertEqual(reopened.text_area(key=page+'_correction_reason').value,'架空の再開試験')
                    self.assertEqual(reopened.session_state['_autosave_'+page]['query']['visit'],visit)

    def test_completed_pages_offer_verified_correction_with_preserved_input(self):
        from isolated_correction_ui import snapshot_form
        from juog_crf_save_ui import attempt_key
        for page in PAGES:
            with self.subTest(page=page):
                typ=a.TYPES[page];visit='30d' if page=='peri' else '90d' if page=='d90' else '6m'
                key=f'JUOG-901|{typ}|{visit}'
                p=dict(registration_id='JUOG-901',facility_code='TEST01',crf_type=typ,visit=visit,submission_id='fictional-v1',record_key=key)
                form={page+'_registration_id':'JUOG-901',page+'_reporter_email':'fictional@example.invalid'}
                if page=='fu':form['fu_visit_month']='6ヶ月'
                app=AppTest.from_file(str(ROOT/PAGES[page]),default_timeout=20)
                app.session_state[page+'_sent']=True
                app.session_state[attempt_key(page)]=dict(status='complete',actor_key='fictional-actor',payload=p,record_version='1',form_state=snapshot_form(page,form))
                app.run();self.assertFalse(list(app.exception))
                reply=dict(ok=True,recovery=dict(state='SAVED',record_key=key,operations=[dict(state='SAVED',uuid='fictional-v1',version=1,audit_verified=True)]))
                with patch('isolated_crf_adapter.actor_key',return_value='fictional-actor'),patch('isolated_crf_adapter.call',return_value=reply),patch('isolated_crf_adapter.begin_edit',return_value=dict(ok=True,record_versions={key:1})):
                    app.button(key='_correction_start_'+page).click().run()
                self.assertFalse(list(app.exception))
                self.assertEqual(app.radio(key=page+'_submission_kind').value,'訂正報告')
                self.assertEqual(app.text_input(key=page+'_registration_id').value,'JUOG-901')
