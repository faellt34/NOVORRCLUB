import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { AbandonAnalysis } from "./AbandonAnalysis";
import { api } from "../lib/api";

jest.mock("../lib/api", () => ({
  api: { get: jest.fn() },
  apiError: (e) => e.message,
  downloadCsv: jest.fn(),
  dashboardMoney: (value) => String(value),
}));
jest.mock("../services/live", () => ({
  useCountUp: (v) => [v, false],
  useFlash: () => [{}, jest.fn()],
}));
jest.mock("./ui/dialog", () => ({
  Dialog: ({ open, children }) => open ? <div>{children}</div> : null,
  DialogContent: ({ children }) => <div>{children}</div>,
  DialogHeader: ({ children }) => <div>{children}</div>,
  DialogTitle: ({ children }) => <div>{children}</div>,
  DialogDescription: ({ children }) => <div>{children}</div>,
}));
jest.mock("sonner", () => ({ toast: { error: jest.fn(), success: jest.fn() } }));

let root, container;
const historical = {
  id: "test-before-pilot", date: "2026-10-24T09:00:00+00:00",
  origem: "Teste", cliente: "Cliente de teste", influencer: "—",
  campanha: "Antiga", cupom: "FAKE", qr: false, estado: "Sem download",
};

beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  api.get.mockReset();
  api.get.mockImplementation((_url, config) => Promise.resolve({
    data: { lista: config.params.include_history ? [historical] : [] },
  }));
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); });

test("a Análise de Abandono permanece visível com todos os indicadores a zero no piloto", async () => {
  await act(async () => root.render(<AbandonAnalysis events={[{
    tipo: "novo_clique", dados: { ...historical },
  }]} pilotSince="2026-10-25T12:00:00+00:00" />));

  expect(container.querySelector('[data-testid="abandon-analysis"]')).not.toBeNull();
  expect(container.textContent).toContain("Análise de Abandono");
  expect(container.querySelector('[data-testid="abandon-empty"]')).not.toBeNull();
  for (const key of ["total", "sem_download", "qr_sem_scan", "convertidos"]) {
    expect(container.querySelector(`[data-testid="funnel-kpi-${key}-value"]`).textContent).toBe("0");
  }
  expect(api.get).toHaveBeenCalledWith("/admin/cliques/analysis", {
    params: { period: "7d", include_history: false },
  });
});

test("o histórico não verificado continua consultável, sem contaminar o piloto", async () => {
  await act(async () => root.render(<AbandonAnalysis events={[]} includeHistory />));
  expect(container.querySelector('[data-testid="funnel-kpi-total-value"]').textContent).toBe("1");
  expect(container.textContent).toContain("Histórico antigo");

  await act(async () => root.render(<AbandonAnalysis events={[]} pilotSince="2026-10-25T12:00:00+00:00" />));
  expect(container.querySelector('[data-testid="funnel-kpi-total-value"]').textContent).toBe("0");
});
