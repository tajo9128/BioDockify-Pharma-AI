// Minimal Service Worker to satisfy PWA installability requirements
// We use a network-first strategy to ensure the app is always up to date.

self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    return self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    // Simple network-only strategy for now to avoid caching issues with the API
    event.respondWith(fetch(event.request));
});
