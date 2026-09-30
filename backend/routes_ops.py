import re
import os
import secrets
import io
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from core import db, NO_ID, get_current_user, require_role, audit, notify, new_id, now_iso, hash_password
from mailer import send_email, configured

router = APIRouter()


@router.get("/admin/payouts")
async def payouts_overview(user: dict = Depends(require_role("admin"))):
    reds = await db.redemptions.find({}, {"influencer_id": 1, "influencer": 1, "date": 1, "commission": 1, "_id": 0}).to_list(100000)
    agg = defaultdict(lambda: {"commission": 0.0, "count": 0})
    names = {}
    for r in reds:
        k = (r["influencer_id"], r["date"][:7])
        agg[k]["commission"] += r["commission"]; agg[k]["count"] += 1
        names[r["influencer_id"]] = r["influencer"]
    paid = {(p["influencer_id"], p["month"]): p async for p in db.payouts.find({}, NO_ID)}
    ibans = {i["id"]: i.get("iban") async for i in db.influencers.find({}, {"id": 1, "iban": 1, "_id": 0})}
    rows = []
    for (inf, month), v in agg.items():
        p = paid.get((inf, month))
        rows.append({"influencer_id": inf, "influencer": names[inf], "month": month, "commission": round(v["commission"], 2), "count": v["count"],
                     "status": "Pago" if p else "Pendente", "paid_at": p["paid_at"] if p else None, "note": p.get("note") if p else None, "iban": ibans.get(inf)})
    rows.sort(key=lambda r: (r["month"], r["influencer"]), reverse=True)
    return rows


class PayoutIn(BaseModel):
    influencer_id: str
    month: str
    note: Optional[str] = ""


@router.post("/admin/payouts")
async def mark_paid(body: PayoutIn, user: dict = Depends(require_role("admin"))):
    if await db.payouts.find_one({"influencer_id": body.influencer_id, "month": body.month}):
        raise HTTPException(status_code=409, detail="Este mês já está marcado como pago")
    inf = await db.influencers.find_one({"id": body.influencer_id}, NO_ID)
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer não encontrado")
    if not re.fullmatch(r"\d{4}-\d{2}", body.month):
        raise HTTPException(status_code=400, detail="Mês inválido (AAAA-MM)")
    total = sum([r["commission"] async for r in db.redemptions.find({"influencer_id": body.influencer_id, "date": {"$regex": f"^{body.month}"}}, {"commission": 1})])
    doc = {"id": new_id("pay"), "influencer_id": body.influencer_id, "month": body.month, "paid_at": datetime.now(timezone.utc).date().isoformat(), "amount": round(total, 2), "note": body.note, "by": user["nome"]}
    await db.payouts.insert_one(dict(doc))
    await audit("PAGAMENTO", f"Extrato {body.month} de {inf['nome']} marcado como pago · {total:.2f}€", user, doc["id"])
    inf_user = await db.users.find_one({"influencer_id": body.influencer_id}, {"id": 1})
    if inf_user:
        await notify([inf_user["id"]], "pagamento", "Comissão paga 💸", f"O extrato de {body.month} ({total:.2f}€) foi marcado como pago em {doc['paid_at']}.", "/influencer/extrato")
    return doc


@router.delete("/admin/payouts/{influencer_id}/{month}")
async def unmark_paid(influencer_id: str, month: str, user: dict = Depends(require_role("admin"))):
    res = await db.payouts.delete_one({"influencer_id": influencer_id, "month": month})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    await audit("PAGAMENTO", f"Extrato {month} de {influencer_id} revertido para pendente", user, f"{influencer_id}/{month}")
    return {"ok": True}


class ForgotIn(BaseModel):
    email: str


@router.post("/auth/forgot-password")
async def forgot_password(body: ForgotIn):
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email}, NO_ID)
    if user:
        token = secrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({"id": new_id("prt"), "token": token, "user_id": user["id"], "email": email, "nome": user["nome"],
                                                   "created_at": now_iso(), "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(), "used": False})
        await audit("RECUPERAÇÃO", f"Pedido de recuperação de palavra-passe · {email}", user, token[:8])
        link = f"{os.environ.get('FRONTEND_URL', '').rstrip('/')}/redefinir-password?token={token}"
        sent = await send_email(email, "RRclub · Redefinir palavra-passe", "Redefinir a sua palavra-passe",
                                f"Olá {user['nome'].split(' ')[0]}, recebemos um pedido para redefinir a sua palavra-passe. O link é válido durante 24 horas e só pode ser usado uma vez.", "Definir nova palavra-passe", link)
        await db.password_reset_tokens.update_one({"token": token}, {"$set": {"emailed": sent}})
        admins = [u["id"] async for u in db.users.find({"role": "admin"}, {"id": 1})]
        await notify(admins, "reset", "Pedido de recuperação de acesso", f"{user['nome']} ({email}) pediu para redefinir a palavra-passe." + (" Email enviado automaticamente." if sent else " Envie-lhe o link no painel."), "/admin")
    return {"ok": True, "message": "Se o email existir, enviámos as instruções de recuperação." if configured() else "Se o email existir, o pedido foi registado. O administrador irá enviar-lhe o link de recuperação."}


@router.get("/admin/reset-requests")
async def reset_requests(user: dict = Depends(require_role("admin"))):
    now = now_iso()
    return await db.password_reset_tokens.find({"used": False, "expires_at": {"$gt": now}}, NO_ID).sort("created_at", -1).to_list(100)


class ResetIn(BaseModel):
    token: str
    password: str


@router.get("/auth/reset-password/{token}")
async def reset_check(token: str):
    t = await db.password_reset_tokens.find_one({"token": token}, NO_ID)
    if not t or t["used"] or t["expires_at"] < now_iso():
        raise HTTPException(status_code=400, detail="Link inválido ou expirado")
    return {"email": t["email"], "nome": t["nome"]}


@router.post("/auth/reset-password")
async def reset_password(body: ResetIn):
    t = await db.password_reset_tokens.find_one({"token": body.token}, NO_ID)
    if not t or t["used"] or t["expires_at"] < now_iso():
        raise HTTPException(status_code=400, detail="Link inválido ou expirado")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="A palavra-passe deve ter pelo menos 6 caracteres")
    await db.users.update_one({"id": t["user_id"]}, {"$set": {"password_hash": hash_password(body.password)}})
    await db.password_reset_tokens.update_one({"token": body.token}, {"$set": {"used": True, "used_at": now_iso()}})
    await db.login_attempts.delete_many({"identifier": {"$regex": f":{re.escape(t['email'])}$"}})
    await audit("RECUPERAÇÃO", f"Palavra-passe redefinida · {t['email']}", {"id": t["user_id"], "nome": t["nome"]}, body.token[:8])
    return {"ok": True}


MONTHS_PT = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


@router.get("/statements/{month}/pdf")
async def statement_pdf(month: str, user: dict = Depends(require_role("influencer"))):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    reds = await db.redemptions.find({"influencer_id": user["influencer_id"], "date": {"$regex": f"^{month}"}}, NO_ID).to_list(50000)
    if not reds:
        raise HTTPException(status_code=404, detail="Sem redenções neste mês")
    pay = await db.payouts.find_one({"influencer_id": user["influencer_id"], "month": month}, NO_ID)
    lines = defaultdict(lambda: {"uses": 0, "revenue": 0.0, "commission": 0.0})
    for r in reds:
        l = lines[(r["campaign"], r["partner"], r["rate"])]
        l["uses"] += 1; l["revenue"] += r["amount"]; l["commission"] += r["commission"]
    y, m = month.split("-")
    label = f"{MONTHS_PT[int(m) - 1]} {y}"
    purple = colors.HexColor("#7C3AED"); dark = colors.HexColor("#0C0A14")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=22, textColor=dark, alignment=0, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor("#7C3AED"), spaceAfter=14)
    body = ParagraphStyle("b", parent=ss["Normal"], fontSize=10, textColor=colors.HexColor("#475569"), leading=14)
    small = ParagraphStyle("s", parent=ss["Normal"], fontSize=8, textColor=colors.HexColor("#94A3B8"))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm, title=f"Extrato {label}")
    el = [Paragraph("ןןCLUB", h1), Paragraph("LUXURY EXPERIENCES · EXTRATO DE COMISSÕES", sub),
          Paragraph(f"<b>Influencer:</b> {user['nome']} &nbsp;&nbsp; <b>Email:</b> {user['email']}", body),
          Paragraph(f"<b>Período:</b> {label} &nbsp;&nbsp; <b>Estado:</b> {'Pago em ' + pay['paid_at'] if pay else 'Pendente de pagamento'} &nbsp;&nbsp; <b>Emitido:</b> {datetime.now(timezone.utc).strftime('%d/%m/%Y')}", body), Spacer(1, 12)]
    data = [["Campanha", "Parceiro", "Utilizações", "Receita (€)", "Taxa", "Comissão (€)"]]
    tu = tr = tc = 0
    for (camp, part, rate), v in sorted(lines.items(), key=lambda x: -x[1]["revenue"]):
        data.append([camp, part, str(v["uses"]), f"{v['revenue']:,.2f}", f"{rate * 100:.0f}%", f"{v['commission']:,.2f}"])
        tu += v["uses"]; tr += v["revenue"]; tc += v["commission"]
    data.append(["TOTAL", "", str(tu), f"{tr:,.2f}", "", f"{tc:,.2f}"])
    t = Table(data, colWidths=[52 * mm, 40 * mm, 22 * mm, 26 * mm, 14 * mm, 26 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), dark), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F8F9FC")]), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EDE9FE")), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (-1, -1), (-1, -1), purple), ("ALIGN", (2, 1), (-1, -1), "RIGHT"), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    el += [t, Spacer(1, 16), Paragraph(f"<b>Total de comissão a receber: {tc:,.2f} €</b>", ParagraphStyle("tot", parent=body, fontSize=13, textColor=purple)), Spacer(1, 10),
           Paragraph("A taxa de comissão é travada em cada redenção no momento da validação pelo parceiro. Este documento é gerado automaticamente pela plataforma RRclub e serve de suporte à faturação/contabilidade. Pagamento por transferência bancária conforme acordo de parceria.", small)]
    doc.build(el)
    await audit("EXTRATO", f"PDF do extrato {month} gerado", user, month)
    return Response(content=buf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="extrato-rrclub-{month}.pdf"'})


class FeedbackIn(BaseModel):
    tipo: str
    mensagem: str
    pagina: Optional[str] = ""


@router.post("/feedback")
async def create_feedback(body: FeedbackIn, user: dict = Depends(get_current_user)):
    if len(body.mensagem.strip()) < 5:
        raise HTTPException(status_code=400, detail="Descreva a sugestão com um pouco mais de detalhe.")
    doc = {"id": new_id("fb"), "user_id": user["id"], "nome": user["nome"], "email": user["email"], "role": user["role"], "tipo": body.tipo, "mensagem": body.mensagem.strip(), "pagina": body.pagina, "status": "Novo", "date": now_iso()}
    await db.feedback.insert_one(dict(doc))
    admins = [u["id"] async for u in db.users.find({"role": "admin"}, {"id": 1})]
    await notify(admins, "feedback", f"Nova sugestão ({body.tipo})", f"{user['nome']}: {body.mensagem[:120]}", "/admin")
    return doc


@router.get("/admin/feedback")
async def list_feedback(user: dict = Depends(require_role("admin"))):
    return await db.feedback.find({}, NO_ID).sort("date", -1).to_list(500)


@router.post("/admin/feedback/{fb_id}/status")
async def feedback_status(fb_id: str, body: dict, user: dict = Depends(require_role("admin"))):
    st = body.get("status")
    if st not in ("Novo", "Em análise", "Implementado", "Rejeitado"):
        raise HTTPException(status_code=400, detail="Estado inválido")
    await db.feedback.update_one({"id": fb_id}, {"$set": {"status": st}})
    return {"ok": True}


@router.post("/payments/subscription/cancel")
async def cancel_subscription(user: dict = Depends(get_current_user)):
    import stripe
    sub = await db.subscriptions.find_one({"user_id": user["id"], "status": "active"}, NO_ID)
    if not sub:
        raise HTTPException(status_code=404, detail="Não tem subscrição ativa")
    ends = None
    if sub.get("stripe_subscription_id"):
        try:
            s = stripe.Subscription.modify(sub["stripe_subscription_id"], cancel_at_period_end=True)
            ends = datetime.fromtimestamp(s["current_period_end"], tz=timezone.utc).date().isoformat() if s.get("current_period_end") else None
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Stripe: {e}")
    await db.subscriptions.update_one({"user_id": user["id"], "status": "active"}, {"$set": {"cancel_at_period_end": True, "ends_at": ends, "cancel_requested_at": now_iso()}})
    await audit("SUBSCRIÇÃO", f"Cancelamento agendado" + (f" · termina {ends}" if ends else ""), user, sub["id"])
    return {"ok": True, "ends_at": ends}


@router.get("/payments/subscription")
async def my_subscription(user: dict = Depends(get_current_user)):
    return await db.subscriptions.find_one({"user_id": user["id"]}, NO_ID)


class EmailSettingsIn(BaseModel):
    resend_api_key: Optional[str] = ""
    sender_email: Optional[str] = ""


@router.get("/admin/launch-check")
async def launch_check(request: Request, user: dict = Depends(require_role("admin"))):
    import httpx
    from mailer import configured as mail_ok, load_settings as _load_mail
    await _load_mail()
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    fe = os.environ.get("FRONTEND_URL", "").rstrip("/")
    fe_host = fe.replace("https://", "").replace("http://", "")
    on_domain = bool(fe_host) and fe_host in host
    admins = await db.users.count_documents({"role": "admin", "status": "Ativo"})
    camp = await db.campaigns.find_one({"status": "Ativa"}, NO_ID)
    partners_iban = await db.partners.count_documents({"iban": {"$exists": True, "$ne": ""}})
    partners = await db.partners.count_documents({})
    iban_pf = await db.settings.find_one({"id": "bank"}, NO_ID)
    stripe_live = (os.environ.get("STRIPE_SECRET_KEY") or "").startswith("sk_live")
    connect_ok = False
    try:
        import stripe as _stripe
        _stripe.Account.list(limit=1)
        connect_ok = True
    except Exception:
        connect_ok = False
    coupon_ok, coupon_url = False, None
    if camp and fe:
        coupon_url = f"{fe}/c/{camp['cupom']}"
        try:
            async with httpx.AsyncClient(timeout=6, follow_redirects=True) as cl:
                r = await cl.get(f"{fe}/api/public/coupon/{camp['cupom']}")
                coupon_ok = r.status_code == 200
        except Exception:
            coupon_ok = False
    items = [
        {"id": "domain", "ok": on_domain, "label": f"Site publicado no domínio {fe_host or '(FRONTEND_URL não definido)'}", "hint": f"A aceder por: {host or '?'}" if not on_domain else "Domínio ativo", "action": "Clique Publish na plataforma e ligue o domínio em Publish › Domain."},
        {"id": "https", "ok": request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https", "label": "HTTPS ativo (necessário para câmara e PWA)", "action": "Automático após ligar o domínio."},
        {"id": "login", "ok": admins > 0, "label": "Login Admin funciona", "hint": f"{admins} admin(s) ativos"},
        {"id": "campaign", "ok": bool(camp), "label": "Existe pelo menos uma campanha/cupão ativo", "hint": camp["cupom"] if camp else "Nenhuma", "action": "Crie em Gestão › Campanhas."},
        {"id": "coupon_public", "ok": coupon_ok, "label": "Cupão público responde no domínio final", "hint": coupon_url or "—", "action": "Abra o link do cupão no telemóvel e confirme que carrega."},
        {"id": "scanner", "ok": None, "label": "Scanner QR testado num telemóvel real", "hint": "Teste manual: Parceiro › Validar Cupom › ícone câmara", "action": "Autorize a câmara; se falhar use 'Usar foto do QR'."},
        {"id": "share", "ok": None, "label": "Partilha do QR (imagem) testada no telemóvel", "hint": "Influencer › cupão › Partilhar"},
        {"id": "email", "ok": bool(mail_ok()), "label": "Email (Resend) configurado", "action": "Definições › Email: cole a chave Resend e verifique o domínio rrclub.online no Resend."},
        {"id": "iban", "ok": bool(iban_pf and iban_pf.get("iban")), "label": "IBAN da plataforma definido", "action": "Definições › IBAN da plataforma."},
        {"id": "partners_iban", "ok": partners > 0 and partners_iban == partners, "label": "Todos os parceiros com IBAN", "hint": f"{partners_iban}/{partners}"},
        {"id": "connect", "ok": connect_ok, "label": "Stripe Connect ativo (split automático para parceiros)", "hint": "Conta Stripe da plataforma sem Connect" if not connect_ok else "Connect ativo", "action": "Em dashboard.stripe.com › Connect › Get started, ative Connect na conta ligada a este projeto (a mesma da chave em uso)."},
        {"id": "stripe", "ok": stripe_live, "label": "Stripe em modo live (pagamentos reais)", "hint": "Chave de teste em uso" if not stripe_live else "Live", "action": "Reclame a conta Stripe, conclua o KYC e coloque a chave live nos secrets de produção."},
    ]
    done = sum(1 for i in items if i["ok"] is True)
    return {"items": items, "done": done, "total": len(items), "host": host, "frontend_url": fe}


@router.get("/admin/settings")
async def get_settings(user: dict = Depends(require_role("admin"))):
    from mailer import load_settings
    st = await load_settings()
    pilot = await db.settings.find_one({"id": "pilot"}, NO_ID) or {}
    bank = await db.settings.find_one({"id": "bank"}, NO_ID) or {}
    return {"iban": bank.get("iban", ""), "iban_titular": bank.get("titular", ""), "email_configured": bool(st["key"]), "resend_key_hint": (st["key"][:6] + "•••" + st["key"][-3:]) if st["key"] else "", "sender_email": st["sender"],
            "demo_disabled": bool(pilot.get("demo_disabled")), "pilot_reset_at": pilot.get("reset_at"), "reset_allowed": os.environ.get("ALLOW_PILOT_RESET", "false").lower() == "true",
            "counts": {"users": await db.users.count_documents({}), "redemptions": await db.redemptions.count_documents({}), "campaigns": await db.campaigns.count_documents({}), "partners": await db.partners.count_documents({}), "influencers": await db.influencers.count_documents({})}}


@router.post("/admin/settings/email")
async def save_email_settings(body: EmailSettingsIn, user: dict = Depends(require_role("admin"))):
    from mailer import load_settings, send_email
    upd = {"id": "email", "sender_email": (body.sender_email or "").strip()}
    if body.resend_api_key and body.resend_api_key.strip():
        if not body.resend_api_key.strip().startswith("re_"):
            raise HTTPException(status_code=400, detail="A chave Resend começa por 're_'")
        upd["resend_api_key"] = body.resend_api_key.strip()
    await db.settings.update_one({"id": "email"}, {"$set": upd}, upsert=True)
    st = await load_settings()
    await audit("CONFIGURAÇÃO", "Definições de email atualizadas", user, "email")
    return {"ok": True, "email_configured": bool(st["key"])}


@router.post("/admin/settings/email/test")
async def test_email(user: dict = Depends(require_role("admin"))):
    from mailer import send_email, load_settings
    await load_settings()
    ok = await send_email(user["email"], "RRclub · Email de teste", "Email configurado com sucesso", f"Olá {user['nome']}, este é um email de teste enviado pela plataforma RRclub.")
    if not ok:
        raise HTTPException(status_code=502, detail="Não foi possível enviar. Verifique a chave Resend e o remetente (em modo teste do Resend só envia para o seu próprio email).")
    return {"ok": True}


class ResetIn2(BaseModel):
    confirm: str


@router.post("/admin/reset-pilot")
async def reset_pilot(body: ResetIn2, user: dict = Depends(require_role("admin"))):
    if os.environ.get("ALLOW_PILOT_RESET", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Reset desativado em produção. O piloto já foi zerado.")
    if body.confirm != "ZERAR":
        raise HTTPException(status_code=400, detail="Escreva ZERAR para confirmar")
    keep_ids = [user["id"]]
    owner = await db.users.find_one({"email": os.environ["ADMIN_EMAIL"].lower()}, NO_ID)
    if owner:
        keep_ids.append(owner["id"])
    for c in ("redemptions", "coupon_claims", "leads", "messages", "conversations", "notifications", "feedback", "payouts", "payment_transactions", "entitlements", "subscriptions", "password_reset_tokens", "login_attempts", "campaigns", "partners", "influencers"):
        await db[c].delete_many({})
    await db.users.delete_many({"id": {"$nin": keep_ids}})
    await db.audit_log.delete_many({})
    await db.settings.update_one({"id": "pilot"}, {"$set": {"id": "pilot", "demo_disabled": True, "reset_at": now_iso(), "by": user["nome"]}}, upsert=True)
    await audit("SISTEMA", f"Dados piloto zerados por {user['nome']} — plataforma pronta para produção", user, "pilot")
    return {"ok": True, "kept_admins": len(keep_ids)}


class PlatformIbanIn(BaseModel):
    iban: str
    titular: Optional[str] = ""


@router.post("/admin/settings/iban")
async def save_platform_iban(body: PlatformIbanIn, user: dict = Depends(require_role("admin"))):
    iban = body.iban.replace(" ", "").upper()
    if iban and not (15 <= len(iban) <= 34 and iban[:2].isalpha() and iban[2:4].isdigit()):
        raise HTTPException(status_code=400, detail="IBAN inválido")
    await db.settings.update_one({"id": "bank"}, {"$set": {"id": "bank", "iban": iban, "titular": body.titular.strip()}}, upsert=True)
    await audit("CONFIGURAÇÃO", f"IBAN da plataforma atualizado · ••••{iban[-4:] if iban else ''}", user, "bank")
    return {"ok": True, "iban": iban}


@router.get("/public/bank")
async def public_bank(user: dict = Depends(get_current_user)):
    bank = await db.settings.find_one({"id": "bank"}, NO_ID) or {}
    return {"iban": bank.get("iban", ""), "titular": bank.get("titular", "")}


@router.get("/influencer/me")
async def influencer_me(user: dict = Depends(require_role("influencer"))):
    return await db.influencers.find_one({"id": user["influencer_id"]}, NO_ID) or {}


class InfIbanIn(BaseModel):
    iban: str


@router.post("/influencer/iban")
async def influencer_iban(body: InfIbanIn, user: dict = Depends(require_role("influencer"))):
    iban = body.iban.replace(" ", "").upper()
    if not (15 <= len(iban) <= 34 and iban[:2].isalpha() and iban[2:4].isdigit()):
        raise HTTPException(status_code=400, detail="IBAN inválido")
    await db.influencers.update_one({"id": user["influencer_id"]}, {"$set": {"iban": iban}})
    await audit("CONFIGURAÇÃO", f"IBAN de comissões atualizado · {user['nome']} · ••••{iban[-4:]}", user, user["influencer_id"])
    return {"ok": True, "iban": iban}


@router.get("/campaigns/{campaign_id}/poster.pdf")
async def campaign_poster(campaign_id: str, site: str = "", user: dict = Depends(get_current_user)):
    from poster import render_poster
    q = {"id": campaign_id}
    if user["role"] == "influencer":
        q["influencer_id"] = user.get("influencer_id")
    elif user["role"] == "partner":
        q["parceiro_id"] = user.get("partner_id")
    c = await db.campaigns.find_one(q, NO_ID)
    if not c:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    partner = await db.partners.find_one({"id": c.get("parceiro_id")}, NO_ID) or {}
    inf = await db.influencers.find_one({"id": c.get("influencer_id")}, NO_ID) or {}
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    pdf = render_poster(c["cupom"], float(c["desconto"]), partner.get("nome", ""), inf.get("handle") or inf.get("nome", ""), f"{base}/c/{c['cupom']}", partner.get("cidade", ""))
    await audit("CARTAZ", f"Cartaz A5 gerado · {c['cupom']}", user, campaign_id)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="cartaz-{c["cupom"]}.pdf"'})


@router.get("/influencer/story-video/{campaign_id}")
async def story_video(campaign_id: str, user: dict = Depends(require_role("influencer"))):
    import asyncio, hashlib, re as _re
    from fastapi.responses import FileResponse
    from story_video import render_story, MEDIA_DIR
    c = await db.campaigns.find_one({"id": campaign_id, "influencer_id": user["influencer_id"]}, NO_ID)
    if not c:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    partner = await db.partners.find_one({"id": c.get("parceiro_id")}, NO_ID) or {}
    inf = await db.influencers.find_one({"id": user["influencer_id"]}, NO_ID) or {}
    site = _re.sub(r"^https?://", "", os.environ.get("FRONTEND_URL", "")).rstrip("/")
    key = hashlib.md5(f"{c['cupom']}|{user['nome']}|{inf.get('handle','')}|{c['desconto']}|{partner.get('nome','')}|{site}|v2".encode()).hexdigest()[:12]
    out = MEDIA_DIR / f"story-{c['cupom']}-{key}.mp4"
    if not out.exists():
        await asyncio.to_thread(render_story, out, user["nome"], inf.get("handle", ""), c["cupom"], float(c["desconto"]), partner.get("nome", ""), site)
        await audit("VÍDEO", f"Story personalizado gerado · {c['cupom']}", user, campaign_id)
    return FileResponse(str(out), media_type="video/mp4", filename=f"story-{c['cupom']}.mp4")
