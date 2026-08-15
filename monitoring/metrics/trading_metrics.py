"""trading_metrics.py - performance metrics computed from the trades table
(win rate, total/average PnL, trade count), optionally scoped to a user
or worker and a time window. Takes the SQLAlchemy session + Trade model
as parameters, same pattern as worker_metrics.py.
"""


def collect(db, trade_model, user_id=None, worker_id=None, since=None):
    query = db.query(trade_model).filter(trade_model.closed_at.isnot(None))
    if user_id is not None:
        query = query.filter(trade_model.user_id == user_id)
    if worker_id is not None:
        query = query.filter(trade_model.worker_id == worker_id)
    if since is not None:
        query = query.filter(trade_model.closed_at >= since)

    trades = query.all()
    return summarize(trades)


def summarize(trades):
    """trades: iterable of objects/rows with a `.pnl` attribute (or dict
    with "pnl" key). Split out so it can be reused on already-fetched
    rows or on plain dicts (e.g. from the trade_logger JSON-lines file)."""
    pnls = [_pnl_of(t) for t in trades]
    pnls = [p for p in pnls if p is not None]

    if not pnls:
        return {
            "trade_count": 0, "win_count": 0, "loss_count": 0, "win_rate_pct": None,
            "total_pnl": 0.0, "average_pnl": None, "best_trade": None, "worst_trade": None,
        }

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    return {
        "trade_count": len(pnls),
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate_pct": round(len(wins) / len(pnls) * 100, 1),
        "total_pnl": round(sum(pnls), 2),
        "average_pnl": round(sum(pnls) / len(pnls), 2),
        "best_trade": round(max(pnls), 2),
        "worst_trade": round(min(pnls), 2),
    }


def _pnl_of(t):
    if isinstance(t, dict):
        return t.get("pnl")
    return getattr(t, "pnl", None)
