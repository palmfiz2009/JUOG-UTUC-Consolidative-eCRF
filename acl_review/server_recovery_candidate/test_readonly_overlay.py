import json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from build_readonly_overlay import build,P
class OverlayTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.base=self.root/'base';self.base.mkdir()
  for name in ('canonical_v9_bridge.py','uat_b2_auth_bridge.py','uat_auth_connect.py'):
   shutil.copyfile(P.parent/'canonical_v9_integration'/name,self.base/name)
  shutil.copyfile(P.parent/'auth_connect_diagnostics/auth_diagnostics.py',self.base/'auth_diagnostics.py')
 def tearDown(self):self.tmp.cleanup()
 def imports(self,overlay):
  code='import sys;sys.path[:0]='+repr([str(overlay),str(self.base)])+';import readonly_probe;print("IMPORTED")'
  return subprocess.run([sys.executable,'-I','-B','-c',code],cwd=self.root,capture_output=True,text=True)
 def test_old_two_file_recipe_fails_new_overlay_imports(self):
  old=self.root/'old';old.mkdir()
  shutil.copyfile(P/'readonly_probe.py',old/'readonly_probe.py')
  shutil.copyfile(P/'readonly_streamlit_entry.py',old/'streamlit_app.py')
  failed=self.imports(old);self.assertNotEqual(failed.returncode,0);self.assertIn("No module named 'content_fingerprint'",failed.stderr)
  before={p.name:p.read_bytes() for p in self.base.iterdir()}
  out=self.root/'overlay';manifest=build(self.base,out)
  self.assertEqual(set(manifest['files']),{'streamlit_app.py','readonly_probe.py','content_fingerprint.py'})
  self.assertFalse(manifest['activation_authorized'])
  result=self.imports(out);self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout.strip(),'IMPORTED')
  self.assertEqual(before,{p.name:p.read_bytes() for p in self.base.iterdir() if p.is_file()})
 def test_missing_dependency_creates_no_output(self):
  (self.base/'canonical_v9_bridge.py').unlink();out=self.root/'overlay'
  with self.assertRaises(FileNotFoundError):build(self.base,out)
  self.assertFalse(out.exists())
 def test_existing_destination_is_never_overwritten(self):
  out=self.root/'overlay';out.mkdir();(out/'keep').write_text('OFFLINE')
  with self.assertRaisesRegex(ValueError,'DESTINATION_MUST_NOT_EXIST'):build(self.base,out)
  self.assertEqual((out/'keep').read_text(),'OFFLINE')
 def test_output_inside_app_is_denied(self):
  with self.assertRaisesRegex(ValueError,'OUTPUT_MUST_BE_OUTSIDE_APP'):build(self.base,self.base/'new')
  self.assertFalse((self.base/'new').exists())
if __name__=='__main__':unittest.main()
