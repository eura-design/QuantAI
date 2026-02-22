from .database import get_db

class MessageRepository:
    @staticmethod
    def get_recent_messages(limit=50):
        with get_db() as conn:
            rows = conn.execute(
                "SELECT sender, text, timestamp FROM messages ORDER BY id ASC LIMIT ?", 
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def add_message(sender, text, timestamp):
        with get_db() as conn:
            conn.execute(
                "INSERT INTO messages (sender, text, timestamp) VALUES (?, ?, ?)",
                (sender, text, timestamp)
            )
            conn.commit()

class StrategyRepository:
    @staticmethod
    def get_latest_strategy(lang):
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM strategy_history WHERE lang = ? ORDER BY id DESC LIMIT 1",
                (lang,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def add_strategy(price, strategy, generated_at, funding_rate, open_interest, lang):
        with get_db() as conn:
            conn.execute(
                "INSERT INTO strategy_history (price, strategy, generated_at, funding_rate, open_interest, lang) VALUES (?,?,?,?,?,?)",
                (price, strategy, generated_at, funding_rate, open_interest, lang)
            )
            conn.commit()

class TradeRepository:
    @staticmethod
    def get_pending_trades():
        with get_db() as conn:
            rows = conn.execute("SELECT id, side, entry FROM virtual_trades WHERE status='PENDING'").fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_open_trades():
        with get_db() as conn:
            rows = conn.execute("SELECT id, side, tp, sl FROM virtual_trades WHERE status='OPEN'").fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def update_trade_status(trade_id, status, close_price=None):
        with get_db() as conn:
            if close_price is not None:
                conn.execute(
                    "UPDATE virtual_trades SET status=?, close_price=? WHERE id=?",
                    (status, close_price, trade_id)
                )
            else:
                conn.execute(
                    "UPDATE virtual_trades SET status=? WHERE id=?",
                    (status, trade_id)
                )
            conn.commit()

    @staticmethod
    def get_stats():
        with get_db() as conn:
            wins = conn.execute("SELECT COUNT(*) FROM virtual_trades WHERE status='WIN'").fetchone()[0]
            losses = conn.execute("SELECT COUNT(*) FROM virtual_trades WHERE status='LOSS'").fetchone()[0]
            total = wins + losses
            win_rate = (wins / total * 100) if total > 0 else 0
            return wins, losses, round(win_rate, 1)

    @staticmethod
    def get_history(limit=10):
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM virtual_trades ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_active_trade():
        """현재 진행 중인(OPEN) 포지션 확인"""
        with get_db() as conn:
            row = conn.execute("SELECT id FROM virtual_trades WHERE status='OPEN'").fetchone()
            return dict(row) if row else None

    @staticmethod
    def upsert_pending_trade(side, entry, tp, sl):
        """PENDING 주문 생성 또는 갱신"""
        with get_db() as conn:
            pending = conn.execute("SELECT id FROM virtual_trades WHERE status='PENDING'").fetchone()
            if pending:
                conn.execute(
                    "UPDATE virtual_trades SET side=?, entry=?, tp=?, sl=? WHERE id=?",
                    (side, entry, tp, sl, pending['id'])
                )
            else:
                conn.execute(
                    "INSERT INTO virtual_trades (side, entry, tp, sl, status) VALUES (?, ?, ?, ?, 'PENDING')",
                    (side, entry, tp, sl)
                )
            conn.commit()

    @staticmethod
    def get_current_status():
        """현재 매매 상태 판단: OPEN > PENDING > IDLE"""
        with get_db() as conn:
            # 1. OPEN 확인
            row = conn.execute("SELECT id FROM virtual_trades WHERE status='OPEN'").fetchone()
            if row: return "OPEN"
            
            # 2. PENDING 확인
            row = conn.execute("SELECT id FROM virtual_trades WHERE status='PENDING'").fetchone()
            if row: return "PENDING"
            
            return "IDLE"

    @staticmethod
    def delete_pending_trades():
        with get_db() as conn:
            conn.execute("DELETE FROM virtual_trades WHERE status='PENDING'")
            conn.commit()
