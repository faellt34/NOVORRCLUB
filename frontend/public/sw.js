// R-Conekta production: passive service worker. All pages and bundles use
// the browser's normal network loading; no stale JavaScript or HTML is served
// by this worker. P5 and all /api/ endpoints are never intercepted.
self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((key) =>
      key.startsWith("club-shell-") ||
      key.startsWith("rrclub-static-mobile3-")
    ).map((key) => caches.delete(key)));
    await self.clients.claim();
  })());
});
