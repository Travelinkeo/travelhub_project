const CACHE_NAME = 'travelhub-v1';
const STATIC_CACHE = 'travelhub-static-v1';
const DYNAMIC_CACHE = 'travelhub-dynamic-v1';

// URLs estáticas para cachear (app shell)
const STATIC_ASSETS = [
    '/',
    '/dashboard/',
    '/static/manifest.json',
    '/static/images/Logo TravelHub.png',
    '/static/images/pwa-192x192.png',
    '/static/images/pwa-512x512.png',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
    'https://fonts.googleapis.com/icon?family=Material+Symbols+Outlined'
];

// URLs de API que se cachearán dinámicamente
const API_CACHE_PATTERNS = [
    '/api/v1/dashboard/',
    '/api/v1/crm/clientes/',
    '/api/v1/bookings/ventas/'
];

// Install - cachear assets estáticos
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('[SW] Cachening static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate - limpiar caches antiguos
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys
                    .filter(key => key !== STATIC_CACHE && key !== DYNAMIC_CACHE)
                    .map(key => {
                        console.log('[SW] Removing old cache:', key);
                        return caches.delete(key);
                    })
            )
        ).then(() => self.clients.claim())
    );
});

// Fetch - estrategia stale-while-revalidate para assets, network-first para API
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') return;

    // Skip admin, API mutations, websocket
    if (url.pathname.startsWith('/admin/') ||
        url.pathname.startsWith('/ws/') ||
        request.headers.get('upgrade') === 'websocket') {
        return;
    }

    // Network-first para páginas HTML (navegación)
    if (request.mode === 'navigate' ||
        (request.headers.get('accept') && request.headers.get('accept').includes('text/html'))) {
        event.respondWith(
            fetch(request)
                .then(response => {
                    const clone = response.clone();
                    caches.open(DYNAMIC_CACHE).then(cache => cache.put(request, clone));
                    return response;
                })
                .catch(() => caches.match(request).then(r => r || caches.match('/')))
        );
        return;
    }

    // Stale-while-revalidate para assets estáticos (CSS, JS, fonts, images)
    if (url.pathname.startsWith('/static/') ||
        url.hostname === 'fonts.googleapis.com' ||
        url.hostname === 'fonts.gstatic.com' ||
        url.hostname === 'cdn.tailwindcss.com') {
        event.respondWith(
            caches.open(STATIC_CACHE).then(cache =>
                cache.match(request).then(cached => {
                    const fetched = fetch(request).then(response => {
                        cache.put(request, response.clone());
                        return response;
                    }).catch(() => cached);
                    return cached || fetched;
                })
            )
        );
        return;
    }

    // Network-first para API y HTMX
    if (url.pathname.startsWith('/api/') ||
        request.headers.get('HX-Request')) {
        event.respondWith(
            fetch(request)
                .then(response => {
                    if (response.ok) {
                        const clone = response.clone();
                        caches.open(DYNAMIC_CACHE).then(cache => cache.put(request, clone));
                    }
                    return response;
                })
                .catch(() => caches.match(request))
        );
        return;
    }

    // Default: network-first
    event.respondWith(
        fetch(request)
            .then(response => {
                if (response.ok) {
                    const clone = response.clone();
                    caches.open(DYNAMIC_CACHE).then(cache => cache.put(request, clone));
                }
                return response;
            })
            .catch(() => caches.match(request))
    );
});

// Background Sync para formulario offline
self.addEventListener('sync', event => {
    if (event.tag === 'sync-ventas') {
        event.waitUntil(syncPendingSales());
    }
});

async function syncPendingSales() {
    const cache = await caches.open('pending-sync');
    const requests = await cache.keys();
    for (const request of requests) {
        try {
            const response = await fetch(request);
            if (response.ok) {
                await cache.delete(request);
                console.log('[SW] Synced sale:', request.url);
            }
        } catch (e) {
            console.log('[SW] Sync failed, will retry:', request.url);
        }
    }
}

// Push notifications para ventas nuevas
self.addEventListener('push', event => {
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'TravelHub';
    const options = {
        body: data.body || 'Nueva actividad en tu agencia',
        icon: '/static/images/pwa-192x192.png',
        badge: '/static/images/pwa-192x192.png',
        vibrate: [100, 50, 100],
        data: data.url || '/dashboard/',
        actions: [
            { action: 'open', title: 'Ver', icon: '/static/images/pwa-192x192.png' },
            { action: 'dismiss', title: 'Cerrar' }
        ]
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', event => {
    event.notification.close();
    if (event.action === 'dismiss') return;
    event.waitUntil(
        clients.openWindow(event.notification.data)
    );
});
