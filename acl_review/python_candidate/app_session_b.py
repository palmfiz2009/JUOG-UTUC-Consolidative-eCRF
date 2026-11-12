"""Review candidate only. Verified OIDC claims enter from native server st.user.

Token issuance time bounds app authority; it is NOT human authentication time.
Provision the durable database explicitly. Runtime never recreates lost state.
"""
import hashlib
import json
import os
import sqlite3


def provision(path):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE sessions (key TEXT PRIMARY KEY, expires INTEGER NOT NULL, revoked INTEGER NOT NULL DEFAULT 0)')


def session_key(claims, environment, now):
    iat, exp = claims.get('iat'), claims.get('exp')
    nonce = claims.get('nonce')
    if (type(iat) is not int or type(exp) is not int or
            not 0 <= iat <= now < exp or exp <= iat or
            not isinstance(nonce, str) or not nonce):
        raise PermissionError('SESSION_CLAIMS_INVALID')
    aud = claims.get('aud')
    aud = [aud] if isinstance(aud, str) else aud
    if not isinstance(aud, list) or not aud or any(not isinstance(a, str) or not a for a in aud):
        raise PermissionError('SESSION_CLAIMS_INVALID')
    material = ['JUOG-B-v1', environment, claims.get('iss'), claims.get('sub'),
                sorted(aud), claims.get('azp'), iat, exp, nonce]
    return hashlib.sha256(json.dumps(material, separators=(',', ':')).encode()).hexdigest()


def check(claims, cfg, now, revoke=False):
    if (cfg.get('session_environment') != 'JUOG_AUTH04_ISOLATED_TEST01' or
            cfg.get('session_b_safety_review_approved') is not True or
            cfg.get('session_b_limited_execution_approved') is not True or
            cfg.get('session_b_durable_store_confirmed') is not True):
        raise PermissionError('SESSION_B_NOT_APPROVED')
    key = session_key(claims, cfg['session_environment'], now)
    expiry = min(now + 3600, claims['iat'] + 3600, claims['exp'])
    if expiry <= now:
        raise PermissionError('APP_SESSION_EXPIRED')
    path = cfg.get('session_b_db_path')
    if not isinstance(path, str) or not os.path.isabs(path) or not os.path.isfile(path):
        raise PermissionError('SESSION_STORE_UNAVAILABLE')
    try:
        # mode=rw ensures even deletion between the checks cannot create an empty DB.
        from pathlib import Path
        db = sqlite3.connect(Path(path).as_uri() + '?mode=rw', uri=True, timeout=5)
        try:
            with db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('INSERT OR IGNORE INTO sessions(key,expires,revoked) VALUES (?,?,?)', (key, expiry, int(revoke)))
                if revoke:
                    db.execute('UPDATE sessions SET revoked=1 WHERE key=?', (key,))
                stored_expiry, revoked = db.execute('SELECT expires,revoked FROM sessions WHERE key=?', (key,)).fetchone()
        finally:
            db.close()
    except (sqlite3.Error, OSError, ValueError) as exc:
        raise PermissionError('SESSION_STORE_UNAVAILABLE') from None
    if revoke:
        return None
    if revoked or stored_expiry <= now:
        raise PermissionError('APP_SESSION_EXPIRED_OR_REVOKED')
    return min(stored_expiry, expiry)


def revoke_and_logout(st):
    import time
    now = int(time.time())
    iat, expiry = st.user.get('iat'), st.user.get('exp')
    if type(iat) is int and type(expiry) is int and now >= min(iat + 3600, expiry):
        # An already-expired token cannot obtain B authority even without its DB row.
        st.logout()
        return
    # Failure to durably revoke must not silently proceed to cookie-only logout.
    check(st.user, st.secrets['juog_identity_bridge'], now, revoke=True)
    st.logout()


def policy_logout(st):
    if st.secrets['juog_identity_bridge'].get('session_policy') == 'isolated_gas_session_b2':
        import time
        now = int(time.time())
        iat, expiry = st.user.get('iat'), st.user.get('exp')
        if type(iat) is int and type(expiry) is int and now >= min(iat + 3600, expiry):
            st.logout()
            return
        from streamlit_unified_client import _post
        result = _post(st, 'session_revoke', {}, 30)
        if result.get('ok') is not True or result.get('revoked') is not True:
            raise PermissionError('SESSION_REVOCATION_NOT_CONFIRMED')
        st.logout()
    elif st.secrets['juog_identity_bridge'].get('session_policy') == 'isolated_app_session_b':
        revoke_and_logout(st)
    else:
        st.logout()
