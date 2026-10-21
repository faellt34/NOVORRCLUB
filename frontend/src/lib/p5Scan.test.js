import { parseCustomerQr } from "./p5Scan";

const origin = "https://rrclub.example";
const scan = "safe_reference_abcdefghijklmnopqrstuvwxyz";

test("P5 PT preserves the customer's individual QR reference on the first scan", () => {
  expect(parseCustomerQr(origin + "/c/PT-5?p5_ref=wrong", origin).scanRef).toBe("");
  expect(parseCustomerQr(origin + "/c/PT-5?p5_ref=" + scan, origin)).toEqual({
    code: "PT-5", scanRef: scan, isP5Url: true,
  });
});

test("rejects a P5 session reference from a different domain", () => {
  const found = parseCustomerQr("https://fake.example/c/PT-5?p5_ref=" + scan, origin);
  expect(found.code).toBe("PT-5");
  expect(found.isP5Url).toBe(true);
  expect(found.scanRef).toBe("");
});

test("rejects malformed or generic P5 references without confusing them with payments", () => {
  expect(parseCustomerQr(origin + "/c/PT-5?p5_ref=short", origin).scanRef).toBe("");
  expect(parseCustomerQr(origin + "/c/PT-5?coupon=only", origin)).toEqual({
    code: "PT-5", scanRef: "", isP5Url: false,
  });
  expect(parseCustomerQr("PT-5", origin)).toEqual({
    code: "PT-5", scanRef: "", isP5Url: false,
  });
});

test("never returns a private session_token in the parsed QR state", () => {
  const value = parseCustomerQr(origin + "/c/PT-5?p5_ref=" + scan, origin);
  expect(value.session_token).toBeUndefined();
});
