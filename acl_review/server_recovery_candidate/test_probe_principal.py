"""Offline native signer: a probe must not mix requests from two principals."""
import copy, json, sys, unittest
from pathlib import Path
P = Path(__file__).parent
sys.path[:0] = [str(P), str(P.parent/'canonical_v9_integration')]
import readonly_probe as m
from test_bridge import native

class PrincipalTests(unittest.TestCase):
 def run_probe(self, switch):
  current = copy.deepcopy(native)
  calls = []
  cfg = dict(approved=True, candidate_sha256=m.SHA, scope=dict(m.SCOPE), write_approved=False, review_ref='OFFLINE', starts_at=1000, expires_at=2800)
  def transport(envelope):
   action = json.loads(envelope['request_json'])['action']
   calls.append(action)
   if action == 'list_requests':
    if switch: current.user['sub'] = 'OFFLINE-SECOND-PRINCIPAL'
    return dict(ok=True, read_only=True, record_key=m.SCOPE['record_key'], requests=[])
   return dict(ok=True, read_only=True, result=dict(ok=True, records=[dict(record_version=1, record_key=m.SCOPE['record_key'], submission_id='OFFLINE-LEGACY', payload=dict(registration_id='JUOG-971', facility_code='TEST01', crf_type='perioperative_30d', visit='30d'))]))
  if switch:
   with self.assertRaisesRegex(PermissionError, '^PROBE_PRINCIPAL_CHANGED$'):
    m.probe(lambda:current, transport, cfg, lambda:1001)
   self.assertEqual(calls, ['list_requests'])
  else:
   result = m.probe(lambda:current, transport, cfg, lambda:1001)
   self.assertEqual(calls, ['list_requests','read_crf'])
   self.assertEqual(result['latest_version'], 1)
   self.assertNotIn(current.user['sub'], str(result))
 def test_principal_switch_blocks_next_request(self): self.run_probe(True)
 def test_same_principal_completes_without_identifier_output(self): self.run_probe(False)

if __name__ == '__main__': unittest.main()
