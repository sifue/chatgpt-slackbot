# ChatGPT Slackbot

Slackを通じて会話人工知能のChatGPTを利用するためのBOTスクリプト。  
会話の履歴数はトークン数に応じて最大まで保持。ユーザーごと、チャンネルごとに異なる履歴を保持する。
環境構築にはOpenAIのAPIトークンとSlackのBoltのアプリケーショントークン3種が必要。  
ユーザーを過去の発言から分析したり、Web検索の結果やワークスペースの結果を加味して質問に答えることもできる。  
基本的には、 `gpt-3.5-turbo-16k` のモデルを利用している。 `!gpt` コマンドは、内部的にFunction Callingを使っており「Web検索をして～して」または「Slack検索をして～して」と伝えることで検索結果を考慮した受け答えができる。 

## ボットの使い方
- AI(ChatGPT)との会話: !gpt \[会話内容\]  
- AI(ChatGPT)との会話の履歴をリセット: !gpt-rs
- 指定したユーザーの直近のパブリックチャンネルで発言からユーザー分析を依頼: !gpt-ua \[@ユーザー名\]
- 指定したパブリックチャンネルで投稿内容からチャンネルの分析を依頼: !gpt-ca \[#パブリックチャンネル名\]
- Web検索(DuckDuckGo)の結果を踏まえて質問に答える: !gpt-w \[質問\]
- パブリックチャンネルの検索結果を踏まえて質問に答える: !gpt-q \[質問\]
- AI(GPT-4)との会話: !gpt-4 \[会話内容\]
- AI(GPT-4)との会話の履歴をリセット: !gpt-4-rs
- AI(GPT-4V)との添付画像を含めた会話(画像は履歴に引き継ぎません): !gpt-4v \[会話内容+画像添付\]
- AI(GPT-4V)との会話の履歴をリセット: !gpt-4v-rs
- 使い方を表示: !gpt-help

セッションの概念はないが、API側には不正行為検出のためにSlack上のユーザーIDを渡している。

## 環境構築
### OpenAIのAPI Token(SECRET KEY)とOrganazation IDを取得。
[OpenAI API Keys](https://beta.openai.com/account/api-keys)にアクセスしてアカウント作成の後、SECRET KEYとOrganization IDを取得。

### Slack Botのトークンの用意
[Bolt 入門ガイド](https://slack.dev/bolt-python/ja-jp/tutorial/getting-started)に準拠。

- SLACK_BOT_TOKEN
- SLACK_APP_TOKEN
- SLACK_USER_TOKEN

を取得しておく。

#### SLACK_BOT_TOKENで要求するスコープ

##### Bot Token Scopes
- chat:write
- files:write (今後のDALL-Eとの統合のため)
- files:read (GPT-4Vのため)

##### User Token Scopes
- search:read

##### Event SubscriptionsのSubscribe to Bot Events で要求するスコープ

- message.channels
- message.groups
- message.im
- message.mpim

#### manifestファイルでの設定

[config/manifest.yml](config/manifest.yml)をSlack Botの設定画面で読み込むことで、上記のスコープを簡単に設定できます。

### インストール方法
Python3.9.6以上で動作を確認済み。

`opt/.env` ファイルをフォルダ内に作成して、自分のクレデンシャル情報を記述

```
ORGANAZTION_ID=org-xxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxxx
SLACK_USER_TOKEN=xoxp-xxxxxxxxxxxxxxxxx
SLACK_APP_TOKEN=xapp-1-xxxxxxxxxxxxxxxxx
NAME_SUFFIX=-main
USE_ONLY_PUBLIC_CHANNEL=False
USE_GPT_4_COMMAND=False
USE_GPT_4V_COMMAND=False
DAILY_USER_LIMIT=
```

NAME_SUFFIXは複数、Dockerコンテナを起動する際にコンテナ名がかぶらないようにするためのサフィックス。USE_ONLY_PUBLIC_CHANNELはパブリックチャンネルのみに利用を制限するか。USE_GPT_4_COMMANDはGPT-4で会話するコマンドを利用するか。USE_GPT_4V_COMMANDはGPT-4Vで会話するコマンドを利用するか。DAILY_USER_LIMITは、1日にユーザーが利用できる上限回数を設定できる機能。整数値で設定する。空の場合は制限なし。

あとは以下を実行してイメージをビルド&実行。

```
docker compose --env-file ./opt/.env up -d --build
```

以上で起動。

```
docker compose --env-file ./opt/.env down
```

で停止。

```
docker compose logs
```
でログ確認。

## 利用ログ
`opt/slackbot.db` のsqlite3ファイルに利用ログが記録される。

```
CREATE TABLE IF NOT EXISTS usage_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date text,
    user_id text,
    command_type text,
    created_at text
)
CREATE INDEX IF NOT EXISTS idx_date_user ON usage_logs (date, user_id)
```

コピーを取得して、sqlite3コマンドでsqlを発行して利用ログを確認できる。ワンライナーであれば以下のように直近のログを表示することができる。  

```
sqlite3 slackbot.db "select * from usage_logs order by created_at desc limit 100;"
```

### SQlite3のDBへの接続および表の整形の仕方

sqlite3コマンドで接続して以下のようにすることで表の整形ができる

```
sqlite3 slackbot.db
sqlite> .headers on
sqlite> .mode column
sqlite> select * from  usage_logs order by created_at desc limit 100;
```

```
id          date        user_id      command_type  created_at
----------  ----------  -----------  ------------  -------------------
94          2023-06-28  UXXXXXXXXXX  gpt           2023-06-28 11:19:56
93          2023-06-28  UXXXXXXXXXX  gpt-ca        2023-06-28 11:18:13
92          2023-06-28  UXXXXXXXXXX  gpt-ua        2023-06-28 11:10:36
91          2023-06-28  UXXXXXXXXXX  gpt-ua        2023-06-28 11:08:49
90          2023-06-28  UXXXXXXXXXX  gpt-ua        2023-06-28 11:04:36
89          2023-06-28  UXXXXXXXXXX  gpt-ua        2023-06-28 11:03:34
88          2023-06-28  UXXXXXXXXXX  gpt-ca        2023-06-28 11:00:51
87          2023-06-28  UXXXXXXXXXX  gpt           2023-06-28 10:54:41
```

### 日付ごとの利用回数取得SQL
```
SELECT date, COUNT(*) as count FROM usage_logs GROUP BY date ORDER BY date DESC;
```

### 日付ごとのコマンドごとの利用回数取得SQL
```
SELECT date, command_type, COUNT(*) as count FROM usage_logs GROUP BY date, command_type ORDER BY date DESC;
```

### ユーザーごとのコマンドごとの利用回数取得SQL
```
SELECT user_id, COUNT(*) as count FROM usage_logs GROUP BY user_id ORDER BY count DESC;
```

## LICENSE
The MIT License
