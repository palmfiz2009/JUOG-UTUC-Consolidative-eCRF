"""Fixed connection-stop messages. Never render exception text or secret values."""

PERMISSION_MESSAGES = {
    'INTEGRATION_NOT_APPROVED': '接続設定が無効、または承認参照が不足しています。',
    'LOGIN_REQUIRED': 'Googleでログインしてください。',
    'RELOGIN_REQUIRED': '本人認証の有効期限が切れています。ログアウト後に再ログインしてください。',
    'IDENTITY_MISMATCH': 'Google本人認証の発行元・対象アプリの確認に失敗しました。',
    'NONCE_UNAVAILABLE': 'Google本人認証に必要なnonceを確認できません。',
    'PRINCIPAL_NOT_APPROVED': 'ログイン本人が承認済みの隔離UAT担当者と一致しません。',
    'CONFIG_BINDING_MISMATCH': 'Streamlitと承認済み接続設定のURL・世代・Script ID・Sheet IDが一致しません。',
}
KEY_MESSAGES = {
    'auth': 'Google認証設定がありません。',
    'google': 'Google認証設定がありません。',
    'client_id': 'Google認証のclient_id設定がありません。',
    'isolated_crf': 'Secretsに[isolated_crf]設定がありません。',
    'registry': 'Secretsに[registry]設定がありません。',
    'expected_spreadsheet_id': 'registry.expected_spreadsheet_id設定がありません。',
    'signing_key': 'isolated_crf.signing_key設定がありません。',
}


def connection_stop_message(error):
    # Do not call str/repr(error): third-party exceptions may contain secrets.
    code = error.args[0] if len(error.args) == 1 and type(error.args[0]) is str else None
    if type(error) is PermissionError and code in PERMISSION_MESSAGES:
        detail = PERMISSION_MESSAGES[code]
    elif type(error) is KeyError and code in KEY_MESSAGES:
        detail = KEY_MESSAGES[code]
    else:
        detail = '接続設定または本人認証の確認に失敗しました。管理者による確認が必要です。'
    return detail + ' 接続・保存は停止しています。'
