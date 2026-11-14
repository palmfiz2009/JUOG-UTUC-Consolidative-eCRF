# PI限定反映・読取承認案（未承認・未反映）

## 対象と成果
既存復旧GAS候補の業務書込拒否をコードと固定設定で検証済み。独立レビュー後の読取専用フロント候補を追加。実機実行前の個別承認を求める。実機読取完了、最新版v2確認、正式PASSを主張しない。

- Script ID: 11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy
- 既存deployment: AKfycbzLj9Dr-vUM6sTZHFOsxo0dUrscxNCp6LA196n2IBtYF3vYJ3ttnWLW3dY2eWJ7Gpf3GQ
- Sheets: 1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU
- 隔離Streamlit既存branch uat-fixture-isolated-20261109（基準b33e545）。main等変更なし。
- 対象者は既存検証済み本人ACL1名、TEST01/facilityのみ。識別子・ACL・鍵を変更しない。
- 対象データはJUOG-971|perioperative_30d|30dのみ。

## 固定ソース
Version9基準SHA256: 6d75109c4fffda3ebe4aedb0d7990f1d694ef3a331dcdb2123c10399279970d6
復旧GAS候補SHA256: ea70e3970a10a405cebdcf6f049ce2f426a91337dadc8846b5a9886b0a382383
読取probe SHA256: 9139b8890b2b6d597583a18daa685baad440903fbac4f7b8fc43b92bba29dc61
読取専用入口SHA256: 4b305743db8024f2ac33b706b0b4d50a30ac8b7fafdb4ef647a0185b66f538da
GAS差分は既存recovery.patch。既存署名/ACL/session/journal関数を再利用。新クラウド・新権限・新鍵・公開範囲拡大なし。編集者用fixture/旧実行helperは起動禁止。

## 承認を求める操作
1. 現行Version9ソース/接続/設定を再読込照合し、設定バックアップ・165行baselineを保全。相違なら中止。
2. 隔離GAS既存deploymentだけを候補版へ更新。反映時点はAUTH_CONNECT。
3. 隔離フロントのstreamlit_app.pyをreadonly_streamlit_entry.py候補へ置換、readonly_probe.pyを追加（他ソース不変）。
4. 最大30分の限定読取に限りAUTH04_APPROVEDへ切替。これは段階名であり業務保存承認ではない。サーバーcanonicalRecoveryReadApproved=true、canonicalRecoveryWriteApproved=false、canonicalRecoveryWriteReviewRefは未設定。reviewRef/approvalRefはこの実承認を参照し、過去の保存承認を流用しない。
5. b971ExecutionUntil=min(記録した開始時刻+1800000ms, 2026-11-19 23:59 JST)。開始・期限は反映直前に固定・証拠化、反映後読戻し必須。GASは設定期限を検査するが30分上限自体は設定手順で担保。
6. Python canonical_recovery_readに同じ開始/期限（秒）、対象scope、candidate_sha256、approved=true、write_approved=false、実review_refを設定。実設定内容を読戻し照合。秘密値を表示しない。
7. 正規OIDCの署名付きlist_requests/read_crf/request_statusだけを実行。ui_contextとsession_revokeは既存認証管理の範囲。正規CRFフォームと保存ボタンは読取専用入口で表示しない。

## 禁止APIと設定保証
prepare_request/execute_request/save_crf/save_draft/get_draft/登録/MDT/VOID/出力を不許可。書込flag=false時には有効payloadと既存operation_idでも拒否し、D3_Journal不変を確認した。要求側approval注入、readflag解除による旧広範囲への復帰も拒否。実設定でwriteflagがtrueまたは確認不能なら開始不可。
署名・ACL・失効・リプレイ検査は維持。認証利用記録V3_SessionEventsとhead更新は発生するが業務台帳/業務監査を更新しない。

## 読取の合格条件
本人所有の971/30d要求のみ一覧。operation_id/submission_id/期待版/内容hash/statusを照合。read_crfの内部ok、record_key、payloadの症例/施設/CRF/visit、連続版を検証。監査鎖は既存domain検証を通過すること。表示証拠はIDのhashと固定metadataのみ、原payloadを出力しない。
probeは手動の内容/提出ID/監査最終照合が必要と明示する。結果のlatest_version=2だけで保存承認・自動訂正しない。未知/不整合はhalt、再送なし。
実行前後D3_Journal165行の6列正規化hash 1414934e5e059e3cc7882486fa7cf5ee14afe99b4ab5dce9736a3c665d0b0797を再照合。現行の変更があれば承認条件不一致として停止。

## 復帰・停止
完了・期限・scope不一致・不正応答・監査不一致・書込設定不一致で直ちにAUTH_CONNECT、auth04ScopeReviewed=false、auth04ExecutionApprovalRef=null、b971ExecutionUntil=0、recovery read/write flags=falseへ戻し読戻し。必要時既存deploymentをVersion9へ戻す。フロントはb33e545へ戻すか読取設定を無効化。期限後session_revokeがAUTH04外側guardに拒否される場合はAUTH_CONNECT復帰後に実施。原履歴を削除/上書きしない。

## 実保存は別承認
今回の承認に保存・訂正・初期化を含めない。読取合格後、971最新版を再取得しv2に限りv3候補を固定。初回保存には別の正式登録済み未使用架空症例の確認が必要。

## 進捗分類
- 技術的検証完了（限定範囲）：正規30日フォーム3条件の入力0/0・署名生成、停止から正規ログアウト/再認証の復帰、候補の署名付き読取/書込拒否のオフライン統合。これはUAT項目全体の完了数ではない。
- 正式評価待ち：既存POST-01/POST-04/FUP-02優先候補は原基準との全条件照合後に判断。今回の追加証拠だけで全項目の技術完了へ昇格しない。QA依頼は保留。
- 技術的未完了：復旧経路の実機読取、最新版/ID/内容/監査照合、実保存・訂正、AUTH-04ログ/旧履歴/バックアップの残条件、60分境界等。
正式UAT PASS32/FAIL1/BLOCKED29/NOT RUN5、変更なし。
