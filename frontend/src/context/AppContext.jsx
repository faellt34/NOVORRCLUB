import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useSessionPolling } from "../hooks/useSessionPolling";
import { api, getToken, setToken } from "../lib/api";

const AppContext = createContext(null);

export const AppProvider = ({ children }) => {
  const [user, setUser] = useState(undefined);
  const [unread, setUnread] = useState({ notifications: 0, messages: 0 });

  const refreshUnread = useCallback(async (signal) => {
    const token = getToken();
    if (!user || !token) return;
    try {
      const [n, m] = await Promise.all([api.get("/notifications", { signal }), api.get("/messages/unread-count", { signal })]);
      if (getToken() !== token || signal?.aborted) return;
      setUnread({ notifications: n.data.unread, messages: m.data.unread });
    } catch {}
  }, [user]);

  useEffect(() => {
    const token = getToken();
    if (!token) { setUser(null); return; }
    let mounted = true;
    api.get("/auth/me").then((r) => {
      if (mounted && getToken() === token) setUser(r.data);
    }).catch(() => {
      if (mounted && (!getToken() || getToken() === token)) { setToken(null); setUser(null); }
    });
    return () => { mounted = false; };
  }, []);

  useSessionPolling(refreshUnread, 20000, Boolean(user));

  useEffect(() => {
    const clearSession = () => { setUser(null); setUnread({ notifications: 0, messages: 0 }); };
    const syncSession = (event) => { if (event.key === "robson_token" && !event.newValue) clearSession(); };
    window.addEventListener("rrclub:session-expired", clearSession);
    window.addEventListener("storage", syncSession);
    return () => {
      window.removeEventListener("rrclub:session-expired", clearSession);
      window.removeEventListener("storage", syncSession);
    };
  }, []);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    setToken(data.token);
    localStorage.setItem("rrclub_currency", data.user.currency || "eur");
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    const token = getToken();
    setToken(null);
    setUser(null);
    setUnread({ notifications: 0, messages: 0 });
    try { await api.post("/auth/logout", {}, { headers: token ? { Authorization: "Bearer " + token } : {} }); } catch {}
  };

  const refreshUser = async () => {
    const { data } = await api.get("/auth/me");
    setUser(data);
    return data;
  };

  const value = useMemo(() => ({ user, role: user?.role, login, logout, refreshUser, unread, refreshUnread }), [user, unread, refreshUnread]);
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

export const useApp = () => useContext(AppContext);
