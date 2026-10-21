/**
 * Parse the customer QR without discarding its P5 session reference.
 * A generic coupon identifies a campaign, never an individual payable bill.
 */
export function parseCustomerQr(raw, expectedOrigin) {
  const text = String(raw || "").trim();
  const match = text.match(/\/c\/([A-Za-z0-9-]+)/);
  const code = (match ? match[1] : text).toUpperCase();
  let scanRef = "";
  let isP5Url = false;
  try {
    const url = new URL(text);
    isP5Url = url.searchParams.has("p5_ref");
    const reference = url.searchParams.get("p5_ref") || "";
    if (
      url.origin === expectedOrigin &&
      /^\/c\/[A-Za-z0-9-]+\/?$/.test(url.pathname) &&
      /^[A-Za-z0-9_-]{24,100}$/.test(reference)
    ) {
      scanRef = reference;
    }
  } catch {
    // A manually typed coupon remains a generic coupon; never a P5 session.
  }
  return { code, scanRef, isP5Url };
}
