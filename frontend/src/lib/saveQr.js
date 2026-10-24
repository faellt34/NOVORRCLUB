// Use the rendered QR, so a P5 download preserves its scan reference and never
// includes the follower's private session token.
export async function saveQr(svg, filename) {
  if (!svg) throw new Error("O QR ainda não está disponível. Aguarde e tente novamente.");
  const markup = new XMLSerializer().serializeToString(svg);
  const source = URL.createObjectURL(new Blob([markup], { type: "image/svg+xml;charset=utf-8" }));
  try {
    const image = new Image();
    await new Promise((resolve, reject) => {
      image.onload = resolve;
      image.onerror = () => reject(new Error("Não foi possível preparar a imagem do QR."));
      image.src = source;
    });
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 600;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Este navegador não conseguiu preparar o QR.");
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, 600, 600);
    ctx.drawImage(image, 30, 30, 540, 540);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
    if (!blob) throw new Error("Não foi possível criar o ficheiro do QR.");
    const file = new File([blob], filename, { type: "image/png" });
    if (navigator.canShare?.({ files: [file] }) && navigator.share) {
      try {
        await navigator.share({ files: [file], title: "QR RRClub" });
        return "shared";
      } catch (error) {
        if (error.name === "AbortError") return "cancelled";
        // The browser may reject sharing after PNG conversion. Use download.
      }
    }
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.target = "_blank";
    anchor.rel = "noopener";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    // Safari needs the object URL to remain valid while it opens the image.
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    return "download";
  } finally {
    URL.revokeObjectURL(source);
  }
}
