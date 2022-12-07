# ChatGPT Slackbot
Slackを通じて会話人工知能のChatGPTを利用するためのBOT
環境構築にはOpenAIのアカウント及びSlackのBoltのアプリケーショントークンが必要
ライブラリには[acheong08/ChatGPT](https://github.com/acheong08/ChatGPT)を利用

## ボットの使い方
- AIとの会話: !gpt \[会話内容\]
- AIとの会話のセッションをリセット: !gpt-rs
- 使い方を表示: !gpt-help

長く会話を行わせていると、長い会話セッションの影響からエラーを出し始めるので、その際は会話のセッションをリセットするようにしてください。

## 環境構築
### OpenAIのアカウントの用意 (ID/PASSWOARD形式)
[OpenAI Chat](https://chat.openai.com/)にアクセスしてID/PASSWOARD形式でアカウント作成。

ライブラリ、ChatGPTはスクレイピングを行なっています。なお[OpenAIの利用規約](https://openai.com/terms/)によると明確にスクレイピングは禁止されていませんが、

原文:
> OpenAI reserves the right to investigate and take appropriate legal action against anyone who, in OpenAI’s sole discretion, violates this provision, including without limitation, removing the offending content from the Site, suspending or terminating the account of such violators and reporting you to the law enforcement authorities. You agree to not use the Site to:  
> (中略)  
> (vii) in the sole judgment of OpenAI, is objectionable or which restricts or inhibits any other person from using or enjoying the Site, or which may expose OpenAI or its users to any harm or liability of any type;  

DeepL翻訳:
> OpenAI は、OpenAI の単独の裁量により、本規定に違反する者を調査し、適切な法的措置を取る権利を有します。これには、本サイトからの違反コンテンツの削除、当該違反者のアカウントの停止または終了、法執行当局への報告などが含まれますが、これらに限定されるものではありません。お客様は、本サイトを以下の目的で使用しないことに同意するものとします。  
> (中略) 
> (vii) OpenAI の単独の判断で、好ましくない、他者による本サイトの利用や楽しみを制限または抑制する、あるいは OpenAI やそのユーザがいかなる種類の損害や責任にもさらされる可能性があると判断される場合。  

以上の行為に該当する可能性があり、アカウントの停止などをされる可能性がありますが、その点はMIT LICNESEの免責に則り自己責任でご利用ください。

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

## LICNESE
MIT
