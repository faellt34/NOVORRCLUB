import React, { act } from "react";
import { createRoot } from "react-dom/client";
import FinanceReconciliationPanel from "./FinanceReconciliationPanel";
import { api } from "../lib/api";

jest.mock("../lib/api", () => ({
  api: { get: jest.fn() },
  apiError: (e) => e?.message || "Falha de comunicação",
  moneyIn: (v) => `${v} EUR`,
}));

let root, container;

beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  api.get.mockReset();
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
});

test("auditoria verifica na Stripe mesmo quando o ledger local ainda está pending", async () => {
  api.get
    .mockResolvedValueOnce({ data: [
      { session_id: "cs_unit", coupon: "RR-BBB7", partner: "Parceiro exemplo",
        influencer: "Influenciador por conciliar",
        payment_status: "pending", amount: 0.9, attribution_source: "current_campaign_unverified" },
    ] })
    .mockResolvedValueOnce({ data: {
      state: "no_transfer_evidence", stripe_session_paid: true, ledger_discrepancy: true,
      local_payment_status: "pending",
      fee_verified: true, stripe_gross_minor: 90, stripe_fee_minor: 26,
      stripe_net_minor: 64, commission_minor: 5, fee_exceeds_commission: true,
      payment_method_actual: "mb_way",
    } });

  await act(async () => {
    root.render(<FinanceReconciliationPanel />);
  });
  expect(container.textContent).toContain("RR-BBB7");
  const btn = Array.from(container.querySelectorAll("button"))
    .find((x) => x.textContent.includes("Verificar na Stripe"));
  expect(btn).toBeDefined();
  expect(btn.disabled).toBe(false);
  await act(async () => {
    btn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
  expect(api.get).toHaveBeenCalledWith("/admin/finance/reconciliation/cs_unit");
  expect(container.textContent).toContain(
    "Stripe confirmou; registo da RRClub está pendente de reconciliação"
  );
  expect(container.textContent).toContain("Sem comprovativo de transferência");
  expect(container.textContent).toContain("MB WAY");
  expect(container.textContent).toContain("0.26 EUR");
  expect(container.textContent).toContain("0.64 EUR");
  expect(container.textContent).toContain("0.05 EUR");
  expect(container.textContent).toContain(
    "a taxa Stripe é superior à comissão contabilizada"
  );
});

test("consulta read-only não é um botão de repasse ou de marcar como pago", async () => {
  api.get.mockResolvedValueOnce({ data: [] });
  await act(async () => { root.render(<FinanceReconciliationPanel />); });
  const allText = container.textContent.toLowerCase();
  expect(allText).not.toContain("executar repasse");
  expect(allText).not.toContain("marcar como pago");
  expect(allText).toContain("sem movimentações financeiras");
});

test("quando backend rejeita auditoria, mostra erro e não inventa pagamento", async () => {
  api.get.mockRejectedValueOnce(new Error("503 auditoria indisponível"));
  await act(async () => { root.render(<FinanceReconciliationPanel />); });
  expect(container.querySelector('[role="alert"]').textContent)
    .toContain("503 auditoria indisponível");
  expect(container.textContent).not.toContain("Transferência confirmada para Stripe Connect");
});
