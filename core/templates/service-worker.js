// TravelHub PWA — Service Worker
// Estrategia: Network First para HTML/API, Cache First para assets estáticos
// Push notifications: maneja subscripción y eventos push

const CACHE_NAME = 'travelhub-v3';
const STATIC_ASSETS = [
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
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
});

// --- ACTIVATE ---
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      );
    }).then(() => self.clients.claim())
  );
});

// --- FETCH (Network First for navigation, Cache First for static assets) ---
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Solo manejar peticiones al mismo origen
  if (url.origin !== self.location.origin) return;

  // Ignorar métodos que no sean GET (POST, PUT, DELETE, etc. pasan directo a la red)
  if (request.method !== 'GET') return;

  // Ignorar llamadas de la API (pasan directo a la red)
  if (url.pathname.startsWith('/api/')) return;

  // Estrategia para páginas HTML (navegación): Network First (con fallback offline)
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match('/offline/'))
    );
    return;
  }

  // Estrategia para archivos estáticos (CSS, JS, imágenes, fuentes)
  const isStaticAsset = url.pathname.startsWith('/static/') ||
                        url.pathname.startsWith('/media/') ||
                        url.pathname.endsWith('.png') ||
                        url.pathname.endsWith('.jpg') ||
                        url.pathname.endsWith('.jpeg') ||
                        url.pathname.endsWith('.svg') ||
                        url.pathname.endsWith('.ico') ||
                        url.pathname.endsWith('.woff2') ||
                        url.pathname.endsWith('.js') ||
                        url.pathname.endsWith('.css');

  if (isStaticAsset) {
    event.respondWith(
      caches.match(request).then((cached) => {
        return cached || fetch(request).then((response) => {
          // Solo almacenar respuestas exitosas (status 200)
          if (response.status === 200) {
            return caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, response.clone());
              return response;
            });
          }
          return response;
        });
      })
    );
    return;
  }

  // Para cualquier otra petición dinámica (HTMX, AJAX, partials), ir directo a la red sin caching.
  // Esto previene que se sirvan páginas con traducciones desactualizadas o datos antiguos.
});

// --- PUSH (Recibir notificaciones) ---
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

// --- MESSAGE (desde la página, para suscripción push) ---
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
