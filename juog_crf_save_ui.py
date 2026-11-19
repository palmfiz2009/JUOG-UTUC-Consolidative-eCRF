"""Shared UI-only submission workflow for the three post-registration CRFs.

Preserves the existing GAS action and append-only versioning.  No new app,
backend, spreadsheet, or persistent store is created. The pending request is
frozen in Streamlit session state so a retry in that session uses the original
submission UUID and payload rather than creating a new version.
"""
from __future__ import annotations

from copy import deepcopy
import time

_PROFILES = {
    "peri": ("perioperative_30d", "30d", "周術期・術後30日"),
    "d90": ("day90", "90d", "術後90日"),
    "fu": ("followup", "followup", "定期経過"),
}


def attempt_key(page: str) -> str:
    if page not in _PROFILES:
        raise ValueError("Unknown CRF page")
    return f"_juog_{page}_save_attempt"


def pending_attempt(page: str, session_state):
    state = session_state.get(attempt_key(page))
    if not isinstance(state, dict):
        return None
    # Keep the button disabled while an active network request may still run.
    # A truly abandoned request can be confirmed with its original UUID after
    # two minutes, rather than triggering a second write on an ordinary rerun.
    if state.get("status") == "saving":
        start = float(state.get("saving_started_at") or 0)
        # Older sessions can lack the timestamp; they cannot represent a
        # currently timed request created by this version of the helper.
        # Confirm them with the same frozen UUID rather than deadlocking save.
        if not start or time.time() - start >= 120:
            state["status"] = "uncertain"
    return state if state.get("status") in ("prepared", "uncertain", "saving", "committed") else None


def submit_crf_with_feedback(
    *,
    page: str,
    registration_id: str,
    payload: dict | None = None,
    email_subject: str = "",
    email_body: str = "",
    warnings=(),
    visit_display: str = "",
    current_visit: str = "",
):
    """Commit a frozen payload and show local progress next to the action area.

    No automatic retry, timer, background save, or new UUID is generated here.
    If a reply is lost, the *same* immutable payload is used on user-triggered
    retry. The server must still enforce UUID idempotency and append-only audit.
    """
    import streamlit as st
    from juog_common import delete_crf_draft, registry_call, save_crf_payload, send_email

    if page not in _PROFILES:
        raise ValueError("Unknown CRF page")
    crf_type, draft_visit, display_name = _PROFILES[page]
    key = attempt_key(page)
    attempt = st.session_state.get(key)
    from isolated_crf_adapter import actor_key
    try:
        actor = actor_key(st)
    except Exception:
        st.error("本人認証・期限・承認条件を確認できないため保存を停止しました。")
        return False
    if attempt is not None and attempt.get("actor_key") != actor:
        st.error("保存要求の本人が一致しません。事務局で未確定要求を照合してください。")
        return False

    if attempt is None:
        if not isinstance(payload, dict):
            st.error("再送対象の申請が見つかりません。事務局に確認してください。")
            return False
        if payload.get("crf_type") != crf_type:
            st.error("CRF種別が一致しません。保存を中止しました。")
            return False
        if str(payload.get("registration_id") or "") != registration_id:
            st.error("登録番号が一致しません。保存を中止しました。")
            return False
        if not payload.get("submission_id") or not payload.get("record_key"):
            st.error("送信IDまたは記録キーが不明です。保存を中止しました。")
            return False
        attempt = {
            "actor_key": actor,
            "status": "prepared",
            "payload": deepcopy(payload),
            "registration_id": registration_id,
            "email_subject": str(email_subject),
            "email_body": str(email_body),
            "had_warnings": bool(warnings),
            "visit_display": str(visit_display),
        }
        st.session_state[key] = attempt
    else:
        if attempt.get("status") == "complete":
            st.info("この送信はすでに確認されています。追加送信はしません。")
            return True
        frozen = attempt.get("payload") or {}
        if (attempt.get("registration_id") != registration_id or
                frozen.get("crf_type") != crf_type):
            st.error("未確認の送信と登録番号が一致しません。別症例として送信せず事務局に確認してください。")
            return False
        if current_visit and str(frozen.get("visit") or "") != current_visit:
            st.error("送信未確認の報告時点と現在の報告時点が異なります。以前の報告を事務局で確認してください。")
            return False
        if frozen.get("record_key") != "|".join((
            registration_id, crf_type, str(frozen.get("visit") or "")
        )):
            st.error("保存内容の識別キーが一致しません。事務局に確認してください。")
            return False

    # No new metadata or UUID is created when the user presses retry.
    # Never write this candidate's official CRF to the old production backend.
    # A coordinated GAS + Streamlit release is required (no schema migration).
    try:
        with st.spinner("接続先の台帳バージョンを確認しています…", show_time=True):
            backend = registry_call("backend_info")
    except Exception:
        backend = {}
    # A valid backend version does not prove which spreadsheet is bound.
    # Pin the exact workbook ID in the existing app's registry secrets.
    # If this value or the backend echo is absent, fail closed.
    try:
        expected_sheet_id = str(st.secrets["registry"]["expected_spreadsheet_id"]).strip()
    except Exception:
        expected_sheet_id = ""
    if not expected_sheet_id:
        attempt["status"] = "uncertain"
        st.error("保存先台帳のIDが未設定です。正式保存は実行していません。管理者へ連絡してください。")
        return False
    if (not backend.get("ok")
            or backend.get("backend_version") != "v2.2.10"
            or str(backend.get("spreadsheet_id") or "").strip() != expected_sheet_id):
        attempt["status"] = "uncertain"
        st.error("保存先台帳のバージョンまたはIDが一致しません。正式保存は実行していません。管理者へ連絡してください。")
        return False

    from clinical_validation import validate_payload
    clinical = validate_payload(attempt["payload"])
    if not clinical["ok"]:
        st.error("臨床入力を確認してください：" + " / ".join(clinical["missing"] + clinical["errors"]))
        return False

    attempt["status"] = "saving"
    attempt["saving_started_at"] = time.time()
    try:
        with st.spinner("中央Google Sheetsへ保存しています…", show_time=True):
            result = save_crf_payload(deepcopy(attempt["payload"]))
    except Exception:
        attempt["status"] = "uncertain"
        st.error("保存結果を確認できません。再送する場合は同じ送信IDを使います。事務局に確認してください。")
        return False

    if not isinstance(result, dict):
        result = {}
    if not result.get("ok"):
        attempt["status"] = "uncertain"
        st.error(
            "保存を確認できませんでした：" +
            str(result.get("message") or result.get("error") or "unknown error") +
            "。再送では同じ送信IDを使用します。"
        )
        return False

    # Never show "saved", send mail or delete a draft on an ambiguous or
    # mismatched server response. A retry must retain this frozen UUID.
    frozen = attempt["payload"]
    if (result.get("submission_id") != frozen["submission_id"]
            or result.get("record_key") != frozen["record_key"]
            or result.get("crf_type") != crf_type
            or str(result.get("visit") or "") != str(frozen.get("visit") or "")
            or str(result.get("spreadsheet_id") or "").strip() != expected_sheet_id
            or result.get("audit_verified") is not True
            or type(result.get("record_version")) is not int
            or result["record_version"] < 1
            or type(result.get("existing")) is not bool):
        attempt["status"] = "uncertain"
        st.error("保存応答の症例・送信ID・Version・監査確認・保存先を照合できません。確定扱いせず、同じ送信IDで確認してください。")
        return False

    attempt["record_version"] = str(result["record_version"])
    attempt["status"] = "committed"
    # If this UUID already existed, an earlier request may have sent mail.
    # Never send a duplicate; don't falsely report a mail failure either.
    if result.get("existing"):
        mail_status = "unconfirmed"
        st.info("前回の送信IDによる保存を確認しました。メール通知は重複送信しません。通知状況は事務局で確認できます。")
    else:
        try:
            with st.spinner("保存完了の通知メールを送信しています…", show_time=True):
                mail_ok, _mail_error = send_email(
                    attempt["email_subject"],
                    attempt["email_body"],
                    attempt["payload"]["reporter_email"],
                )
            mail_status = "sent" if mail_ok else "failed"
        except Exception:
            mail_status = "failed"

    try:
        with st.spinner("仮保存データを整理しています…", show_time=True):
            draft_result = delete_crf_draft(registration_id, crf_type, draft_visit)
        draft_delete_failed = not bool(draft_result.get("ok"))
    except Exception:
        draft_delete_failed = True

    st.session_state[f"{page}_sent"] = True
    st.session_state[f"{page}_sent_registration_id"] = registration_id
    st.session_state[f"{page}_sent_version"] = str(result.get("record_version") or "")
    st.session_state[f"{page}_sent_had_warnings"] = attempt["had_warnings"]
    st.session_state[f"{page}_sent_email_failed"] = mail_status == "failed"
    st.session_state[f"{page}_sent_email_unconfirmed"] = mail_status == "unconfirmed"
    st.session_state[f"{page}_sent_draft_delete_failed"] = draft_delete_failed
    if page == "fu":
        st.session_state["fu_sent_visit"] = attempt["visit_display"]

    attempt["status"] = "complete"
    st.success(
        f"保存しました：{display_name}CRF／{registration_id}／"
        f"Version {result.get('record_version') or '未確認'}"
    )
    if mail_status == "failed":
        st.warning("中央台帳は保存済みですが、通知メール送信は失敗しました。再申請はしないでください。")
    if draft_delete_failed:
        st.info("確定データは保存済みですが、仮保存の削除は未確認です。")
    return True

