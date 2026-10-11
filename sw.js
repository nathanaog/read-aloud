/* Read Aloud — service worker
   1. Offline: keeps a copy of the app so it opens without internet once installed.
      The page is fetched network-first (you get updates when online), cache as fallback.
   2. Speed: adds the two headers that make the page "cross-origin isolated", which lets
      the neural voice use several processor cores. GitHub Pages can't set headers itself.
   Your books are never here — they live in the app's IndexedDB on your device. */
const CACHE = 'read-aloud-v64a1a7b7b0';
const SHELL = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png', './icon-maskable.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

function isolate(res) {
  if (!res || res.type === 'opaque' || res.status === 0) return res;
  const h = new Headers(res.headers);
  h.set('Cross-Origin-Opener-Policy', 'same-origin');
  h.set('Cross-Origin-Embedder-Policy', 'credentialless'); // allows the model download from Hugging Face
  h.set('Cross-Origin-Resource-Policy', 'same-origin');
  return new Response(res.body, { status: res.status, statusText: res.statusText, headers: h });
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) return; // model downloads etc. pass straight through
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const res = await fetch(req, { cache: 'no-cache' });
      if (res.ok) cache.put(req.mode === 'navigate' ? './index.html' : req, res.clone());
      return isolate(res);
    } catch {
      const hit = await cache.match(req.mode === 'navigate' ? './index.html' : req, { ignoreSearch: true });
      return isolate(hit) || new Response('Offline and not cached yet.', { status: 503 });
    }
  })());
});
