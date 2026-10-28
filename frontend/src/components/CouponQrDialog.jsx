import { useEffect, useRef, useState } from "react";
import { QRCodeCanvas } from "qrcode.react";
import { Copy, Download, Share2, Printer, FileText } from "lucide-react";
import { toast } from "sonner";
import { api, apiError, getSiteUrl, couponLink } from "../lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";

const round = (ctx, x, y, w, h, r) => { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); ctx.fill(); };

const loadImg = (src) => new Promise((res) => { if (!src) return res(null); const i = new Image(); i.crossOrigin = "anonymous"; i.onload = () => res(i); i.onerror = () => res(null); i.src = src; });

const fitText = (ctx, text, maxW, size, font) => { let s = size; do { ctx.font = `${font} ${s}px Inter, Arial, sans-serif`; s -= 2; } while (ctx.measureText(text).width > maxW && s > 20); };

export const renderCouponPng = async (qrCanvas, c, link) => {
  const W = 1080, H = 1350;
  const cv = document.createElement("canvas"); cv.width = W; cv.height = H;
  const ctx = cv.getContext("2d");
  ctx.fillStyle = "#0B1220"; ctx.fillRect(0, 0, W, H);
  const glow = ctx.createRadialGradient(W / 2, 330, 40, W / 2, 330, 700); glow.addColorStop(0, "rgba(124,58,237,.55)"); glow.addColorStop(1, "rgba(11,18,32,0)");
  ctx.fillStyle = glow; ctx.fillRect(0, 0, W, H);
  const photo = await loadImg(c.parceiro_foto || c.avatar);
  ctx.textAlign = "center";
  // brand
  ctx.fillStyle = "rgba(255,255,255,.6)"; ctx.font = "600 26px Inter, Arial, sans-serif"; ctx.fillText("R-CONEKTA  ·  BY RRCLUB", W / 2, 70);
  // partner header (photo + name)
  let y = 130;
  if (photo) {
    ctx.save(); ctx.beginPath(); ctx.arc(W / 2, y + 80, 80, 0, Math.PI * 2); ctx.closePath(); ctx.clip();
    ctx.drawImage(photo, W / 2 - 80, y, 160, 160); ctx.restore();
    ctx.strokeStyle = "#A78BFA"; ctx.lineWidth = 6; ctx.beginPath(); ctx.arc(W / 2, y + 80, 83, 0, Math.PI * 2); ctx.stroke();
    y += 200;
  }
  ctx.fillStyle = "#fff"; fitText(ctx, c.parceiro || "", 900, 60, "bold"); ctx.fillText(c.parceiro || "", W / 2, y + 40);
  ctx.fillStyle = "#C4B5FD"; ctx.font = "600 30px Inter, Arial, sans-serif"; ctx.fillText([c.categoria, c.cidade].filter((x) => x && x !== "—").join("  ·  "), W / 2, y + 85);
  // discount pill
  ctx.fillStyle = "#7C3AED"; round(ctx, W / 2 - 220, y + 115, 440, 84, 42);
  ctx.fillStyle = "#fff"; ctx.font = "bold 44px Inter, Arial, sans-serif"; ctx.fillText(`${c.desconto}% DE DESCONTO`, W / 2, y + 173);
  // QR card
  const qy = Math.max(y + 240, 520), qs = 620;
  ctx.fillStyle = "#fff"; round(ctx, W / 2 - qs / 2 - 30, qy - 30, qs + 60, qs + 60, 44);
  ctx.drawImage(qrCanvas, W / 2 - qs / 2, qy, qs, qs);
  // code + CTA
  ctx.fillStyle = "rgba(255,255,255,.08)"; round(ctx, W / 2 - 300, qy + qs + 60, 600, 90, 20);
  ctx.fillStyle = "#fff"; ctx.font = "bold 52px Courier New, monospace"; ctx.fillText(c.cupom, W / 2, qy + qs + 123);
  ctx.fillStyle = "rgba(255,255,255,.8)"; ctx.font = "600 28px Inter, Arial, sans-serif"; ctx.fillText("Aponte a câmara · pague com MB WAY, Apple Pay, cartão ou Pix", W / 2, qy + qs + 190);
  ctx.fillStyle = "rgba(255,255,255,.5)"; ctx.font = "26px Inter, Arial, sans-serif"; ctx.fillText(link.replace(/^https?:\/\//, ""), W / 2, H - 40);
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
            <QRCodeCanvas value={link} size={700} fgColor="#0B1220" level="H" includeMargin style={{ width: 200, height: 200 }}
              imageSettings={{ src: c.parceiro_foto || c.avatar || "/icon-192.png", height: 140, width: 140, excavate: true, crossOrigin: "anonymous" }} />
          </div>
          {c.parceiro_foto || c.avatar ? null : <p className="text-[11px] text-slate-400 text-center">Dica: o parceiro pode adicionar a foto do espaço no painel para aparecer no centro do QR e no cartaz.</p>}
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
