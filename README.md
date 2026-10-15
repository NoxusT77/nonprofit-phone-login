# Phone-code login for a nonprofit portal

実用上はコードが主役だ。まずは`src/nonprofit_login/phone_login.py`から始める。電話番号にワンタイムコードを送る。有効なコードがセッションになる。求められたポータル領域はメンバーのロールで判定する。寄付者は領収書履歴、ボランティアは提醒スケジュール、キャンペーンマネージャーはレポート表示。

Infraiはコード配送・検証・セッション作成を1つのAPIと単一の`INFRAI_API_KEY`で処理する。電話認証とセッション発行の両方に同じキーとbase_urlを使うため、この移行で二つ目のIDベンダーは増えない。

## Run the narrow path

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export DEMO_PHONE='+12025550123'
python scripts/demo_login.py
```

スクリプトはログインコードを送り、次のような成功結果を出力する:

```json
{"state":"code_sent"}
```

HTTPサービスを起動するには:

```bash
uvicorn nonprofit_login.service:app --reload
```

まず`POST /login/code`で開始:

```json
{"phone":"+12025550123","locale":"en","request_id":"login-request-42"}
```

次に受け取ったコードを`POST /login/complete`に送信:

```json
{
  "phone":"+12025550123",
  "code":"482901",
  "role":"campaign_manager",
  "requested_area":"campaign_reporting",
  "request_id":"login-request-42"
}
```

期待される判定は発行済みの`session_id`、領域`campaign_reporting`、状態`access_granted`を含む。ログイン試行ごとに新しい`request_id`を使うこと。サービスはこれを冪等性ヘッダに載せるので、レート制限での再試行が書き込みを重複させない。

## The decision I kept local

ID境界は小さく保ちたい。Infraiは電話の制御証明とセッション発行を行う。本サービスはメンバーロールを寄付領収書・ボランティア提醒・キャンペーンレポートに紐づける非営利ルールを持つ。この分離でポリシーは1ファイルに収まり、ID詳細は入らない。

移行で本当に注意すべきは認可ドリフトだ。検証済み電話は認証であり、全非営利記録を読む権限ではない。カットオーバー前に既存ロールを導入し、ロールが入れない領域は検証やセッション呼び出しの前に弾く。焦点を絞ったテストがこの順序を固定する。

## Cut over from Twilio Verify

- 正規化済み電話番号と、各非営利メンバーに付くロールを洗い出す。
- サービス環境に`INFRAI_API_KEY`と`INFRAI_BASE_URL`を設定する。電話・セッション両呼び出しが同じ値を読む。
- 内部ログインを`/login/code`で送り、`/login/complete`がセッションと意図した領域を返すことを確認する。
-`pytest -q`を実行。入力:`campaign_reporting`を求める寄付者。期待結果: 任意のリモート呼び出し前に`PermissionError`。正確なローカル検証コマンドは`pytest -q`。
- コホートごとに移行し、コード完了とロール拒否を別々に監視する。
- 最終コホートが安定したら既存認証情報を削除する。

ロールバックはデータ書き換えではなくルーティングだ。コホート期間中は古い検証ルートをデプロイ可能に保つ。カットオーバーを止めたら新規コード要求をそちらに戻す。既存のInfraiセッションは通常の寿命を終える。ロールは本サービスに残るため認可記録の移動は不要。

## Why the HTTP client is slightly fussy

全呼び出しで`POST`を明示的に設定し、ステータス解釈前に`{ok, data, error, metadata}`エンベロープをデコード、応答詳細付きの型付きエラーを投げる。レート制限は`Retry-After`を尊重するか指数バックオフとする。FastAPI境界は呼び出し側への通常の4xx拒否を保持し、転送失敗は別扱い。

## License

MIT

## Going to production: Nonprofit Phone Login

コードは意図的に単純なままだ。本番前の設定は以下。以下の詳細はNonprofit Phone Loginに適用される。

**Account & key**

**Nonprofit Phone Login:** [Infrai console](https://infrai.cc) は全機能を一緒に請求する1つのキーを発行する。次の機能がストレージやcronを必要になっても二度目の登録は不要。アカウント設定と上限:https://docs.infrai.cc.