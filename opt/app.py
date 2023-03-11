from user_analysis import sayUserAnalysis
from question import sayAnswer
from channel_analysis import sayChannelAnalysis
from util import getHistoryIdentifier, getUserIdentifier, getTokenSize
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

MAX_TOKEN_SIZE = 4000  # トークンの最大サイズ (実際には4097だが、ヒストリー結合のために少し小さくしておく)
COMPLETION_MAX_TOKEN_SIZE = 1000  # ChatCompletionの出力の最大トークンサイズ
INPUT_MAX_TOKEN_SIZE = MAX_TOKEN_SIZE - COMPLETION_MAX_TOKEN_SIZE  # ChatCompletionの入力に使うトークンサイズ

def countTokenSizeFromHistoryArray(historyArray):
    """
    会話の履歴の配列からトークンのサイズを計算する
    """
    sum = 0
    for history in historyArray:
        sum += getTokenSize(history['content'])
    return sum

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

            # ヒストリーを取得
            historyArray = []
            if historyIdetifier in historyDict.keys():
                historyArray = historyDict[historyIdetifier]
            historyArray.append({"role": "user", "content": prompt})

            print(historyArray)

            # トークンのサイズがINPUT_MAX_TOKEN_SIZEを超えたら古いものを削除
            while countTokenSizeFromHistoryArray(historyArray) > INPUT_MAX_TOKEN_SIZE:
                historyArray = historyArray[1:]

            print(historyArray)

            # 単一の発言でMAX_TOKEN_SIZEを超えたら、対応できない
            if(len(historyArray) == 0):
                messegeOutOfTokenSize = f"発言内容のトークン数が{INPUT_MAX_TOKEN_SIZE}を超えて、{getTokenSize(prompt)}であったため、対応できませんでした。"
                say(messegeOutOfTokenSize)
                print(messegeOutOfTokenSize)
                usingUser = None
                return
            
            say(f"<@{usingUser}> さんの以下の発言に対応中（履歴数: {len(historyArray)} 、トークン数: {countTokenSizeFromHistoryArray(historyArray)}）\n```\n{prompt}\n```")

            # ChatCompletionを呼び出す
            print(f"prompt: `{prompt}`")
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=historyArray,
                top_p=1,
                n=1,
                max_tokens=COMPLETION_MAX_TOKEN_SIZE,
                temperature=1,  # 生成する応答の多様性
                presence_penalty=0,
                frequency_penalty=0,
                logit_bias={},
                user=userIdentifier
            )
            print(response)

            # ヒストリーを新たに追加
            newResponseMessage = response["choices"][0]["message"]
            historyArray.append(newResponseMessage)

            # トークンのサイズがINPUT_MAX_TOKEN_SIZEを超えたら古いものを削除
            while countTokenSizeFromHistoryArray(historyArray) > INPUT_MAX_TOKEN_SIZE:
                historyArray = historyArray[1:]
            historyDict[historyIdetifier] = historyArray # ヒストリーを更新

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

            # 履歴をリセットをする
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

@app.message(re.compile(r"^!gpt-ca (\<\#[^ ]*\>).*$"))
def message_channel_analysis(client, message, say, context):
    try:
        global usingUser
        if usingUser is not None:
            say(f"<@{usingUser}> さんの返答に対応中なのでお待ちください。")
        else:
            usingUser = message["user"]
            sayChannelAnalysis(client,message, say, usingUser, context["matches"][0])
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
    say(f"`!gpt [ボットに伝えたいメッセージ]` の形式でChatGPTのAIと会話できます。会話の履歴は、{INPUT_MAX_TOKEN_SIZE}トークンまで保持します。\n" +
        "`!gpt-rs` 利用しているチャンネルにおけるユーザーの会話の履歴をリセットします。\n" +
        "`!gpt-ua [@ユーザー名]` 直近のパブリックチャンネルでの発言より、どのようなユーザーであるのかを分析します。\n" +
        "`!gpt-ca [#チャンネル名]` パブリックチャンネルの直近の投稿内容から、どのようなチャンネルであるのかを分析します。\n" +
        "`!gpt-q [質問]` パブリックチャンネルの検索結果を踏まえて質問に答えます。(注. 精度はあまり高くありません)\n")

@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)


# アプリを起動
if __name__ == "__main__":
    SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN")).start()
