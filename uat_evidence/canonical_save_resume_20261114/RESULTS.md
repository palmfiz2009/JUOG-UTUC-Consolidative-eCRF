# Canonical save recovery — continuation 2026-11-14

No live business requests, GAS deployment, ACL modification, or external QA contact. AUTH_CONNECT preserved. Formal UAT remains PASS32/FAIL1/BLOCKED29/NOT RUN5.

## Actual frontend fix and outcome

The halted entry stopped before rendering the existing expired-login logout path. Added logout only when integer native iat/exp demonstrate expiry. The halt flag is not cleared directly; subsequent login must pass native OIDC and GAS ACL checks again. Independent review passed the expiry boundary/malformed claims/unchanged guards.

Frontend86ef230 initially showed an ImportError on the newly exported helper during hot reload. Moved the identical helper (AST equality verified) into the entry itself; independently reviewed and deployed7d7859682654e31cd0cde95823e84209f37820a8. EntrySHA256:5f4774443b1168daf45889735ade5de31339bcf685f4680907c8788f2b435dec.

Live verification: expired-login button appeared; clicking it returned to the Google login screen while displaying AUTH_CONNECT/business writes prohibited. Continued to the normal Google account chooser; account selection remains required. This proves logout-path restoration, not successful reauthentication or CRF full-input completion. Screenshot contains no identity/token.

## Recovery implementation and validation

RecoverableClient now binds a lost prepare response only after matching retained actor-bound local attempt, submission_id, expected version and semantic content fingerprint, and checking same-ID request_status. It does not execute automatically. An explicit resume invokes the existing same-ID execution/readback pipeline.

Real V9 domain/lifecycle simulation: lost prepare response -> discover same operation -> content reconciliation -> explicit same-ID resume -> one saved version and one audit. Changed content rejected before discovery; altered server content hash rejected without binding or executing. Three new tests pass.

Independent review found Python/GAS number formatting mismatch for1e-5. Fixed using typed canonical representation, IEEE754 big-endian numeric bytes, UTF16 object-key ordering and ordered pairs. Cross-language16-value regression includes0/-0,1e-5/1e-6/1e-7,large/subnormal numbers,booleans,null,Unicode/numeric keys; all pass. Revised signed AUTH_CONNECT gate9tests pass with updated sourceSHA. Scoped read recovery9, Python discovery3, actualdomain discovery2 and recovery signed adapter2 also pass.

RecoveryChannel reuses original signer/native identity validation and default-deny business guard. New list_requests additionally requires a separate default-deny recovery guard and exact case/facility/record scope. Independent review found no major issue for this candidate.

## Limits preventing live approval now

Recovery route is NOT deployed. Separate API scope/deployment approval is required; full signed AUTH04 positive route remains unverified. The SQLite attempt store remains local-regression-only. The new content-binding method requires retained local attempt state; total local store loss is read-only discovery/manual reconciliation, not autonomous resume. No new persistent service was created.

Real UI six-input completion awaits legitimate account selection and ACL confirmation. Prior offline form zero-errors/12-branch evidence and initial/correction/old-version/audit results are reused, not recounted as new live PASS.

JUOG-971 already has30d v1/v2: later approved correction must freshly confirmv2, freeze exact fictional payload and producev3, preservingv1/v2. Initial save requires a separately designated unused fictional case. No records were overwritten, deleted or created here. Business approval request is not yet execution-ready because live input/state and storage integration remain incomplete.
