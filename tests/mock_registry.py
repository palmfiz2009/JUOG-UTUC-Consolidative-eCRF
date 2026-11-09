"""Loopback-only fake registry for Playwright Streamlit UAT.

Never connects to a real Google Sheet, GAS endpoint, or patient account.
All subjects, report dates, and e-mails are synthetic.
"""
from __future__ import annotations

import json
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 18651
SUBJECT = "JUOG-999"
FACILITY = "F11"
MAIL = "uat@example.invalid"
REGISTERED_AT = date(2026, 8, 1)

LOCK = threading.Lock()
STATE = {"draft": None, "crfs": [], "audit": [], "events": []}


def reply(payload, action, p):
    if action == "validate":
        good = p.get("registration_id") == SUBJECT and p.get("facility_code") == FACILITY
        return {"ok": True} if good else {"ok": False, "error": "SUBJECT_NOT_FOUND"}
    if action == "save_draft":
        if p.get("registration_id") != SUBJECT or p.get("reporter_email") != MAIL:
            return {"ok": False, "error": "INVALID_SYNTHETIC_SUBJECT"}
        with LOCK:
            STATE["draft"] = p.copy()
            STATE["events"].append("save_draft")
        return {"ok": True, "updated_at": "2026-11-09 15:00:00"}
    if action == "get_draft":
        with LOCK:
            d = STATE["draft"]
        if not d:
            return {"ok": True, "source_found": False}
        if p.get("registration_id") != SUBJECT or p.get("reporter_email") != MAIL:
            return {"ok": False, "error": "DRAFT_EMAIL_MISMATCH"}
        with LOCK:
            STATE["events"].append("get_draft")
        return {
            "ok": True, "source_found": True, "draft_state": d["draft_state"],
            "facility_name": d["facility_name"], "reporter_email": MAIL,
            "updated_at": "2026-11-09 15:00:00",
        }
    if action == "save_crf":
        crf = p.get("payload") or {}
        if crf.get("registration_id") != SUBJECT or crf.get("facility_code") != FACILITY:
            return {"ok": False, "error": "FACILITY_MISMATCH"}
        if crf.get("reporter_email") != MAIL:
            return {"ok": False, "error": "INVALID_SYNTHETIC_REPORTER"}
        if crf.get("record_key") != "JUOG-999|perioperative_30d|30d":
            return {"ok": False, "error": "RECORD_KEY_MISMATCH"}
        data = crf.get("data") or {}
        if data.get("reference_date") != "2026-08-25":
            return {"ok": False, "error": "REFERENCE_DATE_MISMATCH"}
        if data.get("day30_visit_date") != "2026-09-24":
            return {"ok": False, "error": "VISIT_DATE_MISMATCH"}
        if data.get("day30_lab_date") != "2026-09-24":
            return {"ok": False, "error": "LAB_DATE_MISMATCH"}
        if crf.get("submission_kind") != "初回報告":
            return {"ok": False, "error": "EXPECTED_INITIAL"}
        with LOCK:
            if STATE["crfs"]:
                return {"ok": False, "error": "INITIAL_ALREADY_EXISTS"}
            entry = crf.copy()
            entry["record_version"] = 1
            STATE["crfs"].append(entry)
            STATE["audit"].append({
                "record_version": 1, "submission_id": crf["submission_id"],
                "record_key": crf["record_key"], "registration_id": SUBJECT,
                "facility_code": FACILITY, "sheet_name": "CRF_30d",
            })
            STATE["events"].append("save_crf")
        return {"ok": True, "existing": False, "record_version": 1,
                "submission_id": crf["submission_id"]}
    if action == "delete_draft":
        with LOCK:
            STATE["draft"] = None
            STATE["events"].append("delete_draft")
        return {"ok": True, "deleted": True}
    return {"ok": False, "error": "UNKNOWN_TEST_ACTION", "action": action}


class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self.send_json({"ok": True, "mode": "LOCAL_MOCK_ONLY"})
        if self.path == "/_test/state":
            with LOCK:
                return self.send_json(STATE)
        return self.send_json({"ok": False}, 404)

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(n)
            body = json.loads(raw)
            if body.get("token") != "LOCAL-UAT-TOKEN-DO-NOT-USE-ELSEWHERE":
                return self.send_json({"ok": False, "error": "BAD_TEST_TOKEN"}, 403)
            if self.path != "/":
                return self.send_json({"ok": False, "error": "WRONG_PATH"}, 404)
            action = body.get("action") or ""
            payload = body.get("payload") or {}
            return self.send_json(reply(body, action, payload))
        except Exception as exc:
            return self.send_json({"ok": False, "error": "MOCK_EXCEPTION:" + str(exc)}, 500)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    with ThreadingHTTPServer((HOST, PORT), Handler) as srv:
        print("Loopback-only UAT backend on 127.0.0.1:" + str(PORT), flush=True)
        srv.serve_forever()
