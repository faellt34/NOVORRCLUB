import { createContext, useContext, useMemo, useState } from "react";
import { USERS, INITIAL_REDEMPTIONS, PARTNER_COUPONS, ADMIN_SEED } from "../lib/mockData";

const AppContext = createContext(null);

export const AppProvider = ({ children }) => {
  const [role, setRole] = useState("influencer");
  const [redemptions, setRedemptions] = useState(INITIAL_REDEMPTIONS);
  const [auditLog, setAuditLog] = useState([]);
  const [processedTx, setProcessedTx] = useState(new Set());
  const [db, setDb] = useState(ADMIN_SEED);
  const [leads, setLeads] = useState([]);

  const user = USERS[role];

  const pushAudit = (action, detail) =>
    setAuditLog((prev) => [{ id: `a-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`, action, detail, date: new Date().toISOString() }, ...prev]);

  const addEntity = (type, data) => {
    const item = { id: `${type}-${Date.now()}`, ...data };
    setDb((prev) => ({ ...prev, [type]: [item, ...prev[type]] }));
    pushAudit("CRIAÇÃO", `${type} · ${data.nome || item.id}`);
    return item;
  };

  const updateEntity = (type, id, data) => {
    setDb((prev) => ({ ...prev, [type]: prev[type].map((e) => (e.id === id ? { ...e, ...data } : e)) }));
    pushAudit("EDIÇÃO", `${type} · ${data.nome || id}`);
  };

  const deleteEntity = (type, id) => {
    setDb((prev) => ({ ...prev, [type]: prev[type].filter((e) => e.id !== id) }));
    pushAudit("REMOÇÃO", `${type} · ${id}`);
  };

  const submitReferral = (lead) => {
    const item = { id: `lead-${Date.now()}`, ...lead, status: "Novo", date: new Date().toISOString() };
    setLeads((prev) => [item, ...prev]);
    pushAudit("INDICAÇÃO", `${lead.nome} · ${lead.categoria} · ${lead.cidade}`);
    return item;
  };

  const validateCoupon = (code, amount) => {
    const normalized = code.trim().toUpperCase();
    const coupon = PARTNER_COUPONS[normalized];
    if (!coupon) return { ok: false, error: "Cupom não encontrado para este parceiro." };
    if (coupon.status !== "Ativa") {
      const statusLabel = coupon.status === "Expirada" ? "expirado" : "pausado";
      return { ok: false, error: `Cupom ${statusLabel} — não pode ser redimido.` };
    }
    const value = parseFloat(String(amount).replace(",", "."));
    if (!value || value <= 0) return { ok: false, error: "Informe um valor de compra válido." };

    const txKey = `${normalized}-${value}-${Math.floor(Date.now() / 5000)}`;
    if (processedTx.has(txKey)) return { ok: false, error: "Redenção duplicada bloqueada (idempotência)." };

    const record = {
      id: `r-${Date.now()}`,
      coupon: normalized,
      influencer: coupon.influencer,
      amount: value,
      discount: +(value * (coupon.discountPct / 100)).toFixed(2),
      commission: +(value * coupon.commissionRate).toFixed(2),
      rate: coupon.commissionRate,
      date: new Date().toISOString(),
      staff: "Você",
    };
    setProcessedTx((prev) => new Set(prev).add(txKey));
    setRedemptions((prev) => [record, ...prev]);
    setAuditLog((prev) => [
      { id: `a-${Date.now()}`, action: "REDENÇÃO", detail: `${normalized} · ${record.amount.toFixed(2)}€ · taxa travada ${(coupon.commissionRate * 100).toFixed(0)}%`, date: record.date },
      ...prev,
    ]);
    return { ok: true, record, coupon };
  };

  const previewCoupon = (code) => PARTNER_COUPONS[String(code).trim().toUpperCase()] || null;

  const value = useMemo(
    () => ({ role, setRole, user, redemptions, validateCoupon, previewCoupon, auditLog, db, addEntity, updateEntity, deleteEntity, leads, submitReferral }),
    [role, user, redemptions, auditLog, processedTx, db, leads]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

export const useApp = () => useContext(AppContext);
