# ChatGPT Slackbot

Slackを通じて会話人工知能のChatGPTを利用するためのBOTスクリプト。  
会話の履歴数はトークン数に応じて最大まで保持。ユーザーごと、チャンネルごとに異なる履歴を保持する。
環境構築にはOpenAIのAPIトークンとSlackのBoltのアプリケーショントークン3種が必要。  
ユーザーを過去の発言から分析したり、Web検索の結果やワークスペースの結果を加味して質問に答えることもできる。  
基本的には、 `gpt-3.5-turbo-16k` のモデルを利用している。  

## ボットの使い方
- AI(ChatGPT)との会話: !gpt \[会話内容\]
- AI(ChatGPT)との会話の履歴をリセット: !gpt-rs
- 指定したユーザーの直近のパブリックチャンネルで発言からユーザー分析を依頼: !gpt-ua \[@ユーザー名\]
- 指定したパブリックチャンネルで投稿内容からチャンネルの分析を依頼: !gpt-ca \[#パブリックチャンネル名\]
- Web検索(DuckDuckGo)の結果を踏まえて質問に答える: !gpt-w \[質問\]
- パブリックチャンネルの検索結果を踏まえて質問に答える: !gpt-q \[質問\]
- AI(GPT-4)との会話: !gpt-4 \[会話内容\]
- AI(GPT-4)との会話の履歴をリセット: !gpt-4-rs
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

##### User Token Scopes
- search:read

#### Event SubscriptionsのSubscribe to Bot Events で要求するスコープ

- message.channels
- message.groups
- message.im
- message.mpim

### インストール方法
Python3.9.6以上で動作を確認済み。

`opt/.env` ファイルをフォルダ内に作成して、自分のクレデンシャル情報を記述

```
ORGANAZTION_ID=org-xxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxxx
SLACK_USER_TOKEN=xoxb-xxxxxxxxxxxxxxxxx
SLACK_APP_TOKEN=xapp-1-xxxxxxxxxxxxxxxxx
NAME_SUFFIX=-main
USE_ONLY_PUBLIC_CHANNEL=False
USE_GPT_4_COMMAND=False
```

NAME_SUFFIXは複数、Dockerコンテナを起動する際にコンテナ名がかぶらないようにするためのサフィックス。USE_ONLY_PUBLIC_CHANNELはパブリックチャンネルのみに利用を制限するか。USE_GPT_4_COMMANDはGPT-4で会話するコマンドを利用するか。

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

## LICNESE
The MIT License
