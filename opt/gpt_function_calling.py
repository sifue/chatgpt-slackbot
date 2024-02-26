from util import get_history_identifier, get_user_identifier, calculate_num_tokens, calculate_num_tokens_by_prompt, say_ts, check_availability
from typing import List, Dict
from datetime import datetime
import json
import urllib3
import os


class GPT_Function_Calling_CommandExecutor():
    """ChatGPT Function Calling を使ってWeb検索利用やSlack検索利用の会話をするコマンドの実行クラス"""

    FUNCTIONS = [
        {
            "name": "get_web_search_result",
            "description": "Web検索を行い、検索結果と現在時刻を取得する。これにより最新の情報を取得できる。クエリには複数の単語を指定することができるほか、ダブルクオーテーションを使ったフレーズ検索、ハイフンを利用したマイナス検索、サイト指定やタイトルに含むもの指定、URLに含むもの指定ができる。",
            "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "検索クエリは、'シャム猫 柴犬', '\"柴犬と三毛猫、飼うならどっち？\"', '日本橋 -東京', '三毛猫 +柴犬', 'シャム猫 filetype:pdf', '柴犬 site:example.com', 'シャム猫 -site:example.com', 'intitle:柴犬', 'inurl:cats' などを組み合わせて使う。例えば、ミノタウロスの閉じ込められた迷宮がどこにあるか知りたい場合には、 'ミノタウロス 迷宮 場所' というクエリとなる。",
                        }
                    },
                "required": ["query"],
            },
        },
        {
            "name": "get_slack_search_result",
            "description": "Slack検索を行い、検索結果と現在時刻をを取得する。クエリには検索単語に加えて from:<@{ユーザーID}> と指定すると特定のユーザーのメッセージ、in:<#{チャンネルID}> と指定すると特定のチャンネルのメッセージを検索できる。つまり <@{ユーザーID}> 形式の固有のSlackユーザーの情報や、 <#{チャンネルID}> 形式の固有のSlackチャンネルの情報について情報を取得できる。has:{絵文字コード} で、特定の絵文字を持つメッセージの検索を、 before:{YYYY-MM-DD形式の日付} 日付以前、 after:{YYYY-MM-DD形式の日付} 日付以降、 on:{YYYY-MM-DD形式の日付} その日付、 during:{YYYY-MMの月} その月のメッセージを検索する条件を追加できる。",
            "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "検索クエリは、 'シャム猫 犬', '\"柴犬と三毛猫、飼うならどっち？\"', '日本橋 -東京', 'from:<@U0VKMCTEV>', 'in:<#C0VF1QBEK>', 'before:2022-11-25', 'after:2022-11-25', 'on:2022-11-25', 'during:2022-11'などを組み合わせて使う。例えば、ユーザー <@U0VKMCTEV> の チャンネル <#C0VF1QBEK> での 2022年11月2日から2022年11月3日までのシャム猫に関することを調べるクエリは、 'from:<@U0VKMCTEV> in:<#C0VF1QBEK> after:2022-11-02 before:2022-11-03 シャム猫' というクエリとなる",
                        }
                    },
                "required": ["query"],
            },
        },
    ]

    MAX_TOKEN_SIZE = 16384  # トークンの最大サイズ
    COMPLETION_MAX_TOKEN_SIZE = 4096  # ChatCompletionの出力の最大トークンサイズ
    # ChatCompletionの入力に使うトークンサイズ、FUNCTION分はJSON化してプロンプトとして雑に計算する(トークン計算方法不明のため)
    INPUT_MAX_TOKEN_SIZE = MAX_TOKEN_SIZE - \
        COMPLETION_MAX_TOKEN_SIZE - \
        calculate_num_tokens_by_prompt(json.dumps(FUNCTIONS, ensure_ascii=False))

    def __init__(self, client_openai):
        self.history_dict: Dict[str, List[Dict[str, str]]] = {}
        self.client_openai = client_openai


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
            "search_results": search_results,
            "current_time": datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        }

    def get_slack_search_result(self, query, client):
        """Slack検索を実行する、Function Calling用実装"""
        search_response = client.search_messages(token=os.getenv("SLACK_USER_TOKEN"),
                                                 query=query, count=100, highlight=False)

        matches = search_response["messages"]["matches"]
        filterd_matches = []
        for match in matches:  # パブリックのチャンネルのメッセージのみを抽出
            if match["channel"]["is_private"] == False and match["channel"]["is_mpim"] == False:
                # JSONが大きいため、トークン数節約のため情報を絞る
                # 参考: https://api.slack.com/methods/search.messages
                filterd_matches.append({
                    "channel_id": match["channel"]["id"],
                    "channel_name": match["channel"]["name"],
                    "text":  match["text"],
                    "timestamp": datetime.fromtimestamp(float(match["ts"])).strftime("%Y/%m/%d %H:%M:%S"),
                    "user_id": match["user"]  # usernameは古いデフォルト名なため入れない
                })
            
            if len(filterd_matches) >= 20: # 利用トークン節約のため含めるメッセージ数を制限
                break

        return {
            "search_results": filterd_matches,
            "current_time": datetime.now().strftime("%Y/%m/%d %H:%M:%S")
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
            messege_out_of_token_size = f"発言内容のトークン数が{self.INPUT_MAX_TOKEN_SIZE}を超えて、いたため対応できませんでした。"
            say_ts(client, message, messege_out_of_token_size)
            logger.info(messege_out_of_token_size)
            return

        say_ts(client, message,
               f"<@{message['user']}> さんの以下の発言に対応中（履歴数: {len(history_array)} 、トークン数: {calculate_num_tokens(history_array)}）\n```\n{prompt}\n```")

        # ChatCompletionを呼び出す
        logger.info(f"user: {message['user']}, prompt: {prompt}")
        response = self.client_openai.chat.completions.create(
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
        new_response_message = response.choices[0].message
        history_array.append(new_response_message)

        # もしFunction Callingがあれば再度問い合わせる
        if new_response_message.function_call:
            function_name = new_response_message.function_call.name
            function_response = []
            search_results = []

            function_args = json.loads(
                new_response_message.function_call.arguments)
            query = function_args.get("query")
            say_ts(client, message,
                   f"関数 `{function_name}` を引数 `query={query}` で呼び出し中...")

            # Function Callingの実行
            if function_name == "get_web_search_result":
                function_response = self.get_web_search_result(query)
                search_results = function_response["search_results"]

                link_references = []
                for idx, result in enumerate(search_results):
                    domain_name = urllib3.util.parse_url(result["href"]).host
                    link_references.append(
                        f"{idx+1}. <{result['href']}|{domain_name}>\n")
                link_references = "\n\n" + "".join(link_references)
                say_ts(client, message,
                       f"以下のWeb検索の結果を参考に返答します。" + link_references)

            elif function_name == "get_slack_search_result":
                function_response = self.get_slack_search_result(query, client)
                search_results = function_response["search_results"]
                say_ts(client, message,
                       f"{len(search_results)}件のSlack検索の結果が見つかりました。")

            function_json_content = json.dumps(function_response)
            # 検索結果全体でMAX_TOKEN_SIZEを超えたら、検索結果を減らす
            while calculate_num_tokens_by_prompt(function_json_content) > self.COMPLETION_MAX_TOKEN_SIZE:
                search_results = search_results[:-1]
                function_response["search_results"] = search_results
                function_json_content = json.dumps(function_response)

            # 単一検索結果でMAX_TOKEN_SIZEを超えるような検索結果が0件なら返答できない(Slackでも1メッセージ4000文字なのでないはず...)
            if len(search_results) == 0:
                no_result_message = "検索結果が0件であったため返答できませんでした。別の質問に変更をお願いします。"
                say_ts(client, message, no_result_message)
                history_array.append({
                    "role": "assistant",
                    "content": no_result_message,
                })
                return

            # 関数呼び出しの結果をヒストリーに追加
            history_array.append({
                "role": "function",
                "name": function_name,
                "content": function_json_content,  # JSON文字列
            })

            # トークンのサイズがINPUT_MAX_TOKEN_SIZEを超えたら古いものを削除
            while calculate_num_tokens(history_array) > self.INPUT_MAX_TOKEN_SIZE:
                history_array = history_array[1:]

            # 検索結果が大きくのでMAX_TOKEN_SIZEを超えたら、対応できない
            if (len(history_array) == 0):
                messege_out_of_token_size = f"検索結果のトークン数が{self.INPUT_MAX_TOKEN_SIZE}を超えていたため、対応できませんでした。"
                say_ts(client, message, messege_out_of_token_size)
                logger.info(messege_out_of_token_size)
                self.execute_reset(client, message, say, context, logger) # 対応できないためリセットをしてしまう
                return

            # ChatCompletionを呼び出す
            response = self.client_openai.chat.completions.create(
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
            new_response_message = response.choices[0].message
            history_array.append(new_response_message)

        # トークンのサイズがINPUT_MAX_TOKEN_SIZEを超えたら古いものを削除
        while calculate_num_tokens(history_array) > self.INPUT_MAX_TOKEN_SIZE:
            history_array = history_array[1:]
        self.history_dict[history_idetifier] = history_array  # ヒストリーを更新

        say_ts(client, message, new_response_message.content)
        logger.info(
            f"user: {message['user']}, content: {new_response_message.content}")

    def execute_reset(self, client, message, say, context, logger):
        """ChatGPT Function Callingを使った会話履歴のリセットをするコマンドの実行メソッド"""
        using_team = message["team"]
        using_channel = message["channel"]
        historyIdetifier = get_history_identifier(
            using_team, using_channel, message["user"])

        # 履歴をリセットをする
        self.history_dict[historyIdetifier] = []

        logger.info(
            f"<@{message['user']}> さんの <#{using_channel}> での会話の履歴をリセットしました。")
        say_ts(client, message,
               f"<@{message['user']}> さんの <#{using_channel}> での会話の履歴をリセットしました。")
