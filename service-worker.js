// Lichi Hair — service worker (covers both / and /admin)
const CACHE = "lichi-v2";
const SHELL = ["/", "/admin", "/icon-192.png", "/icon-512.png", "/manifest.json", "/manifest-admin.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL).catch(()=>{})));
  self.skipWaiting();
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  if (req.url.includes("/api/")) {           // always fresh data
    e.respondWith(fetch(req).catch(() => caches.match(req)));
    return;
  }
  e.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req).then((res) => {
        if (res && res.status === 200 && res.type === "basic") {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      }).catch(() => cached);
      return cached || network;
    })
  );
});
