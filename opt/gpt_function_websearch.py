from util import get_history_identifier, get_user_identifier, calculate_num_tokens, calculate_num_tokens_by_prompt, say_ts, check_availability
from typing import List, Dict
from datetime import datetime
import json
import urllib3

class GPT_Function_Websearch_CommandExecutor():
    """ChatGPT Function Calling を使ってWeb検索利用の会話をするコマンドの実行クラス"""

    MAX_TOKEN_SIZE = 16384  # トークンの最大サイズ
    COMPLETION_MAX_TOKEN_SIZE = 4096  # ChatCompletionの出力の最大トークンサイズ
    INPUT_MAX_TOKEN_SIZE = MAX_TOKEN_SIZE - \
        COMPLETION_MAX_TOKEN_SIZE  # ChatCompletionの入力に使うトークンサイズ

    def __init__(self, openai):
        self.history_dict: Dict[str, List[Dict[str, str]]] = {}
        self.openai = openai

    FUNCTIONS = [
        {
            "name": "get_web_search_result",
            "description": "Web検索(DuckDuckGoを利用)を行い、現在時刻と検索結果を取得する",
            "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "検索クエリ、 e.g. 'cats dogs', '\"cats and dogs\"', 'cats -dogs', 'cats +dogs', 'cats filetype:pdf', 'dogs site:example.com', 'cats -site:example.com', 'intitle:dogs', 'inurl:cats'",
                        }
                    },
                "required": ["query"],
            },
        }
    ]

    def get_web_search_result(self, query):
        """Web検索を実行する、Function Calling用実装"""
        search_results = []
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for r in ddgs.text(query, region='wt-wt', safesearch='on', timelimit='y'):
                search_results.append(r)
                if len(search_results) >= 10:
                    break
        return {
            "current_time": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "search_results": search_results
        }

    def execute(self, client, message, say, context, logger):
        """Function Callingを使って会話をするコマンドの実行メソッド"""
        using_team = message["team"]
        using_channel = message["channel"]
        history_idetifier = get_history_identifier(
            using_team, using_channel, message["user"])
        user_identifier = get_user_identifier(using_team, message["user"])

        prompt = context["matches"][0]

        # ヒストリーを取得
        history_array: List[Dict[str, str]] = []
        if history_idetifier in self.history_dict.keys():
            history_array = self.history_dict[history_idetifier]
        history_array.append({"role": "user", "content": prompt})

        # トークンのサイズがINPUT_MAX_TOKEN_SIZEを超えたら古いものを削除
        while calculate_num_tokens(history_array) > self.INPUT_MAX_TOKEN_SIZE:
            history_array = history_array[1:]

        # 単一の発言でMAX_TOKEN_SIZEを超えたら、対応できない
        if (len(history_array) == 0):
            messege_out_of_token_size = f"発言内容のトークン数が{self.INPUT_MAX_TOKEN_SIZE}を超えて、{calculate_num_tokens_by_prompt(prompt)}であったため、対応できませんでした。"
            say_ts(client, message, messege_out_of_token_size)
            logger.info(messege_out_of_token_size)
            return

        say_ts(client, message,
               f"Function Calling (Web検索)で <@{message['user']}> さんの以下の発言に対応中（履歴数: {len(history_array)} 、トークン数: {calculate_num_tokens(history_array)}）\n```\n{prompt}\n```")

        # ChatCompletionを呼び出す
        logger.info(f"user: {message['user']}, prompt: {prompt}")
        response = self.openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k-0613",
            messages=history_array,
            top_p=1,
            n=1,
            max_tokens=self.COMPLETION_MAX_TOKEN_SIZE,
            temperature=1,  # 生成する応答の多様性
            presence_penalty=0,
            frequency_penalty=0,
            logit_bias={},
            user=user_identifier,
            functions=self.FUNCTIONS,
            function_call="auto"
        )
        logger.debug(response)

        # ヒストリーを新たに追加
        new_response_message = response["choices"][0]["message"]
        history_array.append(new_response_message)

        # もしFunction Callingがあれば再度問い合わせる
        if new_response_message.get("function_call"):
            function_name = new_response_message["function_call"]["name"]
            function_response = []
            if function_name == "get_web_search_result":
                function_args = json.loads(
                    new_response_message["function_call"]["arguments"])
                query = function_args.get("query")
                say_ts(client, message,
                       f"関数 `{function_name}` を引数 `query={query}` で呼び出し中...")
                function_response = self.get_web_search_result(query)
                search_results = function_response["search_results"]

                link_references = []
                for idx, result in enumerate(search_results):
                    domain_name = urllib3.util.parse_url(result["href"]).host
                    link_references.append(
                        f"{idx+1}. <{result['href']}|{domain_name}>\n")
                link_references = "\n\n" + "".join(link_references)
                say_ts(client, message,
                       f"以下のWeb検索の結果を参考に返答を作成します。" + link_references)

            # 関数呼び出しの結果をヒストリーに追加
            history_array.append({
                "role": "function",
                "name": function_name,
                "content": json.dumps(function_response),  # JSON文字列
            })

            # トークンのサイズがINPUT_MAX_TOKEN_SIZEを超えたら古いものを削除
            while calculate_num_tokens(history_array) > self.INPUT_MAX_TOKEN_SIZE:
                history_array = history_array[1:]

            # ChatCompletionを呼び出す
            response = self.openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k-0613",
                messages=history_array,
                top_p=1,
                n=1,
                max_tokens=self.COMPLETION_MAX_TOKEN_SIZE,
                temperature=1,  # 生成する応答の多様性
                presence_penalty=0,
                frequency_penalty=0,
                logit_bias={},
                user=user_identifier
            )
            # ヒストリーを新たに追加
            new_response_message = response["choices"][0]["message"]
            history_array.append(new_response_message)

        # トークンのサイズがINPUT_MAX_TOKEN_SIZEを超えたら古いものを削除
        while calculate_num_tokens(history_array) > self.INPUT_MAX_TOKEN_SIZE:
            history_array = history_array[1:]
        self.history_dict[history_idetifier] = history_array  # ヒストリーを更新

        say_ts(client, message, new_response_message["content"])
        logger.info(
            f"user: {message['user']}, content: {new_response_message['content']}")

    def execute_reset(self, client, message, say, context, logger):
        """ChatGPT Function Callingを使った会話履歴のリセットをするコマンドの実行メソッド"""
        using_team = message["team"]
        using_channel = message["channel"]
        historyIdetifier = get_history_identifier(
            using_team, using_channel, message["user"])

        # 履歴をリセットをする
        self.history_dict[historyIdetifier] = []

        logger.info(
            f"Function Calling (Web検索)の <@{message['user']}> さんの <#{using_channel}> での会話の履歴をリセットしました。")
        say_ts(client, message,
               f"Function Calling (Web検索)の <@{message['user']}> さんの <#{using_channel}> での会話の履歴をリセットしました。")
