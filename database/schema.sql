-- =====================================================================
-- TRADER GOLD SCALPER — Database Schema (Supabase / PostgreSQL)
-- =====================================================================
-- شغّل هذا الملف كامل بـ Supabase SQL Editor (Project -> SQL Editor -> New query).
-- مطابق تماماً لأسماء الجداول والأعمدة الموجودة بـ backend/database/models/*.py
-- عشان SQLAlchemy يقدر يشتغل عليه مباشرة بدون تعديل.
--
-- ترتيب الجداول مهم بسبب الـ Foreign Keys (users أول شي).
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) users — مستخدمي التطبيق (تسجيل دخول JWT خاص بالباك اند، مو Supabase Auth)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL PRIMARY KEY,
    email           TEXT NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    full_name       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- 2) licenses — الاشتراك/الترخيص لكل مستخدم
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS licenses (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    license_key  TEXT NOT NULL UNIQUE,
    plan         TEXT NOT NULL DEFAULT 'trial',          -- trial | monthly | yearly | lifetime
    is_active    BOOLEAN NOT NULL DEFAULT true,
    expires_at   TIMESTAMPTZ,
    device_id    TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ,
    CONSTRAINT chk_license_plan CHECK (plan IN ('trial', 'monthly', 'yearly', 'lifetime'))
);

-- ---------------------------------------------------------------------
-- 3) devices — الأجهزة المسجّلة/الموثوقة لكل مستخدم (device binding)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS devices (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id   TEXT NOT NULL,           -- UUID ثابت يولّده التطبيق بالجهاز
    device_name TEXT,
    platform    TEXT,                    -- ios | android
    is_trusted  BOOLEAN NOT NULL DEFAULT true,
    last_seen   TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_device UNIQUE (user_id, device_id)
);

-- ---------------------------------------------------------------------
-- 4) mt5_accounts — حسابات MT5 المربوطة (الباسورد مشفّر دائماً)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mt5_accounts (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    login               TEXT NOT NULL,
    encrypted_password  TEXT NOT NULL,   -- مشفّر بـ backend/security/encryption.py، ما ينخزن نص صريح إطلاقاً
    server              TEXT NOT NULL,
    broker              TEXT,
    is_live             BOOLEAN NOT NULL DEFAULT false,
    is_active           BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- 5) bot_configs — إعدادات البوت الدائمة لكل مستخدم (صف واحد لكل يوزر)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bot_configs (
    id                       BIGSERIAL PRIMARY KEY,
    user_id                  BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    symbol                   TEXT NOT NULL DEFAULT 'XAUUSD',
    lot_mode                 TEXT NOT NULL DEFAULT 'fixed',   -- fixed | dynamic
    fixed_lot                DOUBLE PRECISION NOT NULL DEFAULT 0.01,
    risk_percent             DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    max_daily_loss           DOUBLE PRECISION NOT NULL DEFAULT 5.0,
    max_consecutive_losses   INTEGER NOT NULL DEFAULT 3,
    is_enabled               BOOLEAN NOT NULL DEFAULT true,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ,
    CONSTRAINT chk_lot_mode CHECK (lot_mode IN ('fixed', 'dynamic'))
);

-- ---------------------------------------------------------------------
-- 6) trading_workers — تشغيلة واحدة (run) من محرك التداول لمستخدم معيّن
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trading_workers (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol      TEXT NOT NULL DEFAULT 'XAUUSD',
    status      TEXT NOT NULL DEFAULT 'stopped',   -- stopped | running | error
    mode        TEXT NOT NULL DEFAULT 'mock',      -- mock | live
    started_at  TIMESTAMPTZ,
    stopped_at  TIMESTAMPTZ,
    last_error  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_worker_status CHECK (status IN ('stopped', 'running', 'error')),
    CONSTRAINT chk_worker_mode CHECK (mode IN ('mock', 'live'))
);

-- ---------------------------------------------------------------------
-- 7) positions — الصفقات المفتوحة حالياً (مرآة لحالة البروكر)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS positions (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    worker_id    BIGINT REFERENCES trading_workers(id) ON DELETE SET NULL,
    ticket       BIGINT NOT NULL,
    symbol       TEXT NOT NULL DEFAULT 'XAUUSD',
    direction    TEXT,                              -- buy | sell
    lot          DOUBLE PRECISION,
    entry_price  DOUBLE PRECISION,
    stop_loss    DOUBLE PRECISION,
    take_profit  DOUBLE PRECISION,
    opened_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_position_direction CHECK (direction IN ('buy', 'sell') OR direction IS NULL)
);

-- ---------------------------------------------------------------------
-- 8) trades — سجل الصفقات المغلقة (للتاريخ والإحصائيات)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trades (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    worker_id    BIGINT REFERENCES trading_workers(id) ON DELETE SET NULL,
    ticket       BIGINT,
    symbol       TEXT NOT NULL DEFAULT 'XAUUSD',
    direction    TEXT,                               -- buy | sell
    lot          DOUBLE PRECISION,
    entry_price  DOUBLE PRECISION,
    exit_price   DOUBLE PRECISION,
    stop_loss    DOUBLE PRECISION,
    take_profit  DOUBLE PRECISION,
    pnl          DOUBLE PRECISION,
    opened_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at    TIMESTAMPTZ,
    CONSTRAINT chk_trade_direction CHECK (direction IN ('buy', 'sell') OR direction IS NULL)
);

-- ---------------------------------------------------------------------
-- 9) user_settings — تفضيلات التطبيق والمخاطر لكل مستخدم (صف واحد لكل يوزر)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_settings (
    id                     BIGSERIAL PRIMARY KEY,
    user_id                BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    risk_percent           DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    max_daily_loss         DOUBLE PRECISION NOT NULL DEFAULT 5.0,
    notifications_enabled  BOOLEAN NOT NULL DEFAULT true,
    theme                  TEXT NOT NULL DEFAULT 'dark',
    language               TEXT NOT NULL DEFAULT 'ar',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- 10) notifications — إشعارات داخل التطبيق (صندوق وارد الموبايل)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type        TEXT NOT NULL,     -- trade_opened | trade_closed | risk_alert | mt5_disconnected | ...
    title       TEXT NOT NULL,
    message     TEXT NOT NULL,
    is_read     BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================
-- ملاحظة Row Level Security:
-- الباك اند (FastAPI) يتصل بقاعدة البيانات مباشرة عبر SQLAlchemy باستخدام
-- Connection String فيه صلاحيات كاملة (service role / postgres user)،
-- مو عبر Supabase REST/anon key من التطبيق مباشرة. لذلك RLS مو ضروري
-- لعمل الباك اند، لكن مفعّل هنا كطبقة حماية إضافية احتياطية.
-- شوف database/triggers.sql للـ triggers و database/indexes.sql للفهارس.
-- =====================================================================
ALTER TABLE users            ENABLE ROW LEVEL SECURITY;
ALTER TABLE licenses         ENABLE ROW LEVEL SECURITY;
ALTER TABLE devices          ENABLE ROW LEVEL SECURITY;
ALTER TABLE mt5_accounts     ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_configs      ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_workers  ENABLE ROW LEVEL SECURITY;
ALTER TABLE positions        ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades           ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings    ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications    ENABLE ROW LEVEL SECURITY;

-- الباك اند يتصل بـ service_role (أو postgres مباشرة) اللي يتخطى RLS تلقائياً.
-- ما فيه سياسات إضافية لأن ولا كلاينت خارجي (مثل Supabase JS) يوصل لهاي الجداول مباشرة.
