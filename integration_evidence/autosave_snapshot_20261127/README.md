# Locked section snapshot optimization

Base: 6b907f1b809d1bcc6e2bc6d2b441bd868a05338b.

The live Version 5 save is already independently reconciled in live_staged_save_20261127. During its input session autosave halted for authentication/ACL verification. This patch reduces redundant full R1_DraftEvents reads to two per new write under the existing ScriptLock. It retains fresh pre/post snapshots, full digest/prefix checks and every authorization guard. No cross-request cache or assertion TTL change.

Offline: Python 231 tests PASS; GAS endpoint 58 groups PASS; legacy audit 13 and identity 14 cases PASS. Added tests cover two scans, next-request tamper detection, prefix corruption during append, and ACL revocation during append. The complete suite passed, then the endpoint suite was rerun after adding the explicit ACL-revocation test. Live latency improvement is not yet measured. No formal UAT PASS is inferred.

QA provenance: the user reports that Dr Takahiro Nakamoto has approved the measured results. This is recorded as a user report, not an invented signed review or approval for unexecuted cases. Previously supplied start-review images and qaRef remain distinct from test-specific coverage.
