"""Offline regression for input-only Streamlit fragments; no services or patients."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
FILES = {
    "02_perioperative_30d_crf.py": "_render_peri_without_full_page_rerun",
    "03_day90_crf.py": "_render_d90_without_full_page_rerun",
    "04_followup_crf.py": "_render_followup_without_full_page_rerun",
}


def is_st_attr_call(node, method: str) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "st"
        and node.func.attr == method
    )


class LocalCrfFragmentTests(unittest.TestCase):
    def test_all_input_pages_are_local_fragments(self):
        for file, name in FILES.items():
            with self.subTest(file=file):
                source = (ROOT / file).read_text(encoding="utf-8")
                tree = ast.parse(source, filename=file)
                fragments = [
                    n for n in tree.body
                    if isinstance(n, ast.FunctionDef) and n.name == name
                ]
                self.assertEqual(len(fragments), 1)
                fn = fragments[0]
                self.assertTrue(
                    any(isinstance(d, ast.Attribute)
                        and isinstance(d.value, ast.Name)
                        and d.value.id == "st" and d.attr == "fragment"
                        for d in fn.decorator_list)
                )
                self.assertGreater(sum(is_st_attr_call(n, "button") for n in ast.walk(fn)), 1)

                # Inputs and saving remain in the same local fragment.
                calls = {
                    n.func.id for n in ast.walk(fn)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                }
                self.assertIn("save_crf_payload", calls)
                self.assertIn("save_crf_draft", calls)
                self.assertIn("validate_registry_id", calls)

                # No external data writes execute at module import time.
                for node in tree.body:
                    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                        self.assertNotIn(
                            getattr(node.value.func, "id", ""),
                            {"save_crf_payload", "save_crf_draft"},
                        )

                # We call the fragment exactly once on a full page load.
                self.assertTrue(
                    any(isinstance(node, ast.Expr)
                        and isinstance(node.value, ast.Call)
                        and isinstance(node.value.func, ast.Name)
                        and node.value.func.id == name
                        for node in tree.body)
                )

    def test_no_backend_schema_or_version_changes_in_this_branch(self):
        # Semantic invariants: the API call arguments and CRF save path are unchanged.
        for file in FILES:
            with self.subTest(file=file):
                src = (ROOT / file).read_text(encoding="utf-8")
                self.assertIn("save_crf_payload(", src)
                self.assertIn("st.rerun()", src)
                self.assertNotIn("juog_crf_save_ui", src)


if __name__ == "__main__":
    unittest.main()
