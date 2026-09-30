import { useEffect, useRef, useState } from "react";
import { getToken } from "../lib/api";

export const wsUrl = () => `${window.location.origin.replace(/^http/, "ws")}/api/ws/dashboard`;

export const useRealtime = (onEvent, { enabled = true } = {}) => {
  const cb = useRef(onEvent);
  cb.current = onEvent;
  const [status, setStatus] = useState("reconectando");
  const [eventos, setEventos] = useState([]);
  const [ultimoEvento, setUltimoEvento] = useState(null);
  useEffect(() => {
    if (!enabled) return;
    let ws, ping, retry, closed = false, delay = 1000;
    const connect = () => {
      setStatus("reconectando");
      ws = new WebSocket(wsUrl());
      ws.onopen = () => { ws.send(JSON.stringify({ type: "auth", token: getToken() || "" })); };
      ws.onmessage = (e) => {
        try {
          const ev = JSON.parse(e.data);
          if (ev.tipo === "ligado") { delay = 1000; setStatus("conectado"); ping = setInterval(() => ws.readyState === 1 && ws.send("ping"), 20000); cb.current?.({ tipo: "ligado" }); return; }
          if (ev.tipo === "pong") return;
          setEventos((p) => [ev, ...p].slice(0, 200)); setUltimoEvento(ev); cb.current?.(ev);
        } catch {}
      };
      ws.onclose = (e) => {
        clearInterval(ping);
        cb.current?.({ tipo: "desligado" });
        if (closed || e.code === 4401 || e.code === 4429) { setStatus("offline"); return; }
        setStatus("reconectando");
        retry = setTimeout(connect, delay); delay = Math.min(delay * 2, 30000);
      };
      ws.onerror = () => ws.close();
    };
    connect();
    const onOffline = () => setStatus("offline");
    window.addEventListener("offline", onOffline);
    return () => { closed = true; clearInterval(ping); clearTimeout(retry); ws?.close(); window.removeEventListener("offline", onOffline); };
  }, [enabled]);
  return { status, eventos, ultimoEvento };
};
