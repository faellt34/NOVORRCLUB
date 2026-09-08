import { useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useApp } from "../context/AppContext";
import { StatusBadge } from "../components/KpiCard";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";

const CONFIG = {
  usuarios: {
    label: "Usuários",
    fields: [
      { key: "nome", label: "Nome" },
      { key: "email", label: "Email" },
      { key: "papel", label: "Papel", type: "select", options: ["Influencer", "Parceiro", "Admin"] },
      { key: "status", label: "Status", type: "select", options: ["Ativo", "Suspenso"] },
    ],
  },
  influencers: {
    label: "Influencers",
    fields: [
      { key: "nome", label: "Nome" },
      { key: "handle", label: "Handle" },
      { key: "cidade", label: "Cidade", type: "select", options: ["Lisboa", "Porto", "Algarve", "Douro"] },
      { key: "status", label: "Status", type: "select", options: ["Ativo", "Suspenso"] },
    ],
  },
  parceiros: {
    label: "Parceiros",
    fields: [
      { key: "nome", label: "Nome" },
      { key: "categoria", label: "Categoria", type: "select", options: ["Restaurante", "Hotel", "Rooftop", "Passeio"] },
      { key: "cidade", label: "Cidade", type: "select", options: ["Lisboa", "Porto", "Algarve", "Douro"] },
      { key: "status", label: "Status", type: "select", options: ["Ativo", "Suspenso"] },
    ],
  },
  campanhas: {
    label: "Campanhas",
    fields: [
      { key: "nome", label: "Nome da Campanha" },
      { key: "parceiro", label: "Parceiro" },
      { key: "cupom", label: "Código do Cupom" },
      { key: "desconto", label: "Desconto (%)" },
      { key: "comissao", label: "Taxa de Comissão (%)" },
      { key: "validade", label: "Validade (AAAA-MM-DD)" },
      { key: "status", label: "Status", type: "select", options: ["Ativa", "Pausada", "Expirada"] },
    ],
  },
};

const emptyForm = (type) => Object.fromEntries(CONFIG[type].fields.map((f) => [f.key, f.type === "select" ? f.options[0] : ""]));

export default function AdminManage() {
  const { db, addEntity, updateEntity, deleteEntity } = useApp();
  const [tab, setTab] = useState("usuarios");
  const [dialog, setDialog] = useState(null);
  const [form, setForm] = useState({});

  const cfg = CONFIG[tab];

  const openCreate = () => { setForm(emptyForm(tab)); setDialog({ mode: "create" }); };
  const openEdit = (item) => { setForm({ ...item }); setDialog({ mode: "edit", id: item.id }); };

  const save = (e) => {
    e.preventDefault();
    const required = cfg.fields.filter((f) => !String(form[f.key] || "").trim());
    if (required.length) { toast.error(`Preencha: ${required.map((f) => f.label).join(", ")}`); return; }
    if (dialog.mode === "create") {
      addEntity(tab, form);
      toast.success(`${cfg.label.slice(0, -1)} criado com sucesso${tab === "campanhas" ? ` · comissão ${form.comissao}%` : ""}`);
    } else {
      updateEntity(tab, dialog.id, form);
      toast.success("Alterações guardadas");
    }
    setDialog(null);
  };

  const remove = (item) => {
    deleteEntity(tab, item.id);
    toast.success(`${item.nome} removido`);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 data-testid="admin-manage-title" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Gestão da Plataforma</h1>
        <p className="text-sm text-slate-500 mt-1">CRUD de usuários, influencers, parceiros e campanhas — cada ação gera registo no audit log</p>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="bg-white border border-slate-200 rounded-xl p-1 h-auto flex-wrap">
          {Object.entries(CONFIG).map(([key, c]) => (
            <TabsTrigger key={key} value={key} data-testid={`tab-${key}`} className="rounded-lg px-4 py-2 text-sm data-[state=active]:bg-purple-600 data-[state=active]:text-white">
              {c.label}
            </TabsTrigger>
          ))}
        </TabsList>

        {Object.keys(CONFIG).map((key) => (
          <TabsContent key={key} value={key}>
            <div className="card-soft p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-slate-900">{CONFIG[key].label} <span className="text-sm font-normal text-slate-400">({db[key].length})</span></h3>
                <button data-testid={`add-${key}-button`} onClick={openCreate} className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold btn-press">
                  <Plus className="w-4 h-4" /> Adicionar
                </button>
              </div>
              <div className="overflow-x-auto -mx-5 px-5">
                <table className="w-full text-sm" data-testid={`table-${key}`}>
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-wider text-slate-400 border-b border-slate-100">
                      {CONFIG[key].fields.map((f) => <th key={f.key} className="pb-3 pr-4 font-semibold">{f.label}</th>)}
                      <th className="pb-3 font-semibold text-right">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {db[key].map((item) => (
                      <tr key={item.id} data-testid={`row-${item.id}`} className="border-b border-slate-50 last:border-0 hover:bg-purple-50/40 transition-colors">
                        {CONFIG[key].fields.map((f) => (
                          <td key={f.key} className="py-3 pr-4">
                            {f.key === "status" ? (
                              ["Ativa", "Pausada", "Expirada"].includes(item[f.key])
                                ? <StatusBadge status={item[f.key]} />
                                : <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${item[f.key] === "Ativo" ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-500"}`}>{item[f.key]}</span>
                            ) : f.key === "cupom" ? (
                              <span className="font-coupon text-[11px] font-bold text-purple-700 bg-purple-50 px-2 py-1 rounded-md">{item[f.key]}</span>
                            ) : f.key === "comissao" ? (
                              <span className="font-semibold text-purple-700">{item[f.key]}%</span>
                            ) : (
                              <span className={f.key === "nome" ? "font-semibold text-slate-900" : "text-slate-600"}>{item[f.key]}{f.key === "desconto" ? "%" : ""}</span>
                            )}
                          </td>
                        ))}
                        <td className="py-3 text-right whitespace-nowrap">
                          <button data-testid={`edit-${item.id}`} onClick={() => openEdit(item)} className="p-2 rounded-lg text-slate-500 hover:bg-purple-50 hover:text-purple-600 btn-press"><Pencil className="w-4 h-4" /></button>
                          <button data-testid={`delete-${item.id}`} onClick={() => remove(item)} className="p-2 rounded-lg text-slate-500 hover:bg-red-50 hover:text-red-500 btn-press"><Trash2 className="w-4 h-4" /></button>
                        </td>
                      </tr>
                    ))}
                    {db[key].length === 0 && (
                      <tr><td colSpan={CONFIG[key].fields.length + 1} className="py-8 text-center text-slate-400">Sem registos.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </TabsContent>
        ))}
      </Tabs>

      <Dialog open={!!dialog} onOpenChange={() => setDialog(null)}>
        <DialogContent data-testid="entity-dialog" className="max-w-md">
          <DialogHeader>
            <DialogTitle>{dialog?.mode === "create" ? `Adicionar ${cfg.label.slice(0, -1)}` : `Editar ${cfg.label.slice(0, -1)}`}</DialogTitle>
            <DialogDescription>As alterações ficam registadas no audit log.</DialogDescription>
          </DialogHeader>
          <form onSubmit={save} className="space-y-3">
            {cfg.fields.map((f) => (
              <div key={f.key}>
                <label className="text-xs font-semibold text-slate-600 mb-1 block">{f.label}</label>
                {f.type === "select" ? (
                  <Select value={form[f.key] || ""} onValueChange={(v) => setForm((p) => ({ ...p, [f.key]: v }))}>
                    <SelectTrigger data-testid={`field-${f.key}`} className="rounded-xl bg-slate-50"><SelectValue /></SelectTrigger>
                    <SelectContent>{f.options.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent>
                  </Select>
                ) : (
                  <Input data-testid={`field-${f.key}`} value={form[f.key] || ""} onChange={(e) => setForm((p) => ({ ...p, [f.key]: e.target.value }))} className="rounded-xl bg-slate-50" />
                )}
              </div>
            ))}
            <button type="submit" data-testid="entity-save-button" className="w-full py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-sm font-semibold btn-press">
              {dialog?.mode === "create" ? "Criar" : "Guardar"}
            </button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
