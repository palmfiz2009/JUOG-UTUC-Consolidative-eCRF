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
