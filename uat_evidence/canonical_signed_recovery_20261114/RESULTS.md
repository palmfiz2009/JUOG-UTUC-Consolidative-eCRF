# Signed recovery integration — 2026-11-14 JST

Formal UAT unchanged: PASS32 / FAIL1 / BLOCKED29 / NOT RUN5. No live business send, GAS deployment, ACL edit, mode change, external communication or main change in this continuation.

## Browser versus EDC

Created fresh browser tab13 and verified existing isolated Streamlit responds normally with AUTH_CONNECT and business-write prohibition. It shows Google login, not authenticated ACL success. Google account chooser opened normally; the individual's choice is pending. Previous tab loss is not classified as ACL denial or EDC failure. No cookies/tokens were read or edited. CRF zero-missing/zero-error live input remains pending authentication; previous offline form evidence is reused.

## New completed technical work

Full signed-entry integration now covers decoder/HMAC, individual ACL, session/replay store, exact scope, actual Sheets journal adapter, lifecycle, recovery list, execute/status/read. Eighteen checks pass, including signed save->COMMITTED status->read submission/version and one sealed audit, no journal changes from recovery reads, wrong actor/facility/case/role, invalid/expired/replayed signature, disallowed API and absent approval. The fixture substitutes exactly two principal allowlist constants IN MEMORY with fictional identity; candidate source is unmodified. This is an offline complete-entry test, not real Google authentication or live UAT. Source and fixture SHA are recorded in full_entry_results.json.

Independent review identified a race where a delayed recover_prepare could reset EXECUTING to PREPARED. Binding now uses a compare-and-set restricted to PREPARING with no operation ID; competing execution cannot be rewound. Resume claims PREPARED->EXECUTING atomically. An uncertain execute is status-only thereafter; no automatic re-execute. Unknown status phase fails closed. A separate server guard, under the existing ScriptLock, refuses another prepare while an unfinished canonical request exists.

RecoverableClient checks authoritative signed request history before new prepare. Unknown prior submissions in a new/empty local store cause LOCAL_STATE_LOST_MANUAL_RECONCILIATION. New race/loss and unsafe-phase/uncertain-execute tests pass. Earlier tests were rerun only for changed-code regression, not credited as additional UAT progress.

Scope hardening: candidate AUTH04 routes require the separate recovery-read approval; removing this flag cannot restore old broad AUTH04 routes. Session revocation stays available. Exact971/30d read/list/status only. Prepare/execute additionally require separate write approval and review reference; drafts/90d/export are excluded. AUTH_CONNECT continues to deny business routes. No live approval flags were set.

## Local store completely lost — bounded safe recovery policy

1. Stop new prepare and execute. Empty local SQLite is never evidence of an empty server history.
2. Through separately approved signed recovery reads, obtain only own971/30d request metadata, status and authenticated readback; preserve journal originals.
3. For COMMITTED requests, reconcile submission ID, expected/latest version, clinical payload fingerprint and the domain's audit-chain verification. Do not re-execute.
4. For unfinished/unknown/ambiguous requests, remain stopped. Recover original approved payload/attempt manifest from a controlled source, match actor/scope/submission/base/content and exact operation ID, and obtain a recorded manual decision before resumption. Missing original evidence means no resumption.
5. Do not synthesize a new submission or operation ID, import an unverified local record, discard pending entries or use a new case to hide an uncertain result.

Automatic reconstruction after total local loss is NOT implemented. Manual handling is an explicit operational dependency. SQLite remains a local regression store; no durable shared Streamlit store or paid infrastructure was added. Server journal and global lock provide authoritative evidence and pending-request exclusion, but do not make local storage durable.

## Concrete limited changes for later approval — not activated

Candidate GAS SHA256 ea70e3970a10a405cebdcf6f049ce2f426a91337dadc8846b5a9886b0a382383, reproducible from Version9 plus build_patch.py/recovery.patch. Same script, deployment target and isolated Sheets as Version9. Deploy only after separate approval and source verification; maintain AUTH_CONNECT at deployment.

Then a separately time-limited read-only activation would permit only context/revoke and own TEST01/JUOG-971/perioperative_30d/30d list_requests/read_crf/request_status. Keep canonicalRecoveryWriteApproved false; verify writes denied. AUTH04 stage transition required by existing design is not currently authorized and must be explicitly included in such approval. Stop procedure is return to AUTH_CONNECT, not merely clear an individual approval flag. Preserve existing165 rows/audit and verify before/after hashes.

Actual business saving remains outside authorization. Before requesting it: authenticate and complete live form input; fresh-read971 latest30d version (previous evidence v2); reconcile existing operation history/manual baseline; freeze payload/hash/API and exactv2->v3 correction; preservev1/v2. Initial saving requires separately designated unused fictional case. Preserved snapshot has only approved970/971 TEST01 registry rows; no new number assigned, no fresh registry/ACL claim made here.

## Other UAT

POST-03/04 form branches and prior saved pathology evidence reused; untested pCR combinations not declared passed. POST-06 specification/QA judgement remains separate from generic VALIDATION_FAILED behavior. AUTH-04 historical marker/host-log/backup access limitations persist; no old history deleted. FUP/A/C and60-minute live proof are not upgraded from these recovery tests. No new evidence is claimed for those unrelated live gaps; external QA remains on hold.
