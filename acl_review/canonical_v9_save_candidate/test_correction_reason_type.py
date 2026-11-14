"""Offline correction reasons must be nonempty text before prepare/signing."""
import copy, unittest
import test_client as support
from client import BridgeError
from canonical_v9_bridge import operation
from juog_common import redact_draft_identifiers
KEY='JUOG-971|perioperative_30d|30d'

class CorrectionReasonTests(unittest.TestCase):
 setUp=support.T.setUp
 call=support.T.call
 def tearDown(self):
  self.c.close();self.rpc.terminate();self.rpc.wait()
  self.rpc.stdin.close();self.rpc.stdout.close();self.tmp.cleanup()
 def test_nontext_reason_never_prepares_correction(self):
  self.c.read();self.c.write(copy.deepcopy(support.BASE));self.c.read()
  before=self.call('inspect',{})
  prepares=sum(a=='prepare_request' for a,p in self.calls)
  for value in [None,0,False,True,123,[],{}]:
   with self.subTest(type=type(value).__name__):
    payload=copy.deepcopy(support.BASE)
    payload.update(submission_kind='訂正報告',correction_reason=value)
    with self.assertRaisesRegex(BridgeError,'^CORRECTION_REASON_REQUIRED$'):
     self.c.write(payload)
  self.assertEqual(sum(a=='prepare_request' for a,p in self.calls),prepares)
  self.assertEqual(self.call('inspect',{}),before)
 def test_empty_and_blank_denied_but_real_text_preserved(self):
  for value in ['', '  ', '\u3000\n']:
   payload=dict(support.BASE,submission_kind='訂正報告',correction_reason=value)
   with self.assertRaisesRegex(BridgeError,'CORRECTION_REASON_REQUIRED'):
    operation('save_crf',{'payload':payload},redact_draft_identifiers,{KEY:1})
  text=' 架空症例の入力値を原資料に合わせて訂正 '
  payload=dict(support.BASE,submission_kind='訂正報告',correction_reason=text)
  self.assertEqual(operation('save_crf',{'payload':payload},redact_draft_identifiers,{KEY:1})['payload']['correction_reason'],text)

if __name__=='__main__':unittest.main()
