from user_analysis import sayUserAnalysis
from question import sayAnswer
from util import getHistoryIdentifier, getUserIdentifier
import re
import openai
import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from dotenv import load_dotenv
load_dotenv()


openai.organization = os.getenv("ORGANAZTION_ID")
openai.api_key = os.getenv("OPENAI_API_KEY")

# ボットトークンとソケットモードハンドラーを使ってアプリを初期化
app = App(token=os.getenv("SLACK_BOT_TOKEN"))

usingUser = None
# key: historyIdetifier value: historyArray ex. [{"role": "user", "content": prompt}]
historyDict = {}
maxHistoryCount = 10  # 会話履歴を参照する履歴の数の設定


@app.message(re.compile(r"^!gpt ((.|\s)*)$"))
def message_gpt(client, message, say, context):
    try:
        global usingUser
        if usingUser is not None:
            say(f"<@{usingUser}> さんの返答に対応中なのでお待ちください。")
        else:
            usingUser = message["user"]
            usingTeam = message["team"]
            usingChannel = message["channel"]
            historyIdetifier = getHistoryIdentifier(
                usingTeam, usingChannel, usingUser)
            userIdentifier = getUserIdentifier(usingTeam, usingUser)

            prompt = context["matches"][0]
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
                temperature=1,  # 生成する応答の多様性
                presence_penalty=0,
                frequency_penalty=0,
                logit_bias={},
                user=userIdentifier
            )
            print(response)

            # ヒストリーを新たに追加、最大を超えたら古いものを削除
            newResponseMessage = response["choices"][0]["message"]
            history.append(newResponseMessage)
            if len(history) > maxHistoryCount:
                history = history[1:]
            historyDict[historyIdetifier] = history

            say(newResponseMessage["content"])

            usingUser = None
    except Exception as e:
        usingUser = None
        print(e)
        say(f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")

        # エラーを発生させた人の会話の履歴をリセットをする
        historyIdetifier = getHistoryIdentifier(
            message["team"], message["channel"], message["user"])
        historyDict[historyIdetifier] = []


@app.message(re.compile(r"^!gpt-rs$"))
def message_reset(client, message, say, context):
    try:
        global usingUser
        if usingUser is not None:
            say(f"<@{usingUser}> さんの返答に対応中なのでお待ちください。")
        else:
            usingUser = message["user"]
            usingTeam = message["team"]
            usingChannel = message["channel"]
            historyIdetifier = getHistoryIdentifier(
                usingTeam, usingChannel, usingUser)

            # エラー時には会話の履歴をリセットをする
            historyDict[historyIdetifier] = []

            print(f"<@{usingUser}> さんの <#{usingChannel}> での会話の履歴をリセットしました。")
            say(f"<@{usingUser}> さんの <#{usingChannel}> での会話の履歴をリセットしました。")
            usingUser = None
    except Exception as e:
        usingUser = None
        print(e)
        say(f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")


@app.message(re.compile(r"^!gpt-ua (\<\@[^ ]*\>).*$"))
def message_user_analysis(client, message, say, context):
    try:
        global usingUser
        if usingUser is not None:
            say(f"<@{usingUser}> さんの返答に対応中なのでお待ちください。")
        else:
            usingUser = message["user"]
            sayUserAnalysis(client,message, say, usingUser, context["matches"][0])
            usingUser = None
    except Exception as e:
        usingUser = None
        print(e)
        say(f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")

@app.message(re.compile(r"^!gpt-q ((.|\s)*)$"))
def message_question(client, message, say, context):
    try:
        global usingUser
        if usingUser is not None:
            say(f"<@{usingUser}> さんの返答に対応中なのでお待ちください。")
        else:
            usingUser = message["user"]
            sayAnswer(client, message, say, usingUser, context["matches"][0])
            usingUser = None
    except Exception as e:
        usingUser = None
        print(e)
        say(f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")

@app.message(re.compile(r"^!gpt-help$"))
def message_help(client, message, say, context):
    say(f"`!gpt [ボットに伝えたいメッセージ]` の形式でChatGPTのAIと会話できます。会話の履歴を{maxHistoryCount}個前まで参照します。\n" +
        "`!gpt-rs` 利用しているチャンネルにおける会話の履歴をリセットします。\n" +
        "`!gpt-ua [@ユーザー名]` 直近のパブリックチャンネルでの発言より、どのようなユーザーであるのかを分析します。\n" + 
        "`!gpt-q [質問]` パブリックチャンネルの検索結果を踏まえて質問に答えます。\n")

@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)


# アプリを起動
if __name__ == "__main__":
    SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN")).start()
