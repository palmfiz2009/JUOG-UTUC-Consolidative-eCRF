"""Read-only continuation of independently evidenced B971 trials.

This module is not deployed. No write request, auth extension or QA status change.
"""
import hashlib
import json

RECORDED_SOURCE = 'f021782ad80bc7382876e872647ec3ec80148537d83ea9634085b44590468d05'
GAS_SOURCE = '211159ea4c29a0047ed3b7e97d0558c4afd30eca897b455445e4658c39b74b85'
FIXTURE_SOURCE = '0bd57252f46b6ac98c1e11d7e7bf983e91ef240ff3c0426c06b9b7bdf0f2e72d'
KEYS = {'JUOG-971|perioperative_30d|30d', 'JUOG-971|day90|90d', 'JUOG-971|followup|6m'}

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def verify_checkpoint(raw, expected_sha, steps, histories, statuses):
    """Inputs histories/statuses are fresh authenticated reads, never checkpoint copies."""
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise PermissionError('CHECKPOINT_HASH_MISMATCH')
    c = json.loads(raw)
    required = {'scope', 'recorded_source_sha256', 'gas_sha256', 'fixture_sha256',
                'cursor', 'completed', 'histories', 'evidence_ref', 'unresolved_operations'}
    if set(c) != required or c['scope'] != 'TEST01/JUOG-971':
        raise PermissionError('CHECKPOINT_INVALID')
    if (c['recorded_source_sha256'] != RECORDED_SOURCE or c['gas_sha256'] != GAS_SOURCE
            or c['fixture_sha256'] != FIXTURE_SOURCE or c['unresolved_operations'] != []
            or not isinstance(c['evidence_ref'], str) or not c['evidence_ref']):
        raise PermissionError('CHECKPOINT_PROVENANCE_INVALID')
    cursor = c['cursor']
    if type(cursor) is not int or not 0 < cursor <= len(steps) or len(c['completed']) != cursor:
        raise PermissionError('CHECKPOINT_CURSOR_INVALID')
    if len(statuses) != cursor or set(histories) != KEYS or set(c['histories']) != KEYS:
        raise PermissionError('CHECKPOINT_READS_MISSING')
    seen = set()
    for i, proof in enumerate(c['completed']):
        if set(proof) != {'index', 'operation_id', 'expected_state', 'expected_error'}:
            raise PermissionError('CHECKPOINT_PROOF_INVALID')
        op = proof['operation_id']
        if type(proof['index']) is not int or proof['index'] != i or type(op) is not str or not op or op in seen:
            raise PermissionError('CHECKPOINT_OPERATION_INVALID')
        seen.add(op)
        error = steps[i]['expected_error']
        state = 'FAILED' if error else 'SAVED'
        if proof['expected_state'] != state or proof['expected_error'] != error:
            raise PermissionError('CHECKPOINT_EXPECTATION_INVALID')
        actual = statuses[i]
        if (actual.get('ok') is not True or actual.get('state') != state
                or actual.get('operation_id') != op or actual.get('action') != 'save_crf'):
            raise PermissionError('CHECKPOINT_STATUS_MISMATCH')
        if error and actual.get('error') != error:
            raise PermissionError('CHECKPOINT_REJECTION_MISMATCH')
    for key, records in histories.items():
        pin = c['histories'][key]
        expected = [s['payload'] for s in steps[:cursor]
                    if s['payload']['record_key'] == key and not s['expected_error']]
        if (set(pin) != {'sha256', 'versions'} or pin['versions'] != list(range(1, len(expected)+1))
                or any(type(n) is not int for n in pin['versions'])
                or any(type(r.get('record_version')) is not int for r in records)
                or digest(records) != pin['sha256'] or [r['record_version'] for r in records] != pin['versions']
                or len(records) != len(expected)):
            raise PermissionError('CHECKPOINT_HISTORY_MISMATCH')
        for record, payload in zip(records, expected):
            if record['record_key'] != key or record['payload'] != payload:
                raise PermissionError('CHECKPOINT_PAYLOAD_MISMATCH')
    return cursor, c['evidence_ref']
