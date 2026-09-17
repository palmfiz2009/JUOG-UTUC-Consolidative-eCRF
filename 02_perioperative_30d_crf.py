from __future__ import annotations

from datetime import timedelta

import streamlit as st

from juog_common import (
    CD_MAJOR,
    CD_OPTIONS,
    LAB_FIELDS,
    POSTOP_TREATMENT_OPTIONS,
    capture_draft_state,
    clear_session_state_prefixes,
    date_str,
    delete_crf_draft,
    get_crf_draft,
    json_block,
    make_submission_metadata,
    render_facility,
    render_submission_kind,
    restore_draft_state,
    save_crf_draft,
    save_crf_payload,
    send_email,
    text,
    today_jst,
    unique_messages,
    valid_email,
    valid_registration_id,
    validate_lab_panel,
    validate_registry_id,
    validate_vitals,
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

def render_optional_lab_panel(prefix: str, disabled=False, columns=3):
    """Optional routine-care labs: measured values only; unmeasured items stay blank."""
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
    """Reuse numeric/range checks while treating blank/NA as ordinary missingness."""
    parsed, errors, _warnings = validate_lab_panel(raw_values, required=False)
    clean_errors = [
        x.replace("数値またはNAで入力してください", "数値で入力してください（未測定・欠測は空欄）")
        for x in errors
    ]
    return parsed, clean_errors


st.title("JUOG UTUC_Consolidative 周術期・術後30日CRF")
st.caption("主要評価項目の手術関連合併症は『手術終了時〜術後30日目』で判定します。30日訪問自体は30日±14日を許容します。")

if "peri_sent" not in st.session_state:
    st.session_state.peri_sent = False

if st.session_state.peri_sent:
    sent_id = st.session_state.get("peri_sent_registration_id", "")
    sent_version = st.session_state.get("peri_sent_version", "")
    st.success("送信が完了しました。")
    if sent_id:
        st.write(f"**JUOG登録番号：{sent_id}**")
    if sent_version:
        st.caption(f"周術期・術後30日CRFを保存しました（version {sent_version}）。")
    else:
        st.caption("周術期・術後30日CRFを保存しました。")
    if st.session_state.get("peri_sent_had_warnings"):
        st.info("確認事項も中央データに保存されています。")
    if st.session_state.get("peri_sent_email_failed"):
        st.warning("中央Google Sheetへの保存は完了していますが、通知メール送信に失敗しました。再入力はせず事務局へ連絡してください。")
    if st.session_state.get("peri_sent_draft_delete_failed"):
        st.info("確定送信は完了していますが、仮保存データの削除確認ができませんでした。確定データには影響ありません。")
    st.caption("訂正する場合はページを再読み込みし、「訂正報告」を選択して送信してください。")
    st.stop()

if st.session_state.get("draft30_loaded_at"):
    st.success(f"仮保存データを読み込みました（最終保存：{st.session_state['draft30_loaded_at']}）。")
    st.session_state.pop("draft30_loaded_at", None)

draft_tool_col1, draft_tool_col2, _draft_tool_spacer = st.columns([0.9, 0.9, 6.2])
with draft_tool_col1:
    draft_clicked = st.button("💾 仮保存", key="draft30_save_button", disabled=False)
with draft_tool_col2:
    with st.popover("↩ 再開"):
        st.caption("仮保存した内容を読み込みます。")
        draft_lookup_id = st.text_input(
            "JUOG登録番号",
            placeholder="JUOG-001",
            key="draft30_lookup_id",
        ).strip().upper()
        if st.button("読み込む", key="draft30_load_button", use_container_width=True):
            if not valid_registration_id(draft_lookup_id):
                st.error("JUOG登録番号を正しく入力してください（例：JUOG-001）。")
            else:
                draft_result = get_crf_draft(draft_lookup_id, "perioperative_30d", "30d")
                if not draft_result.get("ok"):
                    st.error("仮保存データを取得できませんでした：" + (draft_result.get("message") or draft_result.get("error") or "unknown error"))
                elif not draft_result.get("source_found"):
                    st.info("このJUOG登録番号の仮保存データはありません。")
                else:
                    clear_session_state_prefixes(("peri_", "widget_peri_"))
                    restore_draft_state(draft_result.get("draft_state") or {})
                    if not st.session_state.get("peri_facility") and draft_result.get("facility_name"):
                        st.session_state["peri_facility"] = draft_result.get("facility_name")
                    st.session_state["peri_registration_id"] = draft_lookup_id
                    st.session_state["draft30_loaded_at"] = draft_result.get("updated_at") or "時刻不明"
                    st.rerun()

L = False

# ---------------- basic ----------------
st.markdown('<div class="juog-header">1. 基本情報</div>', unsafe_allow_html=True)
b1, b2 = st.columns(2)
with b1:
    facility_code, facility_name = render_facility(key="peri_facility", disabled=L)
    registration_id = st.text_input("JUOG登録番号*", placeholder="JUOG-001", key="peri_registration_id", disabled=L).strip().upper()
    reporter_email = st.text_input("担当者メールアドレス*", key="peri_reporter_email", disabled=L)
with b2:
    submission_kind, correction_reason = render_submission_kind("peri", disabled=L)
    surgery_performed = st.radio(
        "Consolidative surgeryの実施*",
        ["実施した", "実施しなかった"],
        index=None,
        horizontal=True,
        disabled=L,
        key="peri_surgery_performed",
    )

# ---------------- perioperative ----------------
st.markdown('<div class="juog-header">2. 手術・入院経過</div>', unsafe_allow_html=True)

last_evp_date = None
planned_or_reference_date = None
protocol_deviation_reason = ""

op_admission_date = op_date = op_discharge_date = None
initial_hospital_outcome = None
readmission_30d = None
readmission_date = None
readmission_reason = ""
readmission_day30_status = None
readmission_discharge_date = None

op_type = op_completed = None
approaches = []
approach_pattern = ""
conversion_reason = ""
op_incomplete_detail = ""
op_time = bleeding = None
eau_grade = "選択してください"
eau_detail = ""
ln_dissection = None
ln_range = []
unrecovered_g2_relevant = None

no_op_reason = "選択してください"

day0_sbp = day0_dbp = day0_pulse = day0_temp = None
discharge_sbp = discharge_dbp = discharge_pulse = discharge_temp = None
discharge_lab_available = None
discharge_lab_date = None
discharge_labs_raw = {}

if surgery_performed == "実施した":
    st.markdown("#### 手術情報")
    d1, d2, d3 = st.columns(3)
    with d1:
        last_evp_date = st.date_input("EVP最終投与日*", value=None, key="peri_last_evp_date", disabled=L)
    with d2:
        op_admission_date = st.date_input("入院日*", value=None, key="peri_op_admission_date", disabled=L)
    with d3:
        op_date = st.date_input("手術実施日*", value=None, key="peri_op_date", disabled=L)
    planned_or_reference_date = op_date

    s1, s2 = st.columns(2)
    with s1:
        op_type = st.selectbox(
            "術式*",
            ["選択してください", "根治的腎尿管全摘除術", "尿管部分切除術", "その他（プロトコル逸脱）"],
            key="peri_op_type",
            disabled=L,
        )
        if op_type == "その他（プロトコル逸脱）":
            st.text_input("実施術式の詳細*", key="peri_op_other", disabled=L)

        approaches = st.multiselect(
            "実際の手術アプローチ*",
            ["開腹", "腹腔鏡", "ロボット支援"],
            key="peri_approaches",
            disabled=L,
            help="使用したアプローチをすべて選択してください。例：腎側を腹腔鏡、尿管膀胱処理を開腹で行った場合は「腹腔鏡」「開腹」の両方を選択します。",
        )
        if len(approaches) >= 2:
            approach_pattern = st.radio(
                "複数アプローチの扱い*",
                ["予定されたハイブリッド", "予定外のアプローチ変更（conversion）"],
                index=None,
                horizontal=True,
                key="peri_approach_pattern",
                disabled=L,
                help="予定どおり複数アプローチを併用した場合は「予定されたハイブリッド」。術中判断で予定外に変更した場合はconversionです。",
            )
            if approach_pattern == "予定外のアプローチ変更（conversion）":
                conversion_reason = st.text_area("conversionの理由*", key="peri_conversion_reason", disabled=L)
        elif len(approaches) == 1:
            approach_pattern = "単一アプローチ"

        op_completed = st.radio(
            "予定した原発巣切除を完遂*",
            ["はい", "いいえ"],
            index=None,
            horizontal=True,
            key="peri_op_completed",
            disabled=L,
        )
        if op_completed == "いいえ":
            op_incomplete_detail = st.text_area("完遂不能理由*", key="peri_op_incomplete_detail", disabled=L)

    with s2:
        op_time = st.number_input("手術時間 (分)*", min_value=0, value=None, step=1, key="peri_op_time", disabled=L)
        bleeding = st.number_input("出血量 (mL)*", min_value=0, value=None, step=1, key="peri_bleeding", disabled=L)

        eau_grade = st.selectbox(
            "術中合併症 (EAUiaiC)*",
            ["選択してください", "Grade 0", "Grade 1", "Grade 2", "Grade 3", "Grade 4A", "Grade 4B", "Grade 5A", "Grade 5B"],
            key="peri_eau_grade",
            disabled=L,
            help=(
                "EAU Intraoperative Adverse Incident Classification。\n"
                "Grade 0：予定手順からの逸脱なし。\n"
                "Grade 1：軽微な追加・代替処置。\n"
                "Grade 2：主要な追加・代替処置を要するが、直ちに生命を脅かさない。\n"
                "Grade 3：主要な追加・代替処置を要し、直ちに生命を脅かす。\n"
                "Grade 4A：臓器の一部または全摘出を要する重大事象。\n"
                "Grade 4B：予定手術を完了できない、または予定外のストーマ等を要する。\n"
                "Grade 5A：部位・側・患者間違い、または同意のない手術。\n"
                "Grade 5B：術中死亡。"
            ),
        )
        if eau_grade not in ["選択してください", "Grade 0"]:
            eau_detail = st.text_area("術中合併症の詳細*", key="peri_eau_detail", disabled=L)

        ln_dissection = st.radio(
            "リンパ節郭清*",
            ["実施した", "実施しなかった"],
            index=None,
            horizontal=True,
            key="peri_ln_dissection",
            disabled=L,
        )
        if ln_dissection == "実施した":
            ln_range = st.multiselect(
                "郭清範囲*",
                ["腎門部", "下大静脈周囲", "大動脈周囲", "傍大動脈", "大動脈静脈間", "総腸骨", "外腸骨", "内腸骨", "閉鎖", "その他"],
                key="peri_ln_range",
                disabled=L,
            )

        unrecovered_g2_relevant = st.radio(
            "手術時 Grade 2以上の未回復AE（手術手技に影響するもの）*",
            ["なし", "あり"],
            index=None,
            horizontal=True,
            key="peri_unrecovered_g2_relevant",
            disabled=L,
            help="脱毛・色素沈着など、手術手技に影響しない事象は除外します。",
        )
        if unrecovered_g2_relevant == "あり":
            st.text_area("未回復AEの詳細*", key="peri_g2_detail", disabled=L)

    if last_evp_date and op_date:
        washout_days = (op_date - last_evp_date).days
        st.caption(f"EVP最終投与から手術まで：{washout_days}日")
        if 28 <= washout_days <= 56:
            st.success("原則4–8週の範囲内です。")
        elif 57 <= washout_days <= 84:
            st.warning("8週超〜12週以内です。理由を記録してください。")
            protocol_deviation_reason = st.text_area("8週超となった理由*", key="peri_protocol_deviation_reason", disabled=L)
        else:
            st.warning("4–12週の範囲外です。理由を記録してください。")
            protocol_deviation_reason = st.text_area("手術時期の理由／プロトコル逸脱理由*", key="peri_protocol_deviation_reason", disabled=L)

    st.markdown("#### 術後入院経過")
    h1, h2 = st.columns(2)
    with h1:
        initial_hospital_outcome = st.radio(
            "初回手術入院の転帰*",
            ["退院済み", "入院継続中", "初回入院中に死亡"],
            index=None,
            key="peri_initial_hospital_outcome",
            disabled=L,
            help="このCRF入力時点での初回手術入院の転帰を選択してください。",
        )
    with h2:
        if initial_hospital_outcome == "退院済み":
            op_discharge_date = st.date_input("初回退院日*", value=None, key="peri_op_discharge_date", disabled=L)

    if initial_hospital_outcome == "退院済み" and op_discharge_date:
        if op_date and op_discharge_date > op_date + timedelta(days=30):
            readmission_30d = "N/A（術後30日まで初回入院）"
            st.caption("初回退院が術後30日を超えているため、術後30日以内の再入院はN/Aです。")
        else:
            readmission_30d = st.radio(
                "初回退院後、術後30日以内の再入院*",
                ["なし", "あり"],
                index=None,
                horizontal=True,
                key="peri_readmission_30d",
                disabled=L,
            )
            if readmission_30d == "あり":
                r1, r2 = st.columns(2)
                with r1:
                    readmission_date = st.date_input("最初の再入院日*", value=None, key="peri_readmission_date", disabled=L)
                    readmission_reason = st.text_area(
                        "再入院理由*",
                        help="複数回の再入院がある場合は、理由欄にすべて記載してください。",
                        key="peri_readmission_reason",
                        disabled=L,
                    )
                with r2:
                    readmission_day30_status = st.radio(
                        "再入院後の転帰*",
                        ["再退院済み", "再入院継続中", "再入院中に死亡"],
                        index=None,
                        key="peri_readmission_day30_status",
                        disabled=L,
                    )
                    if readmission_day30_status == "再退院済み":
                        readmission_discharge_date = st.date_input("再退院日*", value=None, key="peri_readmission_discharge_date", disabled=L)

    st.markdown("#### 術直後・退院時データ")
    st.caption("術直後バイタル：術後管理場所（病棟・HCU・ICU・PACU等）到着時の最初の記録値。")
    v1, v2, v3, v4 = st.columns(4)
    with v1:
        day0_sbp = st.number_input("到着時 収縮期血圧", min_value=0, value=None, step=1, key="peri_day0_sbp", disabled=L, help="mmHg")
    with v2:
        day0_dbp = st.number_input("到着時 拡張期血圧", min_value=0, value=None, step=1, key="peri_day0_dbp", disabled=L, help="mmHg")
    with v3:
        day0_pulse = st.number_input("到着時 脈拍", min_value=0, value=None, step=1, key="peri_day0_pulse", disabled=L, help="/min")
    with v4:
        day0_temp = st.number_input("到着時 体温", min_value=30.0, max_value=45.0, value=None, step=0.1, key="peri_day0_temp", disabled=L, help="℃")

    if initial_hospital_outcome == "退院済み":
        st.caption("退院時バイタル：初回退院当日または退院前24時間以内で、退院時に最も近い定時測定値。")
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            discharge_sbp = st.number_input("退院時 収縮期血圧", min_value=0, value=None, step=1, key="peri_discharge_sbp", disabled=L, help="mmHg")
        with d2:
            discharge_dbp = st.number_input("退院時 拡張期血圧", min_value=0, value=None, step=1, key="peri_discharge_dbp", disabled=L, help="mmHg")
        with d3:
            discharge_pulse = st.number_input("退院時 脈拍", min_value=0, value=None, step=1, key="peri_discharge_pulse", disabled=L, help="/min")
        with d4:
            discharge_temp = st.number_input("退院時 体温", min_value=30.0, max_value=45.0, value=None, step=0.1, key="peri_discharge_temp", disabled=L, help="℃")

        st.markdown("**退院前最終採血**")
        st.caption("手術後〜初回退院日の採血のうち、退院日に最も近い採血を入力してください。研究目的の追加採血は不要です。")
        discharge_lab_available = st.radio(
            "退院前採血*",
            ["あり", "なし"],
            index=None,
            horizontal=True,
            key="peri_discharge_lab_available",
            disabled=L,
        )
        if discharge_lab_available == "あり":
            discharge_lab_date = st.date_input("採血日*", value=None, key="peri_discharge_lab_date", disabled=L)
            discharge_labs_raw = render_optional_lab_panel("peri_discharge_lab", disabled=L, columns=3)
    elif initial_hospital_outcome == "入院継続中":
        st.caption("入院継続中のため、退院時バイタル・退院前採血は未入力で構いません。")
    elif initial_hospital_outcome == "初回入院中に死亡":
        st.caption("初回入院中死亡のため、退院時バイタル・退院前採血はN/Aです。")

elif surgery_performed == "実施しなかった":
    st.markdown("#### 手術未施行")
    n1, n2 = st.columns(2)
    with n1:
        last_evp_date = st.date_input("EVP最終投与日*", value=None, key="peri_last_evp_date", disabled=L)
        planned_or_reference_date = st.date_input("手術予定日*", value=None, key="peri_planned_or_reference_date", disabled=L)
    with n2:
        no_op_reason = st.selectbox(
            "手術未施行理由*",
            ["選択してください", "病勢進行", "EVP関連有害事象", "中央MDT/手術適応変更", "同意撤回", "患者希望", "その他"],
            key="peri_no_op_reason",
            disabled=L,
        )
        if no_op_reason == "その他":
            st.text_area("手術未施行理由 その他詳細*", key="peri_noop_other", disabled=L)
else:
    st.caption("Consolidative surgeryの実施有無を選択すると、必要な項目が表示されます。")

# ---------------- pathology ----------------
st.markdown('<div class="juog-header">3. 術後病理</div>', unsafe_allow_html=True)
path = {}
if surgery_performed == "実施した":
    p1, p2 = st.columns(2)
    with p1:
        path["histology"] = st.selectbox("組織型*", ["選択してください", "Urothelial carcinoma", "Urothelial carcinoma（亜型・分化を含む）", "その他", "評価不能"], key="peri_path_histology", disabled=L)
        if path["histology"] == "その他":
            path["histology_other"] = st.text_input("組織型 その他詳細*", key="peri_path_histology_other", disabled=L)
        else:
            path["histology_other"] = ""
        path["subtype_presence"] = st.radio("亜型/分化の有無*", ["なし", "あり"], index=None, horizontal=True, key="peri_path_subtype_presence", disabled=L)
        if path["subtype_presence"] == "あり":
            path["subtypes"] = st.multiselect("亜型/分化*", ["Nested", "Micropapillary", "Plasmacytoid", "Sarcomatoid", "Squamous differentiation", "Glandular differentiation", "その他"], key="peri_path_subtypes", disabled=L)
        else:
            path["subtypes"] = []
        path["size_mm"] = st.number_input("病理最大径 (mm)*", min_value=0.0, value=None, step=0.1, key="peri_path_size_mm", disabled=L)
        path["locations"] = st.multiselect("病理部位*", ["腎盂", "上部尿管", "中部尿管", "下部尿管", "その他"], key="peri_path_locations", disabled=L)
    with p2:
        path["ypt"] = st.selectbox("ypT*", ["選択してください", "ypT0", "ypTa", "ypTis", "ypT1", "ypT2", "ypT3", "ypT4", "評価不能"], key="peri_path_ypt", disabled=L)
        if ln_dissection == "実施した":
            path["ypn"] = st.selectbox(
                "ypN*",
                ["選択してください", "ypN0", "ypN1", "ypN2", "ypNX（評価不能）"],
                key="peri_path_ypn",
                disabled=L,
            )
        else:
            path["ypn"] = "ypNX（郭清なし）"
            st.info("リンパ節郭清なしのためypNは ypNX として記録します。")
        if path["ypn"] in ["ypN1", "ypN2"]:
            path["ypn_sites"] = st.multiselect("ypN陽性部位*", ["腎門部", "下大静脈周囲", "大動脈周囲", "傍大動脈", "大動脈静脈間", "総腸骨", "外腸骨", "内腸骨", "閉鎖", "その他"], key="peri_path_ypn_sites", disabled=L)
        else:
            path["ypn_sites"] = []
        path["lvi"] = st.radio("LVI*", ["なし", "あり", "評価不能"], index=None, horizontal=True, key="peri_path_lvi", disabled=L)
        path["r0"] = st.radio("R0切除*", ["R0", "R1/R2", "評価不能"], index=None, horizontal=True, key="peri_path_r0", disabled=L)
        path["trg"] = st.radio(
            "原発巣 TRG*",
            ["TRG 1", "TRG 2", "TRG 3", "評価不能"],
            index=None,
            horizontal=True,
            key="peri_path_trg",
            disabled=L,
            help=(
                "TRG評価は病理部へ依頼してください。各施設の病理診断科でVoskuilen分類に基づき、原発巣を評価してください。\n"
                "TRG 1（Complete Response）：生存がん細胞を認めない。\n"
                "TRG 2（Strong Response）：残存生存がん細胞が腫瘍床の50%未満。\n"
                "TRG 3（Weak / No Response）：残存生存がん細胞が50%以上、または治療効果を認めない。"
            ),
        )
        if (path.get("ypn") == "ypNX（評価不能）" or "評価不能" in [path.get("histology"), path.get("ypt"), path.get("lvi"), path.get("r0"), path.get("trg")]):
            path["eval_failed_reason"] = st.text_area("病理評価不能理由*", key="peri_path_eval_failed_reason", disabled=L)
        else:
            path["eval_failed_reason"] = ""
    # Main pCR endpoint accepts ypT0N0 and ypT0Nx.
    path["pcr"] = bool(
        path.get("ypt") == "ypT0"
        and path.get("ypn") in {"ypN0", "ypNX（郭清なし）", "ypNX（評価不能）"}
    )
    path["pcr_ypt0n0"] = bool(path.get("ypt") == "ypT0" and path.get("ypn") == "ypN0")
else:
    st.info("手術未施行のため病理項目はN/Aです。")

# ---------------- 30d ----------------
st.markdown('<div class="juog-header">4. 術後30日評価</div>', unsafe_allow_html=True)
visit_date_30 = st.date_input("30日評価日*", value=None, key="peri_visit_date_30", disabled=L)
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
            window_deviation_reason = st.text_area("30日評価時期の逸脱理由*", key="peri_window_deviation_reason", disabled=L)
        if surgery_performed == "実施した" and op_date and visit_date_30 < op_date + timedelta(days=30):
            st.warning("術後30日より前の評価です。主要安全性評価期間がまだ完了していないため、術後30日までに新規合併症が生じた場合は訂正報告してください。")

st.write("**30日評価 血液検査（必須）**")
st.caption(
    "30日±14日の期間内で、術後30日目に最も近い採血結果を入力してください。"
)
day30_lab_available = "あり"
day30_lab_date = st.date_input("30日評価に用いた採血日*", value=None, key="peri_day30_lab_date", disabled=L)
day30_labs_raw = render_optional_lab_panel("peri_day30_lab", disabled=L, columns=3)

cd_grade = "N/A"
cd_date = None
cd_detail = ""
cd_relation = "N/A"
renal_exception = False
renal_exception_detail = ""
if surgery_performed == "実施した":
    s1, s2 = st.columns(2)
    with s1:
        cd_grade = st.selectbox("術後30日以内の最高Clavien-Dindo Grade*", CD_OPTIONS, key="peri_cd_grade", disabled=L)
        if cd_grade not in ["選択してください", "Grade 0"]:
            cd_date = st.date_input("当該合併症の発現日*", value=None, key="peri_cd_date", disabled=L)
            cd_detail = st.text_area("手術関連合併症の詳細*", key="peri_cd_detail", disabled=L)
    with s2:
        if cd_grade not in ["選択してください", "Grade 0"]:
            cd_relation = st.selectbox("手術手技との因果関係*", ["選択してください", "関連する", "否定できない", "関連しない"], key="peri_cd_relation", disabled=L)
            renal_exception = st.checkbox(
                "計画書の腎機能低下/透析除外規定に該当",
                value=False,
                key="peri_renal_exception",
                disabled=L,
                help="RNUに伴う生理的腎機能低下、または術前から予測され同意済みの不可避な透析導入は主要合併症集計から除外します。",
            )
            if renal_exception:
                renal_exception_detail = st.text_area(
                    "腎機能低下/透析除外規定に該当する根拠*",
                    placeholder="例：術前単腎・高度CKDで術後透析導入が予測され、術前説明・同意済み。",
                    key="peri_renal_exception_detail",
                    disabled=L,
                )

has_ctcae = st.checkbox("術後30日までに報告すべき薬剤関連等AE（CTCAE v6.0）がある", key="peri_has_ctcae", disabled=L)
ctcae_detail = ""
if has_ctcae:
    ctcae_detail = st.text_area("CTCAE有害事象詳細*", key="peri_ctcae_detail", disabled=L)

st.subheader("術後治療")
adj_plan = st.selectbox("術後治療・今後の予定*", POSTOP_TREATMENT_OPTIONS, key="peri_adj_plan", disabled=L)
adj_detail = ""
adj_start = adj_end = None
adj_ongoing = False
if adj_plan not in ["選択してください", "無治療（経過観察）"]:
    if adj_plan in ["治験（TROP2標的ADC、その他）", "その他"]:
        adj_detail = st.text_input("治療詳細*", key="peri_adj_detail", disabled=L)
    a1, a2 = st.columns(2)
    adj_start = a1.date_input("開始日/予定日*", value=None, key="peri_adj_start", disabled=L)
    adj_ongoing = a2.checkbox("継続中", key="peri_adj_ongoing", disabled=L)
    if not adj_ongoing:
        adj_end = a2.date_input("終了日（予定なら空欄可）", value=None, key="peri_adj_end", disabled=L)

st.subheader("生存状況")
os1, os2 = st.columns(2)
with os1:
    status_alive = st.radio("生存状況*", ["生存", "死亡"], index=None, horizontal=True, key="peri_status_alive", disabled=L)
with os2:
    final_visit_date = death_date = None
    death_cause = ""
    if status_alive == "生存":
        final_visit_date = st.date_input("最終生存確認日*", value=None, key="peri_final_visit_date", disabled=L)
    elif status_alive == "死亡":
        death_date = st.date_input("死亡日*", value=None, key="peri_death_date", disabled=L)
        death_cause = st.selectbox("死因*", ["選択してください", "癌死 (原疾患による)", "治療関連死", "他病死", "不明"], key="peri_death_cause", disabled=L)

# ---------------- validation ----------------
def validate_all():
    missing, errors, warnings = [], [], []
    if facility_name == "選択してください": missing.append("施設名")
    if not registration_id:
        missing.append("JUOG登録番号")
    elif not valid_registration_id(registration_id):
        errors.append("JUOG登録番号の形式が不正です（例：JUOG-001）")
    if not text(reporter_email):
        missing.append("担当者メールアドレス")
    elif not valid_email(reporter_email):
        errors.append("担当者メールアドレスが不正です")
    if submission_kind == "訂正報告" and not text(correction_reason): missing.append("訂正理由")
    if surgery_performed is None:
        missing.append("手術実施有無")
    elif planned_or_reference_date is None:
        missing.append("手術実施日" if surgery_performed == "実施した" else "手術予定日")
    if surgery_performed is not None and last_evp_date is None:
        missing.append("EVP最終投与日")

    if surgery_performed == "実施した":
        for v, label in [(op_admission_date, "入院日"), (op_date, "手術実施日")]:
            if v is None: missing.append(label)
        if initial_hospital_outcome is None:
            missing.append("初回手術入院の転帰")
        if initial_hospital_outcome == "退院済み" and op_discharge_date is None:
            missing.append("初回退院日")
        if op_type == "選択してください": missing.append("術式")
        if op_type == "その他（プロトコル逸脱）" and not text(st.session_state.get("peri_op_other", "")): missing.append("実施術式詳細")
        if not approaches: missing.append("アプローチ")
        if len(approaches) >= 2 and approach_pattern == "": missing.append("複数アプローチの区分")
        if approach_pattern == "予定外のアプローチ変更（conversion）" and not text(conversion_reason): missing.append("conversionの理由")
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
            if last_evp_date > op_date: errors.append("EVP最終投与日が手術実施日より後です")
            if (wd > 56 or wd < 28) and not text(protocol_deviation_reason): missing.append("手術時期の理由/逸脱理由")
        if op_admission_date and op_date and op_admission_date > op_date: errors.append("入院日が手術日より後です")
        if op_discharge_date and op_date and op_discharge_date < op_date:
            errors.append("初回退院日が手術日より前です")
        if op_discharge_date and op_admission_date and op_discharge_date < op_admission_date:
            errors.append("初回退院日が入院日より前です")

        if initial_hospital_outcome == "退院済み":
            if op_discharge_date and op_date and op_discharge_date <= op_date + timedelta(days=30) and readmission_30d is None:
                missing.append("術後30日以内の再入院")
            elif readmission_30d == "あり":
                if readmission_date is None:
                    missing.append("再入院日")
                if not text(readmission_reason):
                    missing.append("再入院理由")
                if readmission_day30_status is None:
                    missing.append("再入院後の転帰")
                if readmission_day30_status == "再退院済み" and readmission_discharge_date is None:
                    missing.append("再退院日")
                if readmission_date and op_discharge_date and readmission_date < op_discharge_date:
                    errors.append("再入院日が初回退院日より前です")
                if readmission_date and op_date and readmission_date > op_date + timedelta(days=30):
                    errors.append("再入院日は術後30日以内の日付を入力してください")
                if readmission_discharge_date and readmission_date and readmission_discharge_date < readmission_date:
                    errors.append("再退院日が再入院日より前です")
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
        if path.get("ypn") in [None, "", "選択してください"]: missing.append("ypN")
        if path.get("ypn") in ["ypN1", "ypN2"] and not path.get("ypn_sites"): missing.append("ypN陽性部位")
        if (path.get("ypn") == "ypNX（評価不能）" or "評価不能" in [path.get("histology"), path.get("ypt"), path.get("lvi"), path.get("r0"), path.get("trg")]) and not text(path.get("eval_failed_reason")): missing.append("病理評価不能理由")
    elif surgery_performed == "実施しなかった":
        if no_op_reason == "選択してください": missing.append("手術未施行理由")
        if no_op_reason == "その他" and not text(st.session_state.get("peri_noop_other", "")): missing.append("手術未施行理由その他詳細")

    discharge_labs_parsed, discharge_labs_errors = validate_optional_lab_panel(discharge_labs_raw)
    errors.extend([f"退院前最終採血：{x}" for x in discharge_labs_errors])
    if surgery_performed == "実施した":
        for v, label in [
            (day0_sbp, "術後管理場所到着時 収縮期血圧"),
            (day0_dbp, "術後管理場所到着時 拡張期血圧"),
            (day0_pulse, "術後管理場所到着時 脈拍"),
            (day0_temp, "術後管理場所到着時 体温"),
        ]:
            if v is None:
                missing.append(label)
        errors.extend(validate_vitals(day0_sbp, day0_dbp, day0_pulse, day0_temp, "術後管理場所到着時バイタル"))

        if initial_hospital_outcome == "退院済み":
            for v, label in [
                (discharge_sbp, "退院時 収縮期血圧"),
                (discharge_dbp, "退院時 拡張期血圧"),
                (discharge_pulse, "退院時 脈拍"),
                (discharge_temp, "退院時 体温"),
            ]:
                if v is None:
                    missing.append(label)
            errors.extend(validate_vitals(discharge_sbp, discharge_dbp, discharge_pulse, discharge_temp, "退院時バイタル"))
            if discharge_lab_available is None:
                missing.append("退院前採血の有無")
            elif discharge_lab_available == "あり":
                if discharge_lab_date is None:
                    missing.append("退院前採血日")
                if not any(text(v) for v in discharge_labs_raw.values()):
                    missing.append("退院前採血結果")
                if discharge_lab_date and op_date and discharge_lab_date < op_date:
                    errors.append("退院前採血日が手術日より前です")
                if discharge_lab_date and op_discharge_date and discharge_lab_date > op_discharge_date:
                    errors.append("退院前採血日が初回退院日より後です")

    if visit_date_30 is None: missing.append("30日評価日")
    if reference_date and visit_date_30:
        wi = window_info(reference_date, 30, 14)
        if visit_date_30 < reference_date: errors.append("30日評価日が手術/予定日より前です")
        if visit_date_30 > today_jst(): errors.append("30日評価日が未来日です")
        if not (wi["min"] <= visit_date_30 <= wi["max"]):
            if not text(window_deviation_reason): missing.append("30日評価時期の逸脱理由")
            warnings.append("30日評価日が30日±14日の範囲外です")

    day30_parsed, day30_errors = validate_optional_lab_panel(day30_labs_raw)
    errors.extend([f"30日血液検査：{x}" for x in day30_errors])
    if day30_lab_date is None:
        missing.append("30日評価に用いた採血日")
    if not any(text(v) for v in day30_labs_raw.values()):
        missing.append("30日評価採血結果")
    if reference_date and day30_lab_date:
        lab_wi = window_info(reference_date, 30, 14)
        if not (lab_wi["min"] <= day30_lab_date <= lab_wi["max"]):
            errors.append("30日評価に用いた採血日が30日±14日の許容期間外です")

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

    if initial_hospital_outcome == "初回入院中に死亡" and status_alive not in [None, "死亡"]:
        errors.append("初回入院中死亡が選択されています。生存状況は『死亡』としてください")
    if readmission_day30_status == "再入院中に死亡" and status_alive not in [None, "死亡"]:
        errors.append("再入院中死亡が選択されています。生存状況は『死亡』としてください")

    if status_alive is None: missing.append("生存状況")
    elif status_alive == "生存":
        if final_visit_date is None:
            missing.append("最終生存確認日")
        else:
            if final_visit_date > today_jst():
                errors.append("最終生存確認日が未来日です")
            if visit_date_30 and final_visit_date < visit_date_30:
                warnings.append("最終生存確認日が30日評価日より前です。30日評価時に生存確認している場合は評価日を入力してください")
        if cd_grade == "Grade V":
            errors.append("CD Grade Vですが生存状況が『生存』です")
    else:
        if death_date is None:
            missing.append("死亡日")
        else:
            if death_date > today_jst():
                errors.append("死亡日が未来日です")
        if death_cause == "選択してください": missing.append("死因")
        if surgery_performed == "実施した" and death_date and op_date and death_date < op_date:
            errors.append("死亡日が手術実施日より前です")

    return unique_messages(missing), unique_messages(errors), unique_messages(warnings), discharge_labs_parsed, day30_parsed

missing, errors, warnings, discharge_labs_parsed, day30_parsed = validate_all()

st.markdown('<div class="juog-header">5. 送信</div>', unsafe_allow_html=True)
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

st.caption("仮保存は正式送信ではありません。")
submit_clicked = st.button("事務局へ確定送信", type="primary", use_container_width=True, disabled=L, key="draft30_submit_button")

if draft_clicked:
    if not valid_registration_id(registration_id):
        st.error("仮保存には正しいJUOG登録番号が必要です（例：JUOG-001）。")
    else:
        draft_state = capture_draft_state(
            "peri_",
            exclude_prefixes=("peri_sent",),
            overrides={"peri_registration_id": registration_id},
        )
        draft_result = save_crf_draft(
            registration_id,
            "perioperative_30d",
            "30d",
            draft_state,
            facility_code=facility_code,
            facility_name=facility_name if facility_name != "選択してください" else "",
            reporter_email=reporter_email,
        )
        if draft_result.get("ok"):
            saved_at = draft_result.get("updated_at") or ""
            st.success("仮保存しました。ブラウザを閉じても『仮保存から再開』から読み込めます。" + (f"（{saved_at}）" if saved_at else ""))
        else:
            st.error("仮保存できませんでした：" + (draft_result.get("message") or draft_result.get("error") or "unknown error"))

if submit_clicked:
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
                "initial_hospital_outcome": initial_hospital_outcome,
                "discharge_date": date_str(op_discharge_date),
                "readmission_30d": readmission_30d,
                "readmission_date": date_str(readmission_date),
                "readmission_reason": text(readmission_reason),
                "readmission_day30_status": readmission_day30_status,
                "readmission_discharge_date": date_str(readmission_discharge_date),
                "operation_type": op_type,
                "operation_type_other": text(st.session_state.get("peri_op_other", "")),
                "approach": "＋".join(approaches),
                "approaches": approaches,
                "approach_pattern": approach_pattern,
                "conversion_reason": text(conversion_reason),
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
                "day0_vitals": {"timepoint": "postoperative_care_area_arrival", "sbp": day0_sbp, "dbp": day0_dbp, "pulse": day0_pulse, "temperature": day0_temp},
                "inpatient_vitals": {"timepoint": "discharge", "sbp": discharge_sbp, "dbp": discharge_dbp, "pulse": discharge_pulse, "temperature": discharge_temp},
                "discharge_vitals": {"available": initial_hospital_outcome == "退院済み", "sbp": discharge_sbp, "dbp": discharge_dbp, "pulse": discharge_pulse, "temperature": discharge_temp},
                "inpatient_lab_available": discharge_lab_available,
                "inpatient_lab_date": date_str(discharge_lab_date),
                "inpatient_labs": discharge_labs_parsed,
                "inpatient_required_test_omission_reason": "",
                "pathology": path if surgery_performed == "実施した" else {},
                "day30_visit_date": date_str(visit_date_30),
                "day30_window_deviation_reason": text(window_deviation_reason),
                "day30_lab_available": day30_lab_available,
                "day30_lab_date": date_str(day30_lab_date),
                "day30_labs": day30_parsed,
                "day30_required_test_omission_reason": "",
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
手術日: {date_str(op_date) if surgery_performed == '実施した' else 'N/A'}
手術予定日: {date_str(planned_or_reference_date) if surgery_performed == '実施しなかった' else 'N/A'}
実施術式: {op_type if surgery_performed == '実施した' else 'N/A'}
手術完遂: {op_completed if surgery_performed == '実施した' else 'N/A'}
EAUiaiC: {eau_grade if surgery_performed == '実施した' else 'N/A'}
R0: {path.get('r0', 'N/A') if surgery_performed == '実施した' else 'N/A'}
pCR（ypT0N0/Nx）: {'はい' if path.get('pcr') else 'いいえ/N/A'}
ypT0N0: {'はい' if path.get('pcr_ypt0n0') else 'いいえ/N/A'}

30日評価日: {date_str(visit_date_30)}
30日最高CD Grade: {cd_grade}
30日主要手術関連合併症（定義該当）: {'はい' if major30 else 'いいえ'}
生存状況: {status_alive}
死亡日: {date_str(death_date) or 'N/A'}
術後治療: {adj_plan}

{json_block(payload)}
"""
            save_result = save_crf_payload(payload)
            if not save_result.get("ok"):
                st.error("中央Google Sheetへ保存できませんでした：" + (save_result.get("message") or save_result.get("error") or "unknown error"))
            else:
                draft_delete = delete_crf_draft(registration_id, "perioperative_30d", "30d")
                st.session_state.peri_sent_draft_delete_failed = not bool(draft_delete.get("ok"))
                sent, send_err = send_email(
                    f"【JUOG CRF】【perioperative_30d】【{registration_id}】",
                    report,
                    reporter_email,
                )
                st.session_state.peri_sent = True
                st.session_state.peri_sent_registration_id = registration_id
                st.session_state.peri_sent_version = str(save_result.get("record_version", "") or "")
                st.session_state.peri_sent_had_warnings = bool(warnings)
                st.session_state.peri_sent_email_failed = not sent
                if not sent:
                    print(f"[JUOG perioperative] email failed: {send_err}")
                st.rerun()
