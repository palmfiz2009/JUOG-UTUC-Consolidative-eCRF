JUOG 隔離環境・管理者本人による鍵交換
PIによる管理者ローカル表示／貼付の限定例外を受領（2026-11-14）。
この許可はAIによる操作代行、業務送信、限定読取再開を含まない。

1. クラウドブラウザではなく、先生ご自身のPCだけで作業してください。
画面共有・録画・スクリーンショットを止め、Windows設定→システム→クリップボードの「履歴」「デバイス間同期」をオフにします。
機密画面のスクリーンショットやキーをChatGPTへ送らないでください。
同期フォルダ（Dropbox/OneDrive/Git）以外にZIPを展開します。

2. 自分のローカルブラウザで対象を照合します。
GAS Script ID:
11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy
https://script.google.com/home/projects/11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy/settings
Streamlit: 既存の隔離アプリ。GitHub branch uat-fixture-isolated-20261109に接続していることを確認。
本番・既存TEST・mainなら中止。新アプリ作成や新GASデプロイは不要です。

3. 最初に通信を停止します。
GASのUNIFIED_ISOLATION_CONFIGだけを編集し、authConnectReviewApprovedをfalseにして保存します。
sessionExecutionStageはAUTH_CONNECTのまま。auth04ScopeReviewed=false、auth04ExecutionApprovalRef=null、b971ExecutionUntil=0を維持。
セッション世代・head・ACL・台帳は変更しません。
保存後、当該フラグがfalseであることを本人が確認してください。
これを確認できなければ鍵変更へ進まないでください。

4. START_WINDOWS.cmdを起動します。
Python 3が必要です。未導入の場合はpython.orgの公式版を使用してください。
起動時にローカル仮想環境とcryptography依存パッケージを準備します（インターネット接続が必要）。
初回は20文字以上の新しい暗号化用パスフレーズを2回入力します。入力は画面に表示されません。
これはGoogleのパスワードではありません。AIに送らず、ご自身の安全な保管領域で保管してください。
暗号化ファイルjuog-isolated-rotation.enc.jsonができます。平文キーはファイル保存されません。
すでに暗号化ファイルがあれば再生成せず、同じファイルを使います。

5. 転送画面で確認事項にYesを選び、同じ暗号化ファイルを選択し、パスフレーズで開きます。
ボタンは鍵名だけを表示します。クリックした値はローカルclipboardに45秒間入ります。
GASの次の3欄に対応するボタンから、新しい値だけを貼り付けて保存します。
- ADMIN_BRIDGE_SIGNING_KEY
- ADMIN_RESUME_DERIVATION_KEY
- ADMIN_DRAFT_PEPPER
旧値はコピーしません。他のプロパティは変更しません。
provisionIsolatedAuth04KeysReviewは実行しないでください。

6. 隔離StreamlitのSettings→Secretsで、[auth_connect]内のsigning_keyの値だけを、対応ボタンから貼り付けます。
TOMLの引用符は保持し、値の文字列だけを置き換えます。他のOAuth設定・Cookie設定・世代等は変更しません。
Save後、対象の隔離アプリだけをRebootします。
GASとStreamlitには同じ署名鍵が入るよう、必ず同じ暗号化ファイルを使ってください。
片側で失敗したら停止状態のまま。同じ新鍵で整合させ、旧鍵には戻さないでください。

7. Clear clipboard and closeを押し、管理画面を閉じます。
アプリ側で新しい値を読めたか・旧鍵を拒否するかは、このツールでは確認していません。
GASのauthConnectReviewApproved=falseを維持し、まだtrueに戻さないでください。
旧鍵は互換用に残しません。旧鍵による署名拒否の実測は未完であり、期限切れ拒否で代用しません。
既存セッションは自動失効しません。世代や台帳の初期化はしないでください。

8. ChatGPTには、次の非秘密情報だけを報告してください。
「GAS3項目保存済み／Streamlit1項目保存・再起動済み／通信停止継続／完了時刻○時○分JST」
または「どの段階で停止したか」。キー、パスフレーズ、秘密画面の画像は送らないでください。
ここまでで交換完了の自己申告にはなりますが、認証回帰・旧鍵拒否・セッション失効の実測完了ではありません。
限定読取・業務保存は再開禁止です。

制約：この補助ツールの復号と対象チェックは架空データで確認済みです。
実Windows GUI、clipboard、管理画面への貼付は未検証です。異常時は続行しません。
clipboard履歴や外部ソフトによる取得を後から消す保証はできません。事前無効化が必要です。
Pythonのメモリ内文字列の完全消去は保証しません。作業終了後は補助ツールを閉じてください。

2026-11-14訂正：現行隔離フロントの設定先は[auth_connect].signing_keyです。
暗号化bundle内部の旧フィールド名は互換性のため保持します。既存bundleを使えます。
本訂正だけを理由に鍵を再生成・再交換しないでください。
