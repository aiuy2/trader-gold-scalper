-- =====================================================================
-- TRADER GOLD SCALPER — Views (Supabase / PostgreSQL)
-- =====================================================================
-- شغّل بعد schema.sql. هذي Views جاهزة تسهّل على statistics_service.py
-- و لوحة الأدمن استعلامات ما تحتاج حساب Python يدوي.

-- ---------------------------------------------------------------------
-- v_daily_pnl — ملخص الربح/الخسارة اليومي لكل مستخدم (لحارس daily_loss
-- المستقبلي المبني على قاعدة البيانات، وشاشة الإحصائيات بالموبايل)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_daily_pnl AS
SELECT
    user_id,
    (closed_at AT TIME ZONE 'UTC')::date AS trade_date,
    COUNT(*)                              AS trades_count,
    COUNT(*) FILTER (WHERE pnl > 0)       AS wins,
    COUNT(*) FILTER (WHERE pnl < 0)       AS losses,
    COALESCE(SUM(pnl), 0)                 AS total_pnl,
    COALESCE(MAX(pnl), 0)                 AS best_trade,
    COALESCE(MIN(pnl), 0)                 AS worst_trade
FROM trades
WHERE closed_at IS NOT NULL
GROUP BY user_id, (closed_at AT TIME ZONE 'UTC')::date;

-- ---------------------------------------------------------------------
-- v_user_statistics — نفس منطق StatisticsService.summary() لكن كـ SQL،
-- يقدر الباك اند يستخدمها مباشرة بدل ما يسحب كل الصفوف لبايثون
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_user_statistics AS
SELECT
    user_id,
    COUNT(*)                                                    AS total_trades,
    ROUND(
        (COUNT(*) FILTER (WHERE pnl > 0))::numeric
        / NULLIF(COUNT(*), 0) * 100, 2
    )                                                            AS win_rate,
    ROUND(COALESCE(SUM(pnl), 0)::numeric, 2)                     AS total_pnl,
    ROUND(COALESCE(AVG(pnl), 0)::numeric, 2)                     AS average_pnl,
    ROUND(COALESCE(MAX(pnl), 0)::numeric, 2)                     AS best_trade,
    ROUND(COALESCE(MIN(pnl), 0)::numeric, 2)                     AS worst_trade
FROM trades
WHERE pnl IS NOT NULL
GROUP BY user_id;

-- ---------------------------------------------------------------------
-- v_open_positions_summary — عدد ولوت الصفقات المفتوحة حالياً لكل مستخدم
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_open_positions_summary AS
SELECT
    user_id,
    COUNT(*)                    AS open_positions_count,
    COALESCE(SUM(lot), 0)       AS total_lot_exposure,
    COUNT(*) FILTER (WHERE direction = 'buy')  AS buy_count,
    COUNT(*) FILTER (WHERE direction = 'sell') AS sell_count
FROM positions
GROUP BY user_id;

-- ---------------------------------------------------------------------
-- v_active_workers — العامل (worker) الحالي الشغّال لكل مستخدم، إن وجد
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_active_workers AS
SELECT DISTINCT ON (user_id)
    id AS worker_id, user_id, symbol, status, mode, started_at
FROM trading_workers
WHERE status = 'running'
ORDER BY user_id, started_at DESC NULLS LAST;

-- ---------------------------------------------------------------------
-- v_user_dashboard — كل شي شاشة الداشبورد بالموبايل تحتاجه بـ query واحد
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_user_dashboard AS
SELECT
    u.id AS user_id,
    u.email,
    bc.symbol,
    bc.is_enabled,
    aw.status  AS worker_status,
    aw.mode    AS worker_mode,
    COALESCE(ops.open_positions_count, 0) AS open_positions_count,
    COALESCE(ops.total_lot_exposure, 0)   AS total_lot_exposure,
    COALESCE(us_stats.total_pnl, 0)       AS total_pnl,
    COALESCE(us_stats.win_rate, 0)        AS win_rate,
    COALESCE(dp.total_pnl, 0)             AS today_pnl,
    l.plan       AS license_plan,
    l.is_active  AS license_active,
    l.expires_at AS license_expires_at
FROM users u
LEFT JOIN bot_configs bc          ON bc.user_id = u.id
LEFT JOIN v_active_workers aw     ON aw.user_id = u.id
LEFT JOIN v_open_positions_summary ops ON ops.user_id = u.id
LEFT JOIN v_user_statistics us_stats   ON us_stats.user_id = u.id
LEFT JOIN v_daily_pnl dp
       ON dp.user_id = u.id AND dp.trade_date = (now() AT TIME ZONE 'UTC')::date
LEFT JOIN licenses l ON l.user_id = u.id AND l.is_active = true;
