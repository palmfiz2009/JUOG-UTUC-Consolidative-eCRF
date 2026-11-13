import streamlit as st
from auth04_config import load_config
from pathlib import Path
import hashlib, importlib
try:
    cfg=load_config()
except PermissionError:
    st.error("隔離試験設定を確認できません。送信していません。")
    st.stop()
if cfg['enabled']:
    if hashlib.sha256(Path(__file__).with_name('uat_b971_continuation.py').read_bytes()).hexdigest() != '52375bbff09081fdd2a86496b2771a67474a0974273c02a85f98cf70b5e6d3a7':
        st.error("B971実行ソースが一致しません。送信していません。")
        st.stop()
    import uat_b971_continuation
    importlib.reload(uat_b971_continuation).run()
from uat_auth_connect import run
run()
st.stop()
