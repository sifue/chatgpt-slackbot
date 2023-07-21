from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt import App
from distutils.util import strtobool
import os
import openai
import re
from gpt_function_calling import GPT_Function_Calling_CommandExecutor
from gpt_4 import GPT_4_CommandExecutor
from util import get_history_identifier, get_user_identifier, calculate_num_tokens, calculate_num_tokens_by_prompt, say_ts, check_availability, check_daily_user_limit
from channel_analysis import say_channel_analysis
from websearch import say_with_websearch
from question import say_answer
from user_analysis import say_user_analysis
from usage_logs import Usage_Logs, Command_Type
from typing import List, Dict
import traceback
import logging
fmt = "%(asctime)s %(levelname)s %(name)s :%(message)s"
logging.basicConfig(level=logging.INFO, format=fmt)


load_dotenv()

openai.organization = os.getenv("ORGANAZTION_ID")
openai.api_key = os.getenv("OPENAI_API_KEY")

# ボットトークンとソケットモードハンドラーを使ってアプリを初期化
app = App(token=os.getenv("SLACK_BOT_TOKEN"))

# ユーザー利用ログを記録するDB、closeは行わない想定
usage_log = Usage_Logs()

# 現在使用中のユーザーのセット、複数リクエストを受けると履歴が壊れることがあるので、一つのユーザーに対しては一つのリクエストしか受け付けないようにする
using_user_set = set()

gpt_4_command_executor = GPT_4_CommandExecutor(openai)
gpt_function_calling_executor = GPT_Function_Calling_CommandExecutor(openai)


@app.message(re.compile(r"^!gpt ((.|\s)*)$"))
def message_gpt(client, message, say, context, logger):
    if not check_availability(message, logger):
        notice_not_available_in_private_message(client, message, logger)
        return

    if not check_daily_user_limit(message, usage_log):
        notice_daily_limit_message(client, message, logger)
        return

    try:
        if message["user"] in using_user_set:  # 既に自身が利用中の場合
            say_ts(client, message,
                   f"<@{message['user']}> さんの返答に対応中なのでお待ちください。")
        else:
            using_user_set.add(message["user"])
            gpt_function_calling_executor.execute(
                client, message, say, context, logger)
            using_user_set.remove(message["user"])  # ユーザーを解放
            usage_log.save(message['user'], Command_Type.GPT.value)
    except Exception as e:
        using_user_set.remove(message["user"])  # ユーザーを解放
        logger.error(traceback.format_exc())
        say_ts(client, message, f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")

        # エラーを発生させた人の会話の履歴をリセットをする
        gpt_function_calling_executor.execute_reset(
            client, message, say, context, logger)


@app.message(re.compile(r"^!gpt-rs$"))
def message_reset(client, message, say, context, logger):
    if not check_availability(message, logger):
        notice_not_available_in_private_message(client, message, logger)
        return

    try:
        if message["user"] in using_user_set:  # 既に自身が利用中の場合
            say_ts(client, message,
                   f"<@{message['user']}> さんの返答に対応中なのでお待ちください。")
        else:
            using_user_set.add(message["user"])
            gpt_function_calling_executor.execute_reset(
                client, message, say, context, logger)
            using_user_set.remove(message["user"])  # ユーザーを解放
    except Exception as e:
        using_user_set.remove(message["user"])  # ユーザーを解放
        logger.error(traceback.format_exc())
        say_ts(client, message, f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")


@app.message(re.compile(r"^!gpt-ua (\<\@[^ ]*\>).*$"))
def message_user_analysis(client, message, say, context, logger):
    """ユーザーの分析を行う"""
    if not check_availability(message, logger):
        notice_not_available_in_private_message(client, message, logger)
        return

    if not check_daily_user_limit(message, usage_log):
        notice_daily_limit_message(client, message, logger)
        return

    try:
        if message["user"] in using_user_set:  # 既に自身が利用中の場合
            say_ts(client, message,
                   f"<@{message['user']}> さんの返答に対応中なのでお待ちください。")
        else:
            using_user_set.add(message["user"])
            say_user_analysis(client, message, say,
                              message["user"], context["matches"][0], logger)
            using_user_set.remove(message["user"])  # ユーザーを解放
            usage_log.save(message['user'], Command_Type.GPT_UA.value)
    except Exception as e:
        using_user_set.remove(message["user"])  # ユーザーを解放
        logger.error(traceback.format_exc())
        say_ts(client, message, f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")


@app.message(re.compile(r"^!gpt-ca (\<\#[^ ]*\>).*$"))
def message_channel_analysis(client, message, say, context, logger):
    """チャンネルの分析を行う"""
    if not check_availability(message, logger):
        notice_not_available_in_private_message(client, message, logger)
        return

    if not check_daily_user_limit(message, usage_log):
        notice_daily_limit_message(client, message, logger)
        return

    try:
        if message["user"] in using_user_set:  # 既に自身が利用中の場合
            say_ts(client, message,
                   f"<@{message['user']}> さんの返答に対応中なのでお待ちください。")
        else:
            using_user_set.add(message["user"])
            say_channel_analysis(client, message, say,
                                 message["user"], context["matches"][0], logger)
            using_user_set.remove(message["user"])  # ユーザーを解放
            usage_log.save(message['user'], Command_Type.GPT_CA.value)
    except Exception as e:
        using_user_set.remove(message["user"])  # ユーザーを解放
        logger.error(traceback.format_exc())
        say_ts(client, message, f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")


@app.message(re.compile(r"^!gpt-w ((.|\s)*)$"))
def message_websearch(client, message, say, context, logger):
    """DuckDuckGoでのWeb検索を踏まえて質問に回答する"""
    if not check_availability(message, logger):
        notice_not_available_in_private_message(client, message, logger)
        return

    if not check_daily_user_limit(message, usage_log):
        notice_daily_limit_message(client, message, logger)
        return

    try:
        if message["user"] in using_user_set:  # 既に自身が利用中の場合
            say_ts(client, message,
                   f"<@{message['user']}> さんの返答に対応中なのでお待ちください。")
        else:
            using_user_set.add(message["user"])
            say_with_websearch(client, message, say,
                               message["user"], context["matches"][0], logger)
            using_user_set.remove(message["user"])  # ユーザーを解放
            usage_log.save(message['user'], Command_Type.GPT_W.value)
    except Exception as e:
        using_user_set.remove(message["user"])  # ユーザーを解放
        logger.error(e)
        say_ts(client, message, f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")


@app.message(re.compile(r"^!gpt-q ((.|\s)*)$"))
def message_question(client, message, say, context, logger):
    """Slackの検索を踏まえて質問に回答する"""
    if not check_availability(message, logger):
        notice_not_available_in_private_message(client, message, logger)
        return

    if not check_daily_user_limit(message, usage_log):
        notice_daily_limit_message(client, message, logger)
        return

    try:
        if message["user"] in using_user_set:  # 既に自身が利用中の場合
            say_ts(client, message,
                   f"<@{message['user']}> さんの返答に対応中なのでお待ちください。")
        else:
            using_user_set.add(message["user"])
            say_answer(client, message, say,
                       message["user"], context["matches"][0], logger)
            using_user_set.remove(message["user"])  # ユーザーを解放
            usage_log.save(message['user'], Command_Type.GPT_Q.value)
    except Exception as e:
        using_user_set.remove(message["user"])  # ユーザーを解放
        logger.error(traceback.format_exc())
        say_ts(client, message, f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")


@app.message(re.compile(r"^!gpt-4 ((.|\s)*)$"))
def message_gpt_4(client, message, say, context, logger):
    """GPT-4の会話をする"""
    if not strtobool(os.getenv("USE_GPT_4_COMMAND")):  # GPT-4コマンドを利用できない場合は終了
        return

    if not check_availability(message, logger):
        notice_not_available_in_private_message(client, message, logger)
        return

    if not check_daily_user_limit(message, usage_log):
        notice_daily_limit_message(client, message, logger)
        return

    try:
        if message["user"] in using_user_set:  # 既に自身が利用中の場合
            say_ts(client, message,
                   f"<@{message['user']}> さんの返答に対応中なのでお待ちください。")
        else:
            using_user_set.add(message["user"])
            gpt_4_command_executor.execute(
                client, message, say, context, logger)
            using_user_set.remove(message["user"])  # ユーザーを解放
            usage_log.save(message['user'], Command_Type.GPT_4.value)  # ログ保存
    except Exception as e:
        using_user_set.remove(message["user"])  # ユーザーを解放
        logger.error(traceback.format_exc())
        say_ts(client, message, f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")

        # エラーを発生させた人の会話の履歴をリセットをする
        gpt_4_command_executor.execute_reset(
            client, message, say, context, logger)


@app.message(re.compile(r"^!gpt-4-rs$"))
def message_reset(client, message, say, context, logger):
    """GPT-4の会話履歴をリセットする"""
    if not strtobool(os.getenv("USE_GPT_4_COMMAND")):  # GPT-4コマンドを利用できない場合は終了
        return

    if not check_availability(message, logger):
        notice_not_available_in_private_message(client, message, logger)
        return

    try:
        if message["user"] in using_user_set:  # 既に自身が利用中の場合
            say_ts(client, message,
                   f"<@{message['user']}> さんの返答に対応中なのでお待ちください。")
        else:
            using_user_set.add(message["user"])
            gpt_4_command_executor.execute_reset(
                client, message, say, context, logger)
            using_user_set.remove(message["user"])  # ユーザーを解放
    except Exception as e:
        using_user_set.remove(message["user"])  # ユーザーを解放
        logger.error(traceback.format_exc())
        say_ts(client, message, f"エラーが発生しました。やり方を変えて再度試してみてください。 Error: {e}")


@app.message(re.compile(r"^!gpt-help$"))
def message_help(client, message, say, context, logger):
    """ヘルプを表示する"""
    help_message = "ChatGPTは13歳以上の方しか利用できず、18歳未満の方は必ず保護者の同意の元で利用してください。このボットで利用できるコマンドは以下のとおりです。\n" +\
     f"`!gpt [ボットに伝えたいメッセージ]` の形式でChatGPTのAIと会話できます。「Web検索をして～して」または「Slack検索をして～して」と伝えることでそれを検索結果を考慮した受け答えができます。会話の履歴は、{gpt_function_calling_executor.INPUT_MAX_TOKEN_SIZE}トークンまで保持します。\n" +\
        "`!gpt-rs` 利用しているチャンネルにおけるユーザーの会話の履歴をリセットします。\n" +\
        "`!gpt-ua [@ユーザー名]` 直近のパブリックチャンネルでの発言より、どのようなユーザーであるのかを分析します。\n" +\
        "`!gpt-ca [#チャンネル名]` パブリックチャンネルの直近の投稿内容から、どのようなチャンネルであるのかを分析します。\n" +\
        "`!gpt-w [質問]` Web検索の結果を踏まえて質問に答えます。\n" +\
        "`!gpt-q [質問]` パブリックチャンネルの検索結果を踏まえて質問に答えます。(注. 精度はあまり高くありません)\n"

    if strtobool(os.getenv("USE_GPT_4_COMMAND")):  # GPT-4コマンドを利用する場合
        help_message += f"`!gpt-4 [ボットに伝えたいメッセージ]` の形式でGPT-4のAIと会話できます。会話の履歴は、{gpt_4_command_executor.INPUT_MAX_TOKEN_SIZE}トークンまで保持します。(注. 知識は多いですが動作は遅く、利用制限があり使えないこともあります)\n"
        help_message += "`!gpt-4-rs` 利用しているチャンネルにおけるユーザーのGPT-4との会話の履歴をリセットします。\n"

    say_ts(client, message, help_message)


def notice_not_available_in_private_message(client, message, logger):
    say_ts(client, message,
           f"<#{message['channel']}> はパブリックチャンネルではないため利用できません。")
    logger.info(
        f"user: {message['user']}, <#{message['channel']}> はパブリックチャンネルではないため利用できません。")


def notice_daily_limit_message(client, message, logger):
    say_ts(client, message,
           f"<@{message['user']}> は、本日の利用回数上限の{os.getenv('DAILY_USER_LIMIT')}回に達しているため、利用できません。")
    logger.info(
        f"user: {message['user']}, 本日の利用回数上限の{os.getenv('DAILY_USER_LIMIT')}回に達しているため、利用できません。")


@app.event("message")
def handle_message_events(body, logger):
    logger.debug(body)


# アプリを起動
if __name__ == "__main__":
    SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN")).start()
