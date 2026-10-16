import React, { act } from "react";
import { createRoot } from "react-dom/client";
import PublicCoupon from "./PublicCoupon";
import { api } from "../lib/api";

let mockParams;
jest.mock("react-router-dom", () => ({
  useParams: () => ({ code: "ROBSON" }),
  useSearchParams: () => [mockParams],
  Link: ({ children }) => <span>{children}</span>,
}), { virtual: true });
jest.mock("../lib/api", () => ({ api: { get: jest.fn(), post: jest.fn() }, apiError: () => "Erro", num: (v) => v }));
jest.mock("../components/BrandLogo", () => ({ BrandLogo: () => null }));
jest.mock("../components/GlobeCanvas", () => ({ GlobeCanvas: () => null }));
jest.mock("qrcode.react", () => ({ QRCodeSVG: ({ value }) => <svg data-qr-value={value} /> }));
jest.mock("sonner", () => ({ toast: { error: jest.fn(), success: jest.fn() } }));
const uuid = "a4456521-192a-41d5-9030-c59e83d723ad";
const coupon = { cupom: "ROBSON", currency: "brl", desconto: 5, status: "Ativa", validade: "2027-12-01", parceiro: "Loja", claims: 1 };
let container, root;
const flush = async () => { await act(async () => { await Promise.resolve(); await Promise.resolve(); }); };
const mount = async (payment, status = "Ativa") => {
  api.get.mockImplementation((path) => Promise.resolve({ data: path.startsWith("/public/coupon/") ? { ...coupon, status } : payment }));
  await act(async () => { root.render(<PublicCoupon />); });
  await flush();
};
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.useFakeTimers(); sessionStorage.clear(); jest.clearAllMocks();
  mockParams = new URLSearchParams(`pix_request_id=${uuid}`);
  container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); jest.useRealTimers(); });

test("pending Pix prevents a second checkout and allows manual status check", async () => {
  await mount({ payment_status: "pending", coupon: "ROBSON", currency: "brl" });
  expect(container.querySelector('[data-testid="public-pay-card"]')).toBeNull();
  expect(container.querySelector('[data-testid="public-pay-polling"]').textContent).toContain("Não faça outro pagamento");
  const checks = api.get.mock.calls.length;
  await act(async () => { [...container.querySelectorAll("button")].find((el) => el.textContent === "Verificar pagamento").click(); });
  expect(api.get.mock.calls.length).toBeGreaterThan(checks);
  expect(api.post).not.toHaveBeenCalled();
});
test.each(["paid", "partially_refunded", "refunded", "disputed"])("%s is a final display state, including after campaign expiry", async (state) => {
  await mount({ payment_status: state, coupon: "ROBSON", currency: "brl", amount: 95, gross_amount: 100, discount: 5, refunded_amount: state.includes("refunded") ? 45 : 0 }, "Expirada");
  expect(container.querySelector('[data-testid="public-pay-success"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="public-pay-polling"]')).toBeNull();
  expect(container.querySelector('[data-testid="public-pay-card"]')).toBeNull();
  expect(container.querySelector('[data-testid="public-receipt"]').textContent).toContain("R$");
  expect(container.querySelector("[data-qr-value]").getAttribute("data-qr-value")).not.toContain(uuid);
});
test("failed Pix allows a new attempt without displaying a successful receipt", async () => {
  await mount({ payment_status: "expired", coupon: "ROBSON" });
  expect(container.querySelector('[data-testid="public-pay-failed"]').textContent).toContain("pedir nova cobrança ao parceiro");
  expect(container.querySelector('[data-testid="public-pay-success"]')).toBeNull();
});
test("payment belonging to another coupon cannot display a successful receipt", async () => {
  await mount({ payment_status: "paid", coupon: "OTHER", currency: "brl" });
  expect(container.querySelector('[data-testid="public-pay-success"]')).toBeNull();
  expect(container.textContent).toContain("outro cupom");
});
test("polling stops on unmount", async () => {
  await mount({ payment_status: "pending", coupon: "ROBSON" });
  act(() => root.unmount());
  const calls = api.get.mock.calls.length;
  await act(async () => { jest.advanceTimersByTime(6000); });
  expect(api.get).toHaveBeenCalledTimes(calls);
  root = createRoot(container);
});
test("an interrupted merchant checkout resumes the stored UUID without customer amount overrides", async () => {
  sessionStorage.setItem("rrclub_pix_ROBSON", JSON.stringify({ request_id: uuid, amount: 100, origin_url: "https://rrclub.online" }));
  api.post.mockRejectedValueOnce(new Error("network"));
  await mount({ payment_status: "pending", coupon: "ROBSON" });
  await act(async () => { [...container.querySelectorAll("button")].find((el) => el.textContent === "Retomar pedido de pagamento").click(); });
  expect(api.post).toHaveBeenCalledWith("/public/pix/checkout", { request_id: uuid });
  expect(JSON.parse(sessionStorage.getItem("rrclub_pix_ROBSON")).request_id).toBe(uuid);
});
test("first-time Pix visitors cannot enter a bill amount or create an arbitrary checkout", async () => {
  mockParams = new URLSearchParams();
  await mount({ payment_status: "pending", coupon: "ROBSON" });
  expect(container.querySelector('[data-testid="public-pix-merchant-bill"]').textContent).toContain("O estabelecimento confirma o valor");
  expect(container.querySelector('[data-testid="public-pay-amount"]')).toBeNull();
  expect(container.querySelector('[data-testid="public-pay-button"]')).toBeNull();
  expect(api.post).not.toHaveBeenCalled();
});

test("merchant-confirmed amount comes from status and cannot be edited by the customer", async () => {
  await mount({ payment_status: "pending", coupon: "ROBSON", currency: "brl", amount: 81, checkout_url: "https://checkout.stripe.com/test" });
  expect(container.querySelector('[data-testid="public-pix-confirmed-bill"]').textContent).toContain("81,00");
  expect(container.querySelector('[data-testid="public-pay-amount"]')).toBeNull();
  expect([...container.querySelectorAll("a")].some((el) => el.href === "https://checkout.stripe.com/test")).toBe(true);
});

test("paid receipt remains confirmed when internal transfers are pending and never offers repayment", async () => {
  await mount({ payment_status: "paid", split_status: "pending", coupon: "ROBSON", currency: "brl", amount: 95, gross_amount: 100, discount: 5 });
  expect(container.querySelector('[data-testid="public-pay-success"]').textContent).toContain("Pagamento confirmado");
  expect(container.querySelector('[data-testid="public-receipt"]').textContent).toContain("95,00");
  expect(container.querySelector('[data-testid="public-pay-card"]')).toBeNull();
  expect(container.querySelector('[data-testid="public-pay-polling"]')).toBeNull();
  expect(api.post).not.toHaveBeenCalled();
});
