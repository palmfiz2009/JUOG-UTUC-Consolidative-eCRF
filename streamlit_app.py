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
    if hashlib.sha256(Path(__file__).with_name('uat_b971_prepare_recovery.py').read_bytes()).hexdigest() != 'f021782ad80bc7382876e872647ec3ec80148537d83ea9634085b44590468d05':
        st.error("B971実行ソースが一致しません。送信していません。")
        st.stop()
    import uat_b971_prepare_recovery
    importlib.reload(uat_b971_prepare_recovery).run()
from uat_auth_connect import run
run()
st.stop()
