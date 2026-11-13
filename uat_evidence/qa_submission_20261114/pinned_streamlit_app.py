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
    if hashlib.sha256(Path(__file__).with_name('uat_b971_cache_reconciliation.py').read_bytes()).hexdigest() != '325c8a6ee1bdd50e1e53a6dfe69e5a0b83cd555e22a414276e8e428a5ab59b87':
        st.error("B971実行ソースが一致しません。送信していません。")
        st.stop()
    import uat_b971_cache_reconciliation
    importlib.reload(uat_b971_cache_reconciliation).run()
from uat_auth_connect import run
run()
st.stop()
