import sqlite3
from datetime import datetime
from enum import Enum

class Usage_Logs:
    '''
    ユーザーの利用ログを保存、取得するActiveRecordタイプの実装クラス

    基本ログの挿入と読み取りのみのため、マルチスレッドからの同時アクセスであっても
    そこまで大きな問題は起こらない想定。
    またこのクラスのインスタンスを一度でも作ったら、それ以降は同じインスタンスを使い回すことを想定している。
    よってDBのクローズは行わない。
    '''
    def __init__(self, db_name='slackbot.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_table()

    def create_table(self):
        c = self.conn.cursor()

        # テーブルが存在しない場合のみ新規作成
        c.execute('''
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date text,
                user_id text,
                command_type text,
                created_at text
            )
        ''')
        
        # (date, user_id)にインデックスを作成
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_date_user ON usage_logs (date, user_id)
        ''')

        self.conn.commit()

    def save(self, user_id, command_type):
        c = self.conn.cursor()
        
        # 現在日時を取得
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        date = datetime.now().strftime('%Y-%m-%d')

        # データの挿入
        c.execute('''
            INSERT INTO usage_logs (date, user_id, command_type, created_at)
            VALUES (?, ?, ?, ?)
        ''', (date, user_id, command_type, now))
        
        self.conn.commit()
    
    def get_num_logs(self, user_id):
        c = self.conn.cursor()

        # 本日の日付を取得
        date = datetime.now().strftime('%Y-%m-%d')

        # 本日の利用数を取得
        c.execute('''
            SELECT COUNT(*)
            FROM usage_logs
            WHERE date = ? AND user_id = ?
        ''', (date, user_id))

        count = c.fetchone()[0]

        return count

    def close(self):
        self.conn.close()


class Command_Type(Enum):
    '''
    ユーザーの利用ログのコマンドタイプ
    '''
    GPT = 'gpt'
    GPT_UA = 'gpt-ua'
    GPT_CA = 'gpt-ca'
    GPT_W = 'gpt-w'
    GPT_Q = 'gpt-q'
    GPT_4 = 'gpt-4'
    GPT_4V = 'gpt-4v'
    