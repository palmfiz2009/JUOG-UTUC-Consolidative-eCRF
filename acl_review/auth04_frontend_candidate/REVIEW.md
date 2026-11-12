# AUTH04 frontend minimal candidate

Review only; no deployment or permission to execute AUTH04.

Transplanted exactly four functions from the previously tested candidate; all unrelated functions unchanged. `capture_restore_redaction.patch` targets the source hash in `source_identity.json`. Current auth-connect source was left unchanged.

Validation: 9 test methods PASS, including parity against 12 existing GAS redaction fixtures; date/datetime/timezone, null/false/zero, clinical notes, age and birth year-month preserved.

## Remaining risks

- REVIEW ONLY: candidate not imported by live UI, not deployed, no AUTH04 execution approval.
- Restore skips prohibited keys but does not erase values already in session_state. All four inspected current CRF call sites clear their reg_/peri_/d90_/fu_ and widget prefixes first. Real UI integration must retain that ordering.
- Unlabeled names/identifiers are not reliably detected; labels in harmless prose may over-redact. The entire matched string is replaced, so clinical free text mixed with identifier labels is lost and requires user review.
- Embedded JSON strings are parsed/redumped; formatting may change while JSON value meaning remains. Unsupported nested types/cycles/depth attacks and arbitrary restore key scoping are not hardened by this minimal transplant.
- Candidate sanitizes capture and restore; it does not erase old persisted drafts or append-only history. Genuine legacy ownership still requires verified V3_DraftOwners.
- No browser widget, live GAS persistence, audit, notification-channel or authorization test performed. Nine unit tests and twelve fixture parity checks are offline evidence only.
- Full candidate file is tied to recorded base hash. Apply only patch after verifying current source identity; do not overwrite newer auth-connect changes.
- No changes to formal UAT count; AUTH04 remains FAIL pending real isolated evidence and separate approvals.
