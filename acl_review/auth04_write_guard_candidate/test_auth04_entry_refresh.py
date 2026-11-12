"""Exercise the actual entry prefix without importing credentials or live APIs."""
import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parent
ENTRY=(ROOT/'streamlit_app.py').read_text().split('\nimport re\n',1)[0]
HARNESS=(ROOT/'uat_auth04_live.py').read_bytes()

class Stop(BaseException):pass

class Tests(unittest.TestCase):
    def setup_context(self):
        state={'auth04_pending':'SYNTHETIC_OBSERVED_OPERATION','auth04_operation_ids':['SYNTHETIC_OBSERVED_OPERATION'],'auth04_expected_versions':{0:2,1:1}}
        ui=types.ModuleType('streamlit');ui.session_state=state
        ui.error=Mock();ui.secrets={'auth_connect':{'enabled':True}}
        ui.stop=Mock(side_effect=Stop)
        module=types.ModuleType('uat_auth04_live');module.resume_observed_6m=Mock();module.revoke_and_logout=Mock()
        calls=[]
        def run():
            recovery_index=2
            calls.append(recovery_index)
            self.assertIs(ui.session_state,state)
            self.assertEqual(state['auth04_pending'],'SYNTHETIC_OBSERVED_OPERATION')
            raise Stop()
        module.run=run
        config=types.ModuleType('auth04_config');config.load_config=lambda:{'enabled':True}
        old=types.ModuleType('uat_auth_connect');old.run=Mock(side_effect=AssertionError('OLD_FALLBACK_MUST_NOT_RUN'))
        preflight=types.ModuleType('uat_oidc_preflight');preflight.run=Mock(side_effect=AssertionError('PREFLIGHT_FALLBACK_MUST_NOT_RUN'))
        modules={'streamlit':ui,'auth04_config':config,'uat_auth04_live':module,'uat_auth_connect':old,'uat_oidc_preflight':preflight}
        return ui,module,calls,modules,old,preflight

    def test_actual_prefix_refresh_preserves_observed_session_state(self):
        ui,module,calls,modules,old,preflight=self.setup_context()
        with patch.dict(sys.modules,modules),patch.object(Path,'read_bytes',return_value=HARNESS),patch.object(importlib,'reload',return_value=module) as reload:
            with self.assertRaises(Stop):exec(compile(ENTRY,str(ROOT/'streamlit_app.py'),'exec'),{'__file__':str(ROOT/'streamlit_app.py')})
        reload.assert_called_once_with(module);self.assertEqual(calls,[2]);ui.error.assert_not_called()
        old.run.assert_not_called();preflight.run.assert_not_called()

    def test_actual_prefix_hash_mismatch_stops_before_reload_or_request(self):
        ui,module,calls,modules,old,preflight=self.setup_context()
        with patch.dict(sys.modules,modules),patch.object(Path,'read_bytes',return_value=b'tampered'),patch.object(importlib,'reload') as reload:
            with self.assertRaises(Stop):exec(compile(ENTRY,str(ROOT/'streamlit_app.py'),'exec'),{'__file__':str(ROOT/'streamlit_app.py')})
        reload.assert_not_called();self.assertEqual(calls,[]);ui.error.assert_called_once();ui.stop.assert_called_once()
        old.run.assert_not_called();preflight.run.assert_not_called()

    def test_actual_prefix_reload_failure_has_no_old_run_fallback(self):
        ui,module,calls,modules,old,preflight=self.setup_context()
        with patch.dict(sys.modules,modules),patch.object(Path,'read_bytes',return_value=HARNESS),patch.object(importlib,'reload',side_effect=RuntimeError('SECRET_SENTINEL')):
            with self.assertRaises(Stop):exec(compile(ENTRY,str(ROOT/'streamlit_app.py'),'exec'),{'__file__':str(ROOT/'streamlit_app.py')})
        self.assertEqual(calls,[]);ui.error.assert_called_once();self.assertNotIn('SECRET_SENTINEL',str(ui.error.call_args))
        ui.stop.assert_called_once();old.run.assert_not_called();preflight.run.assert_not_called()

if __name__=='__main__':unittest.main()
