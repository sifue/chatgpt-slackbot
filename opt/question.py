from typing import List, Dict
from util import get_user_identifier, calculate_num_tokens_by_prompt, say_ts
import datetime
import openai
import os
import re

from dotenv import load_dotenv
load_dotenv()

MAX_TOKEN_SIZE = 4096  # トークンの最大サイズ
COMPLETION_MAX_TOKEN_SIZE = 1024  # ChatCompletionの出力の最大トークンサイズ
INPUT_MAX_TOKEN_SIZE = MAX_TOKEN_SIZE - COMPLETION_MAX_TOKEN_SIZE  # ChatCompletionの入力に使うトークンサイズ

def say_answer(client, message, say, using_user, question, logger):
    """
    質問の答えのメッセージを送信する
    """

    logger.info(f"<@{using_user}>  さんの以下の質問にパブリックチャンネルの検索結果を踏まえて対応中\n```\n{question}\n```")
    say_ts(client, message, f"<@{using_user}>  さんの以下の質問にパブリックチャンネルの検索結果を踏まえて対応中\n```\n{question}\n```")

    usingTeam = message["team"]
    userIdentifier = get_user_identifier(usingTeam, using_user)

    # ChatCompletionから適切なクエリを聞く
    query_ask_prompt = f"「{question}」という質問をSlackの検索で調べるときに適切な検索クエリを教えてください。検索クエリとは単一の検索のための単語、または、複数の検索のための単語を半角スペースで繋げた文字列です。検索クエリを##########検索クエリ##########の形式で教えてください。"
    query_gpt_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": query_ask_prompt}],
        top_p=1,
        n=1,
        max_tokens=COMPLETION_MAX_TOKEN_SIZE,
        temperature=1,  # 生成する応答の多様性
        presence_penalty=0,
        frequency_penalty=0,
        logit_bias={},
        user=userIdentifier
    )
    logger.debug(query_gpt_response)
    query_gpt_response_content = query_gpt_response["choices"][0]["message"]["content"]

    logger.debug(f"queryGPTResponseContent: {query_gpt_response_content}")
    matches = re.match(
        r'^(.|\s)*##########(.*)##########(.|\s)*$', query_gpt_response_content)
    query = ""
    if matches is None:
        query = question # 検索クエリがない場合は質問そのものを検索クエリにする
    else:
        query = matches.group(2)

    logger.debug(f"query: `{query}`")
    search_response = client.search_messages(token=os.getenv("SLACK_USER_TOKEN"),
                                            query=query, count=100, highlight=False)
    matches = search_response["messages"]["matches"]

    prompt = f"「{question}」という質問の答えを、以下のSlack上の「{query}」の検索結果の情報も加味し、検討して答えてください。またその根拠も答えてください。\n\n----------------\n\n"
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
                prompt += formated_message

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
        user=userIdentifier
    )
    logger.debug(chat_gpt_response)

    say_ts(client, message, chat_gpt_response["choices"][0]["message"]["content"])
    logger.info(f"user: {message['user']}, content: {chat_gpt_response['choices'][0]['message']['content']}")
