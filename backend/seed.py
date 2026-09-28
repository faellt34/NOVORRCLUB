import os
import random
from datetime import datetime, timedelta, timezone

from core import db, hash_password, new_id, verify_password, now_iso

AVATAR = "https://i.pravatar.cc/80?img={}"

USERS = [
    {"id": "adm-1", "email": os.environ["ADMIN_EMAIL"].lower(), "password": os.environ["ADMIN_PASSWORD"], "nome": "Rafael (Admin)", "role": "admin", "avatar": AVATAR.format(33), "handle": "Admin Geral"},
    {"id": "adm-2", "email": "admin@robson.club", "password": "admin123", "nome": "Admin Geral", "role": "admin", "avatar": AVATAR.format(60), "handle": "admin@robson.club"},
    {"id": "usr-inf1", "email": "robson@robson.club", "password": "robson123", "nome": "Robson Oliveira", "role": "influencer", "avatar": AVATAR.format(12), "handle": "@robson.luxe", "influencer_id": "if1"},
    {"id": "usr-inf2", "email": "marta@robson.club", "password": "marta123", "nome": "Marta Vasconcelos", "role": "influencer", "avatar": AVATAR.format(45), "handle": "@marta.lx", "influencer_id": "if2"},
    {"id": "usr-inf3", "email": "diogo@robson.club", "password": "diogo123", "nome": "Diogo Fontes", "role": "influencer", "avatar": AVATAR.format(53), "handle": "@diogo.eats", "influencer_id": "if3"},
    {"id": "usr-par1", "email": "gerencia@tivolisky.pt", "password": "tivoli123", "nome": "Tivoli Sky Bar Lisboa", "role": "partner", "avatar": AVATAR.format(68), "handle": "Rooftop · Lisboa", "partner_id": "p1"},
    {"id": "usr-par2", "email": "reservas@belcanto.pt", "password": "belcanto123", "nome": "Belcanto", "role": "partner", "avatar": AVATAR.format(59), "handle": "Restaurante · Lisboa", "partner_id": "p2"},
]

INFLUENCERS = [
    {"id": "if1", "user_id": "usr-inf1", "nome": "Robson Oliveira", "handle": "@robson.luxe", "cidade": "Lisboa", "status": "Ativo", "avatar": AVATAR.format(12)},
    {"id": "if2", "user_id": "usr-inf2", "nome": "Marta Vasconcelos", "handle": "@marta.lx", "cidade": "Lisboa", "status": "Ativo", "avatar": AVATAR.format(45)},
    {"id": "if3", "user_id": "usr-inf3", "nome": "Diogo Fontes", "handle": "@diogo.eats", "cidade": "Porto", "status": "Ativo", "avatar": AVATAR.format(53)},
    {"id": "if4", "user_id": None, "nome": "Inês Castelo", "handle": "@ines.castelo", "cidade": "Algarve", "status": "Suspenso", "avatar": AVATAR.format(31)},
]

PARTNERS = [
    {"id": "p1", "user_id": "usr-par1", "nome": "Tivoli Sky Bar", "categoria": "Rooftop", "cidade": "Lisboa", "status": "Ativo", "avatar": AVATAR.format(68)},
    {"id": "p2", "user_id": "usr-par2", "nome": "Belcanto", "categoria": "Restaurante", "cidade": "Lisboa", "status": "Ativo", "avatar": AVATAR.format(59)},
    {"id": "p3", "user_id": None, "nome": "The Yeatman", "categoria": "Hotel", "cidade": "Porto", "status": "Ativo", "avatar": AVATAR.format(15)},
    {"id": "p4", "user_id": None, "nome": "Vila Vita Parc", "categoria": "Hotel", "cidade": "Algarve", "status": "Ativo", "avatar": AVATAR.format(5)},
    {"id": "p5", "user_id": None, "nome": "Quinta do Crasto", "categoria": "Passeio", "cidade": "Douro", "status": "Ativo", "avatar": AVATAR.format(22)},
]

def VAL(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).date().isoformat()


CAMPAIGNS = [
    {"id": "c1", "nome": "Sunset Sessions Verão", "parceiro_id": "p1", "influencer_id": "if1", "cupom": "ROBSON-LUXE-25", "desconto": 15, "comissao": 10, "validade": VAL(120), "status": "Ativa"},
    {"id": "c2", "nome": "Menu Degustação Estrela", "parceiro_id": "p2", "influencer_id": "if1", "cupom": "ROBSON-BEL-10", "desconto": 10, "comissao": 10, "validade": VAL(90), "status": "Ativa"},
    {"id": "c3", "nome": "Wine Escape Porto", "parceiro_id": "p3", "influencer_id": "if1", "cupom": "ROBSON-YEAT-20", "desconto": 20, "comissao": 12, "validade": VAL(60), "status": "Ativa"},
    {"id": "c4", "nome": "Algarve Golden Week", "parceiro_id": "p4", "influencer_id": "if1", "cupom": "ROBSON-VITA-15", "desconto": 15, "comissao": 10, "validade": VAL(30), "status": "Pausada"},
    {"id": "c5", "nome": "Douro Harvest Tour", "parceiro_id": "p5", "influencer_id": "if1", "cupom": "ROBSON-DOURO-10", "desconto": 10, "comissao": 8, "validade": VAL(-90), "status": "Expirada"},
    {"id": "c6", "nome": "Sky Nights", "parceiro_id": "p1", "influencer_id": "if2", "cupom": "MARTA-SKY-10", "desconto": 10, "comissao": 10, "validade": VAL(200), "status": "Ativa"},
    {"id": "c7", "nome": "Sky Nights", "parceiro_id": "p1", "influencer_id": "if3", "cupom": "DIOGO-SKY-15", "desconto": 15, "comissao": 10, "validade": VAL(200), "status": "Ativa"},
    {"id": "c8", "nome": "Chef's Table", "parceiro_id": "p2", "influencer_id": "if2", "cupom": "MARTA-BEL-10", "desconto": 10, "comissao": 10, "validade": VAL(170), "status": "Ativa"},
]

IMG = {
    "rooftop": "https://images.unsplash.com/photo-1786520403993-e1dfdc0864b5?crop=entropy&cs=srgb&fm=jpg&q=85&w=800",
    "dish": "https://images.unsplash.com/photo-1786520403836-bbb95ed8904f?crop=entropy&cs=srgb&fm=jpg&q=85&w=800",
    "porto": "https://images.unsplash.com/photo-1634057306449-51bc02166e3d?crop=entropy&cs=srgb&fm=jpg&q=85&w=800",
    "hotel": "https://images.unsplash.com/photo-1589125753960-3793f25d50dc?crop=entropy&cs=srgb&fm=jpg&q=85&w=800",
    "spain": "https://images.unsplash.com/photo-1539037116277-4db20889f2d4?crop=entropy&cs=srgb&fm=jpg&q=85&w=800",
    "italy": "https://images.unsplash.com/photo-1523906834658-6e24ef2386f9?crop=entropy&cs=srgb&fm=jpg&q=85&w=800",
    "paris": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?crop=entropy&cs=srgb&fm=jpg&q=85&w=800",
    "dubai": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?crop=entropy&cs=srgb&fm=jpg&q=85&w=800",
}

EBOOKS = [
    {"id": "e1", "titulo": "Rooftops Secretos de Lisboa", "pais": "Portugal", "regiao": "Lisboa", "categoria": "Rooftops", "premium": True, "paginas": 42, "capa": IMG["rooftop"], "descricao": "Os 12 rooftops com as melhores vistas e cocktails de autor da capital.", "idioma": "PT", "preco": 14.9},
    {"id": "e2", "titulo": "Guia Gastronómico Estrelado", "pais": "Portugal", "regiao": "Lisboa", "categoria": "Restaurantes", "premium": False, "paginas": 36, "capa": IMG["dish"], "descricao": "Menus de degustação imperdíveis, do Chiado a Belém.", "idioma": "PT", "preco": 0},
    {"id": "e3", "titulo": "Porto Boutique & Heritage", "pais": "Portugal", "regiao": "Porto", "categoria": "Hotéis", "premium": True, "paginas": 54, "capa": IMG["porto"], "descricao": "Hotéis-palacete e quartos com vista para o Douro.", "idioma": "PT", "preco": 19.9},
    {"id": "e4", "titulo": "Wine Bars da Ribeira", "pais": "Portugal", "regiao": "Porto", "categoria": "Restaurantes", "premium": False, "paginas": 28, "capa": IMG["dish"], "descricao": "Onde provar os melhores Vinhos do Porto junto ao rio.", "idioma": "PT", "preco": 0},
    {"id": "e5", "titulo": "Resorts Escondidos do Algarve", "pais": "Portugal", "regiao": "Algarve", "categoria": "Hotéis", "premium": True, "paginas": 48, "capa": IMG["hotel"], "descricao": "Luxo discreto entre falésias, dos Salgados à Ponta da Piedade.", "idioma": "PT", "preco": 17.9},
    {"id": "e6", "titulo": "Sunset Spots do Algarve", "pais": "Portugal", "regiao": "Algarve", "categoria": "Rooftops", "premium": False, "paginas": 22, "capa": IMG["rooftop"], "descricao": "Terraços e beach clubs para o pôr do sol perfeito.", "idioma": "PT", "preco": 0},
    {"id": "e7", "titulo": "Douro: Quintas & Vindimas", "pais": "Portugal", "regiao": "Douro", "categoria": "Passeios", "premium": True, "paginas": 60, "capa": IMG["porto"], "descricao": "Roteiro completo de quintas, provas e cruzeiros privados.", "idioma": "PT", "preco": 21.9},
    {"id": "e8", "titulo": "Hotéis com Azulejo & História", "pais": "Portugal", "regiao": "Lisboa", "categoria": "Hotéis", "premium": True, "paginas": 38, "capa": IMG["hotel"], "descricao": "Dormir em fachadas pombalinas restauradas ao detalhe.", "idioma": "PT", "preco": 14.9},
    {"id": "e9", "titulo": "Madrid & Barcelona: Azoteas de Luxo", "pais": "Espanha", "regiao": "Madrid", "categoria": "Rooftops", "premium": True, "paginas": 46, "capa": IMG["spain"], "descricao": "As azoteas mais exclusivas de Espanha, com reservas prioritárias.", "idioma": "PT/ES", "preco": 16.9},
    {"id": "e10", "titulo": "Costa Amalfitana Secreta", "pais": "Itália", "regiao": "Amalfi", "categoria": "Hotéis", "premium": True, "paginas": 52, "capa": IMG["italy"], "descricao": "Villas, limoncello e barcos privados entre Positano e Ravello.", "idioma": "PT/EN", "preco": 22.9},
    {"id": "e11", "titulo": "Paris: Bistrôs com Estrela", "pais": "França", "regiao": "Paris", "categoria": "Restaurantes", "premium": False, "paginas": 30, "capa": IMG["paris"], "descricao": "Onde os parisienses jantam quando querem impressionar.", "idioma": "PT/EN", "preco": 0},
    {"id": "e12", "titulo": "Dubai Sky High", "pais": "Emirados", "regiao": "Dubai", "categoria": "Rooftops", "premium": True, "paginas": 40, "capa": IMG["dubai"], "descricao": "Lounges no céu, brunches e experiências de deserto de luxo.", "idioma": "PT/EN", "preco": 24.9},
]

STAFF = ["Ana P.", "João M.", "Carla S."]


def gen_redemptions():
    rng = random.Random(42)
    ref = datetime.now(timezone.utc)
    weights = {"c1": 34, "c2": 24, "c3": 16, "c4": 12, "c5": 6, "c6": 18, "c7": 12, "c8": 8}
    by_id = {c["id"]: c for c in CAMPAIGNS}
    parts = {p["id"]: p for p in PARTNERS}
    infs = {i["id"]: i for i in INFLUENCERS}
    out = []
    for day in range(120):
        d = ref - timedelta(days=day)
        n = max(2, int(rng.gauss(7 - day / 40, 2)))
        for _ in range(n):
            cid = rng.choices(list(weights), weights=list(weights.values()))[0]
            c = by_id[cid]
            if cid == "c5" and day < 90:
                continue
            if cid == "c4" and day < 10:
                continue
            amount = round(rng.uniform(45, 320), 2)
            rate = c["comissao"] / 100
            when = d.replace(hour=rng.randint(12, 23), minute=rng.randint(0, 59))
            out.append({
                "id": new_id("r"), "coupon": c["cupom"], "campaign_id": cid, "campaign": c["nome"],
                "partner_id": c["parceiro_id"], "partner": parts[c["parceiro_id"]]["nome"],
                "influencer_id": c["influencer_id"], "influencer": infs[c["influencer_id"]]["nome"],
                "amount": amount, "discount": round(amount * c["desconto"] / 100, 2),
                "commission": round(amount * rate, 2), "rate": rate, "date": when.isoformat(),
                "staff": rng.choice(STAFF), "idempotency_key": new_id("seed"),
            })
    return out


async def ensure_indexes():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.redemptions.create_index("idempotency_key", unique=True)
    await db.redemptions.create_index([("partner_id", 1), ("date", -1)])
    await db.redemptions.create_index([("influencer_id", 1), ("date", -1)])
    await db.audit_log.create_index([("date", -1)])
    await db.notifications.create_index([("user_id", 1), ("lido", 1)])
    await db.messages.create_index([("conversation_id", 1), ("date", 1)])
    await db.login_attempts.create_index("identifier")
    for c in ("influencers", "partners", "campaigns", "ebooks", "leads", "conversations", "notifications", "messages", "audit_log", "payouts"):
        await db[c].create_index("id", unique=True)


async def seed():
    await ensure_indexes()
    flags = await db.settings.find_one({"id": "pilot"}, {"_id": 0}) or {}
    demo_enabled = os.environ.get("ENABLE_DEMO_SEED", "false").lower() == "true" and not flags.get("demo_disabled")
    users = USERS if demo_enabled else USERS[:1]
    for u in users:
        existing = await db.users.find_one({"email": u["email"]})
        doc = {k: v for k, v in u.items() if k != "password"}
        doc["status"] = "Ativo"
        if not existing:
            doc["password_hash"] = hash_password(u["password"])
            doc["created_at"] = now_iso()
            await db.users.insert_one(doc)
        elif not verify_password(u["password"], existing["password_hash"]):
            await db.users.update_one({"email": u["email"]}, {"$set": {"password_hash": hash_password(u["password"])}})
    if not demo_enabled:
        return
    if await db.influencers.count_documents({}) == 0:
        await db.influencers.insert_many([dict(i) for i in INFLUENCERS])
    if await db.partners.count_documents({}) == 0:
        await db.partners.insert_many([dict(p) for p in PARTNERS])
    if await db.campaigns.count_documents({}) == 0:
        await db.campaigns.insert_many([dict(c) for c in CAMPAIGNS])
    if await db.ebooks.count_documents({}) == 0:
        await db.ebooks.insert_many([dict(e) for e in EBOOKS])
    if await db.redemptions.count_documents({}) == 0:
        await db.redemptions.insert_many(gen_redemptions())
        first = datetime.now(timezone.utc).replace(day=1)
        def prev(n):
            d = first
            for _ in range(n):
                d = (d - timedelta(days=1)).replace(day=1)
            return d
        await db.payouts.insert_many([
            {"id": new_id("pay"), "influencer_id": "if1", "month": prev(1).strftime("%Y-%m"), "paid_at": first.replace(day=5).date().isoformat()},
            {"id": new_id("pay"), "influencer_id": "if1", "month": prev(2).strftime("%Y-%m"), "paid_at": prev(1).replace(day=5).date().isoformat()},
            {"id": new_id("pay"), "influencer_id": "if1", "month": prev(3).strftime("%Y-%m"), "paid_at": prev(2).replace(day=5).date().isoformat()},
            {"id": new_id("pay"), "influencer_id": "if2", "month": prev(1).strftime("%Y-%m"), "paid_at": first.replace(day=5).date().isoformat()},
        ])
    if await db.audit_log.count_documents({}) == 0:
        await db.audit_log.insert_one({"id": new_id("a"), "action": "SISTEMA", "detail": "Base de dados inicializada com dados de arranque", "date": now_iso(), "actor_id": "system", "actor": "Sistema", "ref": None})
