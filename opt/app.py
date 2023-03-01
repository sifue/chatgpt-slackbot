from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from dotenv import load_dotenv
load_dotenv()

import os
import openai

openai.organization = os.getenv("ORGANAZTION_ID")
openai.api_key = os.getenv("OPENAI_API_KEY")

import os
import re
import time

# ボットトークンとソケットモードハンドラーを使ってアプリを初期化
app = App(token=os.getenv('SLACK_BOT_TOKEN'))

usingUser = None
historyDict = {} # key: historyIdetifier value: historyArray ex. [{"role": "user", "content": prompt}]
maxHistoryCount = 10 #会話履歴を参照する履歴の数の設定

def getHistoryIdentifier(team, channel, user):
    """
    会話履歴を取得するためのIDを生成する
    """
    return f"slack-{team}-{channel}-{user}"

def getUserIdentifier(team, user):
    """
    ユーザーを特定するためのIDを生成する
    """
    return f"slack-{team}-{user}"

@app.message(re.compile(r"^!gpt ((.|\s)*)$"))
def message_gpt(client, message, say, context):
    try:
        global usingUser
        if usingUser is not None:
            say(f"<@{usingUser}> さんの返答に対応中なのでお待ちください。")
        else:
            usingUser = message['user']
            usingTeam = message['team']
            usingChannel = message['channel']
            historyIdetifier = getHistoryIdentifier(usingTeam, usingChannel, usingUser)
            userIdentifier = getUserIdentifier(usingTeam, usingUser)

            prompt = context['matches'][0]
            say(f"<@{usingUser}> さんの以下の発言に対応中\n```\n{prompt}\n```")
            
            # ヒストリーを取得
            history = []
            if historyIdetifier in historyDict.keys():
                history = historyDict[historyIdetifier]
            history.append({"role": "user", "content": prompt})

            # ChatCompletionを呼び出す
            print(f"prompt: `{prompt}`")
            response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=history,
            top_p=1,
            n=1,
            max_tokens=1024,
            temperature=1, # 生成する応答の多様性
            presence_penalty=0,
            frequency_penalty=0,
            logit_bias={},
            user=userIdentifier
            )
            print(response)

            # ヒストリーを新たに追加、最大を超えたら古いものを削除
            newResponseMessage = response['choices'][0]['message']
            history.append(newResponseMessage)
            if len(history) > maxHistoryCount:
                history = history[1:]
            historyDict[historyIdetifier] = history

            say(newResponseMessage['content'])

            usingUser = None
    except Exception as e:
        usingUser = None
        print(e)
        say(f"エラーが発生しました。やり方を変えて試してみてください。 Error: {e}")

@app.message(re.compile(r"^!gpt-rs$"))
def message_help(client, message, say, context):
    try:
        global usingUser
        if usingUser is not None:
            say(f"<@{usingUser}> さんの返答に対応中なのでお待ちください。")
        else:
            usingUser = message['user']
            usingTeam = message['team']
            usingChannel = message['channel']
            historyIdetifier = getHistoryIdentifier(usingTeam, usingChannel, usingUser)

            # セッションのリセットをする
            historyDict[historyIdetifier] = []

            print(f"<@{usingUser}> さんの <#{usingChannel}> での会話の履歴をリセットしました。")
 
            say(f"<@{usingUser}> さんの <#{usingChannel}> での会話の履歴をリセットしました。")
            usingUser = None
    except Exception as e:
        usingUser = None
        print(e)
        say(f"エラーが発生しました。やり方を変えて試してみてください。 Error: {e}")

@app.message(re.compile(r"^!gpt-help$"))
def message_help(client, message, say, context):
    say("`!gpt [ボットに伝えたいメッセージ]` の形式でGPT-3のAIと会話できます。\n"  + 
    "`!gpt-rs` 利用しているチャンネルにおける会話の履歴ををリセットします。\n")

@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)

# アプリを起動
if __name__ == "__main__":
    SocketModeHandler(app, os.getenv('SLACK_APP_TOKEN')).start()
