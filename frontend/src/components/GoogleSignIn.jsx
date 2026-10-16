import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api, apiError, setToken } from "../lib/api";
import { useApp } from "../context/AppContext";

let scriptPromise;
let configPromise;
function getConfig() {
  if (!configPromise) configPromise = api.get("/auth/google/config").finally(() => { configPromise = null; });
  return configPromise;
}
function loadGoogle() {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (!scriptPromise) scriptPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = resolve;
    script.onerror = () => { scriptPromise = null; reject(new Error("Google indisponível")); };
    document.head.appendChild(script);
  });
  return scriptPromise;
}

export default function GoogleSignIn({ registration, onPending, linkAccount = false }) {
  const node = useRef(null);
  const current = useRef({ registration, onPending, linkAccount });
  current.current = { registration, onPending, linkAccount };
  const { refreshUser } = useApp();
  const navigate = useNavigate();
  const refreshRef = useRef(refreshUser);
  refreshRef.current = refreshUser;
  const [configured, setConfigured] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    getConfig().then(async ({ data }) => {
      if (cancelled) return;
      if (!data.client_id) { setError("O acesso Google aguarda configuração pela equipa. Utilize email e palavra-passe."); return; }
      setConfigured(true);
      await loadGoogle();
      if (cancelled) return;
      window.google.accounts.id.initialize({ client_id: data.client_id, nonce: data.nonce, auto_select: false, callback: async ({ credential }) => {
        const { registration: form, onPending: pending, linkAccount: linking } = current.current;
        if (form && !form.aceita_termos) { toast.error("Aceite a Política de Privacidade para continuar."); return; }
        try {
          const { data: result } = await api.post(linking ? "/auth/google/link" : "/auth/google", {
            credential, ...(form ? { nome: form.nome, currency: form.currency || "eur", role: form.role, aceita_termos: form.aceita_termos, cidade: form.cidade, handle: form.handle, categoria: form.categoria } : {}),
          });
          if (result.linked) { await refreshRef.current(); toast.success("Conta Google vinculada. Já pode usá-la para entrar."); return; }
          if (result.pending) { pending?.(result.message); return; }
          setToken(result.token);
          localStorage.setItem("rrclub_currency", result.user.currency || "eur");
          await refreshRef.current();
          navigate({ admin: "/admin", partner: "/parceiro", influencer: "/influencer" }[result.user.role] || "/");
        } catch (e) { toast.error(apiError(e)); }
      } });
      window.google.accounts.id.renderButton(node.current, { theme: "outline", size: "large", text: "continue_with", locale: "pt", width: Math.min(node.current.clientWidth || 320, 400) });
    }).catch(() => { if (!cancelled) setError("Login Google indisponível. Pode entrar com email e palavra-passe."); });
    return () => { cancelled = true; };
  }, [navigate]);
  return <div className="my-4"><div ref={node} />{!configured && <button type="button" disabled className="w-full min-h-[44px] rounded-xl border border-slate-200 bg-white text-slate-500 text-sm">Entrar com Google</button>}{error && <p role="status" className="text-xs text-slate-500">{error}</p>}</div>;
}
