"""Offline regression tests for 30-day draft restore. No secrets or network calls.

Run in the repository root:
    python -m unittest discover -s tests -p "test_30d_draft_restore.py" -v
"""
import ast
import sys
import types
import unittest
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def extracted_function(filename, name, namespace):
    path = ROOT / filename
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    fn = next(
        (x for x in module.body if isinstance(x, ast.FunctionDef) and x.name == name),
        None,
    )
    if fn is None:
        raise AssertionError("Function missing: " + name)
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


def actual_widget_sync_loop():
    path = ROOT / "02_perioperative_30d_crf.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    matches = [
        x for x in ast.walk(tree)
        if isinstance(x, ast.For)
        and isinstance(x.target, ast.Name) and x.target.id == "restored_key"
        and isinstance(x.iter, ast.Name) and x.iter.id == "restored_state"
    ]
    if len(matches) != 1:
        raise AssertionError("Expected exactly one restore sync loop, got " + str(len(matches)))
    return compile(ast.Module(body=[matches[0]], type_ignores=[]), str(path), "exec")


class FakeColumn:
    def __init__(self, st):
        self.st = st

    def text_input(self, label, value="", key=None, disabled=False):
        return self.st.session_state.get(key, value)


class FakeStreamlit(types.ModuleType):
    def __init__(self):
        super().__init__("streamlit")
        self.session_state = {}

    def columns(self, n):
        return [FakeColumn(self) for _ in range(n)]

    def caption(self, message):
        return None

    def selectbox(self, label, options, index=0, key=None, disabled=False):
        return self.session_state.get(key, options[index])


class DraftRestoreTests(unittest.TestCase):
    def setUp(self):
        self.st = FakeStreamlit()
        previous = sys.modules.get("streamlit")
        sys.modules["streamlit"] = self.st
        def undo():
            if previous is None:
                sys.modules.pop("streamlit", None)
            else:
                sys.modules["streamlit"] = previous
        self.addCleanup(undo)

        ns = {"date": date, "datetime": datetime}
        self.capture = extracted_function("juog_common.py", "capture_draft_state", ns)
        self.clear = extracted_function("juog_common.py", "clear_session_state_prefixes", ns)
        self.restore = extracted_function("juog_common.py", "restore_draft_state", ns)
        self.facility = extracted_function(
            "juog_common.py", "render_facility",
            {"FACILITY_NAMES": ["関西医科大学", "大阪大学"],
             "FACILITY_NAME_TO_CODE": {"関西医科大学": "F11", "大阪大学": "F07"}},
        )
        self.labs = extracted_function(
            "02_perioperative_30d_crf.py", "render_optional_lab_panel",
            {"st": self.st, "LAB_FIELDS": [("Hb", "Hb", "g/dL"), ("WBC", "WBC", "/μL")]},
        )
        self.sync_loop = actual_widget_sync_loop()

    def load_draft(self, saved):
        self.clear(("peri_", "widget_peri_"))
        self.restore(saved)
        exec(self.sync_loop, {"restored_state": saved, "st": self.st})

    def test_saved_lab_and_facility_survive_rerender(self):
        self.st.session_state.update({
            "peri_facility": "関西医科大学",
            "peri_day30_lab_Hb": "12.7",
            "peri_day30_lab_WBC": "5600",
            "peri_visit_date_30": date(2026, 10, 15),
            "widget_peri_facility": "選択してください",
            "widget_peri_day30_lab_Hb": "",
        })
        saved = self.capture("peri_")
        self.load_draft(saved)
        self.assertEqual(self.facility(key="peri_facility"), ("F11", "関西医科大学"))
        self.assertEqual(
            self.labs("peri_day30_lab"), {"Hb": "12.7", "WBC": "5600"}
        )
        self.assertEqual(self.st.session_state["peri_visit_date_30"], date(2026, 10, 15))

    def test_stale_widgets_are_replaced(self):
        self.st.session_state.update({
            "widget_peri_facility": "大阪大学",
            "widget_peri_day30_lab_Hb": "9.0",
        })
        saved = {
            "peri_facility": {"type": "value", "value": "関西医科大学"},
            "peri_day30_lab_Hb": {"type": "value", "value": "13.5"},
            "peri_discharge_lab_Hb": {"type": "value", "value": "12.0"},
        }
        self.load_draft(saved)
        self.assertEqual(self.st.session_state["widget_peri_facility"], "関西医科大学")
        self.assertEqual(self.st.session_state["widget_peri_day30_lab_Hb"], "13.5")
        self.assertEqual(self.st.session_state["widget_peri_discharge_lab_Hb"], "12.0")

    def test_other_form_keys_do_not_gain_shadow_widgets(self):
        saved = {
            "peri_registration_id": {"type": "value", "value": "JUOG-001"},
            "peri_surgery_performed": {"type": "value", "value": "実施しなかった"},
        }
        self.load_draft(saved)
        self.assertEqual(self.st.session_state["peri_registration_id"], "JUOG-001")
        self.assertNotIn("widget_peri_registration_id", self.st.session_state)
        self.assertNotIn("widget_peri_surgery_performed", self.st.session_state)


if __name__ == "__main__":
    unittest.main()
