from __future__ import annotations

import uuid
from datetime import date
import streamlit as st

from juog_common import (
    POSITIVE_CYTOLOGY,
    add_months,
    age_on_date,
    date_str,
    json_block,
    now_iso,
    recist_target_response,
    registry_call,
    render_facility,
    render_lab_panel,
    render_cytology,
    send_email,
    text,
    today_jst,
    unique_messages,
    valid_email,
    validate_lab_panel,
    validate_cytology,
    validate_anthropometrics,
    validate_vitals,
)

st.markdown(
    """
    <style>
    .block-container {max-width: 1180px !important; padding-top: 1.3rem !important; padding-bottom: 5rem !important;}
    h1 {font-size: 27px !important; text-align:center; color:#0F172A; margin-bottom:30px !important;}
    .juog-header {background:#1E3A8A;color:white;padding:10px 18px;border-radius:8px;font-weight:700;margin-top:24px;margin-bottom:14px;}
    label {font-weight:600 !important; color:#334155 !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("JUOG UTUC_Consolidative 中央MDT審査申請CRF")
st.caption("研究計画書 第3版（2026/09/14）に基づく中央MDT審査申請用CRFです。")

RECIST_HELP = """RECIST v1.1 補助計算：CT等の非リンパ節標的病変は長径、リンパ節は短径を入力します。\n
標的病変は最大5個（1臓器最大2個）が原則です。この画面の自動計算は入力整合性確認用であり、中央放射線診断医によるRECIST総合判定を置き換えません。"""

if "screening_sent" not in st.session_state:
    st.session_state.screening_sent = False

if st.session_state.screening_sent:
    sid = st.session_state.get("screening_id", "")
    st.success("中央MDT審査申請を送信しました。")
    if sid:
        st.write(f"**MDT審査受付番号：{sid}**")
    st.caption("正式登録およびJUOG登録番号の発行は、中央MDTで適格と判定された後に研究事務局が行います。")
    if st.session_state.get("screening_email_failed"):
        st.warning("中央台帳への保存は完了していますが、通知メール送信に失敗しました。再申請はせず事務局へ連絡してください。")
    st.caption("訂正が必要な場合はページを再読み込みして再入力してください。")
    st.stop()

L = False

# -------------------- 1. Basic / screening --------------------
st.markdown('<div class="juog-header">1. 患者背景・スクリーニング</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    facility_code, facility_name = render_facility(key="reg_facility", disabled=L)
    local_subject_code = st.text_input(
        "施設内研究対象者識別コード*",
        disabled=L,
        help="氏名・カルテ番号・生年月日そのものは入力しないでください。各施設の識別コードリストと照合可能な仮名コードです。",
    )
    reporter_email = st.text_input("担当者メールアドレス*", disabled=L)
    consent_date = st.date_input("本人同意取得日*", value=None, disabled=L)
    birth_date = st.date_input("生年月日*", value=None, min_value=date(1900, 1, 1), max_value=today_jst(), disabled=L, help="研究計画書 8.1.1 の患者背景項目。氏名・カルテ番号は入力しません。")
    age = age_on_date(birth_date, consent_date)
    if age is not None:
        st.caption(f"同意取得時年齢（自動計算）：{age}歳")
with c2:
    sex = st.radio("性別*", ["男", "女"], index=None, horizontal=True, disabled=L)
    height = st.number_input("身長 (cm)*", min_value=0.0, value=None, step=0.1, disabled=L)
    weight = st.number_input("体重 (kg)*", min_value=0.0, value=None, step=0.1, disabled=L)
    ecog = st.radio("ECOG PS*", ["0", "1", "2", "3", "4"], index=None, horizontal=True, disabled=L)
    if sex == "女":
        pregnancy = st.radio("妊娠中または妊娠の可能性*", ["なし", "あり"], index=None, horizontal=True, disabled=L)
        breastfeeding = st.radio("授乳中*", ["なし", "あり"], index=None, horizontal=True, disabled=L)
    else:
        pregnancy, breastfeeding = "該当なし", "該当なし"

st.subheader("スクリーニング時バイタル・身体所見")
v1, v2, v3, v4 = st.columns(4)
sbp = v1.number_input("収縮期血圧 (mmHg)*", min_value=0, value=None, step=1, disabled=L)
dbp = v2.number_input("拡張期血圧 (mmHg)*", min_value=0, value=None, step=1, disabled=L)
pulse = v3.number_input("脈拍 (/min)*", min_value=0, value=None, step=1, disabled=L)
temp = v4.number_input("体温 (℃)*", min_value=30.0, max_value=45.0, value=None, step=0.1, disabled=L)
physical_abnormal = st.radio("自覚症状・他覚所見の異常*", ["なし", "あり"], index=None, horizontal=True, disabled=L)
physical_detail = st.text_area("身体所見の詳細*" if physical_abnormal == "あり" else "身体所見の詳細", disabled=L)

h1, h2 = st.columns(2)
with h1:
    past_history = st.text_area("既往歴（なしの場合は『なし』）*", disabled=L)
    comorbidity = st.text_area("現在の合併症（なしの場合は『なし』）*", disabled=L)
with h2:
    concomitant_meds = st.text_area("現在の併用薬（なしの場合は『なし』）*", disabled=L)
    concomitant_tx = st.text_area("現在の併用治療（なしの場合は『なし』）*", disabled=L)

# -------------------- 2. Diagnosis --------------------
st.markdown('<div class="juog-header">2. 原疾患・診断時Stage</div>', unsafe_allow_html=True)
d1, d2 = st.columns(2)
with d1:
    diagnosis_date = st.date_input("初回診断日*", value=None, disabled=L)
    laterality = st.radio("原発巣の左右*", ["右", "左", "両側"], index=None, horizontal=True, disabled=L)
    primary_site = st.multiselect("原発巣部位*", ["腎盂", "上部尿管", "中部尿管", "下部尿管"], disabled=L)
    biopsy_done = st.radio("組織生検*", ["実施", "生検困難のため未実施"], index=None, horizontal=True, disabled=L)
    histology = ""
    biopsy_reason = ""
    if biopsy_done == "実施":
        histology = st.selectbox(
            "病理組織型*",
            ["選択してください", "Urothelial carcinoma", "Urothelial carcinoma（亜型・分化を含む）", "その他"],
            disabled=L,
        )
        if histology == "その他":
            st.text_input("病理組織型 その他詳細*", key="reg_histology_other", disabled=L)
    elif biopsy_done == "生検困難のため未実施":
        biopsy_reason = st.text_area("生検困難の理由*", disabled=L)
with d2:
    ct = st.selectbox("診断時 cT*", ["選択してください", "cTa", "cTis", "cT1", "cT2", "cT3", "cT4"], disabled=L)
    cn = st.selectbox("診断時 cN*", ["選択してください", "cN0", "cN1", "cN2"], disabled=L)
    cm = st.selectbox("診断時 cM*", ["選択してください", "cM0", "cM1"], disabled=L)
    screening_imaging_date = st.date_input("スクリーニング画像検査日（CT/MRI等）*", value=None, disabled=L)
    imaging_utuc_compatible = st.radio("画像上UTUCに合致する所見*", ["あり", "なし"], index=None, horizontal=True, disabled=L)
    cystoscopy_date = st.date_input("スクリーニング膀胱鏡日*", value=None, disabled=L)
    cystoscopy_result = st.selectbox("膀胱鏡所見*", ["選択してください", "腫瘍なし", "腫瘍あり", "評価不能"], disabled=L)
    if cystoscopy_result == "腫瘍あり":
        st.text_area("膀胱病変の詳細*", key="reg_cysto_detail", disabled=L)

st.subheader("スクリーニング尿細胞診")
screen_cytology = render_cytology("reg_screen", required=True, disabled=L)

st.subheader("スクリーニング血液検査")
screen_labs_raw = render_lab_panel("reg_screen_lab", required=True, disabled=L, columns=3)
screen_glucose_raw = st.text_input(
    "血糖 (mg/dL)*",
    value=st.session_state.get("reg_screen_glucose", ""),
    disabled=L,
    help="スクリーニング時のみ収集します。未測定の場合はNAと入力してください。",
)
st.session_state["reg_screen_glucose"] = screen_glucose_raw
screening_required_omission = (
    any(str(v).strip().upper() in {"NA", "N/A", "未実施", "欠測"} for v in screen_labs_raw.values())
    or str(screen_glucose_raw).strip().upper() in {"NA", "N/A", "未実施", "欠測"}
    or screen_cytology == "未実施"
)
screening_omission_reason = ""
if screening_required_omission:
    screening_omission_reason = st.text_area("スクリーニング必須検査の欠測/未実施理由*", disabled=L)

# -------------------- 3. EVP / RECIST --------------------
st.markdown('<div class="juog-header">3. EVP治療歴・術前画像評価</div>', unsafe_allow_html=True)
e1, e2 = st.columns(2)
with e1:
    evp_start = st.date_input("EVP初回投与日*", value=None, disabled=L)
    evp_end = st.date_input("EVP最終投与日*", value=None, disabled=L)
    courses = st.number_input("EVP総投与コース数*", min_value=0, value=None, step=1, disabled=L)
    ev_initial_dose = st.number_input("EV初回量 (mg/kg)*", min_value=0.0, value=None, step=0.01, disabled=L)
    reduction = st.radio("EV減量の有無*", ["なし", "あり"], index=None, horizontal=True, disabled=L)
    reduction_detail = st.text_area("EV減量の詳細*" if reduction == "あり" else "EV減量の詳細", disabled=L)
    pembro_stop = st.radio("irAE等によるPembro中止の有無*", ["なし", "あり"], index=None, horizontal=True, disabled=L)
    pembro_stop_detail = st.text_area("Pembro中止の詳細*" if pembro_stop == "あり" else "Pembro中止の詳細", disabled=L)
with e2:
    best_effect = st.selectbox("EVP最良総合効果*", ["選択してください", "CR", "PR", "SD", "PD", "NE"], disabled=L)
    first_control_date = st.date_input("最初にCR/PR/SDが確認された画像検査日*", value=None, disabled=L)
    central_recist = st.selectbox("施設判定 RECIST v1.1総合判定*", ["選択してください", "CR", "PR", "SD", "PD", "NE"], disabled=L)
    preop_imaging_date = st.date_input("手術適応判定前の直近画像日*", value=None, disabled=L)
    nadir_sum = st.number_input(
        "治療中の標的病変最小SLD（nadir, mm・分かる場合）",
        min_value=0.0, value=None, step=0.1, disabled=L,
        help="RECIST 1.1の標的病変PDはbaselineではなく治療中の最小和（nadir）との比較です。中央判定が主判定なので、不明なら空欄で構いません。",
    )
    new_lesion = st.radio("新病変の出現*", ["なし", "あり"], index=None, horizontal=True, disabled=L)
    nontarget_pd = st.radio("非標的病変の明らかな増悪*", ["なし", "あり"], index=None, horizontal=True, disabled=L)
    short_course_reason = ""
    if courses is not None and courses < 3:
        short_course_reason = st.text_area("3コース未満となったやむを得ない理由*", disabled=L)

st.subheader("RECIST標的病変（補助計算）")
st.caption(RECIST_HELP)
lesions = []
for i in range(1, 6):
    with st.expander(f"標的病変 {i}" + ("（原発巣を推奨）" if i == 1 else ""), expanded=(i == 1)):
        c_a, c_b, c_c, c_d = st.columns([1.4, 1.2, 1, 1])
        site_options = ["該当なし", "原発巣", "リンパ節", "肺", "肝", "骨軟部成分", "その他"]
        site = c_a.selectbox("部位", site_options, key=f"reg_lesion_site_{i}", disabled=L)
        detail = c_b.text_input("詳細/臓器", key=f"reg_lesion_detail_{i}", disabled=L)
        baseline = c_c.number_input("EVP前 (mm)", min_value=0.0, value=None, step=0.1, key=f"reg_lesion_base_{i}", disabled=L)
        followup = c_d.number_input("手術前 (mm)", min_value=0.0, value=None, step=0.1, key=f"reg_lesion_follow_{i}", disabled=L)
        if site != "該当なし":
            lesions.append({"no": i, "site": site, "detail": detail, "baseline": baseline, "followup": followup, "is_node": site == "リンパ節"})

recist_support = recist_target_response(lesions, new_lesion == "あり", nontarget_pd == "あり", nadir_sum=nadir_sum)
if recist_support["change_pct"] is not None:
    st.metric("標的病変 SLD変化率（baseline比・補助）", f"{recist_support['change_pct']:.1f}%")
if recist_support.get("pd_change_pct_from_nadir") is not None:
    st.caption(f"nadir比変化率：{recist_support['pd_change_pct_from_nadir']:.1f}%")
st.info(f"標的病変の補助判定：{recist_support['response']}（中央MDTでは画像と臨床情報を再評価します）")

# cM1 requirements
cm1_basis = ""
cned_date = None
cm1_local_tx = ""
if cm == "cM1":
    st.subheader("cM1症例の登録条件")
    m1, m2 = st.columns(2)
    with m1:
        cm1_basis = st.radio(
            "cM1登録根拠*",
            ["EVPにより遠隔転移巣がCR", "局所療法後にcNEDとなり3か月以上維持"],
            index=None,
            disabled=L,
        )
        cned_date = st.date_input("cNED確認日", value=None, disabled=L)
    with m2:
        cm1_local_tx = st.multiselect("遠隔転移に対する局所療法", ["転移巣切除", "放射線治療", "その他"], disabled=L)
        if "その他" in cm1_local_tx:
            st.text_input("局所療法 その他詳細*", key="reg_cm1_other", disabled=L)

# -------------------- 4. Exclusion / planned surgery --------------------
st.markdown('<div class="juog-header">4. 選択・除外基準、手術予定</div>', unsafe_allow_html=True)
x1, x2 = st.columns(2)
with x1:
    g3_unrecovered = st.radio("EVP関連 Grade 3以上の未回復有害事象*", ["なし", "あり"], index=None, horizontal=True, disabled=L)
    unresectable_vessel = st.radio("切除不能/危険な大血管浸潤*", ["なし", "あり"], index=None, horizontal=True, disabled=L)
    unresectable_organ = st.radio("切除不能/危険な他臓器直接浸潤*", ["なし", "あり"], index=None, horizontal=True, disabled=L)
    other_cancer = st.radio("活動性重複がん*", ["なし", "ありだが計画書上の許容例", "あり（不適）"], index=None, disabled=L)
    other_unsuitable = st.radio("その他、研究責任者が不適当と判断*", ["なし", "あり"], index=None, horizontal=True, disabled=L)
with x2:
    planned_surgery = st.selectbox("予定術式*", ["選択してください", "根治的腎尿管全摘除術", "尿管部分切除術", "その他（プロトコル外）"], disabled=L)
    surgery_date = st.date_input("手術予定日*", value=None, disabled=L)
    washout_extension_reason = ""
    if evp_end and surgery_date:
        washout_days = (surgery_date - evp_end).days
        st.write(f"EVP最終投与→手術予定：**{washout_days}日**")
        if 28 <= washout_days <= 56:
            st.success("原則の4–8週内です。")
        elif 57 <= washout_days <= 84:
            st.warning("8週を超えていますが、計画書上は医学的理由等により最大12週まで許容されます。")
            washout_extension_reason = st.text_area("8週超となる理由*", disabled=L)
        elif washout_days < 28:
            st.error("4週未満です。手術予定時期を再確認してください。")
        else:
            st.error("12週を超えています。計画書の規定外です。")

# -------------------- Validation --------------------
def collect_validation():
    missing, errors, reasons, warnings = [], [], [], []
    if facility_name == "選択してください": missing.append("施設名")
    if not text(local_subject_code): missing.append("施設内研究対象者識別コード")
    if not valid_email(reporter_email): errors.append("担当者メールアドレスが不正です")
    if consent_date is None: missing.append("本人同意取得日")
    if birth_date is None: missing.append("生年月日")
    if birth_date and birth_date > today_jst(): errors.append("生年月日が未来日です")
    if birth_date and consent_date and birth_date > consent_date: errors.append("生年月日が同意取得日より後です")
    if age is None: missing.append("同意取得時年齢")
    elif age < 20: reasons.append("同意取得時年齢が20歳未満")
    elif age > 120: errors.append("同意取得時年齢が120歳を超えています。生年月日を確認してください")
    if sex is None: missing.append("性別")
    if sex == "女":
        if pregnancy is None: missing.append("妊娠の有無")
        if breastfeeding is None: missing.append("授乳の有無")
        if pregnancy == "あり": reasons.append("妊娠中または妊娠の可能性あり")
        if breastfeeding == "あり": reasons.append("授乳中")
    if height is None or height <= 0: missing.append("身長")
    if weight is None or weight <= 0: missing.append("体重")
    errors.extend(validate_anthropometrics(height, weight))
    if ecog is None: missing.append("ECOG PS")
    elif ecog not in ["0", "1"]: reasons.append("ECOG PSが2以上")
    for val, label in [(sbp, "収縮期血圧"), (dbp, "拡張期血圧"), (pulse, "脈拍"), (temp, "体温")]:
        if val is None: missing.append(label)
    errors.extend(validate_vitals(sbp, dbp, pulse, temp, "スクリーニングバイタル"))
    if physical_abnormal is None: missing.append("身体所見")
    if physical_abnormal == "あり" and not text(physical_detail): missing.append("身体所見詳細")
    for val, label in [(past_history, "既往歴"), (comorbidity, "現在の合併症"), (concomitant_meds, "現在の併用薬"), (concomitant_tx, "現在の併用治療")]:
        if not text(val): missing.append(label)

    if diagnosis_date is None: missing.append("初回診断日")
    if laterality is None: missing.append("原発巣の左右")
    if not primary_site: missing.append("原発巣部位")
    if biopsy_done is None: missing.append("組織生検")
    hist_other = st.session_state.get("reg_histology_other", "")
    if biopsy_done == "実施":
        if histology == "選択してください": missing.append("病理組織型")
        elif histology == "その他":
            if not text(hist_other): missing.append("病理組織型 その他詳細")
            reasons.append("組織診がUrothelial carcinomaとして確認されていない")
    if biopsy_done == "生検困難のため未実施":
        if not text(biopsy_reason): missing.append("生検困難の理由")
        if screen_cytology not in POSITIVE_CYTOLOGY:
            reasons.append("生検未実施例で尿細胞診陽性が確認されていない")
        if imaging_utuc_compatible != "あり":
            reasons.append("生検未実施例で画像上UTUC所見が確認されていない")
    if biopsy_done == "実施" and histology not in ["Urothelial carcinoma", "Urothelial carcinoma（亜型・分化を含む）", "選択してください", ""]:
        reasons.append("組織学的にUTUC（urothelial carcinoma）が確認されていない")

    for val, label in [(ct, "cT"), (cn, "cN"), (cm, "cM")]:
        if val == "選択してください": missing.append(label)
    stage_iv = ct == "cT4" or cn in ["cN1", "cN2"] or cm == "cM1"
    if ct != "選択してください" and cn != "選択してください" and cm != "選択してください" and not stage_iv:
        reasons.append("診断時Stage IV（cT4/cN1-2/条件付きcM1）を満たさない")
    if screening_imaging_date is None: missing.append("スクリーニング画像日")
    elif screening_imaging_date > today_jst(): errors.append("スクリーニング画像日が未来日です")
    if imaging_utuc_compatible is None: missing.append("画像上UTUC所見")
    if cystoscopy_date is None: missing.append("スクリーニング膀胱鏡日")
    elif cystoscopy_date > today_jst(): errors.append("スクリーニング膀胱鏡日が未来日です")
    if cystoscopy_result == "選択してください": missing.append("膀胱鏡所見")
    if cystoscopy_result == "腫瘍あり" and not text(st.session_state.get("reg_cysto_detail", "")): missing.append("膀胱病変詳細")
    missing.extend([f"スクリーニング {x}" for x in validate_cytology(screen_cytology, required=True)])
    parsed_labs, lab_errors, lab_warn = validate_lab_panel(screen_labs_raw, required=True)
    errors.extend([f"スクリーニング血液検査：{x}" for x in lab_errors])
    warnings.extend([f"スクリーニング血液検査：{x}" for x in lab_warn])
    glucose_text = str(screen_glucose_raw).strip()
    glucose_value = None
    if not glucose_text:
        errors.append("スクリーニング血液検査：血糖が空欄です（未測定の場合はNAと入力）")
    elif glucose_text.upper() in {"NA", "N/A", "未実施", "欠測"}:
        warnings.append("スクリーニング血液検査：血糖：NA")
    else:
        try:
            glucose_value = float(glucose_text)
            if glucose_value < 0:
                errors.append("スクリーニング血液検査：血糖に負の値は入力できません")
        except ValueError:
            errors.append("スクリーニング血液検査：血糖は数値またはNAで入力してください")
    if (lab_warn or glucose_value is None or screen_cytology == "未実施") and not text(screening_omission_reason):
        missing.append("スクリーニング必須検査の欠測/未実施理由")

    if evp_start is None: missing.append("EVP初回投与日")
    if evp_end is None: missing.append("EVP最終投与日")
    if courses is None: missing.append("EVP総投与コース数")
    elif courses < 1: errors.append("EVP総投与コース数は1以上で入力してください")
    if ev_initial_dose is None or ev_initial_dose <= 0: missing.append("EV初回量")
    if reduction is None: missing.append("EV減量の有無")
    if reduction == "あり" and not text(reduction_detail): missing.append("EV減量の詳細")
    if pembro_stop is None: missing.append("Pembro中止の有無")
    if pembro_stop == "あり" and not text(pembro_stop_detail): missing.append("Pembro中止の詳細")
    if best_effect == "選択してください": missing.append("EVP最良総合効果")
    if first_control_date is None: missing.append("最初のCR/PR/SD確認日")
    if central_recist == "選択してください": missing.append("施設判定RECIST総合判定")
    if preop_imaging_date is None: missing.append("手術適応判定前画像日")
    elif preop_imaging_date > today_jst(): errors.append("手術適応判定前画像日が未来日です")
    if new_lesion is None: missing.append("新病変の有無")
    if nontarget_pd is None: missing.append("非標的病変増悪の有無")
    if central_recist in ["PD", "NE"] or best_effect in ["PD", "NE"]:
        reasons.append("RECIST v1.1でCR/PR/SDが確認されていない")
    if new_lesion == "あり" or nontarget_pd == "あり":
        reasons.append("RECIST v1.1上の進行所見（新病変/非標的病変の明らかな増悪）あり")
    if courses is not None and courses < 3:
        if not text(short_course_reason): missing.append("3コース未満の理由")
        # Protocol allows <3 courses only when >=63 days from first dose at eligibility.
        ref_date = today_jst()
        if evp_start and (ref_date - evp_start).days < 63:
            reasons.append("EVP 3コース未満かつ初回投与から63日未満")

    # RECIST 1.1 target-lesion data-quality checks (supportive; central RECIST remains authoritative).
    organ_counts = {}
    for lesion in lesions:
        site = lesion.get("site")
        organ_counts[site] = organ_counts.get(site, 0) + 1
        if lesion.get("baseline") is None: missing.append(f"標的病変{lesion.get('no')} EVP前径")
        if lesion.get("followup") is None: missing.append(f"標的病変{lesion.get('no')} 手術前径")
        b = lesion.get("baseline")
        if b is not None:
            if lesion.get("is_node") and b < 15:
                warnings.append(f"標的病変{lesion.get('no')}：リンパ節短径が15 mm未満です（RECIST標的病変の測定可能基準を再確認）")
            elif not lesion.get("is_node") and b < 10:
                warnings.append(f"標的病変{lesion.get('no')}：非リンパ節病変が10 mm未満です（RECIST標的病変の測定可能基準を再確認）")
    for organ, count in organ_counts.items():
        if count > 2:
            warnings.append(f"RECIST標的病変：{organ}が{count}病変選択されています（1臓器最大2病変）")
    if nadir_sum is not None and nadir_sum < 0:
        errors.append("nadir SLDに負の値は入力できません")
    if nadir_sum is None and recist_support["response"] == "SD/PD要nadir確認":
        warnings.append("標的病変のみのPD判定には治療中nadirが必要です。施設判定と中央MDT画像評価で確認してください")
    if recist_support["response"] == "PD" and central_recist in ["CR", "PR", "SD"]:
        warnings.append("標的病変の補助計算はPDですが、入力された施設RECIST総合判定は非PDです。画像判定を再確認してください")

    if cm == "cM1":
        if not cm1_basis: missing.append("cM1登録根拠")
        if cm1_basis == "EVPにより遠隔転移巣がCR":
            # Overall response can be PR/SD if primary persists; the metastatic component must be documented as CR by this choice.
            pass
        elif cm1_basis == "局所療法後にcNEDとなり3か月以上維持":
            if cned_date is None: missing.append("cNED確認日")
            elif cned_date > today_jst(): errors.append("cNED確認日が未来日です")
            if not cm1_local_tx: missing.append("遠隔転移に対する局所療法")
            if cned_date and today_jst() < add_months(cned_date, 3):
                reasons.append("cNEDの3か月維持期間不足")

    for val, label in [(g3_unrecovered, "Grade 3以上未回復AE"), (unresectable_vessel, "大血管浸潤"), (unresectable_organ, "他臓器浸潤"), (other_cancer, "活動性重複がん"), (other_unsuitable, "その他不適当")]:
        if val is None: missing.append(label)
    if g3_unrecovered == "あり": reasons.append("EVP関連Grade 3以上の有害事象が未回復")
    if unresectable_vessel == "あり": reasons.append("切除不能/危険な大血管浸潤")
    if unresectable_organ == "あり": reasons.append("切除不能/危険な他臓器直接浸潤")
    if other_cancer == "あり（不適）": reasons.append("活動性重複がん")
    if other_unsuitable == "あり": reasons.append("研究責任者が研究対象者として不適当と判断")

    if planned_surgery == "選択してください": missing.append("予定術式")
    elif planned_surgery == "その他（プロトコル外）": reasons.append("予定術式がRNU/尿管部分切除術ではない")
    if surgery_date is None: missing.append("手術予定日")
    if evp_end and surgery_date:
        wd = (surgery_date - evp_end).days
        if wd < 28: reasons.append("EVP最終投与から手術予定まで4週未満")
        elif wd > 84: reasons.append("EVP最終投与から手術予定まで12週超")
        elif wd > 56 and not text(washout_extension_reason): missing.append("8週超となる理由")

    # Basic chronology
    dates = [(diagnosis_date, "初回診断日"), (consent_date, "同意日"), (evp_start, "EVP初回"), (evp_end, "EVP最終"), (first_control_date, "初回病勢制御"), (preop_imaging_date, "直近画像"), (surgery_date, "手術予定")]
    for d, label in dates:
        if d and d > today_jst() and label != "手術予定": errors.append(f"{label}が未来日です")
    if diagnosis_date and evp_start and diagnosis_date > evp_start: errors.append("初回診断日がEVP初回投与日より後です")
    if diagnosis_date and consent_date and diagnosis_date > consent_date:
        warnings.append("初回診断日が研究同意取得日より後です。日付を確認してください")
    if evp_start and consent_date and evp_start > consent_date:
        warnings.append("EVP初回投与日が研究同意取得日より後です。本研究ではEVPはスクリーニング前治療のため日付を確認してください")
    if evp_start and evp_end and evp_end < evp_start: errors.append("EVP最終投与日が初回投与日より前です")
    if consent_date and surgery_date and surgery_date < consent_date: errors.append("手術予定日が同意取得日より前です")
    if evp_end and surgery_date and evp_end > surgery_date: errors.append("EVP最終投与日が手術予定日より後です")
    if evp_start and first_control_date and first_control_date < evp_start: errors.append("病勢制御確認日がEVP初回投与日より前です")
    if first_control_date and preop_imaging_date and preop_imaging_date < first_control_date: warnings.append("手術適応判定前画像日が最初の病勢制御確認日より前です")

    return unique_messages(missing), unique_messages(errors), unique_messages(reasons), unique_messages(warnings), parsed_labs


def build_data(parsed_labs):
    return {
        "local_subject_code": text(local_subject_code),
        "consent_date": date_str(consent_date),
        "birth_year_month": birth_date.strftime("%Y-%m") if birth_date else "",
        "age_at_consent": age,
        "sex": sex,
        "height_cm": height,
        "weight_kg": weight,
        "ecog_ps": ecog,
        "pregnancy": pregnancy,
        "breastfeeding": breastfeeding,
        "screening_vitals": {"sbp": sbp, "dbp": dbp, "pulse": pulse, "temperature": temp},
        "physical_abnormal": physical_abnormal,
        "physical_detail": text(physical_detail),
        "past_history": text(past_history),
        "comorbidity": text(comorbidity),
        "concomitant_meds": text(concomitant_meds),
        "concomitant_treatment": text(concomitant_tx),
        "diagnosis_date": date_str(diagnosis_date),
        "laterality": laterality,
        "primary_site": primary_site,
        "biopsy_status": biopsy_done,
        "biopsy_reason": text(biopsy_reason),
        "histology": histology,
        "histology_other": text(st.session_state.get("reg_histology_other", "")),
        "ct": ct, "cn": cn, "cm": cm,
        "screening_imaging_date": date_str(screening_imaging_date),
        "imaging_utuc_compatible": imaging_utuc_compatible,
        "cystoscopy_date": date_str(cystoscopy_date),
        "cystoscopy_result": cystoscopy_result,
        "cystoscopy_detail": text(st.session_state.get("reg_cysto_detail", "")),
        "screening_cytology": screen_cytology,
        "screening_labs": {**parsed_labs, "Glucose": (None if str(screen_glucose_raw).strip().upper() in {"NA", "N/A", "未実施", "欠測", ""} else float(screen_glucose_raw))},
        "screening_required_test_omission_reason": text(screening_omission_reason),
        "evp_start": date_str(evp_start),
        "evp_end": date_str(evp_end),
        "evp_courses": courses,
        "ev_initial_dose_mgkg": ev_initial_dose,
        "ev_reduction": reduction,
        "ev_reduction_detail": text(reduction_detail),
        "pembro_stop": pembro_stop,
        "pembro_stop_detail": text(pembro_stop_detail),
        "best_effect": best_effect,
        "first_disease_control_date": date_str(first_control_date),
        "preop_imaging_date": date_str(preop_imaging_date),
        "target_nadir_sum_mm": nadir_sum,
        "site_recist": central_recist,
        "new_lesion": new_lesion,
        "nontarget_pd": nontarget_pd,
        "short_course_reason": text(short_course_reason),
        "target_lesions": lesions,
        "target_recist_support": recist_support,
        "cm1_basis": cm1_basis,
        "cned_date": date_str(cned_date),
        "cm1_local_therapy": cm1_local_tx,
        "cm1_local_therapy_other": text(st.session_state.get("reg_cm1_other", "")),
        "g3_unrecovered_ae": g3_unrecovered,
        "unresectable_vessel": unresectable_vessel,
        "unresectable_organ": unresectable_organ,
        "other_cancer": other_cancer,
        "other_unsuitable": other_unsuitable,
        "planned_surgery": planned_surgery,
        "planned_surgery_date": date_str(surgery_date),
        "washout_extension_reason": text(washout_extension_reason),
    }

missing, errors, ineligible, warnings, parsed_labs = collect_validation()
eligible_candidate = not missing and not errors and not ineligible

st.markdown('<div class="juog-header">5. 中央MDT審査申請</div>', unsafe_allow_html=True)
if missing or errors or ineligible or warnings:
    summary_parts = []
    if missing:
        summary_parts.append(f"未入力 {len(missing)}項目")
    if errors:
        summary_parts.append(f"エラー {len(errors)}件")
    if ineligible:
        summary_parts.append(f"適格性確認 {len(ineligible)}件")
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
        if ineligible:
            st.write("**適格基準上の確認事項**")
            for x in ineligible:
                st.write(f"・{x}")
        if warnings:
            st.write("**確認事項**")
            for x in warnings:
                st.write(f"・{x}")

if eligible_candidate:
    st.success("入力内容は中央MDT審査へ提出可能です。")
elif not missing and not errors and ineligible:
    st.error("現時点では中央MDT審査申請前に適格性を再確認してください。")

if st.button("📨 中央MDT審査を申請", type="primary", use_container_width=True, disabled=bool(missing or errors or ineligible or L)):
    data = build_data(parsed_labs)
    submission_id = str(uuid.uuid4())
    screening_payload = {
        "schema_version": "2026-09-14-v2.2.2",
        "study_code": "JUOG_UTUC_Consolidative",
        "crf_type": "mdt_screening",
        "record_key": f"{facility_code}|{text(local_subject_code)}|mdt_screening",
        "submission_id": submission_id,
        "submitted_at": now_iso(),
        "facility_code": facility_code,
        "facility_name": facility_name,
        "local_subject_code": text(local_subject_code),
        "reporter_email": text(reporter_email),
        "eligibility_candidate": True,
        "warnings": warnings,
        "data": data,
    }
    # First persist the screening workflow record in the central registry.
    # The workflow summary and a full append-only CRF snapshot are stored in the central Google Sheet.
    reg_result = registry_call(
        "submit_screening",
        {
            "facility_code": facility_code,
            "facility_name": facility_name,
            "local_subject_code": text(local_subject_code),
            "reporter_email": text(reporter_email),
            "submission_id": submission_id,
            "consent_date": date_str(consent_date),
            "ct": ct,
            "cn": cn,
            "cm": cm,
            "best_effect": best_effect,
            "site_recist": central_recist,
            "planned_surgery": planned_surgery,
            "planned_surgery_date": date_str(surgery_date),
            "crf_payload": screening_payload,
        },
    )
    if not reg_result.get("ok"):
        msg = reg_result.get("message") or reg_result.get("error") or "中央台帳への登録に失敗しました"
        if reg_result.get("registration_id"):
            msg += f"（既登録番号: {reg_result.get('registration_id')}）"
        st.error(f"中央MDT審査申請を確定できませんでした：{msg}")
    else:
        screening_id = reg_result.get("screening_id", "")
        screening_payload["screening_id"] = screening_id
        report = f"""【JUOG 中央MDT審査申請】
MDT審査受付番号: {screening_id}
施設: {facility_name}
施設内研究対象者識別コード: {text(local_subject_code)}
担当者: {text(reporter_email)}
申請ID: {submission_id}

EVP: {date_str(evp_start)} ～ {date_str(evp_end)} / {courses}コース
最良総合効果: {best_effect}
最初の病勢制御確認日: {date_str(first_control_date)}
施設判定RECIST: {central_recist}
予定術式: {planned_surgery}
手術予定日: {date_str(surgery_date)}

{json_block(screening_payload)}
"""
        sent, err = send_email(
            f"【JUOG MDT申請】【{screening_id}】【{facility_name}】",
            report,
            reporter_email,
        )
        st.session_state.screening_sent = True
        st.session_state.screening_id = screening_id
        st.session_state.screening_email_failed = not sent
        if not sent:
            print(f"[JUOG MDT screening] email failed: {err}")
        st.rerun()
