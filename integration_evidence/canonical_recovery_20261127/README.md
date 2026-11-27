# Bounded canonical recovery — 2026-11-27

Base review HEAD: d9d4d2de0e1a123be4118b0925d5d9368dfe9ada.

Observed trigger: fictional JUOG-901 30d Version 3 first save returned AUTH_EXPIRED after CRF/audit writes. Manual same-UUID recovery subsequently committed; see ../live_v3_recovery_20261127. That was not a clean initial-save PASS.

This change allows one automatic recovery_retry only after independently reading RETRY_ALLOWED and matching the exact original UUID/payload digest. It submits identifiers only; GAS uses its canonical INTENT payload and rechecks owner/ACL/B2/version/lock. Fresh native identity and new signed jti for every call. No assertion lifetime changes. A new status read and request receipt must prove SAVED, expected Version, audit and digest before UI success. A pending, denied, mismatched or unverified result remains blocked. UI explicitly says canonical recovery was performed.

Regression: Python 229 tests (76 + 20 + 43 + 90), GAS endpoint 52 groups, existing CRF audit and identity suites all exit 0. Socket access denied in Python runner. Added 5 tests: bounded retry/fresh signatures/no payload resend, digest mismatch, ACL denial, native expiry/actor change, and persistent pending without COMMIT.

These are OFFLINE results. New behavior has NOT yet been verified live at this commit. Formal UAT delta 0. No independent QA judgment of these measured results is claimed. GAS, Sheets, ACL, external mail, production and main unchanged by this code commit.
