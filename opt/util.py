from typing import List, Dict
import os
from distutils.util import strtobool
import tiktoken


def say_ts(client, message, text):
    """スレッドへの返信を行う形式で発言する"""
    client.chat_postMessage(channel=message["channel"],
                            thread_ts=message["ts"],
                            text=text)


enc = tiktoken.get_encoding("cl100k_base")
GPT_3_5_TURBO_16K_MODEL = "gpt-3.5-turbo-16k"


def calculate_num_tokens(
    messages: List[Dict[str, str]],
    model: str = GPT_3_5_TURBO_16K_MODEL,
) -> int:
    """
    メッセージのトークン数を計算する
    参考実装: https://github.com/seratch/ChatGPT-in-Slack/blob/e8202b144d0d90e5095623f207e291f9008ca8ff/internals.py#L105
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == GPT_3_5_TURBO_16K_MODEL:  # note: future models may deviate from this
        num_tokens = 0
        for message in messages:
            # every message follows <im_start>{role/name}\n{content}<im_end>\n
            num_tokens += 4
            if hasattr(message, "items"):
                for key, value in message.items():

                    if isinstance(value, list): # GPT-4oの場合はcontentが複数ある場合があるのでその分岐
                        for v in value:
                            for in_value_key, in_value_value in v.items():
                                if (in_value_key == "text" or in_value_key == "type")and isinstance(in_value_value, str):
                                    num_tokens += len(encoding.encode(in_value_value))
                    else: 
                        if not isinstance(value, str):
                            continue
                        num_tokens += len(encoding.encode(value))
                        if key == "name":  # if there's a name, the role is omitted
                            num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens
    else:
        error = (
            f"Calculating the number of tokens for for model {model} is not yet supported. "
            "See https://github.com/openai/openai-python/blob/main/chatml.md "
            "for information on how messages are converted to tokens."
        )
        raise NotImplementedError(error)


def calculate_num_tokens_by_prompt(prompt):
    """プロンプトのトークン数を計算する"""
    return calculate_num_tokens([{"role": "user", "content": prompt}])


def get_history_identifier(team, channel, user):
    """会話履歴を取得するためのIDを生成する"""
    return f"slack-{team}-{channel}-{user}"


def get_user_identifier(team, user):
    """ユーザーを特定するためのIDを生成する"""
    return f"slack-{team}-{user}"


def check_availability(message, logger) -> bool:
    """このチャンネルが利用可能かどうかを返す。 check True で利用可能"""
    # もし環境変数にUSE_ONLY_PUBLIC_CHANNELが設定されていて、かつ、チャンネルタイプがpublicであるchannelでないなら、利用不可
    if strtobool(os.getenv("USE_ONLY_PUBLIC_CHANNEL")) and message["channel_type"] != "channel":
        return False
    else:
        return True

def check_daily_user_limit(message, usage_log) -> bool:
    """このユーザーが利用可能かどうかを返す。 check True で利用可能"""
    # もし環境変数にDAILY_USER_LIMITが設定されていて、かつ、ユーザーの利用回数がその上限を超えているなら、利用不可
    if os.getenv("DAILY_USER_LIMIT"):
        daily_user_limit = int(os.getenv("DAILY_USER_LIMIT"))
        num_logs = usage_log.get_num_logs(message["user"])
        return num_logs <= daily_user_limit
    else:
        return True

