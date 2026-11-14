# 設定先訂正・停止中の署名検証に関する独立技術レビュー

日付：2026-11-14。AIによる独立技術レビューであり、正式QA、管理者の鍵交換証明、認証再開承認の代替ではない。実環境操作・秘密値取得・設定変更は実施していない。

## 設定先訂正

フロントcommit `b33e54514dd81545f50dea362052607bdd045ab9`の`uat_auth_connect.py`を確認した。`context()`は`st.secrets['auth_connect']`を読み、その`signing_key`をメモリ上の`juog_identity_bridge`へ渡す。したがって管理画面の設定先は`[auth_connect].signing_key`である。

`local_admin_transfer.py`と同梱版は一致しており、`transfer_fields()`が既存bundle内部の`juog_identity_bridge.signing_key`を取得し、UIには`Streamlit / auth_connect.signing_key`と表示する訂正は適切。bundleの形式・暗号化・導出・既存ファイルを変更せず、既存bundleを再利用できる。README_JA.txtの設定先と「本訂正を理由に再生成・再交換しない」の記載も整合する。

`python -m unittest discover -s uat_evidence/key_incident_20261114 -p test_transfer_destination.py`は1件合格。4項目の対応、GAS署名鍵との一致、bundle不変を合成データで確認している。実Windows GUIや実保存の合格証拠ではない。

配布上の未解消事項：レビュー時点の`admin_local_package/SHA256.json`は旧版であり、変更済みhelperとREADMEの実SHAと一致しない。manifestの再生成、ZIPの再構築と内容照合を完了するまで更新済み配布物として扱わないこと。既存管理者の鍵再生成は不要。

## 停止gateと署名検証順序

Version 9候補の`juogUnifiedIsolationEntryV3_()`は、AUTH_CONNECTで`authConnectReviewApproved!==true`なら`AUTH_CONNECT_NOT_APPROVED`を返し、その後にある`juogV3DecodeBridge_()`へ到達しない。したがって停止中の通常endpoint応答は、新旧どちらの署名鍵が設定されているか、旧鍵署名が拒否されるかを証明しない。

decode内ではHMAC一致を先に検証し、その後claimと期限を検査する。`AUTH_EXPIRED`は期限による拒否であり、旧鍵の署名拒否ではない。任意の不正署名の`AUTH_INVALID`も、不正署名を拒否できる一般的な対照試験にとどまる。旧鍵に由来すると検証できない署名を送っても旧鍵無効化の実測にはならない。旧signerや真正な旧署名試験材料がない場合は「旧鍵拒否未実測」と記録し、別試験で置き換えない。

新しい正常通信の成功だけでも、両側が同じ鍵を使っている証拠にはなるが、それが交換後の新鍵であることを単独では証明しない。管理者の交換記録と対象設定の照合が別に必要。

## 安全に進められる作業と承認境界

- 設定先ラベル・README・manifest・ZIPを訂正し、互換性試験と配布物照合を行える。鍵再生成・鍵再取得は不要。
- 停止中の読取専用診断、台帳不変性、ソース/デプロイ版の照合は継続できる。
- head修復の承認と認証再開の承認は分離する。修復しても停止フラグを自動でtrueへ変更しない。
- 通常endpointで新鍵の認証通信を実測するには、停止解除を含む隔離AUTH_CONNECTの限定認証試験について、対象・期限・停止条件を確定した承認が必要。業務API・限定業務読取・保存は含めない。
- 停止gateを回避する診断入口を無断で追加しない。別の署名検証専用入口が必要なら別途安全性レビューと限定承認の対象。
- 真正な旧署名材料を用意できなければ、旧鍵拒否の直接証拠不足は残る。未実測を合格扱いせず、残存リスクの正式判断が必要。

秘密鍵の読み出し・旧鍵復活・署名検証の迂回は提案しない。正式UATの判定変更を認めるレビューではない。

## 再レビュー：配布物の不整合解消

2026-11-14、更新された`admin_local_package/SHA256.json`と`JUOG_admin_local_rotation_corrected.zip`を独立に再読取照合した。manifestの4ファイルすべてについて、作業ディレクトリの実SHA・ZIP内の実SHA・manifest値が一致。ZIP内manifestも作業ディレクトリと一致し、未記載の余分なファイルは0件だった。

修正版ZIP SHA-256：`765ebcc303b6402a6dcfe021576286d6983b6f906ca472cb224d0e8e5da5b478`

前述の配布物ハッシュ不整合は解消。旧ZIPは証拠として別途保全し、修正版で上書きしていない。本訂正に伴う既存暗号化bundleの再生成・鍵交換・設定操作は不要。実Windows GUIおよび認証再開試験を実施済みとするものではない。
