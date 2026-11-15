"""Offline admin-MDT UI regression: no live GAS, SMTP, or patient records."""
from __future__ import annotations
import ast
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ADMIN_FILE = ROOT / "05_admin_mdt_registration.py"


def _get_fragment():
    tree = ast.parse(ADMIN_FILE.read_text(encoding="utf-8"))
    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_render_admin_final_decision"
    ]
    return tree, functions


class AdminDecisionFragmentContract(unittest.TestCase):
    def test_final_adjudication_widgets_only_reexecute_fragment(self):
        tree, funcs = _get_fragment()
        self.assertEqual(len(funcs), 1)
        fn = funcs[0]
        self.assertTrue(any(
            isinstance(d, ast.Attribute)
            and isinstance(d.value, ast.Name)
            and d.value.id == "st" and d.attr == "fragment"
            for d in fn.decorator_list
        ))
        self.assertTrue(any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name)
            and n.func.value.id == "st" and n.func.attr == "radio"
            for n in ast.walk(fn)
        ))
        self.assertTrue(any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Constant)
            and n.func.value == "finalize_mdt"
            for n in ast.walk(fn)
        ) is False)  # action is the first argument to registry_call, not its callee
        self.assertTrue(any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "registry_call"
            and bool(n.args)
            and isinstance(n.args[0], ast.Constant)
            and n.args[0].value == "finalize_mdt"
            for n in ast.walk(fn)
        ))
        self.assertTrue(any(
            isinstance(n, ast.Expr)
            and isinstance(n.value, ast.Call)
            and isinstance(n.value.func, ast.Name)
            and n.value.func.id == fn.name
            for n in tree.body
        ))
        # Existing admin login and guarded backend check run outside this fragment.
        self.assertTrue(any(
            isinstance(n, ast.FunctionDef) and n.name == "admin_authenticated"
            for n in tree.body
        ))

    def test_soft_message_is_only_appended_for_ineligible_decision(self):
        _tree, funcs = _get_fragment()
        fn = funcs[0]
        matches = []
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            code = ast.unparse(node.test)
            if code != "decision_code == 'INELIGIBLE'":
                continue
            edits = [n for n in node.body if isinstance(n, ast.AugAssign)
                     and isinstance(n.target, ast.Name) and n.target.id == "body"]
            if edits:
                matches.extend(edits)
        self.assertEqual(len(matches), 1)
        text_value = ast.literal_eval(matches[0].value)
        self.assertIn("今後も適応となる症例がございましたら", text_value)
        self.assertIn("ぜひご紹介いただけますと幸いです", text_value)
        self.assertNotIn("患者氏名", text_value)

    def test_existing_mdts_never_autosubmit_on_widget_changes(self):
        _tree, funcs = _get_fragment()
        fn = funcs[0]
        writes = [n for n in ast.walk(fn)
                  if isinstance(n, ast.Call)
                  and isinstance(n.func, ast.Name)
                  and n.func.id == "registry_call"
                  and n.args and isinstance(n.args[0], ast.Constant)
                  and n.args[0].value == "finalize_mdt"]
        self.assertEqual(len(writes), 1)
        self.assertIn("if submitted:", ADMIN_FILE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
