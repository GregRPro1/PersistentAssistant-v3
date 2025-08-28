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

// cache-bust 2025-08-24T16:43:05.8380919+01:00

// cache-bust ext-v2 2025-08-24T16:54:36.5098266+01:00

// cache-bust 2025-08-24T18:29:12.3433470+01:00

// cache-bust tabs-v1 2025-08-25T06:33:20.0743283+01:00

// cache-bust actions-v1 2025-08-25T06:57:00.1111857+01:00

// cache-bust tabs-v1.1 2025-08-25T07:04:27.1338644+01:00

// cache-bust tabs-v1.3 & actions-v6 2025-08-25T07:23:11.4083650+01:00

// cache-bust tabs-v1.4 + actions-v7 + plan-v1 2025-08-25T07:41:05.9233704+01:00

// cache-bust 2025-08-25T08:01:52.6840536+01:00

// cache-bust compose 2025-08-26T08:53:55.7078445+01:00
