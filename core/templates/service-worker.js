// SERVICE WORKER KILL SWITCH v2.0
// Forces all clients to unregister and clear caches to solve dashboard "stuck" issues.

self.addEventListener('install', (event) => {
  self.skipWaiting(); // Force active immediately
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          return caches.delete(cacheName); // Wipe ALL caches
        })
      );
    }).then(() => {
      return self.registration.unregister(); // Kill itself
    }).then(() => {
      return self.clients.claim(); // Take control and force reload
    })
  );
});

// Fallback to network only while dying
self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request));
});
