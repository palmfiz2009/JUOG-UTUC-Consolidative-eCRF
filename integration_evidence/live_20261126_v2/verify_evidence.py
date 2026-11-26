"""Offline consistency checks on actual fictional live captures; not QA approval."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
def read(name):
    return json.loads((ROOT / name).read_text())['values']
def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()

crf = read('after_save_CRF_30d.json')
audit = read('after_save_CRFSubmissionAudit.json')
ops = read('after_save_R1_Operations.json')
records = [dict(zip(crf[0], r)) for r in crf[1:]]
audits = [dict(zip(audit[0], r)) for r in audit[1:]]
events = [json.loads(r[1]) for r in ops[1:]]
p1, p2 = [json.loads(r['payload_json']) for r in records]
expected_data = json.loads(json.dumps(p1['data']))
expected_data['day30_labs']['WBC'] = 6
expected_data['day30_labs_raw']['WBC'] = '6'
checks = {
    'exactly_versions_1_2_in_capture': [r['record_version'] for r in records] == [1, 2],
    'exactly_two_audit_rows': len(audits) == 2,
    'exactly_two_intents_two_commits': [e['kind'] for e in events] == ['INTENT', 'COMMIT', 'INTENT', 'COMMIT'],
    'version1_row_preserved': crf[:2] == read('after_disconnect_CRF_30d.json'),
    'version1_audit_preserved': audit[:2] == read('after_disconnect_CRFSubmissionAudit.json'),
    'version1_operations_preserved': ops[:3] == read('after_disconnect_R1_Operations.json'),
    'only_wbc_data_changed': p2['data'] == expected_data,
    'correction_reason_present': bool(p2['correction_reason']) and p2['submission_kind'] == '訂正報告',
    'distinct_uuids': records[0]['submission_id'] != records[1]['submission_id'],
    'journal_hashes_valid': all(sha(r[1]) == r[2] for r in ops[1:]),
}
for version, record in enumerate(records, 1):
    intent, commit = events[(version-1)*2:version*2]
    audit_row = audits[version-1]
    checks[f'v{version}_binding_payload_audit_receipt'] = (
        record['submission_id'] == intent['uuid'] == commit['uuid'] == audit_row['submission_id'] == commit['receipt']['submission_id']
        and record['record_key'] == intent['key'] == commit['key'] == audit_row['record_key'] == 'JUOG-901|perioperative_30d|30d'
        and sha(record['payload_json']) == intent['digest'] == commit['digest']
        and json.loads(record['payload_json']) == intent['payload']
        and audit_row['record_version'] == commit['receipt']['record_version'] == version
        and commit['receipt']['audit_verified'] is True
        and intent['actor'] == commit['actor'] == 'UAT_TEST01_PI_01'
        and intent['expected'] == commit['expected'] == version-1
    )
result = {'checks': checks, 'all_checks_true': all(checks.values()), 'formal_uat_pass_delta': 0,
          'initial_save_response': 'AUTH_EXPIRED', 'reconciliation_ui': 'V1 and V2 audit verified',
          'scope': 'Actual live UI plus independent Sheets A1:Z20; flattened columns beyond Z not inspected.'}
(ROOT/'comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(result, ensure_ascii=False))
assert all(checks.values())
