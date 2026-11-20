# Identity-switch privacy hardening — 2026-11-21 JST

Scope: existing PR #15 isolated integration review branch only. Baseline commit `b3da31adfcf6677a7f63b38bbc942bba27f73163`.

## Observation (static review)
`resume_panel` cleared the form and `_autosave_*` state on a change/loss of authenticated identity, but did not clear the existing resume input widget keys (`_resume_case_*`, `_resume_visit_*`, `_resume_action_*`, section retry keys) or the separate recovery subject widget. Reusing the browser session under a different principal could therefore leave the previous principal's fictional-test registration identifier visible in the UI. This is a static code-level risk; it has **not** been confirmed in live browser UAT.

## Branch-only changes
- `a1bd1ef3edf0a8162501657b2d7752565d5eceeb`: on identity mismatch in `isolated_autosave_ui.py`, clear prior principal's resume and recovery widget state before stopping execution. Keep the normal within-identity case-switch behavior unchanged.
- `e2dbfc807f8f367ddf24827352a0a7a361ae1ea1`: add `IdentitySwitchPrivacy.test_resume_case_cleared_only_when_principal_changes` to `integration_tests/test_autosave.py`, with entirely fictional case identifiers.

## Verification boundaries
- This execution **did not run** the added test, the complete Python 183-test suite, GAS 40-group suite, or hosted GitHub Actions. Execution environments were not available through the GitHub read/write connector; do **not** increment historical PASS counts.
- Independent isolated Sheets re-read, A1:L100 of 12 Registry/CRF/auth/section tabs: **0 non-header data rows** in each tab. This is a bounded read, not proof the entire sheets have no data.
- Formal 74-item UAT remains **PASS 0 / FAIL 0 / BLOCKED 74 / NOT RUN 0**; no independent QA approval or live save audit evidence.
- Main, existing TEST, Stage 1, fixed S2-01, GAS, Sheets, Streamlit deployment, credentials, ACL, mail settings and real patient data were not modified.
- This isolated hardening does not establish approved clinical protocol alignment or a production-ready release.

## Next authorized checks
Run the newly added fictional-data test and complete historical regression suites in the isolated developer environment, then obtain independent QA assessment and the existing fixture's approved identity/ACL and mail test prerequisites before **any** live candidate deployment. Do not misclassify offline tests as live UAT.
