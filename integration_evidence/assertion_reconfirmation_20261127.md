# Expired request assertion: fail-closed reconfirmation

Parent: f0b7ec87ed2c25461e936fa1785ca6be2d3cc4c8.

After the bounded fresh-signature/read-only reconciliation paths exhaust AUTH_EXPIRED, retain input only when the native OIDC identity and existing B2 deadline still validate. Block all business and recovery routes until a new signed ui_context confirms pinned Script/Sheet/stage/generation, TEST01 facility role and business_writes_allowed=true. Invalid binding or false write authorization cannot release this gate. Real identity/deadline expiry, SESSION_REVOKED, ACL_DENIED, ACL_CHANGED and SESSION_STORE_INVALID retain denial. Assertion TTL, B2 duration, ACL, owner checks and server nonce/jti rules are unchanged; no credential/config/GAS change.

UI reports an unconfirmed connection and offers input-preserving reconfirmation. It never converts an unconfirmed save to success or issues a new UUID. Recovery displays only allowlisted error codes.

Validation: all offline suites exit 0; Python 240 (76 fixture +20 bridge/entry +43 PR +101 integration), GAS 60 groups, existing audit/identity suites pass. Four added cases cover the gate/binding/ACL check, real deadline expiry, ACL revocation, and entry input retention. The existing bounded-expiry test now asserts denial of subsequent writes without any transport; this changes the recovery path, not authentication acceptance. Independent mismatch subcases reset their local gate. Direct test-module execution now includes appended classes.

Live deployment and reconfirmation still require observation; these offline results add no formal UAT PASS. Current formal ledger remains PASS 1 / BLOCKED 73. Existing 9m Version 3 evidence reports both successful canonical save and an earlier section-draft failure; neither is hidden by this fix. No new independent-QA outcome is asserted.
