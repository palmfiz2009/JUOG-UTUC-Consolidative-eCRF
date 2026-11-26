# 2026-11-26 JST: first live 30-day CRF save and recovery

**Actual isolated browser/GAS/Sheets observations, not offline simulation. Formal UAT PASS remains 0; independent outcome QA has not been received.**

## Environment and scope

- Existing fixture app: https://juog-utuc01-fixture-uat-20261109.streamlit.app/
- Fixture branch HEAD checked: `185001376644d48f6c6dee4a7843082cc7597248`.
- Development HEAD before this evidence: `fab66ec15d0303079621fc4eccef6a15449ee0e1`. PR #15 has a different source branch.
- Existing GAS deployment: previously verified Version 1; no GAS source/deployment or ACL changes during this run.
- Script: `1_oVuL1i6Kmyu5egp-iDHIku-nN5JxoQ1ySPSluAsNc2gCFXGvBSJGDAR`.
- Isolated Sheet: `1XaLdVGN39skmXVhiyPN-uOb9B8zjo3rmbNgYZCndJRs`.
- Only fictional TEST01 / JUOG-901 and `fictional@example.invalid` were entered. No real patient data, production, TEST, Stage 1, S2-01, main, external email or new applications were used.
- User reported adding `registry.expected_spreadsheet_id`. Live app then passed its context and ui_context gate and allowed owned-case editing. This is stronger than presence-only configuration evidence; secret values were not inspected.

## Observations and outcomes

1. Before input, bounded CRF_30d, CRFSubmissionAudit, R1_Operations and R1_DraftEvents reads contained headers only.
2. Entered the operated fictional fixture through the actual 30-day UI. Four sections displayed local saving and saved states. `drafts_before_resume.json` contains 31 append-only draft events. All 31 outer event hashes and inner canonical data hashes matched (`draft_hash_checks.json`). The basic section stopped at revision 2 while other sections changed, providing evidence against rewriting every section on each edit.
3. Closed the actual input tab (8), opened a new tab, rechecked JUOG-901, then used the authenticated server resume control. The app displayed its successful resume message, restored surgery/date/numeric/selection values and reported all required inputs complete. Dates, surgery time 120, blood loss 0, pathology size 0, WBC 5, CTCAE false and empty other laboratory inputs were observed. This verifies tab-loss resume under the existing OIDC browser cookie, **not a whole-browser restart or a fresh credential challenge**.
4. Initial formal submission at 10:10:18 JST used UUID `54a012aa-752d-4e5c-8e01-ef92406718a9`. The app displayed `AUTH_EXPIRED` and did not claim success. Independent reads nevertheless found Version 1 and its matching audit row plus INTENT, but no COMMIT. Preserve this **initial end-to-end failure**; do not label it an uninterrupted normal-path PASS.
5. Logged out through the existing session-revocation control and signed in again with the already authorized Google account. Opened recovery, selected JUOG-901 / 30-day, and the server offered retry of its preserved original request. No UUID or payload was invented or manually submitted.
6. Clicked the offered same-UUID recovery once. The UI reported successful audit reconciliation without a duplicate Version. Rechecked status: **Version 1 / same UUID / audit matched**. Actual screenshot and DOM are `recovery_screen.png` and `recovery_screen.txt`.
7. Independent connector reads found one CRF row, one audit row, and INTENT/COMMIT sequence 1/2. COMMIT at 10:13:44 JST has `existing:true`, `record_version:1`, `audit_verified:true`. Original CRF and audit rows remained unchanged. All operation hashes, payload digest, payload/INTENT equality, actor, expected Version and identifiers matched. Run `python integration_evidence/live_20261126_30d/verify_evidence.py` to reproduce the 15 checks in `comparison.json`.

## Limitations and findings requiring follow-up

- **LIVE-30D-01:** Initial save returned AUTH_EXPIRED after CRF and audit persistence, before COMMIT. Recovered without data loss or duplication. The deployed guard checks both session deadline and the 15-second assertion expiry before/after storage work; processing-time expiry is a candidate cause, not a proven timing diagnosis. Do not extend assertion lifetime or remove guards to make the test pass. Capture sanitized timing evidence and correct the latency/transaction path under review before declaring normal initial-save reliability resolved.
- During repeated input, menus could close on rerender and some clicks were not applied while a save overlay was present. All final persisted inputs were checked; the extra robot-assisted selection seen temporarily was removed before formal save. UI responsiveness remains to be evaluated systematically. The screenshot of the local overlay was observed in the tool session, but no saved file of that transient screen is claimed here.
- Full original HTTP response bodies were not exported. The stored COMMIT receipt and actual UI status are evidence of the result, not a substitute claimed to be a captured network trace.
- Sheet snapshots are bounded reads (A1:Z20 for CRF/audit/operations, A1:B200 for drafts). CRF payload_json is complete; flattened columns beyond Z were not independently compared. Server recovery also verified its store. Do not describe this as a full workbook audit.
- Formal rows `30d-D`, `30d-V1`, `30d-R` have **partial live evidence, no independent outcome approval**. Other-owner/facility denial, intentional double-click, different-payload retry and the entire row acceptance criteria were not completed in this run. Formal ledger remains PASS 0 / BLOCKED 74; this evidence does not erase the initial technical FAIL.
- Existing start-before-UAT QA approval is not outcome QA. Ask the independent reviewer to assess this evidence, including the failed first attempt and successful recovery, before any row is marked PASS. No signature or approval is fabricated.
- Version 2, 90-day/follow-up, mail success/failure, all mandatory UAT and production release are not complete. No production readiness claim.

## Files

`first_save_*.json`: post-error snapshots before recovery. `recovered_*.json`: independent post-recovery snapshots. `drafts_before_resume.json` and `draft_hash_checks.json`: draft source and digest comparison. `recovery_screen.*`: actual final browser evidence. `verify_evidence.py` / `comparison.json`: reproducible consistency check. No credentials, OAuth tokens, assertion signatures or private QA signature photos are included.
