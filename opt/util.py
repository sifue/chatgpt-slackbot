import tiktoken

enc = tiktoken.get_encoding("cl100k_base")

def getTokenSize(text):
    return len(enc.encode(text))

def getHistoryIdentifier(team, channel, user):
    """
    会話履歴を取得するためのIDを生成する
    """
    return f"slack-{team}-{channel}-{user}"


def getUserIdentifier(team, user):
    """
    ユーザーを特定するためのIDを生成する
    """
    return f"slack-{team}-{user}"