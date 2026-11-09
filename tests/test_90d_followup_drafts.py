"""Regression tests for 90d and 6-24m draft widget restoration.

Run without Streamlit, GAS, secrets, emails or patient data:
python -m unittest discover -s tests -p 'test_90d_followup_drafts.py' -v
"""
from __future__ import annotations

import ast
import sys
import types
import unittest
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def function_from_file(path, name, env):
    src = (ROOT / path).read_text(encoding="utf-8")
    tree = ast.parse(src, filename=path)
    selected = next((n for n in tree.body
                     if isinstance(n, ast.FunctionDef) and n.name == name), None)
    if selected is None:
        raise AssertionError(f"Missing function {name} in {path}")
    exec(compile(ast.Module(body=[selected], type_ignores=[]), path, "exec"), env)
    return env[name]


def widget_sync_from_file(path, prefix):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"), path)
    loops = [n for n in ast.walk(tree) if
             isinstance(n, ast.For) and isinstance(n.target, ast.Name)
             and n.target.id == "restored_key" and
             isinstance(n.iter, ast.Name) and n.iter.id == "restored_state"]
    if len(loops) != 1:
        raise AssertionError(f"Expected one {prefix} sync loop, got {len(loops)}")
    return compile(ast.Module(body=[loops[0]], type_ignores=[]), path, "exec")


class Column:
    def __init__(self, st):
        self.st = st

    def text_input(self, label, value="", key=None, disabled=False):
        return self.st.session_state.get(key, value)


class FakeStreamlit(types.ModuleType):
    def __init__(self):
        super().__init__("streamlit")
        self.session_state = {}

    def columns(self, num):
        return [Column(self) for _ in range(num)]

    def caption(self, _):
        pass

    def selectbox(self, label, options, index=0, key=None, disabled=False):
        return self.session_state.get(key, options[index])


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.st = FakeStreamlit()
        old_st = sys.modules.get("streamlit")
        sys.modules["streamlit"] = self.st
        self.addCleanup(
            lambda: sys.modules.pop("streamlit", None)
            if old_st is None else sys.modules.__setitem__("streamlit", old_st)
        )
        ns = {"date": date, "datetime": datetime}
        self.capture = function_from_file("juog_common.py", "capture_draft_state", ns)
        self.clear = function_from_file("juog_common.py", "clear_session_state_prefixes", ns)
        self.restore = function_from_file("juog_common.py", "restore_draft_state", ns)
        self.lab_fields = [
            ("WBC", "WBC", "/μL"), ("Hb", "Hb", "g/dL"), ("Na", "Na", "mEq/L")
        ]
        self.render_d90 = function_from_file("03_day90_crf.py", "render_optional_lab_panel", {
            "st": self.st, "LAB_FIELDS": self.lab_fields
        })
        self.render_fu = function_from_file("juog_common.py", "render_lab_panel", {
            "LAB_FIELDS": self.lab_fields
        })
        self.render_facility = function_from_file("juog_common.py", "render_facility", {
            "FACILITY_NAMES": ["関西医科大学", "大阪大学"],
            "FACILITY_NAME_TO_CODE": {"関西医科大学": "F11", "大阪大学": "F07"}
        })
        self.sync_90 = widget_sync_from_file("03_day90_crf.py", "d90")
        self.sync_fu = widget_sync_from_file("04_followup_crf.py", "fu")
        self.visit_key = function_from_file("04_followup_crf.py", "followup_visit_key", {
            "FOLLOWUP_DRAFT_MONTHS": ("6ヶ月", "9ヶ月", "12ヶ月", "15ヶ月", "18ヶ月", "21ヶ月", "24ヶ月（終了）")
        })

    def load(self, prefix, saved, code):
        self.clear((prefix + "_", "widget_" + prefix + "_"))
        self.restore(saved)
        exec(code, {"restored_state": saved, "st": self.st})

    def test_90d_lab_restoration_into_widget_keys(self):
        self.st.session_state.update({
            "d90_lab_Hb": "12.9", "d90_lab_WBC": "6400", "d90_lab_Na": "138",
            "d90_visit_date": date(2026, 10, 30),
            "d90_facility": "関西医科大学",
            "widget_d90_lab_Hb": "", "widget_d90_facility": "大阪大学"
        })
        saved = self.capture("d90_")
        self.load("d90", saved, self.sync_90)
        self.assertEqual(self.render_d90("d90_lab"), {
            "WBC": "6400", "Hb": "12.9", "Na": "138"
        })
        self.assertEqual(
            self.render_facility(key="d90_facility"), ("F11", "関西医科大学")
        )
        self.assertEqual(self.st.session_state["d90_visit_date"], date(2026, 10, 30))

    def test_90d_stale_widget_values_cannot_override_draft(self):
        saved = {
            "d90_lab_Hb": {"type": "value", "value": "13.1"},
            "d90_facility": {"type": "value", "value": "関西医科大学"},
            "d90_registration_id": {"type": "value", "value": "JUOG-999"}
        }
        self.st.session_state.update({
            "widget_d90_lab_Hb": "6.0", "widget_d90_facility": "大阪大学"
        })
        self.load("d90", saved, self.sync_90)
        self.assertEqual(self.st.session_state["widget_d90_lab_Hb"], "13.1")
        self.assertEqual(self.st.session_state["widget_d90_facility"], "関西医科大学")
        self.assertNotIn("widget_d90_registration_id", self.st.session_state)

    def test_followup_lab_restoration_into_widget_keys(self):
        self.st.session_state.update({
            "fu_lab_Hb": "11.6", "fu_lab_WBC": "6100", "fu_lab_Na": "143",
            "fu_visit_month": "6ヶ月", "fu_visit_date": date(2026, 9, 30),
            "widget_fu_lab_Hb": ""
        })
        saved = self.capture("fu_")
        self.load("fu", saved, self.sync_fu)
        self.assertEqual(self.render_fu("fu_lab", required=False), {
            "WBC": "6100", "Hb": "11.6", "Na": "143"
        })
        self.assertEqual(self.st.session_state["fu_visit_month"], "6ヶ月")
        self.assertEqual(self.st.session_state["fu_visit_date"], date(2026, 9, 30))

    def test_followup_stale_widget_state_is_overwritten(self):
        saved = {
            "fu_lab_Hb": {"type": "value", "value": "12.4"},
            "fu_registration_id": {"type": "value", "value": "JUOG-999"}
        }
        self.st.session_state.update({"widget_fu_lab_Hb": "3.0"})
        self.load("fu", saved, self.sync_fu)
        self.assertEqual(self.st.session_state["widget_fu_lab_Hb"], "12.4")
        self.assertNotIn("widget_fu_registration_id", self.st.session_state)


    def test_followup_visit_specific_keys_do_not_collide(self):
        months = ["6ヶ月", "9ヶ月", "12ヶ月", "15ヶ月", "18ヶ月", "21ヶ月", "24ヶ月（終了）"]
        keys = [self.visit_key(month) for month in months]
        self.assertEqual(keys, ["6m", "9m", "12m", "15m", "18m", "21m", "24m"])
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(self.visit_key("選択してください"), "")
        self.assertEqual(self.visit_key("followup"), "")

    def test_followup_draft_save_verify_and_delete_use_visit_key(self):
        tree = ast.parse((ROOT / "04_followup_crf.py").read_text(encoding="utf-8"))
        call_keys = {"save_crf_draft": 2, "get_crf_draft": 2, "delete_crf_draft": 2}
        for function, index in call_keys.items():
            calls = [n for n in ast.walk(tree)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                     and n.func.id == function]
            visit_calls = [n for n in calls
                           if len(n.args) > index
                           and isinstance(n.args[index], ast.Call)
                           and isinstance(n.args[index].func, ast.Name)
                           and n.args[index].func.id == "followup_visit_key"]
            if function == "delete_crf_draft":
                # Submission-specific value is already in visit_key variable.
                visit_calls = [n for n in calls if len(n.args) > index
                               and isinstance(n.args[index], ast.Name)
                               and n.args[index].id == "visit_key"]
            self.assertTrue(visit_calls, f"{function} lacks the period-specific draft key")


if __name__ == "__main__":
    unittest.main()
