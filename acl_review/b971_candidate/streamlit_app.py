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
    if hashlib.sha256(Path(__file__).with_name('uat_b971_live.py').read_bytes()).hexdigest() != '669719d5a63f8c0dda4dc5bb3b5a64297442e07c35db509283d2e3a5bfa8898f':
        st.error("B971実行ソースが一致しません。送信していません。")
        st.stop()
    import uat_b971_live
    importlib.reload(uat_b971_live).run()
from uat_auth_connect import run
run()
st.stop()
