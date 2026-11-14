"""Read-only ACL proposal from native, verified st.user; no network or persistence.

This is defense in depth, not a JWT verifier. Never accept browser form claims.
The fingerprint identifies a proposal, not a credential or authorization grant.
"""
import hashlib
import json

VALID_UNTIL = "2026-11-19T23:59:00+09:00"


def identity_proposal(user, client_id, now):
    if not user.is_logged_in:
        raise PermissionError("LOGIN_REQUIRED")
    issuer, subject = user.get("iss"), user.get("sub")
    aud, azp = user.get("aud"), user.get("azp")
    audiences = [aud] if isinstance(aud, str) else aud
    if (issuer != "https://accounts.google.com" or
            not isinstance(subject, str) or not subject.strip() or
            not isinstance(client_id, str) or not client_id or
            not isinstance(audiences, list) or not audiences or
            any(not isinstance(a, str) or not a for a in audiences) or
            client_id not in audiences or
            (azp is not None and azp != client_id) or
            (len(audiences) > 1 and azp != client_id)):
        raise PermissionError("IDENTITY_MISMATCH")
    iat, exp, nonce = user.get("iat"), user.get("exp"), user.get("nonce")
    if (type(iat) is not int or type(exp) is not int or
            not 0 <= iat <= now < exp or exp <= iat or
            min(iat + 3600, exp) <= now):
        raise PermissionError("RELOGIN_REQUIRED")
    if not isinstance(nonce, str) or not nonce:
        raise PermissionError("NONCE_UNAVAILABLE")
    material = json.dumps(["JUOG-ACL-PROPOSAL-v1", issuer, subject], separators=(",", ":"))
    return {
        "principal_fingerprint": hashlib.sha256(material.encode()).hexdigest(),
        "oauth_client_match": True,
        "b2_claims_ready": True,
        "role": "facility",
        "facilities": ["TEST01"],
        "valid_until": VALID_UNTIL,
        "stage": "AUTH_CONNECT",
        "acl_registered": False,
        "business_writes_allowed": False,
    }
