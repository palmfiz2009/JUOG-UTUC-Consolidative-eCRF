# Live autosave Version 7 and bounded lock wait

Code 3a4770e1fe49680ccaf6c5e128869f280fcaa12f was deployed to existing GAS Version 7 at 2026-11-27 23:47 JST. Existing URL, ACL, assertion lifetime and external-mail stop unchanged. Four 30d section receipts observed; section4 alone revised after WBC blank→0. Reload/case validation/server resume restored 0, empty Neutro and fictional contact. Independent full DraftEvents read verified 255 outer/inner hashes. No new CRF Version was created.

## Follow-up finding

9m entry retrieved 30d Version5, reference date 2026-01-10 and target 2026-10-10. A connection-uncertain stop occurred; explicit reconnect preserved entered values. Later AUTH_EXPIRED halted entry. Only 9m section2 revision1 persisted at 14:55:23.175Z. No formal 9m submission occurred. Do not claim all-visit resolution from the successful 30d subset.

The endpoint allowed a 30-second lock wait despite 15-second assertions. This is a provable expiry path, not a measured attribution of every live timeout. The follow-up patch caps lock wait at 1 second; busy requests return LOCK_TIMEOUT before any storage/auth-event mutation, and require a later newly signed request. Signature/session/ACL expiry checks stay unchanged. Tests cover zero writes on contention, fresh retry, expired old assertion rejection. Python231, GAS59 groups and legacy13/14 PASS. These are offline regressions, not formal UAT.

User-reported independent QA approval for previously measured results is recorded in PR #15 comment7221325105. Untested criteria are not included in that report. Formal UAT is not declared complete.
