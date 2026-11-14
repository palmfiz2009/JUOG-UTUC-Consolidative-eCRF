# Canonical save integration candidate — not deployed

Runtime remains frontend 50d607ad8f4a235d5915039ff1068ddc88b62bed / GAS Version 9 / AUTH_CONNECT. No business HTTP occurred.

Implemented: actual V9 read response unwrapping and contiguous version/scope checks; first version 0 only after authenticated empty read; correction based on observed version; server-issued operation ID persisted before execute; prepare-response loss blocks automatic reprepare; execute-response loss reconciles the same ID after client restart; committed status plus matching submission/version/content required before success. Local transaction locking prevents duplicate attempts across client instances. Unknown result never means saved.

SignedChannel reuses the existing native OIDC/B2 signer. It binds issuer, subject and isolation environment, validates before each transport, restricts actions to read_crf/prepare_request/execute_request/request_status, and denies execution by default. There is no HTTP implementation or activation flag in this candidate. The current deployed form continues to use the existing non-sending preview.

Independent technical review: review_session reran client 9 + channel 3 conditions after fixing missing readback content comparison and per-call principal binding. Final review found no major remaining issue for offline local regression. Two additional tests (two client instances, storage failure) passed subsequently; runtime code unchanged. Not formal QA.

The complete surgery fixture previously rendered through the canonical build_submission passes zero missing/zero errors and the pinned V9 validator. Existing 12 branch regression conditions are reused. A new live no-surgery attempt filled dates and reason but the ui_context check failed and the app halted before a zero-missing live result. The existing generic error discards the server error code, so the failure cannot be attributed to timeout, expiry or ACL with this evidence. No automatic retry/reset or auth bypass was performed. No live completeness claim.

## Not yet technically ready for business activation

- The SQLite store is proven only in local regression; no durable shared Streamlit storage has been identified/approved. Do not deploy this SQLite design as durable production storage.
- The client is not wired to a live business transport/form submission path. AUTH_CONNECT rejects business reads as well as writes.
- The current ui_context failure must be diagnosed without weakening controls; safe error classification instrumentation is needed to retain an allowlisted nonsecret reason on future failures.
- Existing JUOG-971 has 30d v1/v2. Initial 30d save there is prohibited. A new isolated fictional case is required for a live first-save scenario; no case/role was added.
- Full live log/backup access protection and formal QA remain unfulfilled. Historical records remain intact.

## Exact proposed later scope (NOT approved or activated)

1. Read JUOG-971 / TEST01 / perioperative_30d / 30d; require current latest version exactly 2. Abort on any difference.
2. One fictional correction with a nonempty reason, expected_record_version=2, producing v3; preserve v1/v2. Freeze final payload hash before approval. Do not overwrite or delete.
3. Only read_crf, prepare_request(save_crf), execute_request and request_status; personal facility role unchanged. No draft, registration, exports, email or uploads.
4. Verify same operation ID, content readback, v1/v2 preservation and audit after v3. On uncertain prepare, stop; on uncertain execute, status same operation only.
5. Actual execution requires a reviewed durable shared pending store, live input completion, baseline/backup reread and separate PI approval. Return to AUTH_CONNECT after any limited trial. No flags may be set solely to bypass gates.

Formal UAT remains PASS32 / FAIL1 / BLOCKED29 / NOT RUN5.
