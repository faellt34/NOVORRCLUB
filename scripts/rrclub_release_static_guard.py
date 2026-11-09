#!/usr/bin/env python3
"""RRClub pre-publication static guard.

Run without MongoDB, Stripe credentials, calls to gateways or deployments.
This is a regression *gate*, not proof of operational financial readiness.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(fragment: str, path: str, explanation: str) -> None:
    if fragment not in source(path):
        raise AssertionError(f"{explanation} ({path})")


def check_python() -> None:
    files = [
        "backend/server.py",
        "backend/routes_profile.py",
        "backend/routes_admin.py",
        "backend/routes_data.py",
        "backend/routes_auth.py",
        "backend/p5_checkout.py",
        "backend/routes_pix.py",
        "backend/pt_split.py",
    ]
    for file in files:
        ast.parse(source(file), filename=file)
        print(f"PASS python syntax: {file}")


def check_profile() -> None:
    api = "backend/routes_profile.py"
    web = "frontend/src/components/ProfilePhotoDialog.jsx"
    require('router = APIRouter()', api, "Profile router missing")
    require('Depends(require_role("partner", "influencer"))', api, "Avatar authorization missing")
    require('Depends(require_role("partner"))', api, "Cover authorization missing")
    require('"user_id": user["id"]', api, "Profile must bind to current account")
    require('ENTITY_ID.fullmatch(entity_id)', api, "Invalid profile path protection")
    require('PHOTO_ID.fullmatch(photo_id)', api, "Invalid image path protection")
    require("MAX_UPLOAD = 3 * 1024 * 1024", api, "File-size limit missing")
    require('Response(content=data, media_type="image/jpeg"', api, "Image delivery missing")
    require('@router.get("/admin/system/version")', api, "Release endpoint missing")
    require('Depends(require_role("admin"))', api, "Admin-only release report missing")
    for forbidden in ("PaymentIntent.create(", "Transfer.create(", "Session.create(", "stripe.api_key", "PIX_ENABLED"):
        if forbidden in source(api):
            raise AssertionError(f"Profile module must not touch payments: {forbidden}")

    require("import routes_profile", "backend/server.py", "Router not imported")
    require("routes_profile.router", "backend/server.py", "Profile routes not mounted")
    require('"/profile/avatar"', web, "Avatar UI missing")
    require('"/profile/cover"', web, "Partner cover UI missing")
    require('refreshUser()', web, "Profile refresh missing")
    require('data-testid="sidebar-change-avatar"', "frontend/src/components/layout/Sidebar.jsx", "Photo control missing")
    require('data-testid="sidebar-change-cover"', "frontend/src/components/layout/Sidebar.jsx", "Cover control missing")
    require('"cover_image": partner.get("cover_image")', "backend/routes_data.py", "Public cover field missing")
    require("c.cover_image && <img", "frontend/src/pages/PublicCoupon.jsx", "Cover image missing")
    print("PASS profile and campaign wiring")


def check_auth() -> None:
    backend = "backend/routes_admin.py"
    ui = "frontend/src/pages/AdminManage.jsx"
    if "robson123" in source(backend) or "robson123" in source(ui):
        raise AssertionError("Predictable default password must not appear in source")
    require("if not pwd or not re.fullmatch", backend, "Creation policy missing")
    require('elif pwd:', backend, "Password change option missing")
    require("if not re.fullmatch", backend, "Password change validation missing")
    require('dialog?.mode === "create"', ui, "Admin form creation validation missing")
    print("PASS password policy")


def check_financial_isolation() -> None:
    # Never use a frontend badge, flag or a syntactic check as proof of payout.
    require('financial_settlement_verified": False', "backend/p5_checkout.py", "Financial verification label changed")
    require('PIX_ENABLED', "backend/routes_pix.py", "Pix config unexpectedly removed")
    require('payment_status', "backend/routes_pix.py", "Pix settlement paths unexpectedly removed")
    print("PASS financial readiness disclaimers and retained module interfaces")


if __name__ == "__main__":
    check_python()
    check_profile()
    check_auth()
    check_financial_isolation()
    print("PASS RRClub release static safety gate (no live operations)")
