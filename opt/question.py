from util import getHistoryIdentifier, getUserIdentifier
import datetime
import openai
import os
import re

from dotenv import load_dotenv
load_dotenv()


def sayAnswer(client, message, say, usingUser, question):
    """
    質問の答えのメッセージを送信する
    """

    print(f"<@{usingUser}>  さんの以下の質問にパブリックチャンネルの検索結果を踏まえて対応中\n```\n{question}\n```")
    say(f"<@{usingUser}>  さんの以下の質問にパブリックチャンネルの検索結果を踏まえて対応中\n```\n{question}\n```")

    usingTeam = message["team"]
    userIdentifier = getUserIdentifier(usingTeam, usingUser)

    # ChatCompletionから適切なクエリを聞く
    queryAskPrompt = f"「{question}」という質問をSlackの検索で調べるときに適切な検索クエリを教えてください。検索クエリとは単一の検索のための単語、または、複数の検索のための単語を半角スペースで繋げた文字列です。検索クエリを##########検索クエリ##########の形式で教えてください。"
    queryGPTResponse = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": queryAskPrompt}],
        top_p=1,
        n=1,
        max_tokens=1024,
        temperature=1,  # 生成する応答の多様性
        presence_penalty=0,
        frequency_penalty=0,
        logit_bias={},
        user=userIdentifier
    )
    print(queryGPTResponse)
    queryGPTResponseContent = queryGPTResponse["choices"][0]["message"]["content"]

    print(f"queryGPTResponseContent: {queryGPTResponseContent}")
    matches = re.match(
        r'^(.|\s)*##########(.*)##########(.|\s)*$', queryGPTResponseContent)
    query = ""
    if matches is None:
        query = question # 検索クエリがない場合は質問そのものを検索クエリにする
    else:
        query = matches.group(2)

    print(f"query: `{query}`")
    searchResponse = client.search_messages(token=os.getenv("SLACK_USER_TOKEN"),
                                            query=query, count=100, highlight=False)
    matches = searchResponse["messages"]["matches"]

    prompt = f"「{question}」という質問の答えを、以下のSlack上の「{query}」の検索結果の情報も加味し、検討して答えてください。\n\n----------------\n\n"
    for match in matches:
        if match["channel"]["is_private"] == False and match["channel"]["is_mpim"] == False:
            formatedMessage = f"""
投稿チャンネル: {match["channel"]["name"]}
投稿日時: {datetime.datetime.fromtimestamp(float(match["ts"]))}
ユーザー名: {match["username"]}
投稿内容: {match["text"]}
リンク: {match["permalink"]}
            """

            # 指定文字以上になったら履歴は追加しない 上限は4096トークンだが計算できないので適当な値
            if len(prompt) + len(formatedMessage) < 3800:
                prompt += formatedMessage

    # ChatCompletionを呼び出す
    print(f"prompt: `{prompt}`")
    chatGPTResponse = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        top_p=1,
        n=1,
        max_tokens=1024,
        temperature=1,  # 生成する応答の多様性
        presence_penalty=0,
        frequency_penalty=0,
        logit_bias={},
        user=userIdentifier
    )
    print(chatGPTResponse)

    say(chatGPTResponse["choices"][0]["message"]["content"])
