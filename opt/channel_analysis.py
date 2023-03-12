from util import getUserIdentifier, getTokenSize
import datetime
import openai
import os

from dotenv import load_dotenv
load_dotenv()

MAX_TOKEN_SIZE = 3900  # トークンの最大サイズ (実際には4097だが、結合のために少し小さくしておく)
COMPLETION_MAX_TOKEN_SIZE = 1000  # ChatCompletionの出力の最大トークンサイズ
INPUT_MAX_TOKEN_SIZE = MAX_TOKEN_SIZE - COMPLETION_MAX_TOKEN_SIZE  # ChatCompletionの入力に使うトークンサイズ

def sayChannelAnalysis(client, message, say, usingUser, targetChannel):
    """
    チャンネル分析のメッセージを送信する
    """

    print(f"<@{usingUser}> さんの依頼で {targetChannel} について、直近のチャンネルでの発言より分析します。")
    say(f"<@{usingUser}> さんの依頼で {targetChannel} について、直近のチャンネルでの発言より分析します。")

    searchResponse = client.search_messages(token=os.getenv("SLACK_USER_TOKEN"),
                                            query=f"in:{targetChannel}", count=100, highlight=False)
    matches = searchResponse["messages"]["matches"]

    count = 0
    prompt = "以下のSlack上のチャンネルの投稿情報から、このチャンネルがどのようなチャンネルなのか分析して教えてください。\n\n----------------\n\n"
    for match in matches:
        if match["channel"]["is_private"] == False and match["channel"]["is_mpim"] == False:
            formatedMessage = f"""
投稿チャンネル: {match["channel"]["name"]}
投稿日時: {datetime.datetime.fromtimestamp(float(match["ts"]))}
ユーザー名: {match["username"]}
投稿内容: {match["text"]}
            """

            # 指定トークン数以上になったら追加しない
            if getTokenSize(prompt) + getTokenSize(formatedMessage) < INPUT_MAX_TOKEN_SIZE:
                count += 1
                prompt += formatedMessage

    if len(matches) == 0 or count == 0:
        say(f"{targetChannel} での発言は見つかりませんでした。")
        return

    usingTeam = message["team"]
    userIdentifier = getUserIdentifier(usingTeam, usingUser)

    # ChatCompletionを呼び出す
    print(f"prompt: `{prompt}`")
    chatGPTResponse = openai.ChatCompletion.create(
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
    print(chatGPTResponse)

    say(chatGPTResponse["choices"][0]["message"]["content"])
