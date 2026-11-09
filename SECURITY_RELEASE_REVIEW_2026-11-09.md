# JUOG-UTUC01 — EDC security and release-readiness review
**Date:** 2026-11-09 JST  
**Classification:** Internal engineering UAT / risk register; NOT a clinical, legal or GCP certification.  
**Source:** read-only review of `main` and Draft PRs #4–#8.  
**Safety:** No real/patient data, no production deployment or merge, no mutating Google Sheets calls.

## Summary
The CRF UI and test-only backend passed substantial synthetic regression tests, but the following are **release blockers** until separately verified. Real TEST Google Apps Script / Google Sheets E2E was **not** performed as part of these PR checks.

| Priority | Finding from code | Impact / necessary decision | Status |
|---|---|---|---|
| P0 | `authorizeJuogAction_` treats unlisted facility actions (including `save_crf`, `get_crf_linkage`, `get_draft`, `delete_draft`, `submit_screening`, `delete_screening_draft`) as `{ok:true,kind:'facility'}` after checking only shared API token at `doPost` | Server must bind an **authenticated user and site scope** to each facility operation; never trust the facility code claimed in the submitted payload as proof of authorization | **OPEN — architecture decision required; not quietly patched** |
| P0 | `getCrfLinkage_` validates the registration ID with `facility_code:''` and returns 30-day surgery status/reference date for a known study ID | Cross-facility access policy must be enforced server-side. A correct registration ID is not user authorization | OPEN |
| P1 | E-mail is entered by the user and checked as a string for draft ownership; it is not a verified login identity | Site login, authenticated session/role, verification and revocation require a documented workflow | Narrow delete check patched in Draft PR #7; full authentication OPEN |
| P1 | CRF append and audit append are separate Google Sheets operations | A failed second append can leave missing audit. Same-ID replay recovery is proposed; also require an independent reconciliation / repair procedure for changed-ID and partial-failure cases | Draft PR #6, NOT deployed |
| P1 | `saveCrf_` previously checked latest source version before acquiring the script lock | Between source check and save, a 30-day correction could change the reference version | Draft PR #8, 6/6 offline tests PASS |
| P1 | Follow-up drafts previously used a shared `followup` key across 6–24m; linked follow-up source validation was not enforced on the GAS side | Preserve each visit separately and validate 30-day provenance | Draft PR #5, mock browser/contract CI PASS |
| P1 | `deleteDraft_` and `deleteScreeningDraft_` previously deleted keyed drafts without confirming owner | Add saved reporter e-mail check before destructive action | Draft PR #7, 12/12 Node + 5/5 Python checks PASS; NOT deployed |
| P1 | TEST and production deployment/config may differ from the repository source | Verify exact deployed GAS version, Streamlit secrets, SMTP isolation, site roles and all non-patient fixture IDs | OPEN |
| P1 | Source protocol requires central radiologist direct image review and cN1-only Stage IV count logic | Validate UI, MDT reviewer state, RECIST decisions, cT≤3/cN1/cM0 cap, and operation 4–8 weeks after last EVP dose through full decision table | Partially checked; full clinical UAT OPEN |
| P2 | iOS/Android form use, interrupted networks, double-tap and browser back/forward not fully tested | Run mobile and failure-injection matrix on a fully isolated TEST instance | OPEN |
| P2 | Spreadsheet owner/editor, backup/retention and direct manual sheet edits are external to Apps Script lock | Define immutable export/version snapshots, restricted editor access, scheduled backup, reproducible restore and independent monitoring | OPEN |

## Exact test evidence (only synthetic/offline where stated)
- PR #4: Streamlit Chromium flow: 30-day draft save → new session → restore → formal submit → **mock** version/audit match; plus 13 offline checks. GitHub Actions run `42591351052`.
- PR #5: 90-day and 6m forms follow same browser flow using local synthetic registry; 6 Python + 15 Node checks. GitHub Actions run `42595379517`.
- PR #6: 14 in-memory backend checks including forced audit append error and same-ID retry. Run `42596932907`.
- PR #7: 12 in-memory draft-owner cases including pre-MDT drafts + 5 wrapper/call-site tests. Run `42598596113`.
- PR #8: 6 offline lock/ordering/failure tests. Run `42598226113`.
- All above are code checks or browser tests against loopback mocks, **not evidence of deployed TEST GAS/Sheet success**.

## Read-only TEST Sheets reconciliation
- Spreadsheet `TEST_JUOG_UTUC01_UAT_STAGING_20261108_DO_NOT_USE_FOR_PATIENTS`.
- As checked 2026-11-09: Registry **1**, draft **1**, CRF_30d **2**, CRF_90d **2**, CRF_Followup **1**, CRFSubmissionAudit **5**.
- Historical versions 1/2 for 30-day and 90-day are preserved; follow-up 6m has version 1. All five CRF records matched existing audit rows in earlier cross-field checks.
- Historical synthetic 90-day/6m dates fall in 2027 and are **not** valid proof of present-day UI date acceptance. No existing TEST rows were modified.

## Safe integration and release-gate procedure
1. **Do not merge PRs #4–#8 one by one blindly.** They are independently branched from main and can conflict (GS file shared by #5/#6/#7/#8; follow-up delete signature changed by #7 vs visit-specific call sites in #5).
2. First, decide and document facility/user authentication (including administrative override and reporter handover). This is a **P0 blocker**, not something to guess or bypass in code.
3. Create a disposable **integration review branch** from a pinned main SHA and apply reviewed changes with conflict resolution. Never modify production main merely to run tests.
4. Run all Python/Node/Playwright CI and add failure-injection tests for audit repair, changed-ID retries, source-update race, report-month isolation and wrong-facility data access. Run on fake records only.
5. Deploy reviewed integration candidate to a separate TEST app and dedicated TEST GAS/Sheet with controlled secrets. Explicitly verify TEST SMTP/notification suppression and test fixture chronology.
6. Execute authorized real TEST UI→GAS→Sheet UAT, including initial/correction report versions, audit equality, double submission, interrupted connection, pre-MDT/3-role reviewer and cN1-only quota boundary.
7. Obtain independent investigator/study office sign-off on protocol mapping, data dictionary, UAT evidence, role matrix and backup/restore; then decide whether production deployment is appropriate.

## Residual limitation
A field called `reporter_email`, an unguessable JUOG ID, or a global registry API token **must not be treated as site-level authorization**. No real account, secret, authorization or patient data was used in this review. A stronger site identity design may change screen UX and must be approved before implementation.

**Current release decision: HOLD.** Preserve production main and all real TEST records.