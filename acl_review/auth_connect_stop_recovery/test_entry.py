import ast,sys,types,unittest,time
from pathlib import Path
SOURCE=Path(__file__).with_name('streamlit_app.py').read_text()
class Stop(Exception):pass
class Recovery(unittest.TestCase):
    def execute(self,logged=True,valid=True,clicked=False,context_valid=True,expired=False,halted=False,timeout=False):
        calls=[];st=types.ModuleType('streamlit');st.user=types.SimpleNamespace(is_logged_in=logged,get=lambda k: int(time.time()) + ({'iat':-4000,'exp':-100}[k] if expired else {'iat':0,'exp':3600}[k]))
        st.session_state={'auth_connect_halted':halted}
        for name in ['set_page_config','title','info','error','success','caption']:
            setattr(st,name,lambda *a,_n=name,**k:calls.append(_n))
        st.button=lambda label:clicked;st.login=lambda provider:calls.append('login');st.logout=lambda:calls.append('logout')
        def stop():raise Stop()
        st.stop=stop;bridge=types.ModuleType('uat_auth_connect')
        def context(ui):
            calls.append('native_context')
            if not context_valid:raise PermissionError()
            return object()
        bridge.context=context;bridge.context_envelope=lambda native:{'action':'ui_context'}
        def send(e):
            calls.append(e['action'])
            if timeout:raise TimeoutError()
            return {'verified':valid}
        bridge.send=send;bridge.valid_context=lambda r:r['verified']
        sys.modules.update(streamlit=st,uat_auth_connect=bridge)
        try:exec(compile(SOURCE,'candidate','exec'),{})
        except Stop:pass
        return calls
    def test_logged_out_login_no_http(self):
        c=self.execute(logged=False,clicked=True);self.assertIn('login',c);self.assertNotIn('ui_context',c)
    def test_expired_logout_no_http(self):
        c=self.execute(clicked=True,context_valid=False,expired=True);self.assertIn('logout',c);self.assertNotIn('ui_context',c)
    def test_active_config_error_no_logout(self):
        self.assertNotIn('logout',self.execute(clicked=True,context_valid=False))
    def test_halt_preserved(self):
        self.assertNotIn('native_context',self.execute(clicked=True,halted=True))
    def test_timeout_no_retry(self):
        c=self.execute(clicked=True,timeout=True);self.assertEqual(c.count('ui_context'),1);self.assertNotIn('success',c)
    def test_no_request_on_page_load(self):self.assertNotIn('ui_context',self.execute())
    def test_native_rejection_before_transmission(self):self.assertNotIn('ui_context',self.execute(clicked=True,context_valid=False))
    def test_single_authorized_context(self):self.assertEqual(self.execute(clicked=True).count('ui_context'),1)
    def test_acl_failure_not_success(self):self.assertNotIn('success',self.execute(clicked=True,valid=False))
    def test_no_business_or_boundary_import(self):
        imports=[n.module for n in ast.walk(ast.parse(SOURCE)) if isinstance(n,ast.ImportFrom)]
        self.assertEqual(imports,['uat_auth_connect'])
        self.assertNotIn('save_crf',SOURCE);self.assertNotIn('checkpoint',SOURCE)
if __name__=='__main__':unittest.main()
