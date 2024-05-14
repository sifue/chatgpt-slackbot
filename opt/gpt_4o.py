from util import get_history_identifier, get_user_identifier, calculate_num_tokens, calculate_num_tokens_by_prompt, say_ts, check_availability
from typing import List, Dict
import os
import requests
import base64

class GPT_4O_CommandExecutor():
    """GPT-4oを使って添付画像を含めて会話をするコマンドの実行クラス"""

    MAX_TOKEN_SIZE = 128000  # トークンの最大サイズ
    COMPLETION_MAX_TOKEN_SIZE = 2048  # ChatCompletionの出力の最大トークンサイズ
    INPUT_MAX_TOKEN_SIZE = MAX_TOKEN_SIZE - COMPLETION_MAX_TOKEN_SIZE  # ChatCompletionの入力に使うトークンサイズ

    def __init__(self, client_openai):
        self.history_dict : Dict[str, List[Dict[str, str]]] = {}
        self.client_openai = client_openai

    def execute(self, client, message, say, context, logger):
        """GPT-4oを使って会話をするコマンドの実行メソッド"""
        if "team" in message:
            using_team = message["team"]
        else:
            using_team = message["files"][0]["user_team"] # ファイルアップロードの場合は、user_teamを使う
        using_channel = message["channel"]
        history_idetifier = get_history_identifier(
            using_team, using_channel, message["user"])
        user_identifier = get_user_identifier(using_team, message["user"])

        prompt = context["matches"][0]

        contents = [
            {
                "type": "text",
                "text": prompt
            }
        ]

        if "files" in message:
            for file in message["files"]: # ファイルがあれば、それを追加
                url = file["url_private"]
                mimetype = file["mimetype"]
                SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
                url_data = requests.get(url,
                                        allow_redirects=True,
                                        headers={
                                            'Authorization': f"Bearer {SLACK_BOT_TOKEN}"},
                                        stream=True
                                        ).content
                encoded_data = base64.b64encode(url_data)
                encoded_string = encoded_data.decode('utf-8')
                contents.append({
                    "type": "image_url",
                    "image_url": {
                    "url": f"data:{mimetype};base64,{encoded_string}"
                    }
                })

        # ヒストリーを取得
        history_array: List[Dict[str, str]] = []
        if history_idetifier in self.history_dict.keys():
            history_array = self.history_dict[history_idetifier]

        history_array.append({"role": "user", "content": contents})

        # トークンのサイズがINPUT_MAX_TOKEN_SIZEを超えたら古いものを削除
        while calculate_num_tokens(history_array) > self.INPUT_MAX_TOKEN_SIZE:
            history_array = history_array[1:]

        # 単一の発言でMAX_TOKEN_SIZEを超えたら、対応できない
        if(len(history_array) == 0):
            messege_out_of_token_size = f"発言内容のトークン数が{self.INPUT_MAX_TOKEN_SIZE}を超えて、{calculate_num_tokens_by_prompt(prompt)}であったため、対応できませんでした。"
            say_ts(client, message, messege_out_of_token_size)
            logger.info(messege_out_of_token_size)
            return

        say_ts(client, message, f"GPT-4oで <@{message['user']}> さんの以下の発言に対応中（履歴数: {len(history_array)} 、トークン数: {calculate_num_tokens(history_array)}）\n```\n{prompt}\n```")

        # ChatCompletionを呼び出す
        logger.info(f"user: {message['user']}, prompt: {prompt}")
        response = self.client_openai.chat.completions.create(
            model="gpt-4o",
            messages=history_array,
            top_p=1,
            n=1,
            max_tokens=self.COMPLETION_MAX_TOKEN_SIZE,
            temperature=1,  # 生成する応答の多様性
            presence_penalty=0,
            frequency_penalty=0,
            user=user_identifier
        )
        logger.debug(response)

        # ヒストリーを新たに追加
        new_response_message = response.choices[0].message

        history_array.append(new_response_message)

        # トークンのサイズがINPUT_MAX_TOKEN_SIZEを超えたら古いものを削除
        while calculate_num_tokens(history_array) > self.INPUT_MAX_TOKEN_SIZE:
            history_array = history_array[1:]
        self.history_dict[history_idetifier] = history_array # ヒストリーを更新

        say_ts(client, message, new_response_message.content)
        logger.info(f"user: {message['user']}, content: {new_response_message.content}")

    def execute_reset(self, client, message, say, context, logger):
        """GPT-4oを使って会話履歴のリセットをするコマンドの実行メソッド"""
        if "team" in message:
            using_team = message["team"]
        else:
            using_team = message["files"][0]["user_team"] # ファイルアップロードの場合は、user_teamを使う
        using_channel = message["channel"]
        historyIdetifier = get_history_identifier(
            using_team, using_channel, message["user"])

        # 履歴をリセットをする
        self.history_dict[historyIdetifier] = []

        logger.info(f"GPT-4oの <@{message['user']}> さんの <#{using_channel}> での会話の履歴をリセットしました。")
        say_ts(client, message, f"GPT-4oの <@{message['user']}> さんの <#{using_channel}> での会話の履歴をリセットしました。")
