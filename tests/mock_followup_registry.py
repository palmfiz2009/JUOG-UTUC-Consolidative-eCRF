"""Synthetic loopback registry for real Streamlit 90d/follow-up browser UAT.

No external connectivity, credentials, patients, deployed GAS or Google Sheets.
"""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

HOST, PORT = "127.0.0.1", 18661
SUBJECT, FACILITY, EMAIL = "JUOG-999", "F11", "uat@example.invalid"
SOURCE = {
    "ok": True, "source_found": True, "registration_id": SUBJECT,
    "facility_code": FACILITY, "facility_name": "関西医科大学",
    "surgery_performed": "実施しなかった", "reference_date": "2026-03-01",
    "record_version": 1, "submission_id": "SYNTHETIC-30DAY-SOURCE",
}
STATE = {"drafts": {}, "crfs": [], "audit": [], "events": []}
LOCK = threading.RLock()


def key(p):
    return "|".join(str(p.get(x, "")) for x in ("registration_id", "crf_type", "visit"))


def reply(action, p):
    if action == "validate":
        return {"ok": p.get("registration_id") == SUBJECT and
                p.get("facility_code") == FACILITY}
    if action == "get_crf_linkage":
        if p.get("registration_id") != SUBJECT:
            return {"ok": False, "error": "UNKNOWN_SUBJECT"}
        return SOURCE.copy()
    if action == "save_draft":
        if p.get("registration_id") != SUBJECT or p.get("reporter_email") != EMAIL:
            return {"ok": False, "error": "INVALID_SYNTHETIC_DRAFT"}
        with LOCK:
            STATE["drafts"][key(p)] = p.copy()
            STATE["events"].append({"action": action, "key": key(p)})
        return {"ok": True, "updated_at": "2026-11-09T12:00:00+09:00"}
    if action == "get_draft":
        with LOCK:
            draft = STATE["drafts"].get(key(p))
            STATE["events"].append({"action": action, "key": key(p)})
        if not draft:
            return {"ok": True, "source_found": False}
        if p.get("reporter_email") != EMAIL:
            return {"ok": False, "error": "DRAFT_EMAIL_MISMATCH"}
        return {"ok": True, "source_found": True, "draft_state": draft["draft_state"],
                "facility_name": SOURCE["facility_name"], "reporter_email": EMAIL,
                "updated_at": "2026-11-09T12:00:00+09:00"}
    if action == "delete_draft":
        with LOCK:
            was_there = STATE["drafts"].pop(key(p), None) is not None
            STATE["events"].append({"action": action, "key": key(p)})
        return {"ok": True, "deleted": was_there}
    if action == "save_crf":
        d = p.get("payload") or {}
        if d.get("registration_id") != SUBJECT or d.get("facility_code") != FACILITY:
            return {"ok": False, "error": "INVALID_SYNTHETIC_SUBJECT"}
        if d.get("reporter_email") != EMAIL:
            return {"ok": False, "error": "INVALID_SYNTHETIC_REPORTER"}
        kind = d.get("crf_type")
        visit = d.get("visit")
        if (kind, visit) not in {("day90", "90d"), ("followup", "6m")}:
            return {"ok": False, "error": "UNEXPECTED_SYNTHETIC_CRF"}
        if d.get("record_key") != key(d):
            return {"ok": False, "error": "RECORD_KEY_MISMATCH"}
        data = d.get("data") or {}
        if data.get("source_30d_linked") is not True or data.get("source_30d_record_version") != 1:
            return {"ok": False, "error": "SOURCE_NOT_LINKED"}
        if data.get("source_30d_submission_id") != SOURCE["submission_id"] or data.get("reference_date") != SOURCE["reference_date"]:
            return {"ok": False, "error": "SOURCE_INCONSISTENT"}
        expected = "2026-05-30" if kind == "day90" else "2026-09-01"
        if data.get("visit_date") != expected or data.get("vital_status") != "生存":
            return {"ok": False, "error": "EXPECTED_VISIT_MISSING"}
        if str(data.get("labs", {}).get("Hb")) not in ("12.9", "12.90"):
            return {"ok": False, "error": "RESTORED_LAB_NOT_SAVED"}
        with LOCK:
            version = 1 + sum(1 for prev in STATE["crfs"]
                              if prev["record_key"] == d["record_key"])
            if version != 1 or d.get("submission_kind") != "初回報告":
                return {"ok": False, "error": "INITIAL_ALREADY_EXISTS"}
            recorded = d.copy()
            recorded["record_version"] = version
            STATE["crfs"].append(recorded)
            STATE["audit"].append({
                "record_key": d["record_key"], "record_version": version,
                "submission_id": d["submission_id"], "registration_id": SUBJECT,
                "facility_code": FACILITY,
                "sheet_name": "CRF_90d" if kind == "day90" else "CRF_Followup",
            })
            STATE["events"].append({"action": "save_crf", "key": d["record_key"]})
        return {"ok": True, "record_version": version, "submission_id": d["submission_id"]}
    return {"ok": False, "error": "UNEXPECTED_TEST_ACTION", "action": action}


class Handler(BaseHTTPRequestHandler):
    def json_response(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self.json_response({"ok": True, "mode": "LOOPBACK_MOCK"})
        if self.path == "/_test/state":
            with LOCK:
                return self.json_response(STATE)
        return self.json_response({"ok": False}, 404)

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(n))
            if self.path != "/" or body.get("token") != "LOCAL-UAT-TOKEN-DO-NOT-USE-ELSEWHERE":
                return self.json_response({"ok": False, "error": "INVALID_TEST_REQUEST"}, 403)
            return self.json_response(reply(body.get("action"), body.get("payload") or {}))
        except Exception as exc:
            return self.json_response({"ok": False, "error": "MOCK_EXCEPTION:" + str(exc)}, 500)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    with ThreadingHTTPServer((HOST, PORT), Handler) as server:
        print("Loopback mock ready", flush=True)
        server.serve_forever()
