"""Isolation-only OIDC preflight. Never calls business APIs or displays claims."""
import time
import json
import streamlit as st

REDIRECT = "https://juog-utuc01-fixture-uat-20261109.streamlit.app/oauth2callback"
METADATA = "https://accounts.google.com/.well-known/openid-configuration"

def claim_checks(user, client_id, now):
    aud = user.get("aud")
    audiences = aud if isinstance(aud, list) else [aud]
    azp = user.get("azp")
    def timestamp(key):
        value = user.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) else None
    exp, iat, auth_time = timestamp("exp"), timestamp("iat"), timestamp("auth_time")
    return {
        "issuer": user.get("iss") in ("https://accounts.google.com", "accounts.google.com"),
        "subject": isinstance(user.get("sub"), str) and bool(user.get("sub").strip()),
        "audience": bool(client_id) and client_id in audiences,
        "authorized_party": (azp is None or azp == client_id) and (len(audiences) <= 1 or azp == client_id),
        "expiry": exp is not None and exp > now,
        "issued_at": iat is not None and 0 <= iat <= now + 60 and exp is not None and iat < exp,
        "recent_authentication": auth_time is not None and 0 <= now - auth_time <= 3600,
    }

def authentication_time_status(user, now):
    if "auth_time" not in user:
        return "AUTH_TIME_MISSING：認証属性に未返却"
    value = user.get("auth_time")
    if not isinstance(value, int) or isinstance(value, bool):
        return "AUTH_TIME_TYPE_INVALID：整数形式ではない"
    if value > now:
        return "AUTH_TIME_FUTURE：現在より未来"
    if now - value > 3600:
        return "AUTH_TIME_STALE：本人認証から1時間超過"
    return "AUTH_TIME_OK：1時間以内"

def auth_time_request_configured(config):
    try:
        claims = config.get("client_kwargs", {}).get("claims", {})
        if isinstance(claims, str):
            claims = json.loads(claims)
        return isinstance(claims, dict) and "auth_time" in claims.get("id_token", {})
    except Exception:
        return False


def run():
    st.set_page_config(page_title="JUOG UAT — Google認証確認", layout="centered")
    st.title("JUOG UAT：Google認証確認")
    st.info("隔離環境・認証確認のみ。CRF保存、GAS送信、メール送信は停止しています。")
    st.caption("Build: oidc-preflight-20261111-02")
    try:
        config = st.secrets["auth"]
        ready = (
            config.get("redirect_uri") == REDIRECT
            and config.get("server_metadata_url") == METADATA
            and all(isinstance(config.get(k), str) and config[k].strip()
                    for k in ("client_id", "client_secret", "cookie_secret"))
            and len(config["cookie_secret"]) >= 32
        )
    except Exception:
        ready = False
    if not ready:
        st.error("認証設定が未完了、または隔離URLと一致していません。秘密値は共有せず管理者が確認してください。")
        st.stop()
    st.caption("auth_time要求設定：" + ("あり（送信・返却は未証明）" if auth_time_request_configured(config) else "なし・設定形式を確認"))
    if not st.user.is_logged_in:
        st.write("Googleで本人認証してください。認証だけでは施設・ロール権限は付与されません。")
        if st.button("Googleでログイン", type="primary"):
            try:
                st.login()
            except Exception:
                st.error("認証を開始できませんでした。設定・依存ライブラリを確認してください。")
        st.stop()
    checks = claim_checks(st.user, config["client_id"], int(time.time()))
    st.write("Googleログインから復帰しました。以下は属性の照合結果です。")
    labels = {
        "issuer": "発行者", "subject": "個人識別子の存在",
        "audience": "クライアントIDとの一致", "authorized_party": "認証先の整合性",
        "expiry": "有効期限", "issued_at": "発行日時",
        "recent_authentication": "本人認証時刻（1時間以内）",
    }
    st.table([{"確認項目": labels[k], "結果": "確認済み" if v else "未確認・不一致"} for k, v in checks.items()])
    st.write(authentication_time_status(st.user, int(time.time())))
    st.caption("個人識別子・トークン・認証時刻の実値は表示しません。")
    st.warning("施設・ロールACLは未接続です。業務操作は許可されていません。正式UATのPASS判定ではありません。")
    if not all(checks.values()):
        st.error("不足する属性・期限条件があります。認証・認可の完成とは判定しません。")
    if st.button("ログアウト"):
        st.logout()
    st.stop()
