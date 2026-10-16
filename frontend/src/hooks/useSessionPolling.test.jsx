import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { useSessionPolling } from "./useSessionPolling";
let mockToken;
jest.mock("../lib/api", () => ({ getToken: () => mockToken }));
function Poll({ task, enabled = true }) { useSessionPolling(task, 1000, enabled); return null; }
let root, container;
const flush = async () => act(async () => { await Promise.resolve(); });
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.useFakeTimers(); mockToken = "token";
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
  container = document.createElement("div"); root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); jest.useRealTimers(); });
it("does not request without a token", async () => {
  mockToken = null; const task = jest.fn();
  await act(async () => root.render(<Poll task={task} />));
  await act(async () => jest.advanceTimersByTime(5000));
  expect(task).not.toHaveBeenCalled();
});
it("stops after unauthorized instead of retrying indefinitely", async () => {
  const task = jest.fn().mockRejectedValue({ response: { status: 401 } });
  await act(async () => root.render(<Poll task={task} />)); await flush();
  await act(async () => jest.advanceTimersByTime(5000));
  expect(task).toHaveBeenCalledTimes(1);
});
it("does not overlap slow requests and aborts on unmount", async () => {
  let resolve; const task = jest.fn(() => new Promise((r) => { resolve = r; }));
  await act(async () => root.render(<Poll task={task} />));
  await act(async () => jest.advanceTimersByTime(5000));
  expect(task).toHaveBeenCalledTimes(1);
  const signal = task.mock.calls[0][0];
  await act(async () => { root.render(null); resolve(); });
  await act(async () => jest.advanceTimersByTime(5000));
  expect(signal.aborted).toBe(true); expect(task).toHaveBeenCalledTimes(1);
});
it("skips hidden tabs and resumes when visible", async () => {
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
  const task = jest.fn().mockResolvedValue();
  await act(async () => root.render(<Poll task={task} />));
  expect(task).not.toHaveBeenCalled();
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
  await act(async () => jest.advanceTimersByTime(1000));
  expect(task).toHaveBeenCalledTimes(1);
});
