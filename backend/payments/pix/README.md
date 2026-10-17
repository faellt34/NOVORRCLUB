# Pix Brasil

This package holds the read-only checks for the existing Brazilian payment flow.
The routes stay in `backend/routes_pix.py`, already included by `server.py`.
The environment template is `pix.env.example`; it contains no credentials and keeps Pix off.

Configuration: `GET /api/admin/pix/readiness` (no Stripe calls).
Provider checks: `GET /api/admin/pix/provider-readiness` (administrator only, Stripe GETs).
Receipts/webhook: `POST /api/stripe/pix/webhook` (signature verification required).

See `docs/PIX_BRASIL_ENTREGA.md` for the account findings, rollout and limits.

Emergent configuration handoff (no secrets):
`docs/PIX_BRASIL_CONFIGURACAO_EMERGENT.md`.
