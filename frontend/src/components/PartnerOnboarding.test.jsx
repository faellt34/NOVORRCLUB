import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { PartnerOnboarding } from "./PartnerOnboarding";

let root, container;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div"); document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); });
const mount = (props) => act(() => root.render(<PartnerOnboarding hasCampaign {...props} />));

test("Brazil setup never promises manual IBAN transfers and numbers its two steps", () => {
  mount({ currency: "brl", connect: { available: false } });
  expect(container.textContent).not.toContain("IBAN");
  expect(container.textContent).toContain("1. Configurar recebimentos Pix");
  expect(container.textContent).toContain("2. Primeiro cupão QR");
  expect(container.querySelector('[data-testid="onboarding-step-connect-cta"]').disabled).toBe(true);
});
test("Brazil receiving readiness uses transfers and payouts, not card charges", () => {
  mount({ currency: "brl", connect: { charges_enabled: false, receiving_ready: true } });
  expect(container.querySelector('[data-testid="partner-onboarding"]')).toBeNull();
});
test("Portugal keeps IBAN and merchant charge readiness", () => {
  mount({ currency: "eur", hasIban: false, connect: { charges_enabled: true } });
  expect(container.textContent).toContain("IBAN de recebimento");
  expect(container.querySelector('[data-testid="onboarding-step-connect-done"]')).not.toBeNull();
});
