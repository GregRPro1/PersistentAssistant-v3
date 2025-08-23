// v5: bypass diag/config/agent caching
self.addEventListener('install', (e)=>{ self.skipWaiting(); });
self.addEventListener('activate', (e)=>{ e.waitUntil(clients.claim()); });
self.addEventListener('fetch', (event)=>{
  const url = event.request.url;
  if (url.includes('/pwa/diag') || url.includes('/pwa/config') || url.includes('/pwa/agent')) {
    event.respondWith(fetch(event.request, {cache:'no-store'}));
    return;
  }
  event.respondWith(fetch(event.request).catch(()=> caches.match(event.request)));
});
