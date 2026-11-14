import sys,unittest
from pathlib import Path
P=Path(__file__).parent;sys.path.insert(0,str(P.parent/'canonical_v9_integration'))
from recovery_client import discover,KEY,BridgeError
class T(unittest.TestCase):
 def call_for(self,rows):
  self.calls=[]
  def call(a,p):
   self.calls.append(a)
   if a=='list_requests':return {'ok':True,'read_only':True,'record_key':KEY,'requests':rows}
   return {'ok':True,'operation_id':p['operation_id'],'action':'save_crf','state':'UNFINISHED'}
  return call
 def test_empty_never_permits_prepare(self):
  self.assertFalse(discover(self.call_for([]))['may_prepare']);self.assertEqual(self.calls,['list_requests'])
 def test_one_discovers_same_id_only(self):
  r=discover(self.call_for([{'operation_id':'offline-id','state':'UNFINISHED'}]));self.assertEqual(r['operation_id'],'offline-id');self.assertFalse(r['may_execute']);self.assertEqual(self.calls,['list_requests','request_status'])
 def test_multiple_stops(self):
  with self.assertRaises(BridgeError):discover(self.call_for([{'operation_id':'a','state':'UNFINISHED'},{'operation_id':'b','state':'UNFINISHED'}]))
  self.assertEqual(self.calls,['list_requests'])
if __name__=='__main__':unittest.main()
