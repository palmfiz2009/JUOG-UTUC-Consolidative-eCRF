# 設定経路の判定（2026-11-14）

## 結論
厳密な「管理者自身の画面にも表示せず、clipboardも使わない」という条件で、既存GASと既存Streamlit Community Cloudの両方へ安全に注入する経路は確立できなかった。実交換は未実施。非公開API、DOM隠蔽による安全性の偽装、鍵入りソース、AI経由の鍵転送は採用しない。

## 公式経路の確認
- GAS：PropertiesService.setPropertiesはスクリプト内部のAPI。Apps Script REST一覧にScript Properties直接更新APIは見つからない。scripts.runで内部関数を呼ぶにはAPI executableデプロイ、適切なOAuth、共通standard GCP projectが必要。現行は既存web deployment／default GCPの確認記録であり、未承認の新API部署やGCP切替を実施しない。
- Streamlit Community Cloud：公式管理経路は対象appのSettings→Secrets→Save。st.secretsは値の読取インターフェースであり、ローカルsecrets.tomlを書いても既存Cloud appの秘密値は更新されない。調査した公式文書に管理者向けの秘密値更新REST APIは確認できず、APIが存在しないとの絶対的断定はしない。
- 両者の公式設定画面は管理者本人に値を表示し得る。そのため、過去の「Secretsの値を表示・コピーしない」というPI制限のまま実行できるとは扱わない。

出典（公式文書）:
https://developers.google.com/apps-script/api/reference/rest
https://developers.google.com/apps-script/api/how-tos/execute
https://developers.google.com/apps-script/reference/properties
https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/app-settings
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management

## 最小のPI判断：管理者ローカル端末内に限る表示・貼付の例外
対象は下記4値のみ。AI接続のない管理者本人のブラウザで、公式画面だけを使用する。画面共有・録画・スクリーンショット・clipboard履歴／クラウド同期・拡張機能の記録を無効化した信頼できる端末を前提とする。旧値はコピーしない。新値をチャット／GitHub／ツールへ渡さない。管理者本人に値が表示され得ることを明示して承認を得る。これはまだ承認されたと扱わない。
1. 指定隔離GASのADMIN_BRIDGE_SIGNING_KEY
2. 同ADMIN_RESUME_DERIVATION_KEY
3. 同ADMIN_DRAFT_PEPPER
4. 指定隔離Streamlitのjuog_identity_bridge.signing_key
GASはScript ID 11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy。Streamlitは既存隔離repo branch uat-fixture-isolated-20261109に接続したappのみ。管理者は対象branchを自分で確認し、他appなら停止。

## 値をAIへ渡さないための用意
既存generate_encrypted_bundle.pyを再利用。local_admin_transfer.py候補は管理者ローカルで暗号化bundleを復号し、鍵名だけのボタンから対象値をローカルclipboardへ45秒間転送する。ネットワーク通信・自動設定・旧鍵取得・平文ファイル保存は行わない。管理画面側の表示を隠すものではない。clipboard履歴や同期を後から消す保証はないため、事前無効化を必須とする。
復号・宛先照合の新規部分だけを架空bundleで確認済み。実Windows GUI／clipboard／公式画面への貼付は未検証。実鍵生成・復号・設定は管理者本人のみ。従ってこの候補を「実機交換経路検証済み」とは呼ばない。

## 交換順序（例外承認後、管理者本人）
1. 現行ROTATION.mdの非秘密maintenance gateで通信停止を確認。AUTH_CONNECTを維持しauthConnectReviewApproved=false。業務許可は全て無効。旧鍵へ戻さない。
2. 直前にlive_exchange_precheckの台帳165行・下書き3件・code hash0・未完要求0を再確認。B2の360イベント鎖は整合したがScript Propertyのhead突合は秘密画面を開かずに行える手段が必要で、今回は未再確認。
3. 管理者端末で暗号化bundleを生成し、ローカル補助ツールで上記4欄だけを更新する。他のOIDC・Cookie・セッション世代・ACLを変更しない。保存／片側失敗時はgateを閉じたまま、旧鍵へ戻さない。GAS新規デプロイ不要。Streamlitを再起動して旧signerプロセスを停止する。
4. 旧鍵拒否の実測方法は別の未解決条件。再起動で旧signerが失われる前に、旧値を回収せず有効期限内署名を内部生成して比較する経路が必要。現状その管理経路は未検証。再起動後に古いtokenを送って期限切れにするだけでは合格にしない。鍵の実値を取り出して試験しない。
5. 既存sessionは自動失効しない。世代/head初期化を行わず、ROTATION.mdの停止継続／期限満了確認または承認済み失効処理を完了する。その後正規OIDC、新鍵ui_context、TEST01 facility、失効・replay・業務拒否・台帳不変を確認。限定読取はこれらがそろうまで再開しない。

実交換未完、旧鍵無効化未確認、新鍵実機通信未実施。正式UAT PASS32/FAIL1/BLOCKED29/NOT RUN5。
