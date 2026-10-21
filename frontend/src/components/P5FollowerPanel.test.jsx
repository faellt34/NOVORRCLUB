import React, { act } from "react";
import { createRoot } from "react-dom/client";
import P5FollowerPanel from "./P5FollowerPanel";
import { api } from "../lib/api";

jest.mock("../lib/api", () => ({
  api: { get: jest.fn(), post: jest.fn() },
  apiError: (e) => e?.message || "Falha de comunicação",
  moneyIn: (v, c) => String(v) + " " + c,
}));
jest.mock("qrcode.react", () => ({
  QRCodeSVG: ({ value }) => <span data-testid="p5-qr-payload">{value}</span>,
}));
jest.mock("sonner", () => ({ toast: { error: jest.fn(), info: jest.fn() } }));

let root, div;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  api.get.mockReset();
  api.post.mockReset();
  window.sessionStorage.clear();
  div = document.createElement("div");
  document.body.appendChild(div);
  root = createRoot(div);
});
afterEach(() => {
  act(() => root.unmount());
  div.remove();
});

test("P5 QR exposes scan reference but never the private session secret", async () => {
  const secret = "session_token_this_is_private_123456789";
  api.post.mockResolvedValueOnce({
    data: { scan_ref: "scan_ref_safe_public_123456789", session_token: secret,
      expires_at: new Date(Date.now() + 600000).toISOString() },
  });
  api.get.mockResolvedValue({ data: { status: "none" } });
  await act(async () => {
    root.render(<P5FollowerPanel code="RR-SAMPLE" currency="eur" />);
  });
  const qr = div.querySelector('[data-testid="p5-qr-payload"]')?.textContent || "";
  expect(qr).toContain("p5_ref=scan_ref_safe_public_123456789");
  expect(qr).not.toContain(secret);
  expect(div.querySelector('[data-testid="p5-pay-button"]')).toBeNull();
});

test("P5 customer cannot change a partner-approved bill; checkout only after confirmation", async () => {
  api.post.mockResolvedValueOnce({
    data: {
      scan_ref: "p5_scan_partner_approved_123456",
      session_token: "p5_private_secret_123456789012345",
      expires_at: new Date(Date.now() + 600000).toISOString(),
    },
  });
  api.get.mockResolvedValueOnce({
    data: { status: "pending", charge_id: "p5_charge_unit", currency: "brl",
      gross_minor: 10000, discount_minor: 500, net_minor: 9500 },
  });
  await act(async () => {
    root.render(<P5FollowerPanel code="RR-BR-5" currency="brl" />);
  });
  expect(div.textContent).toContain("95 brl");
  expect(div.querySelector('[data-testid="p5-pay-button"]')).not.toBeNull();
  expect(div.querySelector('input[inputmode="decimal"]')).toBeNull();
  expect(api.post).toHaveBeenCalledWith("/public/p5/sessions", { code: "RR-BR-5" });
  expect(api.post).toHaveBeenCalledTimes(1); // displaying QR or bill never charges
});

test("P5 displays awaiting Stripe onboarding, not a platform error", async () => {
  api.post.mockResolvedValueOnce({
    data: {
      scan_ref: "p5_ref_buyer_12345678901234567890",
      session_token: "p5_secret_123456789012345678901234567890",
      expires_at: new Date(Date.now() + 600000).toISOString(),
    },
  });
  api.get.mockResolvedValue({ data: {
    status: "awaiting_connect", charge_id: "p5_charge_waiting",
    currency: "eur", gross_minor: 10000, discount_minor: 500, net_minor: 9500,
  } });
  await act(async () => {
    root.render(<P5FollowerPanel code="PT-PENDING" currency="eur" checkoutEnabled={false} />);
  });
  expect(div.querySelector('[data-testid="p5-awaiting-connect"]')).not.toBeNull();
  expect(div.textContent).toContain("recebimentos em ativação");
  expect(div.querySelector('[data-testid="p5-pay-button"]')).toBeNull();
  expect(api.post).toHaveBeenCalledTimes(1);
});
