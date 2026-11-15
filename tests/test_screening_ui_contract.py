"""Static regression guards for the screening UI; never connect to GAS.

The safety-critical runtime behavior still requires isolated browser, mail, and
GAS/Sheets integration UAT. These assertions alone do not authorize deployment.
"""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "01_registration_crf.py"


class ScreeningUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.ast_tree = ast.parse(cls.source)

    def test_registration_uses_fragment_instead_of_full_page_widget_reruns(self):
        fn = next(
            n for n in self.ast_tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "_render_screening_form"
        )
        self.assertTrue(any(
            isinstance(d, ast.Attribute) and d.attr == "fragment"
            for d in fn.decorator_list
        ))
        in_fn = ast.get_source_segment(self.source, fn)
        self.assertNotIn("st.rerun()", in_fn)
        self.assertIn('st.rerun(scope="fragment")', in_fn)
        self.assertIn('screening_submit_single_button', in_fn)

    def test_unique_frozen_request_and_retry(self):
        text = self.source
        self.assertIn('st.session_state["screening_submit_attempt"] = _pending', text)
        self.assertIn('deepcopy(_request)', text)
        self.assertIn('deepcopy(screening_payload)', text)
        self.assertIn('registry_call("submit_screening", _pending["request"])', text)
        self.assertIn('if _pending["identity"] != (facility_code, text(local_subject_code))', text)
        self.assertIn('reg_result.get("submission_replay")', text)
        self.assertIn('L = bool(st.session_state.get("screening_sent"))', text)

    def test_backend_version_is_verified_before_mutation(self):
        text = self.source
        self.assertIn('registry_call("backend_info")', text)
        self.assertIn('_backend.get("backend_version") != "v2.2.10"', text)
        self.assertLess(
            text.rfind('registry_call("backend_info")'),
            text.rfind('registry_call("submit_screening", _pending["request"])'),
        )

    def test_progress_shown_only_for_explicit_actions(self):
        text = self.source
        self.assertIn('if reg_draft_clicked:', text)
        self.assertIn('with reg_draft_feedback.container():', text)
        self.assertIn('with st.spinner("仮保存しています…", show_time=True)', text)
        self.assertIn('with st.spinner("中央台帳へ送信しています…", show_time=True)', text)
        self.assertIn('st.download_button(', text)
        self.assertNotIn('MACHINE_READABLE_JSON_START', text)

    def test_one_receipt_uuid_not_recreated_in_retry_branch(self):
        fn = next(
            n for n in self.ast_tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "_render_screening_form"
        )
        uuid_nodes = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name) and n.func.value.id == "uuid"
            and n.func.attr == "uuid4"
        ]
        self.assertEqual(len(uuid_nodes), 1)


if __name__ == "__main__":
    unittest.main()
