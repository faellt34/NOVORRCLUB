import { useEffect, useState } from "react";
import { X, Download } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "../lib/api";

export const PdfReader = ({ ebook, onClose }) => {
  const [url, setUrl] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ebook) { setUrl(null); return; }
    let objectUrl = null;
    setLoading(true);
    api.get(`/ebooks/${ebook.id}/pdf`, { responseType: "blob" })
      .then((r) => { objectUrl = URL.createObjectURL(r.data); setUrl(objectUrl); })
      .catch(async (e) => {
        let msg = apiError(e);
        try { msg = JSON.parse(await e.response?.data?.text())?.detail || msg; } catch {}
        toast.error(msg); onClose();
      })
      .finally(() => setLoading(false));
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [ebook, onClose]);

  if (!ebook) return null;
  return (
    <div className="fixed inset-0 z-[60] bg-slate-950/95 flex flex-col" data-testid="pdf-reader">
      <div className="flex items-center justify-between px-4 h-14 text-white border-b border-white/10">
        <div className="min-w-0">
          <p className="text-sm font-semibold truncate" data-testid="pdf-reader-title">{ebook.titulo}</p>
          <p className="text-[11px] text-slate-400">{ebook.pais} · {ebook.regiao} · {ebook.paginas} páginas</p>
        </div>
        <div className="flex items-center gap-2">
          {url && <a href={url} download={`${ebook.titulo}.pdf`} data-testid="pdf-download-button" className="p-2 rounded-lg hover:bg-white/10"><Download className="w-5 h-5" /></a>}
          <button data-testid="pdf-reader-close" onClick={onClose} className="p-2 rounded-lg hover:bg-white/10"><X className="w-5 h-5" /></button>
        </div>
      </div>
      <div className="flex-1 bg-slate-900">
        {loading && <p className="text-slate-400 text-sm text-center pt-20" data-testid="pdf-loading">A carregar o guia...</p>}
        {url && <iframe title={ebook.titulo} src={url} className="w-full h-full" data-testid="pdf-iframe" />}
      </div>
    </div>
  );
};
