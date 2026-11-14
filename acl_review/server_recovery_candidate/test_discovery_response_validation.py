"""Local-state-loss discovery must not report invalid journal rows as clear."""
import sys, unittest
from pathlib import Path
P=Path(__file__).parent
sys.path[:0]=[str(P),str(P.parent/'canonical_v9_integration')]
from recovery_client import discover, KEY, BridgeError

class DiscoveryValidation(unittest.TestCase):
 def call_for(self, rows, status=None):
  self.calls=[]
  def call(action,payload):
   self.calls.append(action)
   if action=='list_requests': return dict(ok=True,read_only=True,record_key=KEY,requests=rows)
   return status
  return call
 def test_unknown_state_is_not_no_pending(self):
  with self.assertRaisesRegex(BridgeError,'RECOVERY_ROW_INVALID'):
   discover(self.call_for([dict(operation_id='offline',state='UNKNOWN',phase='PREPARED')]))
  self.assertEqual(self.calls,['list_requests'])
 def test_inconsistent_terminal_phase_is_rejected(self):
  with self.assertRaisesRegex(BridgeError,'RECOVERY_ROW_INVALID'):
   discover(self.call_for([dict(operation_id='offline',state='SAVED',phase='AUDIT_OR_COMMIT_PENDING')]))
 def test_bad_status_phase_is_not_saved(self):
  row=dict(operation_id='offline',state='UNFINISHED',phase='PREPARED')
  status=dict(ok=True,operation_id='offline',action='save_crf',state='SAVED',phase='PREPARED')
  with self.assertRaisesRegex(BridgeError,'RECOVERY_STATUS_UNCONFIRMED'):
   discover(self.call_for([row],status))
 def test_unexpected_payload_is_not_returned(self):
  row=dict(operation_id='offline',state='SAVED',phase='COMMITTED',payload={'patient_name':'OFFLINE-MARKER'})
  with self.assertRaisesRegex(BridgeError,'RECOVERY_ROW_INVALID') as raised:
   discover(self.call_for([row]))
  self.assertNotIn('OFFLINE-MARKER',str(raised.exception))

if __name__=='__main__':unittest.main()
