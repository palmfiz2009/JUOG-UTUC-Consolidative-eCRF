# Isolated live UI and 90-day evidence, 2026-11-26/27 JST

Formal UAT baseline remains PASS 0 / BLOCKED 74. The following are developer live observations, not independent QA acceptance. This run encountered actual failures; do not describe the 90-day formal save as PASS. Start-review approval is not a verdict on these results.

## Scope and deployed code

Existing app: https://juog-utuc01-fixture-uat-20261109.streamlit.app/
Existing isolated script: 1_oVuL1i6Kmyu5egp-iDHIku-nN5JxoQ1ySPSluAsNc2gCFXGvBSJGDAR
Existing isolated Sheet: 1XaLdVGN39skmXVhiyPN-uOb9B8zjo3rmbNgYZCndJRs
Fictional case JUOG-901 / TEST01 / fictional@example.invalid only. No production/main/other TEST/Stage1/fixed S2-01 changes, no external mail, no new app or service. ACL/secrets/approval references unchanged.

Initial review HEAD c4383474c51b7c1b8e4768a33a5d681c338f608b. All source edits/tests are committed to review/pr15-authenticated-crf-integration-20261116. Targeted deployment copies only were advanced on the existing fixture deployment branch uat-fixture-isolated-20261109, with expected-HEAD leases; no force overwrite. Existing local unrelated changes were retained.

Review fixes: 2a477d2582a8d0835f12ec5c9384b1c9f496f815, 89c59990e852ee66ab227a0714d20e8424a5c134, a60caf64920b05e74d37e1999de628e5b7a87335, 6ac32d5e878517b71cadd5a764ec0a114421e6b3, 472928e9109d3a2c95c4f16b9993bb0a5933ca97.
Fixture deployment latest e12a57a7fcbe93a99f30c80dee4636b1ccfedb60 (previous ae0064aba04512ff121ed6ebc68339feb36353fa, 8d9e8a1ab8c4c3ac512a668e76d2f55e47b3acb1; original rollback 185001376644d48f6c6dee4a7843082cc7597248).

- Removed outer CRF fragments from all three pages while retaining section status timers. The former date-input blank screen did not recur during the completed 90-day form entry. All-page/live concurrency coverage remains incomplete.
- Fresh-signature read-only reconciliation of uncertain formal saves requires exact UUID/digest/version/audit and the original server COMMIT receipt. No automatic write resubmission.
- Section reconciliation requires exact operation ID/data/digest/revision/record version and verified server audit. It never creates a replacement ID.
- Read-only AUTH_EXPIRED retries are bounded to one fresh signature. Revoked/denied sessions remain blocked.
- Transient ACL connection errors stop rendering/writing and offer explicit recheck with retained allowed input keys. Actual ACL/security denial still latches halt. Timer guards include recovery, report-switch, halted identity and unconfirmed connection.

## Live observations and failures

1. Native session expiry blocked correctly; re-login used the previously authorized account. No credential changes.
2. Reload/resume restored 90-day evaluation 2026-04-10 and the existing 30-day Version 2 linkage. Later input filled blood not performed, cytology Negative, imaging and cystoscopy 2026-04-10 / no progression / no tumor, no new complication, no urinary recurrence, observation without treatment, alive confirmed 2026-04-10. All values fictional.
3. All six section statuses displayed saved. Independent connector reads found each section's append-only SECTION_SAVE rows with sequential revisions, unique operation IDs, and matching outer row digests. `draft_rows.json` captures 76 rows across historical 30-day and current 90-day drafts. Clinical form completion is not itself formal-save success.
4. 90-day initial formal submit at 2026-11-27 00:28:39 JST returned AUTH_EXPIRED. UUID e68de6b2-f6de-45a5-b117-24a04ce6bfd6, digest 0b0782a83487d400d717fd115e2d4578012f039e127deee8fa2f19e0929aefb5. Only server INTENT exists; CRF_90d remains header-only, no 90-day audit/COMMIT. Failure remains OPEN.
5. Reloading the app and using the recovery screen independently located the pending server request. One explicit same-UUID retry returned unconfirmed. Subsequent independent reads again found exactly one INTENT and no 90-day CRF/audit/COMMIT. Do not create a new UUID or resubmit through a fresh form.
6. Existing 30-day audit versions 1 and 2 and their UUIDs were unchanged in both reads. These are prior evidence, not new PASS.

AX captures record resumed input, pre-submit form, all saved sections, initial error, server pending recovery, and retry error. `verify_evidence.py` verifies captured digests, section revisions/IDs, and absence of duplicate/final rows; it performs no live writes.

## GAS performance candidate: NOT DEPLOYED

Review commit bb81840a6fc5a49728be738cc889fbcdbc7b209d modifies only isolated_session_store.gs plus its tests. Repeated session ledger verification is a plausible latency contributor; no measured runtime improvement is claimed before deployment.

Within one store/request, hash results are reused only while newly read row bytes exactly match the already verified prefix. Every read still retrieves all current cells and the head property. Any changed cell invalidates the suffix; head mismatch, historical tamper, truncation and newly appended revocation still deny. Signature lifetime remains 15 seconds; ACL, ownership, expiry and every pre-write guard remain unchanged. No cross-request authorization cache.

The existing isolated GAS editor was updated and read back byte-identically to the candidate, but deployment was NOT performed. Automatic approval review rejected opening Deploy because this exact revised deployment requires individual approval. Active deployment remains Version 3 from the prior turn. No workaround attempted.

- Before code SHA256: 03cc5d2b14cf986c0a31f513ad8a6a74373038f969121b9d7566c7fb6171c43c (`b2_before.gs`).
- Staged candidate SHA256: ddf30321934a967223bd2998fd8f5c34a23cfd289e1af738641eedaf25cddac0 (`b2_staged_not_deployed.gs`).
- Requested next operation: update the SAME existing isolated web-app deployment to a new version containing this single-file delta; retain URL, Script/Sheet IDs, access settings, secrets, ACL, generation, notifications disabled and single writer. Rollback: repoint the same deployment to Version 3. Do not delete or roll back accumulated data.
- After approval: verify deployed version/code, read recovery for the original pending 90-day UUID, explicitly retry that same UUID only, and independently match CRF/audit/COMMIT. Do not increase formal PASS until live evidence and independent QA judgment agree.

## Regression

Latest complete offline run: Python 217 = fixture 76 + bridge 20 + PR 43 + adapter 78, all PASS; GAS 50 groups PASS; prior GAS audit and 14 identity cases PASS. All seven run_offline.py suites exit 0. GitHub Actions can rerun the same suites. Hosted run status must be checked separately.

New tests cover fresh signed read-only save/section reconciliation, changed digest/UUID/version/revision refusal, revoked-session refusal, bounded read retries, transient connection vs actual ACL denial, B2 live cell/head rereads, historical tamper/truncation and new revocation. Earlier five failures were obsolete assertions requiring outer form fragments; structural expectations were updated after the rendering change, with security assertions unchanged. The earlier failing log is retained in ../reconcile_20261127/final_regression/pr.log.

Remaining: repeated AUTH_EXPIRED prevents 90-day Version 1; candidate runtime performance unmeasured; full 30-day post-fix UI regression and follow-up visits, fault/concurrency/mail tests, and independent QA acceptance of measured outcomes remain incomplete. No UAT completion or production readiness claim.
