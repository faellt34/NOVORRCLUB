import { useEffect, useState } from "react";
import { Camera, Loader2, Upload } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "./ui/dialog";
import { api, apiError } from "../lib/api";
import { useApp } from "../context/AppContext";
import { toast } from "sonner";

export default function ProfilePhotoDialog({ open, onOpenChange, kind = "avatar" }) {
  const { user, refreshUser } = useApp();
  const cover = kind === "cover";
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!file) { setPreview(""); return; }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const close = (value) => {
    if (busy) return;
    if (!value) setFile(null);
    onOpenChange(value);
  };

  const upload = async () => {
    if (!file || busy) return;
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      await api.post(cover ? "/profile/cover" : "/profile/avatar", form);
      await refreshUser();
      toast.success(cover ? "Capa do estabelecimento atualizada" : "Fotografia atualizada no perfil e nas campanhas");
      setFile(null);
      onOpenChange(false);
    } catch (error) {
      toast.error(apiError(error));
    } finally {
      setBusy(false);
    }
  };

  const choose = (event) => {
    const chosen = event.target.files?.[0];
    event.target.value = "";
    if (!chosen) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(chosen.type)) {
      toast.error("Escolha uma imagem JPG, PNG ou WebP");
      return;
    }
    if (chosen.size > 3 * 1024 * 1024) {
      toast.error("A fotografia deve ter no máximo 3 MB");
      return;
    }
    setFile(chosen);
  };

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="sm:max-w-md" data-testid="profile-photo-dialog">
        <DialogHeader>
          <DialogTitle>{cover ? "Capa do estabelecimento" : "Fotografia do perfil"}</DialogTitle>
          <DialogDescription>
            {cover
              ? "Escolha uma fotografia do restaurante, hotel ou estabelecimento para aparecer nas campanhas."
              : user?.role === "partner"
                ? "Escolha a imagem ou logótipo do estabelecimento. Será apresentada nos cupões associados."
                : "Escolha a sua fotografia. Será apresentada no perfil e nas campanhas associadas."}
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col items-center gap-4 py-3">
          <div className="relative">
            {preview || (cover ? user?.cover_image : user?.avatar) ? (
              <img src={preview || (cover ? user?.cover_image : user?.avatar)} alt="Pré-visualização da fotografia"
                className={cover ? "h-36 w-full rounded-xl object-cover ring-4 ring-indigo-100" : "h-28 w-28 rounded-full object-cover ring-4 ring-indigo-100"} />
            ) : (
              <div className={cover ? "h-36 w-full rounded-xl bg-slate-100 flex items-center justify-center" : "h-28 w-28 rounded-full bg-slate-100 flex items-center justify-center"}>
                <Camera className="h-9 w-9 text-slate-400" />
              </div>
            )}
          </div>
          <label className="cursor-pointer inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold hover:bg-slate-50">
            <Camera className="h-4 w-4" /> Escolher fotografia
            <input type="file" accept="image/jpeg,image/png,image/webp" className="sr-only"
              onChange={choose} disabled={busy} data-testid="profile-photo-input" />
          </label>
          <p className="text-center text-xs text-slate-500">{cover ? "JPG, PNG ou WebP · até 3 MB · formato horizontal recomendado" : "JPG, PNG ou WebP · até 3 MB · imagem quadrada recomendada"}</p>
          <button type="button" onClick={upload} disabled={!file || busy}
            data-testid="profile-photo-save"
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50 hover:bg-indigo-700">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            {busy ? "A guardar..." : "Guardar fotografia"}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
