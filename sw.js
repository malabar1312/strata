// Service worker "RED PRIMERO" — la app instalada en el iPhone SIEMPRE carga la
// última versión cuando hay internet, y cae a la copia guardada solo si estás sin
// conexión. Adiós al problema de "veo la versión vieja" tras cada cambio.
const CACHE = "mariete-billete-v1";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  e.respondWith(
    fetch(req)
      .then((res) => {
        // guarda una copia para poder abrir sin conexión
        if (res && res.status === 200) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        }
        return res;
      })
      .catch(() => caches.match(req)), // sin internet -> última copia
  );
});
