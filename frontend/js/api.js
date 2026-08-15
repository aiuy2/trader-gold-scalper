// api.js — طبقة الاتصال بين الواجهة والـ backend (FastAPI).
// كل شي هنا: تسجيل الدخول/الخروج، تجديد التوكن تلقائياً، ونداءات REST + WebSocket.

const API = (() => {
  const BASE = window.TRADER_CONFIG.API_URL;

  function getTokens() {
    return {
      access: localStorage.getItem("trader_access_token"),
      refresh: localStorage.getItem("trader_refresh_token"),
    };
  }

  function setTokens(access, refresh) {
    if (access) localStorage.setItem("trader_access_token", access);
    if (refresh) localStorage.setItem("trader_refresh_token", refresh);
  }

  function clearTokens() {
    localStorage.removeItem("trader_access_token");
    localStorage.removeItem("trader_refresh_token");
  }

  function isLoggedIn() {
    return !!getTokens().access;
  }

  async function refreshAccessToken() {
    const { refresh } = getTokens();
    if (!refresh) return false;
    try {
      const res = await fetch(`${BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      setTokens(data.access_token, data.refresh_token);
      return true;
    } catch {
      return false;
    }
  }

  // نداء عام يضيف رأس Authorization ويجدد التوكن تلقائياً عند انتهائه (401)
  async function request(path, { method = "GET", body, auth = true, retry = true } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (auth) {
      const { access } = getTokens();
      if (access) headers["Authorization"] = `Bearer ${access}`;
    }
    const res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    if (res.status === 401 && auth && retry) {
      const ok = await refreshAccessToken();
      if (ok) return request(path, { method, body, auth, retry: false });
      clearTokens();
      window.location.hash = "#/login";
      throw new Error("انتهت الجلسة، سجّل الدخول من جديد");
    }

    let data = null;
    try {
      data = await res.json();
    } catch {
      /* بدون محتوى */
    }
    if (!res.ok) {
      const message = (data && (data.detail || data.error)) || `خطأ (${res.status})`;
      throw new Error(typeof message === "string" ? message : JSON.stringify(message));
    }
    return data;
  }

  // --- المصادقة ---
  async function login(email, password) {
    const data = await request("/auth/login", { method: "POST", body: { email, password }, auth: false });
    setTokens(data.access_token, data.refresh_token);
    return data;
  }

  async function register(email, password, full_name) {
    const data = await request("/auth/register", { method: "POST", body: { email, password, full_name }, auth: false });
    setTokens(data.access_token, data.refresh_token);
    return data;
  }

  async function logout() {
    const { refresh } = getTokens();
    try {
      await request("/auth/logout", { method: "POST", body: { refresh_token: refresh } });
    } catch {
      /* نطلع من الحساب محلياً حتى لو فشل النداء */
    }
    clearTokens();
  }

  // --- البوت ---
  const startBot = (mode = "mock") => request("/bot/start", { method: "POST", body: { mode } });
  const stopBot = () => request("/bot/stop", { method: "POST" });
  const botStatus = () => request("/bot/status");
  const getBotConfig = () => request("/bot/config");
  const updateBotConfig = (payload) => request("/bot/config", { method: "PATCH", body: payload });

  // --- الإحصائيات / الصفقات / المراكز ---
  const statsSummary = () => request("/statistics/summary");
  const listPositions = () => request("/positions");
  const listTrades = (limit = 100) => request(`/trades?limit=${limit}`);
  const listHistory = (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/history${q ? "?" + q : ""}`);
  };

  // --- الترخيص ---
  const currentLicense = () => request("/licenses/current");
  const activateLicense = (license_key, plan) => request("/licenses/activate", { method: "POST", body: { license_key, plan } });

  // --- الحسابات (MT5) ---
  const listAccounts = () => request("/accounts");
  const linkAccount = (payload) => request("/accounts", { method: "POST", body: payload });
  const removeAccount = (id) => request(`/accounts/${id}`, { method: "DELETE" });

  // --- الإعدادات ---
  const getSettings = () => request("/settings");
  const updateSettings = (payload) => request("/settings", { method: "PATCH", body: payload });

  // --- الإشعارات ---
  const listNotifications = (unreadOnly = false) => request(`/notifications?unread_only=${unreadOnly}`);
  const markNotificationRead = (id) => request(`/notifications/${id}/read`, { method: "POST" });

  // --- WebSocket (تحديثات حية: صفقات، مراكز، حالة البوت) ---
  function connectSocket(onEvent) {
    const { access } = getTokens();
    if (!access) return null;
    const wsUrl = BASE.replace(/^http/, "ws") + `/ws?token=${encodeURIComponent(access)}`;
    let socket;
    try {
      socket = new WebSocket(wsUrl);
    } catch {
      return null;
    }
    socket.onopen = () => {
      socket.send(JSON.stringify({ subscribe: ["trades", "positions", "bot_status", "notifications"] }));
    };
    socket.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        onEvent(msg);
      } catch {
        /* تجاهل رسالة غير صالحة */
      }
    };
    return socket;
  }

  return {
    isLoggedIn, login, register, logout, clearTokens,
    startBot, stopBot, botStatus, getBotConfig, updateBotConfig,
    statsSummary, listPositions, listTrades, listHistory,
    currentLicense, activateLicense,
    listAccounts, linkAccount, removeAccount,
    getSettings, updateSettings,
    listNotifications, markNotificationRead,
    connectSocket,
  };
})();
