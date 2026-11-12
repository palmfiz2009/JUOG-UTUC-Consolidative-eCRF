"""Review candidate: fixed-path, nonsecret AUTH04 execution configuration.

No Secrets access, environment-variable fallback, request input, or credential
copying. This module alone does not enable the frontend or the GAS server gate.
"""
import json
from pathlib import Path

_PATH = Path(__file__).with_name('auth04_runtime.json')
_FIELDS = {'enabled', 'stage', 'fixture_id', 'facility_code', 'fixture_sha256',
           'url', 'session_store_generation', 'approval_ref', 'review_ref',
           'prerequisites_verified', 'notifications_disabled', 'write_actions'}
_PINS = {
    'stage': 'AUTH04_APPROVED',
    'fixture_id': 'JUOG-970',
    'facility_code': 'TEST01',
    'fixture_sha256': '0747f9ac3f59a6e230cc6cc6debaebde3138578ec82741567e995ab1e2d0d126',
    'url': 'https://script.google.com/macros/s/AKfycbzLj9Dr-vUM6sTZHFOsxo0dUrscxNCp6LA196n2IBtYF3vYJ3ttnWLW3dY2eWJ7Gpf3GQ/exec',
    'session_store_generation': 'd72bcf33-423d-4c4d-862d-2e2d69bc3edf',
}


def validate_config(value):
    """Return validated config; reject unknown fields, including credentials."""
    if type(value) is not dict or set(value) != _FIELDS:
        raise ValueError('AUTH04_CONFIG_INVALID')
    if any(type(value[k]) is not bool for k in
           ('enabled', 'prerequisites_verified', 'notifications_disabled')):
        raise ValueError('AUTH04_CONFIG_INVALID')
    if any(type(value[k]) is not str or value[k] != v for k, v in _PINS.items()):
        raise ValueError('AUTH04_CONFIG_INVALID')
    if (type(value['write_actions']) is not list or
            value['write_actions'] != ['save_draft', 'save_crf']):
        raise ValueError('AUTH04_CONFIG_INVALID')
    for key in ('approval_ref', 'review_ref'):
        if type(value[key]) is not str or len(value[key]) > 300:
            raise ValueError('AUTH04_CONFIG_INVALID')
    if value['enabled'] and (not value['prerequisites_verified'] or
            not value['notifications_disabled'] or
            not value['approval_ref'].strip() or not value['review_ref'].strip()):
        raise ValueError('AUTH04_CONFIG_INVALID')
    return dict(value, write_actions=list(value['write_actions']))


def load_config():
    # Fail closed, including malformed files. Never include the input/exception
    # in the public error because a misconfigured file might contain a secret.
    try:
        raw = _PATH.read_text(encoding='utf-8')
        if len(raw) > 4096:
            raise ValueError()
        return validate_config(json.loads(raw))
    except Exception:
        raise PermissionError('AUTH04_CONFIG_UNAVAILABLE') from None
