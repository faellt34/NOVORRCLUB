import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, getToken, setToken } from "../lib/api";

const AppContext = createContext(null);

export const AppProvider = ({ children }) => {
  const [user, setUser] = useState(undefined);
  const [unread, setUnread] = useState({ notifications: 0, messages: 0 });

  const refreshUnread = useCallback(async () => {
    try {
      const [n, m] = await Promise.all([api.get("/notifications"), api.get("/messages/unread-count")]);
      setUnread({ notifications: n.data.unread, messages: m.data.unread });
    } catch {}
  }, []);

  useEffect(() => {
    if (!getToken()) { setUser(null); return; }
    api.get("/auth/me").then((r) => setUser(r.data)).catch(() => { setToken(null); setUser(null); });
  }, []);

  useEffect(() => {
    if (!user) return;
    refreshUnread();
    const t = setInterval(refreshUnread, 20000);
    return () => clearInterval(t);
  }, [user, refreshUnread]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    setToken(data.token);
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch {}
    setToken(null);
    setUser(null);
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
