const isLocal =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

const API_BASE = isLocal
  ? "http://localhost:8000"
  : "https://smart-price-tracker-backend.onrender.com";

function getToken() {
  return localStorage.getItem("access_token");
}

async function apiFetch(path, options = {}) {
  const headers = options.headers || {};
  headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(API_BASE + path, { ...options, headers });
  const text = await res.text();
  
  let data = null;
  try { 
    data = text ? JSON.parse(text) : null; 
  } catch { 
    data = { raw: text }; 
  }

  if (!res.ok) {
    // Log the full error for debugging
    console.error("API Error:", {
      status: res.status,
      statusText: res.statusText,
      path,
      method: options.method || "GET",
      response: data
    });
    
    // Create a more informative error
    const error = new Error(data?.detail || data?.message || `Request failed (${res.status})`);
    error.status = res.status;
    error.data = data;
    throw error;
  }
  
  return data;
}

function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstChild;
}

function fmtMoney(price, currency) {
  if (price === null || price === undefined) return "—";
  const c = currency || "";
  return `${Number(price).toLocaleString()} ${c}`.trim();
}