// RRClub Mobile 3.0: prefer fresh network assets and never cache financial/API responses.
const CACHE = "rrclub-static-mobile3-v2-20261029";
const STATIC_PREFIX = "/static/";

self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(
      keys.filter((key) =>
        key !== CACHE &&
        (key.startsWith("club-shell-") || key.startsWith("rrclub-static-mobile3-"))
      ).map((key) => caches.delete(key))
    );
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;

  // SPA HTML is always obtained from the network: never serve a stale dashboard shell.
  // A financial app should not show an offline page as if it were the live site.
  if (request.mode === "navigate") {
    event.respondWith(fetch(request, { cache: "no-store" }));
    return;
  }

  // Only public, non-personal static assets may be stored for offline reuse.
  if (!url.pathname.startsWith(STATIC_PREFIX) &&
      url.pathname !== "/manifest.json" &&
      !/^\/icon-(192|512)\.png$/.test(url.pathname)) {
    return;
  }

  event.respondWith((async () => {
    try {
      const response = await fetch(request, { cache: "no-store" });
      if (response.ok && response.type === "basic") {
        const cache = await caches.open(CACHE);
        await cache.put(request, response.clone());
      }
      return response;
    } catch (error) {
      return (await caches.match(request)) || Response.error();
    }
  })());
});
