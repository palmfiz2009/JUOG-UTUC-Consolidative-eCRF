# Independent technical safety review — editor-only auth probe gate

Scope: technical review and synthetic offline tests, not formal QA or deployment approval. Reviewed gate.gs against the existing V9 candidate entry, doPost, session store and guard in ../b971_candidate/bundle_prepare_view_candidate.gs. No service access, credential reads, ACL changes, deployments, or real probe occurred during this review.

## Disposition

Suitable for the explicitly constrained operational sequence: enable once, perform one normal OIDC ui_context attempt, immediately invoke stop regardless of probe result, and require confirmed disabled state plus post-stop evidence. This is conditional on no other authorized callers and no simultaneous manual/config editing. The helper does not implement a server-enforced one-shot authorization; it must not be described as doing so. The existing initial disabled state and runtime baseline were not independently measured by these offline tests.

## Corrected issue

The original uncertain-enable fallback serialized its old full config and could overwrite an unrelated configuration update. It now rereads the latest config, validates the fixed isolated target, stage and session policy, checks for an intervening change, and changes only authConnectReviewApproved to false. The regression test demonstrates preservation of an unrelated concurrent change. A noncooperating writer can still race between the final comparison and setProperty because PropertiesService has no compare-and-swap; the stated no-concurrent-editing constraint is necessary.

## Stop evidence

Stop writes false and confirms exact readback before reading evidence. It then validates the existing session-store hash chain/head through store.read(), returns only sessionEvents, and checks the 165-by-6 D3_Journal baseline using the pinned SHA-256 digest. No raw sheet contents or exception text are returned or logged. Evidence errors cannot reverse the disable: stopConfirmed remains true while postStopEvidenceVerified is false. A true ok on stop refers to the gate write; acceptance also requires stopConfirmed=true, postStopEvidenceVerified=true and businessBaselineUnchanged=true. Compare sessionEvents with the separately established pre-probe count of 362; this review does not establish that live count or prove event kinds merely from a count.

## Remaining limitations and business boundary

- Enabling persists until stop. A failed/interrupted operator flow can leave auth enabled. Immediate stop is operationally mandatory; a failed stop or stopConfirmed=false is unresolved, never successful completion.
- V9 receives a configuration snapshot and checks auth approval before acquiring its script lock. A request holding a stale enabled snapshot can pass after stop. The guard does not reread authConnectReviewApproved. With only the single controlled caller and the probe finished before stop, this does not create an additional authorized request. It is not a guarantee against in-flight or other callers.
- That stale snapshot remains AUTH_CONNECT, so the existing entry returns before constructing a business store/service. The reviewed path does not promote allRoutesReviewed or schemaParityApproved; the helper requires both false when enabling. It makes no ACL writes and preserves unrelated config in ordinary serialized operation.
- Session bookkeeping occurs before context payload validation in the existing entry. A failed/rejected attempt can still append auth events. Never infer that failure means no session events changed. The auth gate also has a session_revoke response branch; the operational request must be the approved ui_context request, not another action.
- An uncertain enable's emergency rollback confirms false but does not perform post-stop evidence collection. Call the normal stop function to obtain that evidence.
- Existing doPost reads signing/resume/draft property keys. This helper does not read them; review did not inspect credential values. Current-key rotation does not establish old-key rejection, which remains unmeasured.
- Baseline validation checks D3_Journal only. It supports the specific 165-row journal preservation claim, not a whole-workbook parity or complete route-review claim.

## Offline verification

Run: node offline_regression.cjs

16 cases passed. Coverage includes successful enable/stop preservation, wrong script/stage, lock contention, business/schema approval rejection, already-enabled rejection, baseline row/hash drift, ledger error after confirmed stop, baseline drift after stop, unrelated-config preservation on rollback, disabled-entry rejection, and demonstrations of the two existing server-side one-shot/stale-snapshot limitations. All mocks use synthetic config/data; the hash comparator is stubbed to exercise the decision, not to verify live contents or the production hash implementation. Entry tests stub authenticated decode and the session gate; they are targeted control-flow tests, not OIDC/session cryptographic validation or formal QA.
