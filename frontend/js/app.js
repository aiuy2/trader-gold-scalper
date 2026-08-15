// app.js — التوجيه بين الشاشات + رسم كل شاشة + الربط بالـ API.

const NAV_ITEMS = [
  { hash: "#/dashboard", label: "لوحة التحكم", icon: "◈" },
  { hash: "#/trades", label: "الصفقات", icon: "≡" },
  { hash: "#/settings", label: "الإعدادات", icon: "⚙" },
  { hash: "#/license", label: "الترخيص", icon: "◆" },
];

const state = {
  socket: null,
  pollTimer: null,
};

function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

function showToast(message, kind = "ok") {
  const stack = document.getElementById("toast-stack");
  const toast = el(`<div class="toast ${kind === "err" ? "err" : "ok"}">${message}</div>`);
  stack.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function fmtMoney(n) {
  if (n === null || n === undefined) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${Number(n).toFixed(2)}`;
}

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("ar-EG", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

/* ==========================================================================
   التوجيه
   ========================================================================== */

function currentRoute() {
  return window.location.hash || "#/dashboard";
}

async function router() {
  const hash = currentRoute();

  if (!API.isLoggedIn()) {
    renderAuthShell(hash === "#/register" ? "register" : "login");
    return;
  }

  if (hash === "#/login" || hash === "#/register") {
    window.location.hash = "#/dashboard";
    return;
  }

  renderAppShell(hash);

  try {
    if (hash.startsWith("#/trades")) await renderTrades();
    else if (hash.startsWith("#/settings")) await renderSettings();
    else if (hash.startsWith("#/license")) await renderLicense();
    else await renderDashboard();
  } catch (err) {
    showToast(err.message || "صار خطأ غير متوقع", "err");
  }

  ensureLiveConnection();
}

window.addEventListener("hashchange", router);

/* ==========================================================================
   شاشة الدخول / التسجيل
   ========================================================================== */

function renderAuthShell(mode) {
  const root = document.getElementById("root");
  const isRegister = mode === "register";
  root.innerHTML = "";
  root.appendChild(el(`
    <div class="auth-shell">
      <div class="auth-card">
        <div class="auth-brand">
          <div class="mark">TRADER <span>GOLD</span> SCALPER</div>
          <div class="sub-ar" style="margin-top:4px;">بوت تاجر لسكالب الذهب — XAUUSD</div>
        </div>
        <div id="auth-error" class="hidden auth-error"></div>
        <form id="auth-form">
          ${isRegister ? `
            <div class="field">
              <label>الاسم الكامل</label>
              <input type="text" name="full_name" autocomplete="name" />
            </div>` : ""}
          <div class="field">
            <label>البريد الإلكتروني</label>
            <input type="email" name="email" required autocomplete="email" />
          </div>
          <div class="field">
            <label>كلمة المرور</label>
            <input type="password" name="password" required autocomplete="${isRegister ? "new-password" : "current-password"}" minlength="6" />
          </div>
          <button type="submit" class="btn btn-gold btn-block">${isRegister ? "إنشاء حساب" : "تسجيل الدخول"}</button>
        </form>
        <div class="auth-switch">
          ${isRegister
            ? `عندك حساب؟ <a href="#/login">سجّل دخولك</a>`
            : `حساب جديد؟ <a href="#/register">أنشئ حساب مجاني</a>`}
        </div>
        <div class="auth-note">يبدأ كل حساب جديد بترخيص تجريبي مجاني لمدة 7 أيام.</div>
      </div>
    </div>
  `));

  document.getElementById("auth-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const errBox = document.getElementById("auth-error");
    errBox.classList.add("hidden");
    const fd = new FormData(e.target);
    const submitBtn = e.target.querySelector("button[type=submit]");
    submitBtn.disabled = true;
    try {
      if (isRegister) {
        await API.register(fd.get("email"), fd.get("password"), fd.get("full_name") || null);
      } else {
        await API.login(fd.get("email"), fd.get("password"));
      }
      window.location.hash = "#/dashboard";
      router();
    } catch (err) {
      errBox.textContent = err.message;
      errBox.classList.remove("hidden");
    } finally {
      submitBtn.disabled = false;
    }
  });
}

/* ==========================================================================
   هيكل التطبيق (الشريط الجانبي + شريط السعر)
   ========================================================================== */

function navHtml(activeHash, mobile = false) {
  return NAV_ITEMS.map(item => `
    <div class="nav-item ${item.hash === activeHash ? "active" : ""}" data-hash="${item.hash}">
      <span class="nav-icon">${item.icon}</span>
      ${mobile ? "" : `<span>${item.label}</span>`}
      ${mobile ? `<span style="font-size:10px;">${item.label}</span>` : ""}
    </div>
  `).join("");
}

function renderAppShell(activeHash) {
  const root = document.getElementById("root");
  root.innerHTML = "";
  const shell = el(`
    <div id="app-shell">
      <aside class="sidebar">
        <div class="sidebar-brand">
          <div class="mark">TRADER <span>GOLD</span></div>
          <div class="sub-ar">تاجر — بوت سكالب الذهب</div>
        </div>
        <nav>${navHtml(activeHash)}</nav>
        <div class="sidebar-foot">
          <div class="sidebar-user" id="sidebar-user">...</div>
          <button class="btn btn-outline btn-block" id="logout-btn">تسجيل الخروج</button>
        </div>
      </aside>
      <div class="main-area">
        <div class="ticker-bar">
          <span class="ticker-symbol">XAUUSD</span>
          <span class="ticker-dot" id="live-dot"></span>
          <span id="ticker-status">غير متصل</span>
          <span class="ticker-spacer"></span>
          <span class="ticker-note">TRADER GOLD SCALPER API</span>
        </div>
        <main class="page" id="page"></main>
      </div>
      <nav class="mobile-nav">${navHtml(activeHash, true)}</nav>
    </div>
    <div class="toast-stack" id="toast-stack"></div>
  `);
  root.appendChild(shell);

  root.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => { window.location.hash = item.dataset.hash; });
  });
  document.getElementById("logout-btn").addEventListener("click", async () => {
    await API.logout();
    stopLiveConnection();
    window.location.hash = "#/login";
    router();
  });

  loadUserBadge();
}

async function loadUserBadge() {
  try {
    const res = await fetch(`${window.TRADER_CONFIG.API_URL}/users/me`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("trader_access_token")}` },
    });
    if (res.ok) {
      const me = await res.json();
      const badge = document.getElementById("sidebar-user");
      if (badge) badge.textContent = me.email || me.full_name || "";
    }
  } catch { /* تجاهل */ }
}

/* ==========================================================================
   لوحة التحكم
   ========================================================================== */

async function renderDashboard() {
  const page = document.getElementById("page");
  page.innerHTML = `<div class="page-head"><div><div class="page-title">لوحة التحكم</div><div class="page-sub">حالة البوت والأداء اليومي</div></div></div><div id="dash-body"></div>`;
  const body = document.getElementById("dash-body");
  body.innerHTML = `<div class="empty-state">جارِ التحميل…</div>`;

  const [status, stats, positions, config] = await Promise.all([
    API.botStatus().catch(() => ({ running: false })),
    API.statsSummary().catch(() => null),
    API.listPositions().catch(() => []),
    API.getBotConfig().catch(() => null),
  ]);

  const running = !!status.running;
  const stateClass = running ? "running" : "stopped";
  const dailyLossLimit = config ? config.max_daily_loss : null;
  const todayLoss = stats && stats.total_pnl < 0 ? Math.abs(stats.total_pnl) : 0;
  const lossPct = dailyLossLimit ? Math.min(100, (todayLoss / dailyLossLimit) * 100) : 0;

  body.innerHTML = `
    <div class="pulse-card">
      <div class="pulse-ring ${stateClass}"><div class="pulse-core">${running ? "▶" : "■"}</div></div>
      <div class="pulse-info">
        <div class="status-label">حالة البوت</div>
        <div class="status-value ${stateClass}">${running ? "يعمل الآن" : "متوقف"}</div>
        <div class="pulse-meta">الرمز: ${config ? config.symbol : "XAUUSD"} · الوضع: ${config && config.is_enabled === false ? "معطّل" : "mock (تجريبي)"}</div>
      </div>
      <div class="pulse-actions">
        <button class="btn btn-gold" id="btn-start" ${running ? "disabled" : ""}>تشغيل البوت</button>
        <button class="btn btn-danger" id="btn-stop" ${running ? "" : "disabled"}>إيقاف البوت</button>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card"><div class="stat-label">إجمالي الربح/الخسارة</div><div class="stat-value ${stats && stats.total_pnl >= 0 ? "pos" : "neg"}">${stats ? fmtMoney(stats.total_pnl) : "—"}</div></div>
      <div class="stat-card"><div class="stat-label">نسبة الصفقات الرابحة</div><div class="stat-value">${stats ? stats.win_rate + "%" : "—"}</div></div>
      <div class="stat-card"><div class="stat-label">عدد الصفقات</div><div class="stat-value">${stats ? stats.total_trades : "—"}</div></div>
      <div class="stat-card"><div class="stat-label">أفضل / أسوأ صفقة</div><div class="stat-value">${stats ? fmtMoney(stats.best_trade) : "—"} / ${stats ? fmtMoney(stats.worst_trade) : "—"}</div></div>
    </div>

    ${dailyLossLimit ? `
    <div class="gauge-card">
      <div class="gauge-head"><span>حد الخسارة اليومي</span><span>${todayLoss.toFixed(2)} / ${dailyLossLimit}</span></div>
      <div class="gauge-track"><div class="gauge-fill ${lossPct > 70 ? "danger" : ""}" style="width:${lossPct}%"></div></div>
    </div>` : ""}

    <div class="panel">
      <div class="panel-head">المراكز المفتوحة <span class="count">${positions.length}</span></div>
      ${positions.length ? `
        <table>
          <thead><tr><th>الاتجاه</th><th>اللوت</th><th>سعر الدخول</th><th>وقف الخسارة</th><th>جني الأرباح</th><th>الوقت</th></tr></thead>
          <tbody>
            ${positions.map(p => `
              <tr>
                <td><span class="dir-badge ${p.direction}">${p.direction === "buy" ? "شراء" : "بيع"}</span></td>
                <td>${p.lot}</td>
                <td>${p.entry_price}</td>
                <td>${p.stop_loss ?? "—"}</td>
                <td>${p.take_profit ?? "—"}</td>
                <td>${fmtDate(p.opened_at)}</td>
              </tr>`).join("")}
          </tbody>
        </table>` : `<div class="empty-state"><div class="glyph">◇</div>لا توجد مراكز مفتوحة حالياً</div>`}
    </div>
  `;

  document.getElementById("btn-start").addEventListener("click", async (e) => {
    e.target.disabled = true;
    try {
      const res = await API.startBot("mock");
      if (res.success === false) throw new Error(res.error || "تعذّر تشغيل البوت");
      showToast("تم تشغيل البوت");
      renderDashboard();
    } catch (err) {
      showToast(err.message, "err");
      e.target.disabled = false;
    }
  });
  document.getElementById("btn-stop").addEventListener("click", async (e) => {
    e.target.disabled = true;
    try {
      await API.stopBot();
      showToast("تم إيقاف البوت");
      renderDashboard();
    } catch (err) {
      showToast(err.message, "err");
      e.target.disabled = false;
    }
  });
}

/* ==========================================================================
   الصفقات
   ========================================================================== */

async function renderTrades() {
  const page = document.getElementById("page");
  page.innerHTML = `<div class="page-head"><div><div class="page-title">الصفقات</div><div class="page-sub">سجل الصفقات المغلقة</div></div></div><div id="trades-body"><div class="empty-state">جارِ التحميل…</div></div>`;

  const trades = await API.listTrades(100).catch(() => []);
  const body = document.getElementById("trades-body");

  body.innerHTML = `
    <div class="panel">
      <div class="panel-head">آخر الصفقات <span class="count">${trades.length}</span></div>
      ${trades.length ? `
        <table>
          <thead><tr><th>الاتجاه</th><th>اللوت</th><th>الدخول</th><th>الخروج</th><th>الربح/الخسارة</th><th>فُتحت</th><th>أُغلقت</th></tr></thead>
          <tbody>
            ${trades.map(t => `
              <tr>
                <td><span class="dir-badge ${t.direction}">${t.direction === "buy" ? "شراء" : "بيع"}</span></td>
                <td>${t.lot}</td>
                <td>${t.entry_price}</td>
                <td>${t.exit_price ?? "—"}</td>
                <td class="pnl ${t.pnl >= 0 ? "pos" : "neg"}">${t.pnl !== null && t.pnl !== undefined ? fmtMoney(t.pnl) : "—"}</td>
                <td>${fmtDate(t.opened_at)}</td>
                <td>${fmtDate(t.closed_at)}</td>
              </tr>`).join("")}
          </tbody>
        </table>` : `<div class="empty-state"><div class="glyph">≡</div>ما فيه صفقات مسجّلة بعد. شغّل البوت من لوحة التحكم عشان تبدأ.</div>`}
    </div>
  `;
}

/* ==========================================================================
   الإعدادات
   ========================================================================== */

async function renderSettings() {
  const page = document.getElementById("page");
  page.innerHTML = `<div class="page-head"><div><div class="page-title">الإعدادات</div><div class="page-sub">إدارة إعدادات البوت والمخاطرة وحسابات MT5</div></div></div><div id="settings-body"><div class="empty-state">جارِ التحميل…</div></div>`;

  const [config, accounts] = await Promise.all([
    API.getBotConfig().catch(() => null),
    API.listAccounts().catch(() => []),
  ]);
  const body = document.getElementById("settings-body");

  body.innerHTML = `
    <div class="panel">
      <div class="panel-head">إعدادات البوت والمخاطرة</div>
      <div class="panel-body">
        <form id="bot-config-form">
          <div class="form-grid">
            <div class="field"><label>الرمز</label><input type="text" name="symbol" value="${config?.symbol ?? "XAUUSD"}" /></div>
            <div class="field"><label>نمط اللوت</label>
              <select name="lot_mode">
                <option value="fixed" ${config?.lot_mode === "fixed" ? "selected" : ""}>ثابت</option>
                <option value="dynamic" ${config?.lot_mode === "dynamic" ? "selected" : ""}>ديناميكي</option>
              </select>
            </div>
            <div class="field"><label>اللوت الثابت</label><input type="number" step="0.01" name="fixed_lot" value="${config?.fixed_lot ?? 0.01}" /></div>
            <div class="field"><label>نسبة المخاطرة %</label><input type="number" step="0.1" name="risk_percent" value="${config?.risk_percent ?? 1}" /></div>
            <div class="field"><label>حد الخسارة اليومي</label><input type="number" step="0.1" name="max_daily_loss" value="${config?.max_daily_loss ?? 5}" /></div>
            <div class="field"><label>أقصى خسائر متتالية</label><input type="number" name="max_consecutive_losses" value="${config?.max_consecutive_losses ?? 3}" /></div>
          </div>
          <div class="toggle-row">
            <div><div class="t-label">تفعيل البوت</div><div class="t-desc">إيقافه هنا يمنع تشغيله حتى لو ضغطت "تشغيل" من لوحة التحكم</div></div>
            <label class="switch"><input type="checkbox" name="is_enabled" ${config?.is_enabled !== false ? "checked" : ""} /><span class="switch-track"></span></label>
          </div>
          <div style="margin-top:16px;"><button type="submit" class="btn btn-gold">حفظ الإعدادات</button></div>
        </form>
      </div>
    </div>

    <div class="panel">
      <div class="panel-head">حسابات MT5 <span class="count">${accounts.length}</span></div>
      ${accounts.length ? `
        <table>
          <thead><tr><th>تسجيل الدخول</th><th>السيرفر</th><th>الوسيط</th><th>النوع</th><th></th></tr></thead>
          <tbody>
            ${accounts.map(a => `
              <tr>
                <td>${a.login}</td>
                <td>${a.server}</td>
                <td>${a.broker || "—"}</td>
                <td>${a.is_live ? "حقيقي" : "تجريبي"}</td>
                <td><button class="btn btn-danger" style="padding:5px 10px;font-size:12px;" data-remove="${a.id}">إزالة</button></td>
              </tr>`).join("")}
          </tbody>
        </table>` : `<div class="empty-state">ما ربطت أي حساب MT5 بعد</div>`}
      <div class="panel-body">
        <form id="link-account-form">
          <div class="form-grid">
            <div class="field"><label>رقم الحساب (Login)</label><input type="text" name="login" required /></div>
            <div class="field"><label>كلمة مرور الحساب</label><input type="password" name="password" required /></div>
            <div class="field"><label>السيرفر</label><input type="text" name="server" required placeholder="مثال: ICMarkets-Demo" /></div>
            <div class="field"><label>الوسيط (اختياري)</label><input type="text" name="broker" /></div>
          </div>
          <div class="toggle-row" style="border-bottom:none;">
            <div><div class="t-label">حساب حقيقي (Live)</div><div class="t-desc">اتركه بدون تفعيل لحساب تجريبي (Demo)</div></div>
            <label class="switch"><input type="checkbox" name="is_live" /><span class="switch-track"></span></label>
          </div>
          <button type="submit" class="btn btn-outline">ربط الحساب</button>
        </form>
      </div>
    </div>
  `;

  document.getElementById("bot-config-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await API.updateBotConfig({
        symbol: fd.get("symbol"),
        lot_mode: fd.get("lot_mode"),
        fixed_lot: parseFloat(fd.get("fixed_lot")),
        risk_percent: parseFloat(fd.get("risk_percent")),
        max_daily_loss: parseFloat(fd.get("max_daily_loss")),
        max_consecutive_losses: parseInt(fd.get("max_consecutive_losses"), 10),
        is_enabled: fd.get("is_enabled") === "on",
      });
      showToast("تم حفظ إعدادات البوت");
    } catch (err) { showToast(err.message, "err"); }
  });

  document.getElementById("link-account-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await API.linkAccount({
        login: fd.get("login"), password: fd.get("password"), server: fd.get("server"),
        broker: fd.get("broker") || "", is_live: fd.get("is_live") === "on",
      });
      showToast("تم ربط الحساب");
      renderSettings();
    } catch (err) { showToast(err.message, "err"); }
  });

  body.querySelectorAll("[data-remove]").forEach(btn => {
    btn.addEventListener("click", async () => {
      try { await API.removeAccount(btn.dataset.remove); showToast("تمت إزالة الحساب"); renderSettings(); }
      catch (err) { showToast(err.message, "err"); }
    });
  });
}

/* ==========================================================================
   الترخيص
   ========================================================================== */

async function renderLicense() {
  const page = document.getElementById("page");
  page.innerHTML = `<div class="page-head"><div><div class="page-title">الترخيص</div><div class="page-sub">حالة اشتراكك وتفعيل مفتاح جديد</div></div></div><div id="license-body"><div class="empty-state">جارِ التحميل…</div></div>`;

  const lic = await API.currentLicense().catch(() => null);
  const body = document.getElementById("license-body");
  const isActive = lic && lic.is_active && (!lic.expires_at || new Date(lic.expires_at) > new Date());

  body.innerHTML = `
    <div class="panel">
      <div class="panel-head">الترخيص الحالي</div>
      <div class="panel-body">
        ${lic ? `
          <div class="field"><label>مفتاح الترخيص</label><div class="license-key">${lic.license_key}</div></div>
          <div class="form-grid" style="margin-top:14px;">
            <div><div class="stat-label">الخطة</div><div>${lic.plan}</div></div>
            <div><div class="stat-label">الحالة</div><div><span class="badge ${isActive ? "active" : "expired"}">${isActive ? "فعّال" : "منتهي"}</span></div></div>
            <div><div class="stat-label">تاريخ الانتهاء</div><div>${lic.expires_at ? fmtDate(lic.expires_at) : "بدون انتهاء"}</div></div>
          </div>
        ` : `<div class="empty-state">ما فيه ترخيص مفعّل على هذا الحساب</div>`}
      </div>
    </div>

    <div class="panel">
      <div class="panel-head">تفعيل مفتاح جديد</div>
      <div class="panel-body">
        <form id="activate-form">
          <div class="form-grid">
            <div class="field"><label>مفتاح الترخيص</label><input type="text" name="license_key" required placeholder="XXXX-XXXX-XXXX-XXXX" /></div>
            <div class="field"><label>الخطة</label>
              <select name="plan">
                <option value="monthly">شهري</option>
                <option value="yearly">سنوي</option>
                <option value="lifetime">مدى الحياة</option>
              </select>
            </div>
          </div>
          <button type="submit" class="btn btn-gold">تفعيل</button>
        </form>
      </div>
    </div>
  `;

  document.getElementById("activate-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const res = await API.activateLicense(fd.get("license_key"), fd.get("plan"));
      if (res.success === false) throw new Error(res.error || "تعذّر تفعيل المفتاح");
      showToast("تم تفعيل الترخيص");
      renderLicense();
    } catch (err) { showToast(err.message, "err"); }
  });
}

/* ==========================================================================
   الاتصال الحي (WebSocket) — تحديث الشريط + إشعارات فورية
   ========================================================================== */

function ensureLiveConnection() {
  if (state.socket && state.socket.readyState === WebSocket.OPEN) return;
  stopLiveConnection();

  const dot = document.getElementById("live-dot");
  const statusEl = document.getElementById("ticker-status");

  state.socket = API.connectSocket((msg) => {
    if (msg.type === "trade_opened") showToast(`صفقة جديدة: ${msg.data.direction === "buy" ? "شراء" : "بيع"} @ ${msg.data.entry_price}`);
    if (msg.type === "trade_closed") showToast(`أُغلقت صفقة — الربح/الخسارة: ${fmtMoney(msg.data.pnl)}`, msg.data.pnl >= 0 ? "ok" : "err");
    if (msg.type === "bot_status_changed" && currentRoute().startsWith("#/dashboard")) renderDashboard();
    if ((msg.type === "trade_opened" || msg.type === "trade_closed") && currentRoute().startsWith("#/dashboard")) renderDashboard();
  });

  if (!state.socket) return;
  state.socket.onopen = () => { if (dot) dot.classList.add("live"); if (statusEl) statusEl.textContent = "متصل — تحديثات حية"; };
  state.socket.onclose = () => { if (dot) dot.classList.remove("live"); if (statusEl) statusEl.textContent = "غير متصل"; };
  state.socket.onerror = () => { if (dot) dot.classList.remove("live"); };
}

function stopLiveConnection() {
  if (state.socket) { try { state.socket.close(); } catch { /* تجاهل */ } state.socket = null; }
}

/* ==========================================================================
   الإقلاع
   ========================================================================== */

window.addEventListener("DOMContentLoaded", () => {
  document.getElementById("boot-screen").remove();
  router();
});
