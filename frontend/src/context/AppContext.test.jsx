import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { AppProvider, useApp } from "./AppContext";
import { api } from "../lib/api";
let mockToken = null;
jest.mock("../lib/api", () => ({
  api: { get: jest.fn(), post: jest.fn() },
  getToken: () => mockToken,
  setToken: (token) => { mockToken = token; },
}));
let context;
function Probe() { context = useApp(); return null; }
it("stops local access immediately while still revoking the bearer token on logout", async () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  mockToken = null;
  api.get.mockResolvedValue({ data: { unread: 0 } });
  api.post.mockImplementation((path) => Promise.resolve({ data: path === "/auth/login" ? { token: "session-to-revoke", user: { id: "u", role: "influencer", currency: "brl" } } : { ok: true } }));
  const root = createRoot(document.createElement("div"));
  await act(async () => root.render(<AppProvider><Probe /></AppProvider>));
  await act(async () => context.login("user@example.com", "password"));
  expect(mockToken).toBe("session-to-revoke");
  await act(async () => context.logout());
  expect(mockToken).toBeNull(); expect(context.user).toBeNull();
  expect(api.post).toHaveBeenCalledWith("/auth/logout", {}, { headers: { Authorization: "Bearer session-to-revoke" } });
  act(() => root.unmount());
});
