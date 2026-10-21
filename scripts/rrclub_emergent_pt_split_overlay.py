#!/usr/bin/env python3
"""RRClub Portugal: apply only PT split patch, preserving Emergent local customizations.
Read-only Stripe during script: ZERO provider API calls. ZERO financial transfers.
No deployment, no secrets changed. Three-way merge with safe semantic fallback.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen

REPO = "faellt34/NOVORRCLUB"
BASE = "e92a45597d978a6a8518f8efdff2c565b410ea23"
TARGET = "8282d202e5cf89103959d746a9c4a65ac4e32249"
MANIFEST = json.loads(r'''[["backend/server.py","12138cd8cb889189f84e9eb83b9f8292ec83d212","263093c58431017fc90c163cc378086f0a873366"],["backend/p5_checkout.py","a7a71629306d6dfb5ea2c59eb4ba2f4ac9958532","f9220f79c502cb8f0399f2c7dbb7314d2b110ec8"],["backend/p5_rules.py","6ac3bff3db6a1c3fcc4a340462d81643f1c729da","123899834f279d90ea1fa20cafe063b6ffb106e3"],["backend/routes_payments.py","befa224447004dac1be313b4fb7afbc2079e6225","395e0e21a0b935eb986547b5c8bdc894cdeac30c"],["backend/tests/test_p5_rules.py","3037fcf439720814c0c952a7a94260d35e408fd9","7ab15f14e9d03c4e2d25d2fef2fcfb6878caac63"],["frontend/src/pages/AdminPayouts.jsx","2846363d5d8869deb247b044b54003e09f0afb87","8c163651ecf831a616eb67229e4fa80a9a4c3d42"],["backend/pt_split.py",null,"dc88657f8fa96206f6ea1e540de3a68812685f6a"],["backend/tests/test_pt_split.py",null,"d018137a5736a432f8c464902eade4b616327108"],["frontend/src/components/PortugalSplitPanel.jsx",null,"79e8d3adbb57cdb33cafd1ffcb197a734399cf90"]]''')
ROOT = Path("/app") if (Path("/app/backend/server.py")).is_file() else Path.cwd()


def fail(message):
    raise RuntimeError(message)


def gitblob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def download(ref, path, expected):
    url = "https://raw.githubusercontent.com/" + REPO + "/" + ref + "/" + path
    with urlopen(Request(url, headers={"User-Agent": "RRClub-PT-SPLIT-OVERLAY"}), timeout=30) as f:
        payload = f.read(500000)
    if gitblob(payload) != expected:
        fail("Falha de integridade do ficheiro " + path + "; nada aplicado.")
    return payload


def flag_in_env(name):
    if os.getenv(name, "").lower() == "true":
        return True
    env = ROOT / "backend/.env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == name and value.strip().strip('"').strip("'").lower() == "true":
                return True
    return False


def semantic_merge(path, ours):
    s = ours.decode("utf-8")
    if path == "backend/server.py":
        if "import pt_split" not in s:
            for anchor in ("import p5_checkout\n", "import routes_finance\n"):
                if s.count(anchor) == 1:
                    s = s.replace(anchor, anchor + "import pt_split\n", 1)
                    break
            else:
                fail("server.py não tem ponto de importação conhecido; nada aplicado.")
        if "pt_split.router" not in s:
            anchor = "p5_checkout.router,"
            if s.count(anchor) != 1:
                fail("server.py tem routers inesperados; nada aplicado.")
            s = s.replace(anchor, "p5_checkout.router, pt_split.router,", 1)
        ast.parse(s, filename=path)
        return s.encode("utf-8")

    if path == "backend/routes_payments.py":
        if "await settle_webhook_safely" not in s:
            anchor = '            await fulfil(obj["id"], {"stripe_subscription_id": obj.get("subscription"), "stripe_payment_intent_id": obj.get("payment_intent"), "customer_email": ((obj.get("customer_details") or {}).get("email")) or obj.get("customer_email")})'
            if s.count(anchor) != 1:
                fail("routes_payments.py: webhook diferente; nada aplicado.")
            s = s.replace(
                anchor,
                anchor + '\n            from pt_split import settle_webhook_safely\n'
                         '            await settle_webhook_safely(obj["id"])',
                1,
            )
        ast.parse(s, filename=path)
        return s.encode("utf-8")

    if path == "frontend/src/pages/AdminPayouts.jsx":
        if "PortugalSplitPanel" not in s:
            a = 'import FinanceReconciliationPanel from "../components/FinanceReconciliationPanel";'
            b = '{reportCurrency() === "eur" && <FinanceReconciliationPanel />}'
            if s.count(a) != 1 or s.count(b) != 1:
                fail("AdminPayouts.jsx personalizado; nenhuma alteração aplicada.")
            s = s.replace(a, a + '\nimport PortugalSplitPanel from "../components/PortugalSplitPanel";', 1)
            s = s.replace(b, '{reportCurrency() === "eur" && <PortugalSplitPanel />}\n      ' + b, 1)
        return s.encode("utf-8")

    fail("Conflito local em " + path + "; nenhuma alteração aplicada.")


def three_way(path, ours, ancestor, updated):
    with tempfile.TemporaryDirectory(prefix="ptsplit3way_") as d:
        d = Path(d)
        for name, payload in (("local", ours), ("base", ancestor), ("new", updated)):
            (d / name).write_bytes(payload)
        proc = subprocess.run(
            ["git", "merge-file", "-p", "--diff3", str(d/"local"), str(d/"base"), str(d/"new")],
            capture_output=True, timeout=15,
        )
        if proc.returncode == 0:
            return proc.stdout
    return semantic_merge(path, ours)


def write_atomically(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".ptsplit-staging")
    try:
        tmp.write_bytes(payload)
        if path.exists():
            tmp.chmod(path.stat().st_mode & 0o777)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def main():
    print("=== RRCLUB PT SPLIT 5/80/5/10: CORREÇÃO SEGURA ===", flush=True)
    if not all((ROOT/path).is_file() for path in (
        "backend/server.py", "backend/routes_auth.py",
        "backend/p5_checkout.py", "backend/routes_pix.py",
        "frontend/src/pages/AdminPayouts.jsx",
    )):
        fail("Workspace RRClub P5 não reconhecido; nada aplicado.")
    # Never introduce or modify an automatic financial operation while active.
    if flag_in_env("PT_SPLIT_AUTO_TRANSFER"):
        fail("Transferências PT já ativas: necessário plano de manutenção. Nada aplicado.")
    if flag_in_env("PT_SPLIT_LIVE_ENABLED"):
        fail("P5 PT live já ativo: necessário plano de manutenção. Nada aplicado.")

    print("1/4 Obter 9 ficheiros autorizados do GitHub...", flush=True)
    staged = {}
    for rel, ancestor_hash, target_hash in MANIFEST:
        dest = ROOT / rel
        if dest.is_symlink():
            fail("Ficheiro simbólico inesperado " + rel)
        wanted = download(TARGET, rel, target_hash)
        if dest.is_file() and dest.read_bytes() == wanted:
            continue
        if ancestor_hash is None:
            if dest.exists():
                fail("Ficheiro existente diferente: " + rel)
            staged[rel] = wanted
            continue
        if not dest.is_file():
            fail("Ficheiro original ausente: " + rel)
        ancestor = download(BASE, rel, ancestor_hash)
        local = dest.read_bytes()
        merged = wanted if local == ancestor else three_way(rel, local, ancestor, wanted)
        if local != merged:
            staged[rel] = merged
    if not staged:
        print("Nada a atualizar: split PT já instalado.")
        return

    print("2/4 Validar sintaxe e políticas antes de aplicar...", flush=True)
    for rel, payload in staged.items():
        if rel.endswith(".py"):
            ast.parse(payload.decode("utf-8"), filename=rel)
    for rel in ("backend/routes_auth.py", "backend/routes_pix.py"):
        ast.parse((ROOT/rel).read_text(encoding="utf-8"), filename=rel)
    module = staged.get("backend/pt_split.py") or (ROOT/"backend/pt_split.py").read_bytes()
    route = staged.get("backend/routes_payments.py") or (ROOT/"backend/routes_payments.py").read_bytes()
    p5 = staged.get("backend/p5_checkout.py") or (ROOT/"backend/p5_checkout.py").read_bytes()
    if not all(term in module for term in (
        b"PT_SPLIT_AUTO_TRANSFER", b"source_transaction=charge_id",
        b"stripe.Transfer.create", b'"kind": "coupon_pay"', b'"currency": "eur"',
    )):
        fail("Faltam proteções de split Portugal.")
    if b"await settle_webhook_safely" not in route or b'"split_version": VERSION' not in p5:
        fail("Webhook ou checkout P5 Portugal incompleto.")
    jsx = [(rel, data) for rel, data in staged.items() if rel.endswith(".jsx")]
    if jsx:
        with tempfile.TemporaryDirectory(prefix="pt_split_jsx_") as tmp:
            paths = []
            for n, (rel, data) in enumerate(jsx):
                file = Path(tmp) / ("file" + str(n) + ".jsx")
                file.write_bytes(data)
                paths.append(str(file))
            js = ("const fs=require('fs');const parser=require('@babel/parser');"
                  "for(const f of process.argv.slice(1)){parser.parse(fs.readFileSync(f,'utf8'),"
                  "{sourceType:'module',plugins:['jsx']});}console.log('JSX OK')")
            test = subprocess.run(["node", "-e", js, *paths], cwd=str(ROOT/"frontend"),
                                  capture_output=True, text=True, timeout=40)
            if test.returncode != 0:
                fail("O JSX da interface PT não passou na análise: " + test.stderr[-400:])

    originals = {}
    backup = Path(tempfile.mkdtemp(prefix="rrclub_pt_split_backup_", dir="/tmp"))
    for rel in staged:
        p = ROOT / rel
        originals[rel] = p.read_bytes() if p.is_file() else None
        if originals[rel] is not None:
            out = backup / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, out)
    print("3/4 Backup:", backup, flush=True)
    try:
        for rel, payload in staged.items():
            write_atomically(ROOT / rel, payload)
        e = dict(os.environ)
        e["PYTHONPATH"] = str(ROOT/"backend")
        test = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s",
             str(ROOT/"backend/tests"), "-p", "test_p5_rules.py", "-v"],
            cwd=str(ROOT), env=e, capture_output=True, text=True, timeout=30,
        )
        if test.returncode != 0:
            fail("Teste P5 falhou: " + (test.stderr or test.stdout)[-600:])
        print("4/4 CONCLUÍDO: " + str(len(staged)) + " ficheiros integrados.", flush=True)
        print("Portugal: 5% desconto; 80% parceiro; 5% influenciador; 10% RRClub.")
        print("Novo painel administrativo de elegibilidade Stripe Connect instalado.")
        print("P5 live e transferências PT não foram ativados.", flush=True)
        print("Pix Brasil, MB WAY e autenticação preservados; nenhum deploy.", flush=True)
    except Exception:
        for rel, previous in originals.items():
            dest = ROOT / rel
            if previous is None:
                if dest.exists(): dest.unlink()
            else:
                write_atomically(dest, previous)
        print("RESTAURO: ficheiros anteriores recuperados.", flush=True)
        raise


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("NÃO APLICADO:", type(exc).__name__, str(exc)[:400], flush=True)
        sys.exit(1)
