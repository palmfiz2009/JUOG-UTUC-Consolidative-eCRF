import sys,json,subprocess,unittest
from pathlib import Path
P=Path(__file__).parent;sys.path[:0]=[str(P),str(P.parent/'canonical_v9_save_candidate'),str(P.parent/'canonical_v9_integration')]
from recoverable_client import recovery_fingerprint
class T(unittest.TestCase):
 def test_cross_language_values(self):
  values=[0,0.0,-0.0,1,1.0,1e-5,1e-6,1e-7,1e20,1e21,0.12345678901234567,5e-324,True,None,'架空',{'10':0,'2':1,'😀':1,'\ue000':2}]
  for v in values:
   op={'action':'save_crf','payload':{'data':v}}
   js="const fs=require('fs'),crypto=require('crypto');const f=new Function(fs.readFileSync(process.argv[1],'utf8')+';return juogCanonicalRecoveryContent_;')();const op=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(crypto.createHash('sha256').update(f(op)).digest('hex'));"
   r=subprocess.run(['node','-e',js,str(P/'recovery_scope.gs')],input=json.dumps(op),text=True,capture_output=True,check=True)
   self.assertEqual(recovery_fingerprint(op),r.stdout)
if __name__=='__main__':unittest.main()
