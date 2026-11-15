"""Offline tests only: wholly fictional inputs; no patient records or email sending."""
import unittest

from screening_crf_receipt import receipt_sections, render_receipt_html, render_receipt_text


class ScreeningReceiptTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "screening_id": "JUOG-SCR-901", "facility_name": "架空病院",
            "local_subject_code": "001", "reporter_email": "fictional@example.invalid",
            "submission_id": "fictional-submission", "submitted_at": "2026-11-15T12:00:00+09:00",
            "data": {
                "consent_date": "2026-11-11", "age_at_consent": 72,
                "birth_year_month": "1954-10", "sex": "女",
                "past_history": "架空の既往歴\n追記された事項",
                "concomitant_meds": "薬剤A\n薬剤B",
                "screening_vitals": {"sbp": 120, "dbp": 70, "pulse": 60, "temperature": 36.6},
                "screening_labs": {"WBC": 6000, "Hb": 12.3, "CRP": 0.1, "future_lab": 7},
                "primary_site": ["腎盂", "尿管"], "ct": "cT2", "cn": "cN0", "cm": "cM0",
                "evp_courses": 4, "best_effect": "PR",
                "target_lesions": [{"organ": "架空臓器", "diameter_mm": 12}],
                "target_recist_support": {"response": "PR", "change_pct": -40.0},
                "planned_surgery": "架空の術式", "other_unsuitable": "なし",
                "unmapped_future_field": "<script>unsafe</script>",
                "zero_value_example": 0,
            },
        }

    def test_receipt_contains_identifiers_round_and_full_clinical_sections(self):
        text = render_receipt_text(self.payload, review_round=2)
        for item in ("JUOG-SCR-901", "審査ラウンド: 2", "001", "架空病院",
                     "同意・患者背景", "診断・病期", "検体検査",
                     "術前再評価・RECIST", "手術計画",
                     "120 mmHg", "12.3 g/dL", "4 コース",
                     "薬剤A", "薬剤B", "fictional-submission"):
            with self.subTest(item=item):
                self.assertIn(item, text)
        self.assertNotIn("MACHINE_READABLE_JSON", text)
        self.assertNotIn('"schema_version":', text)

    def test_html_escapes_submitted_user_content_and_prints(self):
        html = render_receipt_html(self.payload, review_round=2)
        self.assertIn("<!doctype html>", html)
        self.assertIn("@page{size:A4", html)
        self.assertIn("申請者控え", html)
        self.assertIn("&lt;script&gt;unsafe&lt;/script&gt;", html)
        self.assertNotIn("<script>unsafe</script>", html)
        self.assertIn("架空の既往歴<br>追記された事項", html)
        self.assertIn("001", html)

    def test_forward_compatible_without_losing_new_fields(self):
        sections = receipt_sections(self.payload, 2)
        strings = "\n".join(str(row) for _, rows in sections for row in rows)
        self.assertIn("future_lab", strings)
        self.assertIn("unmapped_future_field", strings)
        self.assertIn("zero_value_example', '0", strings)
        self.assertIn("臓器", strings)
        self.assertIn("12", strings)

    def test_missing_values_are_distinct_from_zero_and_false(self):
        self.payload["data"]["screening_labs"]["Hb"] = 0
        self.payload["data"]["pregnancy"] = False
        plain = render_receipt_text(self.payload, 1)
        self.assertIn("ヘモグロビン（Hb）: 0 g/dL", plain)
        self.assertIn("妊娠: なし", plain)
        self.assertIn("授乳: —", plain)

    def test_empty_payload_has_safe_placeholder(self):
        html = render_receipt_html({"data": {}}, None)
        self.assertIn("MDT審査受付番号", html)
        self.assertIn("登録なし", html)


if __name__ == "__main__":
    unittest.main()
