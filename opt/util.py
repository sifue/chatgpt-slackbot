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