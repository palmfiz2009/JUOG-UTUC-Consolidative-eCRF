# Canonical CRF save integration continuation — 2026-11-14

Formal UAT: PASS32 / FAIL1 / BLOCKED29 / NOT RUN5. No business network sends. No external QA contact.

## Runtime and evidence

Isolated frontend diagnostic-only commit: 49149825f2ae4ad2a35edb07eda2c38f0910f9a4. Two files only; authentication, ACL, signer and disabled-save behavior unchanged. Independent technical review and 4 diagnostic tests passed. Live screen shows PREVIOUS_FAILURE_UNCLASSIFIED and remains safely halted. Earlier failure was discarded by the old implementation, so its cause cannot be reconstructed. This is diagnostic deployment, not restored CRF access or live full-input success.

GAS remains Version9; recovery candidate was NOT deployed. No GAS settings or ACL were changed. Live D3_Journal was reread: 165 rows, normalized six-column JSON SHA-256 1414934e5e059e3cc7882486fa7cf5ee14afe99b4ab5dce9736a3c665d0b0797, identical to the preserved baseline. Raw rows/identity were not exported into this evidence.

## Completed candidate work

Prior save client in dfd20c8 is reused: actual V9 read response/version binding; initial expected version0 only after empty authenticated read; correction uses observed version; server operation ID persisted before execute; same-ID status reconciliation; committed status plus submission/version/content comparison; old versions and audit retained. Previous 11 client and 3 signed-channel tests are not counted again as new evidence. SQLite remains a local regression store, not approved Streamlit durability.

New read-only recovery candidate discovers existing owner-specific requests from the existing GAS journal after loss of client memory. Scope is TEST01/JUOG-971/perioperative_30d/30d. It returns bounded metadata only; rejects malformed metadata, wrong roles/scope and unavailable/unapproved state. Empty results do not permit new prepare. Multiple pending requests stop. Discovery never calls prepare or execute.

Independent technical reviewer reran 23 tests: scoped recovery9, modified-candidate AUTH_CONNECT signed gate9, Python discovery3, actual V9 domain/lifecycle discovery2. All passed. The latter two show lost prepare-response recovery and committed request discovery without any journal mutation during discovery. Tests use synthetic identity, in-memory sheets/domain store and clock; they are not live Google OIDC or persistent infrastructure proof.

Reproduce candidate with acl_review/server_recovery_candidate/build_patch.py against pinned Version9 source; generated bundle excluded from this evidence commit because the source is reproducible from the reviewed patch. Base and candidate SHA-256 are in source_identity.json.

## Required work before live saving

- Recovery candidate is discovery only: full signed AUTH04 entry positive-route integration, content reconciliation and guarded execution resumption are not connected. No claim of completed durable live save function.
- New scoped list_requests route requires separate GAS deployment/API scope approval. Its approval flags are not enabled in live settings. AUTH_CONNECT still denies business routes.
- Diagnose the next controlled authenticated ui_context attempt using the new safe codes; do not bypass auth or blindly reset/retry a failed business operation. Complete live six-field/branch input verification after legitimate access is restored.
- Reuse existing zero-missing/zero-error offline form fixture and 12 branch tests; they do not prove live full-input completion.
- Existing JUOG-971 has 30d versions1 and2. A first save cannot be tested there. For a later correction, require a fresh authenticated read, exact latest version2, fixed payload hash, nonempty fictional correction reason, target version3, and retention of versions1/2. Abort on any state difference.
- A separate unused fictional case needs designation and approval for live initial-save testing. No new case was created.
- Before presenting final business execution approval, finish durable recovery integration, independent review and fresh baseline/backup verification; freeze exact API/case/version/payload. No premature activation proposed here.

AUTH-04: prior identifier rejection/redacted readback evidence reused; legacy immutable history preserved. Full host/GAS log and backup access protection remain unverified. Display masking alone is not sufficient. Formal QA not performed or impersonated.
