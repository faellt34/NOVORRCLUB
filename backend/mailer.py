import asyncio
import html
import logging
import os
import re

import resend

from core import db, NO_ID

logger = logging.getLogger(__name__)


_settings_cache = {"key": None, "sender": None, "loaded": False}


async def load_settings():
    doc = await db.settings.find_one({"id": "email"}, NO_ID) or {}
    _settings_cache.update({"key": (doc.get("resend_api_key") or os.environ.get("RESEND_API_KEY") or "").strip(),
                            "sender": (doc.get("sender_email") or os.environ.get("RESEND_FROM") or os.environ.get("SENDER_EMAIL") or "onboarding@resend.dev").strip(), "loaded": True})
    return _settings_cache


def configured() -> bool:
    return bool(_settings_cache["key"])


def _safe_url(url: str) -> str:
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    return url if url and (url.startswith("https://") and (not base or url.startswith(base))) else ""


def _wrap(title: str, body: str, cta_label: str = None, cta_url: str = None) -> str:
    title, body, cta_label = html.escape(title or ""), html.escape(body or "").replace("\n", "<br>"), html.escape(cta_label or "Abrir")
    cta_url = _safe_url(cta_url)
    cta = f'<tr><td style="padding:24px 0 8px"><a href="{html.escape(cta_url, quote=True)}" style="background:#7C3AED;color:#fff;text-decoration:none;padding:12px 22px;border-radius:12px;font-weight:600;display:inline-block">{cta_label}</a></td></tr>' if cta_url else ""
    return f"""<table width="100%" cellpadding="0" cellspacing="0" style="background:#F8F9FC;padding:32px 0;font-family:Arial,Helvetica,sans-serif"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:16px;padding:32px;border:1px solid #E9E5F5">
<tr><td style="font-size:20px;font-weight:700;color:#0C0A14;padding-bottom:4px">RRclub</td></tr>
<tr><td style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#7C3AED;padding-bottom:24px">Luxury Experiences</td></tr>
<tr><td style="font-size:18px;font-weight:700;color:#0C0A14;padding-bottom:12px">{title}</td></tr>
<tr><td style="font-size:14px;line-height:1.6;color:#475569">{body}</td></tr>
{cta}
<tr><td style="font-size:11px;color:#94A3B8;padding-top:24px;border-top:1px solid #F1F5F9">Recebeu este email porque tem conta no RRclub. Se não reconhece esta ação, ignore esta mensagem.</td></tr>
</table></td></tr></table>"""


async def send_email(to: str, subject: str, title: str, body: str, cta_label: str = None, cta_url: str = None) -> bool:
    if not _settings_cache["loaded"]:
        await load_settings()
    if not configured() or not to or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", to):
        return False
    from core import rate_limit
    try:
        await rate_limit(f"email:{to.lower()}", 20, 3600)
    except Exception:
        logger.warning(f"Limite de emails atingido para {to}")
        return False
    resend.api_key = _settings_cache["key"]
    params = {"from": _settings_cache["sender"], "to": [to], "subject": subject, "html": _wrap(title, body, cta_label, cta_url)}
    try:
        await asyncio.to_thread(resend.Emails.send, params)
        return True
    except Exception as e:
        logger.error(f"Resend falhou para {to}: {e}")
        return False


async def email_user(user_id: str, subject: str, title: str, body: str, cta_label: str = None, path: str = None):
    user = await db.users.find_one({"id": user_id}, NO_ID)
    if not user or not user.get("email"):
        return False
    url = f"{os.environ.get('FRONTEND_URL', '').rstrip('/')}{path}" if path else None
    return await send_email(user["email"], subject, title, body, cta_label, url)
