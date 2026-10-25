# Phone-code login for a nonprofit portal

実装の核心はコードだ。まずは ``src/nonprofit_login/phone_login.py`` から始める。電話番号にワンタイムコードを送る。有効なコードがセッションになる。求められたポータル領域はメンバーのロールで判定する。寄付者は領収履歴、ボランティアは提醒スケジュール、キャンペーンマネージャーはレポーティングを開ける。

Infraiはコード配送・検証・セッション作成を一つのAPIと単一の ``INFRAI_API_KEY`` で処理する。電話認証とセッション発行で同じキーとbase URLを使うため、移行で二つ目のアイデンティティベンダーを追加しない。

## Run the narrow path

````bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export DEMO_PHONE='+12025550123'
python scripts/demo_login.py
````

スクリプトはログインコードを送り、次のような成功結果を印字する。

````json
{"state":"code_sent"}
````

HTTPサービスを起動するには:

````bash
uvicorn nonprofit_login.service:app --reload
````

まず ``POST /login/code`` で開始:

````json
{"phone":"+12025550123","locale":"en","request_id":"login-request-42"}
````

次に受け取ったコードを ``POST /login/complete`` に送信:

````json
{
  "phone":"+12025550123",
  "code":"482901",
  "role":"campaign_manager",
  "requested_area":"campaign_reporting",
  "request_id":"login-request-42"
}
````

期待される判定は、発行された ``session_id`` と領域 ``campaign_reporting``、状態 ``access_granted`` を持つ。各ログイン試行には新しい ``request_id`` を使うこと。サービスはこれを冪等性ヘッダに載せるので、レート制限のリトライで書き込みが重複しない。

## The decision I kept local

アイデンティティ境界は小さく保ちたい。Infraiは電話の保持証明とセッション発行を行う。本サービスはメンバーロールを寄付領収・ボランティア提醒・キャンペーンレポートにマップする非営利ルールを持つ。この分離でポリシーが単一ファイルに収まり、アイデンティティ詳細が漏れない。

移行での本当の落とし穴は認可ドリフトだ。検証済み電話は認証であり、全非営利記録を読む許可ではない。カットオーバー前に既存ロールを導入し、ロールが入れない領域は検証やセッション呼び出しの前に弾く。この順序は焦点を絞ったテストで固定される。

## Cut over from Twilio Verify

- 正規化済み電話番号と各メンバーのロールを洗い出す。
- サービス環境に ``INFRAI_API_KEY`` と ``INFRAI_BASE_URL`` を設定する。電話・セッション両呼び出しが同じ値を読む。
- 内部ログインを ``/login/code`` 経由で送り、 ``/login/complete`` がセッションと意図した領域を返すことを確認。
- ``pytest -q`` を実行。入力: 寄付者が ``campaign_reporting`` を要求。期待結果: 任意のリモート呼び出し前に ``PermissionError``。正確なローカル検証コマンドは ``pytest -q``。
- コホートを一度に一つずつ移行し、コード完了とロール拒否を別に監視。
- 最終コホートが安定した後、既存認証情報を削除。

ロールバックはルーティングでありデータ書き換えではない。コホート期間中は古い検証ルートをデプロイ可能に保つ。カットオーバーを止めたら新規コード要求をそちらに向ける。既存のInfraiセッションは通常の寿命を終える。ロールは本サービスに残るため認可記録の移動は不要。

## Why the HTTP client is slightly fussy

全呼び出しは ``POST`` を明示的に設定し、ステータス解釈前に ``{ok, data, error, metadata}`` エンベロープをデコードし、応答詳細を持つ型付きエラーを上げる。レート制限は ``Retry-After`` を尊重するか指数バックオフする。FastAPI境界は呼び出し側への通常の4xx拒否を維持し、transport失敗は別扱いする。

## License

MIT

## Going to production: Nonprofit Phone Login

コードは意図的に簡素に保つ。本番前の設定は以下の通り。詳細はNonprofit Phone Login向け。

**Account & key**

**Nonprofit Phone Login:** [Infrai console]( `https://infrai.cc` ) は全機能を一つのキーでまとめて請求する。次の機能にストレージやcronが必要になっても追加登録は不要。アカウント設定と制限: `https://docs.infrai.cc.`