"""Offline proof that CRF UI retries retain the original payload and UUID."""
from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
import unittest

from juog_common import (
    freeze_crf_submission_attempt,
    release_crf_attempt_if_certainly_rejected,
)

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "02_perioperative_30d_crf.py": "_crf_pending_peri",
    "03_day90_crf.py": "_crf_pending_d90",
    "04_followup_crf.py": "_crf_pending_fu",
}


def payload(uuid="fictional-uuid-1", date="2026-11-15T10:00:00+09:00", value="fictional"):
    return {
        "record_key": "JUOG-901|perioperative_30d|30d",
        "submission_id": uuid,
        "submitted_at": date,
        "data": {"fake": value},
    }


class FrozenCrfSubmissionTests(unittest.TestCase):
    def test_retry_uses_identical_first_snapshot_and_uuid(self):
        state = {}
        initial, error = freeze_crf_submission_attempt(state, "slot", payload())
        self.assertFalse(error)
        later, error = freeze_crf_submission_attempt(
            state, "slot", payload(uuid="new-uuid", date="new-time")
        )
        self.assertFalse(error)
        self.assertEqual(later, initial)
        self.assertEqual(later["submission_id"], "fictional-uuid-1")
        self.assertEqual(len(state), 1)

    def test_changed_body_is_blocked_until_reconciled(self):
        state = {}
        first, _ = freeze_crf_submission_attempt(state, "slot", payload())
        second, error = freeze_crf_submission_attempt(
            state, "slot", payload(value="changed-after-uncertain-save")
        )
        self.assertIsNone(second)
        self.assertIn("保存結果が未確認", error)
        self.assertEqual(state["slot"]["payload"], first)

    def test_changed_record_scope_is_blocked(self):
        state = {}
        freeze_crf_submission_attempt(state, "slot", payload())
        different = payload()
        different["record_key"] = "JUOG-902|perioperative_30d|30d"
        result, error = freeze_crf_submission_attempt(state, "slot", different)
        self.assertIsNone(result)
        self.assertTrue(error)

    def test_payload_is_defensively_copied(self):
        state = {}
        original = payload()
        result, _ = freeze_crf_submission_attempt(state, "slot", original)
        original["data"]["fake"] = "external mutation"
        result["data"]["fake"] = "local mutation"
        self.assertEqual(state["slot"]["payload"]["data"]["fake"], "fictional")

    def test_explicit_prewrite_rejections_unlock_corrected_attempt(self):
        for error in (
            "MISSING_CORRECTION_REASON",
            "INITIAL_ALREADY_EXISTS",
            "NO_PRIOR_RECORD_FOR_CORRECTION",
            "DIRECT_IDENTIFIER_NOT_ALLOWED",
            "VALIDATION_FAILED",
        ):
            with self.subTest(error=error):
                state = {}
                freeze_crf_submission_attempt(state, "slot", payload())
                self.assertTrue(
                    release_crf_attempt_if_certainly_rejected(
                        state, "slot", {"ok": False, "error": error}
                    )
                )
                self.assertNotIn("slot", state)

    def test_unknown_failure_must_remain_frozen(self):
        for error in (
            "CRF_AUDIT_UNCONFIRMED",
            "CRF_READBACK_UNCONFIRMED",
            "LOCK_TIMEOUT",
            "SERVER_ERROR",
            "NETWORK_TIMEOUT",
            "",
        ):
            with self.subTest(error=error):
                state = {}
                freeze_crf_submission_attempt(state, "slot", payload())
                self.assertFalse(
                    release_crf_attempt_if_certainly_rejected(
                        state, "slot", {"ok": False, "error": error}
                    )
                )
                self.assertEqual(state["slot"]["payload"]["submission_id"], "fictional-uuid-1")

    def test_success_does_not_release_until_receipt_is_handled(self):
        state = {}
        freeze_crf_submission_attempt(state, "slot", payload())
        self.assertFalse(release_crf_attempt_if_certainly_rejected(
            state, "slot", {"ok": True, "record_version": 1}
        ))
        self.assertIn("slot", state)

    def test_every_crf_fills_and_freezes_before_backend_send(self):
        for path, slot in PAGES.items():
            with self.subTest(page=path):
                source = (ROOT / path).read_text(encoding="utf-8")
                self.assertIn(f'st.session_state, "{slot}", payload', source)
                self.assertIn(f'"{slot}", save_result', source)
                self.assertLess(
                    source.index("freeze_crf_submission_attempt(\n"),
                    source.index("save_crf_payload(payload)")
                )
                ast.parse(source, filename=path)


if __name__ == "__main__":
    unittest.main()
