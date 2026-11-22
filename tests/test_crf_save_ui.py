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
        self.secrets = {"registry": {"expected_spreadsheet_id": "isolated-fixture-sheet"}}
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
        actor_patch = patch("isolated_crf_adapter.actor_key", return_value="offline-native-actor")
        actor_patch.start()
        self.addCleanup(actor_patch.stop)
        import juog_crf_save_ui
        self.helper = importlib.reload(juog_crf_save_ui)
        self.st = FakeSt()
        self.saved = []
        self.emails = []
        self.deleted = []
        self.responses = [{"ok":True, "record_version":1, "existing":False}]

        def save(payload):
            self.saved.append(deepcopy(payload))
            response = self.responses.pop(0)
            if response.get("ok"):
                receipt = {
                    "submission_id": payload["submission_id"],
                    "record_key": payload["record_key"],
                    "crf_type": payload["crf_type"],
                    "visit": payload["visit"],
                    "spreadsheet_id": "isolated-fixture-sheet",
                    "audit_verified": True,
                }
                return {**receipt, **response}
            return response

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
                         lambda action, payload=None: {
                             "ok": True, "backend_version": "v2.2.10",
                             "spreadsheet_id": "isolated-fixture-sheet"
                         } if action == "backend_info" else {"ok": False}),
            patch.object(juog_common, "save_crf_payload", save),
            patch.object(juog_common, "send_email", mail),
            patch.object(juog_common, "delete_crf_draft", delete),
        )
        for p in self.patchers:
            p.start()
            self.addCleanup(p.stop)

    def fixture(self, crf_type="perioperative_30d", visit="30d", submission_id="fictional-uuid"):
        import json
        from pathlib import Path
        value=json.loads((Path(__file__).resolve().parents[1]/'clinical_contract/valid_fixtures.json').read_text())[crf_type]
        value.update(visit=visit,record_key=f"JUOG-901|{crf_type}|{visit}",submission_id=submission_id,reporter_email="synthetic@example.invalid")
        value["data"]["fictional"]=True
        if crf_type=="followup":value["data"]["visit_month"]=visit.replace("m","ヶ月")+("（終了）" if visit=="24m" else "")
        return value

    def test_clinical_rejection_does_not_freeze_attempt_or_contact_backend(self):
        from juog_common import registry_call
        bad = self.fixture()
        bad['data']['day30_visit_date'] = '2999-01-01'
        with patch('juog_common.registry_call') as backend:
            self.assertFalse(self.helper.submit_crf_with_feedback(
                page='peri', registration_id='JUOG-901', payload=bad))
            backend.assert_not_called()
        self.assertNotIn(self.helper.attempt_key('peri'), self.st.session_state)
        self.assertEqual(self.saved, [])
        fixed = self.fixture(submission_id='fictional-corrected-input')
        self.assertTrue(self.helper.submit_crf_with_feedback(
            page='peri', registration_id='JUOG-901', payload=fixed))
        self.assertEqual(self.saved[0]['submission_id'], fixed['submission_id'])

    def test_completed_receipt_cannot_acknowledge_another_request(self):
        original=self.fixture()
        self.assertTrue(self.helper.submit_crf_with_feedback(
            page='peri',registration_id='JUOG-901',payload=original))
        for case,visit,payload in [('JUOG-902','30d',None),('JUOG-901','90d',None),
                ('JUOG-901','30d',self.fixture(submission_id='another-request'))]:
            self.assertFalse(self.helper.submit_crf_with_feedback(
                page='peri',registration_id=case,current_visit=visit,payload=payload))
        self.assertEqual(len(self.saved),1)
        self.assertTrue(self.helper.submit_crf_with_feedback(
            page='peri',registration_id='JUOG-901',payload=original))

    def test_full_save_marks_saved_and_shows_version(self):
        ok = self.helper.submit_crf_with_feedback(
            page="peri", registration_id="JUOG-901",
            payload=self.fixture(), email_subject="FAKE", email_body="fictional",
        )
        self.assertTrue(ok)
        self.assertEqual(self.st.session_state["peri_sent_version"], "1")
        self.assertTrue(self.st.session_state["peri_sent"])
        self.assertEqual(self.emails, [])
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
        self.assertFalse(self.st.session_state["d90_sent_email_unconfirmed"])
        self.assertEqual(self.st.session_state["d90_sent_version"], "2")

    def test_verified_initial_save_explicitly_disables_smtp(self):
        # Distinct from replay: a brand-new committed Version must not send.
        # Existing send_email mock captures *any* attempted invocation.
        ok = self.helper.submit_crf_with_feedback(
            page="peri", registration_id="JUOG-901",
            payload=self.fixture(), email_subject="do not send",
            email_body="fictional body")
        self.assertTrue(ok)
        self.assertEqual(self.emails, [])
        self.assertFalse(self.st.session_state["peri_sent_email_failed"])
        self.assertFalse(self.st.session_state["peri_sent_email_unconfirmed"])
        self.assertTrue(any(k == "info" and "通知メールは送信しません" in m
                            for k,m,*_ in self.st.messages))
        self.assertEqual(len(self.deleted), 1)

    def test_replay_never_dispatches_smtp(self):
        self.responses = [{"ok": True, "record_version": 1, "existing": True}]
        self.assertTrue(self.helper.submit_crf_with_feedback(
            page="fu", registration_id="JUOG-901",
            payload=self.fixture("followup","6m")))
        self.assertEqual(self.emails, [])
        self.assertFalse(self.st.session_state["fu_sent_email_unconfirmed"])

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
        self.assertEqual(self.emails, [])

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
            "actor_key":"offline-native-actor", "status":"saving","saving_started_at":time.time(),
            "registration_id":"JUOG-901","payload":self.fixture("day90","90d"),
        }
        pending=self.helper.pending_attempt("d90", self.st.session_state)
        self.assertEqual(pending["status"],"saving")
        self.assertEqual(len(self.saved),0)

    def test_old_abandoned_save_reuses_same_uuid(self):
        import time
        key=self.helper.attempt_key("d90")
        self.st.session_state[key]={
            "actor_key":"offline-native-actor", "status":"saving","saving_started_at":time.time()-130,
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
            "actor_key":"offline-native-actor", "status":"committed","record_version":"1",
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
            "actor_key": "offline-native-actor", "status": "saving", "registration_id": "JUOG-901",
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

    def test_missing_pinned_workbook_fails_without_writes_or_mail(self):
        self.st.secrets = {"registry": {}}
        self.assertFalse(self.helper.submit_crf_with_feedback(
            page="peri", registration_id="JUOG-901", payload=self.fixture()))
        self.assertEqual(self.saved, [])
        self.assertEqual(self.emails, [])
        self.assertEqual(self.deleted, [])

    def test_backend_workbook_id_mismatch_fails_closed(self):
        import juog_common
        with patch.object(juog_common, "registry_call",
                          lambda action, payload=None: {
                              "ok": True, "backend_version": "v2.2.10",
                              "spreadsheet_id": "wrong-workbook"
                          }):
            ok = self.helper.submit_crf_with_feedback(
                page="peri", registration_id="JUOG-901", payload=self.fixture())
        self.assertFalse(ok)
        self.assertEqual(self.saved, [])
        self.assertEqual(self.emails, [])
        self.assertEqual(self.deleted, [])

    def test_backend_missing_workbook_echo_fails_closed(self):
        import juog_common
        with patch.object(juog_common, "registry_call",
                          lambda action, payload=None: {
                              "ok": True, "backend_version": "v2.2.10"
                          }):
            ok = self.helper.submit_crf_with_feedback(
                page="peri", registration_id="JUOG-901", payload=self.fixture())
        self.assertFalse(ok)
        self.assertEqual(self.saved, [])

    def test_wrong_uuid_success_reply_is_unconfirmed_and_retry_reuses_uuid(self):
        self.responses = [
            {"ok": True, "record_version": 2, "existing": False,
             "submission_id": "other-submission"},
            {"ok": True, "record_version": 2, "existing": True,
             "submission_id": "locked-uuid"},
        ]
        payload = self.fixture("day90", "90d", "locked-uuid")
        self.assertFalse(self.helper.submit_crf_with_feedback(
            page="d90", registration_id="JUOG-901", payload=payload))
        self.assertEqual(self.helper.pending_attempt("d90", self.st.session_state)["status"],
                         "uncertain")
        self.assertFalse(self.st.session_state.get("d90_sent", False))
        self.assertEqual(self.emails, [])
        self.assertEqual(self.deleted, [])
        self.assertTrue(self.helper.submit_crf_with_feedback(
            page="d90", registration_id="JUOG-901"))
        self.assertEqual([p["submission_id"] for p in self.saved],
                         ["locked-uuid", "locked-uuid"])
        self.assertEqual(self.emails, [])
        self.assertEqual(self.st.session_state["d90_sent_version"], "2")

    def test_missing_version_ack_fails_without_deleting_draft(self):
        self.responses = [{"ok": True, "existing": False}]
        self.assertFalse(self.helper.submit_crf_with_feedback(
            page="peri", registration_id="JUOG-901", payload=self.fixture()))
        self.assertEqual(len(self.saved), 1)
        self.assertEqual(self.emails, [])
        self.assertEqual(self.deleted, [])
        self.assertFalse(self.st.session_state.get("peri_sent", False))

    def test_missing_existing_flag_is_not_considered_confirmed(self):
        self.responses = [{"ok": True, "record_version": 1}]
        self.assertFalse(self.helper.submit_crf_with_feedback(
            page="peri", registration_id="JUOG-901", payload=self.fixture()))
        self.assertEqual(self.emails, [])
        self.assertEqual(self.deleted, [])

    def test_missing_or_mismatched_receipt_blocks_mail_and_draft_delete(self):
        for key, value in (
            ("spreadsheet_id", "wrong-sheet"),
            ("record_key", "JUOG-901|day90|90d"),
            ("crf_type", "day90"),
            ("visit", "90d"),
            ("audit_verified", False),
            ("audit_verified", None),
        ):
            with self.subTest(field=key, value=value):
                self.st.session_state.clear()
                self.saved.clear()
                self.deleted.clear()
                self.emails.clear()
                self.responses = [{"ok": True, "record_version": 2,
                                   "existing": False, key: value}]
                ok = self.helper.submit_crf_with_feedback(
                    page="peri", registration_id="JUOG-901",
                    payload=self.fixture())
                self.assertFalse(ok)
                self.assertEqual(len(self.saved), 1)
                self.assertEqual(self.emails, [])
                self.assertEqual(self.deleted, [])
                self.assertEqual(self.helper.pending_attempt(
                    "peri", self.st.session_state)["status"], "uncertain")
                self.assertFalse(self.st.session_state.get("peri_sent", False))

    def test_valid_replay_receipt_does_not_duplicate_email(self):
        self.responses = [{"ok": True, "record_version": 2,
                           "existing": True}]
        self.assertTrue(self.helper.submit_crf_with_feedback(
            page="peri", registration_id="JUOG-901",
            payload=self.fixture()))
        self.assertEqual(self.emails, [])
        self.assertEqual(self.st.session_state["peri_sent_version"], "2")

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

