from __future__ import annotations

import hmac
import streamlit as st

from juog_common import date_str, registry_call, send_email, text, today_jst

st.markdown(
    """
    <style>
    .block-container {max-width: 1180px !important; padding-top: 1.3rem !important; padding-bottom: 5rem !important;}
    h1 {font-size: 27px !important; text-align:center; color:#0F172A; margin-bottom:30px !important;}
    h2 {font-size:16px !important; color:white !important; background:#7C2D12; padding:10px 18px; border-radius:8px; margin-top:24px !important;}
    label {font-weight:600 !important; color:#334155 !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("JUOG 事務局専用：中央MDT判定・正式登録")
st.caption("施設から提出された中央MDT審査申請の判定を記録し、適格例のみJUOG登録番号を発行します。")


def admin_authenticated() -> bool:
    if st.session_state.get("juog_admin_authenticated"):
        return True
    try:
        expected = str(st.secrets["admin"]["password"])
    except Exception:
        st.error("事務局認証が設定されていません。Streamlit Secrets に [admin] password を設定してください。")
        return False

    with st.form("admin_login"):
        password = st.text_input("事務局パスワード", type="password")
        submitted = st.form_submit_button("ログイン", type="primary", use_container_width=True)
    if submitted:
        if password and hmac.compare_digest(password, expected):
            st.session_state.juog_admin_authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います。")
    return False


if not admin_authenticated():
    st.stop()

c_logout, _ = st.columns([1, 5])
if c_logout.button("ログアウト"):
    st.session_state.juog_admin_authenticated = False
    st.rerun()

stats = registry_call("stats")
if not stats.get("ok"):
    st.error("中央台帳に接続できません。Apps Script / registry Secrets を確認してください。")
    st.code(stats.get("message") or stats.get("error") or "unknown error")
    st.stop()

m1, m2, m3, m4 = st.columns(4)
m1.metric("正式登録", f"{stats.get('total', 0)} / 42")
m2.metric("cN1", f"{stats.get('cN1', 0)} / 20")
m3.metric("SD", f"{stats.get('SD', 0)} / 12")
scr_stats = stats.get("screenings") or {}
m4.metric("MDT未判定/保留", int(scr_stats.get("PENDING", 0)) + int(scr_stats.get("HOLD", 0)))

st.header("1. 審査対象の選択")
status_label = st.radio(
    "表示する症例",
    ["未判定・保留", "未判定のみ", "保留のみ", "不適格", "登録済み", "すべて"],
    horizontal=True,
)
status_map = {
    "未判定・保留": "PENDING,HOLD",
    "未判定のみ": "PENDING",
    "保留のみ": "HOLD",
    "不適格": "INELIGIBLE",
    "登録済み": "REGISTERED",
    "すべて": "PENDING,HOLD,INELIGIBLE,REGISTERED",
}
list_result = registry_call("list_screenings", {"statuses": status_map[status_label]})
if not list_result.get("ok"):
    st.error("審査対象一覧を取得できませんでした。")
    st.code(list_result.get("message") or list_result.get("error") or "unknown error")
    st.stop()

rows = list_result.get("screenings") or []
if not rows:
    st.info("該当する中央MDT審査申請はありません。")
    st.stop()

status_jp = {"PENDING": "未判定", "HOLD": "保留", "INELIGIBLE": "不適格", "REGISTERED": "登録済み"}
options = []
row_by_label = {}
for r in rows:
    label = (
        f"{r.get('screening_id','')}｜{status_jp.get(r.get('status',''), r.get('status',''))}｜"
        f"{r.get('facility_name','')}｜{r.get('local_subject_code','')}｜"
        f"{r.get('ct','')}/{r.get('cn','')}/{r.get('cm','')}｜Best {r.get('best_effect','')}"
    )
    options.append(label)
    row_by_label[label] = r

selected_label = st.selectbox("MDT審査受付番号 / 症例", options)
selected = row_by_label[selected_label]
screening_id = selected.get("screening_id", "")

detail_result = registry_call("get_screening", {"screening_id": screening_id})
if not detail_result.get("ok"):
    st.error("症例情報を取得できませんでした。")
    st.code(detail_result.get("message") or detail_result.get("error") or "unknown error")
    st.stop()
case = detail_result.get("screening") or {}

st.header("2. 申請情報の確認")
a1, a2, a3 = st.columns(3)
a1.write(f"**MDT受付番号**  {case.get('screening_id','')}")
a1.write(f"**施設**  {case.get('facility_name','')}")
a1.write(f"**施設内識別コード**  {case.get('local_subject_code','')}")
a2.write(f"**診断時TNM**  {case.get('ct','')} / {case.get('cn','')} / {case.get('cm','')}")
a2.write(f"**EVP最良総合効果**  {case.get('best_effect','')}")
a2.write(f"**施設判定RECIST**  {case.get('site_recist','')}")
a3.write(f"**予定術式**  {case.get('planned_surgery','') or '—'}")
a3.write(f"**手術予定日**  {case.get('planned_surgery_date','') or '—'}")
a3.write(f"**現在の状態**  {status_jp.get(case.get('status',''), case.get('status',''))}")

if case.get("status") in {"HOLD", "INELIGIBLE", "REGISTERED"}:
    st.info(
        f"前回MDT：{case.get('mdt_date','') or '—'} / 中央RECIST {case.get('central_recist','') or '—'} / "
        f"判定 {case.get('mdt_decision','') or '—'}"
        + (f" / 理由：{case.get('mdt_reason','')}" if case.get("mdt_reason") else "")
        + (f" / 登録番号：{case.get('registration_id','')}" if case.get("registration_id") else "")
    )

st.warning("中央MDTの実際の審査は、施設から提出されたCRF・画像等の匿名化資料を確認した上で行ってください。この画面は判定記録と正式登録の管理用です。")

if case.get("status") == "REGISTERED":
    st.success(f"正式登録済み：{case.get('registration_id','')}")
    st.stop()
if case.get("status") == "INELIGIBLE":
    st.error("この審査受付は不適格確定済みです。再審査が必要な場合は、台帳を直接変更せず研究事務局で手順を確認してください。")
    st.stop()

st.header("3. 中央MDT判定")
with st.form(f"mdt_form_{screening_id}"):
    b1, b2 = st.columns(2)
    with b1:
        mdt_date = st.date_input("中央MDT判定日*", value=today_jst(), max_value=today_jst())
        central_recist = st.selectbox("中央RECIST v1.1総合判定*", ["選択してください", "CR", "PR", "SD", "PD", "NE"])
    with b2:
        decision_jp = st.radio("本試験における手術適応判定*", ["適格（手術適応あり）", "不適格", "保留"], index=None)
        admin_user = st.text_input("判定記録者（事務局）*")
    reason = st.text_area("不適格・保留の理由*" if decision_jp in {"不適格", "保留"} else "備考（任意）")

    is_eligible = decision_jp == "適格（手術適応あり）"
    confirm = st.checkbox(
        "中央MDTで『手術適応あり』と判定され、正式登録してJUOG登録番号を発行することを確認しました。",
        disabled=not is_eligible,
    )
    submitted = st.form_submit_button(
        "MDT判定を確定" if not is_eligible else "正式登録・JUOG登録番号を発行",
        type="primary",
        use_container_width=True,
    )

if submitted:
    errors = []
    if central_recist == "選択してください":
        errors.append("中央RECISTを選択してください")
    if decision_jp is None:
        errors.append("MDT判定を選択してください")
    if not text(admin_user):
        errors.append("判定記録者を入力してください")
    if decision_jp in {"不適格", "保留"} and not text(reason):
        errors.append("不適格・保留の理由を入力してください")
    if is_eligible and central_recist not in {"CR", "PR", "SD"}:
        errors.append("適格として正式登録する場合、中央RECISTはCR/PR/SDである必要があります")
    if is_eligible and not confirm:
        errors.append("正式登録の確認チェックが必要です")

    if errors:
        st.error("\n".join([f"・{x}" for x in errors]))
    else:
        decision_code = {
            "適格（手術適応あり）": "ELIGIBLE",
            "不適格": "INELIGIBLE",
            "保留": "HOLD",
        }[decision_jp]
        result = registry_call(
            "finalize_mdt",
            {
                "screening_id": screening_id,
                "mdt_date": date_str(mdt_date),
                "central_recist": central_recist,
                "decision": decision_code,
                "reason": text(reason),
                "admin_user": text(admin_user),
            },
        )
        if not result.get("ok"):
            st.error("MDT判定を確定できませんでした：" + (result.get("message") or result.get("error") or "unknown error"))
        else:
            reporter_email = case.get("reporter_email", "")
            if decision_code == "ELIGIBLE":
                registration_id = result.get("registration_id", "")
                body = f"""【JUOG UTUC_Consolidative 中央MDT結果】
MDT審査受付番号: {screening_id}
施設: {case.get('facility_name','')}
施設内研究対象者識別コード: {case.get('local_subject_code','')}
中央MDT判定日: {date_str(mdt_date)}
中央RECIST: {central_recist}
判定: 手術適応あり（適格）

正式登録番号: {registration_id}
登録日: {result.get('registration_date','')}

以後の周術期・90日・定期経過CRFでは、このJUOG登録番号を使用してください。
"""
                sent, mail_err = send_email(
                    f"【JUOG 正式登録】【{registration_id}】【{case.get('facility_name','')}】",
                    body,
                    reporter_email,
                )
                st.success(f"正式登録しました：{registration_id}")
                if result.get("counts_after"):
                    ca = result["counts_after"]
                    st.info(f"登録後集積：全体 {ca.get('total')}例 / cN1 {ca.get('cN1')}例 / SD {ca.get('SD')}例")
                if not sent:
                    st.warning("正式登録は完了していますが、結果通知メールの送信に失敗しました。JUOG番号は再発行しないでください。")
                    st.code(mail_err or "mail error")
            else:
                decision_text = "不適格" if decision_code == "INELIGIBLE" else "保留"
                body = f"""【JUOG UTUC_Consolidative 中央MDT結果】
MDT審査受付番号: {screening_id}
施設: {case.get('facility_name','')}
施設内研究対象者識別コード: {case.get('local_subject_code','')}
中央MDT判定日: {date_str(mdt_date)}
中央RECIST: {central_recist}
判定: {decision_text}
理由: {text(reason)}

JUOG正式登録番号は発行されていません。
"""
                sent, mail_err = send_email(
                    f"【JUOG MDT結果】【{screening_id}】【{decision_text}】",
                    body,
                    reporter_email,
                )
                if decision_code == "INELIGIBLE":
                    st.success("不適格として判定を確定しました。正式登録番号は発行されていません。")
                else:
                    st.success("保留として判定を記録しました。追加情報提出後に再審査できます。")
                if not sent:
                    st.warning("判定記録は完了していますが、結果通知メールの送信に失敗しました。")
                    st.code(mail_err or "mail error")
            st.session_state["last_admin_screening"] = screening_id
