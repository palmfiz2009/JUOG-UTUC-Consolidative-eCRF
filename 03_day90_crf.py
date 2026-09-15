from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from juog_common import (
    CD_MAJOR,
    CD_OPTIONS,
    LAB_FIELDS,
    POSTOP_TREATMENT_OPTIONS,
    RECURRENCE_DRUG_OPTIONS,
    date_str,
    json_block,
    make_submission_metadata,
    render_facility,
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
    window_info,
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


def render_optional_lab_panel(prefix: str, disabled=False, columns=3):
    """Routine-care labs: enter measured values only; unmeasured items stay blank."""
    st.caption("数値を入力してください。未測定・欠測の項目は空欄で構いません。0 は実測値として保存されます。")
    cols = st.columns(columns)
    out = {}
    for i, (key, label, unit) in enumerate(LAB_FIELDS):
        session_key = f"{prefix}_{key}"
        if session_key not in st.session_state:
            st.session_state[session_key] = ""
        out[key] = cols[i % columns].text_input(
            f"{label} ({unit})",
            value=st.session_state[session_key],
            key=f"widget_{session_key}",
            disabled=disabled,
        )
        st.session_state[session_key] = out[key]
    return out


def validate_optional_lab_panel(raw_values: dict):
    parsed, errors, _warnings = validate_lab_panel(raw_values, required=False)
    clean_errors = [
        x.replace("数値またはNAで入力してください", "数値で入力してください（未測定・欠測は空欄）")
        for x in errors
    ]
    return parsed, clean_errors


def fetch_30d_linkage(registration_id: str):
    return registry_call(
        "get_crf_linkage",
        {"registration_id": registration_id.strip().upper(), "source_crf_type": "perioperative_30d"},
        timeout=20,
    )


st.title("JUOG UTUC_Consolidative 術後90日CRF")

if "d90_sent" not in st.session_state:
    st.session_state.d90_sent = False
if "d90_linkage" not in st.session_state:
    st.session_state.d90_linkage = None
if "d90_linkage_message" not in st.session_state:
    st.session_state.d90_linkage_message = ""

if st.session_state.d90_sent:
    sent_id = st.session_state.get("d90_sent_registration_id", "")
    sent_version = st.session_state.get("d90_sent_version", "")
    st.success("送信が完了しました。")
    if sent_id:
        st.write(f"**JUOG登録番号：{sent_id}**")
    if sent_version:
        st.caption(f"術後90日CRFを保存しました（version {sent_version}）。")
    else:
        st.caption("術後90日CRFを保存しました。")
    if st.session_state.get("d90_sent_had_warnings"):
        st.info("確認事項も中央データに保存されています。")
    if st.session_state.get("d90_sent_email_failed"):
        st.warning("中央Google Sheetへの保存は完了していますが、通知メール送信に失敗しました。再入力はせず事務局へ連絡してください。")
    st.caption("訂正する場合はページを再読み込みし、「訂正報告」を選択して送信してください。")
    st.stop()

L = False

st.markdown('<div class="juog-header">1. 基本情報・90日評価時期</div>', unsafe_allow_html=True)

top1, top2 = st.columns(2)
with top1:
    registration_id = st.text_input(
        "JUOG登録番号*",
        placeholder="JUOG-001",
        key="d90_registration_id",
        disabled=L,
    ).strip().upper()
    reporter_email = st.text_input("担当者メールアドレス*", key="d90_reporter_email", disabled=L)
with top2:
    submission_kind, correction_reason = render_submission_kind("d90", disabled=L)

fetch_disabled = not valid_registration_id(registration_id)
if st.button("既存情報を取得", use_container_width=True, disabled=fetch_disabled or L):
    result = fetch_30d_linkage(registration_id)
    if result.get("ok"):
        st.session_state.d90_linkage = result
        st.session_state.d90_linkage_message = result.get("message", "")
        st.rerun()
    else:
        # Safe fallback: do not infer data. Allow manual entry only after an explicit failed retrieval.
        st.session_state.d90_linkage = {
            "ok": True,
            "source_found": False,
            "registration_id": registration_id,
            "manual_fallback": True,
            "facility_code": result.get("facility_code", ""),
            "facility_name": result.get("facility_name", ""),
        }
        st.session_state.d90_linkage_message = (
            result.get("message")
            or "既存の周術期・30日CRFを安全に取得できませんでした。手入力に切り替えます。"
        )
        st.rerun()

linkage = st.session_state.get("d90_linkage")
if linkage and linkage.get("registration_id") != registration_id:
    linkage = None
    st.warning("JUOG登録番号が変更されています。「既存情報を取得」をもう一度押してください。")

if not linkage:
    st.info("JUOG登録番号を入力し、「既存情報を取得」を押してください。90日CRFでは既存の手術情報を確認してから入力を開始します。")
    st.stop()

source_found = bool(linkage.get("source_found"))
manual_fallback = bool(linkage.get("manual_fallback")) or not source_found
facility_code = str(linkage.get("facility_code") or "")
facility_name = str(linkage.get("facility_name") or "")

if source_found:
    surgery_performed = str(linkage.get("surgery_performed") or "")
    reference_date = parse_iso_date(linkage.get("reference_date"))
    source_30d_record_version = int(linkage.get("record_version") or 0)
    source_30d_submission_id = str(linkage.get("submission_id") or "")

    st.success("周術期・30日CRFの最新情報を取得しました。")
    c1, c2, c3 = st.columns(3)
    c1.text_input("施設", value=facility_name, disabled=True)
    c2.text_input("Consolidative surgery", value=surgery_performed, disabled=True)
    c3.text_input(
        "手術日" if surgery_performed == "実施した" else "手術予定日",
        value=date_str(reference_date),
        disabled=True,
    )
    st.caption(f"参照元：周術期・30日CRF version {source_30d_record_version}")
else:
    source_30d_record_version = 0
    source_30d_submission_id = ""
    st.warning(st.session_state.get("d90_linkage_message") or "周術期・30日CRFが見つからないため手入力します。")
    if facility_name:
        st.text_input("施設", value=facility_name, disabled=True)
    else:
        facility_code, facility_name = render_facility(key="d90_facility", disabled=L)
    m1, m2 = st.columns(2)
    with m1:
        surgery_performed = st.radio(
            "Consolidative surgeryの実施*",
            ["実施した", "実施しなかった"],
            index=None,
            horizontal=True,
            disabled=L,
        )
    with m2:
        reference_date = st.date_input(
            "手術日*" if surgery_performed == "実施した" else "手術予定日*",
            value=None,
            disabled=L,
        )

visit_date = st.date_input("90日評価日*", value=None, disabled=L)
visit_deviation_reason = ""
if reference_date:
    wi = window_info(reference_date, 90, 14)
    st.info(f"90日評価許容期間：{wi['min']:%Y/%m/%d} ～ {wi['max']:%Y/%m/%d}")
    if visit_date:
        if wi["min"] <= visit_date <= wi["max"]:
            st.success("90日±14日の範囲内です。")
        else:
            st.warning("90日±14日の範囲外です。データは受理できますが、理由を記録してください。")
            visit_deviation_reason = st.text_area("90日評価時期の逸脱理由*", disabled=L)
        if surgery_performed == "実施した" and visit_date < reference_date + timedelta(days=90):
            st.warning("術後90日より前の評価です。術後90日までに新たな手術関連合併症が生じた場合は訂正報告してください。")

# ---------------- surveillance ----------------
st.markdown('<div class="juog-header">2. 90日検査</div>', unsafe_allow_html=True)
st.subheader("血液検査")
st.caption(
    "90日±14日の期間内に通常診療として採血が実施された場合、その期間内で術後90日目に最も近い採血結果を入力してください。"
    "研究目的の追加採血は不要です。"
)
lab_available = st.radio(
    "90日評価期間内の採血*",
    ["あり", "なし"],
    index=None,
    horizontal=True,
    disabled=L,
)
lab_date = None
labs_raw = {}
if lab_available == "あり":
    lab_date = st.date_input("90日評価に用いた採血日*", value=None, disabled=L)
    labs_raw = render_optional_lab_panel("d90_lab", disabled=L, columns=3)

st.subheader("尿細胞診")
cytology = render_cytology("d90", required=True, disabled=L)

st.subheader("画像検査・膀胱鏡")
i1, i2 = st.columns(2)
with i1:
    imaging_status = st.radio("画像検査（CT/MRI等）の実施*", ["実施", "未実施"], index=None, horizontal=True, disabled=L)
    imaging_date = None
    imaging_not_done_reason = ""
    recist_status = "NE（未実施）"
    progression_date = None
    progression_sites = []
    progression_detail = ""
    if imaging_status == "実施":
        imaging_date = st.date_input("画像検査日*", value=None, disabled=L)
        recist_status = st.selectbox("画像上のRECIST v1.1進行*", ["選択してください", "PDなし", "PDあり", "NE（評価不能）"], disabled=L)
        if recist_status == "PDあり":
            progression_date = st.date_input("RECIST PD確認日*", value=None, disabled=L)
            progression_sites = st.multiselect("進行/新病変部位*", ["原発/手術局所", "リンパ節", "肺", "肝", "骨", "その他"], disabled=L)
            progression_detail = st.text_area("進行所見の詳細*", disabled=L)
    elif imaging_status == "未実施":
        imaging_not_done_reason = st.text_area("画像検査未実施理由*", placeholder="例：90日以前に死亡、全身状態不良、患者都合等", disabled=L)
with i2:
    cystoscopy_status = st.radio("膀胱鏡の実施*", ["実施", "未実施"], index=None, horizontal=True, disabled=L)
    cystoscopy_date = None
    cystoscopy_result = "未実施"
    cystoscopy_detail = ""
    cystoscopy_not_done_reason = ""
    if cystoscopy_status == "実施":
        cystoscopy_date = st.date_input("膀胱鏡日*", value=None, disabled=L)
        cystoscopy_result = st.selectbox("膀胱鏡所見*", ["選択してください", "腫瘍なし", "腫瘍あり", "評価不能"], disabled=L)
        cystoscopy_detail = st.text_area("膀胱鏡所見の詳細*" if cystoscopy_result in ["腫瘍あり", "評価不能"] else "膀胱鏡所見の詳細", disabled=L)
    elif cystoscopy_status == "未実施":
        cystoscopy_not_done_reason = st.text_area("膀胱鏡未実施理由*", placeholder="例：90日以前に死亡、全身状態不良、患者拒否等", disabled=L)

required_test_omission_reason = ""
cytology_not_done_now = cytology == "未実施"
if cytology_not_done_now:
    required_test_omission_reason = st.text_area(
        "尿細胞診未実施理由*",
        placeholder="例：全身状態不良、患者都合、死亡前の評価不能等",
        disabled=L,
    )

# ---------------- safety ----------------
st.markdown('<div class="juog-header">3. 術後31〜90日の手術関連合併症・有害事象</div>', unsafe_allow_html=True)
new_complication = "N/A"
cd_grade = "N/A"
cd_date = None
cd_detail = ""
cd_relation = "N/A"
renal_exception = False
renal_exception_detail = ""
if surgery_performed == "実施した":
    new_complication = st.radio("30日報告後〜術後90日までに新たな手術関連合併症*", ["なし", "あり"], index=None, horizontal=True, disabled=L)
    if new_complication == "あり":
        c1, c2 = st.columns(2)
        with c1:
            cd_grade = st.selectbox("最高Clavien-Dindo Grade*", [x for x in CD_OPTIONS if x not in ["Grade 0"]], disabled=L)
            cd_date = st.date_input("合併症発現日*", value=None, disabled=L)
            cd_detail = st.text_area("合併症詳細*", disabled=L)
        with c2:
            cd_relation = st.selectbox("手術手技との因果関係*", ["選択してください", "関連する", "否定できない", "関連しない"], disabled=L)
            renal_exception = st.checkbox("計画書の腎機能低下/透析除外規定に該当", disabled=L)
            if renal_exception:
                renal_exception_detail = st.text_area(
                    "腎機能低下/透析除外規定に該当する根拠*",
                    placeholder="例：術前から透析導入が医学的に予測され、説明・同意済み。",
                    disabled=L,
                )
    elif new_complication == "なし":
        cd_grade = "Grade 0"
else:
    st.info("手術未施行例のClavien-Dindo評価はN/Aです。")

has_ctcae = st.checkbox("90日評価までに報告すべき薬剤関連等AE（CTCAE v6.0）がある", disabled=L)
ctcae_detail = ""
if has_ctcae:
    ctcae_detail = st.text_area("CTCAE有害事象詳細*", disabled=L)

# ---------------- recurrence ----------------
st.markdown('<div class="juog-header">4. 尿路内再発・治療</div>', unsafe_allow_html=True)
intra_status = st.radio("尿路内再発の有無*", ["なし", "あり"], index=None, horizontal=True, disabled=L)
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
if intra_status == "あり":
    r1, r2 = st.columns(2)
    with r1:
        intra_date = st.date_input("尿路内再発診断日*", value=None, disabled=L)
        intra_sites = st.multiselect("再発部位*", ["膀胱", "対側腎盂", "対側尿管", "同側残存尿管", "その他"], disabled=L)
        if "その他" in intra_sites:
            intra_site_other = st.text_input("再発部位 その他詳細*", disabled=L)
    with r2:
        intra_tx = st.multiselect("対応/治療*", ["経過観察", "TURBT", "BCG注入療法", "抗がん剤注入療法", "上部尿路内視鏡的治療", "手術（腎尿管全摘等）", "その他"], disabled=L)
        if "その他" in intra_tx:
            intra_tx_other = st.text_input("尿路内治療 その他詳細*", disabled=L)
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

# ---------------- post-op treatment ----------------
st.markdown('<div class="juog-header">5. 術後治療</div>', unsafe_allow_html=True)
adj_plan = st.selectbox("現在/これまでの術後治療*", POSTOP_TREATMENT_OPTIONS, disabled=L)
adj_detail = ""
adj_start = adj_end = None
adj_ongoing = False
if adj_plan not in ["選択してください", "無治療（経過観察）"]:
    if adj_plan in ["治験（TROP2標的ADC、その他）", "その他"]:
        adj_detail = st.text_area("治療詳細*", disabled=L)
    a1, a2 = st.columns(2)
    adj_start = a1.date_input("開始日*", value=None, disabled=L)
    adj_ongoing = a2.checkbox("継続中", disabled=L)
    if not adj_ongoing:
        adj_end = a2.date_input("終了日（継続予定なら空欄可）", value=None, disabled=L)

# ---------------- OS ----------------
st.markdown('<div class="juog-header">6. 生存状況</div>', unsafe_allow_html=True)
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
    if not facility_name or facility_name == "選択してください":
        missing.append("施設名")
    if not registration_id:
        missing.append("JUOG登録番号")
    elif not valid_registration_id(registration_id):
        errors.append("JUOG登録番号の形式が不正です（例：JUOG-001）")
    if not text(reporter_email):
        missing.append("担当者メールアドレス")
    elif not valid_email(reporter_email):
        errors.append("担当者メールアドレスが不正です")
    if submission_kind == "訂正報告" and not text(correction_reason):
        missing.append("訂正理由")
    if surgery_performed not in ["実施した", "実施しなかった"]:
        missing.append("手術実施有無")
    if reference_date is None:
        missing.append("手術日" if surgery_performed == "実施した" else "手術予定日")
    if visit_date is None: missing.append("90日評価日")
    if reference_date and visit_date:
        wi = window_info(reference_date, 90, 14)
        if visit_date < reference_date: errors.append("90日評価日が手術/予定日より前です")
        if visit_date > today_jst(): errors.append("90日評価日が未来日です")
        if not (wi["min"] <= visit_date <= wi["max"]):
            warnings.append("90日評価日が90日±14日の範囲外です")
            if not text(visit_deviation_reason): missing.append("90日評価時期の逸脱理由")

    parsed_labs, lab_errors = validate_optional_lab_panel(labs_raw)
    errors.extend([f"90日血液検査：{x}" for x in lab_errors])
    if lab_available is None:
        missing.append("90日評価期間内の採血有無")
    elif lab_available == "あり":
        if lab_date is None:
            missing.append("90日評価に用いた採血日")
        if not any(text(v) for v in labs_raw.values()):
            missing.append("90日評価採血結果")
        if lab_date and reference_date:
            wi_lab = window_info(reference_date, 90, 14)
            if not (wi_lab["min"] <= lab_date <= wi_lab["max"]):
                errors.append("90日評価に用いた採血日が90日±14日の許容期間外です")
        if lab_date and lab_date > today_jst():
            errors.append("90日評価に用いた採血日が未来日です")
        if lab_date and visit_date and lab_date > visit_date:
            warnings.append("90日採血日が90日評価日より後です")

    missing.extend([f"90日{x}" for x in validate_cytology(cytology, required=True)])
    if cytology == "未実施" and not text(required_test_omission_reason):
        missing.append("尿細胞診未実施理由")
    if imaging_status is None: missing.append("画像検査実施有無")
    elif imaging_status == "実施":
        if imaging_date is None: missing.append("画像検査日")
        if recist_status == "選択してください": missing.append("RECIST進行判定")
        if recist_status == "PDあり":
            if progression_date is None: missing.append("RECIST PD確認日")
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
        if d and visit_date and d > visit_date: errors.append(f"{label}が90日評価日より後です")
        if d and d > today_jst(): errors.append(f"{label}が未来日です")
        if d and reference_date and label in ["画像検査日", "膀胱鏡日"]:
            wi_test = window_info(reference_date, 90, 14)
            if not (wi_test["min"] <= d <= wi_test["max"]):
                warnings.append(f"{label}が90日±14日の目安範囲外です")

    if surgery_performed == "実施した":
        if new_complication is None: missing.append("31〜90日新規手術関連合併症")
        if new_complication == "あり":
            if cd_grade in ["選択してください", "Grade 0", "N/A"]: missing.append("Clavien-Dindo Grade")
            if cd_date is None: missing.append("合併症発現日")
            if not text(cd_detail): missing.append("合併症詳細")
            if cd_relation == "選択してください": missing.append("手術手技との因果関係")
            if renal_exception and not text(renal_exception_detail): missing.append("腎機能低下/透析除外規定の根拠")
            if cd_date and reference_date:
                d = (cd_date - reference_date).days
                if d <= 30: errors.append("31〜90日合併症欄には術後31日以降の事象を入力してください（30日以内は30日CRFの訂正報告）")
                if d > 90: errors.append("90日手術関連合併症の評価対象は術後90日以内です")
    if has_ctcae and not text(ctcae_detail): missing.append("CTCAE有害事象詳細")

    if intra_status is None: missing.append("尿路内再発の有無")
    if intra_status == "あり":
        if intra_date is None: missing.append("尿路内再発診断日")
        if not intra_sites: missing.append("尿路内再発部位")
        if "その他" in intra_sites and not text(intra_site_other): missing.append("尿路内再発部位その他詳細")
        if not intra_tx: missing.append("尿路内再発の対応/治療")
        if "経過観察" in intra_tx and len(intra_tx) > 1: errors.append("尿路内再発治療で『経過観察』と他治療を同時選択できません")
        if "その他" in intra_tx and not text(intra_tx_other): missing.append("尿路内治療その他詳細")
        if intra_tx and "経過観察" not in intra_tx and intra_tx_status is None:
            missing.append("尿路内再発治療の状況")
        if intra_tx_status == "実施済み・継続中":
            if any(x in intra_tx for x in ["TURBT", "上部尿路内視鏡的治療", "手術（腎尿管全摘等）"]):
                if intra_procedure_date is None: missing.append("尿路内再発処置/手術日")
                if not text(intra_path): missing.append("尿路内再発病理")
            if any(x in intra_tx for x in ["BCG注入療法", "抗がん剤注入療法"]):
                if intra_instill_start is None: missing.append("尿路内注入療法開始日")
                if not intra_instill_ongoing and intra_instill_end is None: missing.append("尿路内注入療法終了日")
                if intra_instill_start and intra_instill_end and intra_instill_end < intra_instill_start:
                    errors.append("尿路内注入療法終了日が開始日より前です")
        for dt, label in [(intra_procedure_date, "尿路内再発処置日"), (intra_instill_start, "尿路内注入療法開始日"), (intra_other_date, "尿路内その他治療日")]:
            if intra_date and dt and dt < intra_date:
                errors.append(f"{label}が再発診断日より前です")

    if adj_plan == "選択してください": missing.append("術後治療")
    if adj_plan in ["治験（TROP2標的ADC、その他）", "その他"] and not text(adj_detail): missing.append("術後治療詳細")
    if adj_plan not in ["選択してください", "無治療（経過観察）"] and adj_start is None: missing.append("術後治療開始日")
    if adj_start and adj_end and adj_end < adj_start: errors.append("術後治療終了日が開始日より前です")

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
st.markdown('<div class="juog-header">7. 送信</div>', unsafe_allow_html=True)
if missing or errors or warnings:
    summary_parts = []
    if missing:
        summary_parts.append(f"未入力 {len(missing)}項目")
    if errors:
        summary_parts.append(f"エラー {len(errors)}件")
    if warnings:
        summary_parts.append(f"確認事項 {len(warnings)}件")
    st.caption("入力状況：" + " / ".join(summary_parts))
    with st.expander("入力状況の詳細を確認"):
        if missing:
            st.write("**未入力**")
            st.write(" / ".join(missing))
        if errors:
            st.write("**入力エラー**")
            for x in errors:
                st.write(f"・{x}")
        if warnings:
            st.write("**確認事項**")
            for x in warnings:
                st.write(f"・{x}")
else:
    st.success("必須項目の入力と基本的な整合性チェックが完了しています。")

if st.button("90日データを確定送信", type="primary", use_container_width=True, disabled=L):
    if missing or errors:
        st.error("未入力または入力エラーを修正してください。")
    else:
        reg_ok, reg_msg = validate_registry_id(registration_id, facility_code)
        if reg_ok is False:
            st.error(reg_msg)
        else:
            if reg_ok is None:
                st.warning(reg_msg)

            # Semi-automatic linkage safety check:
            # if the source 30-day CRF changed after retrieval, stop and require re-fetch.
            linkage_stale = False
            if source_found:
                latest = fetch_30d_linkage(registration_id)
                if not latest.get("ok") or not latest.get("source_found"):
                    st.error("参照元の周術期・30日CRFを再確認できませんでした。「既存情報を取得」をやり直してください。")
                    linkage_stale = True
                elif (
                    int(latest.get("record_version") or 0) != int(source_30d_record_version or 0)
                    or str(latest.get("submission_id") or "") != str(source_30d_submission_id or "")
                ):
                    st.error("参照元の周術期・30日CRFが更新されています。「既存情報を取得」を押して最新情報を再取得してください。")
                    linkage_stale = True

            if not linkage_stale:
                major_31_90 = bool(
                    new_complication == "あり"
                    and cd_grade in CD_MAJOR
                    and cd_relation in ["関連する", "否定できない"]
                    and not renal_exception
                )
                meta = make_submission_metadata(
                    "day90",
                    "90d",
                    registration_id,
                    facility_code,
                    facility_name,
                    reporter_email,
                    submission_kind,
                    correction_reason,
                )
                data = {
                    "source_30d_linked": source_found,
                    "source_30d_record_version": source_30d_record_version if source_found else None,
                    "source_30d_submission_id": source_30d_submission_id if source_found else "",
                    "surgery_performed": surgery_performed,
                    "reference_date": date_str(reference_date),
                    "visit_date": date_str(visit_date),
                    "visit_deviation_reason": text(visit_deviation_reason),
                    "lab_available": lab_available,
                    "lab_date": date_str(lab_date),
                    "labs": parsed_labs,
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
                    "new_surgical_complication_day31_90": new_complication,
                    "cd_grade_day31_90": cd_grade,
                    "cd_event_date": date_str(cd_date),
                    "cd_detail": text(cd_detail),
                    "cd_surgery_relation": cd_relation,
                    "renal_exception": renal_exception,
                    "renal_exception_detail": text(renal_exception_detail),
                    "major_surgery_related_complication_day31_90": major_31_90,
                    "ctcae_event": has_ctcae,
                    "ctcae_detail": text(ctcae_detail),
                    "intraluminal_recurrence": intra_status,
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
                    "postop_treatment": adj_plan,
                    "postop_treatment_detail": text(adj_detail),
                    "postop_treatment_start": date_str(adj_start),
                    "postop_treatment_end": date_str(adj_end),
                    "postop_treatment_ongoing": adj_ongoing,
                    "vital_status": vital_status,
                    "last_alive_date": date_str(last_alive_date),
                    "death_date": date_str(death_date),
                    "death_cause": death_cause,
                }
                payload = {**meta, "data": data}
                report = f"""【JUOG 術後90日報告】
JUOG登録番号: {registration_id}
施設: {facility_name}
報告種別: {submission_kind}
90日評価日: {date_str(visit_date)}
手術実施: {surgery_performed}
手術日/予定日: {date_str(reference_date)}
参照30日CRF: {'version ' + str(source_30d_record_version) if source_found else '手入力'}
RECIST進行: {recist_status}
PD確認日: {date_str(progression_date) or 'N/A'}
尿路内再発: {intra_status}
31〜90日新規手術関連合併症: {new_complication}
最高CD Grade: {cd_grade}
31〜90日主要手術関連合併症（定義該当）: {'はい' if major_31_90 else 'いいえ'}
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
                        f"【JUOG CRF】【day90】【{registration_id}】",
                        report,
                        reporter_email,
                    )
                    st.session_state.d90_sent = True
                    st.session_state.d90_sent_registration_id = registration_id
                    st.session_state.d90_sent_version = str(save_result.get("record_version", "") or "")
                    st.session_state.d90_sent_had_warnings = bool(warnings)
                    st.session_state.d90_sent_email_failed = not sent
                    if not sent:
                        print(f"[JUOG day90] email failed: {send_err}")
                    st.rerun()
