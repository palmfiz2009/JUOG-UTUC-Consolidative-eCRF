# JUOG-UTUC01 — 90-day and 6–24 month UAT evidence

**Date:** 2026-11-09 (JST). **Status:** engineering validation completed; real TEST deployed-Stack UAT and release approval PENDING.

## Reason for change

- 90-day and 6–24 month draft restoration previously repopulated backing state, but not the separate `widget_d90_lab_*` or `widget_fu_lab_*` keys used by the rendered text inputs. Pre-existing widget state could overwrite the restored result.
- Follow-up `save_draft/get_draft/delete_draft` previously used a single `followup` draft key regardless of visit period. A 9m draft could overwrite a 6m draft for the same subject.
- GAS `validateDay90SourceLink_` previously checked 30-day provenance only for `day90`, not `followup`. The UI checked follow-up 30-day provenance, but a direct API save could bypass it.
- GAS `validateCrfHardStops_` lacked the frontend's no-future clinical evaluation date rule.

## Changes (review branch only)

- Restore separate widget-state keys for 90d labs/facility and follow-up labs before rerun.
- Use period-specific follow-up draft keys: `6m`, `9m`, `12m`, `15m`, `18m`, `21m`, `24m`. A 6m draft never shares the same key as a 9m draft.
- Require visit-period selection to save/resume follow-up drafts. For legacy draft key `followup`, allow read only when its recorded `fu_visit_month` exactly matches the selected report month; do not automatically treat a different month as interchangeable.
- After follow-up formal save, delete its visit-specific draft and, only when the matching legacy visit was restored, delete the matching legacy draft.
- Check source 30-day CRF version, submission ID, surgery status, reference date and facility server-side for linked day90 and follow-up. Follow-up requires linkage; preserve day90 explicit manual fallback.
- Reject future CRF visit, clinical lab, death and last-alive dates at GAS write boundary in Asia/Tokyo, matching the frontend.

## Verified automation (no external GAS/Sheets writes)

- **6/6 Python offline regression tests**: 90d lab/facility draft restore, stale widget cleanup, follow-up lab restore, visit-specific draft mapping and save/load/delete routing.
- **15/15 JavaScript backend contract tests**: source linkage, version and submission ID, surgery date/status, facility, visit month key, allowed day90 fallback, missing source and future-date hard stops.
- **Playwright, genuine Streamlit page + local 127.0.0.1 mock registry:** both 90-day and 6m follow-up forms completed full UI workflow (input → draft save → new browser session → draft restore → formal submit), with synthetic mock CRF version 1 and matching mock audit entry for each. Synthetic ID `JUOG-999`; source reference date 2026-03-01, 90d visit 2026-05-30, 6m visit 2026-09-01; never use production identity or credentials.
- Browser execution before GAS date-hardstop patch: GitHub Actions run **42594507108** SUCCESS; offline and browser run after both source and future-date patches: **42595379517** (verify completion before approval).

## Real TEST spreadsheet snapshot (read only)

Sheet: `TEST_JUOG_UTUC01_UAT_STAGING_20261108_DO_NOT_USE_FOR_PATIENTS`.

- 90-day records v1/v2 and 6m follow-up v1 have matching `CRFSubmissionAudit` rows. All five synthetic CRF rows across 30d/90d/follow-up reconcile to five audit rows.
- **Important:** The existing real TEST 90-day and 6m payloads have only minimal UAT fields and **future visit dates** (2027-03-08 and 2027-06-06). They are synthetic ledger test fixtures, **not** evidence that the present Streamlit form accepted/validated those dates.
- In particular, legacy TEST 6m payload lacks `source_30d_linked`, `source_30d_record_version` and clinical fields. The new backend validation will reject such an incomplete payload if submitted anew, intentionally; it does not alter any historical rows.
- No Google Sheet rows were added, overwritten or deleted during this source-code UAT.

## Release gates

1. [x] Static code review, isolated synthetic Python/JS tests.
2. [x] Actual Streamlit local-browser UI with mock registry for 90d and 6m.
3. [ ] Deployed TEST Streamlit + real TEST GAS/Google Sheet save and audit check (normal user flow, no historical backdating).
4. [ ] Test 9m, 12m, 15m, 18m, 21m and 24m UI flows, legacy draft fallback, and both surgery-performed / surgery-not-performed branches.
5. [ ] Confirm GAS deployed version, role secrets, TEST SMTP isolation and error recovery if a CRF row appends but the separate audit append fails.
6. [ ] Clinical PI and study-office approval prior to production merge/deployment.

**Both PR #4 and PR #5 remain Draft. Do not merge TEST wholesale or alter production main.**
