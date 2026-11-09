"""AppTest evidence probes against the actual existing Streamlit application source.

Unlike browser Playwright, st.testing.v1.AppTest does not require a remote
Streamlit Cloud viewer session. Tests use placeholder secrets, loopback-only
registry URL, no actual registry listener, and NEVER submit/modify cases.
These tests supply supporting evidence, not automatic formal UAT PASS.
"""
from __future__ import annotations

import json
import unittest
from datetime import date, timedelta
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "apptest-artifacts"
OUT.mkdir(exist_ok=True, parents=True)
APP = ROOT / "streamlit_app.py"

checks: list[dict] = []


def probe(name, fn):
    try:
        detail = fn()
    except Exception as exc:
        checks.append({"check": name, "result": "FAIL", "detail": repr(exc)[:300]})
        raise
    checks.append({"check": name, "result": "PASS", "detail": str(detail)[:300]})


def start():
    app = AppTest.from_file(str(APP), default_timeout=40).run()
    assert not app.exception, "AppTest exception at entrypoint: " + repr(app.exception)
    return app


def switch(app, page):
    app.switch_page(page).run(timeout=40)
    assert not app.exception, f"AppTest exception in {page}: {app.exception}"
    return app


def by_label(widgets, label):
    matches = [w for w in widgets if w.label == label]
    assert len(matches) == 1, f"Expected one {label}: {len(matches)}"
    return matches[0]


class CurrentStreamlitSourceChecks(unittest.TestCase):
    def test_all_six_existing_pages_can_render_without_browser(self):
        def work():
            at = start()
            expected = [
                ("01_registration_crf.py", "中央MDT審査申請CRF"),
                ("02_perioperative_30d_crf.py", "周術期・術後30日CRF"),
                ("03_day90_crf.py", "術後90日CRF"),
                ("04_followup_crf.py", "定期経過報告CRF"),
                ("06_mdt_reviewer.py", "中央MDT判定者専用"),
                ("05_admin_mdt_registration.py", "事務局専用：中央MDT集約"),
            ]
            for path, title in expected:
                switch(at, path)
                titles = [t.value for t in at.title]
                assert any(title in t for t in titles), f"{path} titles={titles}"
            return "All 6 router pages rendered in AppTest, no network or save"
        probe("SRC-APPTEST-6PAGE-RENDER", work)

    def test_scr01_blank_consent_prevents_submit(self):
        def work():
            at = start()
            consent = at.get_by_key("reg_consent_date")
            assert consent.value is None, f"Expected blank consent date, got {consent.value}"
            submit = by_label(at.button, "📨 中央MDT審査を申請")
            assert submit.disabled, "Central MDT submit was enabled without written consent"
            return "Consent=None, submit.disabled=True"
        probe("SCR-01-partial-no-consent", work)

    def test_scr02_non_stage4_flags_before_submission(self):
        def work():
            at = start()
            at.get_by_key("reg_ct").select("cT3").run()
            at.get_by_key("reg_cn").select("cN0").run()
            at.get_by_key("reg_cm").select("cM0").run()
            assert not at.exception, repr(at.exception)
            submit = by_label(at.button, "📨 中央MDT審査を申請")
            assert submit.disabled, "cT3N0M0 must not be accepted"
            message = "\n".join(str(getattr(e, "value", "")) for e in list(at.markdown)+list(at.info)+list(at.error)+list(at.warning))
            assert "Stage IV" in message or "Stage Ⅳ" in message or "病期" in message, (
                "No visible stage eligibility rationale found; submit disabled alone is not discriminative")
            return "cT3N0M0 selectboxes, disabled submission, stage rationale"
        probe("SCR-02-partial-non-stage4", work)

    def test_scr09_ecog2_disallowed_vs_ecog1(self):
        def work():
            at = start()
            at.get_by_key("reg_ecog").set_value("2").run()
            assert not at.exception, repr(at.exception)
            message2 = "\n".join(str(getattr(e, "value", "")) for e in list(at.markdown)+list(at.info)+list(at.error)+list(at.warning))
            assert "ECOG PSが2以上" in message2, f"ECOG 2 rejection not shown: {message2[-500:]}"
            at.get_by_key("reg_ecog").set_value("1").run()
            message1 = "\n".join(str(getattr(e, "value", "")) for e in list(at.markdown)+list(at.info)+list(at.error)+list(at.warning))
            assert "ECOG PSが2以上" not in message1, "ECOG 1 was incorrectly rejected"
            return "ECOG 2 ineligible rationale; ECOG 1 passes this one condition"
        probe("SCR-09-partial-ecog-boundary", work)

    def test_admin_wrong_password_rejected_without_registry_call(self):
        def work():
            at = switch(start(), "05_admin_mdt_registration.py")
            pw = by_label(at.text_input, "事務局パスワード")
            pw.set_value("DEFINITELY-WRONG-ADMIN-PASSWORD-20261110")
            login = by_label(at.button, "ログイン")
            login.click().run()
            assert not at.exception, repr(at.exception)
            msgs = [str(x.value) for x in at.error]
            assert any("パスワードが違います" in m for m in msgs), msgs
            assert not any(getattr(x, "label", "") == "ログアウト" for x in at.button), (
                "Authenticated controls unexpectedly visible")
            return "Wrong admin password rejected before any read/write operations"
        probe("AUTH-01-partial-wrong-admin-password", work)

    def test_reviewer_wrong_role_password_rejected(self):
        def work():
            at = switch(start(), "06_mdt_reviewer.py")
            role = by_label(at.selectbox, "担当領域")
            role.select("radiology").run()
            by_label(at.text_input, "判定者パスワード").set_value("WRONG-REVIEWER-PASSWORD")
            by_label(at.button, "ログイン").click().run()
            assert not at.exception, repr(at.exception)
            errors = [str(x.value) for x in at.error]
            assert any("パスワードが違います" in e for e in errors), errors
            return "Radiology invalid credential rejected without registry requests"
        probe("AUTH-02-partial-invalid-reviewer", work)

    def test_day90_followup_require_real_subject_linkage(self):
        def work():
            at = switch(start(), "03_day90_crf.py")
            assert any(x.label == "既存情報を取得" for x in at.button), "90d source lookup missing"
            at = switch(at, "04_followup_crf.py")
            assert any(x.label == "既存情報を取得" for x in at.button), "followup source lookup missing"
            return "Both downstream forms expose source-linkage action, not triggered"
        probe("POST-05-partial-source-linkage-control", work)



    def test_scr08_age_19_vs_20(self):
        def work():
            at = start()
            at.get_by_key("reg_consent_date").set_value(date(2026, 9, 15)).run()
            at.get_by_key("reg_birth_date").set_value(date(2007, 9, 1)).run()
            underage = "\n".join(str(x.value) for x in list(at.markdown)+list(at.error))
            assert "同意取得時年齢が20歳未満" in underage, underage[-500:]
            at.get_by_key("reg_birth_date").set_value(date(2006, 9, 1)).run()
            adult = "\n".join(str(x.value) for x in list(at.markdown)+list(at.error))
            assert "同意取得時年齢が20歳未満" not in adult, adult[-500:]
            return "Age 19 excluded, 20 not excluded on age (other fields remain blank)"
        probe("SCR-08-partial-age-boundary", work)

    def test_scr03_04_stageiv_routes(self):
        def work():
            at = start()
            at.get_by_key("reg_ct").select("cT3").run()
            at.get_by_key("reg_cn").select("cN0").run()
            at.get_by_key("reg_cm").select("cM0").run()
            def screen_text():
                return "\n".join(str(x.value) for x in list(at.markdown)+list(at.error))
            assert "診断時Stage IV" in screen_text(), "Non-Stage-IV guard missing"
            at.get_by_key("reg_ct").select("cT4").run()
            assert "診断時Stage IV" not in screen_text(), "T4N0M0 incorrectly excluded for stage"
            at.get_by_key("reg_ct").select("cT3").run()
            at.get_by_key("reg_cn").select("cN1").run()
            assert "診断時Stage IV" not in screen_text(), "T3N1M0 incorrectly excluded for stage"
            return "cT3N0M0 rejected; cT4N0M0 and cT3N1M0 pass Stage-IV-only check"
        probe("SCR-03-04-partial-stageiv-eligibility", work)

    def test_scr10_short_course_63_day_boundary(self):
        def work():
            at = start()
            at.get_by_key("reg_courses").set_value(2).run()
            at.get_by_key("reg_short_course_reason").set_value("Synthetic UAT reason").run()
            at.get_by_key("reg_evp_start").set_value(date(2026, 10, 1)).run()
            def screen_text():
                return "\n".join(str(x.value) for x in list(at.markdown)+list(at.error))
            assert "EVP 3コース未満かつ初回投与から63日未満" in screen_text(), "Short interval not rejected"
            at.get_by_key("reg_evp_start").set_value(date(2026, 7, 1)).run()
            assert "EVP 3コース未満かつ初回投与から63日未満" not in screen_text(), "Long interval still rejected"
            return "<3 course UAT rejects 40d but not 132d; exception rationale supplied"
        probe("SCR-10-partial-63day-boundary", work)

    def test_scr07_cm1_cned_duration_under_3mo(self):
        def work():
            at = start()
            at.get_by_key("reg_cm").select("cM1").run()
            at.get_by_key("reg_cm1_basis").set_value("局所療法後にcNEDとなり3か月以上維持").run()
            at.get_by_key("reg_cned_date").set_value(date(2026, 10, 1)).run()
            def screen_text():
                return "\n".join(str(x.value) for x in list(at.markdown)+list(at.error))
            assert "cNEDの3か月維持期間不足" in screen_text(), "cNED too short not reported"
            at.get_by_key("reg_cned_date").set_value(date(2026, 5, 1)).run()
            assert "cNEDの3か月維持期間不足" not in screen_text(), "Mature cNED incorrectly rejected"
            return "cM1 cNED duration <3 months rejected, >3 months not duration-rejected"
        probe("SCR-07-partial-cned-duration", work)

    def test_reg09_surgery_interval_4_8_12_week_screening(self):
        def work():
            at = start()
            at.get_by_key("reg_evp_end").set_value(date(2026, 7, 1)).run()
            def messages():
                return "\n".join(str(x.value) for x in list(at.error)+list(at.warning)+list(at.success)+list(at.markdown))
            at.get_by_key("reg_surgery_date").set_value(date(2026, 7, 22)).run()  # 3 weeks
            assert "4週未満" in messages(), "3-week surgery window rejection missing"
            at.get_by_key("reg_surgery_date").set_value(date(2026, 8, 26)).run()  # 8 weeks
            assert "原則の4–8週内" in messages(), "8-week acceptance banner missing"
            at.get_by_key("reg_surgery_date").set_value(date(2026, 9, 2)).run()  # 9 weeks
            assert "8週を超えています" in messages(), "9-week extension warning missing"
            assert any(x.label == "8週超となる理由*" for x in at.text_area)
            at.get_by_key("reg_surgery_date").set_value(date(2026, 9, 30)).run()  # 13 weeks
            assert "12週を超えています" in messages(), "13-week rejection missing"
            return "3w rejected, 8w standard, 9w deviation reason required, 13w rejected"
        probe("REG-09-partial-protocol-washout", work)

    def test_scr12_glucose_zero_na_negative_values(self):
        def work():
            at = start()
            at.get_by_key("reg_screen_glucose_raw").set_value("-1").run()
            def messages():
                return "\n".join(str(x.value) for x in list(at.error)+list(at.warning)+list(at.markdown))
            assert "血糖に負の値は入力できません" in messages(), "negative glucose not rejected"
            at.get_by_key("reg_screen_glucose_raw").set_value("0").run()
            assert "血糖に負の値は入力できません" not in messages(), "0 should be real measurement"
            at.get_by_key("reg_screen_glucose_raw").set_value("NA").run()
            assert "スクリーニング血液検査：血糖：NA" in messages(), "NA not flagged"
            assert any(x.label == "スクリーニング必須検査の欠測/未実施理由*" for x in at.text_area), (
                "NA did not request omission reason")
            return "Glucose -1 rejected, 0 treated as actual, NA demands documented reason"
        probe("SCR-12-partial-glucose-NA", work)


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        (OUT / "app_test_results.json").write_text(
            json.dumps({
                "kind": "local AppTest against existing source",
                "scope": "simulation only; no deployed TEST GAS/Sheet writes",
                "formal_uat_pass_added": 0,
                "checks": checks,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
