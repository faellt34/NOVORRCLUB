import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core import db, NO_ID, require_role, new_id, now_iso
from routes_data import since

router = APIRouter()
MODEL = ("anthropic", "claude-sonnet-4-6")


class AskIn(BaseModel):
    session_id: str | None = None
    message: str


async def _context() -> str:
    reds = await db.redemptions.find({"date": {"$gte": since(30)}}, {"_id": 0, "amount": 1, "commission": 1, "coupon": 1, "partner": 1, "influencer": 1, "date": 1, "paid_online": 1, "is_test": 1}).to_list(5000)
    claims = await db.coupon_claims.find({"date": {"$gte": since(30)}}, {"_id": 0, "coupon": 1, "origem": 1, "qr_downloaded": 1, "converted": 1, "date": 1}).to_list(20000)
    camps = await db.campaigns.find({}, {"_id": 0, "nome": 1, "cupom": 1, "parceiro": 1, "influencer": 1, "desconto": 1, "comissao": 1, "status": 1, "validade": 1, "is_test": 1}).to_list(300)
    by_coupon = {}
    for r in reds:
        d = by_coupon.setdefault(r["coupon"], {"vendas": 0, "receita": 0.0, "comissao": 0.0})
        d["vendas"] += 1; d["receita"] += r["amount"]; d["comissao"] += r["commission"]
    for c in claims:
        d = by_coupon.setdefault(c["coupon"], {"vendas": 0, "receita": 0.0, "comissao": 0.0})
        d["cliques"] = d.get("cliques", 0) + 1
        d["qr"] = d.get("qr", 0) + (1 if c.get("qr_downloaded") else 0)
    origins = {}
    for c in claims:
        origins[c.get("origem", "?")] = origins.get(c.get("origem", "?"), 0) + 1
    summary = {"hoje": datetime.now(timezone.utc).date().isoformat(), "janela": "últimos 30 dias",
               "totais": {"vendas": len(reds), "receita": round(sum(r["amount"] for r in reds), 2), "comissoes": round(sum(r["commission"] for r in reds), 2), "cliques": len(claims),
                          "qr_baixados": sum(1 for c in claims if c.get("qr_downloaded")), "convertidos": sum(1 for c in claims if c.get("converted")), "pagos_online": sum(1 for r in reds if r.get("paid_online"))},
               "origens": origins, "por_cupom": by_coupon, "campanhas": camps,
               "contagens": {"influencers": await db.influencers.count_documents({"status": "Ativo"}), "parceiros": await db.partners.count_documents({"status": "Ativo"})}}
    return json.dumps(summary, ensure_ascii=False, default=str)


@router.post("/admin/ai/ask")
async def ai_ask(body: AskIn, user: dict = Depends(require_role("admin"))):
    from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone
    session_id = body.session_id or new_id("ai")
    history = await db.ai_messages.find({"session_id": session_id}, NO_ID).sort("date", 1).to_list(40)
    ctx = await _context()
    system = ("És o analista de dados do RR CLUB, uma plataforma portuguesa que liga influencers a restaurantes/parceiros através de cupões QR. "
              "Responde sempre em português de Portugal, de forma curta, direta e acionável (máx. ~180 palavras), com números concretos retirados dos DADOS. "
              "Quando fizer sentido, termina com 2-3 ações sugeridas em lista. Se não houver dados suficientes, diz isso claramente e sugere como obter. "
              "Split de cada venda: parceiro 75%, influencer 5%, RR CLUB 10%, Stripe 10%. Dados marcados is_test são simulações.\n\nDADOS (JSON):\n" + ctx)
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=session_id, system_message=system).with_model(*MODEL)
    prior = "\n".join(f"{m['role']}: {m['content']}" for m in history[-10:])
    text = (f"Conversa anterior:\n{prior}\n\nNova pergunta: {body.message}" if prior else body.message)
    await db.ai_messages.insert_one({"id": new_id("m"), "session_id": session_id, "role": "user", "content": body.message, "date": now_iso(), "user_id": user["id"]})

    async def gen():
        yield f"event: meta\ndata: {json.dumps({'session_id': session_id})}\n\n"
        full = []
        try:
            async for ev in chat.stream_message(UserMessage(text=text)):
                if isinstance(ev, TextDelta):
                    full.append(ev.content)
                    yield f"data: {json.dumps(ev.content)}\n\n"
                elif isinstance(ev, StreamDone):
                    break
        except Exception as e:
            yield f"event: error\ndata: {json.dumps(str(e))}\n\n"
        answer = "".join(full)
        if answer:
            await db.ai_messages.insert_one({"id": new_id("m"), "session_id": session_id, "role": "assistant", "content": answer, "date": now_iso(), "user_id": user["id"]})
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/admin/ai/history")
async def ai_history(session_id: str, user: dict = Depends(require_role("admin"))):
    return await db.ai_messages.find({"session_id": session_id}, NO_ID).sort("date", 1).to_list(100)


class CaptionIn(BaseModel):
    campaign_id: str
    tom: str = "elegante"


@router.post("/influencer/ai/captions")
async def ai_captions(body: CaptionIn, user: dict = Depends(require_role("influencer"))):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    c = await db.campaigns.find_one({"id": body.campaign_id, "influencer_id": user.get("influencer_id")}, NO_ID)
    if not c:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    partner = await db.partners.find_one({"id": c.get("parceiro_id")}, NO_ID) or {}
    inf = await db.influencers.find_one({"id": user.get("influencer_id")}, NO_ID) or {}
    link = f"{os.environ.get('FRONTEND_URL', '').rstrip('/')}/c/{c['cupom']}"
    prompt = (f"Cria legendas de Instagram Story/Reel para o influencer {inf.get('nome')} ({inf.get('handle', '')}) promover o cupão {c['cupom']} com {c['desconto']:g}% de desconto "
              f"em {partner.get('nome')} ({partner.get('categoria', '')}, {partner.get('cidade', '')}). Link: {link}. Tom: {body.tom}. "
              "Devolve APENAS JSON válido com esta forma: {\"pt\": [\"...\", \"...\"], \"en\": [\"...\", \"...\"], \"es\": [\"...\", \"...\"]} — 2 legendas por idioma, "
              "cada uma com 1-2 frases, 2-4 emojis, o código do cupão em MAIÚSCULAS, um call-to-action e 3 hashtags no fim. Português de Portugal no pt.")
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=new_id("cap"), system_message="És um copywriter de redes sociais para experiências premium. Respondes só com JSON.").with_model(*MODEL)
    raw = await chat.send_message(UserMessage(text=prompt))
    txt = raw.strip()
    if txt.startswith("```"):
        txt = txt.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        data = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
    except Exception:
        data = {"pt": [raw], "en": [], "es": []}
    return {"cupom": c["cupom"], "link": link, "captions": {k: [s for s in data.get(k, []) if isinstance(s, str)] for k in ("pt", "en", "es")}}
