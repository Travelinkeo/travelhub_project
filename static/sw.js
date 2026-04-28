const CACHE_NAME = 'travelhub-cache-v1';
const urlsToCache = [
  '/',
  '/dashboard/modern/',
  '/static/images/Logo TravelHub.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response, otherwise fetch from network
        return response || fetch(event.request);
      })
  );
});
