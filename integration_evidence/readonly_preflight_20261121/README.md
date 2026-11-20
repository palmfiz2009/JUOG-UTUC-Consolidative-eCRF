# Independent read-only isolated fixture preflight — 2026-11-21 JST

## Purpose and scope
Verify a real, existing TEST01 isolated Google Sheet using the connected Google Sheets **read-only** APIs, without opening patient/fictional clinical rows or identity subjects. The scope is **metadata and schema headers only**, not EDC runtime or QA. No tests were submitted. Local branch at initial read: `2d545c1b5d22045c54d87401691fd869fbb1de90`; production main: `c5580662be09f914cad372aa4e4df0ed62cdf2e8`. PR #15 is Draft at `73a4556b24291cb36e8800c4a99b372b5c30b759` and remains a different head.

## Actual Google Sheets API observations (2026-11-21 JST)
- Spreadsheet ID already configured in `isolated_crf_profile.json`: `1XaLdVGN39skmXVhiyPN-uOb9B8zjo3rmbNgYZCndJRs`; title `TEST_JUOG_UTUC01_FIXTURE_CSV_20261109_ISOLATED_NO_PATIENTS`. Drive API could read its metadata successfully.
- Sheet metadata returns **19 tabs**, including all six integration-specific V3/R1 tabs previously missing in the *older* preflight snapshot. They were already added under the prior approved preparation documented in `integration_evidence/live_20261120/APPROVED_EXECUTION.md`; **not added now**.
- The six row-1 header arrays are read from the actual Sheet and exactly match the arrays in `integration_schema.json`: `V3_Users` (7), `V3_SessionEvents` (3), `R1_CaseOwners` (4), `R1_Operations` (3), `R1_DraftOwners` (2), `R1_DraftEvents` (2). Also read only headers of `CRF_30d` and `CRFSubmissionAudit` (match the declared integration columns). No non-header identity, clinical or other values were fetched.
- Scoped read of `V3_Users!G2:G10` (ACL valid_until) and `R1_CaseOwners!D2:D10` (owner enabled flag) returned no values. This does **not** prove global emptiness or determine the actual person's issuer/subject. It does establish that the checked ranges do not document a currently usable TEST01 ACL or owner assignment.
- Existing `isolated_crf_profile.json` (read at HEAD) remains `enabled:false`, `url:""`, `generation:""`, `principal_fingerprint:""`, `qa_ref:""`, `pi_ref:""`, `single_writer_ref:""`, `backup_ref:""`, `b2_policy_ref:""`.
- Old deployment archive, backup and host wake are **prior evidence from 2026-11-20**, *not re-proven against the currently running hosted service*. The previous archived old-writer state is not sufficient to exclude other projects/users/triggers. The candidate GAS and Streamlit served SHA are not independently accessible as a running integrated endpoint from this profile.
- The last 15 GitHub Actions runs accessible for this repository were on unrelated branches, latest created 2026-11-16; there were zero matching runs for HEAD `2d545c1b5d22045c54d87401691fd869fbb1de90`. Thus there is no hosted regression proof for this commit.
- No independent reviewer decision, approved clinical conformity, authenticated signed runtime, complete writer isolation or mail-scoped permission is evidenced by these metadata reads. The approved 2026-09-16 protocol original is already located; do not request it again.

## Decision
**Live 30d-V1 UAT remains BLOCKED; no user action can be truthfully certified as a formal PASS from these observations.** Baseline stays PASS 0 / FAIL 0 / BLOCKED 74 / NOT RUN 0. This is not a failing test; it is a missing authorized integrated runtime and QA decision.

## Smallest remaining human-controlled gate
1. Verify the **actual OIDC issuer+subject** using an authorized account, and approve a new explicit TEST01 ACL expiration and fictional case-owner allocation. Past ACL expiry was 2026-11-19 23:59 JST; do not extend unilaterally.
2. Appoint independent QA and authorize clinical-condition conformity review against the **already located** protocol, including eight outstanding interpretive topics; do not fabricate QA approval or re-request the protocol.
3. Individually authorize the **existing isolated** candidate GAS review/approved code deployment, signed B2 configuration and the existing Streamlit fixture switch, with a consistent backup and exclusive-writer proof. This changes neither production nor existing TEST/main. Notification remains disabled; no external mailbox is necessary to get the *first* 30d-V1 save.
4. Once these exist, actually execute authorized OIDC login → 30d form entry → section autosave/resume → first official v1 submission → Sheets record/UUID/Version/record_key/CRFSubmissionAudit verification, then independent QA classification. No fake clinical subject or auth identity.

## Non-effects
No GAS or Streamlit deployments, settings, ACL, secrets, sheet writes, patient data, production, existing TEST, Stage 1, S2-01, GitHub main, PR head, mail, paid browser workflow or hosted Actions were executed in this run. This document only records actual metadata/header reads; no evidence of successful real-browser UAT is claimed.
