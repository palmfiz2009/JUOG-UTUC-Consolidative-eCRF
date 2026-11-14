# Independent technical review, 2026-11-14 UTC
Reviewer: separate AI technical reviewer /root/review_session. Not formal third-party QA.
Verdict: no major blocker for limited authentication-entry change.
Independent checks: expired-native logout without HTTP; active-native signed revoke success before logout; revoke denial, transport exception and context failure keep halted. Streamlit logout controlflow checked; Stop/Rerun BaseException is not swallowed.
Targeted local regression: 6/6 passed. No business send added, no halt clearing, no expiry extension.
Frontend commit b33e54514dd81545f50dea362052607bdd045ab9; file SHA256 c7f7376ce6610d817a1da5acf7fee4ecc362b3e39fe760869bc3dca9b4566fe4. Only isolated entry changed; GAS Version9 unchanged.

## Live result
The new explicit logout button appeared on the halted AUTH_EXPIRED screen. Clicking it returned to the application's Google-login screen. Google sign-in then reached the account chooser. Individual account selection is pending; no new authenticated CRF run claimed. No business retry occurred.

## Expiry classification limits
AUTH_EXPIRED was returned by the GAS response. Version9 uses this code both for signature expiry and transaction-time guard expiry. Native claims had not met the entry's native-expiry logout predicate at the halted-screen observation. Therefore Google token expiry / ACL denial is not established. Exact GAS throw site and latency are not exposed in the retained safe diagnostics; classify as server-side signed-auth expiry, exact timing unresolved. Do not count as 60-minute-boundary UAT.

## Recovery candidate — not deployed
Pinned candidate SHA256 ea70e3970a10a405cebdcf6f049ce2f426a91337dadc8846b5a9886b0a382383, Version9 baseline 6d75109c4fffda3ebe4aedb0d7990f1d694ef3a331dcdb2123c10399279970d6. Previous reviewed 18-case integration reused, not rerun or counted anew.
Read target: existing isolated script/deployment and Sheets only, TEST01 facility principal, JUOG-971 perioperative_30d/30d. APIs ui_context, session_revoke, list_requests, request_status and read_crf only; prepare_request/execute_request/save_draft and all other business writes denied. Proposed approval window: maximum 30 minutes from recorded activation, never beyond ACL expiry 2026-11-19 23:59 JST. Immediate rollback to AUTH_CONNECT / Version9 on scope mismatch, unexpected response or business-journal change. Journal baseline165 rows SHA256 1414934e5e059e3cc7882486fa7cf5ee14afe99b4ab5dce9736a3c665d0b0797 must be freshly compared at activation and completion.
IMPORTANT: bb55180 candidate requires AUTH04_APPROVED even for separately gated reads. Current PI prohibits that transition and deployment. Thus current code is not deployable under present authorization. This is an explicit activation-design/approval dependency, not live recovery completion. No approval flags changed. Read approval must not imply write approval; canonicalRecoveryWriteApproved remains false.

## Remaining live work
Surgery-performed input 0/0 and signature preview require the user's new Google account selection. Existing971 cannot initial-save; fresh authenticated read must prove latestv2 before any separately approved v3 correction. Another registered unused fictional case must be verified for an initial save. Total local-state loss remains manual reconciliation, not automatic recovery. AUTH04 log/backup/history and other UAT live gaps unchanged. Formal PASS32 / FAIL1 / BLOCKED29 / NOT RUN5. No external QA contact.
