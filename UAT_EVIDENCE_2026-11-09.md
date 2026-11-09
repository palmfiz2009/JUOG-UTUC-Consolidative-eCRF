# JUOG-UTUC01 — TEST-only UAT evidence and release gate (2026-11-09)

> This is an evidence log, **not a release approval**. No production branch or patient data was modified.

## Scope and current repository state

- Production `main` has diverged from TEST branch `validation-v2.2.8` (TEST ahead by 4 commits, behind by 2 at inspection).
- TEST-vs-main changes concern six files: `02_perioperative_30d_crf.py`, `05_admin_mdt_registration.py`, `05_registry_google_apps_script.gs`, `VERSION.txt`, `juog_common.py`, `streamlit_app.py`.
- In direct file-content comparison, `05_registry_google_apps_script.gs` differs only in release labels/comments, `05_admin_mdt_registration.py` in backend version label, and `VERSION.txt` in release status. `streamlit_app.py` differs in both UAT email guard and a `main`-only support form fix (`未発番`). Do not roll the latter back.
- The isolated review branch contains only the 30-day draft widget restoration change, offline unit-test code, this evidence file, and a read-only GitHub Actions test workflow.
- Actual file-by-file source comparison confirms that scoped role tokens, cN1-only accounting, and Apps Script integrity guards **already exist in main source** (v2.2.8 release candidate), although real production GAS deployment/configuration has **not** been verified. The TEST-only differences include disabled SMTP and an extra UAT startup guard. Do not merge TEST wholesale.

## Read-only TEST registry evidence

TEST spreadsheet: `TEST_JUOG_UTUC01_UAT_STAGING_20261108_DO_NOT_USE_FOR_PATIENTS`, sheet ID `1R1a55w19qfS7XTa6Ran7EnuTNZpFkGoXIFfqesv7zoc`.

- `Registry`: synthetic `JUOG-001`, facility `F11`, active, registered 2026-11-08; linked to `JUOG-SCR-001`.
- `Screening`: `cT3 cN1 cM0`, PR; planned surgery 2026-12-06.
- `CRF_30d`: `JUOG-001|perioperative_30d|30d`, v1 initial report and v2 correction retained, both saved 2026-11-08.
- `CRFSubmissionAudit`: matching v1/v2 `record_key`, `record_version`, `submission_id`, `registration_id`, `facility_code`. No deletions or overwrites were made during this review.
- `CRF_Drafts`: one 30-day draft updated 2026-11-09 15:19:09 JST. Selected facility and some 30-day lab fields are present in the snapshot.

## Chronology blocker — not an application success

- The 2026-11-09 draft includes planned/reference date **2026-12-06**, 30-day evaluation date **2027-01-05** and 30-day lab date **2027-01-05**.
- For a 30-day ±14 day window, the valid window from 2026-12-06 is **2026-12-22 through 2027-01-19**.
- The Streamlit form rejects a **future** 30-day evaluation date. Meanwhile Apps Script checks that the planned/actual surgery reference date is not earlier than formal registration.
- Thus the saved TEST snapshot cannot be submitted successfully through the *current normal UI* on 2026-11-09. A new TEST subject registered on or after 2026-11-08 also cannot legitimately have reached 30-day follow-up yet.
- Existing v1/v2 rows confirm Google Sheet append and audit entries but do **not** prove the newer Streamlit draft-restore behavior or its current UI-to-Apps-Script end-to-end pathway.
- Do not backdate consent/registration, fabricate a clinical elapsed interval without simulation labeling, or weaken production date checks to make a test pass.

## Review and test coverage

- Extracted change: sync `widget_peri_facility`, `widget_peri_day30_lab_*` and `widget_peri_discharge_lab_*` to restored backing values before rerender.
- Created isolated Python regression tests for restoration of facility and Hb/WBC, handling of stale widget state, and isolation from unrelated fields.
- Three tests passed against a local reconstruction on 2026-11-09; **GitHub Actions on the exact PR checkout also passed all three tests** (run 42586660771, commit 0c532c83e003fd503146d5bbd4b0a4c44e3cb2aa). These are isolated regression tests, not full Streamlit/GAS integration tests.
- A read-only GitHub Actions job is supplied on the review branch; it has no study credentials and performs no external registration or notification.

## Remaining release gates

1. [x] CI on exact checkout: three regression tests passed. [ ] Human code review/approval of the submitted changes.
2. Deployed TEST Streamlit: restore draft and verify facility, Hb, WBC, Na, discharge labs, date values before and after rerun.
3. Date-valid end-to-end TEST (after elapsed window or within an explicitly isolated simulated clock and TEST backend): initial and/or correction via normal form, with valid full synthetic dates.
4. Google Sheets after each approved submission: compare `submission_id`, `record_key`, `record_version` and audit append; verify prior versions unchanged and duplicate initial reports rejected.
5. Examine backend integrity separately: `savePayloadToSheet_` appends CRF first and audit second; this is not a database transaction. Verify recovery if audit append fails.
6. Validate TEST outbound SMTP remains disabled; confirm the production-deployed GAS build, its server-side role secrets and cN1-only behavior against the already-present main source **separately** before any release.
7. Explicit review approval before merging. Do not merge `validation-v2.2.8` wholesale.

**Result: isolated regression CI passed; real browser-driven TEST UAT, full release review and production deployment NOT completed.**
