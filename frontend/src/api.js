// A thin wrapper around fetch. The backend's URL is set at build time
// through VITE_API_URL (see render.yaml), falling back to the local
// FastAPI dev server so `npm run dev` works without any extra setup.
// render.yaml's fromService only offers a bare host, no scheme, so a
// plain hostname here is assumed to be an https backend, not http.

const RAW_API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const API_BASE_URL = /^https?:\/\//.test(RAW_API_URL) ? RAW_API_URL : `https://${RAW_API_URL}`;

async function postJSON(path, body) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    const message = detail?.detail?.[0]?.msg ?? detail?.detail ?? `request failed with status ${response.status}`;
    throw new Error(message);
  }
  return response.json();
}

export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.ok;
}

export function predictTonnes(settings) {
  return postJSON("/predict/tonnes", settings);
}

export function predictWinderRul(reading) {
  return postJSON("/predict/winder-rul", reading);
}
