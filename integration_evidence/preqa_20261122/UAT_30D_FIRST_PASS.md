# 承認後に実行する30日CRF初回UAT

**準備資料。未実行。正式PASS 0／BLOCKED 74。** 開始前QAの署名だけでは各実機試験のPASSにならない。本手順・コミットをqaRefへ入れない。

## 0. 対象の固定と再利用する証拠

- 開発ブランチ：review/pr15-authenticated-crf-integration-20261116。本コミットのコードSHAをQA記録へ追記して差分レビューする。PR #15のHEADは別ブランチ `review/crf30-90-followup-unified-save-20261115` / `73a4556...` であり、配備元にしない。
- 既存アプリ：https://juog-utuc01-fixture-uat-20261109.streamlit.app/ 。11月22日のGitHub読取で現在のソースブランチ `uat-fixture-isolated-20261109` は `a2bcc6f7ff513ab30b9c8455f1b4893b465ea5ca` のまま。これはホストが稼働するSHAの実測ではない。前回実画面はAUTH_CONNECT、業務保存禁止。旧URL/旧generationを新構成へコピーしない。
- 既存候補GAS：`1_oVuL1i6Kmyu5egp-iDHIku-nN5JxoQ1ySPSluAsNc2gCFXGvBSJGDAR`。前回実画面では未デプロイ、既存コードは統合候補ではない。
- 唯一の書込対象Sheet：`1XaLdVGN39skmXVhiyPN-uOb9B8zjo3rmbNgYZCndJRs`、19タブ。TEST01・本人1名、期限2026-11-28 23:59 JST、JUOG-901 ownerは配置・読戻し済み（880c895の証拠）。期限後は自動延長しない。
- 旧writer停止と13タブのバックアップ照合は `../live_20261120/APPROVED_EXECUTION.md` を再利用。旧fixtureのみのアーカイブ証拠であり、他プロジェクト・他アカウントのwriter不在証明ではない。AUTH04の旧Sheet/project、Stage1、固定S2-01は触らない。
- 原本と8つの未確定臨床条件は `CLINICAL_DECISIONS.md`。判断を代行せず、承認された範囲を記録する。

## 1. QA後の配備チェック（今回実行禁止）

1. 中本先生の実レビュー記録を対象SHA・環境・許可範囲・日時と照合。既存のPI承認を再要求せず、実施直前の適用範囲を照合する。臨床決裁が不足する条件をPASSにしない。
2. 旧fixtureの停止状態に変更がないこと、当該Sheetへ到達する他のデプロイ/トリガー/直接writerがないことを権限者の一覧と照合。既存バックアップを再作成して済んだ扱いにせず、19タブと今回のACL/owner、未確定操作、既存B2 headがある場合はその現在状態を整合したチェックポイントとして保全する。秘密は私的保管先だけ。
3. `python tools/prepare_isolated_uat.py /absolute/unused/local-directory` で9本のGASソースとSHA256 manifestを作る。リポジトリ全体をclasp pushしない（本番用補助gsが混在）。既存候補のコードとmanifestを比較し、対象9本だけ反映。新しいGASプロジェクトやアプリは作らない。manifestの追加OAuth権限を推測しない。
4. 候補のSPREADSHEET_IDを上記Sheetへ固定。JUOG_PR15_CONFIGはisolated_crf_endpoint.gsの必須値を照合する：stage=PR15_ISOLATED_CRFS、scriptId/spreadsheetId一致、notificationsDisabled=true、sessionPolicy=isolated_gas_session_b2、sessionStoreApproved=true、bridgeIssuer=JUOG_PR15_FIXTURE、audience=JUOG_PR15_GAS、oidcIssuer=https://accounts.google.com。qaRef/piRef/singleWriterRef/backupRef/b2PolicyRefは実際の根拠への参照。署名鍵は安全な私的管理で新規生成し、GitHubや画面証拠へ記載しない。
5. 新generationを使用し、旧 `d72bcf33-423d-4c4d-862d-2e2d69bc3edf` は拒否。B2イベント表が空で既存headもない初回のみ、genesis=SHA256(UTF-8の `JUOG-B2|<Sheet ID>|<新generation>`)、property名 `JUOG_B2_HEAD_<Sheet ID>`、値 `0:<genesis>` を設定する。既存イベント/headがあればゼロへ戻さず復旧手順へ。
6. 配備版番号・時刻・実行主体・URL・9本のhashを記録。旧writerは停止維持。既存Streamlitをレビュー済みSHAへ切替、既存OIDCを保持。プロファイルとSecretsのurl/generation/script_id/spreadsheet_idを一致させる。registry.expected_spreadsheet_idも同じ。本人pinは検証済み値のみ。B2の60分上限、署名15秒、nonce/jti検査を維持。Google auth_time保証を実装したと誤記しない。
7. 未認証/誤署名の拒否、正規本人のui_context/backend_infoでScript/Sheet/generation/stage/role=facility/TEST01を実測。未確認なら保存に進まない。秘密・Cookie・署名assertionを記録に含めない。

## 2. JUOG-901：入力 → 自動仮保存 → 再開（30d-D）

1. 試験開始時にRegistry/owner/ACLを読み取り、JUOG-901が一意で本人所有、30dの現在Versionが0、正式CRF/監査/operationに不明な既存要求がないことを確認。すでに保存がある場合は初回扱いで再送せず復旧照合する。
2. 本人OIDCログインし、編集対象JUOG-901を確認して編集開始。30日画面を選択。既存 `clinical_contract/operated_fixture.json` を架空入力の基準にする（同意2026-01-01、手術2026-01-10、30日評価/採血2026-02-09、手術120分、出血0等）。画面にない派生値/旧分岐値は入力しない。`offline-v1` はローカルテスト専用文字列であり実機UUIDとして入力・再利用しない。実画面が作る新規UUIDを証拠に採取する。
3. 基本/手術入院/病理/30日評価の4セクションで入力を確定（テキストはEnterまたは欄外クリック）。約2秒の待機後、該当セクションだけの薄い保存中表示→「保存しました」を動画または連続画面で記録。未確定のキー入力だけで保存されたと扱わない。
4. R1_DraftEventsの該当key/actor/section/revision/operation_id/record_version=0とdataを読戻す。event_jsonのSHA256がdigestと一致し、イベント内dataのソートキーcanonical SHA256が内部digestと一致することを別途照合。0/false/null/空文字を比較し、変更しないセクションに追加revisionがないことを確認。
5. 「保存しました」の後にタブを閉じ、新しいブラウザセッションで再ログイン・症例確認・再開する。サーバ読取応答と4セクションの値が一致することを照合。最後の未確定入力・保存応答不明は「復元済み」としない。

## 3. 正式Version 1（30d-V1）

1. 可視必須項目・日付・臨床警告を確認。初回報告の送信操作を1回行い、UUID、record_key=`JUOG-901|perioperative_30d|30d`、payload digest、expected_version=0、操作時刻を記録する。承認された診断方法で原応答のJSON本文を採取し、token/署名/個人IDは除去した別コピーだけGitHubへ載せる。
2. 応答のok=true、audit_verified=true、UUID/key/visit/type/Sheet/Script/generation、record_version=1、existing=falseを画面と照合。これだけでPASSにしない。
3. 読取りを分離してCRF_30dの保存行とCRFSubmissionAuditを取得。UUIDは各1行、key・case・facility・Version・sheet_nameが一致。payload_jsonは凍結送信内容と一致し、旧行の削除・Registryの重複採番がないことを確認する。
4. R1_Operationsに同じUUIDのINTENTとCOMMITが各1件、actor/key/digest/expected=0が一致し、INTENT payloadとCRF payload、COMMIT receiptと応答が一致。各event_jsonとdigestを照合する。B2認証イベントの追記はCRF保存監査とは分けて記録する。
5. recovery_statusを再取得してSAVED/Version1/UUID/監査一致を確認。旧下書きはversion=0の履歴として保持し、get_sectionsは正式Version1用の新しい下書き世代を返す。通知はdisabled、外部送信0。
6. 中本先生が画面・応答・Sheet行・監査・operationの証拠一式を独立判定してから、該当行だけ正式UAT PASSへ変更する。不足ならBLOCKED、実測不一致ならFAIL。74行をまとめてPASSにしない。

## 4. 続く試験の順序

- 30d-V2：保存済み画面の「この保存を照合して訂正入力を開始」。最新UUID/Version/監査・本人権限を再確認し、訂正理由＋1項目変更。新UUIDでVersion2、Version1不変、audit/INTENT/COMMIT各対応。別タブが先に訂正した場合は開始拒否またはVERSION_CONFLICT。
- 90d、6/9/12/15/18/21/24m：30日参照元UUID・Versionを記録してから各画面のD/V1/V2/R/N/Lを実施。暦月の未決方針を勝手にPASSにしない。
- 通信障害：まず読取失敗と保存応答消失、同一操作ID/UUIDの手動再試行、新しい署名jti、Version非増加を確認。意図的な監査破損/途中失敗の注入は保存先と復旧計画を限定し、既存実データへ注入しない。
- セッション失効/別本人/別施設/所有権変更：新規保存を拒否し、旧要求・入力を別人へ引き継がない。旧署名/jtiの再利用は拒否。
- メール成功/失敗試験は初回PASSの条件から分離。現コードは外部送信停止でありMAIL-02/03は未実装・未実測のまま。実在する限定宛先・送信権限と通知機能の別変更が必要。

## 5. 障害時の保全と復旧

新規writer停止→障害時のCRF/監査/operation/draft/session/headを保全→成功応答済みUUID一覧を照合→INTENTの正規payloadで同一UUID再試行可能か判定。判断不能なら新規送信停止・事務局照合。部分的にCRF行だけ戻したり、旧writerを並行再有効化しない。復元は承認された一貫したスナップショット＋その後の成功済み記録を保持し、hash/連番/Version/auditを再照合。古いsessionを復活させず再認証する。RTO実測・全体復元リハーサルは未完了でありBACKUP-01をPASSにしない。

## 6. 証拠ファイル

`live/<実施日時JST>/<UAT-ID>/` に①environment.json（配備版/hash/Script/Sheet/時刻）、②screen-before/after、③request-redacted.json（UUID/key/digest、署名なし）、④response-redacted.json、⑤sheet-rows.json、⑥audit-and-operations.json、⑦comparison.json（フィールド別一致/不一致）、⑧qa-decision.md（本人の実判定・根拠）を保存。原応答/元ログは既存の私的証拠保管先、公開コピーは完全架空データかつ秘密除去後のみ。証拠欠落は成功にしない。
