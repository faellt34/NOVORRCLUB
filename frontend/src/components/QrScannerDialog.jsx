import { useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { Camera, CameraOff } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";

export const extractCoupon = (text) => {
  const m = String(text).trim().match(/\/c\/([A-Za-z0-9-]+)/);
  return (m ? m[1] : String(text).trim()).toUpperCase();
};

export const QrScannerDialog = ({ open, onOpenChange, onDetected }) => {
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(true);
  const scannerRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    let stopped = false;
    setError(""); setStarting(true);
    const fallback = setTimeout(() => setError((e) => e || "Nenhuma câmara detetada neste dispositivo. Digite o código manualmente."), 6000);
    const t = setTimeout(async () => {
      const el = document.getElementById("qr-reader");
      if (!el) return;
      const scanner = new Html5Qrcode("qr-reader", { verbose: false });
      scannerRef.current = scanner;
      try {
        await scanner.start({ facingMode: "environment" }, { fps: 10, qrbox: { width: 240, height: 240 } }, (text) => {
          if (stopped) return;
          stopped = true;
          onDetected(extractCoupon(text));
          onOpenChange(false);
        }, () => {});
        clearTimeout(fallback);
        setStarting(false);
      } catch (e) {
        clearTimeout(fallback);
        setStarting(false);
        setError(String(e?.message || e).includes("Permission") || String(e).includes("NotAllowed")
          ? "Permissão de câmara negada. Autorize a câmara no navegador ou digite o código."
          : "Não foi possível aceder à câmara neste dispositivo. Digite o código manualmente.");
      }
    }, 150);
    return () => {
      clearTimeout(t);
      clearTimeout(fallback);
      stopped = true;
      const s = scannerRef.current;
      scannerRef.current = null;
      if (s) s.stop().then(() => s.clear()).catch(() => {});
    };
  }, [open, onDetected, onOpenChange]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="scanner-modal" className="max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Camera className="w-4 h-4 text-purple-600" /> Ler QR do cliente</DialogTitle>
          <DialogDescription>Aponte a câmara para o QR code do cupom — a leitura é automática</DialogDescription>
        </DialogHeader>
        <div className="relative rounded-2xl bg-slate-950 overflow-hidden min-h-[280px]">
          <div id="qr-reader" data-testid="qr-reader" className="w-full [&_video]:rounded-2xl" />
          {starting && !error && <p className="absolute inset-0 flex items-center justify-center text-xs text-slate-400" data-testid="scanner-starting">A iniciar câmara...</p>}
          {error && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 p-6 text-center" data-testid="scanner-error">
              <CameraOff className="w-8 h-8 text-slate-500" />
              <p className="text-xs text-slate-300">{error}</p>
            </div>
          )}
          {!starting && !error && <div className="scanner-line absolute left-[15%] right-[15%] h-0.5 bg-purple-400 shadow-[0_0_12px_rgba(167,139,250,0.9)] pointer-events-none" />}
        </div>
      </DialogContent>
    </Dialog>
  );
};
