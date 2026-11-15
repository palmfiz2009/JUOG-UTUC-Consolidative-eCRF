"""UI contract: replayed CRF confirmations must not send duplicate email.

Tests only Python source AST. No Streamlit, API calls or patient records.
"""
from __future__ import annotations
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = {
    "02_perioperative_30d_crf.py": "peri",
    "03_day90_crf.py": "d90",
    "04_followup_crf.py": "fu",
}


def invoked(node: ast.AST, name: str) -> bool:
    return any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name)
               and x.func.id == name for x in ast.walk(node))


class ReplayNotificationTests(unittest.TestCase):
    def test_replayed_uuid_does_not_trigger_email(self):
        for file, prefix in PAGES.items():
            with self.subTest(file=file):
                src = (ROOT / file).read_text(encoding="utf-8")
                tree = ast.parse(src, filename=file)
                candidate = [
                    x for x in ast.walk(tree) if isinstance(x, ast.If)
                    and ast.unparse(x.test) == "save_result.get('existing')"
                ]
                self.assertEqual(len(candidate), 1, "must distinguish already-saved UUID")
                case = candidate[0]
                self.assertFalse(any(invoked(node, "send_email") for node in case.body),
                                 "already saved request must not email again")
                self.assertTrue(any(invoked(node, "send_email") for node in case.orelse),
                                "new request must still send notification")
                self.assertIn(f'{prefix}_sent_email_unverified', src)
                self.assertIn("通知メールを重複送信しませんでした", src)

    def test_identical_correction_does_not_claim_new_version(self):
        for file, prefix in PAGES.items():
            with self.subTest(file=file):
                source = (ROOT / file).read_text(encoding="utf-8")
                tree = ast.parse(source, filename=file)
                branch = [
                    n for n in ast.walk(tree) if isinstance(n, ast.If)
                    and ast.unparse(n.test) ==
                    "save_result.get('error') == 'DUPLICATE_CONTENT_ALREADY_RECORDED'"
                ]
                self.assertEqual(len(branch),1)
                self.assertFalse(invoked(ast.Module(body=branch[0].body,type_ignores=[]),"send_email"))
                self.assertTrue(invoked(ast.Module(body=branch[0].body,type_ignores=[]),
                                        "release_crf_attempt_if_certainly_rejected"))
                self.assertIn("新しい版は作成せず、メールも再送していません",source)
                self.assertIn("@st.fragment",source)

    def test_only_definite_duplicate_error_releases_frozen_retry(self):
        from juog_common import (
            freeze_crf_submission_attempt,
            release_crf_attempt_if_certainly_rejected,
        )
        payload = {
            "submission_id":"synthetic-uuid-1",
            "submitted_at":"2026-11-16T06:00:00+09:00",
            "record_key":"JUOG-901|perioperative_30d|30d",
            "data":{"fully_fictional": True},
        }
        for err, should_release in [
            ("DUPLICATE_CONTENT_ALREADY_RECORDED",True),
            ("PREVIOUS_CRF_AUDIT_UNCONFIRMED",False),
            ("CRF_AUDIT_UNCONFIRMED",False),
            ("SERVER_ERROR",False),
        ]:
            with self.subTest(error=err):
                session = {}
                freeze_crf_submission_attempt(session,"slot",payload)
                found = release_crf_attempt_if_certainly_rejected(
                    session,"slot",{"ok":False,"error":err}
                )
                self.assertEqual(found,should_release)
                self.assertEqual("slot" in session,not should_release)


if __name__ == "__main__":
    unittest.main()
