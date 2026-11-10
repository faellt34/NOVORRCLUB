import React, { useRef, useState } from "react";
import { Copy, Download, QrCode, ShieldCheck } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";

export default function PreviewQrCard({ country = "PT" }) {
 const [copied,setCopied] = useState(false);
 const qrRef = useRef(null);
 const code = "DEMO-INVERNO";
 const download = () => {
   const svg=qrRef.current?.querySelector("svg");
   if (!svg) return;
   const clone=svg.cloneNode(true);
   clone.setAttribute("xmlns","http://www.w3.org/2000/svg");
   const xml=new XMLSerializer().serializeToString(clone);
   const url=URL.createObjectURL(new Blob([xml],{type:"image/svg+xml;charset=utf-8"}));
   const a=document.createElement("a");a.href=url;a.download="rrclub-qr-demo.svg";a.click();URL.revokeObjectURL(url);
 };
 const copy = async () => {
   try {await navigator.clipboard.writeText(code);setCopied(true);}
   catch {setCopied(false);}
 };
 return <section className="rounded-2xl border border-[#DCE6EE] bg-white p-4 sm:p-6 shadow-sm" aria-label="QR Code fictício">
   <p className="uppercase text-[11px] tracking-widest text-[#477FAE] font-bold">Campanhas · QR Code</p>
   <h2 className="text-xl font-extrabold text-[#203047] mt-1">QR para demonstração</h2>
   <p className="text-sm text-slate-600 mt-2 mb-5">Código fictício para validar o fluxo visual do parceiro. Não representa campanha ou cupom oficial.</p>
   <div className="flex flex-col sm:flex-row gap-5 sm:items-center">
     <div ref={qrRef} className="p-4 w-fit rounded-2xl bg-white border border-slate-200 mx-auto sm:mx-0">
       <QRCodeSVG value={"RRCLUB-DEMO:"+country+":"+code} size={164} level="M" marginSize={0} fgColor="#203047" bgColor="#FFFFFF"/>
     </div>
     <div className="flex-1 min-w-0">
       <div className="text-xs text-slate-500">Campanha fictícia · {country}</div>
       <div className="font-extrabold text-lg tracking-wider text-[#203047] mt-1">{code}</div>
       <p className="text-xs text-slate-500 mt-2">No simulador, utiliza o texto <strong>{code}</strong> para validar. A câmara não é ativada nesta versão.</p>
       <div className="flex flex-wrap gap-2 mt-4">
         <button type="button" onClick={copy} className="inline-flex items-center gap-2 rounded-xl border px-3 py-2.5 font-semibold text-sm"><Copy size={16}/>{copied?"Copiado":"Copiar código"}</button>
         <button type="button" onClick={download} className="inline-flex items-center gap-2 rounded-xl bg-[#203047] text-white px-3 py-2.5 font-semibold text-sm"><Download size={16}/> Descarregar QR</button>
       </div>
     </div>
   </div>
   <p className="mt-5 pt-4 border-t border-slate-100 text-xs text-slate-500 flex items-center gap-2"><ShieldCheck size={15}/> QR contém apenas identificador fictício, sem dados de utilizadores.</p>
 </section>;
}
