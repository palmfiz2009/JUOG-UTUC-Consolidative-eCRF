"""Isolated regression tests for post-registration CRF UI save behavior.

All identifiers are fictional. No network, database, app deployment or emails.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import importlib
import sys
import types
import unittest
from unittest.mock import patch


class FakeSt(types.ModuleType):
    def __init__(self):
        super().__init__("streamlit")
        self.session_state = {}
        self.messages = []

    @contextmanager
    def spinner(self, text, show_time=False):
        self.messages.append(("spinner", text, show_time))
        yield

    def success(self, text):
        self.messages.append(("success", text))

    def error(self, text):
        self.messages.append(("error", text))

    def warning(self, text):
        self.messages.append(("warning", text))

    def info(self, text):
        self.messages.append(("info", text))


class CRFSaveUITests(unittest.TestCase):
    def setUp(self):
        import juog_crf_save_ui
        self.helper = importlib.reload(juog_crf_save_ui)
        self.st = FakeSt()
        self.saved = []
        self.emails = []
        self.deleted = []
        self.responses = [{"ok":True, "record_version":1, "existing":False}]

        def save(payload):
            self.saved.append(deepcopy(payload))
            return self.responses.pop(0)

        def mail(subject, body, receiver):
            self.emails.append((subject, body, receiver))
            return True, None

        def delete(registration_id, crf_type, visit):
            self.deleted.append((registration_id, crf_type, visit))
            return {"ok":True}

        import juog_common
        self.patchers = (
            patch.dict(sys.modules, {"streamlit": self.st}),
            patch.object(juog_common, "registry_call",
                         lambda action, payload=None: {"ok":True,"backend_version":"v2.2.10"}
                         if action=="backend_info" else {"ok":False}),
            patch.object(juog_common, "save_crf_payload", save),
            patch.object(juog_common, "send_email", mail),
            patch.object(juog_common, "delete_crf_draft", delete),
        )
        for p in self.patchers:
            p.start()
            self.addCleanup(p.stop)

    def fixture(self, crf_type="perioperative_30d", visit="30d", submission_id="fictional-uuid"):
        return {
            "registration_id": "JUOG-901",
            "crf_type": crf_type,
            "visit": visit,
            "record_key": f"JUOG-901|{crf_type}|{visit}",
            "submission_id": submission_id,
            "reporter_email": "synthetic@example.invalid",
            "data": {"fictional": True},
        }

    def test_full_save_marks_saved_and_shows_version(self):
        ok = self.helper.submit_crf_with_feedback(
            page="peri", registration_id="JUOG-901",
            payload=self.fixture(), email_subject="FAKE", email_body="fictional",
        )
        self.assertTrue(ok)
        self.assertEqual(self.st.session_state["peri_sent_version"], "1")
        self.assertTrue(self.st.session_state["peri_sent"])
        self.assertEqual(len(self.emails), 1)
        self.assertEqual(self.deleted[0], ("JUOG-901", "perioperative_30d", "30d"))
        self.assertTrue(any(k == "success" and "Version 1" in m for k,m,*_ in self.st.messages))

    def test_failed_reply_retry_uses_same_frozen_payload_and_no_duplicate_mail(self):
        self.responses = [
            {"ok":False, "error":"CONNECTION_UNCERTAIN"},
            {"ok":True, "record_version":2, "existing":True},
        ]
        payload = self.fixture("day90", "90d", "fixed-uuid")
        self.assertFalse(self.helper.submit_crf_with_feedback(
            page="d90", registration_id="JUOG-901", payload=payload,
            email_subject="FAKE", email_body="FROZEN",
        ))
        self.assertEqual(self.helper.pending_attempt("d90",self.st.session_state)["status"],"uncertain")
        payload["data"]["fictional"] = False
        payload["submission_id"] = "wrong-uuid"
        self.assertTrue(self.helper.submit_crf_with_feedback(page="d90", registration_id="JUOG-901"))
        self.assertEqual([a["submission_id"] for a in self.saved], ["fixed-uuid", "fixed-uuid"])
        self.assertEqual([a["data"]["fictional"] for a in self.saved], [True, True])
        self.assertEqual(self.emails, [])
        self.assertTrue(self.st.session_state["d90_sent_email_unconfirmed"])
        self.assertEqual(self.st.session_state["d90_sent_version"], "2")

    def test_pending_retry_rejects_different_patient(self):
        self.responses = [{"ok":False,"error":"TIMEOUT"}]
        self.helper.submit_crf_with_feedback(
            page="fu", registration_id="JUOG-901",
            payload=self.fixture("followup","6m"), visit_display="6ヶ月",
        )
        self.assertFalse(self.helper.submit_crf_with_feedback(page="fu", registration_id="JUOG-902"))
        self.assertEqual(len(self.saved),1)

    def test_multiple_visits_not_mixed_or_rekeyed(self):
        self.responses = [{"ok":True,"record_version":3,"existing":False}]
        self.assertTrue(self.helper.submit_crf_with_feedback(
            page="fu", registration_id="JUOG-901",
            payload=self.fixture("followup","12m"), visit_display="12ヶ月",
        ))
        self.assertEqual(self.st.session_state["fu_sent_visit"],"12ヶ月")
        self.assertTrue(self.helper.submit_crf_with_feedback(page="fu", registration_id="JUOG-901"))
        self.assertEqual(len(self.saved),1)
        self.assertEqual(len(self.emails),1)

    def test_pending_followup_retry_rejects_changed_visit(self):
        self.responses = [{"ok":False,"error":"TIMEOUT"}]
        self.assertFalse(self.helper.submit_crf_with_feedback(
            page="fu", registration_id="JUOG-901",
            payload=self.fixture("followup","6m"), visit_display="6ヶ月",
        ))
        self.assertFalse(self.helper.submit_crf_with_feedback(
            page="fu", registration_id="JUOG-901", current_visit="9m",
        ))
        self.assertEqual(len(self.saved),1)

    def test_saving_state_stays_locked_during_active_request(self):
        import time
        key=self.helper.attempt_key("d90")
        self.st.session_state[key]={
            "status":"saving","saving_started_at":time.time(),
            "registration_id":"JUOG-901","payload":self.fixture("day90","90d"),
        }
        pending=self.helper.pending_attempt("d90", self.st.session_state)
        self.assertEqual(pending["status"],"saving")
        self.assertEqual(len(self.saved),0)

    def test_old_abandoned_save_reuses_same_uuid(self):
        import time
        key=self.helper.attempt_key("d90")
        self.st.session_state[key]={
            "status":"saving","saving_started_at":time.time()-130,
            "registration_id":"JUOG-901","payload":self.fixture("day90","90d","old-uuid"),
            "email_subject":"FAKE","email_body":"FAKE","had_warnings":False,
            "visit_display":"",
        }
        pending=self.helper.pending_attempt("d90",self.st.session_state)
        self.assertEqual(pending["status"],"uncertain")
        self.responses=[{"ok":True,"existing":True,"record_version":1}]
        self.assertTrue(self.helper.submit_crf_with_feedback(page="d90",registration_id="JUOG-901"))
        self.assertEqual(self.saved[0]["submission_id"],"old-uuid")
        self.assertEqual(len(self.emails),0)

    def test_committed_but_not_finalized_save_can_be_confirmed(self):
        self.st.session_state[self.helper.attempt_key("peri")]={
            "status":"committed","record_version":"1",
            "registration_id":"JUOG-901","payload":self.fixture(),
            "email_subject":"FAKE","email_body":"FAKE","had_warnings":False,
            "visit_display":"",
        }
        self.assertIsNotNone(self.helper.pending_attempt("peri",self.st.session_state))
        self.responses=[{"ok":True,"existing":True,"record_version":1}]
        self.assertTrue(self.helper.submit_crf_with_feedback(page="peri",registration_id="JUOG-901"))
        self.assertEqual(len(self.saved),1)
        self.assertEqual(len(self.emails),0)

    def test_interrupted_request_status_recovers_for_same_id_retry(self):
        self.st.session_state[self.helper.attempt_key("d90")] = {
            "status": "saving", "registration_id": "JUOG-901",
            "payload": self.fixture("day90", "90d"),
            "email_subject": "fictional", "email_body": "fictional",
            "had_warnings": False, "visit_display": "",
        }
        state = self.helper.pending_attempt("d90", self.st.session_state)
        self.assertEqual(state["status"],"uncertain")
        self.assertTrue(self.helper.submit_crf_with_feedback(page="d90",registration_id="JUOG-901"))
        self.assertEqual(len(self.saved),1)

    def test_old_gas_backend_is_rejected_before_save(self):
        import juog_common
        with patch.object(juog_common,"registry_call",
                          lambda action,payload=None:{"ok":True,"backend_version":"v2.2.9"}):
            ok=self.helper.submit_crf_with_feedback(
                page="peri",registration_id="JUOG-901",payload=self.fixture(),
            )
        self.assertFalse(ok)
        self.assertEqual(len(self.saved),0)
        self.assertEqual(self.emails,[])
        self.assertEqual(self.deleted,[])

    def test_status_not_marked_success_when_server_rejects(self):
        self.responses = [{"ok":False, "error":"INITIAL_ALREADY_EXISTS"}]
        self.assertFalse(self.helper.submit_crf_with_feedback(
            page="peri", registration_id="JUOG-901",payload=self.fixture(),
        ))
        self.assertFalse(self.st.session_state.get("peri_sent",False))
        self.assertEqual(self.emails,[])
        self.assertEqual(self.deleted,[])


if __name__ == "__main__":
    unittest.main()
