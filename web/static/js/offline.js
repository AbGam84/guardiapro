const OFFLINE_QUEUE_KEY = "excalibu_offline_queue";

function isOnline() {
  return navigator.onLine;
}

function getOfflineQueue() {
  try {
    return JSON.parse(localStorage.getItem(OFFLINE_QUEUE_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveOfflineQueue(q) {
  localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(q));
}

function queueOfflineRequest(path, opts) {
  const q = getOfflineQueue();
  q.push({
    path,
    method: opts.method || "POST",
    body: opts.body instanceof FormData ? null : opts.body,
    isForm: opts.body instanceof FormData,
    ts: Date.now(),
  });
  saveOfflineQueue(q);
  showOfflineBanner(`${q.length} reporte(s) pendiente(s) de sincronizar`);
  return { queued: true, queue_size: q.length };
}

function showOfflineBanner(text) {
  let el = document.getElementById("offlineBanner");
  if (!el) {
    el = document.createElement("div");
    el.id = "offlineBanner";
    el.style.cssText = "position:fixed;bottom:0;left:0;right:0;background:#ff8c1a;color:#050c14;padding:10px 14px;font-size:.85rem;font-weight:600;text-align:center;z-index:9999";
    document.body.appendChild(el);
  }
  el.textContent = text;
  el.classList.remove("hidden");
}

function hideOfflineBanner() {
  const el = document.getElementById("offlineBanner");
  if (el) el.classList.add("hidden");
}

async function syncOfflineQueue() {
  if (!isOnline()) return 0;
  const q = getOfflineQueue();
  if (!q.length) {
    hideOfflineBanner();
    return 0;
  }
  const token = typeof getToken === "function" ? getToken() : "";
  let synced = 0;
  const remaining = [];
  for (const item of q) {
    try {
      const headers = { Authorization: "Bearer " + token };
      let body = item.body;
      if (!item.isForm) headers["Content-Type"] = "application/json";
      const res = await fetch(item.path, { method: item.method, headers, body });
      if (res.ok) synced += 1;
      else remaining.push(item);
    } catch {
      remaining.push(item);
    }
  }
  saveOfflineQueue(remaining);
  if (remaining.length) showOfflineBanner(`${remaining.length} reporte(s) pendiente(s) de sincronizar`);
  else hideOfflineBanner();
  return synced;
}

async function apiWithOffline(path, opts = {}) {
  const mutating = (opts.method || "GET").toUpperCase() !== "GET";
  if (mutating && !isOnline()) {
    if (opts.body instanceof FormData) {
      throw new Error("Sin conexión: fotos requieren internet. Los textos se guardan en cola.");
    }
    return queueOfflineRequest(path, opts);
  }
  try {
    const data = await api(path, opts);
    if (mutating) await syncOfflineQueue();
    return data;
  } catch (ex) {
    if (mutating && !isOnline()) return queueOfflineRequest(path, opts);
    throw ex;
  }
}

window.addEventListener("online", () => {
  syncOfflineQueue().then((n) => {
    if (n > 0) showOfflineBanner(`Sincronizados ${n} reporte(s)`);
    setTimeout(hideOfflineBanner, 3000);
  });
});

window.addEventListener("offline", () => showOfflineBanner("Sin conexión — los reportes se guardan localmente"));

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
