"""Human-readable, printable JUOG screening CRF receipt.

Pure rendering only. Never logs data, fetches credentials, or sends messages.
Submitted payload is authoritative; do not rebuild a receipt from mutable widgets.
"""
from __future__ import annotations

from html import escape
from typing import Any
import json

# Grouped in the same clinical sequence as the screening form. Any future field
# not listed here is still emitted under '追加項目', so it cannot silently vanish.
_SECTIONS = (
    ("1. 同意・患者背景", (
        ("consent_date", "本人同意取得日"), ("birth_year_month", "生年月（年月のみ）"),
        ("age_at_consent", "同意取得時年齢", "歳"), ("sex", "性別"),
        ("height_cm", "身長", "cm"), ("weight_kg", "体重", "kg"),
        ("ecog_ps", "ECOG Performance Status"), ("pregnancy", "妊娠"),
        ("breastfeeding", "授乳"), ("physical_abnormal", "身体診察の異常所見"),
        ("physical_detail", "身体診察の詳細"), ("past_history", "既往歴"),
        ("comorbidity", "併存疾患"), ("concomitant_meds", "併用薬"),
        ("concomitant_treatment", "併用治療"),
    )),
    ("2. 診断・病期", (
        ("diagnosis_date", "診断日"), ("laterality", "患側"),
        ("primary_site", "原発部位"), ("biopsy_status", "生検"),
        ("biopsy_reason", "生検未実施理由"), ("histology", "組織型"),
        ("histology_other", "その他の組織型"), ("ct", "診断時 cT"),
        ("cn", "診断時 cN"), ("cm", "診断時 cM"),
        ("screening_imaging_date", "診断時画像検査日"),
        ("imaging_utuc_compatible", "画像所見（UTUCに合致）"),
        ("cystoscopy_date", "膀胱鏡実施日"),
        ("cystoscopy_result", "膀胱鏡所見"),
        ("cystoscopy_detail", "膀胱鏡所見の詳細"),
        ("screening_cytology", "尿細胞診"),
    )),
    ("3. 初期評価・臨床検査", (
        ("screening_required_test_omission_reason", "必須検査の未実施理由"),
    )),
    ("4. EVP治療内容・効果", (
        ("evp_start", "EVP開始日"), ("evp_end", "EVP最終投与日"),
        ("evp_courses", "EVPコース数", "コース"),
        ("ev_initial_dose_mgkg", "EV初回投与量", "mg/kg"),
        ("ev_reduction", "EV減量"), ("ev_reduction_detail", "EV減量の詳細"),
        ("pembro_stop", "ペムブロリズマブ中止"),
        ("pembro_stop_detail", "中止の詳細"),
        ("best_effect", "EVP最良総合効果"),
        ("first_disease_control_date", "最初の病勢制御確認日"),
        ("short_course_reason", "治療コース短縮理由"),
    )),
    ("5. 術前再評価・RECIST", (
        ("preop_imaging_date", "術前画像検査日"),
        ("target_nadir_sum_mm", "標的病変の最小径和", "mm"),
        ("site_recist", "施設判定RECIST v1.1"),
        ("new_lesion", "新病変"), ("nontarget_pd", "非標的病変のPD"),
        ("cm1_basis", "cM1の判定根拠"),
        ("cned_date", "cNED判定日"),
        ("cm1_local_therapy", "cM1局所治療"),
        ("cm1_local_therapy_other", "cM1局所治療の詳細"),
    )),
    ("6. 術前安全性・適格性確認", (
        ("g3_unrecovered_ae", "Grade 3以上AEの未回復"),
        ("unresectable_vessel", "切除困難な大血管浸潤"),
        ("unresectable_organ", "切除困難な他臓器浸潤"),
        ("other_cancer", "他の悪性腫瘍"),
        ("other_unsuitable", "その他の不適格要因"),
    )),
    ("7. 手術計画", (
        ("planned_surgery", "予定術式"),
        ("planned_surgery_date", "手術予定日"),
        ("washout_extension_reason", "投与後手術時期の延長理由"),
    )),
)
_VITALS = (
    ("sbp", "収縮期血圧", "mmHg"), ("dbp", "拡張期血圧", "mmHg"),
    ("pulse", "脈拍", "回/分"), ("temperature", "体温", "℃"),
)
_LABS = (
    ("WBC", "白血球数（WBC）", "/μL"), ("Hb", "ヘモグロビン（Hb）", "g/dL"),
    ("PLT", "血小板数（PLT）", "×10⁴/μL"),
    ("Neutro", "好中球", "%"), ("Lympho", "リンパ球", "%"),
    ("Mono", "単球", "%"), ("Eosino", "好酸球", "%"), ("Baso", "好塩基球", "%"),
    ("TP", "総蛋白（TP）", "g/dL"), ("Alb", "アルブミン", "g/dL"),
    ("AST", "AST", "U/L"), ("ALT", "ALT", "U/L"),
    ("ALP", "ALP", "U/L"), ("LDH", "LDH", "U/L"),
    ("T_Bil", "総ビリルビン", "mg/dL"),
    ("Cre", "クレアチニン", "mg/dL"), ("eGFR", "eGFR", "mL/min/1.73m²"),
    ("BUN", "尿素窒素", "mg/dL"), ("Na", "Na", "mEq/L"),
    ("K", "K", "mEq/L"), ("Cl", "Cl", "mEq/L"),
    ("CRP", "CRP", "mg/dL"), ("Glucose", "血糖", "mg/dL"),
)
_RECIST = (
    ("response", "標的病変の補助判定"), ("baseline_sum", "ベースライン径和", "mm"),
    ("followup_sum", "術前径和", "mm"),
    ("change_pct", "ベースラインからの変化率", "%"),
    ("nadir_sum", "最小径和", "mm"),
    ("pd_change_pct_from_nadir", "最小径和からの変化率", "%"),
    ("reason", "補助判定の注記"),
)


def _display(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "あり" if value else "なし"
    if isinstance(value, (list, tuple)):
        return "、".join(_display(x) for x in value) if value else "—"
    if isinstance(value, dict):
        return "／".join(f"{k}: {_display(v)}" for k, v in value.items()) if value else "—"
    return str(value)


def _rows_from(mapping: dict, fields: tuple) -> list[tuple[str, str]]:
    rows = []
    used = set()
    for spec in fields:
        key, label = spec[:2]
        unit = spec[2] if len(spec) > 2 else ""
        used.add(key)
        value = _display(mapping.get(key))
        if value != "—" and unit:
            value = f"{value} {unit}"
        rows.append((label, value))
    # Forward compatibility: do not drop fields added by a future CRF revision.
    for key, val in mapping.items():
        if key not in used:
            rows.append((str(key), _display(val)))
    return rows


def receipt_sections(payload: dict, review_round: int | None = None):
    """Return (title, rows) pairs from the immutable confirmed submission."""
    data = payload.get("data") or {}
    meta = [
        ("MDT審査受付番号", _display(payload.get("screening_id"))),
        ("審査ラウンド", _display(review_round)),
        ("申請施設", _display(payload.get("facility_name"))),
        ("施設内研究対象者識別コード", _display(payload.get("local_subject_code"))),
        ("申請担当者メール", _display(payload.get("reporter_email"))),
        ("申請日時", _display(payload.get("submitted_at"))),
        ("申請ID（照合用）", _display(payload.get("submission_id"))),
    ]
    sections = [("申請情報", meta)]
    handled = {"local_subject_code"}
    for title, fields in _SECTIONS:
        rows = []
        for spec in fields:
            key = spec[0]
            handled.add(key)
            unit = spec[2] if len(spec) > 2 else ""
            value = _display(data.get(key))
            if unit and value != "—":
                value = f"{value} {unit}"
            rows.append((spec[1], value))
        sections.append((title, rows))
        if title.startswith("3."):
            sections.append(("3-1. バイタルサイン", _rows_from(data.get("screening_vitals") or {}, _VITALS)))
            sections.append(("3-2. 検体検査", _rows_from(data.get("screening_labs") or {}, _LABS)))
            handled.update(("screening_vitals", "screening_labs"))
        if title.startswith("5."):
            sections.append(("5-1. 標的病変（入力内容）", [
                (f"病変 {i + 1}", _display(lesion))
                for i, lesion in enumerate(data.get("target_lesions") or [])
            ] or [("標的病変", "登録なし")]))
            sections.append(("5-2. RECIST補助計算（中央判定ではありません）",
                             _rows_from(data.get("target_recist_support") or {}, _RECIST)))
            handled.update(("target_lesions", "target_recist_support"))
    extras = [(str(k), _display(v)) for k, v in data.items() if k not in handled]
    if extras:
        sections.append(("8. 追加項目", extras))
    warnings = payload.get("warnings") or []
    if warnings:
        sections.append(("申請時の確認事項", [("確認事項", _display(warnings))]))
    return sections


def render_receipt_text(payload: dict, review_round: int | None = None) -> str:
    lines = [
        "JUOG-UTUC01 中央MDT審査申請 CRF（申請者控え）",
        "※これは中央MDTへの申請控えです。正式登録・手術適応の確定通知ではありません。",
        "※提出時点の内容を表示しています。旧版のCRF・監査記録はシステムで保持します。",
        "",
    ]
    for heading, rows in receipt_sections(payload, review_round):
        lines.extend([f"【{heading}】", *[f"{label}: {value}" for label, value in rows], ""])
    return "\n".join(lines)


def render_receipt_html(payload: dict, review_round: int | None = None, *, include_print_button: bool = True) -> str:
    """Complete standalone HTML, suitable for email and offline A4 printing."""
    sections_html = []
    for title, rows in receipt_sections(payload, review_round):
        body = "".join(
            "<tr><th scope='row'>" + escape(str(label)) + "</th><td>" +
            escape(str(value)).replace("\n", "<br>") + "</td></tr>"
            for label, value in rows
        )
        sections_html.append(
            "<section><h2>" + escape(title) + "</h2><table>" + body + "</table></section>"
        )
    return """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JUOG-UTUC01 中央MDT審査申請CRF控え</title>
<style>
body{font-family:"Noto Sans JP","Yu Gothic","Meiryo",sans-serif;color:#1e293b;margin:0;background:#fff}
main{max-width:850px;margin:auto;padding:30px 24px 70px}
h1{font-size:21px;color:#132a49;margin-bottom:9px}
.lead{font-size:12px;line-height:1.65;color:#475569;margin:0 0 20px}
section{break-inside:avoid;page-break-inside:avoid;margin:20px 0}
h2{font-size:15px;padding:8px 11px;color:#12334c;background:#eaf2f5;border-left:4px solid #147d82;margin:0 0 8px}
table{border-collapse:collapse;width:100%;font-size:12px;table-layout:fixed}
th,td{text-align:left;vertical-align:top;padding:7px 9px;border-bottom:1px solid #dde5eb;line-height:1.5;overflow-wrap:anywhere}
th{width:38%;font-weight:600;background:#f8fafc}
.print-button{padding:8px 16px;border:1px solid #147d82;color:#075a61;background:white;border-radius:5px;cursor:pointer}
footer{font-size:11px;color:#64748b;border-top:1px solid #ddd;margin-top:28px;padding-top:12px}
@page{size:A4;margin:14mm}
@media print{main{padding:0;max-width:100%}.print-button{display:none}section{margin:13px 0}h2{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
</style></head><body><main>
""" + ('<button type="button" class="print-button" onclick="window.print()">印刷／PDF保存</button>'
       if include_print_button else '') + """
<h1>JUOG-UTUC01 中央MDT審査申請 CRF（申請者控え）</h1>
<p class="lead">中央MDTへの申請控えです。正式登録・手術適応の確定通知ではありません。<br>
提出時点の内容を表示しています。申請内容の修正はシステムの正式な手続きで行ってください。</p>
""" + "\n".join(sections_html) + """
<footer>JUOG-UTUC01 eCRF — 提出済みデータから作成した申請者控え。原本は中央台帳と監査記録で管理します。</footer>
</main></body></html>"""
