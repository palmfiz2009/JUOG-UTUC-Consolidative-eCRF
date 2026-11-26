"""PR15 isolation adapter. Disabled unless a separately approved profile is installed.

Reuses the fixture native-OIDC signer. No legacy token fallback, automatic retry,
deployment, secret defaults or network at import. Business API replies are checked
against the pinned workbook and authenticated principal on every request.
"""
import copy
import hashlib
import json
import time
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from uat_b2_auth_bridge import signed_request
from uat_identity_proposal import identity_proposal

SCRIPT = '1_oVuL1i6Kmyu5egp-iDHIku-nN5JxoQ1ySPSluAsNc2gCFXGvBSJGDAR'
SHEET = '1XaLdVGN39skmXVhiyPN-uOb9B8zjo3rmbNgYZCndJRs'
STAGE = 'PR15_ISOLATED_CRFS'
ROUTES = {'ui_context','session_revoke','backend_info','validate','get_crf_linkage',
          'save_crf','save_draft','get_draft','delete_draft','read_crf','request_status','recovery_status','recovery_retry','get_sections','save_section'}

def load_profile():
    return json.loads(Path(__file__).with_name('isolated_crf_profile.json').read_text())

def context(st):
    c = load_profile()
    if (c.get('enabled') is not True or c.get('stage') != STAGE or
        c.get('script_id') != SCRIPT or c.get('spreadsheet_id') != SHEET or
        any(not isinstance(c.get(k),str) or not c[k].strip() for k in
            ('qa_ref','pi_ref','single_writer_ref','backup_ref','b2_policy_ref','principal_fingerprint','generation','url')) or
        c['generation'] == 'd72bcf33-423d-4c4d-862d-2e2d69bc3edf' or
        not c['url'].startswith('https://script.google.com/macros/s/') or not c['url'].endswith('/exec')):
        raise PermissionError('INTEGRATION_NOT_APPROVED')
    client = st.secrets['auth']['google']['client_id']
    if identity_proposal(st.user,client,int(time.time()))['principal_fingerprint'] != c['principal_fingerprint']:
        raise PermissionError('PRINCIPAL_NOT_APPROVED')
    secret = dict(st.secrets['isolated_crf'])
    if any(secret.get(k)!=c[k] for k in ('url','generation','script_id','spreadsheet_id')):
        raise PermissionError('CONFIG_BINDING_MISMATCH')
    if st.secrets['registry']['expected_spreadsheet_id'] != SHEET:
        raise PermissionError('CONFIG_BINDING_MISMATCH')
    bridge = dict(oidc_issuer='https://accounts.google.com',oidc_client_id=client,
        signing_key=secret['signing_key'],bridge_issuer='JUOG_PR15_FIXTURE',audience='JUOG_PR15_GAS',
        session_policy='isolated_gas_session_b2',session_environment='JUOG_AUTH04_ISOLATED_TEST01',
        session_store_generation=c['generation'],session_b_safety_review_approved=True,
        session_b_limited_execution_approved=True)
    return SimpleNamespace(user=st.user,secrets={'juog_identity_bridge':bridge}), c

def actor_key(st):
    # Native principal + generation, NOT reporter email or form state.
    native,c = context(st)
    signed_request(native,'ui_context',{})  # validate expiry/claims even before UI state access
    return hashlib.sha256(json.dumps([st.user.get('iss'),st.user.get('sub'),c['generation']]).encode()).hexdigest()

def transport(url,envelope,timeout):
    req=urllib.request.Request(url,data=json.dumps(envelope).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=timeout) as response:
        result=json.load(response)
    if not isinstance(result,dict):raise ValueError('INVALID_RESPONSE')
    return result

def _reconcile_save(st, body, expected, actor, timeout):
    """Read-only fresh-signature reconciliation; never retransmit a write."""
    from isolated_recovery_ui import _valid_recovery
    if actor_key(st) != actor:
        raise PermissionError('ACTOR_CHANGED')
    query = {k: body[k] for k in ('registration_id', 'facility_code', 'crf_type', 'visit')}
    status = call(st, 'recovery_status', query, timeout)
    if not _valid_recovery(status, query):
        return None
    recovery = status['recovery']
    digest = hashlib.sha256(json.dumps(body, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    matches = [x for x in recovery['operations'] if x['uuid'] == body['submission_id']]
    if (recovery['state'] != 'SAVED' or len(matches) != 1
            or matches[0].get('digest') != digest or matches[0].get('version') != expected + 1
            or matches[0].get('audit_verified') is not True or matches[0].get('state') != 'SAVED'):
        return None
    result = call(st, 'request_status', {**query, 'submission_id': body['submission_id']}, timeout)
    receipt = result.get('receipt')
    if (actor_key(st) != actor or result.get('ok') is not True
            or result.get('state') != 'COMMITTED_RECHECK_REQUIRED' or not isinstance(receipt, dict)
            or receipt.get('ok') is not True or receipt.get('audit_verified') is not True
            or any(receipt.get(k) != body[k] for k in ('submission_id', 'record_key', 'crf_type', 'visit'))
            or type(receipt.get('record_version')) is not int or receipt['record_version'] != expected + 1
            or type(receipt.get('existing')) is not bool or receipt.get('spreadsheet_id') != SHEET):
        return None
    verified = copy.deepcopy(receipt)
    verified.update({k: result[k] for k in ('spreadsheet_id', 'script_id', 'integration_stage', 'generation', 'role', 'facility_code')})
    verified['reconciled_after_uncertain_response'] = True
    return verified


def _reconcile_section(st, operation, actor, timeout):
    from isolated_autosave_ui import _read_ok, acknowledge, canonical
    query={k:operation[k] for k in ('registration_id','facility_code','crf_type','visit')}
    result=call(st,'get_sections',query,timeout)
    if actor_key(st)!=actor or not _read_ok(result,query):
        return None
    event=result['sections'].get(operation['section'])
    if not isinstance(event,dict):
        return None
    digest=hashlib.sha256(canonical(operation['data']).encode()).hexdigest()
    if (event.get('action')!='SECTION_SAVE' or event.get('key')!=result['record_key']
            or event.get('record_version')!=operation['record_version'] or event.get('digest')!=digest):
        return None
    verified=dict(result,receipt=event,reconciled_after_uncertain_response=True)
    return verified if acknowledge({},operation,verified) else None


def call(st,action,payload=None,timeout=20):
    if action not in ROUTES:return {'ok':False,'error':'ROUTE_DENIED'}
    try:
        native,c=context(st)
        actor=actor_key(st)
        if st.session_state.get('auth_connect_halted') and action!='session_revoke':
            raise PermissionError('SESSION_HALTED')
        prior=st.session_state.get('_integration_actor')
        if prior is not None and prior!=actor:
            st.session_state['auth_connect_halted']=True
            raise PermissionError('ACTOR_CHANGED')
        st.session_state['_integration_actor']=actor
        p=copy.deepcopy(payload or {})
        if action == 'save_section':
            from isolated_privacy import redact_draft_identifiers
            if redact_draft_identifiers(p.get('data', {})) != p.get('data', {}):
                raise PermissionError('DIRECT_IDENTIFIER_NOT_ALLOWED')
        if action in ('save_crf','save_draft'):
            from isolated_privacy import redact_draft_identifiers
            body=p.get('payload',{}) if action=='save_crf' else p
            if body.get('reporter_email')!='fictional@example.invalid':
                raise PermissionError('FICTIONAL_CONTACT_REQUIRED')
            if redact_draft_identifiers(body)!=body:raise PermissionError('DIRECT_IDENTIFIER_NOT_ALLOWED')
        if action=='save_crf':
            if st.session_state.get('_recovery_blocks_new'):raise PermissionError('RECOVERY_RECONCILIATION_REQUIRED')
            body=p.get('payload',{})
            if st.session_state.get('_integration_edit_subject')!=body.get('registration_id'):
                raise PermissionError('EDIT_SUBJECT_REQUIRED')
            uuid=body.get('submission_id'); key=body.get('record_key')
            digest=hashlib.sha256(json.dumps(body,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
            pending=st.session_state.setdefault('_integration_pending',{})
            if uuid in pending:
                old=pending[uuid]
                if old['actor']!=actor or old['digest']!=digest:raise PermissionError('SUBMISSION_ID_CONFLICT')
                p['expected_record_version']=old['expected']
            else:
                versions=st.session_state.get('_integration_versions',{})
                if key not in versions:raise PermissionError('OBSERVED_VERSION_REQUIRED')
                expected=versions[key]
                if type(expected) is not int or expected<0:raise PermissionError('INVALID_VERSION')
                p['expected_record_version']=expected
                pending[uuid]={'actor':actor,'digest':digest,'expected':expected}
        envelope=signed_request(native,action,p)
        try:
            r=transport(c['url'],envelope,timeout)
        except Exception:
            if action not in {'save_crf','save_section'}:
                raise
            r={'ok':False,'error':'RESULT_UNCONFIRMED'}
        if action in {'ui_context','backend_info','validate','get_crf_linkage','read_crf','request_status','recovery_status','get_sections'} and r.get('error') == 'AUTH_EXPIRED':
            # One read-only retry with freshly validated native identity and jti.
            # Never retry an expired write or a revoked/denied session here.
            refreshed, fresh_config = context(st)
            if actor_key(st) != actor or fresh_config != c:
                raise PermissionError('ACTOR_CHANGED')
            r = transport(c['url'], signed_request(refreshed, action, p), timeout)
        if action == 'save_section' and r.get('error') in {'AUTH_EXPIRED','RESULT_UNCONFIRMED'}:
            confirmed = _reconcile_section(st, p, actor, timeout)
            if confirmed is not None:
                r = confirmed
        if action == 'save_crf' and r.get('error') in {'AUTH_EXPIRED','RESULT_UNCONFIRMED'}:
            # The original assertion may expire after COMMIT. Do not bypass its
            # checks or reuse it: independently read with fresh OIDC/B2 signatures.
            confirmed = _reconcile_save(st, p['payload'], p['expected_record_version'], actor, timeout)
            if confirmed is not None:
                r = confirmed
            else:
                st.session_state['_recovery_blocks_new'] = True

        if r.get('ok') is True:
            if (r.get('spreadsheet_id')!=SHEET or r.get('script_id')!=SCRIPT or
                r.get('integration_stage')!=STAGE or r.get('generation')!=c['generation']):
                raise PermissionError('RESPONSE_BINDING_MISMATCH')
            if action!='session_revoke' and (r.get('role')!='facility' or r.get('facility_code')!='TEST01'):
                raise PermissionError('ACL_RESPONSE_MISMATCH')
            if action=='validate':
                versions=r.get('record_versions')
                if not isinstance(versions,dict) or any(type(v) is not int or v<0 for v in versions.values()):
                    raise PermissionError('INVALID_VERSION_RESPONSE')
                # Preserve observed versions until explicit subject validation is repeated.
                observed=st.session_state.setdefault('_integration_versions',{})
                for key,value in versions.items():observed.setdefault(key,value)
        elif r.get('error') in {'AUTH_EXPIRED','SESSION_REVOKED','ACL_DENIED','ACL_CHANGED','SESSION_STORE_INVALID'}:
            st.session_state['auth_connect_halted']=True
        return r
    except PermissionError as e:
        return {'ok':False,'error':str(e) if str(e) in {
            'INTEGRATION_NOT_APPROVED','PRINCIPAL_NOT_APPROVED','CONFIG_BINDING_MISMATCH',
            'SESSION_HALTED','ACTOR_CHANGED','SUBMISSION_ID_CONFLICT','OBSERVED_VERSION_REQUIRED',
            'INVALID_VERSION','RESPONSE_BINDING_MISMATCH','ACL_RESPONSE_MISMATCH','INVALID_VERSION_RESPONSE','EDIT_SUBJECT_REQUIRED',
            'FICTIONAL_CONTACT_REQUIRED','DIRECT_IDENTIFIER_NOT_ALLOWED','RECOVERY_RECONCILIATION_REQUIRED'
        } else 'AUTHENTICATION_REQUIRED'}
    except Exception:
        # Do not leak URLs, credentials or raw transport exceptions. No retry.
        return {'ok':False,'error':'RESULT_UNCONFIRMED'}

def begin_edit(st,registration_id):
    """Explicit user action, never a silent refresh during submit/retry."""
    for page in ('peri','d90','fu'):
        pending=st.session_state.get('_juog_'+page+'_save_attempt',{})
        if pending.get('status') in ('prepared','saving','uncertain','committed'):
            return {'ok':False,'error':'RECONCILE_PENDING_FIRST'}
    result=call(st,'validate',{'registration_id':registration_id,'facility_code':'TEST01'})
    if result.get('ok') is True:
        st.session_state.setdefault('_integration_versions',{}).update(result['record_versions'])
        st.session_state['_integration_edit_subject']=registration_id
    return result
