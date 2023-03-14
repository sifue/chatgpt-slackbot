from typing import List, Dict
from util import get_user_identifier, calculate_num_tokens_by_prompt, calculate_num_tokens, say_ts
import datetime
import openai
import os

from dotenv import load_dotenv
load_dotenv()

MAX_TOKEN_SIZE = 4096  # トークンの最大サイズ
COMPLETION_MAX_TOKEN_SIZE = 1024  # ChatCompletionの出力の最大トークンサイズ
INPUT_MAX_TOKEN_SIZE = MAX_TOKEN_SIZE - COMPLETION_MAX_TOKEN_SIZE  # ChatCompletionの入力に使うトークンサイズ

def say_channel_analysis(client, message, say, using_user, target_channel, logger):
    """
    チャンネル分析のメッセージを送信する
    """

    logger.info(f"<@{using_user}> さんの依頼で {target_channel} について、直近のチャンネルでの発言より分析します。")
    say_ts(client, message, f"<@{using_user}> さんの依頼で {target_channel} について、直近のチャンネルでの発言より分析します。")

    search_response = client.search_messages(token=os.getenv("SLACK_USER_TOKEN"),
                                            query=f"in:{target_channel}", count=100, highlight=False)
    matches = search_response["messages"]["matches"]

    count = 0
    prompt = "以下のSlack上のチャンネルの投稿情報から、このチャンネルがどのようなチャンネルなのか分析して教えてください。\n\n----------------\n\n"
    for match in matches:
        if match["channel"]["is_private"] == False and match["channel"]["is_mpim"] == False:
            formated_message = f"""
投稿チャンネル: {match["channel"]["name"]}
投稿日時: {datetime.datetime.fromtimestamp(float(match["ts"]))}
ユーザー名: {match["username"]}
投稿内容: {match["text"]}
            """

            # 指定トークン数以上になったら追加しない
            if calculate_num_tokens_by_prompt(prompt + formated_message) < INPUT_MAX_TOKEN_SIZE:
                count += 1
                prompt += formated_message

    if len(matches) == 0 or count == 0:
        say_ts(client, message, f"{target_channel} での発言は見つかりませんでした。")
        return

    using_team = message["team"]
    user_identifier = get_user_identifier(using_team, using_user)

    # ChatCompletionを呼び出す
    logger.debug(f"prompt: `{prompt}`")
    chat_gpt_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        top_p=1,
        n=1,
        max_tokens=COMPLETION_MAX_TOKEN_SIZE,
        temperature=1,  # 生成する応答の多様性
        presence_penalty=0,
        frequency_penalty=0,
        logit_bias={},
        user=user_identifier
    )
    logger.debug(chat_gpt_response)

    say_ts(client, message, chat_gpt_response["choices"][0]["message"]["content"])
    logger.info(f"user: {message['user']}, content: {chat_gpt_response['choices'][0]['message']['content']}")
