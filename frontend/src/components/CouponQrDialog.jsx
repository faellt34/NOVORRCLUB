import { useEffect, useRef, useState } from "react";
import { QRCodeCanvas } from "qrcode.react";
import { Copy, Download, Share2, Printer, FileText } from "lucide-react";
import { toast } from "sonner";
import { api, apiError, getSiteUrl, couponLink } from "../lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";

const round = (ctx, x, y, w, h, r) => { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); ctx.fill(); };

export const renderCouponPng = (qrCanvas, c, link) => {
  const W = 1080, H = 1350;
  const cv = document.createElement("canvas"); cv.width = W; cv.height = H;
  const ctx = cv.getContext("2d");
  const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, "#5B21B6"); g.addColorStop(1, "#08061A");
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = "#fff"; ctx.textAlign = "center";
  ctx.font = "bold 92px Georgia, serif"; ctx.fillText("RRclub", W / 2, 150);
  ctx.font = "600 34px Inter, Arial, sans-serif"; ctx.fillStyle = "rgba(255,255,255,.75)"; ctx.fillText(`EXPERIÊNCIAS PREMIUM · ${link.replace(/^https?:\/\//, "").split("/")[0]}`, W / 2, 205);
  ctx.fillStyle = "#fff"; round(ctx, 140, 270, 800, 800, 48);
  ctx.drawImage(qrCanvas, 190, 320, 700, 700);
  ctx.fillStyle = "#7C3AED"; round(ctx, 190, 1110, 700, 96, 24);
  ctx.fillStyle = "#fff"; ctx.font = "bold 54px Courier New, monospace"; ctx.fillText(c.cupom, W / 2, 1176);
  ctx.font = "bold 44px Inter, Arial, sans-serif"; ctx.fillText(`${c.desconto}% OFF · ${c.parceiro || ""}`, W / 2, 1265);
  ctx.font = "30px Inter, Arial, sans-serif"; ctx.fillStyle = "rgba(255,255,255,.7)"; ctx.fillText(link.replace(/^https?:\/\//, ""), W / 2, 1315);
  return new Promise((res) => cv.toBlob(res, "image/png"));
};

export const CouponQrDialog = ({ campaign: c, open, onOpenChange }) => {
  const ref = useRef(null);
  const [busy, setBusy] = useState(false);
  const [site, setSite] = useState(window.location.origin);
  useEffect(() => { getSiteUrl().then(setSite); }, []);
  if (!c) return null;
  const link = couponLink(site, c.cupom);
  const msg = `${c.desconto}% OFF em ${c.parceiro} com o meu cupão ${c.cupom}: ${link}`;

  const png = () => renderCouponPng(ref.current?.querySelector("canvas"), c, link);

  const download = async () => {
    setBusy(true);
    try {
      const blob = await png();
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `cupao-${c.cupom}.png`; a.click(); URL.revokeObjectURL(a.href);
      toast.success("Imagem do cupão descarregada (PNG)");
    } finally { setBusy(false); }
  };

  const share = async () => {
    setBusy(true);
    try {
      const blob = await png();
      const file = new File([blob], `cupao-${c.cupom}.png`, { type: "image/png" });
      if (navigator.canShare?.({ files: [file] })) { await navigator.share({ files: [file], text: msg, title: `Cupão ${c.cupom}` }); return; }
      window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`, "_blank");
    } catch (e) { if (e?.name !== "AbortError") toast.error("Não foi possível partilhar neste dispositivo"); }
    finally { setBusy(false); }
  };

  const copy = () => { navigator.clipboard?.writeText(link).catch(() => {}); toast.success("Link copiado"); };
  const print = () => { const w = window.open("", "_blank"); png().then((b) => { const u = URL.createObjectURL(b); w.document.write(`<img src="${u}" style="width:100%;max-width:600px" onload="window.print()">`); }); };
  const poster = async () => {
    setBusy(true);
    try {
      const r = await api.get(`/campaigns/${c.id}/poster.pdf`, { params: { site }, responseType: "blob", timeout: 60000 });
      const a = document.createElement("a"); a.href = URL.createObjectURL(r.data); a.download = `cartaz-${c.cupom}.pdf`; a.click(); URL.revokeObjectURL(a.href);
      toast.success("Cartaz A5 descarregado — imprima e coloque na mesa/balcão");
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="coupon-qr-dialog" className="max-w-sm">
        <DialogHeader>
          <DialogTitle>QR do cupão {c.cupom}</DialogTitle>
          <DialogDescription>{c.parceiro} · {c.desconto}% OFF — o cliente abre o link, paga ou mostra ao parceiro para validar</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col items-center gap-4">
          <div ref={ref} data-testid="coupon-qr-canvas" className="p-3 bg-white rounded-2xl border-2 border-purple-100">
            <QRCodeCanvas value={link} size={700} fgColor="#3B0764" level="M" includeMargin style={{ width: 200, height: 200 }} />
          </div>
          <p className="text-xs text-slate-500 break-all text-center" data-testid="coupon-qr-link">{link}</p>
          <div className="grid grid-cols-4 gap-2 w-full">
            {[
              ["copy", Copy, "Copiar", copy],
              ["download", Download, "PNG", download],
              ["share", Share2, "Partilhar", share],
              ["print", Printer, "Imprimir", print],
            ].map(([k, Icon, label, fn]) => (
              <button key={k} data-testid={`coupon-qr-${k}`} disabled={busy} onClick={fn} className="flex flex-col items-center gap-1 py-2.5 rounded-xl bg-purple-50 hover:bg-purple-100 disabled:opacity-60 text-purple-700 btn-press">
                <Icon className="w-4 h-4" /><span className="text-[10px] font-semibold">{label}</span>
              </button>
            ))}
          </div>
          <button data-testid="coupon-qr-poster" disabled={busy} onClick={poster} className="w-full py-2.5 rounded-xl bg-gradient-to-r from-[#5B21B6] to-[#08061A] hover:opacity-90 disabled:opacity-60 text-white text-xs font-semibold inline-flex items-center justify-center gap-2 btn-press">
            <FileText className="w-4 h-4" /> {busy ? "A preparar..." : "Cartaz A5 para mesa / balcão (PDF)"}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
