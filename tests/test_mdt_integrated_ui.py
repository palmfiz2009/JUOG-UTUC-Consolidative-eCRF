"""Source-only tests for MDT UI behavior; never imports a live Streamlit app."""
from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent


def extract_function(filename: str, name: str, scope: dict) -> object:
    source = (ROOT / filename).read_text(encoding="utf-8")
    module = ast.parse(source, filename=filename)
    fn = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == name)
    isolated = ast.Module(body=[fn], type_ignores=[])
    exec(compile(ast.fix_missing_locations(isolated), filename, "exec"), scope)
    return scope[name]


class MdtMailTests(unittest.TestCase):
    def setUp(self):
        self.sent = []
        emails = {
            "radiology_email": "rad@example.org",
            "medical_oncology_email": "onc@example.org",
            "urology_email": "uro@example.org",
        }
        self.secrets = {"mdt_reviewers": emails}
        def send(subject, body, recipients):
            self.sent.append((subject, body, recipients))
            return (True, None)
        self.scope = {
            "st": SimpleNamespace(secrets=self.secrets),
            "_smtp_send": send,
            "valid_email": lambda s: bool(re.fullmatch(r"[^@ ]+@[^@ ]+\.[^@ ]+", s)),
        }
        self.send = extract_function(
            "05_admin_mdt_registration.py", "notify_mdt_final_result", self.scope
        )

    def test_three_reviewers_receive_final_status_and_public_reason(self):
        ok, err = self.send("JUOG-SCR-TEST", "架空施設", "不適格", "対外説明文")
        self.assertTrue(ok, err)
        self.assertEqual(len(self.sent), 1)
        subject, body, addresses = self.sent[0]
        self.assertEqual(len(addresses), 3)
        self.assertIn("不適格", subject)
        self.assertIn("対外説明文", body)
        self.assertNotIn("consensus_note", body)
        self.assertNotIn("合意形成記録：", body)

    def test_missing_reviewer_address_does_not_send(self):
        del self.secrets["mdt_reviewers"]["radiology_email"]
        ok, _err = self.send("JUOG-SCR-TEST", "架空施設", "保留")
        self.assertFalse(ok)
        self.assertFalse(self.sent)

    def test_failed_smtp_does_not_claim_success(self):
        self.scope["_smtp_send"] = lambda *args: (False, "TEST_ONLY_FAKE_ERROR")
        ok, err = self.send("JUOG-SCR-TEST", "架空施設", "適格")
        self.assertFalse(ok)
        self.assertIn("失敗", err)


class MdtCorrectionTests(unittest.TestCase):
    def test_prefill_and_new_form(self):
        source_scope = {"prior": {"central_recist": "PR"}, "correction_mode": True}
        helper = extract_function("06_mdt_reviewer.py", "_previous_index", source_scope)
        choices = ["選択してください", "CR", "PR", "SD", "PD", "NE"]
        self.assertEqual(helper(choices, "central_recist"), 2)
        source_scope["correction_mode"] = False
        self.assertEqual(helper(choices, "central_recist"), 0)


if __name__ == "__main__":
    unittest.main()
