# Signed staged save regression

Base: 6fb364c4ca55a189950a96cd8a1b51d5aeb75f27.

Opt-in `staged_save: true` splits canonical INTENT, CRF/audit, and COMMIT across fresh authenticated requests. Intermediate responses are `ok:false / SAVE_PENDING`. The adapter permits at most two canonical recovery phases, preserves UUID and digest, and requires independent recovery/status receipt reconciliation before success. Each request retains 15-second assertion expiry, fresh jti, OIDC, B2, owner and facility checks. Existing clients retain their previous transaction route.

Validation: Python 231 tests; GAS 55 integration groups; legacy audit 13 and identity 14 checks PASS. Includes bounded pending behavior, replay rejection, identity/ACL/session revocation after INTENT and no premature success.

OFFLINE ONLY. No deployment or new formal UAT PASS is established by these results. Real hosting latency remains to be measured after isolated rollout. Formal UAT remains PASS 0 / BLOCKED 74 pending complete evidence and independent QA judgment of measurements.
