import { useState } from "react";
import { Lightbulb, Send } from "lucide-react";
import { useLocation } from "react-router-dom";
import { toast } from "sonner";
import { api, apiError } from "../lib/api";
import { useT } from "../context/I18nContext";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";
import { Textarea } from "./ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";

const TYPES = ["Melhoria", "Nova funcionalidade", "Erro / Bug", "Outro"];

export const FeedbackDialog = ({ open, onOpenChange }) => {
  const { t } = useT();
  const { pathname } = useLocation();
  const [tipo, setTipo] = useState(TYPES[0]);
  const [mensagem, setMensagem] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/feedback", { tipo, mensagem, pagina: pathname });
      toast.success(t("sent")); setMensagem(""); onOpenChange(false);
    } catch (err) { toast.error(apiError(err)); } finally { setLoading(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="feedback-dialog" className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Lightbulb className="w-4 h-4 text-amber-500" /> {t("suggestTitle")}</DialogTitle>
          <DialogDescription>{t("suggestText")}</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="text-xs font-semibold text-slate-600 mb-1 block">{t("type")}</label>
            <Select value={tipo} onValueChange={setTipo}>
              <SelectTrigger data-testid="feedback-type-select" className="rounded-xl bg-slate-50"><SelectValue /></SelectTrigger>
              <SelectContent>{TYPES.map((x) => <SelectItem key={x} value={x}>{x}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-600 mb-1 block">{t("message")}</label>
            <Textarea data-testid="feedback-message-input" value={mensagem} onChange={(e) => setMensagem(e.target.value)} className="rounded-xl bg-slate-50 min-h-[110px]" placeholder="..." />
          </div>
          <button type="submit" disabled={loading || mensagem.trim().length < 5} data-testid="feedback-submit-button" className="w-full py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-sm font-semibold inline-flex items-center justify-center gap-2 btn-press"><Send className="w-4 h-4" /> {t("send")}</button>
        </form>
      </DialogContent>
    </Dialog>
  );
};
