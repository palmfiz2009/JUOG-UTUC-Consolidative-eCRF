# JUOG-UTUC01 EDC — CRF/Audit Data Integrity CSV 実機試験手順（ドラフト）

Document ID: CSV-OQ-CRF-AUDIT-001  
Revision: 0.1 / 2026-11-15 JST  
Status: **DRAFT / NOT EXECUTED / NOT APPROVED**  
Related: PR #19, GCP-02/GCP-03/GCP-05, UAT POST-01/POST-02/POST-03/FUP-01/FUP-02, DATA-04  
Candidate: `quality/audit-recovery-no-false-success-20261115` (pin immutable head SHA at execution)  
Reference standard: ICH E6(R3) data governance/computerised systems (apply risk-based scope after QA review).

## Purpose / acceptance criteria
Confirm that an authorised CRF save (30-day, 90-day, follow-up) is acknowledged only when the matching CRF row and exactly one corresponding audit entry exist, are independently readable, and their submission_id, record_key, record_version, registration_id and facility_code agree. A same-UUID replay after uncertainty must not add a new version. Cross-sheet write is **not transactional**; failure should yield an explicit pending/unconfirmed state, not false success.

## Pre-execution gates (all must be formally authorised)
- Dedicated **isolated** Streamlit + GAS deployment + 12-tab isolated Sheets using **only fully fictional** fixtures; real patient records, production, existing TEST, Stage1 and fixed S2-01 unchanged.
- Freeze and record application Git SHA, backend source checksum, GAS deployment/version ID, isolated Spreadsheet ID, source sheet/audit sheet schema, timestamp/zone and account/ACL role IDs **without secrets**.
- Verified backup and isolation, notifications/SMTP/Dropbox external upload disabled and tested non-reachable; emergency rollback prepared; operator/tester and independent reviewer assigned.
- Formal QA approval of protocol steps, controlled failure-injection method, and criteria for acceptable partial writes.
- Prior unknown TEST v2.2.10 Version 2 submission UUID **must be reconciled separately**. Never use or replay it in this test.

## Executable scenarios (planned — no actual PASS claimed)

| Case | Action (fictional only) | Expected result | Evidence to preserve |
|---|---|---|---|
| OQ-01 | Submit valid 30-day first report once | CRF v1 and Audit v1 each 1 row; identical UUID/key/subject/site; success only after readback | Screen, bounded row read, audit row, timestamp, SHA |
| OQ-02 | Resend exact UUID + exact immutable payload | existing=true, v1 unchanged, no new CRF/audit rows, no duplicate email | pre/post bounded counts + response |
| OQ-03 | Simulate audit append failure after CRF write | Return error/unconfirmed; CRF may be v1, audit absent; no success banner | fault log without PHI, source metadata |
| OQ-04 | Retry OQ-03 with exact original UUID/body | Repair or verify matching audit v1; keep single CRF v1, no v2 | same UUID fingerprint, before/after row hashes |
| OQ-05 | Inject conflicting audit UUID/version/key | Reject; no overwrite and no new CRF version | conflict code, before/after unchanged hashes |
| OQ-06 | Inject duplicate audit UUID | Reject, no silent selection; retain evidence for reconciliation | duplicate count, error |
| OQ-07 | Inject CRF readback failure/content mismatch | No success; no false assumption of audit completeness | response, after-state |
| OQ-08 | Retry UUID with changed payload or record key | Reject SUBMISSION_ID_CONFLICT; no new version | before/after rows |
| OQ-09 | Submit corrected report with **new** UUID/reason after verified v1 | Exactly v2, both CRF and Audit v2; v1 unchanged | both versions, correspondence, reason |
| OQ-10 | Attempt duplicate first report with **new** UUID | INITIAL_ALREADY_EXISTS; no new rows | response and row count |
| OQ-11 | Modify linked 30-day CRF before 90-day save under concurrent lock contention | New 90-day save rejected as stale source, no premature success | linked version refs + response |
| OQ-12 | After confirmed 90-day save, replay same original UUID following source correction | Existing reply/reconciliation only; no modified historical payload | immutable snapshot and audit |
| OQ-13 | Repeat OQ-01/02/09 for follow-up visit and linked source | Matching versioning, subject ACL, audit and linkage | 6–24mo representative branch and readback |
| OQ-14 | Expire/deny facility role and attempt save | No CRF/audit write, access rejected | role-negative response, unchanged rows |
| OQ-15 | Simulate browser/session loss after ambiguous save | **Expected pending gap**: system must not generate a new UUID silently; evaluate and implement durable reconciliation before release | defect/change request, sign-off status |

## Required test record per scenario
- Test ID, approved precondition, expected result, precise run time (JST), version/commit/deployment/sheet IDs, actor's authorised role (no secrets), input fixture reference, failure injection configuration, HTTP/GUI result, both bounded sheet rows, audit comparison, independent reviewer/date, exception/discrepancy and CAPA.
- Never put real patient names, MRNs, full DOB, passwords, access/role tokens, signed requests or raw PHI into GitHub evidence.
- Pass only if all criteria objectively proven; otherwise FAIL/BLOCKED with explicit disposition. No technical reviewer may self-grant formal QA acceptance.

## Present evidence
- Offline real-source JS/GAS syntax and failure-injection 18 checks: PASS, GitHub Actions 43727297018 (commit c0daf04624da5536bb9299cec69dc6918eecfd4d).
- Offline frontend frozen UUID/immutable payload 8 checks: PASS in the same workflow.
- Real isolated GAS+Sheets scenarios OQ-01 through OQ-15: **NOT EXECUTED under this document**.
- Official 67-item UAT remains PASS32/FAIL1/BLOCKED29/NOT RUN5; no status changes.

## Exit criteria
QA-approved traceability (URS/FS→risk→script→evidence); no unresolved critical discrepancy; independent review of deployed application + server code; validated durable retry design; verified audit consistency and recovery; backup restore/ACL/SOP evidence; separately authorised release.
