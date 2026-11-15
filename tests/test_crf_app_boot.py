"""Boot all three CRFs without submitting any data or contacting GAS.

Uses Streamlit AppTest in a fresh session; no Secrets or patient data.
"""
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]
PAGES=[
    "02_perioperative_30d_crf.py",
    "03_day90_crf.py",
    "04_followup_crf.py",
]


class InitialRenderTests(unittest.TestCase):
    def test_all_three_initial_pages_render_without_errors(self):
        for path in PAGES:
            with self.subTest(page=path):
                app=AppTest.from_file(str(ROOT/path), default_timeout=20)
                app.run()
                errors=[str(exc.message) for exc in app.exception]
                self.assertFalse(errors, "\n".join(errors))
                self.assertGreater(len(app.title),0)


    def test_30_day_surgery_path_change_does_not_raise(self):
        app=AppTest.from_file(str(ROOT/"02_perioperative_30d_crf.py"),default_timeout=20)
        app.run()
        app.radio(key="peri_surgery_performed").set_value("実施しなかった").run()
        self.assertFalse([str(x.message) for x in app.exception])

    def test_day90_manual_linkage_path_does_not_raise(self):
        app=AppTest.from_file(str(ROOT/"03_day90_crf.py"),default_timeout=20)
        app.session_state["d90_registration_id"]="JUOG-901"
        app.session_state["d90_linkage"]={
            "ok":True, "source_found":False,"manual_fallback":True,
            "registration_id":"JUOG-901","facility_code":"F01","facility_name":"架空病院",
        }
        app.run()
        self.assertFalse([str(x.message) for x in app.exception])

    def test_followup_linked_patient_path_does_not_raise(self):
        app=AppTest.from_file(str(ROOT/"04_followup_crf.py"),default_timeout=20)
        app.session_state["fu_registration_id"]="JUOG-901"
        app.session_state["fu_linkage"]={
            "ok":True,"source_found":True,
            "registration_id":"JUOG-901","facility_code":"F01",
            "facility_name":"架空病院","surgery_performed":"実施した",
            "reference_date":"2026-01-01","record_version":1,
            "submission_id":"fictional",
        }
        app.run()
        self.assertFalse([str(x.message) for x in app.exception])


if __name__=="__main__":
    unittest.main()
