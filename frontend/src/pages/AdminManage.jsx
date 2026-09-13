import { useCallback, useEffect, useState } from "react";
import { Plus, Pencil, Trash2, FileUp, FileCheck2 } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "../lib/api";
import { StatusBadge } from "../components/KpiCard";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";

const CITIES = ["Lisboa", "Porto", "Algarve", "Douro", "Madrid", "Paris", "Roma", "Dubai", "Outra"];

const CONFIG = {
  usuarios: {
    label: "Usuários", singular: "Usuário",
    fields: [
      { key: "nome", label: "Nome" },
      { key: "email", label: "Email" },
      { key: "password", label: "Palavra-passe", hideInTable: true, optional: true, placeholder: "deixe vazio para manter / padrão robson123" },
      { key: "papel", label: "Papel", type: "select", options: ["Influencer", "Parceiro", "Admin"] },
      { key: "status", label: "Status", type: "select", options: ["Ativo", "Pendente", "Suspenso"] },
    ],
  },
  influencers: {
    label: "Influencers", singular: "Influencer",
    fields: [
      { key: "nome", label: "Nome" },
      { key: "handle", label: "Handle" },
      { key: "cidade", label: "Cidade", type: "select", options: CITIES },
      { key: "iban", label: "IBAN (receber comissões)", optional: true, hideInTable: true },
      { key: "status", label: "Status", type: "select", options: ["Ativo", "Suspenso"] },
    ],
  },
  parceiros: {
    label: "Parceiros", singular: "Parceiro",
    fields: [
      { key: "nome", label: "Nome" },
      { key: "categoria", label: "Categoria", type: "select", options: ["Restaurante", "Hotel", "Rooftop", "Passeio"] },
      { key: "cidade", label: "Cidade", type: "select", options: CITIES },
      { key: "iban", label: "IBAN (recebimentos)", optional: true, hideInTable: true },
      { key: "status", label: "Status", type: "select", options: ["Ativo", "Pendente", "Suspenso"] },
    ],
  },
  campanhas: {
    label: "Campanhas", singular: "Campanha",
    fields: [
      { key: "nome", label: "Nome da Campanha" },
      { key: "parceiro", label: "Parceiro (nome exato)" },
      { key: "influencer", label: "Influencer (nome ou @handle)" },
      { key: "cupom", label: "Código do Cupom" },
      { key: "desconto", label: "Desconto (%)" },
      { key: "comissao", label: "Taxa de Comissão (%)" },
      { key: "validade", label: "Validade (AAAA-MM-DD)" },
      { key: "status", label: "Status", type: "select", options: ["Ativa", "Pausada", "Expirada"] },
    ],
  },
  ebooks: {
    label: "E-books", singular: "E-book",
    fields: [
      { key: "titulo", label: "Título" },
      { key: "pais", label: "País" },
      { key: "regiao", label: "Região/Cidade" },
      { key: "categoria", label: "Categoria", type: "select", options: ["Restaurantes", "Hotéis", "Rooftops", "Passeios"] },
      { key: "idioma", label: "Idioma", type: "select", options: ["PT", "PT/EN", "PT/ES", "EN", "ES", "FR", "IT"] },
      { key: "paginas", label: "Páginas" },
      { key: "preco", label: "Preço (€)" },
      { key: "premium", label: "Premium", type: "select", options: ["true", "false"] },
      { key: "capa", label: "URL da capa", hideInTable: true },
      { key: "descricao", label: "Descrição", hideInTable: true },
    ],
  },
};

const emptyForm = (type) => Object.fromEntries(CONFIG[type].fields.map((f) => [f.key, f.type === "select" ? f.options[0] : ""]));

export default function AdminManage() {
  const [tab, setTab] = useState("usuarios");
  const [db, setDb] = useState({});
  const [dialog, setDialog] = useState(null);
  const [form, setForm] = useState({});
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(null);

  const uploadPdf = async (item, file) => {
    if (!file) return;
    setUploading(item.id);
    const fd = new FormData();
    fd.append("file", file);
    try {
      await api.post(`/admin/ebooks/${item.id}/pdf`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(`PDF de "${item.titulo}" carregado`);
      load("ebooks");
    } catch (e) { toast.error(apiError(e)); } finally { setUploading(null); }
  };

  const load = useCallback((kind) => api.get(`/admin/${kind}`).then((r) => setDb((p) => ({ ...p, [kind]: r.data }))).catch((e) => toast.error(apiError(e))), []);
  useEffect(() => { if (!db[tab]) load(tab); }, [tab, db, load]);

  const cfg = CONFIG[tab];
  const openCreate = () => { setForm(emptyForm(tab)); setDialog({ mode: "create" }); };
  const openEdit = (item) => { setForm({ ...emptyForm(tab), ...Object.fromEntries(Object.entries(item).map(([k, v]) => [k, v == null ? "" : String(v)])), password: "" }); setDialog({ mode: "edit", id: item.id }); };

  const save = async (e) => {
    e.preventDefault();
    const missing = cfg.fields.filter((f) => !f.optional && !String(form[f.key] ?? "").trim());
    if (missing.length) { toast.error(`Preencha: ${missing.map((f) => f.label).join(", ")}`); return; }
    setBusy(true);
    try {
      const payload = Object.fromEntries(cfg.fields.map((f) => [f.key, form[f.key]]).filter(([k, v]) => !(k === "password" && !v)));
      if (dialog.mode === "create") {
        await api.post(`/admin/${tab}`, payload);
        toast.success(`${cfg.singular} criado com sucesso${tab === "campanhas" ? ` · comissão ${form.comissao}%` : ""}`);
      } else {
        await api.put(`/admin/${tab}/${dialog.id}`, payload);
        toast.success("Alterações guardadas");
      }
      setDialog(null); load(tab);
    } catch (err) { toast.error(apiError(err)); } finally { setBusy(false); }
  };

  const remove = async (item) => {
    if (!window.confirm(`Remover "${item.nome || item.titulo}"? Esta ação fica no audit log.`)) return;
    try { await api.delete(`/admin/${tab}/${item.id}`); toast.success(`${item.nome || item.titulo} removido`); load(tab); }
    catch (err) { toast.error(apiError(err)); }
  };

  const cell = (f, item) => {
    const v = item[f.key];
    if (f.key === "status") return ["Ativa", "Pausada", "Expirada"].includes(v) ? <StatusBadge status={v} /> : <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${v === "Ativo" ? "bg-emerald-50 text-emerald-600" : v === "Pendente" ? "bg-amber-50 text-amber-600" : "bg-red-50 text-red-500"}`}>{v}</span>;
    if (f.key === "cupom") return <span className="font-coupon text-[11px] font-bold text-purple-700 bg-purple-50 px-2 py-1 rounded-md">{v}</span>;
    if (f.key === "comissao") return <span className="font-semibold text-purple-700">{v}%</span>;
    if (f.key === "premium") return <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${v ? "bg-purple-50 text-purple-700" : "bg-slate-100 text-slate-500"}`}>{v ? "Premium" : "Gratuito"}</span>;
    if (f.key === "preco") return <span className="text-slate-600">{v ? `${v}€` : "—"}</span>;
    return <span className={["nome", "titulo"].includes(f.key) ? "font-semibold text-slate-900" : "text-slate-600"}>{v}{f.key === "desconto" ? "%" : ""}</span>;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 data-testid="admin-manage-title" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Gestão da Plataforma</h1>
        <p className="text-sm text-slate-500 mt-1">CRUD de usuários, influencers, parceiros, campanhas e e-books — cada ação gera registo no audit log</p>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="bg-white border border-slate-200 rounded-xl p-1 h-auto flex-wrap">
          {Object.entries(CONFIG).map(([key, c]) => (
            <TabsTrigger key={key} value={key} data-testid={`tab-${key}`} className="rounded-lg px-4 py-2 text-sm data-[state=active]:bg-purple-600 data-[state=active]:text-white">{c.label}</TabsTrigger>
          ))}
        </TabsList>

        {Object.keys(CONFIG).map((key) => {
          const rows = db[key];
          const cols = CONFIG[key].fields.filter((f) => !f.hideInTable);
          return (
            <TabsContent key={key} value={key}>
              <div className="card-soft p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-slate-900">{CONFIG[key].label} <span className="text-sm font-normal text-slate-400">({rows?.length ?? "…"})</span></h3>
                  <button data-testid={`add-${key}-button`} onClick={openCreate} className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold btn-press"><Plus className="w-4 h-4" /> Adicionar</button>
                </div>
                <div className="overflow-x-auto -mx-5 px-5">
                  <table className="w-full text-sm" data-testid={`table-${key}`}>
                    <thead>
                      <tr className="text-left text-xs uppercase tracking-wider text-slate-400 border-b border-slate-100">
                        {cols.map((f) => <th key={f.key} className="pb-3 pr-4 font-semibold">{f.label.split(" (")[0]}</th>)}
                        <th className="pb-3 font-semibold text-right">Ações</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(rows || []).map((item) => (
                        <tr key={item.id} data-testid={`row-${item.id}`} className="border-b border-slate-50 last:border-0 hover:bg-purple-50/40 transition-colors">
                          {cols.map((f) => <td key={f.key} className="py-3 pr-4">{cell(f, item)}</td>)}
                          <td className="py-3 text-right whitespace-nowrap">
                            {key === "ebooks" && (
                              <label data-testid={`upload-pdf-${item.id}`} title={item.pdf_name ? `PDF: ${item.pdf_name}` : "Carregar PDF"} className={`inline-flex p-2 rounded-lg cursor-pointer btn-press ${item.pdf_path || item.pdf_name ? "text-emerald-600 hover:bg-emerald-50" : "text-slate-500 hover:bg-purple-50 hover:text-purple-600"} ${uploading === item.id ? "opacity-50 pointer-events-none" : ""}`}>
                                {item.pdf_name ? <FileCheck2 className="w-4 h-4" /> : <FileUp className="w-4 h-4" />}
                                <input type="file" accept="application/pdf" className="hidden" data-testid={`upload-pdf-input-${item.id}`} onChange={(e) => { uploadPdf(item, e.target.files?.[0]); e.target.value = ""; }} />
                              </label>
                            )}
                            <button data-testid={`edit-${item.id}`} onClick={() => openEdit(item)} className="p-2 rounded-lg text-slate-500 hover:bg-purple-50 hover:text-purple-600 btn-press"><Pencil className="w-4 h-4" /></button>
                            <button data-testid={`delete-${item.id}`} onClick={() => remove(item)} className="p-2 rounded-lg text-slate-500 hover:bg-red-50 hover:text-red-500 btn-press"><Trash2 className="w-4 h-4" /></button>
                          </td>
                        </tr>
                      ))}
                      {rows && rows.length === 0 && <tr><td colSpan={cols.length + 1} className="py-8 text-center text-slate-400">Sem registos.</td></tr>}
                    </tbody>
                  </table>
                </div>
              </div>
            </TabsContent>
          );
        })}
      </Tabs>

      <Dialog open={!!dialog} onOpenChange={() => setDialog(null)}>
        <DialogContent data-testid="entity-dialog" className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{dialog?.mode === "create" ? `Adicionar ${cfg.singular}` : `Editar ${cfg.singular}`}</DialogTitle>
            <DialogDescription>As alterações ficam registadas no audit log do servidor.</DialogDescription>
          </DialogHeader>
          <form onSubmit={save} className="space-y-3">
            {cfg.fields.map((f) => (
              <div key={f.key}>
                <label className="text-xs font-semibold text-slate-600 mb-1 block">{f.label}</label>
                {f.type === "select" ? (
                  <Select value={form[f.key] || ""} onValueChange={(v) => setForm((p) => ({ ...p, [f.key]: v }))}>
                    <SelectTrigger data-testid={`field-${f.key}`} className="rounded-xl bg-slate-50"><SelectValue /></SelectTrigger>
                    <SelectContent>{f.options.map((o) => <SelectItem key={o} value={o}>{f.key === "premium" ? (o === "true" ? "Premium (bloqueado)" : "Gratuito (preview)") : o}</SelectItem>)}</SelectContent>
                  </Select>
                ) : (
                  <Input data-testid={`field-${f.key}`} type={f.key === "password" ? "password" : "text"} placeholder={f.placeholder} value={form[f.key] || ""} onChange={(e) => setForm((p) => ({ ...p, [f.key]: e.target.value }))} className="rounded-xl bg-slate-50" />
                )}
              </div>
            ))}
            <button type="submit" disabled={busy} data-testid="entity-save-button" className="w-full py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-sm font-semibold btn-press">
              {busy ? "A guardar..." : dialog?.mode === "create" ? "Criar" : "Guardar"}
            </button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
