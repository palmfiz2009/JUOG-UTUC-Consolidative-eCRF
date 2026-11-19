# Browser-loss recovery in the existing fixture Streamlit

No new app. `streamlit_app.py` opens `isolated_recovery_ui.render` only after the existing native OIDC / signed ACL checks. Every reconciliation and retry obtains a new signed request through the unchanged B2 signer. The server rechecks ACL, case owner and session at entry and before returning/writing. Reused jti, old signatures, revoked sessions, different owners/facilities and altered payloads are denied.

The user enters the authorized JUOG case and exact CRF/visit. No UUID is generated in the recovery UI. The server reads `R1_Operations`, CRF rows and CRFSubmissionAudit under the existing single script lock:

| State | Required evidence | User action |
|---|---|---|
| SAVED | Original canonical payload/digest/actor/key; exactly one matching CRF and audit; expected Version+1 and matching COMMIT | Display UUID, Version and verified audit. No resend |
| RETRY_ALLOWED | Original canonical payload, UUID and digest retained; no conflicting operation; consistent current/expected Version; only repairable partial state | Retry with the original UUID; server selects stored payload; fresh signature required; reread after retry |
| NEEDS_RECONCILIATION | Missing/corrupt/foreign/untracked/contradictory evidence | Stop new submission, ask secretariat to reconcile |
| NO_SERVER_RECORD / transport or authentication failure | Insufficient proof of the original outcome | No success claim; stop new submission and request reconciliation |

INTENT now retains the immutable canonical payload in the existing operation journal; no sheet/column/resource is created. Legacy INTENT records without that payload cannot be reconstructed and are deliberately blocked for operator reconciliation. Read operations never repair or silently create records. Recovery retry cannot accept browser-supplied payload/digest/expected version. Existing UUID mismatch, expected-version conflict, audit readback and old-version retention rules remain enforced.

The browser's block flag stays set until verified saved evidence is read. A retry response alone never produces success. If a response is lost, the next explicit reconciliation can establish SAVED; no automatic new UUID or automatic resubmission occurs. Prior identity/session context is not transferred to a different login. Native Streamlit/OIDC behavior after real browser restart remains a live UAT item, not something in-memory mocks establish.

## Operational prerequisites (not executed)

1. Independently approve the reviewed commit, primary clinical rule table and UAT scope.
2. Re-identify the existing candidate GAS and fixture Sheet; inventory and individually approve exclusion of every old writer. A script lock cannot exclude another GAS project or direct Sheet editor.
3. Back up all data/audit/operation/owner/ACL/session tabs, script/config/deployment metadata and B2 head properties at one consistent point; protect secrets separately. Retain original UUIDs, pending payloads and hashes.
4. Individually approve deployment of the additional generated/runtime/recovery `.gs` files and existing Streamlit code switch. Preserve native OIDC, ACL and B2. No new app, new workbook or paid service is needed. Profile remains disabled until genuine approval references exist.
5. Verify canonical INTENT payloads fit the existing Sheets storage limits, recovery reads and authorization, actual simultaneous writes and browser restart/session expiry in the isolated environment. No legacy operation is silently migrated.
6. For rollback, stop the approved writer, preserve failure-time evidence, reconcile acknowledged receipts, then restore CRF/audit/journal consistently. Never roll back only the CRF table or discard acknowledged versions. Revoke old authority and obtain approval for a fresh generation/key; do not resurrect old sessions. Compare hashes and obtain independent QA/PI release before resuming.

Mail stays disabled. Neither live backup/restore, writer exclusion, hosted Actions execution nor independent QA is claimed complete.
