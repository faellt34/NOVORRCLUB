import asyncio
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException

from core import db, NO_ID, require_role, audit, new_id, now_iso
from realtime import emit, broadcast

router = APIRouter()
TEST_COLLECTIONS = ("redemptions", "coupon_claims", "audit_log", "notifications", "payouts", "login_attempts", "password_reset_tokens", "click_events", "erros_transferencia")


@router.post("/admin/reset-all")
async def reset_all(body: dict, user: dict = Depends(require_role("admin"))):
    raise HTTPException(status_code=403, detail="Limpeza de dados desativada para preservar registos.")


async def _step(run_id: str, passo: int, titulo: str, estado: str, **extra):
    await broadcast("teste_passo", run_id=run_id, passo=passo, titulo=titulo, estado=estado, **extra)


@router.post("/admin/test-run")
async def test_run(body: dict, user: dict = Depends(require_role("admin"))):
    inf = await db.influencers.find_one({"id": body.get("influencer_id")}, NO_ID)
    partner = await db.partners.find_one({"id": body.get("partner_id")}, NO_ID)
    if not inf or not partner:
        raise HTTPException(status_code=400, detail="Escolha um influencer e um parceiro")
    valor = float(str(body.get("valor") or 50).replace(",", "."))
    run_id = new_id("test")
    ts = now_iso()
    cupom = f"TEST-{secrets.token_hex(3).upper()}"
    camp = {"id": new_id("c"), "nome": f"Teste #{datetime.now(timezone.utc).strftime('%H%M%S')}", "parceiro_id": partner["id"], "parceiro": partner["nome"], "influencer_id": inf["id"], "influencer": inf["nome"],
            "cupom": cupom, "desconto": 10.0, "comissao": 5.0, "validade": (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat(), "status": "Ativa", "is_test": True, "test_run_id": run_id, "created_at": ts}
    await db.campaigns.insert_one(dict(camp))
    await _step(run_id, 1, "Campanha criada", "ok", cupom=cupom)
    emit("cupom_gerado", cupom=cupom, campanha=camp["nome"], quantidade=1, ref=camp["id"], is_test=True)
    emit("cupons_gerados", quantidade=1, cupom=cupom, campanha=camp["nome"], parceiro=partner["nome"], por=user["nome"], ref=camp["id"])
    await asyncio.sleep(0.6)
    await _step(run_id, 2, "QR gerado", "ok", cupom=cupom)
    await asyncio.sleep(0.6)
    await _step(run_id, 3, "A simular clique do cliente...", "run")
    cl = {"id": new_id("cl"), "key": f"{cupom}:test:{run_id}", "coupon": cupom, "campaign_id": camp["id"], "campaign": camp["nome"], "influencer_id": inf["id"], "influencer": inf["nome"], "partner_id": partner["id"], "partner": partner["nome"],
          "origem": "Teste", "cliente": "Cliente de teste", "date": now_iso(), "created_at": now_iso(), "qr_downloaded": False, "qr_downloaded_at": None, "converted": False, "converted_at": None, "valor": None, "is_test": True, "test_run_id": run_id}
    await db.coupon_claims.insert_one(dict(cl))
    dados = {k: cl[k] for k in ("id", "coupon", "campaign", "influencer", "partner", "origem", "cliente", "date", "qr_downloaded", "converted", "valor")}
    emit("clique_cupao", cupom=cupom, campanha=camp["nome"], origem="Teste", influencer=inf["nome"], influencer_id=inf["id"], partner_id=partner["id"], ref=cl["id"])
    emit("novo_clique", dados=dados, campanha_id=camp["id"], influencer_id=inf["id"], partner_id=partner["id"], origem="Teste")
    await asyncio.sleep(0.7)
    await _step(run_id, 3, "Cliente clicou no link", "ok")
    await _step(run_id, 4, "A simular download do QR...", "run")
    await asyncio.sleep(0.7)
    qts = now_iso()
    await db.coupon_claims.update_one({"id": cl["id"]}, {"$set": {"qr_downloaded": True, "qr_downloaded_at": qts}})
    emit("qr_baixado", claim_id=cl["id"], cupom_id=cl["id"], cupom=cupom, at=qts, influencer_id=inf["id"], partner_id=partner["id"])
    await _step(run_id, 4, "QR baixado", "ok")
    await _step(run_id, 5, "A simular pagamento Stripe (modo teste)...", "run")
    await asyncio.sleep(0.9)
    rate = 0.05
    rec = {"id": new_id("r"), "coupon": cupom, "campaign_id": camp["id"], "campaign": camp["nome"], "partner_id": partner["id"], "partner": partner["nome"], "influencer_id": inf["id"], "influencer": inf["nome"],
           "amount": round(valor, 2), "discount": round(valor * 0.10, 2), "commission": round(valor * rate, 2), "rate": rate, "date": now_iso(), "staff": "Simulação (modo teste)", "idempotency_key": f"test-{run_id}",
           "paid_online": True, "payment_method": "card_test", "is_test": True, "test_run_id": run_id}
    await db.redemptions.insert_one(dict(rec))
    await db.payment_transactions.insert_one({"id": new_id("pt"), "session_id": f"cs_test_{run_id}", "kind": "qr_test", "coupon": cupom, "amount": round(valor * 0.9, 2), "gross_amount": valor, "status": "paid", "payment_status": "paid",
                                              "partner_id": partner["id"], "redemption_id": rec["id"], "is_test": True, "test_run_id": run_id, "created_at": now_iso()})
    await _step(run_id, 5, f"Pagamento processado — €{valor:.0f}", "ok", valor=valor)
    await _step(run_id, 6, "A executar split...", "run")
    await asyncio.sleep(0.6)
    await db.coupon_claims.update_one({"id": cl["id"]}, {"$set": {"converted": True, "converted_at": rec["date"], "valor": valor, "redemption_id": rec["id"]}})
    await audit("REDENÇÃO", f"{cupom} · TESTE · {valor:.2f}€ · {partner['nome']}", user, rec["id"])
    emit("split_executado", valor_plataforma=rec["commission"], valor_total=valor, cupom=cupom, parceiro=partner["nome"], influencer=inf["nome"], ref=rec["id"], origem="qr", influencer_id=inf["id"], partner_id=partner["id"], record=rec, is_test=True)
    emit("venda", valor=valor, comissao=rec["commission"], cupom=cupom, claim_id=cl["id"], at=rec["date"], influencer_id=inf["id"], partner_id=partner["id"])
    emit("venda_validada", valor=valor, restaurante_id=partner["id"], influencer_id=inf["id"], partner_id=partner["id"], cupom=cupom)
    split = {"restaurante": round(valor * 0.75, 2), "influencer": round(valor * 0.05, 2), "rrclub": round(valor * 0.10, 2), "stripe": round(valor * 0.10, 2)}
    await _step(run_id, 6, "Split executado", "ok", split=split)
    return {"run_id": run_id, "campaign_id": camp["id"], "cupom": cupom, "claim_id": cl["id"], "redemption_id": rec["id"], "valor": valor, "split": split}


@router.delete("/admin/test-run/{run_id}")
async def delete_test_run(run_id: str, user: dict = Depends(require_role("admin"))):
    raise HTTPException(status_code=403, detail="Exclusão de testes desativada para preservar registos.")


@router.post("/admin/test-run/clear-all")
async def clear_all_tests(body: dict, user: dict = Depends(require_role("admin"))):
    raise HTTPException(status_code=403, detail="Limpeza de testes desativada para preservar registos.")
