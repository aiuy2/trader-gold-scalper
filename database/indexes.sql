-- =====================================================================
-- TRADER GOLD SCALPER — Indexes (Supabase / PostgreSQL)
-- =====================================================================
-- شغّل هذا الملف بعد schema.sql. كل الفهارس هنا تخدم أنماط الاستعلام
-- الفعلية بالباك اند (backend/database/repositories/*.py و api/*.py).

-- licenses: تحقق الترخيص بالـ license_key، وجلب ترخيص المستخدم
CREATE INDEX IF NOT EXISTS idx_licenses_user_id       ON licenses (user_id);
CREATE INDEX IF NOT EXISTS idx_licenses_active_expiry  ON licenses (is_active, expires_at);

-- devices: تحقق device binding بأسرع شكل
CREATE INDEX IF NOT EXISTS idx_devices_user_id   ON devices (user_id);
CREATE INDEX IF NOT EXISTS idx_devices_device_id ON devices (device_id);

-- mt5_accounts: حسابات المستخدم النشطة
CREATE INDEX IF NOT EXISTS idx_mt5_accounts_user_id   ON mt5_accounts (user_id);
CREATE INDEX IF NOT EXISTS idx_mt5_accounts_is_active ON mt5_accounts (user_id, is_active);

-- trading_workers: آخر/حالة العامل الحالي لكل مستخدم (يُستعلم كل تشغيل/إيقاف)
CREATE INDEX IF NOT EXISTS idx_workers_user_status ON trading_workers (user_id, status);
CREATE INDEX IF NOT EXISTS idx_workers_created_at  ON trading_workers (created_at DESC);

-- positions: قائمة الصفقات المفتوحة لكل مستخدم (يُستعلم باستمرار من الداشبورد)
CREATE INDEX IF NOT EXISTS idx_positions_user_id   ON positions (user_id);
CREATE INDEX IF NOT EXISTS idx_positions_worker_id ON positions (worker_id);
CREATE INDEX IF NOT EXISTS idx_positions_ticket    ON positions (ticket);

-- trades: سجل الصفقات + الإحصائيات (فرز حسب تاريخ الإغلاق دائماً)
CREATE INDEX IF NOT EXISTS idx_trades_user_id       ON trades (user_id);
CREATE INDEX IF NOT EXISTS idx_trades_worker_id     ON trades (worker_id);
CREATE INDEX IF NOT EXISTS idx_trades_closed_at     ON trades (closed_at DESC);
CREATE INDEX IF NOT EXISTS idx_trades_user_closed   ON trades (user_id, closed_at DESC);
CREATE INDEX IF NOT EXISTS idx_trades_open_only     ON trades (user_id) WHERE closed_at IS NULL;

-- notifications: صندوق الوارد (غير مقروء أولاً، الأحدث أولاً)
CREATE INDEX IF NOT EXISTS idx_notifications_user_id    ON notifications (user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications (user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications (created_at DESC);
