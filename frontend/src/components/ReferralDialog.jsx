import { useState } from "react";
import { Send } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "../lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";

const INITIAL = { nome: "", categoria: "Restaurante", cidade: "Lisboa", contacto: "", nota: "" };

export const ReferralDialog = ({ open, onOpenChange, onCreated }) => {
  const [form, setForm] = useState(INITIAL);
  const [loading, setLoading] = useState(false);

  const set = (key) => (e) => setForm((p) => ({ ...p, [key]: e.target?.value ?? e }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.nome.trim() || !form.contacto.trim()) {
      toast.error("Preencha o nome do espaço e o contacto.");
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.post("/leads", form);
      toast.success("Indicação enviada! O admin foi notificado e vai avaliar o parceiro.");
      onCreated?.(data);
      setForm(INITIAL);
      onOpenChange(false);
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="referral-dialog" className="max-w-md">
        <DialogHeader>
          <DialogTitle>Indicar um parceiro</DialogTitle>
          <DialogDescription>Conhece um espaço premium? Indique-o e ganhe bónus se for aprovado.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-xs font-semibold text-slate-600 mb-1 block">Nome do espaço *</label>
            <Input data-testid="referral-nome-input" value={form.nome} onChange={set("nome")} placeholder="Ex.: Bairro Alto Hotel Rooftop" className="rounded-xl bg-slate-50" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-600 mb-1 block">Categoria</label>
              <Select value={form.categoria} onValueChange={(v) => setForm((p) => ({ ...p, categoria: v }))}>
                <SelectTrigger data-testid="referral-categoria-select" className="rounded-xl bg-slate-50"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {["Restaurante", "Hotel", "Rooftop", "Passeio"].map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 mb-1 block">Cidade</label>
              <Select value={form.cidade} onValueChange={(v) => setForm((p) => ({ ...p, cidade: v }))}>
                <SelectTrigger data-testid="referral-cidade-select" className="rounded-xl bg-slate-50"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {["Lisboa", "Porto", "Algarve", "Douro", "Madrid", "Paris", "Roma", "Dubai", "Outra"].map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-600 mb-1 block">Contacto (email ou telefone) *</label>
            <Input data-testid="referral-contacto-input" value={form.contacto} onChange={set("contacto")} placeholder="geral@espaco.pt" className="rounded-xl bg-slate-50" />
            <p className="text-[11px] text-slate-400 mt-1">Se for um email, a conta de acesso do parceiro é criada automaticamente após aprovação.</p>
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-600 mb-1 block">Nota (opcional)</label>
            <Textarea data-testid="referral-nota-input" value={form.nota} onChange={set("nota")} placeholder="Porque é um bom fit para o Robson Club?" className="rounded-xl bg-slate-50 min-h-[70px]" />
          </div>
          <button type="submit" disabled={loading} data-testid="referral-submit-button" className="w-full py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-sm font-semibold inline-flex items-center justify-center gap-2 btn-press">
            <Send className="w-4 h-4" /> {loading ? "A enviar..." : "Enviar indicação"}
          </button>
        </form>
      </DialogContent>
    </Dialog>
  );
};
