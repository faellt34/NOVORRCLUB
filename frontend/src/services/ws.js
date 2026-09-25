import { useEffect, useRef } from "react";
import { getToken } from "../lib/api";

export const wsUrl = () => `${window.location.origin.replace(/^http/, "ws")}/api/ws/dashboard?token=${encodeURIComponent(getToken() || "")}`;

export const useRealtime = (onEvent, { enabled = true } = {}) => {
  const cb = useRef(onEvent);
  cb.current = onEvent;
  useEffect(() => {
    if (!enabled) return;
    let ws, ping, retry, closed = false, delay = 1000;
    const connect = () => {
      ws = new WebSocket(wsUrl());
      ws.onopen = () => { delay = 1000; ping = setInterval(() => ws.readyState === 1 && ws.send("ping"), 20000); cb.current?.({ tipo: "ligado" }); };
      ws.onmessage = (e) => { try { const ev = JSON.parse(e.data); if (ev.tipo !== "pong") cb.current?.(ev); } catch {} };
      ws.onclose = (e) => {
        clearInterval(ping);
        cb.current?.({ tipo: "desligado" });
        if (closed || e.code === 4401) return;
        retry = setTimeout(connect, delay); delay = Math.min(delay * 2, 15000);
      };
      ws.onerror = () => ws.close();
    };
    connect();
    return () => { closed = true; clearInterval(ping); clearTimeout(retry); ws?.close(); };
  }, [enabled]);
};
