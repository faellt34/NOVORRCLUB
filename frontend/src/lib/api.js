import axios from "axios";

export const reportCurrency = () => localStorage.getItem("rrclub_currency") === "brl" ? "brl" : "eur";
export const moneyIn = (v, currency = "eur") => new Intl.NumberFormat(currency === "brl" ? "pt-BR" : "pt-PT", { style: "currency", currency: currency.toUpperCase() }).format(Number(v) || 0);
export const dashboardMoney = (v) => new Intl.NumberFormat(reportCurrency() === "brl" ? "pt-BR" : "pt-PT", { style: "currency", currency: reportCurrency().toUpperCase() }).format(Number(v) || 0);

const TOKEN_KEY = "robson_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY));

export const api = axios.create({ baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`, withCredentials: true });

api.interceptors.request.use((config) => {
  config.headers["X-Currency"] = reportCurrency();
  const t = getToken();
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

api.interceptors.response.use((response) => response, (error) => {
  const sentToken = error.config?.headers?.Authorization;
  if (!String(error.config?.url || "").startsWith("/auth/") && !String(error.config?.url || "").startsWith("/public/") && error.response?.status === 401 && sentToken && sentToken === 'Bearer ' + getToken()) {
    setToken(null);
    window.dispatchEvent(new Event("rrclub:session-expired"));
  }
  return Promise.reject(error);
});

export const apiError = (e, fallback = "Ocorreu um erro. Tente novamente.") => {
  const d = e?.response?.data?.detail;
  if (!d) return e?.message || fallback;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x?.msg || JSON.stringify(x)).join(" ");
  return d?.msg || String(d);
};

export const eur = (v) =>
  new Intl.NumberFormat("pt-PT", { style: "currency", currency: "EUR", maximumFractionDigits: Number(v) % 1 === 0 ? 0 : 2 }).format(Number(v) || 0);

export const num = (v) => new Intl.NumberFormat("pt-PT").format(Number(v) || 0);

export const slug = (s) => String(s).toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-");

let siteUrl = null;
export const getSiteUrl = async () => {
  if (siteUrl) return siteUrl;
  try { const { data } = await api.get("/public/site"); siteUrl = data.frontend_url || window.location.origin; }
  catch { siteUrl = window.location.origin; }
  return siteUrl;
};
export const couponLink = (site, code) => `${site}/c/${code}`;

export const downloadCsv = (filename, header, rows) => {
  const blob = new Blob([header + "\n" + rows.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};
