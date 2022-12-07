# ChatGPT Slackbot
Slackを通じて会話人工知能のChatGPTを利用するためのBOT
環境構築にはOpenAIのアカウント及びSlackのBoltのアプリケーショントークンが必要
ライブラリには[acheong08/ChatGPT](https://github.com/acheong08/ChatGPT)を利用

## ボットの使い方
- AIとの会話: !gpt \[会話内容\]
- AIとの会話のセッションをリセット: !gpt-rs
- 使い方を表示: !gpt-help

## 環境構築
### OpenAIのアカウントの用意 (ID/PASSWOARD形式)
[OpenAI Chat](https://chat.openai.com/)にアクセスしてID/PASSWOARD形式でアカウント作成。

### Slack Botのトークンの用意
[Bolt 入門ガイド](https://slack.dev/bolt-python/ja-jp/tutorial/getting-started)に準拠。

- SLACK_BOT_TOKEN
- SLACK_APP_TOKEN

を取得しておく。

#### SLACK_BOT_TOKENで要求するスコープ

- chat:write 

#### Event SubscriptionsのSubscribe to Bot Events で要求するスコープ

- message.channels
- message.groups
- message.im
- message.mpim

### インストール方法
Python3.9.6以上で動作を確認済み。

.env ファイルを実行フォルダ内に作成して、自分のクレデンシャル情報を記述

```
EMAIL=xxx@example.com
PASSWORD=password99999
SLACK_BOT_TOKEN=xoxb-9999999
SLACK_APP_TOKEN=xapp-9999999-9999999
```


```sh
pip3 install python-dotenv --upgrade
pip3 install revChatGPT --upgrade
pip3 install slack_bolt --upgrade
pip3 list # python-dotenv と revChatGPT と slack-bolt と slack-sdkを確認
python3 app.py
```

以上で起動。tmuxなどのセッションを維持するツールで起動することを前提としている。

なお、revChatGPT はアップデートがよくあるため、

```sh
pip3 install revChatGPT --upgrade
```

は時折実行して再起動する必要がある。操作確認バージョンは、revChatGPT v0.0.29
