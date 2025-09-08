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
  const req = event.request
  const url = new URL(req.url)

  // Let the browser handle requests for scripts from extensions
  if (url.protocol === 'chrome-extension:') return

  // Skip non-GET requests entirely
  if (req.method !== 'GET') return

  // Bypass cross-origin requests (e.g., API on another port) and dev-specific paths
  const isSameOrigin = url.origin === self.location.origin
  if (!isSameOrigin) {
    event.respondWith(fetch(req))
    return
  }

  // Avoid interfering with Vite dev client and HMR endpoints if any are requested from same origin
  if (url.pathname.startsWith('/@vite') || url.pathname.startsWith('/vite') || url.pathname.includes('sockjs')) {
    event.respondWith(fetch(req))
    return
  }

  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME)

    // For navigation requests, try network first with fallback to cached shell
    if (req.mode === 'navigate') {
      try {
        const networkResponse = await fetch(req)
        // Optionally update shell cache
        if (networkResponse && networkResponse.ok) {
          try { cache.put('/index.html', networkResponse.clone()) } catch {}
        }
        return networkResponse
      } catch (err) {
        const fallback = await cache.match('/index.html')
        if (fallback) return fallback
        return new Response('Offline', { status: 503, statusText: 'Service Unavailable' })
      }
    }

    // Only cache static asset-like requests
    const staticDestinations = ['style', 'script', 'image', 'font', 'manifest']
    if (!staticDestinations.includes(req.destination)) {
      // For XHR/fetch (destination "empty") or other types, just go to network without caching
      try {
        return await fetch(req)
      } catch (err) {
        // If offline and request was for a static asset previously cached, return cache fallback
        const fallback = await cache.match(req)
        if (fallback) return fallback
        return new Response('Network error', { status: 503, statusText: 'Service Unavailable' })
      }
    }

    // Cache-first for same-origin static assets
    const cached = await cache.match(req)
    if (cached) return cached

    try {
      const networkResponse = await fetch(req)
      if (networkResponse && networkResponse.ok) {
        try { await cache.put(req, networkResponse.clone()) } catch {}
      }
      return networkResponse
    } catch (err) {
      return new Response('Network error', { status: 503, statusText: 'Service Unavailable' })
    }
  })())
})
