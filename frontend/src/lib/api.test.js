import { api, getToken, setToken } from "./api";
const reject401 = (config) => Promise.reject({ config, response: { status: 401 } });
afterEach(() => { localStorage.clear(); });
it("expires the matching session on 401", async () => {
  setToken("expired"); const expired = jest.fn();
  window.addEventListener("rrclub:session-expired", expired);
  await expect(api.get("/notifications", { adapter: reject401 })).rejects.toBeDefined();
  expect(getToken()).toBeNull(); expect(expired).toHaveBeenCalledTimes(1);
  window.removeEventListener("rrclub:session-expired", expired);
});
it("a late 401 from an old session cannot log out the new session", async () => {
  setToken("old");
  await expect(api.get("/notifications", { adapter: (config) => { setToken("new"); return reject401(config); } })).rejects.toBeDefined();
  expect(getToken()).toBe("new");
});
