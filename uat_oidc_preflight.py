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
        claims = config.get("authorize_params", {}).get("claims", {})
        if isinstance(claims, str):
            claims = json.loads(claims)
        return isinstance(claims, dict) and "auth_time" in claims.get("id_token", {})
    except Exception:
        return False


def runtime_parameter_check():
    """Inspect parameter presence only; never output credentials or claim values."""
    try:
        from importlib.metadata import version
        from streamlit.web.server.starlette.starlette_auth_routes import _create_oauth_client
        client, _ = _create_oauth_client("google")
        params = client.authorize_params or {}
        raw = params.get("claims")
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        forwarded = isinstance(parsed, dict) and parsed.get("id_token", {}).get("auth_time", {}).get("essential") is True
        import asyncio
        from urllib.parse import urlparse, parse_qs
        async def serialize_only():
            # Build a URL locally using the configured client. No HTTP request,
            # token exchange, persistent state or business operation is performed.
            async with client._get_oauth_client() as session:
                session.redirect_uri = REDIRECT
                return client._create_oauth2_authorization_url(
                    session, "https://accounts.google.com/o/oauth2/v2/auth",
                    **params)
        generated = asyncio.run(serialize_only())
        query = parse_qs(urlparse(generated["url"]).query)
        actual_claims = json.loads(query.get("claims", ["{}"])[0])
        serialized = actual_claims.get("id_token", {}).get("auth_time", {}).get("essential") is True
        status = " / AUTH_TIME_URL_" + ("READY（送信前の生成検査）" if serialized else "MISSING")
        return status + " / Streamlit " + version("streamlit") + " / Authlib " + version("authlib") + " / AUTH_TIME_PARAMETER_" + ("READY" if forwarded else "MISSING")
    except Exception:
        return "AUTH_TIME_PARAMETER_CHECK_UNAVAILABLE（秘密値・例外内容は非表示）"


def run():
    st.set_page_config(page_title="JUOG UAT — Google認証確認", layout="centered")
    st.title("JUOG UAT：Google認証確認")
    st.info("隔離環境・認証確認のみ。CRF保存、GAS送信、メール送信は停止しています。")
    st.caption("Build: oidc-acl-proposal-20261113-01")
    try:
        root_config = st.secrets["auth"]
        named_google = "google" in root_config
        config = dict(root_config["google"]) if named_google else dict(root_config)
        config["redirect_uri"] = root_config.get("redirect_uri")
        config["cookie_secret"] = root_config.get("cookie_secret")
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
    st.caption("選択中の認証プロバイダー：" + ("google" if named_google else "default（auth.googleがありません）"))
    st.caption(runtime_parameter_check())
    if not st.user.is_logged_in:
        st.write("Googleで本人認証してください。認証だけでは施設・ロール権限は付与されません。")
        if st.button("Googleでログイン", type="primary"):
            try:
                st.login("google" if named_google else None)
            except Exception:
                st.error("認証を開始できませんでした。設定・依存ライブラリを確認してください。")
        st.stop()
    cookie_provider = st.user.get("provider")
    provider_label = cookie_provider if cookie_provider in ("google", "default") else "不明"
    st.caption("現在のログイン結果のプロバイダー：" + provider_label)
    if cookie_provider == "default" and named_google:
        st.warning("旧default設定のログイン結果が残っています。新しいgoogle設定のログイン結果はまだ未確認です。")
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
    st.subheader("本人ACL登録前の照合（読取専用）")
    st.caption("案Bは最大60分のアプリセッションです。Googleでの直近1時間以内の再認証を保証しません。")
    from uat_identity_proposal import identity_proposal
    try:
        proposal = identity_proposal(st.user, config["client_id"], int(time.time()))
    except PermissionError as error:
        messages = {
            "LOGIN_REQUIRED": "Googleログインが必要です。",
            "IDENTITY_MISMATCH": "本人識別子または既存OAuthクライアントとの一致を確認できません。",
            "RELOGIN_REQUIRED": "既存認証結果の期限が切れています。ログアウト後、Googleで再ログインしてください。",
            "NONCE_UNAVAILABLE": "B2に必要なnonceを取得できません。接続を有効化せず実装を確認してください。",
        }
        st.warning(messages.get(str(error), "本人照合を完了できません。"))
    else:
        st.success("正規ログイン結果と既存OAuthクライアントの一致、およびB2用属性を確認しました。")
        st.write("本人照合番号（issuer＋subjectのSHA-256）：")
        st.code(proposal["principal_fingerprint"], language=None)
        st.table([
            {"登録予定項目": "対象施設", "内容": "TEST01のみ"},
            {"登録予定項目": "ロール", "内容": "facility（全施設管理権限なし）"},
            {"登録予定項目": "期限", "内容": "2026年11月19日23:59 JST"},
            {"登録予定項目": "接続段階", "内容": "AUTH_CONNECTのみ・業務保存禁止"},
        ])
        st.info("これは登録予定の照合です。本人ACL登録・GAS送信・設定有効化は行っていません。PI承認前に権限は付与されません。")
    st.warning("施設・ロールACLは未接続です。業務操作は許可されていません。正式UATのPASS判定ではありません。")
    if not all(checks.values()):
        st.error("不足する属性・期限条件があります。認証・認可の完成とは判定しません。")
    if st.button("ログアウト"):
        st.logout()
    st.stop()
