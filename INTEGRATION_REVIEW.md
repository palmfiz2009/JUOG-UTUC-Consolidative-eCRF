# PR #15 authenticated CRF integration candidate — OFFLINE ONLY

2026-11-16 UTC. Not deployed. Profile disabled. Independent QA **not approved**.
No production/TEST/Stage 1/S2-01/main updates; no GAS stop/deploy, Sheets writes,
Streamlit switch, live login, mail or paid hosted compute performed.

## Fixed inputs

- PR #15: `73a4556b24291cb36e8800c4a99b372b5c30b759`.
- Fixture: `a2bcc6f7ff513ab30b9c8455f1b4893b465ea5ca`.
- ACL source: `4cb56d4292f4dc354b04a42cb6aea51a07b70626`.
- Development branch: `review/pr15-authenticated-crf-integration-20261116`.
- New branch is based on PR #15. Existing fixture branch is unchanged and is NOT
  switched to this commit. No new app/resource is created. `fixture_regression/`
  is a pinned source snapshot for offline tests, not a second application to deploy.

## Implemented changes

| Files | Behavior |
|---|---|
| `fixture_regression/test_auth04_config.py` | Incorrect negative example JUOG-971 changed to JUOG-970; positive exact-pin assertion and mutation of every pin added. No production validator relaxed. |
| `fixture_regression/test_uat_auth_connect.py` | Boundary panel dependency mocked in three controller unit tests. Actual boundary state machine remains separately tested. No login/ACL/revoke bypass. |
| `fixture_regression/uat_auth04_live.py`, corresponding test | Full suite exposed additional pre-existing CASE=970 versus fixture/config=971 mismatch. Fixed to exact 971; 970 explicitly denied. No widening to arbitrary cases. |
| `streamlit_app.py` | Existing fixture-style native OIDC entry, halt, signed revoke-before-logout and expiry checks; selects existing PR forms after signed ACL check. Explicit edit-start observes current versions. |
| `isolated_crf_adapter.py`, `isolated_crf_profile.json` | Disabled approval profile, exact project/workbook/generation binding, native-principal pin, real fixture HMAC signer, one request/no automatic retry, no legacy API-token fallback, frozen UUID/digest/expected-version/actor. |
| `uat_b2_auth_bridge.py`, `uat_b2_session.py`, `uat_identity_proposal.py` | Fixture authentication primitives copied unchanged. B2 remains capped at min(iat+3600, exp); this does NOT prove recent Google reauthentication/auth_time. |
| `juog_common.py` | All registry routes use signed adapter. SMTP boundary disabled. Facility selector restricted to fictional TEST01. |
| `juog_crf_save_ui.py`, `tests/test_crf_save_ui.py` | Frozen helper attempts bound to verified principal/generation. Unit-test auth dependency mocked, with separate real signer tests. PR receipt verification preserved. |
| `05_registry_google_apps_script.gs` | doPost accepts only signed integration entry; CRF/draft internals split from lock wrappers to avoid nested locks; guards before append/update/header writes. Privacy detector preserves fixture-style camelcase/NFKC/encoded-JSON/free-text rejection. |
| `isolated_auth_bridge.gs`, `isolated_session_store.gs` | Original ACL and durable B2 session/replay/expiry/chain validation reused unchanged. |
| `isolated_crf_endpoint.gs` | Single outer ScriptLock; every route authorized; exclusive case-owner binding; draft principal ownership persists across assignment changes; expected-version conflict checks; durable actor-bound intent/commit records; PR CRF+audit readback before success; partial failures do not acknowledge success. |
| `isolated_privacy.py` | Fixture Python identifier detector/redactor retained; adapter rejects changed/redacted input instead of silently saving scrubbed data. |
| `integration_tests/`, `run_offline.py`, `integration_evidence/` | Reproducible offline suite with Python TCP connections denied; actual GAS source executed against in-memory Google-service substitutes. |

## Verified offline

Run from this branch's repository root, with requirements installed:

```sh
python run_offline.py
```

- Fixture existing tests: **76 passed**.
- Fixture canonical bridge/entry tests: **20 passed**.
- PR regression tests including actual Streamlit AppTest page renders: **39 passed**.
- New Python integration/signer/entry tests: **21 passed**.
- Total Python: **156 passed** (not 156 real UAT cases).
- Full-source GAS integration: **21 test groups passed**. Includes 30d,90d,
  6m,9m,12m,15m,18m,21m,24m v1/v2/replay; old rows retained, body/audit loss,
  same-UUID repair, invalid signature, replay, logout, ACL, ownership, expiry,
  version conflicts, lock contention, missing schema and draft ownership. A real fixture Python signer envelope was also verified by the actual GAS verifier offline.
- PR baseline Node tests: audit/CRF regression groups and **14 identity cases passed**.
- Logs, environment versions, changed-file hashes and UAT mapping are committed.
- Test approval strings and signing keys are explicitly fictional in-memory test
  values. They are not actual PI/QA approval or production credentials.

## Important concurrency semantics

Edit-start versions are frozen. Submit-time `validate` cannot silently advance
that baseline. Same clinical UUID + exact frozen payload + same expected version
uses a **new** short-lived assertion jti. Reuse of assertion jti is denied.
An unresolved intent blocks a new UUID for that record. Two different correction
UUIDs based on the same version cannot both commit. Actual concurrent GAS
executions remain a real UAT requirement; the tests model lock rejection and
serialized version conflicts, not physical cloud concurrency.

The one-project ScriptLock does not block the old fixture GAS project. The old
writer must be stopped separately after approval. No automatic stop is included.

## Remaining major issues / release blockers

1. **Clinical server-side validation parity remains incomplete (inherited PR issue).**
   The PR hard-stop validator checks selected date/vital contradictions, not the
   complete UI conditional-required field dictionary or all future-date rules.
   Adapter rejects empty clinical data but a nonempty incomplete clinical payload
   is not thereby proven valid. The all-visit persistence fixtures test storage,
   not clinical completeness. Complete/review the server contract and negative
   cases before enabling real save UAT. Do not interpret all-green regressions
   as absence of this known gap.
2. **Browser/session loss recovery is safely stopped but not a completed user flow.**
   In-session retry preserves UUID and payload. Server `request_status` is
   owner-scoped and returns `UNCONFIRMED` or `COMMITTED_RECHECK_REQUIRED`; it never
   turns historical receipt alone into current verified success. If the browser
   loses its frozen payload/UUID, automatic reconstruction/new submission is not
   implemented. An operator reconciliation/recovery flow is still needed for NET-04.
3. **Notification success/failure UAT remains blocked.** SMTP is intentionally
   disabled. No notification outbox or mail-success claim is added. A separately
   approved existing test mailbox and notification implementation/review are needed.
4. No real OIDC-to-GAS login, Sheet transaction, cross-project writer exclusion,
   backup/restore rehearsal or independent QA has been completed here. B2 store
   has its inherited 10,000-event ceiling and fail-closed chain/head recovery;
   operational archival/recovery must be rehearsed before use.

These are deployment gates, not waived requirements. Formal UAT PASS delta: **0**.

## Necessary approved changes — NOT performed

1. Re-identify candidate undeployed GAS/fixture Sheet and all old writer deployments,
   triggers, app endpoints, API credentials and direct editing permissions.
2. Obtain individual approval for stopping every old writer; drain requests; verify
   negative writes through old endpoints. If exclusion cannot be established, stop.
3. Take consistent backup of all tabs/code/deployments/config/ACL/session events,
   session-head properties and hashes, with separately protected secrets. Confirm
   a pre-existing approved backup destination. Preserve unresolved operations.
4. Approve and provision headers only as specified in `integration_schema.json`,
   fictional Registry/owner fixtures, and verified issuer/subject ACL. No arbitrary
   case assignment or principal inferred from an email. No runtime schema creation.
5. After resolving blockers and independent review, approve code and properties on
   the existing candidate GAS. Bind `SPREADSHEET_ID` and `JUOG_PR15_CONFIG` to the
   candidate IDs in the profile; new generation and signing key, real approval refs.
   Initialize B2 genesis/head using its documented hash expression, not guessed values.
6. Approve switching only the existing fixture Streamlit to this reviewed commit,
   native OIDC configuration preserved, isolated profile and matching Secrets.
   Do not carry old AUTH_CONNECT approval flags into this new execution scope.
7. Execute the mapped 74 UAT rows with actual endpoint/deployment/version, UUID,
   payload digest, original sanitized response, Sheet row, audit and time evidence.
   No unknown outcome counts as PASS. Independent QA signs results separately.

## Rollback / recovery

Stop the single writer, retain failure-time rows/logs and pending UUIDs, reconcile
all success receipts before restoring any snapshot. Restore data/audit/operation
state consistently; compare hashes and old versions. Never delete acknowledged
records merely to return to a previous snapshot. Preserve session evidence;
revoke all old authority and use a separately approved new generation/key rather
than resurrecting revoked sessions or resetting only the B2 head. Reauthenticate,
verify ACL/ownership, old assertion rejection and outstanding operation resolution.
Resume only after independent QA/PI approval. RPO goal for acknowledged saves is
zero; RTO has not been measured. Production and main remain outside this scope.
