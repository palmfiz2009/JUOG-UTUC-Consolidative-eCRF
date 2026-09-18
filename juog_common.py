from __future__ import annotations

import json
import re
import ssl
import urllib.request
import urllib.error
import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

STUDY_CODE = "JUOG_UTUC_Consolidative"
SCHEMA_VERSION = "2026-09-14-v2.2.2"
TZ = ZoneInfo("Asia/Tokyo")

# Canonical institution names follow the protocol (2026-09-14, v3).
FACILITIES = [
    ("F01", "愛知県がんセンター"),
    ("F02", "秋田大学"),
    ("F03", "愛媛大学"),
    ("F04", "大分大学"),
    ("F05", "岡山大学"),
    ("F06", "大阪公立大学"),
    ("F07", "大阪大学"),
    ("F08", "大阪府済生会野江病院"),
    ("F09", "香川大学"),
    ("F10", "鹿児島大学"),
    ("F11", "関西医科大学"),
    ("F12", "岐阜大学"),
    ("F13", "九州大学病院"),
    ("F14", "京都大学"),
    ("F15", "久留米大学"),
    ("F16", "神戸大学"),
    ("F17", "国立がん研究センター中央病院"),
    ("F18", "国立病院機構四国がんセンター"),
    ("F19", "札幌医科大学"),
    ("F20", "千葉大学"),
    ("F21", "筑波大学"),
    ("F22", "東京科学大学"),
    ("F23", "東京慈恵会医科大学附属柏病院"),
    ("F24", "東京慈恵会医科大学"),
    ("F25", "東北大学"),
    ("F26", "鳥取大学"),
    ("F27", "富山大学"),
    ("F28", "長崎大学病院"),
    ("F29", "名古屋大学"),
    ("F30", "奈良県立医科大学"),
    ("F31", "新潟大学大学院 医歯学総合研究科"),
    ("F32", "浜松医科大学"),
    ("F33", "原三信病院"),
    ("F34", "兵庫医科大学"),
    ("F35", "弘前大学"),
    ("F36", "北海道大学"),
    ("F37", "三重大学"),
    ("F38", "横浜市立大学"),
    ("F39", "琉球大学"),
    ("F40", "和歌山県立医科大学"),
]
FACILITY_NAME_TO_CODE = {name: code for code, name in FACILITIES}
FACILITY_CODE_TO_NAME = {code: name for code, name in FACILITIES}
FACILITY_NAMES = [name for _, name in FACILITIES]

REGISTRATION_ID_RE = re.compile(r"^JUOG-\d{3,4}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# Protocol-required blood tests (8.1.2 / schedule table).
LAB_FIELDS = [
    ("WBC", "WBC", "/μL"),
    ("Hb", "Hb", "g/dL"),
    ("PLT", "PLT", "×10^4/μL"),
    ("Neutro", "Neutro", "%"),
    ("Lympho", "Lympho", "%"),
    ("Mono", "Mono", "%"),
    ("Eosino", "Eosino", "%"),
    ("Baso", "Baso", "%"),
    ("ALP", "ALP", "U/L"),
    ("T_Bil", "T-Bil", "mg/dL"),
    ("Alb", "Alb", "g/dL"),
    ("AST", "AST", "U/L"),
    ("ALT", "ALT", "U/L"),
    ("TP", "TP", "g/dL"),
    ("LDH", "LDH", "U/L"),
    ("Cre", "Cre", "mg/dL"),
    ("eGFR", "eGFR", "mL/min/1.73m²"),
    ("BUN", "BUN", "mg/dL"),
    ("Na", "Na", "mEq/L"),
    ("K", "K", "mEq/L"),
    ("Cl", "Cl", "mEq/L"),
    ("CRP", "CRP", "mg/dL"),
]
DIFF_KEYS = {"Neutro", "Lympho", "Mono", "Eosino", "Baso"}

CYTOLOGY_OPTIONS = [
    "選択してください",
    "Negative (クラスI・II)",
    "AUC (非定型細胞)",
    "SHGUC (高異型度癌疑い)",
    "HGUC (クラスIV・V相当)",
    "LGUC (低異型度腫瘍)",
    "判定不能",
    "未実施",
]
POSITIVE_CYTOLOGY = {"SHGUC (高異型度癌疑い)", "HGUC (クラスIV・V相当)", "LGUC (低異型度腫瘍)"}


POSTOP_TREATMENT_OPTIONS = [
    "選択してください",
    "無治療（経過観察）",
    "術前からのEVP継続投与",
    "術前からのEV単独継続（間欠療法等を含む）",
    "術前からのペムブロリズマブ単剤継続",
    "ニボルマブ単剤（術後補助療法）",
    "GC療法（術後補助療法）",
    "GCarbo療法（術後補助療法）",
    "HER2標的ADC",
    "サシツズマブ ゴビテカン（SG）",
    "FGFR阻害薬",
    "放射線治療",
    "治験（TROP2標的ADC、その他）",
    "その他",
]

RECURRENCE_DRUG_OPTIONS = [
    "プラチナ製剤併用療法（GC療法）",
    "プラチナ製剤併用療法（GCarbo療法）",
    "維持療法（アベルマブ等）",
    "EVP療法",
    "ペムブロリズマブ単剤",
    "ニボルマブ単剤",
    "HER2標的ADC",
    "サシツズマブ ゴビテカン（SG）",
    "FGFR阻害薬",
    "放射線治療",
    "治験（TROP2標的ADC、その他）",
]

CD_OPTIONS = ["選択してください", "Grade 0", "Grade I", "Grade II", "Grade IIIa", "Grade IIIb", "Grade IVa", "Grade IVb", "Grade V"]
CD_MAJOR = {"Grade IIIa", "Grade IIIb", "Grade IVa", "Grade IVb", "Grade V"}


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def today_jst() -> date:
    return datetime.now(TZ).date()


def valid_email(value: str | None) -> bool:
    return bool(value and EMAIL_RE.fullmatch(value.strip()))


def valid_registration_id(value: str | None) -> bool:
    return bool(value and REGISTRATION_ID_RE.fullmatch(value.strip().upper()))


def add_months(d: date, months: int) -> date:
    month0 = d.month - 1 + months
    year = d.year + month0 // 12
    month = month0 % 12 + 1
    day = min(d.day, monthrange(year, month)[1])
    return date(year, month, day)


def age_on_date(birth_date: date | None, reference_date: date | None) -> int | None:
    if not birth_date or not reference_date:
        return None
    return reference_date.year - birth_date.year - ((reference_date.month, reference_date.day) < (birth_date.month, birth_date.day))


def date_str(v) -> str:
    return v.isoformat() if isinstance(v, date) else ("" if v is None else str(v))


def text(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def unique_messages(items):
    return list(dict.fromkeys([x for x in items if x]))


def window_info(anchor: date | None, target_days: int, tolerance_days: int):
    if not anchor:
        return None
    target = anchor + timedelta(days=target_days)
    return {
        "target": target,
        "min": target - timedelta(days=tolerance_days),
        "max": target + timedelta(days=tolerance_days),
    }


def in_window(value: date | None, min_date: date | None, max_date: date | None) -> bool:
    return bool(value and min_date and max_date and min_date <= value <= max_date)


def validate_anthropometrics(height_cm, weight_kg):
    """Hard-stop only clearly implausible / likely digit-entry errors.

    Deliberately broad ranges: this is not a clinical normal-range check.
    A 200 kg patient is accepted; 300 kg is rejected as a likely input error for this trial.
    """
    errors = []
    if height_cm is not None and not (80.0 <= float(height_cm) <= 250.0):
        errors.append("身長は80〜250 cmの範囲で入力してください（桁・単位を確認してください）")
    if weight_kg is not None and not (20.0 <= float(weight_kg) < 300.0):
        errors.append("体重は20〜300 kg未満の範囲で入力してください（桁・単位を確認してください）")
    return errors


def validate_vitals(sbp, dbp, pulse, temperature, prefix=""):
    """Hard-stop only impossible/very implausible values and SBP/DBP reversal."""
    errors = []
    lead = f"{prefix}：" if prefix else ""
    if sbp is not None and not (40 <= float(sbp) <= 300):
        errors.append(f"{lead}収縮期血圧は40〜300 mmHgの範囲で入力してください（桁を確認してください）")
    if dbp is not None and not (20 <= float(dbp) <= 200):
        errors.append(f"{lead}拡張期血圧は20〜200 mmHgの範囲で入力してください（桁を確認してください）")
    if pulse is not None and not (20 <= float(pulse) <= 250):
        errors.append(f"{lead}脈拍は20〜250 /minの範囲で入力してください（桁を確認してください）")
    if temperature is not None and not (25.0 <= float(temperature) <= 45.0):
        errors.append(f"{lead}体温は25〜45 ℃の範囲で入力してください（桁・単位を確認してください）")
    if sbp is not None and dbp is not None and float(dbp) >= float(sbp):
        errors.append(f"{lead}拡張期血圧が収縮期血圧以上になっています。入力を確認してください")
    return errors


def parse_lab_value(raw):
    s = "" if raw is None else str(raw).strip()
    if not s:
        return "blank", None
    if s.upper() in {"NA", "N/A", "未実施", "欠測"}:
        return "na", None
    try:
        return "value", float(s)
    except ValueError:
        return "invalid", None


def validate_lab_panel(raw_values: dict, required: bool):
    errors, warnings, parsed = [], [], {}
    labels = {k: label for k, label, _ in LAB_FIELDS}
    for key, _, _ in LAB_FIELDS:
        state, num = parse_lab_value(raw_values.get(key, ""))
        if state == "blank":
            if required:
                errors.append(f"{labels[key]}：空欄です（未測定の場合はNAと入力）")
            parsed[key] = None
        elif state == "na":
            parsed[key] = None
            warnings.append(f"{labels[key]}：NA")
        elif state == "invalid":
            errors.append(f"{labels[key]}：数値またはNAで入力してください")
            parsed[key] = None
        else:
            parsed[key] = num
            if num is not None and num < 0:
                errors.append(f"{labels[key]}：負の値は入力できません")
            if key in DIFF_KEYS and num is not None and num > 100:
                errors.append(f"{labels[key]}：100%を超えています")
    return parsed, unique_messages(errors), unique_messages(warnings)


def lab_payload(raw_values: dict):
    parsed, _, _ = validate_lab_panel(raw_values, required=False)
    return parsed


def recist_target_response(lesions: list[dict], new_lesion: bool = False, nontarget_pd: bool = False, nadir_sum: float | None = None):
    """Supportive RECIST 1.1 target-lesion calculation.

    This is NOT a substitute for central radiology overall RECIST assessment.
    Each lesion dict contains baseline/followup and is_node. Lymph nodes use short axis.
    PR is referenced to baseline. PD is referenced to the smallest sum on study (nadir),
    so target-lesion PD is not asserted when nadir is unavailable.
    """
    if new_lesion or nontarget_pd:
        return {
            "response": "PD", "baseline_sum": None, "followup_sum": None,
            "change_pct": None, "nadir_sum": nadir_sum, "pd_change_pct_from_nadir": None,
            "reason": "new lesion / unequivocal non-target progression",
        }
    measured = [x for x in lesions if x.get("baseline") is not None]
    if not measured:
        return {
            "response": "NE", "baseline_sum": None, "followup_sum": None,
            "change_pct": None, "nadir_sum": nadir_sum, "pd_change_pct_from_nadir": None,
            "reason": "no target-lesion measurements",
        }
    if any(x.get("followup") is None for x in measured):
        return {
            "response": "NE", "baseline_sum": None, "followup_sum": None,
            "change_pct": None, "nadir_sum": nadir_sum, "pd_change_pct_from_nadir": None,
            "reason": "missing follow-up measurement",
        }
    base = sum(float(x["baseline"]) for x in measured)
    follow = sum(float(x["followup"]) for x in measured)
    if base <= 0:
        return {
            "response": "NE", "baseline_sum": base, "followup_sum": follow,
            "change_pct": None, "nadir_sum": nadir_sum, "pd_change_pct_from_nadir": None,
            "reason": "baseline sum <= 0",
        }
    change = (follow - base) / base * 100.0
    all_cr = all((float(x["followup"]) < 10.0 if x.get("is_node") else float(x["followup"]) == 0.0) for x in measured)
    pd_change = None
    target_pd = False
    if nadir_sum is not None and nadir_sum > 0:
        pd_change = (follow - float(nadir_sum)) / float(nadir_sum) * 100.0
        target_pd = pd_change >= 20.0 and (follow - float(nadir_sum)) >= 5.0
    if all_cr:
        resp = "CR"
    elif target_pd:
        # Once PD criteria relative to nadir are met, PD takes precedence over a baseline-based PR.
        resp = "PD"
    elif change <= -30.0:
        resp = "PR"
    elif nadir_sum is None:
        resp = "SD/PD要nadir確認"
    else:
        resp = "SD"
    return {
        "response": resp, "baseline_sum": base, "followup_sum": follow,
        "change_pct": change, "nadir_sum": nadir_sum, "pd_change_pct_from_nadir": pd_change,
        "reason": "supportive target-lesion calculation",
    }


def make_submission_metadata(crf_type: str, visit: str, registration_id: str, facility_code: str, facility_name: str, reporter_email: str, submission_kind: str = "初回報告", correction_reason: str = ""):
    return {
        "schema_version": SCHEMA_VERSION,
        "study_code": STUDY_CODE,
        "crf_type": crf_type,
        "visit": visit,
        "record_key": f"{registration_id}|{crf_type}|{visit}",
        "submission_id": str(uuid.uuid4()),
        "submitted_at": now_iso(),
        "submission_kind": submission_kind,
        "correction_reason": correction_reason,
        "registration_id": registration_id,
        "facility_code": facility_code,
        "facility_name": facility_name,
        "reporter_email": reporter_email,
    }


def json_block(payload: dict) -> str:
    return "--- MACHINE_READABLE_JSON_START ---\n" + json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str) + "\n--- MACHINE_READABLE_JSON_END ---"


def get_secret(path: tuple[str, ...]):
    import streamlit as st
    obj = st.secrets
    for part in path:
        obj = obj[part]
    return obj


def _office_email_addresses():
    """Return office notification recipients.

    Preferred configuration in Streamlit Secrets:
    [office]
    emails = ["office1@example.org", "office2@example.org"]

    Falls back to the two legacy office recipients so existing deployments
    continue to work until [office] is configured.
    """
    import streamlit as st
    fallback = ["urosec@kmu.ac.jp", "yoshida.tks@kmu.ac.jp"]
    try:
        raw = st.secrets["office"]["emails"]
        if isinstance(raw, str):
            raw = [raw]
        addrs = []
        for value in raw:
            addr = str(value).strip()
            if addr and addr not in addrs:
                addrs.append(addr)
        return addrs or fallback
    except Exception:
        return fallback


def _smtp_send(subject: str, content: str, to_addrs: list[str]):
    import streamlit as st
    try:
        mail_user = st.secrets["email"]["user"]
        mail_pass = st.secrets["email"]["pass"]
        clean = []
        for value in to_addrs:
            addr = str(value).strip()
            if addr and addr not in clean:
                clean.append(addr)
        if not clean:
            return False, "NO_RECIPIENTS"

        msg = MIMEMultipart()
        msg["From"] = mail_user
        msg["To"] = ", ".join(clean)
        msg["Subject"] = subject
        msg.attach(MIMEText(content, "plain", "utf-8"))

        import smtplib
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(mail_user, mail_pass)
            server.send_message(msg)
        return True, None
    except Exception as exc:
        return False, str(exc)


def send_office_email(subject: str, content: str):
    """Send a notification to the JUOG office only."""
    return _smtp_send(subject, content, _office_email_addresses())


def send_support_email(subject: str, content: str):
    """Send an eCRF support request to the designated support address only."""
    return _smtp_send(subject, content, ["yoshida.tks@kmu.ac.jp"])


def send_direct_email(to_addr: str, subject: str, content: str):
    """Send an e-mail only to one explicitly specified recipient."""
    addr = (to_addr or "").strip()
    if not valid_email(addr):
        return False, "INVALID_RECIPIENT"
    return _smtp_send(subject, content, [addr])


def send_email(subject: str, content: str, reporter_email: str | None = None):
    """Send an office notification, optionally also to the submitting facility."""
    to_addrs = _office_email_addresses()
    if reporter_email:
        addr = reporter_email.strip()
        if addr and addr not in to_addrs:
            to_addrs.append(addr)
    return _smtp_send(subject, content, to_addrs)


def registry_call(action: str, payload: dict | None = None, timeout: int = 20):
    """Call the central registration service.

    Expected Streamlit secrets:
    [registry]
    url = "https://script.google.com/macros/s/.../exec"
    token = "..."
    """
    import streamlit as st
    try:
        url = st.secrets["registry"]["url"]
        token = st.secrets["registry"]["token"]
    except Exception:
        return {"ok": False, "error": "REGISTRY_NOT_CONFIGURED"}
    body = {"action": action, "token": token, "payload": payload or {}}
    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False, default=str).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    # Google Apps Script ContentService may transiently fail while resolving its
    # one-time redirect URL. Retry a small number of times from the canonical
    # /exec endpoint; persistent configuration errors still surface unchanged.
    import time
    retryable_http = {404, 408, 429, 500, 502, 503, 504}
    last_error = None
    for attempt in range(3):
        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as res:
                text_body = res.read().decode("utf-8")
            data = json.loads(text_body)
            return data if isinstance(data, dict) else {"ok": False, "error": "INVALID_RESPONSE"}
        except urllib.error.HTTPError as exc:
            last_error = {"ok": False, "error": f"HTTP_{exc.code}"}
            if exc.code not in retryable_http or attempt == 2:
                return last_error
            time.sleep(0.6 * (attempt + 1))
        except Exception as exc:
            last_error = {"ok": False, "error": f"REGISTRY_ERROR:{exc}"}
            if attempt == 2:
                return last_error
            time.sleep(0.6 * (attempt + 1))
    return last_error or {"ok": False, "error": "REGISTRY_ERROR:UNKNOWN"}




def save_crf_payload(payload: dict, timeout: int = 30):
    """Persist one eCRF submission to the central Google Sheet service.

    The service is append-only at the submission level. A correction creates a new
    version for the same record_key; the prior submission remains in the audit trail.
    """
    return registry_call("save_crf", {"payload": payload}, timeout=timeout)


def save_crf_draft(
    registration_id: str,
    crf_type: str,
    visit: str,
    draft_state: dict,
    facility_code: str = "",
    facility_name: str = "",
    reporter_email: str = "",
    timeout: int = 30,
):
    """Upsert a non-final eCRF draft owned by the entered reporter e-mail."""
    return registry_call(
        "save_draft",
        {
            "registration_id": (registration_id or "").strip().upper(),
            "crf_type": crf_type,
            "visit": visit,
            "facility_code": facility_code or "",
            "facility_name": facility_name or "",
            "reporter_email": (reporter_email or "").strip(),
            "schema_version": SCHEMA_VERSION,
            "draft_state": draft_state or {},
        },
        timeout=timeout,
    )


def get_crf_draft(registration_id: str, crf_type: str, visit: str, reporter_email: str, timeout: int = 30):
    """Fetch a saved draft after matching the draft owner e-mail address."""
    return registry_call(
        "get_draft",
        {
            "registration_id": (registration_id or "").strip().upper(),
            "crf_type": crf_type,
            "visit": visit,
            "reporter_email": (reporter_email or "").strip(),
        },
        timeout=timeout,
    )


def delete_crf_draft(registration_id: str, crf_type: str, visit: str, timeout: int = 30):
    """Delete a draft after the corresponding CRF has been formally submitted."""
    return registry_call(
        "delete_draft",
        {
            "registration_id": (registration_id or "").strip().upper(),
            "crf_type": crf_type,
            "visit": visit,
        },
        timeout=timeout,
    )


def capture_draft_state(prefix: str, *, exclude_prefixes: tuple[str, ...] = (), overrides: dict | None = None):
    """Serialize selected Streamlit session-state values with enough type data to restore widgets."""
    import streamlit as st

    out = {}
    for key in list(st.session_state.keys()):
        if not str(key).startswith(prefix):
            continue
        if any(str(key).startswith(x) for x in exclude_prefixes):
            continue
        value = st.session_state[key]
        if isinstance(value, datetime):
            out[str(key)] = {"type": "datetime", "value": value.isoformat()}
        elif isinstance(value, date):
            out[str(key)] = {"type": "date", "value": value.isoformat()}
        elif value is None or isinstance(value, (str, int, float, bool, list, dict)):
            out[str(key)] = {"type": "value", "value": value}

    for key, value in (overrides or {}).items():
        if isinstance(value, datetime):
            out[str(key)] = {"type": "datetime", "value": value.isoformat()}
        elif isinstance(value, date):
            out[str(key)] = {"type": "date", "value": value.isoformat()}
        else:
            out[str(key)] = {"type": "value", "value": value}
    return out


def clear_session_state_prefixes(prefixes: tuple[str, ...] | list[str]):
    """Clear form widget state before restoring a saved draft."""
    import streamlit as st

    for key in list(st.session_state.keys()):
        if any(str(key).startswith(prefix) for prefix in prefixes):
            del st.session_state[key]


def restore_draft_state(draft_state: dict):
    """Restore values produced by capture_draft_state into Streamlit session state."""
    import streamlit as st

    for key, item in (draft_state or {}).items():
        if not isinstance(item, dict) or "value" not in item:
            continue
        kind = str(item.get("type") or "value")
        value = item.get("value")
        try:
            if kind == "date" and value:
                value = date.fromisoformat(str(value)[:10])
            elif kind == "datetime" and value:
                value = datetime.fromisoformat(str(value))
        except Exception:
            continue
        st.session_state[str(key)] = value

def validate_registry_id(registration_id: str, facility_code: str):
    if not valid_registration_id(registration_id):
        return False, "JUOG登録番号の形式が不正です（例：JUOG-001）"
    result = registry_call("validate", {"registration_id": registration_id.strip().upper(), "facility_code": facility_code})
    if result.get("ok"):
        return True, ""
    if result.get("error") == "REGISTRY_NOT_CONFIGURED":
        # Keep the CRF usable during setup, but make the limitation explicit to the UI.
        return None, "中央登録台帳との照合は未設定です。形式チェックのみ実施しました。"
    return False, result.get("message") or result.get("error") or "中央登録台帳で確認できませんでした"


def render_facility(label="施設名*", key="facility_name", disabled=False):
    import streamlit as st
    options = ["選択してください"] + FACILITY_NAMES
    current = st.session_state.get(key, "選択してください")
    try:
        idx = options.index(current)
    except ValueError:
        idx = 0
    name = st.selectbox(label, options, index=idx, key=f"widget_{key}", disabled=disabled)
    st.session_state[key] = name
    code = FACILITY_NAME_TO_CODE.get(name, "")
    return code, name


def render_lab_panel(prefix: str, required: bool, disabled=False, columns=2):
    import streamlit as st
    st.caption("数値を入力してください。未測定・欠測の場合は NA と入力してください。0 は実測値として保存されます。")
    cols = st.columns(columns)
    out = {}
    for i, (key, label, unit) in enumerate(LAB_FIELDS):
        session_key = f"{prefix}_{key}"
        if session_key not in st.session_state:
            st.session_state[session_key] = ""
        star = "*" if required else ""
        out[key] = cols[i % columns].text_input(
            f"{label} ({unit}){star}",
            value=st.session_state[session_key],
            key=f"widget_{session_key}",
            disabled=disabled,
        )
        st.session_state[session_key] = out[key]
    return out


def render_cytology(prefix: str, required: bool, disabled=False):
    import streamlit as st
    star = "*" if required else ""
    return st.selectbox(
        f"尿細胞診{star}",
        CYTOLOGY_OPTIONS,
        key=f"{prefix}_cytology",
        disabled=disabled,
    )


def validate_cytology(value: str, required: bool):
    if required and value in {None, "", "選択してください"}:
        return ["尿細胞診"]
    return []

def render_submission_kind(prefix: str, disabled=False):
    import streamlit as st
    kind = st.radio("報告種別*", ["初回報告", "訂正報告"], horizontal=True, key=f"{prefix}_submission_kind", disabled=disabled)
    reason = ""
    if kind == "訂正報告":
        reason = st.text_area("訂正理由*", key=f"{prefix}_correction_reason", disabled=disabled)
    return kind, reason
