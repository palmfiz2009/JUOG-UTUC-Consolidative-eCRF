"""Keep complete DOB in the browser only, never in the screening draft.
Pure source check; offline with no Streamlit secrets or data.
"""
import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent.parent

class BirthDateDraftExclusionTests(unittest.TestCase):
    def test_screening_draft_excludes_complete_birth_date(self):
        source=(ROOT/"01_registration_crf.py").read_text(encoding="utf-8")
        tree=ast.parse(source)
        saves=[]
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call) or not isinstance(n.func,ast.Name):
                continue
            if n.func.id=="capture_draft_state":
                saves.append(n)
        self.assertEqual(len(saves),1)
        keywords={k.arg:k.value for k in saves[0].keywords}
        exclusions=ast.literal_eval(keywords["exclude_prefixes"])
        self.assertIn("reg_birth_date",exclusions)
        self.assertIn("reg_draft",exclusions)
        self.assertIn("birth_year_month",source)
        self.assertIn("age_at_consent",source)
        self.assertIn("仮保存から再開した場合は再入力",source)

    def test_server_has_both_legacy_read_redactions(self):
        gas=(ROOT/"05_registry_google_apps_script.gs").read_text(encoding="utf-8")
        self.assertEqual(gas.count("draft_state:stripDirectIdentifiers_(draftState)"),2)
        self.assertIn("function containsLabeledIdentifierText_",gas)
        self.assertIn("function stripDirectIdentifiers_",gas)

if __name__ == "__main__":
    unittest.main()
