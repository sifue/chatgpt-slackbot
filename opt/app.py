from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from dotenv import load_dotenv
load_dotenv()

import os

import asyncio
from gpt3contextual import ContextualChat, ContextManager

contextManager = ContextManager()
contextualChat = ContextualChat(os.getenv("OPENAI_API_KEY"), context_manager=contextManager)

import os
import re
import time

# ボットトークンとソケットモードハンドラーを使ってアプリを初期化します
app = App(token=os.getenv('SLACK_BOT_TOKEN'))

usingUser = None

@app.message(re.compile(r"^!gpt ((.|\s)*)$"))
def message_gpt(client, message, say, context):
    try:
        global usingUser
        if usingUser is not None:
            say(f"<@{usingUser}> さんの返答に対応中なのでお待ちください。")
        else:
            usingUser = message['user']
            prompt = context['matches'][0]
            say(f"<@{usingUser}> さんの以下の発言に対応中\n```\n{prompt}\n```")
            print(f"prompt: `{prompt}`")
            asyncio.run(chat(usingUser, prompt, say))

    except Exception as e:
        usingUser = None
        print(e)
        say(f"エラーが発生しました。やり方を変えて試してみてください。 Error: {e}")

async def chat(user, prompt, say):
    """ContextualChatを非同期実行するための関数"""
    global contextualChat
    response, returnPrompt, completion = await contextualChat.chat(user, prompt)
    say(response)

    global usingUser
    usingUser = None

@app.message(re.compile(r"^!gpt-rs([ ]?)([^ ]*)([ ]?)([^ ]*)([ ]?)([^ ]*)$"))
def message_help(client, message, say, context):
    try:
        global usingUser
        if usingUser is not None:
            say(f"<@{usingUser}> さんの返答に対応中なのでお待ちください。")
        else:
            usingUser = message['user']

            username = context['matches'][1] if context['matches'][1] != "" else "Human"
            agentname = context['matches'][3] if context['matches'][3] != "" else "AI"
            chat_description = context['matches'][5] if context['matches'][5] != "" else "Normal Conversation"

            global contextManager
            contextManager = ContextManager(
                username=username,
                agentname=agentname,
                chat_description=chat_description)
            global contextualChat
            contextualChat = ContextualChat(os.getenv("OPENAI_API_KEY"), context_manager=contextManager)

            print(f"<@{usingUser}> さんが会話のセッションをリセットしました。 username: {username}, agentname: {agentname}, chat_description: {chat_description}")
 
            say(f"会話のセッションをリセットしました。 ユーザーが何か: {username},  AIが何か: {agentname}, シチュエーション: {chat_description}")
            usingUser = None
    except Exception as e:
        usingUser = None
        print(e)
        say(f"エラーが発生しました。やり方を変えて試してみてください。 Error: {e}")

@app.message(re.compile(r"^!gpt-help$"))
def message_help(client, message, say, context):
    say("`!gpt [ボットに伝えたいメッセージ]` の形式でGPT-3のAIと会話。\n"  + 
    "`!gpt-rs [ユーザーが何か] [AIが何か] [シチュエーション]` の形式でシチュエーションをリセット。\n")

@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)

# アプリを起動します
if __name__ == "__main__":
    SocketModeHandler(app, os.getenv('SLACK_APP_TOKEN')).start()
