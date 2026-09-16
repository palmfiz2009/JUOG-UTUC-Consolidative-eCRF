from __future__ import annotations

from datetime import date

import streamlit as st

from juog_common import (
    CD_OPTIONS,
    POSTOP_TREATMENT_OPTIONS,
    add_months,
    date_str,
    json_block,
    make_submission_metadata,
    render_lab_panel,
    render_submission_kind,
    render_cytology,
    registry_call,
    save_crf_payload,
    send_email,
    text,
    today_jst,
    unique_messages,
    valid_email,
    valid_registration_id,
    validate_lab_panel,
    validate_registry_id,
    validate_cytology,
)

st.markdown("""
<style>
.block-container {max-width:1180px!important;padding-top:1.3rem!important;padding-bottom:5rem!important;}
h1 {font-size:27px!important;text-align:center;color:#0F172A;margin-bottom:30px!important;}
.juog-header {background:#1E3A8A;color:white;padding:10px 18px;border-radius:8px;font-weight:700;margin-top:24px;margin-bottom:14px;}
label {font-weight:600!important;color:#334155!important;}
</style>
""", unsafe_allow_html=True)

def parse_iso_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def fetch_30d_linkage(registration_id: str):
    return registry_call(
        "get_crf_linkage",
        {"registration_id": registration_id.strip().upper(), "source_crf_type": "perioperative_30d"},
        timeout=20,
    )


st.title("JUOG UTUC_Consolidative 定期経過報告CRF")
st.caption("術後3か月毎（6〜24か月）の経過報告。基準日は周術期・30日CRFに記録された実手術日（未施行例は予定日）を使用します。尿一般検査は収集せず、尿細胞診を記録します。")

if "fu_sent" not in st.session_state:
    st.session_state.fu_sent = False
if "fu_linkage" not in st.session_state:
    st.session_state.fu_linkage = None
if "fu_linkage_message" not in st.session_state:
    st.session_state.fu_linkage_message = ""

if st.session_state.fu_sent:
    sent_id = st.session_state.get("fu_sent_registration_id", "")
    sent_visit = st.session_state.get("fu_sent_visit", "")
    sent_version = st.session_state.get("fu_sent_version", "")
    st.success("送信が完了しました。")
    if sent_id:
        st.write(f"**JUOG登録番号：{sent_id}**")
    if sent_visit:
        st.write(f"**報告時期：{sent_visit}**")
    if sent_version:
        st.caption(f"定期経過CRFを保存しました（version {sent_version}）。")
    else:
        st.caption("定期経過CRFを保存しました。")
    if st.session_state.get("fu_sent_had_warnings"):
        st.info("確認事項も中央データに保存されています。")
    if st.session_state.get("fu_sent_email_failed"):
        st.warning("中央Google Sheetへの保存は完了していますが、通知メール送信に失敗しました。再入力はせず事務局へ連絡してください。")
    st.caption("訂正する場合はページを再読み込みし、『訂正報告』を選択して送信してください。")
    st.stop()

L = False

st.markdown('<div class="juog-header">1. 基本情報・報告時期</div>', unsafe_allow_html=True)
top1, top2 = st.columns(2)
with top1:
    registration_id = st.text_input(
        "JUOG登録番号*",
        placeholder="JUOG-001",
        key="fu_registration_id",
        disabled=L,
    ).strip().upper()
    reporter_email = st.text_input("担当者メールアドレス*", key="fu_reporter_email", disabled=L)
with top2:
    submission_kind, correction_reason = render_submission_kind("fu", disabled=L)

fetch_disabled = not valid_registration_id(registration_id)
if st.button("既存情報を取得", use_container_width=True, disabled=fetch_disabled or L):
    result = fetch_30d_linkage(registration_id)
    if result.get("ok") and result.get("source_found"):
        st.session_state.fu_linkage = result
        st.session_state.fu_linkage_message = ""
        st.rerun()
    else:
        st.session_state.fu_linkage = None
        st.session_state.fu_linkage_message = (
            result.get("message")
            or result.get("error")
            or "周術期・30日CRFから手術情報を取得できませんでした。"
        )
        st.rerun()

linkage = st.session_state.get("fu_linkage")
if linkage and linkage.get("registration_id") != registration_id:
    linkage = None
    st.warning("JUOG登録番号が変更されています。『既存情報を取得』をもう一度押してください。")

if not linkage:
    msg = st.session_state.get("fu_linkage_message")
    if msg:
        st.error(msg)
        st.caption("Follow-up CRFでは手術日を手入力せず、周術期・30日CRFの確定情報を基準にします。30日CRFを確認・訂正後、再度取得してください。")
    else:
        st.info("JUOG登録番号を入力し、『既存情報を取得』を押してください。")
        if registration_id and not valid_registration_id(registration_id):
            st.warning("JUOG登録番号は JUOG-001 のように3桁で入力してください。")
    st.stop()

facility_code = str(linkage.get("facility_code") or "")
facility_name = str(linkage.get("facility_name") or "")
surgery_performed = str(linkage.get("surgery_performed") or "")
reference_date = parse_iso_date(linkage.get("reference_date"))
source_30d_record_version = int(linkage.get("record_version") or 0)
source_30d_submission_id = str(linkage.get("submission_id") or "")

st.success("周術期・30日CRFの最新情報を取得しました。")
c1, c2, c3, c4 = st.columns(4)
c1.text_input("JUOG登録番号", value=registration_id, disabled=True)
c2.text_input("施設", value=facility_name, disabled=True)
c3.text_input("Consolidative surgery", value=surgery_performed, disabled=True)
c4.text_input(
    "実手術日" if surgery_performed == "実施した" else "手術予定日",
    value=date_str(reference_date),
    disabled=True,
)
st.caption(f"参照元：周術期・30日CRF version {source_30d_record_version}")

if surgery_performed == "実施した":
    st.caption("6〜24か月の評価時期は、30日CRFに記録された実手術日を基準に計算します。")
else:
    st.warning("Consolidative surgery未施行例です。30日CRFに記録された予定日を基準日として表示します。")

visit_month = st.selectbox(
    "今回の報告時期*",
    ["選択してください", "6ヶ月", "9ヶ月", "12ヶ月", "15ヶ月", "18ヶ月", "21ヶ月", "24ヶ月（終了）"],
    disabled=L,
)
visit_date = st.date_input("今回の評価日*", value=None, disabled=L)
timing_note = ""
if reference_date and visit_month != "選択してください":
    month_no = int(''.join(x for x in visit_month if x.isdigit()))
    target_date = add_months(reference_date, month_no)
    base_label = "実手術日" if surgery_performed == "実施した" else "手術予定日"
    st.info(f"目安の評価日：{target_date:%Y/%m/%d}（{base_label} {reference_date:%Y/%m/%d} を基準）")
    if visit_date:
        delta = abs((visit_date - target_date).days)
        if delta > 30:
            st.warning(f"目安日から{delta}日ずれています。臨床上の事情があればそのまま入力できます。")
            timing_note = st.text_area("評価時期がずれた理由（任意だが記録推奨）", disabled=L)

# ---------------- surveillance ----------------
st.markdown('<div class="juog-header">2. 定期検査（尿細胞診・画像・膀胱鏡）</div>', unsafe_allow_html=True)
cytology = render_cytology("fu", required=True, disabled=L)

s1, s2 = st.columns(2)
with s1:
    imaging_status = st.radio("画像検査（CT/MRI等）の実施*", ["実施", "未実施"], index=None, horizontal=True, disabled=L)
    imaging_date = None
    imaging_not_done_reason = ""
    recist_status = "NE（未実施）"
    progression_date = None
    progression_sites = []
    progression_detail = ""
    if imaging_status == "実施":
        imaging_date = st.date_input("画像検査日*", value=None, disabled=L)
        recist_status = st.selectbox("RECIST v1.1進行状況*", ["選択してください", "PDなし", "今回PDあり", "既報PD（今回新規PDなし）", "NE（評価不能）"], disabled=L)
        if recist_status == "今回PDあり":
            progression_date = st.date_input("今回のPD確認日*", value=None, disabled=L)
            progression_sites = st.multiselect("進行/新病変部位*", ["手術局所", "リンパ節", "肺", "肝", "骨", "その他"], disabled=L)
            progression_detail = st.text_area("進行所見詳細*", disabled=L)
    elif imaging_status == "未実施":
        imaging_not_done_reason = st.text_area("画像検査未実施理由*", placeholder="例：死亡、全身状態不良、患者都合等", disabled=L)
with s2:
    cystoscopy_status = st.radio("膀胱鏡の実施*", ["実施", "未実施"], index=None, horizontal=True, disabled=L)
    cystoscopy_date = None
    cystoscopy_result = "未実施"
    cystoscopy_detail = ""
    cystoscopy_not_done_reason = ""
    if cystoscopy_status == "実施":
        cystoscopy_date = st.date_input("膀胱鏡日*", value=None, disabled=L)
        cystoscopy_result = st.selectbox("膀胱鏡所見*", ["選択してください", "腫瘍なし", "腫瘍あり", "評価不能"], disabled=L)
        cystoscopy_detail = st.text_area("膀胱鏡所見詳細*" if cystoscopy_result in ["腫瘍あり", "評価不能"] else "膀胱鏡所見詳細", disabled=L)
    elif cystoscopy_status == "未実施":
        cystoscopy_not_done_reason = st.text_area("膀胱鏡未実施理由*", placeholder="例：死亡、全身状態不良、患者拒否等", disabled=L)

# ---------------- labs ----------------
st.markdown('<div class="juog-header">3. 採血検査</div>', unsafe_allow_html=True)
is_final = visit_month == "24ヶ月（終了）"
if is_final:
    st.info("2年終了時の採血は計画書上必須です。")
    show_labs = True
else:
    show_labs = st.checkbox("今回の採血結果を入力する（3か月毎は必要に応じて）", disabled=L)

labs_raw = {}
if show_labs:
    labs_raw = render_lab_panel("fu_lab", required=is_final, disabled=L, columns=3)
else:
    st.caption("今回採血なし。")

required_test_omission_reason = ""
cytology_not_done_now = cytology == "未実施"
lab_na_now = show_labs and any(str(v).strip().upper() in {"NA", "N/A", "未実施", "欠測"} for v in labs_raw.values())
if cytology_not_done_now or (is_final and lab_na_now):
    required_test_omission_reason = st.text_area("必須検査の欠測/未実施理由*", placeholder="未実施またはNAとした項目の理由を記載してください", disabled=L)

# ---------------- intraluminal recurrence ----------------
st.markdown('<div class="juog-header">4. 尿路内再発</div>', unsafe_allow_html=True)
intra_status = st.selectbox("尿路内再発状況*", ["選択してください", "なし", "今回新規あり", "既報あり（今回新規なし）"], disabled=L)
intra_date = None
intra_sites = []
intra_site_other = ""
intra_tx = []
intra_tx_other = ""
intra_tx_status = None
intra_procedure_date = None
intra_instill_start = None
intra_instill_end = None
intra_instill_ongoing = False
intra_other_date = None
intra_path = ""
if intra_status == "今回新規あり":
    i1, i2 = st.columns(2)
    with i1:
        intra_date = st.date_input("再発診断日*", value=None, disabled=L)
        intra_sites = st.multiselect("再発部位*", ["膀胱", "対側腎盂", "対側尿管", "同側残存尿管", "その他"], disabled=L)
        if "その他" in intra_sites:
            intra_site_other = st.text_input("部位その他詳細*", disabled=L)
    with i2:
        intra_tx = st.multiselect("対応/治療*", ["経過観察", "TURBT", "BCG注入療法", "抗がん剤注入療法", "上部尿路内視鏡的治療", "手術（腎尿管全摘等）", "その他"], disabled=L)
        if "その他" in intra_tx:
            intra_tx_other = st.text_input("治療その他詳細*", disabled=L)
        if intra_tx and "経過観察" not in intra_tx:
            intra_tx_status = st.radio(
                "尿路内再発治療の状況*", ["実施済み・継続中", "今後の予定"],
                index=None, horizontal=True, disabled=L,
            )

    if intra_tx_status == "実施済み・継続中":
        if any(x in intra_tx for x in ["TURBT", "上部尿路内視鏡的治療", "手術（腎尿管全摘等）"]):
            intra_procedure_date = st.date_input("処置/手術日*", value=None, disabled=L)
            intra_path = st.text_area("組織型・Grade・pTNM等*", disabled=L)
        if any(x in intra_tx for x in ["BCG注入療法", "抗がん剤注入療法"]):
            q1, q2 = st.columns(2)
            intra_instill_start = q1.date_input("尿路内注入療法 開始日*", value=None, disabled=L)
            intra_instill_ongoing = q2.checkbox("尿路内注入療法 継続中", disabled=L)
            if not intra_instill_ongoing:
                intra_instill_end = q2.date_input("尿路内注入療法 終了日*", value=None, disabled=L)
        if "その他" in intra_tx:
            intra_other_date = st.date_input("その他治療 実施/開始日", value=None, disabled=L)

# ---------------- systemic/local treatment after recurrence ----------------
st.markdown('<div class="juog-header">5. 現在の治療・再発治療</div>', unsafe_allow_html=True)
treatment_options = POSTOP_TREATMENT_OPTIONS + ["上記尿路内再発に対する治療を継続中", "転移巣切除", "緩和ケア"]
# De-duplicate while preserving order.
treatment_options = list(dict.fromkeys(treatment_options))
current_treatment = st.selectbox("現在の主な治療状況*", treatment_options, disabled=L)
current_treatment_detail = ""
treatment_start = treatment_end = None
treatment_ongoing = False
if current_treatment not in ["選択してください", "無治療（経過観察）", "上記尿路内再発に対する治療を継続中", "緩和ケア"]:
    if current_treatment in ["治験（TROP2標的ADC、その他）", "その他"]:
        current_treatment_detail = st.text_area("治療詳細*", disabled=L)
    t1, t2 = st.columns(2)
    treatment_start = t1.date_input("治療開始日*", value=None, disabled=L)
    treatment_ongoing = t2.checkbox("継続中", disabled=L)
    if not treatment_ongoing:
        treatment_end = t2.date_input("治療終了日（継続予定なら空欄可）", value=None, disabled=L)
elif current_treatment in ["上記尿路内再発に対する治療を継続中", "緩和ケア"]:
    current_treatment_detail = st.text_area("治療内容/状況の詳細", disabled=L)

# ---------------- AE / complications ----------------
st.markdown('<div class="juog-header">6. 有害事象・遅発性合併症</div>', unsafe_allow_html=True)
has_event = st.checkbox("今回の期間に特記すべき薬剤関連AEまたは遅発性合併症がある", disabled=L)
cd_grade = "N/A"
ae_detail = ""
if has_event:
    a1, a2 = st.columns(2)
    cd_grade = a1.selectbox("Clavien-Dindo分類（手術関連の場合）", ["N/A"] + [x for x in CD_OPTIONS if x != "選択してください"], disabled=L)
    ae_detail = a2.text_area("事象詳細（発現日・CTCAE Grade・処置・転帰・手術関連性等）*", disabled=L)

# ---------------- OS ----------------
st.markdown('<div class="juog-header">7. 生存状況</div>', unsafe_allow_html=True)
o1, o2 = st.columns(2)
with o1:
    vital_status = st.radio("生存状況*", ["生存", "死亡"], index=None, horizontal=True, disabled=L)
with o2:
    last_alive_date = death_date = None
    death_cause = ""
    if vital_status == "生存":
        last_alive_date = st.date_input("最終生存確認日*", value=None, disabled=L)
    elif vital_status == "死亡":
        death_date = st.date_input("死亡日*", value=None, disabled=L)
        death_cause = st.selectbox("死因*", ["選択してください", "癌死 (原疾患による)", "治療関連死", "他病死", "不明"], disabled=L)

# ---------------- validation ----------------
def validate_all():
    missing, errors, warnings = [], [], []
    if not facility_code or not facility_name:
        errors.append("30日CRFから施設情報を取得できていません")
    if source_30d_record_version <= 0 or not source_30d_submission_id:
        errors.append("30日CRFとの連携情報が不完全です。既存情報を再取得してください")
    if facility_name == "選択してください": missing.append("施設名")
    if not valid_registration_id(registration_id): errors.append("JUOG登録番号の形式が不正です（例：JUOG-001）")
    if not valid_email(reporter_email): errors.append("担当者メールアドレスが不正です")
    if surgery_performed is None: missing.append("手術実施有無")
    if reference_date is None: missing.append("手術日/予定日")
    if submission_kind == "訂正報告" and not text(correction_reason): missing.append("訂正理由")
    if visit_month == "選択してください": missing.append("報告時期")
    if visit_date is None: missing.append("評価日")
    if visit_date and visit_date > today_jst(): errors.append("評価日が未来日です")
    if reference_date and visit_date and visit_date < reference_date: errors.append("評価日が手術/予定日より前です")

    missing.extend([f"定期{x}" for x in validate_cytology(cytology, required=True)])
    if cytology_not_done_now and not text(required_test_omission_reason):
        missing.append("必須尿細胞診の未実施理由")
    if imaging_status is None: missing.append("画像検査実施有無")
    elif imaging_status == "実施":
        if imaging_date is None: missing.append("画像検査日")
        if recist_status == "選択してください": missing.append("RECIST進行状況")
        if recist_status == "今回PDあり":
            if progression_date is None: missing.append("PD確認日")
            if not progression_sites: missing.append("進行/新病変部位")
            if not text(progression_detail): missing.append("進行所見詳細")
    elif not text(imaging_not_done_reason):
        missing.append("画像検査未実施理由")
    if cystoscopy_status is None: missing.append("膀胱鏡実施有無")
    elif cystoscopy_status == "実施":
        if cystoscopy_date is None: missing.append("膀胱鏡日")
        if cystoscopy_result == "選択してください": missing.append("膀胱鏡所見")
        if cystoscopy_result in ["腫瘍あり", "評価不能"] and not text(cystoscopy_detail): missing.append("膀胱鏡所見詳細")
    elif not text(cystoscopy_not_done_reason):
        missing.append("膀胱鏡未実施理由")
    for d, label in [(imaging_date, "画像検査日"), (cystoscopy_date, "膀胱鏡日"), (progression_date, "PD確認日")]:
        if d and visit_date and d > visit_date: errors.append(f"{label}が今回評価日より後です")
        if d and d > today_jst(): errors.append(f"{label}が未来日です")
        if d and reference_date and visit_month != "選択してください" and label in ["画像検査日", "膀胱鏡日"]:
            month_no_check = int(''.join(x for x in visit_month if x.isdigit()))
            target_check = add_months(reference_date, month_no_check)
            if abs((d - target_check).days) > 30:
                warnings.append(f"{label}が{visit_month}の目安日から30日超ずれています")

    parsed_labs = {}
    if show_labs:
        parsed_labs, lab_errors, lab_warn = validate_lab_panel(labs_raw, required=is_final)
        errors.extend([f"採血：{x}" for x in lab_errors])
        warnings.extend([f"採血：{x}" for x in lab_warn])
        if is_final and lab_warn and not text(required_test_omission_reason):
            missing.append("24ヶ月必須採血の欠測理由")
    elif is_final:
        missing.append("24ヶ月終了時採血")

    if intra_status == "選択してください": missing.append("尿路内再発状況")
    if intra_status == "今回新規あり":
        if intra_date is None: missing.append("尿路内再発診断日")
        if not intra_sites: missing.append("尿路内再発部位")
        if "その他" in intra_sites and not text(intra_site_other): missing.append("尿路内再発部位その他詳細")
        if not intra_tx: missing.append("尿路内再発の対応/治療")
        if "経過観察" in intra_tx and len(intra_tx) > 1: errors.append("『経過観察』と他治療を同時選択できません")
        if "その他" in intra_tx and not text(intra_tx_other): missing.append("尿路内治療その他詳細")
        if intra_tx and "経過観察" not in intra_tx and intra_tx_status is None:
            missing.append("尿路内再発治療の状況")
        if intra_tx_status == "実施済み・継続中":
            if any(x in intra_tx for x in ["TURBT", "上部尿路内視鏡的治療", "手術（腎尿管全摘等）"]):
                if intra_procedure_date is None: missing.append("尿路内処置/手術日")
                if not text(intra_path): missing.append("尿路内再発病理")
            if any(x in intra_tx for x in ["BCG注入療法", "抗がん剤注入療法"]):
                if intra_instill_start is None: missing.append("尿路内注入療法開始日")
                if not intra_instill_ongoing and intra_instill_end is None: missing.append("尿路内注入療法終了日")
                if intra_instill_start and intra_instill_end and intra_instill_end < intra_instill_start:
                    errors.append("尿路内注入療法終了日が開始日より前です")
        for dt, label in [(intra_procedure_date, "尿路内処置日"), (intra_instill_start, "尿路内注入療法開始日"), (intra_other_date, "尿路内その他治療日")]:
            if intra_date and dt and dt < intra_date:
                errors.append(f"{label}が再発診断日より前です")

    if current_treatment == "選択してください": missing.append("現在の治療状況")
    if current_treatment in ["治験（TROP2標的ADC、その他）", "その他"] and not text(current_treatment_detail): missing.append("現在治療の詳細")
    if current_treatment not in ["選択してください", "無治療（経過観察）", "上記尿路内再発に対する治療を継続中", "緩和ケア"] and treatment_start is None:
        missing.append("治療開始日")
    if treatment_start and treatment_end and treatment_end < treatment_start: errors.append("治療終了日が開始日より前です")

    if has_event and not text(ae_detail): missing.append("有害事象/合併症詳細")
    if vital_status is None: missing.append("生存状況")
    elif vital_status == "生存":
        if last_alive_date is None: missing.append("最終生存確認日")
        if cd_grade == "Grade V": errors.append("CD Grade Vですが生存状況が生存です")
    else:
        if death_date is None: missing.append("死亡日")
        if death_cause == "選択してください": missing.append("死因")
    for d, label in [(last_alive_date, "最終生存確認日"), (death_date, "死亡日")]:
        if d and d > today_jst(): errors.append(f"{label}が未来日です")

    return unique_messages(missing), unique_messages(errors), unique_messages(warnings), parsed_labs

missing, errors, warnings, parsed_labs = validate_all()
st.markdown('<div class="juog-header">8. 送信</div>', unsafe_allow_html=True)
if missing: st.warning("未入力：" + " / ".join(missing))
if errors: st.error("入力エラー：\n" + "\n".join([f"・{x}" for x in errors]))
if warnings: st.info("確認事項：\n" + "\n".join([f"・{x}" for x in warnings]))

if st.button("🚀 定期経過データを確定送信", type="primary", use_container_width=True, disabled=L):
    if missing or errors:
        st.error("未入力または入力エラーを修正してください。")
    else:
        reg_ok, reg_msg = validate_registry_id(registration_id, facility_code)
        if reg_ok is False:
            st.error(reg_msg)
        else:
            if reg_ok is None:
                st.warning(reg_msg)

            # 送信直前に30日CRFを再照合。取得後に手術日等が訂正されていれば保存しない。
            latest = fetch_30d_linkage(registration_id)
            linkage_stale = False
            if not latest.get("ok") or not latest.get("source_found"):
                st.error("参照元の周術期・30日CRFを再確認できませんでした。『既存情報を取得』をやり直してください。")
                linkage_stale = True
            elif (
                int(latest.get("record_version") or 0) != int(source_30d_record_version or 0)
                or str(latest.get("submission_id") or "") != str(source_30d_submission_id or "")
                or str(latest.get("facility_code") or "") != facility_code
                or str(latest.get("surgery_performed") or "") != surgery_performed
                or str(latest.get("reference_date") or "")[:10] != date_str(reference_date)
            ):
                st.error("参照元の周術期・30日CRFが更新されています。『既存情報を取得』を押して最新情報を再取得してください。")
                linkage_stale = True

            if not linkage_stale:
                visit_key = visit_month.replace("ヶ月（終了）", "m").replace("ヶ月", "m")
                meta = make_submission_metadata(
                    "followup",
                    visit_key,
                    registration_id,
                    facility_code,
                    facility_name,
                    reporter_email,
                    submission_kind,
                    correction_reason,
                )
                data = {
                    "source_30d_linked": True,
                    "source_30d_record_version": source_30d_record_version,
                    "source_30d_submission_id": source_30d_submission_id,
                    "surgery_performed": surgery_performed,
                    "reference_date": date_str(reference_date),
                    "visit_month": visit_month,
                    "visit_date": date_str(visit_date),
                    "timing_note": text(timing_note),
                    "urine_cytology": cytology,
                    "required_test_omission_reason": text(required_test_omission_reason),
                    "imaging_status": imaging_status,
                    "imaging_date": date_str(imaging_date),
                    "imaging_not_done_reason": text(imaging_not_done_reason),
                    "recist_progression_status": recist_status,
                    "progression_date": date_str(progression_date),
                    "progression_sites": progression_sites,
                    "progression_detail": text(progression_detail),
                    "cystoscopy_status": cystoscopy_status,
                    "cystoscopy_date": date_str(cystoscopy_date),
                    "cystoscopy_result": cystoscopy_result,
                    "cystoscopy_detail": text(cystoscopy_detail),
                    "cystoscopy_not_done_reason": text(cystoscopy_not_done_reason),
                    "labs_performed": show_labs,
                    "labs": parsed_labs,
                    "intraluminal_recurrence_status": intra_status,
                    "intraluminal_recurrence_date": date_str(intra_date),
                    "intraluminal_sites": intra_sites,
                    "intraluminal_site_other": text(intra_site_other),
                    "intraluminal_treatment": intra_tx,
                    "intraluminal_treatment_other": text(intra_tx_other),
                    "intraluminal_treatment_status": intra_tx_status,
                    "intraluminal_procedure_date": date_str(intra_procedure_date),
                    "intraluminal_instillation_start": date_str(intra_instill_start),
                    "intraluminal_instillation_end": date_str(intra_instill_end),
                    "intraluminal_instillation_ongoing": intra_instill_ongoing,
                    "intraluminal_other_treatment_date": date_str(intra_other_date),
                    "intraluminal_pathology": text(intra_path),
                    "current_treatment": current_treatment,
                    "current_treatment_detail": text(current_treatment_detail),
                    "treatment_start": date_str(treatment_start),
                    "treatment_end": date_str(treatment_end),
                    "treatment_ongoing": treatment_ongoing,
                    "event_present": has_event,
                    "cd_grade": cd_grade,
                    "event_detail": text(ae_detail),
                    "vital_status": vital_status,
                    "last_alive_date": date_str(last_alive_date),
                    "death_date": date_str(death_date),
                    "death_cause": death_cause,
                }
                payload = {**meta, "data": data}
                base_label = "実手術日" if surgery_performed == "実施した" else "手術予定日"
                report = f"""【JUOG 定期経過報告】
JUOG登録番号: {registration_id}
施設: {facility_name}
報告時期: {visit_month}
評価日: {date_str(visit_date)}
報告種別: {submission_kind}
手術実施: {surgery_performed}
{base_label}: {date_str(reference_date)}
参照30日CRF: version {source_30d_record_version}
RECIST進行状況: {recist_status}
今回PD確認日: {date_str(progression_date) or 'N/A'}
尿路内再発: {intra_status}
現在の治療: {current_treatment}
生存状況: {vital_status}
死亡日: {date_str(death_date) or 'N/A'}

{json_block(payload)}
"""
                save_result = save_crf_payload(payload)
                if not save_result.get("ok"):
                    st.error(
                        "中央Google Sheetへ保存できませんでした："
                        + (save_result.get("message") or save_result.get("error") or "unknown error")
                    )
                else:
                    sent, send_err = send_email(
                        f"【JUOG CRF】【followup-{visit_key}】【{registration_id}】",
                        report,
                        reporter_email,
                    )
                    st.session_state.fu_sent = True
                    st.session_state.fu_sent_registration_id = registration_id
                    st.session_state.fu_sent_visit = visit_month
                    st.session_state.fu_sent_version = str(save_result.get("record_version", "") or "")
                    st.session_state.fu_sent_had_warnings = bool(warnings)
                    st.session_state.fu_sent_email_failed = not sent
                    if not sent:
                        print(f"[JUOG followup] email failed: {send_err}")
                    st.rerun()
