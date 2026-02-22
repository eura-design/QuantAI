import sqlite3
from contextlib import contextmanager

DB_NAME = "quant_v2.db"
DB_TIMEOUT = 10.0

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=DB_TIMEOUT)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        # 채팅 메시지 테이블
        c.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                sender TEXT, 
                text TEXT, 
                timestamp TEXT
            )
        """)
        
        # 전략 히스토리 테이블
        c.execute("""
            CREATE TABLE IF NOT EXISTS strategy_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                price REAL, 
                strategy TEXT, 
                generated_at TEXT, 
                funding_rate REAL, 
                open_interest REAL, 
                lang TEXT DEFAULT 'ko', 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 가상 매매 테이블
        c.execute("""
            CREATE TABLE IF NOT EXISTS virtual_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                side TEXT,
                entry REAL,
                tp REAL,
                sl REAL,
                status TEXT DEFAULT 'OPEN',
                close_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
