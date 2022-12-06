from revChatGPT.revChatGPT import Chatbot
import os
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
load_dotenv()

config = {
    "email": os.getenv('EMAIL'),
    "password": os.getenv('PASSWORD')
}

global chatbot
chatbot = Chatbot(config, conversation_id=None)
chatbot.refresh_session()

# ボットトークンとソケットモードハンドラーを使ってアプリを初期化します
app = App(token=os.getenv('SLACK_BOT_TOKEN'))

usingUser = None

@app.message(re.compile(r"^!gpt (.*)$"))
def message_img(client, message, say, context):
    global usingUser
    try:
        if usingUser is not None:
            say(f"<@{usingUser}> さんの返答に対応中なのでお待ちください。")
        else:
            usingUser = message['user']
            prompt = context['matches'][0]
            response = chatbot.get_chat_response(prompt)
            print(f"prompt: `{prompt}`")
            message = response['message']
            print(f"response: `{response}`")
            say(message)
            usingUser = None
    except Exception as e:
        usingUser = None
        print(e)
        say(f"エラーが発生しました。やり方を変えて試してみてください。 Error: {e}")


@app.message(re.compile(r"^!gpt-help$"))
def message_help(client, message, say, context):
    say("`!gpt [ボットに伝えたいメッセージ]` の形式でChatGPTのAIと会話できます")

@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)

# アプリを起動します
if __name__ == "__main__":
    SocketModeHandler(app, os.getenv('SLACK_APP_TOKEN')).start()
