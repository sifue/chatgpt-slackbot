from typing import List, Dict
from util import get_user_identifier, calculate_num_tokens_by_prompt, say_ts
import datetime
import openai
import os

from dotenv import load_dotenv
load_dotenv()

MAX_TOKEN_SIZE = 16384  # トークンの最大サイズ
COMPLETION_MAX_TOKEN_SIZE = 4096  # ChatCompletionの出力の最大トークンサイズ
INPUT_MAX_TOKEN_SIZE = MAX_TOKEN_SIZE - COMPLETION_MAX_TOKEN_SIZE  # ChatCompletionの入力に使うトークンサイズ

def say_user_analysis(client, message, say, using_user, target_user, logger):
    """
    ユーザー分析のメッセージを送信する
    """

    logger.info(f"<@{using_user}> さんの依頼で {target_user} さんについて、直近のパブリックチャンネルの発言より分析します。")
    say_ts(client, message, f"<@{using_user}> さんの依頼で {target_user} さんについて、直近のパブリックチャンネルの発言より分析します。")

    search_page = 1
    total_page = 1
    prompt = "以下のSlack上の投稿情報からこのユーザーがどのような人物なのか、どのような性格なのか分析して教えてください。\n\n----------------\n\n"
    message_count = 0
    is_full = False

    # 入力トークンサイズまで何度も検索して、直近のパブリックチャンネルの発言を取得する
    while not is_full and search_page <= total_page:
        logger.info(f"<@{using_user}> さんの {target_user} さんについての {search_page} / {total_page} 回目の検索を開始します。")
        searchResponse = client.search_messages(token=os.getenv("SLACK_USER_TOKEN"),
                                                query=f"from:{target_user}", page=search_page, count=100, highlight=False)
        matches = searchResponse["messages"]["matches"]
        total_page = searchResponse["messages"]["paging"]["total"]

        for match in matches:
            if match["channel"]["is_private"] == False and match["channel"]["is_mpim"] == False:
                formated_message = f"""
    投稿チャンネル: {match["channel"]["name"]}
    投稿日時: {datetime.datetime.fromtimestamp(float(match["ts"]))}
    ユーザーID: {match["user"]}
    投稿内容: {match["text"]}
                """

                # 入力トークンサイズ以下なら、promptに追加する、そうでないなら is_full を True にする
                if calculate_num_tokens_by_prompt(prompt + formated_message) < INPUT_MAX_TOKEN_SIZE:
                    message_count += 1
                    prompt += formated_message
                else:
                    is_full = True
        search_page += 1

    if message_count == 0:
        say_ts(client, message, f"{target_user} さんの発言は見つかりませんでした。")
        return

    using_team = message["team"]
    user_identifier = get_user_identifier(using_team, using_user)

    logger.info(f"{target_user} さんについての {message_count} 件の発言を分析します。")

    # ChatCompletionを呼び出す
    logger.debug(f"prompt: `{prompt}`")
    chat_gpt_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
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
