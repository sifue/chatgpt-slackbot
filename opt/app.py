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

# ボットトークンとソケットモードハンドラーを使ってアプリを初期化します
app = App(token=os.getenv('SLACK_BOT_TOKEN'))

usingUser = None
userNameSuffix = str(time.time())

@app.message(re.compile(r"^!gpt (.*)$"))
def message_img(client, message, say, context):
    try:
        global usingUser
        if usingUser is not None:
            say(f"<@{usingUser}> さんの返答に対応中なのでお待ちください。")
        else:
            usingUser = message['user']
            prompt = context['matches'][0]
            say(f"<@{usingUser}> さんの発言 `{prompt}` に対応します。")
            print(f"prompt: `{prompt}`")

            response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            top_p=1,
            n=1,
            max_tokens=1024,
            temperature=0.5, # 生成する応答の多様性
            user=f"slack-user-{usingUser}-{userNameSuffix}"
            )

            print(response)
            message = response['choices'][0]['text']
            say(message)

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

            global userNameSuffix
            userNameSuffix = str(time.time())
            print(f"<@{usingUser}> さんが会話のセッションをリセットしました。")
 
            say(f"会話のセッションをリセットしました。")
            usingUser = None
    except Exception as e:
        usingUser = None
        print(e)
        say(f"エラーが発生しました。やり方を変えて試してみてください。 Error: {e}")

@app.message(re.compile(r"^!gpt-help$"))
def message_help(client, message, say, context):
    say("`!gpt [ボットに伝えたいメッセージ]` の形式でGPT-3のAIと会話できます。" +
    "厳密にはChatGPTではなくGPT-3のモデルと会話します。\n" + 
    "!gpt-rs` 会話のセッションをリセットします。\n")

@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)

# アプリを起動します
if __name__ == "__main__":
    SocketModeHandler(app, os.getenv('SLACK_APP_TOKEN')).start()
