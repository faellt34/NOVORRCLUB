import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { PixBillStatus } from "./PixBillStatus";
import { api } from "../lib/api";

jest.mock("../lib/api", () => ({ api: { get: jest.fn() }, moneyIn: (value) => `R$ ${value}` }));
jest.mock("qrcode.react", () => ({ QRCodeSVG: () => <svg data-testid="payment-qr" /> }));
const bill = { request_id: "12345678-1234-4234-8234-123456789abc", amount: 95,
  customer_url: "https://rrclub.online/c/TEST?pix_request_id=12345678-1234-4234-8234-123456789abc" };
let root, container, onPaid;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.useFakeTimers(); jest.clearAllMocks();
  container = document.createElement("div"); root = createRoot(container); onPaid = jest.fn();
});
afterEach(() => { act(() => root.unmount()); jest.useRealTimers(); });
async function mount(status) {
  api.get.mockResolvedValue({ data: { ...bill, ...status } });
  await act(async () => { root.render(<PixBillStatus bill={bill} onPaid={onPaid} />); });
}
test("pending payment shows QR without confirming the sale", async () => {
  await mount({ payment_status: "pending" });
  expect(container.textContent).toContain("Aguardando pagamento");
  expect(container.querySelector("svg")).not.toBeNull();
  expect(onPaid).not.toHaveBeenCalled();
});
test("confirmation hides payment link and refreshes dashboard once while transfers finish", async () => {
  await mount({ payment_status: "paid", split_status: "pending" });
  expect(container.textContent).toContain("Não cobre novamente");
  expect(container.textContent).toContain("divisão em processamento");
  expect(container.querySelector("a")).toBeNull();
  api.get.mockResolvedValue({ data: { ...bill, payment_status: "paid", split_status: "completed" } });
  await act(async () => { jest.advanceTimersByTime(3000); });
  expect(container.textContent).toContain("Divisão concluída nos saldos Stripe");
  expect(onPaid).toHaveBeenCalledTimes(1);
  const calls = api.get.mock.calls.length;
  await act(async () => { jest.advanceTimersByTime(6000); });
  expect(api.get).toHaveBeenCalledTimes(calls);
});
test("provider outage preserves payment confirmation without a repayment link", async () => {
  await mount({ payment_status: "paid", split_status: "pending" });
  api.get.mockRejectedValue(new Error("network"));
  await act(async () => { jest.advanceTimersByTime(3000); });
  expect(container.textContent).toContain("Pagamento confirmado");
  expect(container.querySelector("a")).toBeNull();
  expect(onPaid).toHaveBeenCalledTimes(1);
  await act(async () => { container.querySelector('button').click(); });
  expect(container.textContent).toContain("Pagamento confirmado");
  expect(container.querySelector("a")).toBeNull();
});
test("expiry stops polling and does not confirm a sale", async () => {
  await mount({ payment_status: "expired" });
  expect(container.querySelector("svg")).toBeNull();
  expect(onPaid).not.toHaveBeenCalled();
  await act(async () => { jest.advanceTimersByTime(6000); });
  expect(api.get).toHaveBeenCalledTimes(1);
});
test("unmount aborts request and stops polling", async () => {
  await mount({ payment_status: "pending" });
  const signal = api.get.mock.calls[0][1].signal;
  act(() => root.unmount());
  await act(async () => { jest.advanceTimersByTime(6000); });
  expect(signal.aborted).toBe(true);
  expect(api.get).toHaveBeenCalledTimes(1);
  root = createRoot(container);
});
test("slow requests never overlap", async () => {
  let resolve;
  api.get.mockImplementation(() => new Promise((r) => { resolve = r; }));
  await act(async () => { root.render(<PixBillStatus bill={bill} onPaid={onPaid} />); });
  await act(async () => { jest.advanceTimersByTime(12000); });
  expect(api.get).toHaveBeenCalledTimes(1);
  await act(async () => { resolve({ data: { ...bill, payment_status: "paid", split_status: "completed" } }); });
  expect(onPaid).toHaveBeenCalledTimes(1);
});
