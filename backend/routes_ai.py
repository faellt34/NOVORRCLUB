import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from payment_policy import reporting_currency, currency_query

from core import db, NO_ID, require_role, new_id, now_iso
from routes_data import since

router = APIRouter()
MODEL = ("anthropic", "claude-sonnet-4-6")


def ai_error_message(error):
    message = str(error).lower()
    if any(term in message for term in ("budget", "quota", "credit", "billing")):
        return "Assistente temporariamente indisponível por limite do serviço de IA. A administração precisa verificar o saldo e o orçamento no fornecedor."
    return "O serviço de IA está temporariamente indisponível. Tente novamente mais tarde."


class AskIn(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=4000)


async def _context(currency="eur") -> str:
    reds = await db.redemptions.find(currency_query({"date": {"$gte": since(30)}}, currency), {"_id": 0, "amount": 1, "commission": 1, "coupon": 1, "partner": 1, "influencer": 1, "date": 1, "paid_online": 1, "is_test": 1, "is_refund": 1, "dispute_hold": 1}).to_list(5000)
    claims = await db.coupon_claims.find(currency_query({"date": {"$gte": since(30)}}, currency), {"_id": 0, "coupon": 1, "origem": 1, "qr_downloaded": 1, "converted": 1, "date": 1}).to_list(20000)
    camps = await db.campaigns.find(currency_query({}, currency), {"_id": 0, "nome": 1, "cupom": 1, "parceiro": 1, "influencer": 1, "desconto": 1, "comissao": 1, "status": 1, "validade": 1, "is_test": 1}).to_list(300)
    by_coupon = {}
    for r in reds:
        d = by_coupon.setdefault(r["coupon"], {"vendas": 0, "receita": 0.0, "comissao": 0.0})
        d["vendas"] += 0 if r.get("is_refund") else 1; d["receita"] += r["amount"]; d["comissao"] += (0 if r.get("dispute_hold") else r["commission"])
    for c in claims:
        d = by_coupon.setdefault(c["coupon"], {"vendas": 0, "receita": 0.0, "comissao": 0.0})
        d["cliques"] = d.get("cliques", 0) + 1
        d["qr"] = d.get("qr", 0) + (1 if c.get("qr_downloaded") else 0)
    origins = {}
    for c in claims:
        origins[c.get("origem", "?")] = origins.get(c.get("origem", "?"), 0) + 1
    summary = {"moeda": currency.upper(), "hoje": datetime.now(timezone.utc).date().isoformat(), "janela": "últimos 30 dias",
               "totais": {"vendas": sum(not r.get("is_refund") for r in reds), "receita": round(sum(r["amount"] for r in reds), 2), "comissoes": round(sum((0 if r.get("dispute_hold") else r["commission"]) for r in reds), 2), "cliques": len(claims),
                          "qr_baixados": sum(1 for c in claims if c.get("qr_downloaded")), "convertidos": sum(1 for c in claims if c.get("converted")), "pagos_online": sum(1 for r in reds if r.get("paid_online"))},
               "origens": origins, "por_cupom": by_coupon, "campanhas": camps,
               "contagens": {"influencers": await db.influencers.count_documents({"status": "Ativo"}), "parceiros": await db.partners.count_documents({"status": "Ativo"})}}
    return json.dumps(summary, ensure_ascii=False, default=str)


@router.post("/admin/ai/ask")
async def ai_ask(body: AskIn, user: dict = Depends(require_role("admin")), currency: str = Depends(reporting_currency)):
    if not os.getenv("EMERGENT_LLM_KEY"):
        raise HTTPException(503, "Assistente temporariamente indisponível. A administração precisa configurar o serviço de IA.")
    from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone
    session_id = body.session_id or new_id("ai")
    history = await db.ai_messages.find(currency_query({"session_id": session_id, "user_id": user["id"]}, currency), NO_ID).sort("date", 1).to_list(40)
    ctx = await _context(currency)
    system = ("És o analista de dados do RR CLUB, uma plataforma portuguesa que liga influencers a restaurantes/parceiros através de cupões QR. "
              "Responde sempre em português de Portugal, de forma curta, direta e acionável (máx. ~180 palavras), com números concretos retirados dos DADOS. "
              "Quando fizer sentido, termina com 2-3 ações sugeridas em lista. Se não houver dados suficientes, diz isso claramente e sugere como obter. "
              "Regra do Pix Brasil sobre o valor original: desconto do cliente 5%, cliente paga 95%, parceiro recebe 80%, influencer 5%, RR Club 10% antes dos custos. A RR Club assume as tarifas reais; nunca inventes uma tarifa fixa da Stripe. Esta regra não define os contratos de Portugal. Não somes moedas diferentes. Dados marcados is_test são simulações.\n\nDADOS (JSON):\n" + ctx)
    try:
        chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=session_id, system_message=system).with_model(*MODEL)
    except Exception as error:
        raise HTTPException(503, ai_error_message(error))
    prior = "\n".join(f"{m['role']}: {m['content']}" for m in history[-10:])
    text = (f"Conversa anterior:\n{prior}\n\nNova pergunta: {body.message}" if prior else body.message)
    await db.ai_messages.insert_one({"id": new_id("m"), "session_id": session_id, "role": "user", "content": body.message, "date": now_iso(), "user_id": user["id"], "currency": currency})

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
            yield f"event: error\ndata: {json.dumps(ai_error_message(e))}\n\n"
        answer = "".join(full)
        if answer:
            await db.ai_messages.insert_one({"id": new_id("m"), "session_id": session_id, "role": "assistant", "content": answer, "date": now_iso(), "user_id": user["id"], "currency": currency})
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/admin/ai/history")
async def ai_history(session_id: str, user: dict = Depends(require_role("admin")), currency: str = Depends(reporting_currency)):
    return await db.ai_messages.find(currency_query({"session_id": session_id, "user_id": user["id"]}, currency), NO_ID).sort("date", 1).to_list(100)

class StoryImageIn(BaseModel):
    campaign_id: str
    estilo: str = "luxo"


@router.post("/influencer/ai/story-image")
async def ai_story_image(body: StoryImageIn, user: dict = Depends(require_role("influencer"))):
    import base64
    from fastapi import HTTPException
    from fastapi.responses import Response
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    c = await db.campaigns.find_one({"id": body.campaign_id, "influencer_id": user.get("influencer_id")}, NO_ID)
    if not c:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    partner = await db.partners.find_one({"id": c.get("parceiro_id")}, NO_ID) or {}
    estilos = {"luxo": "dark luxury editorial photography, deep purple and gold accents, soft candlelight, shallow depth of field",
               "fresco": "bright airy lifestyle photo, natural daylight, pastel tones, minimal and clean",
               "noite": "vibrant nightlife, neon purple and violet lights, city bokeh, cinematic"}
    prompt = (f"Vertical 9:16 Instagram story image for a premium {partner.get('categoria') or 'restaurant'} named '{partner.get('nome')}' in {partner.get('cidade') or 'Lisbon'}. "
              f"{estilos.get(body.estilo, estilos['luxo'])}. Show an inviting scene (signature dish or elegant ambience), no people faces. "
              f"Leave clean negative space in the lower third. Render the text '{c['desconto']:g}% OFF' large and the coupon code '{c['cupom']}' in a small elegant pill, both in white sans-serif, perfectly legible. "
              "Brand mark: small text 'RRclub' at the top. No other text, no watermarks.")
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=new_id("img"), system_message="You generate polished marketing images.").with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
    _, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))
    if not images:
        raise HTTPException(status_code=409, detail="O Gemini não devolveu imagem. Tente outro estilo.")
    img = images[0]
    return Response(base64.b64decode(img["data"]), media_type=img.get("mime_type", "image/png"), headers={"Content-Disposition": f'inline; filename="story-{c["cupom"]}.png"'})


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
