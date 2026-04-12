// Service worker — network-first for HTML/API, cache-first for static assets.
// Bump CACHE_NAME to force old caches to evict on new deploys.
const CACHE_NAME = 'catan-v2'

self.addEventListener('install', e => {
  // Activate immediately, don't wait for old SW to release tabs
  self.skipWaiting()
})

self.addEventListener('activate', e => {
  e.waitUntil(
    (async () => {
      // Purge any old caches from previous versions
      const keys = await caches.keys()
      await Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
      // Take control of existing clients immediately
      await self.clients.claim()
    })()
  )
})

self.addEventListener('fetch', e => {
  const req = e.request
  const url = new URL(req.url)

  // Never touch API or WebSocket requests — always go to network
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws/')) {
    return
  }

  // Non-GET: bypass cache
  if (req.method !== 'GET') {
    return
  }

  // HTML navigation: network-first, fallback to cache on offline
  if (req.mode === 'navigate' || req.destination === 'document') {
    e.respondWith(
      fetch(req)
        .then(res => {
          const copy = res.clone()
          caches.open(CACHE_NAME).then(c => c.put(req, copy))
          return res
        })
        .catch(() => caches.match(req).then(r => r || caches.match('/')))
    )
    return
  }

  // Static assets (hashed JS/CSS): cache-first, network fallback
  if (url.pathname.startsWith('/assets/') || /\.(js|css|svg|png|jpg|woff2?)$/.test(url.pathname)) {
    e.respondWith(
      caches.match(req).then(cached => {
        if (cached) return cached
        return fetch(req).then(res => {
          const copy = res.clone()
          caches.open(CACHE_NAME).then(c => c.put(req, copy))
          return res
        })
      })
    )
    return
  }

  // Everything else: network, no cache
})
