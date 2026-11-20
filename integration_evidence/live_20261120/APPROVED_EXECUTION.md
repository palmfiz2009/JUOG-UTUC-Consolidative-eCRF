# Approved isolated preparation — 2026-11-20 JST

The user's subsequent `承認` authorized the named environment preparation in APPROVAL_SCOPE.md. It did not supply independent QA approval, clinical protocol approval evidence, a renewed ACL expiry, or a mail recipient. This record supersedes the earlier preflight's environment state; historical observations remain unchanged.

## Executed and verified

1. Copied the existing isolated Sheet to [the private backup](https://docs.google.com/spreadsheets/d/1G9Qo_MfVf-uDXZzZwu4IgRuzVGQih9By_7glH8DILS4/edit). All 13 tab names, dimensions and bounded FORMULA-rendered values matched. Source modification time remained `2026-11-09T13:28:04.604Z` before provisioning. This is a copy-integrity check, not a full restoration rehearsal.
2. Copied both visible old GAS source files and the candidate's visible source through the editor. Stored [source ZIP backup](https://drive.google.com/file/d/1uqk4vfvxPIp3Y-6iVhDTWZfarXea0snk/view?usp=drivesdk) in the existing private Drive root. Hashes are in approved_actions.json. No secret values were published. The ZIP's deployment text was a short AX diff; the complete non-secret pre-archive deployment observation is preserved separately as old-deployment-before.txt here. Manifest and secret properties were not exported; retained projects/version remain the rollback authority.
3. Verified the old fixture GAS's Spreadsheet ID property matches the named fixture Sheet. Both old and candidate projects show zero triggers for the current account. Archived ONLY deployment `AKfycbxq4ElxrKAQGdp_MG4oI5VuvGGRWcIdbpuQym3w67R2bvLVl0c4b8qlVXERCql3js8gbw` (old fixture Version 1). Reopened deployment management and observed zero active deployments and Version 1 retained under archived deployments. No HTTP write probe was issued. Other accounts' triggers/other projects' writers are not certified absent.
4. Added six header-only tabs to the existing fixture Sheet: V3_Users, V3_SessionEvents, R1_CaseOwners, R1_Operations, R1_DraftOwners, R1_DraftEvents. Headers exactly match integration_schema.json; each contains one row. Re-read all original 13 tabs: values/formulas unchanged. Inspected the six added tabs in the native UI; header text readable, row 1 frozen. No ACL entries, owner assignments, clinical records or journal genesis were seeded.
5. Awakened the existing fixture Streamlit. It displays JUOG AUTH_CONNECT, business saving prohibited, and inability to verify identity/expiry/settings. Its Source button points to `uat-fixture-isolated-20261109/streamlit_app.py`; this does not establish a served commit SHA. It is not the PR15 integrated CRF runtime.

## Evidence and result

- Machine-readable checks: approved_actions.json.
- Native screenshots: old-archived-status.jpg, fixture-auth-expired.jpg and one image for each new tab.
- Formal 74-item UAT: **PASS 0 / FAIL 0 / BLOCKED 74 / NOT RUN 0; new PASS 0**. Preparation checks are not CRF UAT passes. The earlier 67-item ledger is untouched.
- No runtime code changed in this execution; prior offline test results were not rerun or re-labelled as live results. Evidence checks verified 13 backup matches, 13 original-tab preservation checks, 6 exact header rows and 74 unchanged result classifications.
- Candidate GAS code/deployment, Streamlit source/configuration, security credentials, ACL duration and notification settings were not changed. No new app, paid service, patient data, production, old TEST, Stage 1, S2-01 or main change.

## Remaining gates

- Approved clinical protocol original/version and conformity review are still missing. Additional targeted Dropbox title searches found no protocol named JUOG or Consolidative; no patient-image folders or unrelated databases were opened. The 254 UI-derived conditions cannot be declared clinically approved.
- Actual independent reviewer/approval reference is missing. The approved scope explicitly conditions candidate deployment on clinical/independent-review prerequisites; no qaRef is fabricated.
- Fresh expiry and verified principal are needed for the TEST01 ACL. The previous expiry (2026-11-19 23:59 JST) is past. Waking the app did not grant or extend access.
- The integrated signed endpoint and Streamlit switch remain pending the above gates, followed by verification that no other writer reaches this Sheet. The six tabs alone are not a complete B2/auth initialization.
- Automatic draft saving and persisted section progress remain implementation gaps; the current CRF UI has a manual draft button. They are not counted as delivered.
- External mail remains disabled. Success/failure mail UAT requires a specifically designated test mailbox and scoped sending authorization.

## Recovery boundary

The old deployment's Version 1 and source/settings remain intact. An authorized rollback can reactivate the retained deployment through deployment management, only after excluding the candidate writer. Do not reactivate it in parallel with a new writer. The private Sheet copy preserves the original 13 tabs; restore only after reconciling any subsequent journal/CRF activity. Do not delete or overwrite audit/version history. The six new tabs are empty except headers; no destructive rollback was attempted. A complete manifest/secret-property export and end-to-end restore rehearsal are not claimed.
