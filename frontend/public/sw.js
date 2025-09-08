const CACHE_NAME = 'stock-analysis-v2'; // Bump version to ensure update
const APP_SHELL_URLS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png'
];

// Install: Cache the app shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Opened cache and caching app shell');
        // Use addAll to ensure all assets are cached. If one fails, all fail.
        return cache.addAll(APP_SHELL_URLS);
      })
      .catch(error => {
        console.error('Failed to cache app shell:', error);
      })
  );
});

// Activate: Clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  return self.clients.claim(); // Take control of open clients immediately
});

// Fetch: Serve from cache, fall back to network, and cache new assets
self.addEventListener('fetch', (event) => {
  // Let the browser handle requests for scripts from extensions
  if (event.request.url.startsWith('chrome-extension://')) {
    return;
  }

  // Don't cache API requests
  if (event.request.url.includes('/api/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  event.respondWith(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.match(event.request).then((response) => {
        // If we have a cached response, return it.
        if (response) {
          return response;
        }

        // Otherwise, fetch from the network.
        return fetch(event.request).then((networkResponse) => {
          // If the fetch is successful, clone the response and store it in the cache.
          if (networkResponse && networkResponse.status === 200) {
            // Only cache GET requests.
            if (event.request.method === 'GET') {
               cache.put(event.request, networkResponse.clone());
            }
          }
          return networkResponse;
        });
      });
    })
  );
});
