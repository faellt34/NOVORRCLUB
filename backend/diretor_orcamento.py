"""Limites explícitos de chamadas IA e lotes de auditoria do Diretor.

Sem dependências externas: os cálculos podem ser testados offline.
"""

LIMITE_DIARIO_DEFAULT = 60
AUDITORIA_LOTE_MAX = 3
MAX_PASSOS_CONVERSA = 5


class LimiteAtingido(Exception):
    def __init__(self, usado, limite):
        self.usado = usado
        self.limite = limite
        super().__init__(f"Limite diário de IA atingido ({usado}/{limite})")


async def reservar_quota_diaria(quota_collection, usage_collection, dia, limite, n):
    """Reserva N chamadas com um único incremento condicional atómico em MongoDB.

    A inicialização considera registos do contador antigo antes do primeiro uso.
    Uma reserva não é reembolsada após erro: nunca subestima o limite.
    """
    if not isinstance(n, int) or n < 1 or n > limite:
        raise LimiteAtingido(0, limite)
    quota_id = f"diretor:{dia}"
    historico = await usage_collection.count_documents({"dia": dia})
    await quota_collection.update_one(
        {"_id": quota_id}, {"$setOnInsert": {"dia": dia, "usado": historico}}, upsert=True)
    reserva = await quota_collection.update_one(
        {"_id": quota_id, "usado": {"$lte": limite - n}}, {"$inc": {"usado": n}})
    if not reserva.matched_count:
        atual = await quota_collection.find_one({"_id": quota_id}) or {}
        raise LimiteAtingido(int(atual.get("usado", historico)), limite)


def selecionar_lote_auditoria(ficheiros, inicio=0, limite=AUDITORIA_LOTE_MAX):
    """Devolve uma fatia estável, sem repetição nem auditoria surpresa de toda a base."""
    if not isinstance(inicio, int) or inicio < 0:
        raise ValueError("O início deve ser um inteiro não negativo")
    if not isinstance(limite, int) or not 1 <= limite <= AUDITORIA_LOTE_MAX:
        raise ValueError("O lote deve conter entre 1 e 3 ficheiros")
    priority = {"core.py": 0, "routes_diretor.py": 1}
    ordered = sorted(set(ficheiros), key=lambda f: (priority.get(f, 2), f))
    if inicio >= len(ordered):
        return {"ficheiros": [], "total": len(ordered), "inicio": inicio, "proximo_inicio": None}
    fim = min(inicio + limite, len(ordered))
    return {"ficheiros": ordered[inicio:fim], "total": len(ordered), "inicio": inicio,
            "proximo_inicio": fim if fim < len(ordered) else None}
