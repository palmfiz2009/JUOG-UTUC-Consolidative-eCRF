"""Read-only comparison of captured fictional live Sheets evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
def read(name):
    return json.loads((ROOT / name).read_text())['values']
def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()

crf = read('recovered_crf.json')
audit = read('recovered_audit.json')
ops = read('recovered_operations.json')
c = dict(zip(crf[0], crf[1]))
a = dict(zip(audit[0], audit[1]))
events = [json.loads(r[1]) for r in ops[1:]]
intent, commit = events
p = json.loads(c['payload_json'])
checks = {
    'one_crf_row_in_captured_range': len(crf) == 2,
    'one_audit_row_in_captured_range': len(audit) == 2,
    'intent_and_commit_only_in_captured_range': [e['kind'] for e in events] == ['INTENT', 'COMMIT'],
    'uuid_matches': all(x == c['submission_id'] for x in [a['submission_id'], intent['uuid'], commit['uuid'], p['submission_id'], commit['receipt']['submission_id']]),
    'key_matches': all(x == 'JUOG-901|perioperative_30d|30d' for x in [c['record_key'], a['record_key'], intent['key'], commit['key'], p['record_key']]),
    'version_remained_one': c['record_version'] == a['record_version'] == commit['receipt']['record_version'] == 1,
    'original_rows_unchanged': crf == read('first_save_crf.json') and audit == read('first_save_audit.json'),
    'payload_matches_preserved_intent': p == intent['payload'],
    'payload_digest_matches': sha(c['payload_json']) == intent['digest'] == commit['digest'],
    'operation_hashes_match': all(sha(row[1]) == row[2] for row in ops[1:]),
    'owner_and_expected_match': intent['actor'] == commit['actor'] == 'UAT_TEST01_PI_01' and intent['expected'] == commit['expected'] == 0,
    'receipt_verified_existing': commit['receipt']['existing'] is True and commit['receipt']['audit_verified'] is True,
    'zero_and_false_retained': p['data']['blood_loss_ml'] == 0 and p['data']['pathology']['size_mm'] == 0 and p['data']['ctcae_event'] is False,
    'missing_lab_distinct': p['data']['day30_labs']['Hb'] is None and p['data']['day30_labs_raw']['Hb'] == '',
    'fictional_contact': p['reporter_email'] == 'fictional@example.invalid',
}
out = {'kind': 'live_evidence_consistency_not_independent_qa', 'uuid': c['submission_id'], 'checks': checks, 'all_checks_true': all(checks.values()), 'scope': 'CRF/audit A1:Z20 and operation A1:Z20; server recovery independently verifies store'}
(ROOT / 'comparison.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(out, ensure_ascii=False))
assert all(checks.values())
