import React, { act } from "react";
import { createRoot } from "react-dom/client";
import GoogleSignIn from "./GoogleSignIn";
import { api, setToken } from "../lib/api";

const mockNavigate = jest.fn();
const mockRefresh = jest.fn();
const mockToast = { error: jest.fn(), success: jest.fn() };
jest.mock("react-router-dom", () => ({ useNavigate: () => mockNavigate }), { virtual: true });
jest.mock("sonner", () => ({ toast: { error: (...args) => mockToast.error(...args), success: (...args) => mockToast.success(...args) } }));
jest.mock("../context/AppContext", () => ({ useApp: () => ({ refreshUser: mockRefresh }) }));
jest.mock("../lib/api", () => ({ api: { get: jest.fn(), post: jest.fn() }, setToken: jest.fn(), apiError: e => e.message }));

let initialize;
let root;
let container;
function render(element) {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => root.render(element));
}
async function waitFor(assertion) {
  let failure;
  for (let i = 0; i < 30; i++) {
    try { return assertion(); } catch (e) { failure = e; }
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 1)); });
  }
  throw failure;
}
const screen = {
  getByRole: role => container.querySelector(role === "button" ? "button" : `[role="${role}"]`),
  findByText: pattern => waitFor(() => {
    expect(container.textContent).toMatch(pattern);
    return container;
  })
};
afterEach(() => { if (root) act(() => root.unmount()); container?.remove(); root = null; });
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.clearAllMocks();
  localStorage.clear();
  initialize = jest.fn();
  window.google = { accounts: { id: { initialize, renderButton: jest.fn() } } };
  api.get.mockResolvedValue({ data: { client_id: "test-client", nonce: "nonce-1" } });
  mockRefresh.mockResolvedValue({});
});

async function callback() {
  await waitFor(() => expect(initialize).toHaveBeenCalled());
  return initialize.mock.calls[initialize.mock.calls.length - 1][0].callback;
}

test("Google unavailable keeps a clear email/password fallback", async () => {
  api.get.mockResolvedValue({ data: { client_id: "" } });
  render(<GoogleSignIn />);
  await screen.findByText(/aguarda configuração/);
  expect(screen.getByRole("button").disabled).toBe(true);
  expect(initialize).not.toHaveBeenCalled();
});

test("successful login stores the RRClub session and uses the existing role", async () => {
  api.post.mockResolvedValue({ data: { token: "test-session", user: { role: "partner", currency: "brl" } } });
  render(<GoogleSignIn />);
  const signIn = await callback();
  await act(async () => signIn({ credential: "test-credential" }));
  expect(api.post).toHaveBeenCalledWith("/auth/google", { credential: "test-credential" });
  expect(setToken).toHaveBeenCalledWith("test-session");
  expect(localStorage.getItem("rrclub_currency")).toBe("brl");
  expect(mockNavigate).toHaveBeenCalledWith("/parceiro");
});

test("linking does not replace the session, role or reporting currency", async () => {
  localStorage.setItem("rrclub_currency", "brl");
  api.post.mockResolvedValue({ data: { linked: true } });
  render(<GoogleSignIn linkAccount />);
  const link = await callback();
  await act(async () => link({ credential: "test-credential" }));
  expect(api.post).toHaveBeenCalledWith("/auth/google/link", { credential: "test-credential" });
  expect(setToken).not.toHaveBeenCalled();
  expect(mockNavigate).not.toHaveBeenCalled();
  expect(localStorage.getItem("rrclub_currency")).toBe("brl");
});

test("registration requires terms before submitting a Google credential", async () => {
  render(<GoogleSignIn registration={{ role: "partner", aceita_termos: false }} />);
  const signIn = await callback();
  await act(async () => signIn({ credential: "test-credential" }));
  expect(api.post).not.toHaveBeenCalled();
  expect(mockToast.error).toHaveBeenCalledWith(expect.stringMatching(/Política de Privacidade/));
});

test("pending partner preserves the current form and does not open a session", async () => {
  const pending = jest.fn();
  const form = { nome: "Espaço", currency: "brl", role: "partner", aceita_termos: true, cidade: "João Pessoa", handle: "", categoria: "Restaurante" };
  api.post.mockResolvedValue({ data: { pending: true, message: "Aguarde aprovação" } });
  render(<GoogleSignIn registration={form} onPending={pending} />);
  const signIn = await callback();
  await act(async () => signIn({ credential: "test-credential" }));
  expect(api.post).toHaveBeenCalledWith("/auth/google", { credential: "test-credential", ...form });
  expect(pending).toHaveBeenCalledWith("Aguarde aprovação");
  expect(setToken).not.toHaveBeenCalled();
  expect(mockNavigate).not.toHaveBeenCalled();
});

test("a failed attempt obtains a fresh one-time nonce for retry", async () => {
  api.get.mockResolvedValueOnce({ data: { client_id: "test-client", nonce: "nonce-1" } })
    .mockResolvedValue({ data: { client_id: "test-client", nonce: "nonce-2" } });
  api.post.mockRejectedValue(new Error("Já existe uma conta"));
  render(<GoogleSignIn />);
  const signIn = await callback();
  await act(async () => signIn({ credential: "test-credential" }));
  await waitFor(() => expect(initialize).toHaveBeenCalledWith(expect.objectContaining({ nonce: "nonce-2" })));
  expect(setToken).not.toHaveBeenCalled();
});
