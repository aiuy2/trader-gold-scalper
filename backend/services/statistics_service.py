"""statistics_service.py - aggregates the trades table into dashboard stats
(win rate, total P&L, average trade, best/worst) for the current user."""
from database.database import SessionLocal
from database.repositories import trades as trades_repo


class StatisticsService:
    @staticmethod
    def summary(user_id: int) -> dict:
        db = SessionLocal()
        try:
            trades = [
                t for t in trades_repo.list_for_user(db, user_id, limit=10_000)
                if t.pnl is not None
            ]
        finally:
            db.close()

        total_trades = len(trades)
        if total_trades == 0:
            return {
                "total_trades": 0, "win_rate": 0, "total_pnl": 0,
                "average_pnl": 0, "best_trade": 0, "worst_trade": 0,
            }

        pnls = [t.pnl for t in trades]
        wins = [p for p in pnls if p > 0]
        return {
            "total_trades": total_trades,
            "win_rate": round(len(wins) / total_trades * 100, 2),
            "total_pnl": round(sum(pnls), 2),
            "average_pnl": round(sum(pnls) / total_trades, 2),
            "best_trade": round(max(pnls), 2),
            "worst_trade": round(min(pnls), 2),
        }
