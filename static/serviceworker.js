const CACHE_NAME = 'travelhub-cache-v1';
const STATIC_CACHE_URLS = [
  '/static/core/css/responsive.css',
  '/static/core/css/tailwind-built.css',
  '/static/vendor/htmx_v2.js',
  '/static/manifest.json'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_CACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.filter(name => name !== CACHE_NAME)
          .map(name => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const requestUrl = new URL(event.request.url);

  // Network-first for /api/
  if (requestUrl.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const resClone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, resClone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Cache-first for /static/
  if (requestUrl.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then(response => {
        return response || fetch(event.request).then(netResponse => {
          const resClone = netResponse.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, resClone));
          return netResponse;
        });
      })
    );
    return;
  }

  // Default network-first for navigation/other requests
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
