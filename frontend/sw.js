// sw.js — يخزّن هيكل الواجهة (HTML/CSS/JS) محلياً حتى يفتح التطبيق بسرعة.
// لا يخزّن أي بيانات من الـ API (الأسعار/الصفقات تبقى دائماً حية من السيرفر).
const CACHE_NAME = "trader-gold-scalper-shell-v1";
const SHELL_FILES = [
  "./",
  "./index.html",
  "./css/style.css",
  "./js/config.js",
  "./js/api.js",
  "./js/app.js",
  "./manifest.json",
  "./assets/icon.svg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_FILES)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // لا نتدخل أبداً في نداءات الـ API أو الـ WebSocket — فقط ملفات الواجهة الثابتة
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
