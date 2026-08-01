// TravelHub PWA — Service Worker v5
// Estrategias: Network First para HTML, Cache First para assets, Stale-While-Revalidate para HTMX
// Push notifications, Background Sync, offline indicator
// FIXED: respondWith siempre devuelve Response válida (nunca undefined)

const CACHE_NAME = 'travelhub-v11';
const STATIC_ASSETS = [
  '/offline/',
  '/static/core/css/tailwind-built.css',
  '/static/core/css/responsive.css',
  '/static/vendor/htmx_v2.js',
  '/static/vendor/alpine_v2.js',
  '/static/images_pwa/pwa-192x192.png',
  '/static/images_pwa/pwa-512x512.png',
  '/static/images_pwa/pwa-maskable-192x192.png',
  '/static/images_pwa/pwa-maskable-512x512.png',
];

// --- INSTALL ---
self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
});

// --- ACTIVATE ---
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// --- FETCH ---
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (url.origin !== self.location.origin) return;
  if (request.method !== 'GET') return;
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/admin/') || url.pathname.startsWith('/system/') || url.pathname.startsWith('/erp/')) return;

  // Navegación: Network First con fallback offline seguro (NUNCA devuelve undefined)
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(async () => {
        const offlinePage = await caches.match('/offline/');
        if (offlinePage) return offlinePage;
        return new Response(
          '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Offline</title></head><body style="font-family:sans-serif;text-align:center;padding:50px;"><h2>Sin conexión a Internet</h2><p>Comprueba tu conexión y vuelve a intentarlo.</p><button onclick="window.location.reload()">Reintentar</button></body></html>',
          { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
        );
      })
    );
    return;
  }

  // Assets estáticos: Cache First
  if (url.pathname.startsWith('/static/') || url.pathname.startsWith('/media/')) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response.status === 200) {
            return caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, response.clone());
              return response;
            });
          }
          return response;
        }).catch(() => new Response('', { status: 503, statusText: 'Service Unavailable' }));
      })
    );
    return;
  }

  // HTMX partials y demás peticiones: Stale-While-Revalidate
  // IMPORTANTE: respondWith SIEMPRE debe recibir una Response válida, nunca undefined.
  event.respondWith(
    caches.match(request).then((cached) => {
      const fetchPromise = fetch(request).then((response) => {
        if (response.status === 200) {
          return caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, response.clone());
            return response;
          });
        }
        return response;
      }).catch(() => {
        // Si la red falla y hay cache, úsalo; si no, devuelve 503 (nunca undefined)
        if (cached) return cached;
        return new Response('', { status: 503, statusText: 'Service Unavailable' });
      });
      return cached || fetchPromise;
    })
  );
});

// --- PUSH ---
self.addEventListener('push', (event) => {
  let data = { title: 'TravelHub', body: '', icon: '/static/images_pwa/pwa-192x192.png', badge: '/static/images_pwa/pwa-maskable-192x192.png' };
  if (event.data) {
    try {
      data = { ...data, ...JSON.parse(event.data.text()) };
    } catch {
      data.body = event.data.text();
    }
  }
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon,
      badge: data.badge,
      image: data.image || undefined,
      vibrate: [200, 100, 200],
      data: data.data || {},
      actions: data.actions || [],
      tag: data.tag || 'default',
      renotify: data.renotify || false,
      requireInteraction: data.requireInteraction || false,
    })
  );
});

// --- NOTIFICATION CLICK ---
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url === url && 'focus' in client) return client.focus();
      }
      return clients.openWindow(url);
    })
  );
});

// --- MESSAGE ---
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  if (event.data && event.data.type === 'SYNC_NOW') {
    self.registration.sync.register('sync-pending');
  }
});

// --- BACKGROUND SYNC ---
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-pending') {
    event.waitUntil(syncPendingData());
  }
});

async function syncPendingData() {
  try {
    const cache = await caches.open('pending-requests');
    const requests = await cache.keys();
    for (const req of requests) {
      try {
        await fetch(req);
        await cache.delete(req);
      } catch {
        // Reintentar en el próximo sync
      }
    }
  } catch {
    // Silencioso
  }
}
