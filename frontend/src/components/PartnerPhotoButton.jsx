import { useRef, useState } from "react";
import { Camera } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "../lib/api";

const compress = (file) => new Promise((resolve, reject) => {
  const img = new Image();
  img.onload = () => {
    const S = 512, side = Math.min(img.width, img.height);
    const cv = document.createElement("canvas"); cv.width = S; cv.height = S;
    cv.getContext("2d").drawImage(img, (img.width - side) / 2, (img.height - side) / 2, side, side, 0, 0, S, S);
    let q = 0.85, out = cv.toDataURL("image/jpeg", q);
    while (out.length > 180_000 && q > 0.4) { q -= 0.1; out = cv.toDataURL("image/jpeg", q); }
    URL.revokeObjectURL(img.src); resolve(out);
  };
  img.onerror = reject;
  img.src = URL.createObjectURL(file);
});

export const PartnerPhotoButton = ({ current, onSaved }) => {
  const input = useRef(null);
  const [busy, setBusy] = useState(false);
  const pick = async (e) => {
    const file = e.target.files?.[0]; e.target.value = "";
    if (!file) return;
    if (!/^image\/(png|jpeg|webp)$/.test(file.type)) return toast.error("Use uma imagem PNG, JPEG ou WEBP");
    setBusy(true);
    try { await api.post("/partner/foto", { foto: await compress(file) }); toast.success("Foto do espaço atualizada — já aparece no cupão e no QR"); onSaved?.(); }
    catch (err) { toast.error(apiError(err)); } finally { setBusy(false); }
  };
  return (
    <button type="button" data-testid="partner-photo-button" disabled={busy} onClick={() => input.current?.click()} className="relative w-14 h-14 rounded-2xl overflow-hidden border-2 border-white shadow-md bg-slate-100 shrink-0 btn-press" title="Foto do espaço (aparece no cupão e no QR)">
      {current ? <img src={current} alt="" className="w-full h-full object-cover" /> : <Camera className="w-5 h-5 text-slate-400 absolute inset-0 m-auto" />}
      <span className="absolute bottom-0 inset-x-0 bg-black/55 text-white text-[9px] font-semibold py-0.5">{busy ? "..." : "Foto"}</span>
      <input ref={input} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={pick} data-testid="partner-photo-input" />
    </button>
  );
};
