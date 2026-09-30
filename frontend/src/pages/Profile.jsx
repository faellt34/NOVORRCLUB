import { useEffect, useRef, useState } from "react";
import { Camera, CheckCircle2, Upload } from "lucide-react";
import { toast } from "sonner";
import { useApp } from "../context/AppContext";
import { api, apiError } from "../lib/api";

export default function Profile() {
  const { user, refreshUser } = useApp();
  const inputRef = useRef(null);
  const [preview, setPreview] = useState(user?.avatar);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => () => preview?.startsWith("blob:") && URL.revokeObjectURL(preview), [preview]);

  const chooseFile = (event) => {
    const selected = event.target.files?.[0];
    if (!selected) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(selected.type)) {
      toast.error("Escolha uma imagem JPG, PNG ou WebP.");
      return;
    }
    if (selected.size > 5 * 1024 * 1024) {
      toast.error("A fotografia deve ter no máximo 5 MB.");
      return;
    }
    if (preview?.startsWith("blob:")) URL.revokeObjectURL(preview);
    setFile(selected);
    setPreview(URL.createObjectURL(selected));
  };

  const save = async () => {
    if (!file) return;
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post("/auth/profile/avatar", form);
      await refreshUser();
      setFile(null);
      setPreview(data.user.avatar);
      toast.success("Fotografia do perfil atualizada.");
    } catch (error) {
      toast.error(apiError(error));
    } finally {
      setBusy(false);
    }
  };

  if (!user) return null;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 data-testid="profile-title" className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Meu perfil</h1>
        <p className="text-sm text-slate-500 mt-1">Atualize a fotografia que aparece na sua área e nas mensagens.</p>
      </div>

      <section className="card-soft p-6 sm:p-8" data-testid="profile-photo-card">
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
          <div className="relative">
            <img src={preview} alt={user.nome} className="w-32 h-32 rounded-full object-cover ring-4 ring-purple-100" />
            <button type="button" onClick={() => inputRef.current?.click()} aria-label="Escolher fotografia" className="absolute bottom-0 right-0 w-10 h-10 rounded-full bg-purple-600 hover:bg-purple-500 text-white flex items-center justify-center shadow-lg">
              <Camera className="w-5 h-5" />
            </button>
          </div>
          <div className="flex-1 text-center sm:text-left">
            <h2 className="text-lg font-semibold text-slate-900">{user.nome}</h2>
            <p className="text-sm text-slate-500 mt-1">{user.email}</p>
            <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={chooseFile} className="hidden" data-testid="profile-photo-input" />
            <button type="button" onClick={() => inputRef.current?.click()} className="mt-5 inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 hover:bg-purple-50 text-sm font-semibold text-slate-700">
              <Upload className="w-4 h-4" /> Escolher fotografia
            </button>
            <p className="text-xs text-slate-400 mt-3">JPG, PNG ou WebP · máximo 5 MB</p>
            {file && (
              <button type="button" onClick={save} disabled={busy} data-testid="profile-photo-save" className="mt-4 inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white text-sm font-semibold">
                <CheckCircle2 className="w-4 h-4" /> {busy ? "A guardar..." : "Guardar fotografia"}
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
