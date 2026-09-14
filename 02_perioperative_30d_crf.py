from __future__ import annotations

from datetime import timedelta

import streamlit as st

from juog_common import (
    CD_MAJOR,
    CD_OPTIONS,
    POSTOP_TREATMENT_OPTIONS,
    date_str,
    json_block,
    make_submission_metadata,
    render_facility,
    render_lab_panel,
    render_submission_kind,
    send_email,
    text,
    today_jst,
    unique_messages,
    valid_email,
    valid_registration_id,
    validate_lab_panel,
    validate_registry_id,
    window_info,
)

st.markdown("""
<style>
.block-container {max-width:1180px!important; padding-top:1.3rem!important; padding-bottom:5rem!important;}
h1 {font-size:27px!important; text-align:center; color:#0F172A; margin-bottom:30px!important;}
.juog-header {background:#1E3A8A;color:white;padding:10px 18px;border-radius:8px;font-weight:700;margin-top:24px;margin-bottom:14px;}
label {font-weight:600!important;color:#334155!important;}
</style>
""", unsafe_allow_html=True)

st.title("JUOG UTUC_Consolidative 周術期・術後30日CRF")
st.caption("主要評価項目の手術関連合併症は『手術終了時〜術後30日目』で判定します。30日訪問自体は30日±14日を許容します。")

if "peri_sent" not in st.session_state:
    st.session_state.peri_sent = False
L = st.session_state.peri_sent
if L:
    st.info("このセッションでは送信済みです。訂正が必要な場合はページを再読み込みし『訂正報告』として送信してください。")

# ---------------- basic ----------------
st.markdown('<div class="juog-header">1. 基本情報</div>', unsafe_allow_html=True)
b1, b2 = st.columns(2)
with b1:
    facility_code, facility_name = render_facility(key="peri_facility", disabled=L)
    registration_id = st.text_input("JUOG登録番号*", placeholder="JUOG-001", disabled=L).strip().upper()
    reporter_email = st.text_input("担当者メールアドレス*", disabled=L)
with b2:
    submission_kind, correction_reason = render_submission_kind("peri", disabled=L)
    surgery_performed = st.radio("Consolidative surgeryの実施*", ["実施した", "実施しなかった"], index=None, horizontal=True, disabled=L)
    planned_or_reference_date = st.date_input("手術日（未施行例は予定日）*", value=None, disabled=L)

# ---------------- perioperative ----------------
st.markdown('<div class="juog-header">2. 手術・入院経過</div>', unsafe_allow_html=True)
last_evp_date = st.date_input("EVP最終投与日*", value=None, disabled=L)
protocol_deviation_reason = ""

op_admission_date = op_date = op_discharge_date = None
op_type = approach = op_completed = None
op_incomplete_detail = ""
op_time = bleeding = None
eau_grade = "選択してください"
eau_detail = ""
ln_dissection = None
ln_range = []
unrecovered_g2_relevant = None

if surgery_performed == "実施した":
    c1, c2 = st.columns(2)
    with c1:
        op_admission_date = st.date_input("入院日*", value=None, disabled=L)
        op_date = st.date_input("手術実施日*", value=planned_or_reference_date, disabled=L)
        op_discharge_date = st.date_input("退院日*", value=None, disabled=L)
        op_type = st.selectbox("術式*", ["選択してください", "根治的腎尿管全摘除術", "尿管部分切除術", "その他（プロトコル逸脱）"], disabled=L)
        if op_type == "その他（プロトコル逸脱）":
            st.text_input("実施術式の詳細*", key="peri_op_other", disabled=L)
        approach = st.radio("アプローチ*", ["開腹", "腹腔鏡", "ロボット支援"], index=None, horizontal=True, disabled=L)
        op_completed = st.radio("予定した原発巣切除を完遂*", ["はい", "いいえ"], index=None, horizontal=True, disabled=L)
        if op_completed == "いいえ":
            op_incomplete_detail = st.text_area("完遂不能理由*", disabled=L)
    with c2:
        op_time = st.number_input("手術時間 (分)*", min_value=0, value=None, step=1, disabled=L)
        bleeding = st.number_input("出血量 (mL)*", min_value=0, value=None, step=1, disabled=L)
        eau_grade = st.selectbox("術中合併症 (EAUiaiC)*", ["選択してください", "Grade 0", "Grade 1", "Grade 2", "Grade 3", "Grade 4A", "Grade 4B", "Grade 5A", "Grade 5B"], disabled=L)
        if eau_grade not in ["選択してください", "Grade 0"]:
            eau_detail = st.text_area("術中合併症詳細*", disabled=L)
        ln_dissection = st.radio("リンパ節郭清*", ["実施した", "実施しなかった"], index=None, horizontal=True, disabled=L)
        if ln_dissection == "実施した":
            ln_range = st.multiselect("郭清範囲*", ["腎門部", "下大静脈周囲", "大動脈周囲", "傍大動脈", "大動脈静脈間", "総腸骨", "外腸骨", "内腸骨", "閉鎖", "その他"], disabled=L)
        unrecovered_g2_relevant = st.radio(
            "手術時点で手術手技に影響しうるGrade 2以上の未回復AE*",
            ["なし", "あり"], index=None, horizontal=True, disabled=L,
            help="脱毛・色素沈着など手術手技に影響しない事象は除外します。",
        )
        if unrecovered_g2_relevant == "あり":
            st.text_area("未回復AEの詳細*", key="peri_g2_detail", disabled=L)

    if last_evp_date and op_date:
        washout_days = (op_date - last_evp_date).days
        st.write(f"EVP最終投与→手術：**{washout_days}日**")
        if 28 <= washout_days <= 56:
            st.success("計画書の原則4–8週内です。")
        elif 57 <= washout_days <= 84:
            st.warning("8週超〜12週以内：計画書上、医学的理由等により許容される範囲です。")
            protocol_deviation_reason = st.text_area("8週超となった理由*", disabled=L)
        else:
            st.warning("計画書の4–12週の範囲外です。実データは受理しますが、理由を記録してください。")
            protocol_deviation_reason = st.text_area("手術時期のプロトコル逸脱理由*", disabled=L)
else:
    no_op_reason = st.selectbox("手術未施行理由*", ["選択してください", "病勢進行", "EVP関連有害事象", "中央MDT/手術適応変更", "同意撤回", "患者希望", "その他"], disabled=L)
    if no_op_reason == "その他":
        st.text_area("手術未施行理由 その他詳細*", key="peri_noop_other", disabled=L)

# Day0 / inpatient vitals and labs
st.subheader("Day 0 / 術後入院中の安全性データ")
v1, v2 = st.columns(2)
with v1:
    day0_sbp = st.number_input("Day 0 収縮期血圧 (mmHg)", min_value=0, value=None, step=1, disabled=L)
    day0_dbp = st.number_input("Day 0 拡張期血圧 (mmHg)", min_value=0, value=None, step=1, disabled=L)
    day0_pulse = st.number_input("Day 0 脈拍 (/min)", min_value=0, value=None, step=1, disabled=L)
    day0_temp = st.number_input("Day 0 体温 (℃)", min_value=30.0, max_value=45.0, value=None, step=0.1, disabled=L)
with v2:
    inpatient_sbp = st.number_input("入院中代表 収縮期血圧 (mmHg)", min_value=0, value=None, step=1, disabled=L)
    inpatient_dbp = st.number_input("入院中代表 拡張期血圧 (mmHg)", min_value=0, value=None, step=1, disabled=L)
    inpatient_pulse = st.number_input("入院中代表 脈拍 (/min)", min_value=0, value=None, step=1, disabled=L)
    inpatient_temp = st.number_input("入院中代表 体温 (℃)", min_value=30.0, max_value=45.0, value=None, step=0.1, disabled=L)

st.write("**術後入院中 血液検査（代表値）**")
inpatient_labs_raw = render_lab_panel("peri_inpatient_lab", required=(surgery_performed == "実施した"), disabled=L, columns=3)
inpatient_omission_reason = ""
if surgery_performed == "実施した" and any(str(v).strip().upper() in {"NA", "N/A", "未実施", "欠測"} for v in inpatient_labs_raw.values()):
    inpatient_omission_reason = st.text_area("術後入院中の必須採血 欠測/未実施理由*", disabled=L)

# ---------------- pathology ----------------
st.markdown('<div class="juog-header">3. 術後病理</div>', unsafe_allow_html=True)
path = {}
if surgery_performed == "実施した":
    p1, p2 = st.columns(2)
    with p1:
        path["histology"] = st.selectbox("組織型*", ["選択してください", "Urothelial carcinoma", "Urothelial carcinoma（亜型・分化を含む）", "その他", "評価不能"], disabled=L)
        if path["histology"] == "その他":
            path["histology_other"] = st.text_input("組織型 その他詳細*", disabled=L)
        else:
            path["histology_other"] = ""
        path["subtype_presence"] = st.radio("亜型/分化の有無*", ["なし", "あり"], index=None, horizontal=True, disabled=L)
        if path["subtype_presence"] == "あり":
            path["subtypes"] = st.multiselect("亜型/分化*", ["Nested", "Micropapillary", "Plasmacytoid", "Sarcomatoid", "Squamous differentiation", "Glandular differentiation", "その他"], disabled=L)
        else:
            path["subtypes"] = []
        path["size_mm"] = st.number_input("病理最大径 (mm)*", min_value=0.0, value=None, step=0.1, disabled=L)
        path["locations"] = st.multiselect("病理部位*", ["腎盂", "上部尿管", "中部尿管", "下部尿管", "その他"], disabled=L)
    with p2:
        path["ypt"] = st.selectbox("ypT*", ["選択してください", "ypT0", "ypTa", "ypTis", "ypT1", "ypT2", "ypT3", "ypT4", "評価不能"], disabled=L)
        if ln_dissection == "実施した":
            path["ypn"] = st.selectbox("ypN*", ["選択してください", "ypN0", "ypN1", "ypN2", "評価不能"], disabled=L)
        else:
            path["ypn"] = "未郭清"
            st.info("リンパ節未郭清のためypNは『未郭清』として記録します。")
        if path["ypn"] in ["ypN1", "ypN2"]:
            path["ypn_sites"] = st.multiselect("ypN陽性部位*", ["腎門部", "下大静脈周囲", "大動脈周囲", "傍大動脈", "大動脈静脈間", "総腸骨", "外腸骨", "内腸骨", "閉鎖", "その他"], disabled=L)
        else:
            path["ypn_sites"] = []
        path["lvi"] = st.radio("LVI*", ["なし", "あり", "評価不能"], index=None, horizontal=True, disabled=L)
        path["r0"] = st.radio("R0切除*", ["R0", "R1/R2", "評価不能"], index=None, horizontal=True, disabled=L)
        path["trg"] = st.radio("TRG*", ["TRG 1", "TRG 2", "TRG 3", "評価不能"], index=None, horizontal=True, disabled=L)
        if "評価不能" in [path.get("histology"), path.get("ypt"), path.get("ypn"), path.get("lvi"), path.get("r0"), path.get("trg")]:
            path["eval_failed_reason"] = st.text_area("病理評価不能理由*", disabled=L)
        else:
            path["eval_failed_reason"] = ""
    path["pcr"] = bool(path.get("ypt") == "ypT0" and (ln_dissection != "実施した" or path.get("ypn") == "ypN0"))
    if path["pcr"]:
        st.success("pCR定義に合致します（ypT0、郭清例ではypN0）。")
else:
    st.info("手術未施行のため病理項目はN/Aです。")

# ---------------- 30d ----------------
st.markdown('<div class="juog-header">4. 術後30日評価</div>', unsafe_allow_html=True)
visit_date_30 = st.date_input("30日評価日*", value=None, disabled=L)
window_deviation_reason = ""
reference_date = op_date if surgery_performed == "実施した" and op_date else planned_or_reference_date
if reference_date:
    wi = window_info(reference_date, 30, 14)
    st.info(f"計画書上の30日評価許容期間：{wi['min']:%Y/%m/%d} ～ {wi['max']:%Y/%m/%d}（30日±14日）")
    if visit_date_30:
        if wi["min"] <= visit_date_30 <= wi["max"]:
            st.success("評価日は30日±14日の範囲内です。")
        else:
            st.warning("評価日は30日±14日の範囲外です。データは入力できますが、理由を記録してください。")
            window_deviation_reason = st.text_area("30日評価時期の逸脱理由*", disabled=L)
        if surgery_performed == "実施した" and op_date and visit_date_30 < op_date + timedelta(days=30):
            st.warning("術後30日より前の評価です。主要安全性評価期間がまだ完了していないため、術後30日までに新規合併症が生じた場合は訂正報告してください。")

st.write("**30日評価 血液検査**")
day30_labs_raw = render_lab_panel("peri_day30_lab", required=True, disabled=L, columns=3)
day30_omission_reason = ""
if any(str(v).strip().upper() in {"NA", "N/A", "未実施", "欠測"} for v in day30_labs_raw.values()):
    day30_omission_reason = st.text_area("30日必須採血 欠測/未実施理由*", disabled=L)

cd_grade = "N/A"
cd_date = None
cd_detail = ""
cd_relation = "N/A"
renal_exception = False
renal_exception_detail = ""
if surgery_performed == "実施した":
    s1, s2 = st.columns(2)
    with s1:
        cd_grade = st.selectbox("術後30日以内の最高Clavien-Dindo Grade*", CD_OPTIONS, disabled=L)
        if cd_grade not in ["選択してください", "Grade 0"]:
            cd_date = st.date_input("当該合併症の発現日*", value=None, disabled=L)
            cd_detail = st.text_area("手術関連合併症の詳細*", disabled=L)
    with s2:
        if cd_grade not in ["選択してください", "Grade 0"]:
            cd_relation = st.selectbox("手術手技との因果関係*", ["選択してください", "関連する", "否定できない", "関連しない"], disabled=L)
            renal_exception = st.checkbox(
                "計画書の腎機能低下/透析除外規定に該当",
                value=False,
                disabled=L,
                help="RNUに伴う生理的腎機能低下、または術前から予測され同意済みの不可避な透析導入は主要合併症集計から除外します。",
            )
            if renal_exception:
                renal_exception_detail = st.text_area(
                    "腎機能低下/透析除外規定に該当する根拠*",
                    placeholder="例：術前単腎・高度CKDで術後透析導入が予測され、術前説明・同意済み。",
                    disabled=L,
                )

has_ctcae = st.checkbox("術後30日までに報告すべき薬剤関連等AE（CTCAE v6.0）がある", disabled=L)
ctcae_detail = st.text_area("CTCAE有害事象詳細*" if has_ctcae else "CTCAE有害事象詳細", disabled=L)

st.subheader("術後治療")
adj_plan = st.selectbox("術後治療・今後の予定*", POSTOP_TREATMENT_OPTIONS, disabled=L)
adj_detail = ""
adj_start = adj_end = None
adj_ongoing = False
if adj_plan not in ["選択してください", "無治療（経過観察）"]:
    if adj_plan in ["治験（TROP2標的ADC、その他）", "その他"]:
        adj_detail = st.text_input("治療詳細*", disabled=L)
    a1, a2 = st.columns(2)
    adj_start = a1.date_input("開始日/予定日*", value=None, disabled=L)
    adj_ongoing = a2.checkbox("継続中", disabled=L)
    if not adj_ongoing:
        adj_end = a2.date_input("終了日（予定なら空欄可）", value=None, disabled=L)

st.subheader("生存状況")
os1, os2 = st.columns(2)
with os1:
    status_alive = st.radio("生存状況*", ["生存", "死亡"], index=None, horizontal=True, disabled=L)
with os2:
    final_visit_date = death_date = None
    death_cause = ""
    if status_alive == "生存":
        final_visit_date = st.date_input("最終生存確認日*", value=None, disabled=L)
    elif status_alive == "死亡":
        death_date = st.date_input("死亡日*", value=None, disabled=L)
        death_cause = st.selectbox("死因*", ["選択してください", "癌死 (原疾患による)", "治療関連死", "他病死", "不明"], disabled=L)

# ---------------- validation ----------------
def validate_all():
    missing, errors, warnings = [], [], []
    if facility_name == "選択してください": missing.append("施設名")
    if not valid_registration_id(registration_id): errors.append("JUOG登録番号の形式が不正です（例：JUOG-001）")
    if not valid_email(reporter_email): errors.append("担当者メールアドレスが不正です")
    if submission_kind == "訂正報告" and not text(correction_reason): missing.append("訂正理由")
    if surgery_performed is None: missing.append("手術実施有無")
    if planned_or_reference_date is None: missing.append("手術日/予定日")
    if last_evp_date is None: missing.append("EVP最終投与日")

    if surgery_performed == "実施した":
        for v, label in [(op_admission_date, "入院日"), (op_date, "手術実施日"), (op_discharge_date, "退院日")]:
            if v is None: missing.append(label)
        if op_type == "選択してください": missing.append("術式")
        if op_type == "その他（プロトコル逸脱）" and not text(st.session_state.get("peri_op_other", "")): missing.append("実施術式詳細")
        if approach is None: missing.append("アプローチ")
        if op_completed is None: missing.append("手術完遂")
        if op_completed == "いいえ" and not text(op_incomplete_detail): missing.append("完遂不能理由")
        if op_time is None or op_time <= 0: missing.append("手術時間")
        if bleeding is None: missing.append("出血量")
        if eau_grade == "選択してください": missing.append("EAUiaiC")
        if eau_grade not in ["選択してください", "Grade 0"] and not text(eau_detail): missing.append("術中合併症詳細")
        if ln_dissection is None: missing.append("リンパ節郭清")
        if ln_dissection == "実施した" and not ln_range: missing.append("郭清範囲")
        if unrecovered_g2_relevant is None: missing.append("手術時未回復Grade 2以上AE")
        if unrecovered_g2_relevant == "あり" and not text(st.session_state.get("peri_g2_detail", "")): missing.append("未回復AE詳細")
        if op_date and last_evp_date:
            wd = (op_date - last_evp_date).days
            if (wd > 56 or wd < 28) and not text(protocol_deviation_reason): missing.append("手術時期の理由/逸脱理由")
        if op_admission_date and op_date and op_admission_date > op_date: errors.append("入院日が手術日より後です")
        if op_discharge_date and op_date and op_discharge_date < op_date: errors.append("退院日が手術日より前です")
        if op_type == "その他（プロトコル逸脱）": warnings.append("術式が計画書規定（RNU/尿管部分切除術）外です")
        if unrecovered_g2_relevant == "あり": warnings.append("手術時点で手術手技に影響しうるGrade 2以上未回復AEあり：プロトコル適合性を確認してください")

        # pathology
        for key, label in [("histology", "病理組織型"), ("ypt", "ypT"), ("lvi", "LVI"), ("r0", "R0"), ("trg", "TRG")]:
            if path.get(key) in [None, "", "選択してください"]: missing.append(label)
        if path.get("histology") == "その他" and not text(path.get("histology_other")): missing.append("病理組織型その他詳細")
        if path.get("subtype_presence") is None: missing.append("亜型/分化")
        if path.get("subtype_presence") == "あり" and not path.get("subtypes"): missing.append("亜型/分化の種類")
        if path.get("size_mm") is None: missing.append("病理最大径")
        if not path.get("locations"): missing.append("病理部位")
        if ln_dissection == "実施した" and path.get("ypn") in [None, "", "選択してください"]: missing.append("ypN")
        if path.get("ypn") in ["ypN1", "ypN2"] and not path.get("ypn_sites"): missing.append("ypN陽性部位")
        if "評価不能" in [path.get("histology"), path.get("ypt"), path.get("ypn"), path.get("lvi"), path.get("r0"), path.get("trg")] and not text(path.get("eval_failed_reason")): missing.append("病理評価不能理由")
    elif surgery_performed == "実施しなかった":
        if no_op_reason == "選択してください": missing.append("手術未施行理由")
        if no_op_reason == "その他" and not text(st.session_state.get("peri_noop_other", "")): missing.append("手術未施行理由その他詳細")

    # inpatient required only if surgery occurred
    inpatient_parsed, inpatient_errors, inpatient_warn = validate_lab_panel(inpatient_labs_raw, required=(surgery_performed == "実施した"))
    errors.extend([f"術後入院中血液検査：{x}" for x in inpatient_errors])
    warnings.extend([f"術後入院中血液検査：{x}" for x in inpatient_warn])
    if surgery_performed == "実施した" and inpatient_warn and not text(inpatient_omission_reason):
        missing.append("術後入院中必須採血の欠測/未実施理由")
    if surgery_performed == "実施した":
        for v, label in [(day0_sbp, "Day0収縮期血圧"), (day0_dbp, "Day0拡張期血圧"), (day0_pulse, "Day0脈拍"), (day0_temp, "Day0体温"), (inpatient_sbp, "入院中収縮期血圧"), (inpatient_dbp, "入院中拡張期血圧"), (inpatient_pulse, "入院中脈拍"), (inpatient_temp, "入院中体温")]:
            if v is None: missing.append(label)

    if visit_date_30 is None: missing.append("30日評価日")
    if reference_date and visit_date_30:
        wi = window_info(reference_date, 30, 14)
        if visit_date_30 < reference_date: errors.append("30日評価日が手術/予定日より前です")
        if visit_date_30 > today_jst(): errors.append("30日評価日が未来日です")
        if not (wi["min"] <= visit_date_30 <= wi["max"]):
            if not text(window_deviation_reason): missing.append("30日評価時期の逸脱理由")
            warnings.append("30日評価日が30日±14日の範囲外です")

    day30_parsed, day30_errors, day30_warn = validate_lab_panel(day30_labs_raw, required=True)
    errors.extend([f"30日血液検査：{x}" for x in day30_errors])
    warnings.extend([f"30日血液検査：{x}" for x in day30_warn])
    if day30_warn and not text(day30_omission_reason):
        missing.append("30日必須採血の欠測/未実施理由")

    if surgery_performed == "実施した":
        if cd_grade == "選択してください": missing.append("30日CD Grade")
        if cd_grade not in ["選択してください", "Grade 0"]:
            if cd_date is None: missing.append("合併症発現日")
            if not text(cd_detail): missing.append("合併症詳細")
            if cd_relation == "選択してください": missing.append("手術手技との因果関係")
            if renal_exception and not text(renal_exception_detail): missing.append("腎機能低下/透析除外規定の根拠")
            if op_date and cd_date:
                if cd_date < op_date: errors.append("合併症発現日が手術日より前です")
                if cd_date > op_date + timedelta(days=30): errors.append("30日CRFの手術関連合併症は術後30日以内の日付を入力してください")
    if has_ctcae and not text(ctcae_detail): missing.append("CTCAE有害事象詳細")

    if adj_plan == "選択してください": missing.append("術後治療")
    if adj_plan in ["治験（TROP2標的ADC、その他）", "その他"] and not text(adj_detail): missing.append("術後治療詳細")
    if adj_plan not in ["選択してください", "無治療（経過観察）"] and adj_start is None: missing.append("術後治療開始日")
    if adj_start and adj_end and adj_end < adj_start: errors.append("術後治療終了日が開始日より前です")

    if status_alive is None: missing.append("生存状況")
    elif status_alive == "生存":
        if final_visit_date is None: missing.append("最終生存確認日")
        if cd_grade == "Grade V": errors.append("CD Grade Vですが生存状況が『生存』です")
    else:
        if death_date is None: missing.append("死亡日")
        if death_cause == "選択してください": missing.append("死因")
        if death_date and reference_date and death_date < reference_date: errors.append("死亡日が手術/予定日より前です")

    return unique_messages(missing), unique_messages(errors), unique_messages(warnings), inpatient_parsed, day30_parsed

missing, errors, warnings, inpatient_parsed, day30_parsed = validate_all()

st.markdown('<div class="juog-header">5. 送信</div>', unsafe_allow_html=True)
if missing:
    st.warning("未入力：" + " / ".join(missing))
if errors:
    st.error("入力エラー：\n" + "\n".join([f"・{x}" for x in errors]))
if warnings:
    st.info("確認事項：\n" + "\n".join([f"・{x}" for x in warnings]))

if st.button("🚀 事務局へ確定送信", type="primary", use_container_width=True, disabled=L):
    if missing or errors:
        st.error("未入力または入力エラーを修正してください。")
    else:
        reg_ok, reg_message = validate_registry_id(registration_id, facility_code)
        if reg_ok is False:
            st.error(reg_message)
        else:
            if reg_ok is None:
                st.warning(reg_message)
            major30 = bool(
                surgery_performed == "実施した"
                and cd_grade in CD_MAJOR
                and cd_relation in ["関連する", "否定できない"]
                and not renal_exception
            )
            meta = make_submission_metadata(
                "perioperative_30d", "30d", registration_id, facility_code, facility_name, reporter_email,
                submission_kind, correction_reason,
            )
            data = {
                "surgery_performed": surgery_performed,
                "reference_date": date_str(planned_or_reference_date),
                "last_evp_date": date_str(last_evp_date),
                "admission_date": date_str(op_admission_date),
                "operation_date": date_str(op_date),
                "discharge_date": date_str(op_discharge_date),
                "operation_type": op_type,
                "operation_type_other": text(st.session_state.get("peri_op_other", "")),
                "approach": approach,
                "operation_completed": op_completed,
                "incomplete_reason": text(op_incomplete_detail),
                "operation_time_min": op_time,
                "blood_loss_ml": bleeding,
                "eauiaic": eau_grade,
                "eauiaic_detail": text(eau_detail),
                "ln_dissection": ln_dissection,
                "ln_range": ln_range,
                "unrecovered_grade2plus_relevant_ae": unrecovered_g2_relevant,
                "unrecovered_ae_detail": text(st.session_state.get("peri_g2_detail", "")),
                "surgery_timing_reason_or_deviation": text(protocol_deviation_reason),
                "no_operation_reason": no_op_reason if surgery_performed == "実施しなかった" else "",
                "no_operation_other": text(st.session_state.get("peri_noop_other", "")),
                "day0_vitals": {"sbp": day0_sbp, "dbp": day0_dbp, "pulse": day0_pulse, "temperature": day0_temp},
                "inpatient_vitals": {"sbp": inpatient_sbp, "dbp": inpatient_dbp, "pulse": inpatient_pulse, "temperature": inpatient_temp},
                "inpatient_labs": inpatient_parsed,
                "inpatient_required_test_omission_reason": text(inpatient_omission_reason),
                "pathology": path if surgery_performed == "実施した" else {},
                "day30_visit_date": date_str(visit_date_30),
                "day30_window_deviation_reason": text(window_deviation_reason),
                "day30_labs": day30_parsed,
                "day30_required_test_omission_reason": text(day30_omission_reason),
                "cd_grade_30": cd_grade,
                "cd_event_date_30": date_str(cd_date),
                "cd_detail_30": text(cd_detail),
                "cd_surgery_relation": cd_relation,
                "renal_exception": renal_exception,
                "renal_exception_detail": text(renal_exception_detail),
                "major_surgery_related_complication_30d": major30,
                "ctcae_event": has_ctcae,
                "ctcae_detail": text(ctcae_detail),
                "postop_treatment": adj_plan,
                "postop_treatment_detail": text(adj_detail),
                "postop_treatment_start": date_str(adj_start),
                "postop_treatment_end": date_str(adj_end),
                "postop_treatment_ongoing": adj_ongoing,
                "vital_status": status_alive,
                "last_alive_date": date_str(final_visit_date),
                "death_date": date_str(death_date),
                "death_cause": death_cause,
            }
            payload = {**meta, "data": data}
            report = f"""【JUOG 周術期・30日報告】
JUOG登録番号: {registration_id}
施設: {facility_name}
報告種別: {submission_kind}
訂正理由: {text(correction_reason) or 'N/A'}
手術実施: {surgery_performed}
手術日/予定日: {date_str(planned_or_reference_date)}
実施術式: {op_type if surgery_performed == '実施した' else 'N/A'}
手術完遂: {op_completed if surgery_performed == '実施した' else 'N/A'}
EAUiaiC: {eau_grade if surgery_performed == '実施した' else 'N/A'}
R0: {path.get('r0', 'N/A') if surgery_performed == '実施した' else 'N/A'}
pCR: {'はい' if path.get('pcr') else 'いいえ/N/A'}

30日評価日: {date_str(visit_date_30)}
30日最高CD Grade: {cd_grade}
30日主要手術関連合併症（定義該当）: {'はい' if major30 else 'いいえ'}
生存状況: {status_alive}
死亡日: {date_str(death_date) or 'N/A'}
術後治療: {adj_plan}

{json_block(payload)}
"""
            sent, send_err = send_email(f"【JUOG CRF】【perioperative_30d】【{registration_id}】", report, reporter_email)
            if sent:
                st.session_state.peri_sent = True
                st.success("確定送信しました。")
                st.balloons()
                if warnings:
                    st.warning("確認事項もJSON内に保存されています。")
                st.rerun()
            else:
                st.error("メール送信に失敗しました。データは送信されていません。事務局へ連絡してください。")
                print(f"[JUOG perioperative] email failed: {send_err}")
