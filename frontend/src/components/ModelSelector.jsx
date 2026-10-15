import { useEffect, useState } from "react";
import { Cpu } from "lucide-react";
import { api } from "../lib/api";

const KEY = "diretor_modelo";
export const getModelo = () => localStorage.getItem(KEY) || "gemini";

export const ModelSelector = ({ value, onChange }) => {
  const [list, setList] = useState([]);
  useEffect(() => { api.get("/diretor/modelos").then((r) => setList(r.data)).catch(() => {}); }, []);
  const cur = list.find((m) => m.id === value);
  return (
    <div className="flex flex-col gap-1" data-testid="model-selector">
      <div className="inline-flex rounded-xl bg-slate-100 p-1">
        {list.map((m) => (
          <button key={m.id} data-testid={`model-${m.id}`} onClick={() => { localStorage.setItem(KEY, m.id); onChange(m.id); }} title={`${m.nome} · ${m.nota}`}
            className={`px-3 py-1 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 transition-colors ${value === m.id ? "bg-indigo-600 text-white shadow-sm" : "text-slate-500 hover:text-slate-900"}`}>
            <Cpu className="w-3 h-3" />{m.id === "gpt" ? "ChatGPT" : m.id === "claude" ? "Claude" : "Gemini"}<span className="opacity-70">{m.custo}</span>
          </button>
        ))}
      </div>
      {cur && <p data-testid="model-note" className="text-[10px] text-slate-400">{cur.nome} · {cur.nota}</p>}
    </div>
  );
};
