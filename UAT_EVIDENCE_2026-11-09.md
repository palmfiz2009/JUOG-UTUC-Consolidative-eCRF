# JUOG-UTUC01 — TEST-only UAT evidence and release gate (2026-11-09)

> This is an evidence log, **not a release approval**. No production branch or patient data was modified.

## Scope and current repository state

- Production `main` has diverged from TEST branch `validation-v2.2.8` (TEST ahead by 4 commits, behind by 2 at inspection).
- TEST-vs-main changes concern six files: `02_perioperative_30d_crf.py`, `05_admin_mdt_registration.py`, `05_registry_google_apps_script.gs`, `VERSION.txt`, `juog_common.py`, `streamlit_app.py`.
- In direct file-content comparison, `05_registry_google_apps_script.gs` differs only in release labels/comments, `05_admin_mdt_registration.py` in backend version label, and `VERSION.txt` in release status. `streamlit_app.py` differs in both UAT email guard and a `main`-only support form fix (`未発番`). Do not roll the latter back.
- The isolated review branch contains only the 30-day draft widget restoration change, offline Python/Node unit tests, a Playwright browser-test harness with a loopback-only fake registry, this evidence file, and a read-only GitHub Actions test workflow. No production/test backend credentials are needed.
- Actual file-by-file source comparison confirms that scoped role tokens, cN1-only accounting, and Apps Script integrity guards **already exist in main source** (v2.2.8 release candidate), although real production GAS deployment/configuration has **not** been verified. The TEST-only differences include disabled SMTP and an extra UAT startup guard. Do not merge TEST wholesale.

## Read-only TEST registry evidence

TEST spreadsheet: `TEST_JUOG_UTUC01_UAT_STAGING_20261108_DO_NOT_USE_FOR_PATIENTS`, sheet ID `1R1a55w19qfS7XTa6Ran7EnuTNZpFkGoXIFfqesv7zoc`.

- `Registry`: synthetic `JUOG-001`, facility `F11`, active, registered 2026-11-08; linked to `JUOG-SCR-001`.
- `Screening`: `cT3 cN1 cM0`, PR; planned surgery 2026-12-06.
- `CRF_30d`: `JUOG-001|perioperative_30d|30d`, v1 initial report and v2 correction retained, both saved 2026-11-08.
- `CRFSubmissionAudit`: matching v1/v2 `record_key`, `record_version`, `submission_id`, `registration_id`, `facility_code`. Additional read-only reconciliation on 2026-11-09 found 5 CRF records total (30d 2, 90d 2, followup 1), all 5 with corresponding audit rows, continuous per-key versions, no orphan audit entries and no payload key mismatches. No deletions or overwrites were made during this review.
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
- The PR also contains ten in-memory Apps Script contract tests: initial submission, retry, append-only correction, malformed input, conflicting submission ID, cN1 eligibility and count, recursive identifier guard, role authorization, and MDT judgment privacy. All ten passed alongside three Python tests on GitHub Actions run **42587647962** (commit **823957c2c8e4154c7773ed3273de4fbe5b99686c**). These use a backend-mock Google Sheet, not a deployed-Web-App integration test.



## Playwright UI validation (local isolated synthetic registry)

- **PASS — GitHub Actions run 42591351052**, exact branch commit `07e7adbb047f83261d9769795b8ec6a113c1e145` (browser and offline regression jobs both succeeded).
- Executed the **real Streamlit 30d form** in headless Chromium and used a local 127.0.0.1-only HTTP mock for registry requests. The browser never sent a request to real TEST or production Google Apps Script.
- Synthetic fixture: `JUOG-999`, facility F11, fictitious registration 2026-08-01, EVP last dose 2026-08-10, planned surgery 2026-08-25 (not performed), 30d visit / blood test / last alive confirmation on 2026-09-24. All dates are in the past at test time and internally consistent.
- Confirmed from the browser: form filled → save draft → open a new Streamlit browser session → reload draft by fake email/ID → restored facility, Hb, WBC, Na and 30d visit date → press formal submit.
- Confirmed mock registry received the final CRF and appended synthetic version 1 plus one audit record with matching `record_key`, `record_version` and `submission_id`; draft was deleted after save. 30d lab Hb and Na were found in final payload.
- No real TEST Google Sheets row was written. This is **UI + transport contract integration against a mock**, not a certified live-GAS/Google-Sheets E2E test. It does not resolve the real TEST registration-date chronology limitation or validate deployment configuration.
- CI test program: `tests/test_streamlit_30d_browser.py` + `tests/mock_registry.py`; synthetic dummy-only registry URL is generated inside Actions, never committed as a real secret.
## Remaining release gates

1. [x] CI on exact checkout: three regression tests passed. [ ] Human code review/approval of the submitted changes.
2. [x] Local Streamlit browser UI with mock backend: facility, Hb/WBC/Na, date restoration, formal submission and mock audit all pass. [ ] Independently verify discharge labs in a surgery-performed UI path and the deployed TEST Streamlit with real TEST GAS.
3. Date-valid end-to-end TEST (after elapsed window or within an explicitly isolated simulated clock and TEST backend): initial and/or correction via normal form, with valid full synthetic dates.
4. Google Sheets after each approved submission: compare `submission_id`, `record_key`, `record_version` and audit append; verify prior versions unchanged and duplicate initial reports rejected.
5. Examine backend integrity separately: `savePayloadToSheet_` appends CRF first and audit second; this is not a database transaction. Verify recovery if audit append fails.
   Check whether server-side future visit-date validation should mirror the form, as `validateCrfHardStops_` currently guards before-reference dates but does not itself reject future evaluation dates.
6. Validate TEST outbound SMTP remains disabled; confirm the production-deployed GAS build, its server-side role secrets and cN1-only behavior against the already-present main source **separately** before any release.
7. Explicit review approval before merging. Do not merge `validation-v2.2.8` wholesale.

**Result: 13/13 offline checks plus successful full browser workflow against loopback mock. Actual deployed TEST GAS/Google Sheets end-to-end UAT, release review and production deployment NOT completed.**
