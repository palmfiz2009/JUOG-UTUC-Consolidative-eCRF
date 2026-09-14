# v2.2.2 Test Report

Build: 2026-09-14

## Automated checks
- Python syntax compile: PASS (all Python files)
- pytest common logic: 16/16 PASS
- Streamlit page smoke: all 6 pages PASS（4施設CRF + 事務局 + MDT判定者ログインゲート）
- Apps Script JavaScript execution in mock Google Sheet: PASS (`BACKEND_V222_TEST_OK`)

## Backend integration scenarios checked
- Screening ID issuance and full ScreeningCRF persistence
- 3 independent MDT reviews -> eligible -> JUOG formal registration
- facility RECIST PR / central RECIST SD retained as `DISCORDANT` while registration remains possible
- central RECIST PD blocks formal registration
- SD count remains based on EVP best overall response
- 30d initial report, duplicate initial rejection, correction version 2
- ineligible screening retained but excluded from Registry
- HOLD -> resubmission increments review round and prior reviews are not reused

## v2.2.2 hard-stop checks
- height 300 cm: rejected
- weight 200 kg: accepted by range logic
- weight 300 kg: rejected
- Hb 5 g/dL: accepted by range logic (abnormal-but-possible lab values are not rejected solely for being extreme)
- DBP >= SBP: rejected
- obvious vital-sign digit errors: rejected
- EVP final dose after planned/actual surgery: rejected
- surgery before consent: rejected by registration/client and backend CRF chronology guards
- 90d evaluation date before surgery/reference date: rejected
- death date before formal registration date: rejected by Apps Script before Google Sheet persistence

## Still required
Real-environment UAT with the deployed Streamlit app, Streamlit Secrets, Apps Script Web App, Gmail notification, and the actual Google Sheet. Use test subjects only until UAT passes.
