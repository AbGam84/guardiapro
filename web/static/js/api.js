const TOKEN_KEY = "guardiapro_token";

function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

function setToken(t) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (!(opts.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers.Authorization = "Bearer " + token;
  const res = await fetch(path, { ...opts, headers });
  const text = await res.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text }; }
  if (!res.ok) throw new Error(data.detail || data.message || "Error " + res.status);
  return data;
}

function fmt(dt) {
  if (!dt) return "—";
  try {
    return new Date(dt).toLocaleString("es-CR", { dateStyle: "short", timeStyle: "short" });
  } catch { return dt; }
}

const ENTRY_LABELS = {
  inicio: "Inicio de turno",
  ronda: "Ronda / patrullaje",
  checkpoint: "Punto de control",
  incidente: "Incidente",
  novedad: "Novedad",
  visita: "Visita / ingreso",
  vehiculo: "Vehículo",
  llaves: "Llaves / acceso",
  entrega: "Entrega de turno",
  fin: "Fin de turno",
};
