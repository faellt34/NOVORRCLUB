import { useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { Camera, CameraOff, ImageUp } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";

export const extractCoupon = (text) => {
  const m = String(text).trim().match(/\/c\/([A-Za-z0-9-]+)/);
  return (m ? m[1] : String(text).trim()).toUpperCase();
};

const cameraError = (e) => {
  const s = `${e?.name || ""} ${e?.message || e || ""}`;
  if (/NotAllowed|Permission|denied/i.test(s)) return "Permissão de câmara negada. Autorize a câmara nas definições do navegador ou use uma foto do QR.";
  if (/NotFound|no camera|Requested device not found/i.test(s)) return "Nenhuma câmara detetada neste dispositivo. Use uma foto do QR ou digite o código.";
  if (/NotReadable|in use|Could not start/i.test(s)) return "A câmara está a ser usada por outra aplicação. Feche-a e tente novamente.";
  if (!window.isSecureContext) return "A câmara só funciona em HTTPS. Abra o site pelo endereço seguro.";
  return "Não foi possível aceder à câmara. Use uma foto do QR ou digite o código.";
};

export const QrScannerDialog = ({ open, onOpenChange, onDetected }) => {
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(true);
  const scannerRef = useRef(null);
  const doneRef = useRef(false);

  const finish = (text) => {
    if (doneRef.current) return;
    doneRef.current = true;
    onDetected(extractCoupon(text));
    onOpenChange(false);
  };

  useEffect(() => {
    if (!open) return;
    doneRef.current = false;
    setError(""); setStarting(true);
    const fallback = setTimeout(() => setError((e) => e || "A câmara demora a responder. Use uma foto do QR ou digite o código."), 8000);
    const t = setTimeout(async () => {
      const el = document.getElementById("qr-reader");
      if (!el) return;
      const scanner = new Html5Qrcode("qr-reader", { verbose: false });
      scannerRef.current = scanner;
      try {
        await scanner.start({ facingMode: "environment" }, { fps: 10, qrbox: (w, h) => { const s = Math.min(w, h) * 0.75; return { width: s, height: s }; } }, finish, () => {});
        clearTimeout(fallback);
        setStarting(false);
      } catch (e) {
        clearTimeout(fallback);
        setStarting(false);
        setError(cameraError(e));
      }
    }, 150);
    return () => {
      clearTimeout(t);
      clearTimeout(fallback);
      const s = scannerRef.current;
      scannerRef.current = null;
      if (s) {
        try {
          const p = s.getState && s.getState() === 2 ? s.stop() : Promise.resolve();
          p.then(() => { try { s.clear(); } catch {} }).catch(() => {});
        } catch { try { s.clear(); } catch {} }
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const scanFile = async (file) => {
    if (!file) return;
    const s = scannerRef.current;
    if (s) {
      try {
        if (s.getState && s.getState() === 2) await s.stop();
      } catch {}
    }
    const reader = new Html5Qrcode("qr-file-reader", { verbose: false });
    try { finish(await reader.scanFile(file, false)); }
    catch { setError("Não foi possível ler um QR nesta foto. Tente aproximar ou digite o código."); }
    finally { try { reader.clear(); } catch {} }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="scanner-modal" className="max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Camera className="w-4 h-4 text-purple-600" /> Ler QR do cliente</DialogTitle>
          <DialogDescription>Aponte a câmara para o QR code do cupom — a leitura é automática</DialogDescription>
        </DialogHeader>
        <div className="relative rounded-2xl bg-slate-950 overflow-hidden min-h-[280px]">
          <div id="qr-reader" data-testid="qr-reader" className="w-full [&_video]:rounded-2xl [&_video]:object-cover" />
          <div id="qr-file-reader" className="hidden" />
          {starting && !error && <p className="absolute inset-0 flex items-center justify-center text-xs text-slate-400" data-testid="scanner-starting">A iniciar câmara...</p>}
          {error && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 p-6 text-center bg-slate-950" data-testid="scanner-error">
              <CameraOff className="w-8 h-8 text-slate-500" />
              <p className="text-xs text-slate-300">{error}</p>
            </div>
          )}
          {!starting && !error && <div className="scanner-line absolute left-[15%] right-[15%] h-0.5 bg-purple-400 shadow-[0_0_12px_rgba(167,139,250,0.9)] pointer-events-none" />}
        </div>
        <label data-testid="scanner-upload-photo" className="w-full py-2.5 rounded-xl bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-semibold inline-flex items-center justify-center gap-2 cursor-pointer btn-press">
          <ImageUp className="w-4 h-4" /> Usar foto do QR (galeria / captura)
          <input type="file" accept="image/*" capture="environment" className="hidden" data-testid="scanner-upload-input" onChange={(e) => { scanFile(e.target.files?.[0]); e.target.value = ""; }} />
        </label>
      </DialogContent>
    </Dialog>
  );
};
