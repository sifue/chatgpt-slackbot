import traceback
import logging
fmt = "%(asctime)s %(levelname)s %(name)s :%(message)s"
logging.basicConfig(level=logging.INFO, format=fmt)

from typing import List, Dict
from user_analysis import say_user_analysis
from question import say_answer
from channel_analysis import say_channel_analysis
from util import get_history_identifier, get_user_identifier, calculate_num_tokens, calculate_num_tokens_by_prompt, say_ts, check_availability
from gpt_4 import GPT_4_CommandExecutor
import re
import openai
import os
from distutils.util import strtobool
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from dotenv import load_dotenv
load_dotenv()

openai.organization = os.getenv("ORGANAZTION_ID")
openai.api_key = os.getenv("OPENAI_API_KEY")

# ボットトークンとソケットモードハンドラーを使ってアプリを初期化
app = App(token=os.getenv("SLACK_BOT_TOKEN"))

# 現在使用中のユーザーのセット、複数リクエストを受けると履歴が壊れることがあるので、一つのユーザーに対しては一つのリクエストしか受け付けないようにする
using_user_set = set()  
# key: historyIdetifier value: historyArray ex. [{"role": "user", "content": prompt}]
history_dict : Dict[str, List[Dict[str, str]]] = {}
gpt_4_command_executor = GPT_4_CommandExecutor(openai)

MAX_TOKEN_SIZE = 4096  # トークンの最大サイズ
COMPLETION_MAX_TOKEN_SIZE = 1024  # ChatCompletionの出力の最大トークンサイズ
INPUT_MAX_TOKEN_SIZE = MAX_TOKEN_SIZE - COMPLETION_MAX_TOKEN_SIZE  # ChatCompletionの入力に使うトークンサイズ

@app.message(re.compile(r"^!gpt ((.|\s)*)$"))
def message_gpt(client, message, say, context, logger):
    """会話を行う"""
    if not check_availability(message, logger):
        say_ts(client, message, f"<#{message['channel']}> はパブリックチャンネルではないため利用できません。")
        logger.info(f"user: {message['user']}, <#{message['channel']}> はパブリックチャンネルではないため利用できません。")
        return

    try:
        if message["user"] in using_user_set: # 既に自身が利用中の場合
            say_ts(client, message, f"<@{message['user']}> さんの返答に対応中なのでお待ちください。")
        else:
            using_user_set.add(message["user"])
            using_team = message["team"]
            using_channel = message["channel"]
            history_idetifier = get_history_identifier(
                using_team, using_channel, message["user"])
            user_identifier = get_user_identifier(using_team, message["user"])

            prompt = context["matches"][0]

            # ヒストリーを取得
            history_array: List[Dict[str, str]] = []
            if history_idetifier in history_dict.keys():
                history_array = history_dict[history_idetifier]
            history_array.append({"role": "user", "content": prompt})

            # トークンのサイズがINPUT_MAX_TOKEN_SIZEを超えたら古いものを削除
            while calculate_num_tokens(history_array) > INPUT_MAX_TOKEN_SIZE:
                history_array = history_array[1:]

            # 単一の発言でMAX_TOKEN_SIZEを超えたら、対応できない
            if(len(history_array) == 0):
                messege_out_of_token_size = f"発言内容のトークン数が{INPUT_MAX_TOKEN_SIZE}を超えて、{calculate_num_tokens_by_prompt(prompt)}であったため、対応できませんでした。"
                say_ts(client, message, messege_out_of_token_size)
                logger.info(messege_out_of_token_size)
                using_user_set.remove(message["user"]) # ユーザーを解放
                return
            
            say_ts(client, message, f"<@{message['user']}> さんの以下の発言に対応中（履歴数: {len(history_array)} 、トークン数: {calculate_num_tokens(history_array)}）\n```\n{prompt}\n```")

            # ChatCompletionを呼び出す
            logger.info(f"user: {message['user']}, prompt: {prompt}")
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=history_array,
                top_p=1,
                n=1,
                max_tokens=COMPLETION_MAX_TOKEN_SIZE,
                temperature=1,  # 生成する応答の多様性
                presence_penalty=0,
                frequency_penalty=0,
                logit_bias={},
                user=user_identifier
            )
            logger.debug(response)

            # ヒストリーを新たに追加
            new_response_message = response["choices"][0]["message"]
            history_array.append(new_response_message)

            # トークンのサイズがINPUT_MAX_TOKEN_SIZEを超えたら古いものを削除
            while calculate_num_tokens(history_array) > INPUT_MAX_TOKEN_SIZE:
                history_array = history_array[1:]
            history_dict[history_idetifier] = history_array # ヒストリーを更新

            say_ts(client, message, new_response_message["content"])
            logger.info(f"user: {message['user']}, content: {new_response_message['content']}")

            using_user_set.remove(message["user"]) # ユーザーを解放
    except Exception as e:
        using_user_set.remove(message["user"]) # ユーザーを解放
        logger.error(traceback.format_exc())
        say_ts(client, message, f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")

        # エラーを発生させた人の会話の履歴をリセットをする
        history_idetifier = get_history_identifier(
            message["team"], message["channel"], message["user"])
        history_dict[history_idetifier] = []


@app.message(re.compile(r"^!gpt-rs$"))
def message_reset(client, message, say, context, logger):
    """会話の履歴をリセットする"""
    if not check_availability(message, logger):
        say_ts(client, message, f"<#{message['channel']}> はパブリックチャンネルではないため利用できません。")
        logger.info(f"user: {message['user']}, <#{message['channel']}> はパブリックチャンネルではないため利用できません。")
        return

    try:
        if message["user"] in using_user_set: # 既に自身が利用中の場合
            say_ts(client, message, f"<@{message['user']}> さんの返答に対応中なのでお待ちください。")
        else:
            using_user_set.add(message["user"])
            using_team = message["team"]
            using_channel = message["channel"]
            historyIdetifier = get_history_identifier(
                using_team, using_channel, message["user"])

            # 履歴をリセットをする
            history_dict[historyIdetifier] = []

            logger.info(f"<@{message['user']}> さんの <#{using_channel}> での会話の履歴をリセットしました。")
            say_ts(client, message, f"<@{message['user']}> さんの <#{using_channel}> での会話の履歴をリセットしました。")
            using_user_set.remove(message["user"]) # ユーザーを解放
    except Exception as e:
        using_user_set.remove(message["user"]) # ユーザーを解放
        logger.error(traceback.format_exc())
        say_ts(client, message, f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")


@app.message(re.compile(r"^!gpt-ua (\<\@[^ ]*\>).*$"))
def message_user_analysis(client, message, say, context, logger):
    """ユーザーの分析を行う"""
    if not check_availability(message, logger):
        say_ts(client, message, f"<#{message['channel']}> はパブリックチャンネルではないため利用できません。")
        logger.info(f"user: {message['user']}, <#{message['channel']}> はパブリックチャンネルではないため利用できません。")
        return
    
    try:
        if message["user"] in using_user_set: # 既に自身が利用中の場合
            say_ts(client, message, f"<@{message['user']}> さんの返答に対応中なのでお待ちください。")
        else:
            using_user_set.add(message["user"])
            say_user_analysis(client,message, say, message["user"], context["matches"][0], logger)
            using_user_set.remove(message["user"]) # ユーザーを解放
    except Exception as e:
        using_user_set.remove(message["user"]) # ユーザーを解放
        logger.error(traceback.format_exc())
        say_ts(client, message, f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")

@app.message(re.compile(r"^!gpt-ca (\<\#[^ ]*\>).*$"))
def message_channel_analysis(client, message, say, context, logger):
    """チャンネルの分析を行う"""
    if not check_availability(message, logger):
        say_ts(client, message, f"<#{message['channel']}> はパブリックチャンネルではないため利用できません。")
        logger.info(f"user: {message['user']}, <#{message['channel']}> はパブリックチャンネルではないため利用できません。")
        return

    try:
        if message["user"] in using_user_set: # 既に自身が利用中の場合
            say_ts(client, message, f"<@{message['user']}> さんの返答に対応中なのでお待ちください。")
        else:
            using_user_set.add(message["user"])
            say_channel_analysis(client,message, say, message["user"], context["matches"][0], logger)
            using_user_set.remove(message["user"]) # ユーザーを解放
    except Exception as e:
        using_user_set.remove(message["user"]) # ユーザーを解放
        logger.error(traceback.format_exc())
        say_ts(client, message, f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")

@app.message(re.compile(r"^!gpt-q ((.|\s)*)$"))
def message_question(client, message, say, context, logger):
    """Slackの検索を踏まえて質問に回答する"""
    if not check_availability(message, logger):
        say_ts(client, message, f"<#{message['channel']}> はパブリックチャンネルではないため利用できません。")
        logger.info(f"user: {message['user']}, <#{message['channel']}> はパブリックチャンネルではないため利用できません。")
        return

    try:
        if message["user"] in using_user_set: # 既に自身が利用中の場合
            say_ts(client, message, f"<@{message['user']}> さんの返答に対応中なのでお待ちください。")
        else:
            using_user_set.add(message["user"])
            say_answer(client, message, say, message["user"], context["matches"][0], logger)
            using_user_set.remove(message["user"]) # ユーザーを解放
    except Exception as e:
        using_user_set.remove(message["user"]) # ユーザーを解放
        logger.error(traceback.format_exc())
        say_ts(client, message, f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")

@app.message(re.compile(r"^!gpt-4 ((.|\s)*)$"))
def message_gpt_4(client, message, say, context, logger):
    """GPT-4の会話をする"""
    if not strtobool(os.getenv("USE_GPT_4_COMMAND")):  # GPT-4コマンドを利用できない場合は終了
        return

    if not check_availability(message, logger):
        say_ts(client, message, f"<#{message['channel']}> はパブリックチャンネルではないため利用できません。")
        logger.info(f"user: {message['user']}, <#{message['channel']}> はパブリックチャンネルではないため利用できません。")
        return

    try:
        if message["user"] in using_user_set: # 既に自身が利用中の場合
            say_ts(client, message, f"<@{message['user']}> さんの返答に対応中なのでお待ちください。")
        else:
            using_user_set.add(message["user"])
            gpt_4_command_executor.execute(client, message, say, context, logger)
            using_user_set.remove(message["user"]) # ユーザーを解放
    except Exception as e:
        using_user_set.remove(message["user"]) # ユーザーを解放
        logger.error(traceback.format_exc())
        say_ts(client, message, f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")

        # エラーを発生させた人の会話の履歴をリセットをする
        gpt_4_command_executor.execute_reset(client, message, say, context, logger)


@app.message(re.compile(r"^!gpt-4-rs$"))
def message_reset(client, message, say, context, logger):
    """GPT-4の会話履歴をリセットする"""
    if not strtobool(os.getenv("USE_GPT_4_COMMAND")):  # GPT-4コマンドを利用できない場合は終了
        return

    if not check_availability(message, logger):
        say_ts(client, message, f"<#{message['channel']}> はパブリックチャンネルではないため利用できません。")
        logger.info(f"user: {message['user']}, <#{message['channel']}> はパブリックチャンネルではないため利用できません。")
        return

    try:
        if message["user"] in using_user_set: # 既に自身が利用中の場合
            say_ts(client, message, f"<@{message['user']}> さんの返答に対応中なのでお待ちください。")
        else:
            using_user_set.add(message["user"])
            gpt_4_command_executor.execute_reset(client, message, say, context, logger)
            using_user_set.remove(message["user"]) # ユーザーを解放
    except Exception as e:
        using_user_set.remove(message["user"]) # ユーザーを解放
        logger.error(traceback.format_exc())
        say_ts(client, message, f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")


@app.message(re.compile(r"^!gpt-help$"))
def message_help(client, message, say, context, logger):
    """ヘルプを表示する"""
    help_message =  f"`!gpt [ボットに伝えたいメッセージ]` の形式でChatGPTのAIと会話できます。会話の履歴は、{INPUT_MAX_TOKEN_SIZE}トークンまで保持します。\n" +\
        "`!gpt-rs` 利用しているチャンネルにおけるユーザーの会話の履歴をリセットします。\n" +\
        "`!gpt-ua [@ユーザー名]` 直近のパブリックチャンネルでの発言より、どのようなユーザーであるのかを分析します。\n" +\
        "`!gpt-ca [#チャンネル名]` パブリックチャンネルの直近の投稿内容から、どのようなチャンネルであるのかを分析します。\n" +\
        "`!gpt-q [質問]` パブリックチャンネルの検索結果を踏まえて質問に答えます。(注. 精度はあまり高くありません)\n"

    if  strtobool(os.getenv("USE_GPT_4_COMMAND")):  # GPT-4コマンドを利用する場合
        help_message += f"`!gpt-4 [ボットに伝えたいメッセージ]` の形式でGPT-4のAIと会話できます。会話の履歴は、{gpt_4_command_executor.INPUT_MAX_TOKEN_SIZE}トークンまで保持します。(注. 知識は多いですが動作は遅く、利用制限があり使えないこともあります)\n"
        help_message += "`!gpt-4-rs` 利用しているチャンネルにおけるユーザーのGPT-4との会話の履歴をリセットします。\n"

    say_ts(client, message, help_message)

@app.event("message")
def handle_message_events(body, logger):
    logger.debug(body)


# アプリを起動
if __name__ == "__main__":
    SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN")).start()
