# JUOG-UTUC01 v2.2.9 — integrated EDC update / deployment checklist

**Status:** REVIEWED SOURCE + OFFLINE TESTED, NOT DEPLOYED.
**Date:** 2026-11-15. Patient data, production Google Sheet, existing TEST, isolated UAT projects, and \`main\` remain unchanged.

## Scope

- Screening IDs remain stable for the same facility code + original local subject code; a new submission creates a new \`review_round\`, not a new JUOG-SCR number.
- Protect historic numeric subject codes where Google Sheets stored \`01\` as \`1\`: match the original append-only ScreeningCRF JSON, not naive numeric coercion.
- Same \`submission_id\` is a replay: no extra round and no repeat reviewer request email. Retry still repairs a missing ScreeningCRF snapshot.
- Require the same original applicant email for repeated screening submissions; a legitimate change needs an office-controlled process.
- VOID, finalized INELIGIBLE, and REGISTERED cases are not automatically reopened or re-numbered.
- Show applicant-supplied history, current comorbidities and other malignancy status to all three independent MDT reviewers.
- On reviewer corrections, prefill previous judgments and stabilize the comment field label.
- Display latest radiology RECIST as non-widget read-only text on the office screen, avoiding a keyed disabled input that can show an old version.
- When a new review round is created, email MDT reviewers with the same screening ID and new review round.
- After the office confirms final MDT consensus, notify the original applicant and office using the existing method **and** send one status email to all three MDT reviewer addresses; omit internal consensus notes and patient identifiers. SMTP failure does not reverse the final decision or justify repeat finalization.
- **No** new cM1/PET or vascular-reconstruction eligibility protocol, no changes to role tokens or research criteria.

## Changed source files

- \`01_registration_crf.py\`
- \`05_registry_google_apps_script.gs\`
- \`05_admin_mdt_registration.py\`
- \`06_mdt_reviewer.py\`
- \`VERSION.txt\` and the read-only \`JUOG_Production_Preflight_v229.gs\`
- Dedicated test scripts \`tests/test_screening_identity.mjs\` and \`tests/test_mdt_integrated_ui.py\`, plus isolated GitHub Actions workflow.

## Tests and evidence

- GitHub Actions syntax + source-only tests: https://github.com/palmfiz2009/JUOG-UTUC-Consolidative-eCRF/actions/runs/43672252014 — **PASS**.
- 14 fabricated in-memory identity/reapplication/replay/VOID/closed/email-ownership cases — **PASS**.
- 4 isolated MDT notification/correction-helper unit tests — **PASS**.
- No real Streamlit Cloud interaction, SMTP delivery, GAS Web App version creation, clinical Sheet write, full end-to-end acceptance, or production deploy has been performed.

## Required isolated integration gate

1. Identify a separate isolated Streamlit app, isolated Apps Script project, isolated test Sheet, and isolated SMTP recipients. Never reuse real patient data or actual MDT recipients in this gate.
2. Save an immutable copy and hashes of source/backend before replacement; preserve credentials outside source control.
3. Deploy the branch's \`05_registry_google_apps_script.gs\` to an **isolated** GAS Web App (new version).
4. Ensure isolated app points to the isolated GAS URL, test Sheet and dummy email recipients; use the four Python files from this branch.
5. Confirm \`backend_info.backend_version=v2.2.9\` and \`environment=TEST\`; avoid a mistaken production connection.
6. Test new application → re-submission same ID, new round, re-review email; identical UUID retry → no new round/no mail; \`01\` / \`1\` remain distinct when originally different cases; mismatched applicant email rejected.
7. Test all three specialist roles receive history, while radiology does **not** see the site RECIST/invasion judgment before submitting.
8. Test a fictional reviewer correction v1→v2, verify append-only review history and current RECIST office display.
9. Test fictional office ELIGIBLE, INELIGIBLE and HOLD finalization, public reason to applicant, internal consensus text withheld, three MDT result emails, and mail failure without repeat registration.
10. Verify no new direct identifiers in Sheets, no unintended role bypass or registered ID duplication; sign off before production.

## Coordinated production cutover (only after approved TEST)

1. Record production \`main\` commit, deployed Streamlit branch, GAS deployment ID/version, Script Properties identity **without exposing key values**, target production spreadsheet ID and name. Back up all source and data.
2. Suspend new applicant submissions during the small cutover window.
3. Run the read-only \`JUOG_Production_Preflight_v229.gs\` after its source is reviewed and after the relevant backend changes are in place.
4. Deploy **GAS version v2.2.9** from this branch as a new version, preserving the existing \`/exec\` URL and verifying it points to the known production Sheet. The existing v2.2.8 front-end office page may temporarily block on version mismatch; this is intentional.
5. Only then merge/activate the corresponding Streamlit Python code on the actual production deploy branch and verify the app displays backend \`v2.2.9\`, environment \`PRODUCTION\`, and the correct Sheet name. Don't presume that merely replacing a local file updates the hosted app.
6. After release, use a nonclinical post-deploy check; do not submit a fabricated patient into production.
7. On failure, revert **both** Streamlit deploy and GAS deploy versions to their preserved known-good pair; maintain all existing append-only clinical records.

## Known existing single case

- JUOG-SCR-001–004 are marked VOID; JUOG-SCR-005 is the retained INELIGIBLE record for the same original candidate. This patch does not delete or reactivate any record.
- Future reapplication of a finalized INELIGIBLE case is **not** automatically authorized; an approved reopening workflow, not an additional ID, would be needed.

## Limits

The current chat has authorized GitHub source editing but **not direct Streamlit Cloud control or Google Apps Script Web App deployment access**. Thus this branch is safe to inspect/test, but it is not yet a running TEST or production release. Do not merge into main as a substitute for deploying GAS or validating TEST.
