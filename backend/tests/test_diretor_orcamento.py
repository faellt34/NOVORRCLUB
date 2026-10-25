"""Garantias offline de controlo de consumo do Diretor IA."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
import unittest

from diretor_orcamento import (AUDITORIA_LOTE_MAX, MAX_PASSOS_CONVERSA,
                               LimiteAtingido, reservar_quota_diaria, selecionar_lote_auditoria)


class DiretorOrcamentoTests(unittest.TestCase):
    def test_auditoria_em_lotes_estaveis_sem_duplicados(self):
        files = ["routes_z.py", "core.py", "routes_diretor.py", "routes_b.py", "routes_z.py"]
        a = selecionar_lote_auditoria(files, 0, 3)
        b = selecionar_lote_auditoria(files, a["proximo_inicio"], 3)
        self.assertEqual(a["ficheiros"], ["core.py", "routes_diretor.py", "routes_b.py"])
        self.assertEqual(b["ficheiros"], ["routes_z.py"])
        self.assertIsNone(b["proximo_inicio"])
        self.assertEqual(a["total"], 4)
        self.assertEqual(len(set(a["ficheiros"] + b["ficheiros"])), 4)

    def test_limite_de_lote_e_inicio_invalidos(self):
        self.assertEqual(AUDITORIA_LOTE_MAX, 3)
        for args in ((-1, 2), (0, 0), (0, 4)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                selecionar_lote_auditoria(["core.py"], *args)
        self.assertEqual(selecionar_lote_auditoria([], 0, 3)["ficheiros"], [])

    def test_orquestrador_conta_cada_interacao_llm(self):
        src = (Path(__file__).resolve().parents[1] / "routes_diretor.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        funcs = {n.name: n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)}
        converse = funcs["conversar"]
        loops = [n for n in ast.walk(converse) if isinstance(n, ast.For)
                 and isinstance(n.iter, ast.Call) and isinstance(n.iter.func, ast.Name)
                 and n.iter.func.id == "range"]
        self.assertTrue(any(isinstance(n, ast.Await) and isinstance(n.value, ast.Call)
                            and isinstance(n.value.func, ast.Name) and n.value.func.id == "_llm_guard"
                            for loop in loops for node in loop.body for n in ast.walk(node)))
        self.assertEqual(MAX_PASSOS_CONVERSA, 5)
        guard = funcs["_llm_guard"]
        method_calls = {n.func.attr for n in ast.walk(guard) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertIn("insert_many", method_calls)
        self.assertIn("reservar_quota_diaria", {n.func.id for n in ast.walk(guard)
                                                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)})


class _QuotaFalsa:
    def __init__(self):
        self.docs = {}

    async def update_one(self, filtro, operacao, upsert=False):
        key = filtro["_id"]
        if upsert and key not in self.docs:
            self.docs[key] = {"_id": key, **operacao["$setOnInsert"]}
        doc = self.docs.get(key)
        if doc and "$inc" in operacao and doc["usado"] <= filtro["usado"]["$lte"]:
            doc["usado"] += operacao["$inc"]["usado"]
            return SimpleNamespace(matched_count=1)
        return SimpleNamespace(matched_count=1 if doc and upsert else 0)

    async def find_one(self, filtro):
        return self.docs.get(filtro["_id"])


class _UsoFalso:
    def __init__(self, historico=0):
        self.historico = historico

    async def count_documents(self, filtro):
        return self.historico


class ReservaQuotaTests(unittest.IsolatedAsyncioTestCase):
    async def test_reservas_paralelas_nao_ultrapassam_limite(self):
        quota, uso = _QuotaFalsa(), _UsoFalso()
        resultados = await asyncio.gather(
            *(reservar_quota_diaria(quota, uso, "2026-10-25", 3, 1) for _ in range(6)),
            return_exceptions=True,
        )
        self.assertEqual(sum(r is None for r in resultados), 3)
        self.assertEqual(sum(isinstance(r, LimiteAtingido) for r in resultados), 3)
        self.assertEqual(quota.docs["diretor:2026-10-25"]["usado"], 3)

    async def test_contador_anterior_e_reserva_por_lote(self):
        quota, uso = _QuotaFalsa(), _UsoFalso(historico=4)
        await reservar_quota_diaria(quota, uso, "2026-10-25", 7, 3)
        self.assertEqual(quota.docs["diretor:2026-10-25"]["usado"], 7)
        with self.assertRaises(LimiteAtingido):
            await reservar_quota_diaria(quota, uso, "2026-10-25", 7, 1)


if __name__ == "__main__":
    unittest.main()
