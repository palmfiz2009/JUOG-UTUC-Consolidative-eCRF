"""Server-only Streamlit OIDC identity bridge. No network or secret defaults."""
import base64, hashlib, hmac, json, time

def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

def signed_request(st, action, payload):
    # st.user must be Streamlit's authenticated OIDC object, never session_state/form fields.
    if not st.user.is_logged_in:
        raise PermissionError('INDIVIDUAL_LOGIN_REQUIRED')
    cfg = st.secrets['juog_identity_bridge']
    sub, issuer = st.user.get('sub'), st.user.get('iss')
    if not isinstance(sub, str) or not sub or issuer != cfg['oidc_issuer']:
        raise PermissionError('IDENTITY_CLAIMS_INVALID')
    # Defense in depth after Streamlit/Authlib's OIDC verification, not a JWT verifier.
    client_id = cfg.get('oidc_client_id')
    audience = st.user.get('aud')
    audiences = [audience] if isinstance(audience, str) else audience
    if (not isinstance(client_id, str) or not client_id or
            not isinstance(audiences, list) or not audiences or
            any(not isinstance(a, str) or not a for a in audiences) or
            client_id not in audiences):
        raise PermissionError('OIDC_AUDIENCE_INVALID')
    azp = st.user.get('azp')
    if (azp is not None and azp != client_id) or (len(audiences) > 1 and azp != client_id):
        raise PermissionError('OIDC_AUTHORIZED_PARTY_INVALID')
    # A Streamlit login cookie can outlive IdP tokens; enforce fresh authentication policy.
    now = int(time.time())
    expiry = st.user.get('exp')
    if not isinstance(expiry, int) or isinstance(expiry, bool) or expiry <= now:
        raise PermissionError('OIDC_TOKEN_EXPIRED_OR_MISSING')
    auth_time = st.user.get('auth_time')
    if not isinstance(auth_time, int) or isinstance(auth_time, bool) or not 0 <= now - auth_time <= int(cfg['max_auth_age_seconds']):
        raise PermissionError('FRESH_OIDC_LOGIN_REQUIRED')
    key = str(cfg['signing_key']).encode('utf-8')
    if len(key) < 32:
        raise PermissionError('BRIDGE_NOT_CONFIGURED')
    # Sign exact UTF-8 request bytes, avoiding Python/JS number canonicalization differences.
    request = json.dumps({'action': action, 'payload': payload}, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    if len(request.encode('utf-8')) > 200000:
        raise ValueError('REQUEST_TOO_LARGE')
    claims = {'v': 1, 'iss': cfg['bridge_issuer'], 'aud': cfg['audience'],
              'oidc_issuer': issuer, 'sub': sub, 'iat': now, 'exp': now + 60,
              'request_hash': hashlib.sha256(request.encode('utf-8')).hexdigest()}
    encoded = _b64(json.dumps(claims, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
    signature = _b64(hmac.new(key, encoded.encode('ascii'), hashlib.sha256).digest())
    # Never print/log this envelope or include it in evidence.
    return {'request_json': request, 'identity_assertion': encoded + '.' + signature}
