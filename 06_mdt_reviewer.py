from __future__ import annotations

import hmac
import streamlit as st

from juog_common import registry_call, text

ROLE_LABELS = {
    "radiology": "放射線診断専門医",
    "medical_oncology": "腫瘍内科専門医",
    "urology": "泌尿器科専門医",
}

LAB_DISPLAY = [
    ("WBC", "WBC", "/μL"), ("Hb", "Hb", "g/dL"), ("PLT", "PLT", "×10^4/μL"),
    ("Neutro", "Neutro", "%"), ("Lympho", "Lympho", "%"),
    ("Alb", "Alb", "g/dL"), ("AST", "AST", "U/L"), ("ALT", "ALT", "U/L"),
    ("T_Bil", "T-Bil", "mg/dL"), ("Cre", "Cre", "mg/dL"),
    ("eGFR", "eGFR", "mL/min/1.73m²"), ("BUN", "BUN", "mg/dL"),
    ("Na", "Na", "mEq/L"), ("K", "K", "mEq/L"), ("Cl", "Cl", "mEq/L"),
    ("CRP", "CRP", "mg/dL"), ("Glucose", "血糖", "mg/dL"),
]

def render_screening_labs(data):
    labs = data.get("screening_labs") or {}
    rows = []
    for key, label, unit in LAB_DISPLAY:
        value = labs.get(key)
        rows.append({"項目": label, "値": "NA" if value in (None, "") else value, "単位": unit})
    st.dataframe(rows, use_container_width=True, hide_index=True)

st.markdown(
    """
    <style>
    .block-container {max-width: 1180px !important; padding-top: 1.3rem !important; padding-bottom: 5rem !important;}
    h1 {font-size: 27px !important; text-align:center; color:#0F172A; margin-bottom:30px !important;}
    h2 {font-size:16px !important; color:white !important; background:#334155; padding:10px 18px; border-radius:8px; margin-top:24px !important;}
    label {font-weight:600 !important; color:#334155 !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("JUOG 中央MDT判定者専用")
st.caption("各判定者が独立して入力します。自分の判定を提出する前に、他の判定者の結果は表示されません。")


def authenticate_reviewer():
    current = st.session_state.get("juog_reviewer_role")
    if current in ROLE_LABELS:
        return current

    role = st.selectbox(
        "担当領域",
        ["選択してください", "radiology", "medical_oncology", "urology"],
        format_func=lambda x: ROLE_LABELS.get(x, x),
    )
    password = st.text_input("判定者パスワード", type="password")
    if st.button("ログイン", type="primary", use_container_width=True):
        if role == "選択してください":
            st.error("担当領域を選択してください。")
            return None
        try:
            expected = str(st.secrets["reviewer_passwords"][role])
        except Exception:
            st.error("判定者パスワードが設定されていません。Streamlit Secrets を確認してください。")
            return None
        if password and hmac.compare_digest(password, expected):
            st.session_state.juog_reviewer_role = role
            st.rerun()
        else:
            st.error("パスワードが違います。")
    return None


role = authenticate_reviewer()
if not role:
    st.stop()

c1, c2 = st.columns([4, 1])
c1.info(f"ログイン中：{ROLE_LABELS[role]}")
if c2.button("ログアウト"):
    st.session_state.pop("juog_reviewer_role", None)
    st.rerun()

result = registry_call("list_review_cases", {"reviewer_role": role})
if not result.get("ok"):
    st.error("中央台帳から審査症例を取得できませんでした。")
    st.code(result.get("message") or result.get("error") or "unknown error")
    st.stop()

all_cases = result.get("cases") or []

notice = st.session_state.pop("juog_review_submit_notice", None)
if notice:
    st.success(notice)

if not all_cases:
    st.success("現在、判定対象の症例はありません。")
    st.stop()

show_submitted = st.checkbox(
    "判定済み症例も表示する",
    value=False,
    key=f"show_submitted_{role}",
    help="通常は未判定症例だけを表示します。過去の自分の判定を確認・訂正する場合のみONにしてください。",
)

cases = all_cases if show_submitted else [c for c in all_cases if not c.get("review_submitted")]
if not cases:
    st.success("✅ 現在、未判定の症例はありません。自分に割り当てられた判定はすべて提出済みです。")
    st.caption("過去の判定を確認・訂正する場合は「判定済み症例も表示する」をONにしてください。")
    st.stop()

labels = []
case_by_label = {}
for case in cases:
    mark = "✅ 判定済" if case.get("review_submitted") else "未判定"
    label = (
        f"{case.get('screening_id','')}｜{mark}｜{case.get('facility_name','')}｜"
        f"{case.get('ct','')}/{case.get('cn','')}/{case.get('cm','')}｜Best {case.get('best_effect','')}"
    )
    labels.append(label)
    case_by_label[label] = case

st.header("1. 審査症例")
selected_label = st.selectbox("症例", labels)
case = case_by_label[selected_label]
screening_id = case.get("screening_id", "")
review_round = int(case.get("review_round") or 1)

full_result = registry_call("get_screening_crf", {"screening_id": screening_id})
if not full_result.get("ok"):
    st.error("申請CRF詳細を取得できませんでした。")
    st.code(full_result.get("message") or full_result.get("error") or "unknown error")
    st.stop()
payload = full_result.get("payload") or {}
data = payload.get("data") or {}

st.write(f"**MDT受付番号**：{screening_id}　　**審査ラウンド**：{review_round}")
q1, q2, q3 = st.columns(3)
q1.write(f"**施設**：{case.get('facility_name','')}")
q1.write(f"**施設内識別コード**：{case.get('local_subject_code','')}")
q2.write(f"**診断時TNM**：{case.get('ct','')} / {case.get('cn','')} / {case.get('cm','')}")
q2.write(f"**EVP最良総合効果**：{case.get('best_effect','')}")
if role == "radiology":
    q3.write("**RECIST**：中央で独立判定")
else:
    q3.write(f"**施設RECIST**：{case.get('site_recist','')}")
q3.write(f"**予定術式**：{case.get('planned_surgery','') or '—'}")

st.header("2. 申請情報")
with st.expander("患者背景・EVP・画像情報を確認", expanded=True):
    x1, x2 = st.columns(2)
    with x1:
        st.write(f"同意取得日：{data.get('consent_date','')}")
        st.write(f"生年月：{data.get('birth_year_month','')}")
        st.write(f"同意時年齢：{data.get('age_at_consent','')}歳")
        st.write(f"性別：{data.get('sex','')}")
        st.write(f"ECOG PS：{data.get('ecog_ps','')}")
        st.write(f"原発部位：{data.get('laterality','')} / {data.get('primary_site','')}")
        st.write(f"組織型：{data.get('histology','')}")
        st.write(f"EVP：{data.get('evp_start','')} ～ {data.get('evp_end','')} / {data.get('evp_courses','')}コース")
        st.write(f"Grade 3以上未回復AE：{data.get('g3_unrecovered_ae','')}")
    with x2:
        st.write(f"直近画像日：{data.get('preop_imaging_date','')}")
        if role == "radiology":
            st.caption("施設RECIST・施設側の浸潤判定は、中央放射線診断の独立性を保つため判定提出前は表示しません。")
        else:
            st.write(f"施設RECIST：{data.get('site_recist','')}")
            st.write(f"他臓器浸潤：{data.get('unresectable_organ','')}")
            st.write(f"大血管浸潤：{data.get('unresectable_vessel','')}")
        st.write(f"新病変：{data.get('new_lesion','')}")
        st.write(f"非標的病変増悪：{data.get('nontarget_pd','')}")
        st.write(f"cM1根拠：{data.get('cm1_basis','') or 'N/A'}")
        st.write(f"cNED確認日：{data.get('cned_date','') or 'N/A'}")
        st.write(f"予定術式・予定日：{data.get('planned_surgery','')} / {data.get('planned_surgery_date','')}")
    lesions = data.get("target_lesions") or []
    if lesions:
        st.write("**標的病変**")
        st.dataframe(lesions, use_container_width=True, hide_index=True)

if role == "medical_oncology":
    st.subheader("腫瘍内科評価用の提出情報")
    st.caption("以下は申請施設から提出された情報です。本中央判定は提出情報に基づく評価であり、判定者が患者を直接診察したことを意味しません。")
    m1, m2 = st.columns(2)
    with m1:
        st.write(f"**申請ECOG PS**：{data.get('ecog_ps','')} ")
        st.write(f"**EVP関連Grade 3以上未回復AE**：{data.get('g3_unrecovered_ae','')}")
        st.write(f"**Pembro中止**：{data.get('pembro_stop','')}")
        if data.get('pembro_stop_detail'):
            st.write(f"Pembro中止詳細：{data.get('pembro_stop_detail')}")
        important_ae = data.get('important_ae_irAE')
        if important_ae:
            st.write("**重要AE / irAE（既往・回復済みを含む）**：" + "、".join(important_ae))
            if data.get('important_ae_irAE_detail'):
                st.write(f"詳細：{data.get('important_ae_irAE_detail')}")
        else:
            st.caption("重要AE / irAE詳細：この申請では詳細項目未収集（既存のAE・Pembro中止情報等で評価）")
    with m2:
        st.write(f"**現在の合併症**：{data.get('comorbidity','')}")
        st.write(f"**現在の併用薬**：{data.get('concomitant_meds','')}")
        st.write(f"**現在の併用治療**：{data.get('concomitant_treatment','')}")
        vitals = data.get('screening_vitals') or {}
        st.write(
            f"**スクリーニングバイタル**：BP {vitals.get('sbp','')}/{vitals.get('dbp','')} mmHg、"
            f"HR {vitals.get('pulse','')}/min、T {vitals.get('temperature','')}℃"
        )
    st.write("**スクリーニング採血データ**")
    render_screening_labs(data)
    st.caption("異常値が疑わしい場合や、irAE（例：肺障害、心筋炎、1型/劇症1型糖尿病、内分泌障害等）の回復状況が不十分な場合は『追加情報/回復待ち』として事務局へ確認できます。")
elif role == "urology":
    st.caption("泌尿器科中央判定は、申請施設から提出された臨床情報・画像情報に基づく評価であり、判定者による患者の直接診察を意味しません。")

# An unreviewed case is already identified by list_review_cases, so avoid an
# unnecessary extra round-trip to Google Apps Script. Fetch prior details only
# when this reviewer has actually submitted a review for the current round.
prior = None
if case.get("review_submitted"):
    own_result = registry_call(
        "get_own_review",
        {"screening_id": screening_id, "review_round": review_round, "reviewer_role": role},
    )
    if not own_result.get("ok"):
        st.error("自分の判定履歴を取得できませんでした。")
        st.code(own_result.get("message") or own_result.get("error") or "unknown error")
        st.stop()
    prior = own_result.get("review")

correction_key = f"juog_correction_mode_{role}_{screening_id}_{review_round}"
correction_mode = bool(st.session_state.get(correction_key, False))

if prior:
    decision_label = {
        "ELIGIBLE": "適格",
        "INELIGIBLE": "不適格",
        "HOLD": "保留",
    }.get(str(prior.get("decision", "")).upper(), str(prior.get("decision", "")))

    st.success("✅ この症例の中央MDT判定は提出完了しています。通常は追加操作は不要です。")
    s1, s2, s3 = st.columns(3)
    s1.metric("提出済み判定", decision_label or "—")
    s2.metric("Version", str(prior.get("review_version", "") or "—"))
    s3.metric("審査ラウンド", str(review_round))
    st.caption(
        f"判定者：{prior.get('reviewer_name','')}　／　提出日時：{prior.get('submitted_at','')}"
    )
    if prior.get("comment"):
        st.write(f"**前回コメント**：{prior.get('comment')}")

    if not correction_mode:
        if st.button("提出済み判定を訂正する", type="secondary", use_container_width=True):
            st.session_state[correction_key] = True
            st.rerun()
        st.caption("訂正が不要であれば、この症例での操作は終了です。")
        st.stop()
    else:
        st.warning("⚠️ 訂正再提出モードです。訂正理由を入力し、全項目を再確認して提出してください。")
        if st.button("訂正をやめる", use_container_width=True):
            st.session_state[correction_key] = False
            st.rerun()

st.header("3. 独立判定")
with st.form(f"review_form_{role}_{screening_id}_{review_round}"):
    reviewer_name = st.text_input("判定者氏名*")

    role_payload = {}
    if role == "radiology":
        central_recist = st.selectbox(
            "中央RECIST v1.1総合判定*",
            ["選択してください", "CR", "PR", "SD", "PD", "NE"],
            help="施設判定とは別に、中央放射線診断医としてRECIST v1.1に基づき判定してください。この中央判定を適格性確認時の正式RECISTとして扱います。",
        )
        organ_invasion = st.selectbox("他臓器直接浸潤の画像評価*", ["選択してください", "切除不能/危険な浸潤なし", "切除不能/危険な浸潤あり", "判定困難"])
        vessel_invasion = st.selectbox("大血管浸潤の画像評価*", ["選択してください", "切除不能/危険な浸潤なし", "切除不能/危険な浸潤あり", "判定困難"])
        cm1_status = st.selectbox(
            "診断時cM1例の活動性遠隔病変*",
            ["選択してください", "非cM1のため該当なし", "活動性病変消失/cNED", "活動性病変あり", "判定困難"],
        )
        role_payload = {
            "central_recist": central_recist,
            "organ_invasion": organ_invasion,
            "vessel_invasion": vessel_invasion,
            "cm1_status": cm1_status,
        }
    elif role == "medical_oncology":
        g3_ae_recovered = st.selectbox(
            "申請情報上、EVP関連Grade 3以上AEの未回復がないこと*",
            ["選択してください", "確認できる", "未回復AEあり", "追加情報が必要"],
            help="申請施設から提出されたAE情報を確認します。判定者による直接診察を意味しません。",
        )
        ecog_0_1 = st.selectbox(
            "申請情報上、ECOG PS 0–1であること*",
            ["選択してください", "確認できる", "ECOG PS 2以上と報告", "追加情報が必要"],
            help="申請施設が報告したECOG PSを確認します。中央判定者が患者を直接診察して採点する項目ではありません。",
        )
        medical_safety = st.selectbox(
            "提出された臨床情報・検査値を踏まえた内科的な手術移行安全性*",
            ["選択してください", "手術移行可能", "手術移行不適", "追加情報/回復待ち"],
            help="採血、バイタル、併存疾患、EVP関連AE/irAEの回復状況等を総合して判定してください。",
        )
        role_payload = {
            "g3_ae_recovered": g3_ae_recovered,
            "ecog_0_1": ecog_0_1,
            "medical_safety": medical_safety,
        }
    else:
        technically_resectable = st.selectbox("申請情報・画像に基づく技術的切除可能性*", ["選択してください", "切除可能", "切除不能/危険", "追加情報が必要"])
        surgery_appropriate = st.selectbox("提出情報に基づくConsolidative surgeryの外科的妥当性*", ["選択してください", "適応あり", "適応なし", "保留"])
        role_payload = {
            "technically_resectable": technically_resectable,
            "surgery_appropriate": surgery_appropriate,
        }

    decision_jp = st.radio("担当領域としての判定*", ["適格", "不適格", "保留"], index=None, horizontal=True)
    comment = st.text_area("コメント" + ("*" if decision_jp in {"不適格", "保留"} else "（任意）"))
    is_correction = bool(prior) and correction_mode
    correction_reason = st.text_input("訂正理由*") if is_correction else ""
    confirm = st.checkbox("申請資料を確認し、自分の担当領域として独立して判定しました。")
    submit_label = "訂正版を提出" if is_correction else "判定を提出"
    submitted = st.form_submit_button(submit_label, type="primary", use_container_width=True)

if submitted:
    errors = []
    if not text(reviewer_name):
        errors.append("判定者氏名を入力してください")
    if decision_jp is None:
        errors.append("判定を選択してください")
    if decision_jp in {"不適格", "保留"} and not text(comment):
        errors.append("不適格・保留ではコメントが必要です")
    if not confirm:
        errors.append("独立判定の確認チェックが必要です")
    if prior and not is_correction:
        errors.append("このラウンドはすでに提出済みです。変更する場合は『訂正再提出』を選択してください")
    if is_correction and not text(correction_reason):
        errors.append("訂正理由を入力してください")
    for k, v in role_payload.items():
        if v == "選択してください":
            errors.append("担当領域の必須判定項目をすべて選択してください")
            break

    if errors:
        st.error("\n".join(f"・{x}" for x in errors))
    else:
        decision_code = {"適格": "ELIGIBLE", "不適格": "INELIGIBLE", "保留": "HOLD"}[decision_jp]
        request = {
            "screening_id": screening_id,
            "review_round": review_round,
            "reviewer_role": role,
            "reviewer_name": text(reviewer_name),
            "decision": decision_code,
            "comment": text(comment),
            "is_correction": bool(is_correction),
            "correction_reason": text(correction_reason),
            **role_payload,
        }
        result = registry_call("submit_mdt_review", request)
        if not result.get("ok"):
            st.error("判定を保存できませんでした：" + (result.get("message") or result.get("error") or "unknown error"))
        else:
            if is_correction:
                st.session_state[correction_key] = False
            st.session_state["juog_review_submit_notice"] = (
                f"✅ {screening_id} の判定を提出しました（version {result.get('review_version')}）。"
            )
            st.rerun()
