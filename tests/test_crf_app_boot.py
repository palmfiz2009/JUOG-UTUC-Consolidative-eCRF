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


if __name__=="__main__":
    unittest.main()
