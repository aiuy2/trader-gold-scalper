-- dev_seed.sql - local/dev-only sample data, safe to run repeatedly
-- (ON CONFLICT DO NOTHING). Never run this against a production database.
--
-- REPLACE_WITH_BCRYPT_HASH below is a placeholder, not a usable hash.
-- Generate a real one with the same scheme backend/app/security.py uses
-- (passlib "bcrypt"), then paste it in before running this file:
--   pip install passlib[bcrypt]
--   python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('password123'))"
-- Simplest alternative: skip this file and just POST /auth/register - it
-- hashes the password correctly for you and also seeds a trial license.

INSERT INTO users (email, hashed_password, full_name)
VALUES (
    'demo@tradergoldscalper.local',
    'REPLACE_WITH_BCRYPT_HASH',
    'Demo User'
)
ON CONFLICT (email) DO NOTHING;

INSERT INTO licenses (user_id, license_key, plan, is_active, expires_at)
SELECT id, 'DEMO-0000-0000-0001', 'trial', true, now() + interval '7 days'
FROM users WHERE email = 'demo@tradergoldscalper.local'
ON CONFLICT (license_key) DO NOTHING;

INSERT INTO bot_configs (user_id, symbol, lot_mode, fixed_lot, risk_percent, max_daily_loss, max_consecutive_losses, is_enabled)
SELECT id, 'XAUUSD', 'fixed', 0.01, 1.0, 5.0, 3, true
FROM users WHERE email = 'demo@tradergoldscalper.local'
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO devices (user_id, device_id, device_name, platform, is_trusted)
SELECT id, 'demo-device-0001', 'Demo iPhone', 'ios', true
FROM users WHERE email = 'demo@tradergoldscalper.local'
ON CONFLICT (user_id, device_id) DO NOTHING;
