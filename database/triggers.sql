-- =====================================================================
-- TRADER GOLD SCALPER — Triggers & Functions (Supabase / PostgreSQL)
-- =====================================================================
-- شغّل بعد schema.sql. يغطي:
--   1) تحديث updated_at تلقائياً عند أي UPDATE.
--   2) إنشاء صفوف افتراضية (bot_configs / user_settings) تلقائياً عند
--      تسجيل مستخدم جديد، بدل ما الباك اند يسويها يدوياً بكل مكان.

-- ---------------------------------------------------------------------
-- 1) دالة عامة لتحديث updated_at
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_bot_configs_updated_at ON bot_configs;
CREATE TRIGGER trg_bot_configs_updated_at
    BEFORE UPDATE ON bot_configs
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_licenses_updated_at ON licenses;
CREATE TRIGGER trg_licenses_updated_at
    BEFORE UPDATE ON licenses
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------
-- 2) عند إنشاء مستخدم جديد بجدول users: نسوي له تلقائياً:
--    - صف user_settings بالإعدادات الافتراضية
--    - صف bot_configs بالإعدادات الافتراضية (بوت متوقف is_enabled=false
--      لحد ما يربط حساب MT5 ويفعّله بنفسه من التطبيق)
--    - ترخيص تجريبي (trial) لمدة 7 أيام يبدأ فور التسجيل
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_settings (user_id)
    VALUES (NEW.id)
    ON CONFLICT (user_id) DO NOTHING;

    INSERT INTO bot_configs (user_id, is_enabled)
    VALUES (NEW.id, false)
    ON CONFLICT (user_id) DO NOTHING;

    INSERT INTO licenses (user_id, license_key, plan, is_active, expires_at)
    VALUES (
        NEW.id,
        'TRIAL-' || UPPER(SUBSTRING(MD5(NEW.email || now()::text) FOR 12)),
        'trial',
        true,
        now() + INTERVAL '7 days'
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_handle_new_user ON users;
CREATE TRIGGER trg_handle_new_user
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user();

-- ---------------------------------------------------------------------
-- 3) عند إغلاق صفقة (تحديث closed_at) نولّد إشعار trade_closed تلقائياً
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION notify_trade_closed()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.closed_at IS NOT NULL AND OLD.closed_at IS NULL THEN
        INSERT INTO notifications (user_id, type, title, message)
        VALUES (
            NEW.user_id,
            'trade_closed',
            'تم إغلاق صفقة',
            format(
                '%s %s بلوت %s — النتيجة: %s',
                NEW.symbol,
                CASE NEW.direction WHEN 'buy' THEN 'شراء' WHEN 'sell' THEN 'بيع' ELSE NEW.direction END,
                COALESCE(NEW.lot::text, '-'),
                COALESCE(ROUND(NEW.pnl::numeric, 2)::text, '-')
            )
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notify_trade_closed ON trades;
CREATE TRIGGER trg_notify_trade_closed
    AFTER UPDATE ON trades
    FOR EACH ROW
    EXECUTE FUNCTION notify_trade_closed();
