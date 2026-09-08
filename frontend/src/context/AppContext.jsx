import { createContext, useContext, useMemo, useState } from "react";
import { USERS, INITIAL_REDEMPTIONS, PARTNER_COUPONS } from "../lib/mockData";

const AppContext = createContext(null);

export const AppProvider = ({ children }) => {
  const [role, setRole] = useState("influencer");
  const [redemptions, setRedemptions] = useState(INITIAL_REDEMPTIONS);
  const [auditLog, setAuditLog] = useState([]);
  const [processedTx, setProcessedTx] = useState(new Set());

  const user = USERS[role];

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
    () => ({ role, setRole, user, redemptions, validateCoupon, previewCoupon, auditLog }),
    [role, user, redemptions, auditLog, processedTx]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

export const useApp = () => useContext(AppContext);
