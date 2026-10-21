#!/usr/bin/env python3
"""RRClub: P5 v3 com merge semântico de conflitos locais e restauro condicionado.

NUNCA executa deploy, Stripe, pagamentos, Git pull/reset/checkout nem altera .env.
Transferência seletiva com merge de três vias, backup e rollback em falhas.
Não altera ficheiros se houver conflito com modificações locais.
"""
from __future__ import annotations
import ast
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen

REPO = "faellt34/NOVORRCLUB"
BASE = "65122258cfe9d95e03af9c390182a42a432c8748"
TARGET = "e92a45597d978a6a8518f8efdff2c565b410ea23"
MANIFEST = json.loads(r'''[["backend/server.py","d704f699be7b5578deb6215c4e699ce875bb3ea4","12138cd8cb889189f84e9eb83b9f8292ec83d212"],["backend/routes_payments.py","109252c3396cfbde8bf9acb49061e727727f09cb","befa224447004dac1be313b4fb7afbc2079e6225"],["backend/routes_pix.py","be961ec0c7b7c3661e2b4070026c3b85f4c25e15","dfcaec04768e51721f71a7445899c17525bcbaf7"],["frontend/src/components/QrScannerDialog.jsx","88502ef19c1c2005ee0f2d866972df2a2c202720","8ad87ef52782c74da6aa3b82e35345b2d2876af7"],["frontend/src/pages/PublicCoupon.jsx","25b657f0d0a7984d90664a128a91f723ab4453e9","eabcd93b3d2a37f1a0a2f3b2025239cc836e0db4"],["frontend/src/pages/PartnerDashboard.jsx","0c2920633c2ce13306b2f46437179e8cd29c316c","cdd5f3362d31fb504b0ec00b58bd3a64bad76df6"],["backend/p5_checkout.py",null,"a7a71629306d6dfb5ea2c59eb4ba2f4ac9958532"],["backend/p5_rules.py",null,"6ac3bff3db6a1c3fcc4a340462d81643f1c729da"],["backend/tests/test_p5_rules.py",null,"3037fcf439720814c0c952a7a94260d35e408fd9"],["frontend/src/components/P5FollowerPanel.jsx",null,"311abf3ec32b00ea2289124c85050b27cdc60a25"],["frontend/src/components/P5FollowerPanel.test.jsx",null,"16a7eba19ff505c470e2c670dbeb4da2845e22c7"]]''')
ROOT = Path("/app") if (Path("/app/backend/server.py").is_file()) else Path.cwd()
BACKUP = None


def abort(message):
    raise RuntimeError(message)


def gitblob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def fetch(commit, rel, expected):
    url = f"https://raw.githubusercontent.com/{REPO}/{commit}/{rel}"
    req = Request(url, headers={"User-Agent": "RRClub-P5-safe-overlay/1.0"})
    try:
        with urlopen(req, timeout=25) as response:
            data = response.read(400_000)
    except Exception as exc:
        abort(f"Não foi possível obter {rel}: {type(exc).__name__}")
    if gitblob(data) != expected:
        abort(f"Conteúdo GitHub divergente para {rel}; nada aplicado.")
    return data


def local_flag(name):
    if name in os.environ:
        return os.environ[name].strip().strip('"').strip("'").lower()
    env = ROOT / "backend/.env"
    if env.is_file():
        for raw in env.read_text(encoding="utf-8").splitlines():
            k, sep, v = raw.partition("=")
            if sep and k.strip() == name:
                return v.strip().strip('"').strip("'").lower()
    return "false"


def three_way(rel, ours, ancestor, theirs):
    with tempfile.TemporaryDirectory(prefix="rrclub_p5_merge_") as tmp:
        tmp = Path(tmp)
        for name, contents in (("ours", ours), ("ancestor", ancestor), ("theirs", theirs)):
            (tmp / name).write_bytes(contents)
        p = subprocess.run(
            ["git", "merge-file", "--diff3", "-p", str(tmp/"ours"),
             str(tmp/"ancestor"), str(tmp/"theirs")],
            capture_output=True, timeout=15,
        )
        if p.returncode != 0:
            return semantic_merge(rel, ours, ancestor, theirs)
        return p.stdout


def semantic_merge(rel, ours, ancestor, theirs):
    """Surgical P5 insertions: never remove bespoke Emergent code."""
    content = ours.decode("utf-8")
    if rel == "backend/server.py":
        if "import p5_checkout" not in content:
            for anchor in ("import routes_finance\n", "import routes_pix\n"):
                if content.count(anchor) == 1:
                    content = content.replace(anchor, anchor + "import p5_checkout\n", 1)
                    break
            else:
                abort("server.py: P5 import placement unknown, no files changed.")
        route_match = re.search(
            r"(?m)^for\s+r\s+in\s+\((.*?)\):\s*\n\s*api_router\.include_router\(r\)",
            content, re.DOTALL,
        )
        if not route_match:
            abort("server.py: custom router registration unknown, no files changed.")
        old = route_match.group(0)
        if "p5_checkout.router" not in route_match.group(1):
            if "routes_finance.router," not in old:
                abort("server.py: financial router anchor missing, no files changed.")
            new = old.replace(
                "routes_finance.router,", "routes_finance.router, p5_checkout.router,", 1
            )
            content = content.replace(old, new, 1)
        if "await p5_checkout.ensure_p5_indexes()" not in content:
            anchor = "    await seed()\n"
            if content.count(anchor) != 1:
                abort("server.py: startup anchor unknown, no files changed.")
            content = content.replace(
                anchor,
                anchor + "    if p5_checkout.enabled():\n"
                         "        await p5_checkout.ensure_p5_indexes()\n", 1
            )
        ast.parse(content, filename=rel)
        print("  ✓ server.py: routers locais preservados", flush=True)
        return content.encode("utf-8")

    if rel == "backend/routes_payments.py":
        start = content.find("async def public_pay")
        if start < 0:
            abort("routes_payments.py: public_pay not found, no files changed.")
        end = content.find("\n@router.", start + 1)
        block = content[start:end if end >= 0 else len(content)]
        if 'currency_enabled("eur")' not in block:
            anchor = '    partner = await db.partners.find_one({"id": c.get("parceiro_id")}, NO_ID) or {}\n'
            if block.count(anchor) != 1:
                abort("routes_payments.py: checkout changed, no files changed.")
            guard = (
                '    from p5_checkout import currency_enabled\n'
                '    currency = str(c.get("currency") or partner.get("currency") or "eur").lower()\n'
                '    if currency != "eur":\n'
                '        raise HTTPException(status_code=409, detail="Esta campanha não usa o checkout EUR. Pague pelo fluxo local do parceiro.")\n'
                '    if currency_enabled("eur"):\n'
                '        raise HTTPException(status_code=409, detail="P5 ativo: o parceiro deve ler o QR individual e confirmar o valor antes do pagamento.")\n'
            )
            content = content[:start] + block.replace(anchor, anchor + guard, 1) + content[start + len(block):]
        ast.parse(content, filename=rel)
        print("  ✓ routes_payments.py: checkout local preservado", flush=True)
        return content.encode("utf-8")

    if rel == "backend/routes_pix.py":
        start = content.find("async def partner_checkout")
        if start < 0:
            abort("routes_pix.py: partner checkout missing, no files changed.")
        end = content.find("\nasync def ", start + 1)
        block = content[start:end if end >= 0 else len(content)]
        if "currency_enabled('brl')" not in block:
            anchor = "    existing=await db.payment_transactions.find_one({'id':'pix-'+str(body.request_id),'kind':'pix_coupon'},NO_ID)\n"
            guard = (
                "    if not existing:\n"
                "        from p5_checkout import currency_enabled\n"
                "        if currency_enabled('brl'):\n"
                "            raise HTTPException(409, 'P5 ativo: leia o QR individual do cliente antes de iniciar uma cobrança Pix.')\n"
            )
            if block.count(anchor) != 1:
                abort("routes_pix.py: partner checkout changed, no files changed.")
            content = content[:start] + block.replace(anchor, anchor + guard, 1) + content[start + len(block):]
        if "PIX_ALLOW_NEW_CONNECT_ACCOUNTS" not in content:
            anchor = "        if not account:\n            created=await provider('accounts.create',"
            guard = (
                "        if not account:\n"
                "            from p5_checkout import currency_enabled\n"
                "            if currency_enabled('brl') and os.environ.get('PIX_ALLOW_NEW_CONNECT_ACCOUNTS', 'false').lower() != 'true':\n"
                "                raise HTTPException(409, 'P5 Brasil: concilie primeiro as contas Connect já existentes antes de criar outra.')\n"
                "            created=await provider('accounts.create',"
            )
            if content.count(anchor) != 1:
                abort("routes_pix.py: Connect setup changed, no files changed.")
            content = content.replace(anchor, guard, 1)
        ast.parse(content, filename=rel)
        print("  ✓ routes_pix.py: conta Pix brasileira preservada", flush=True)
        return content.encode("utf-8")

    if rel == "frontend/src/components/QrScannerDialog.jsx":
        anchor = "export const QrScannerDialog = ({ open, onOpenChange, onDetected }) => {"
        if "preserveRaw" not in content:
            if content.count(anchor) != 1 or content.count("onDetected(extractCoupon(text));") != 1:
                abort("QrScannerDialog.jsx: scanner local changed, no files changed.")
            content = content.replace(
                anchor,
                "export const QrScannerDialog = ({ open, onOpenChange, onDetected, preserveRaw = false }) => {", 1,
            ).replace(
                "onDetected(extractCoupon(text));",
                "onDetected(preserveRaw ? String(text) : extractCoupon(text));", 1,
            )
        print("  ✓ QrScannerDialog.jsx: QR P5 completo", flush=True)
        return content.encode("utf-8")

    abort(f"Conflito em {rel}; exige inspeção manual segura. Nenhum ficheiro alterado.")


def syntax_checks(staged):
    # Python parse uses no runtime imports, database or remote APIs.
    for rel, payload in staged.items():
        if rel.endswith(".py"):
            try:
                ast.parse(payload.decode("utf-8"), filename=rel)
            except SyntaxError as exc:
                abort(f"Erro de sintaxe {rel}, linha {exc.lineno}: {exc.msg}")
    # In particular, catch a shell command accidentally pasted into routes_auth.py.
    auth = ROOT / "backend/routes_auth.py"
    if auth.is_file():
        try:
            content = staged.get("backend/routes_auth.py") or auth.read_bytes()
            ast.parse(content.decode("utf-8"), filename=str(auth))
        except SyntaxError as exc:
            abort(f"routes_auth.py continua com erro na linha {exc.lineno}. Nada aplicado.")

    jsx = [(rel, payload) for rel, payload in staged.items() if rel.endswith(".jsx")]
    if jsx:
        with tempfile.TemporaryDirectory(prefix="rrclub_p5_jsx_") as tmp:
            tmp = Path(tmp)
            paths = []
            for i, (_, payload) in enumerate(jsx):
                p = tmp / f"file{i}.jsx"
                p.write_bytes(payload)
                paths.append(str(p))
            js = ("const fs=require('fs');const parser=require('@babel/parser');"
                  "for(const p of process.argv.slice(1)){"
                  "parser.parse(fs.readFileSync(p,'utf8'),{sourceType:'module',plugins:['jsx']});"
                  "}console.log('JSX P5: sintaxe aprovada');")
            try:
                p = subprocess.run(
                    ["node", "-e", js, *paths], cwd=str(ROOT/"frontend"),
                    capture_output=True, text=True, timeout=40,
                )
            except (OSError, subprocess.TimeoutExpired):
                abort("O teste JSX não pôde ser executado. Nada aplicado.")
            if p.returncode != 0:
                abort("Validação JSX falhou: " + (p.stderr or "")[:350])
            print("  ✓ JSX validado")


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".p5-staging")
    try:
        tmp.write_bytes(data)
        if path.exists():
            tmp.chmod(path.stat().st_mode & 0o777)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def stage_auth_repair(staged):
    """Repair only a recognizable terminal command pasted over line 1."""
    auth = ROOT / "backend/routes_auth.py"
    lines = auth.read_text(encoding="utf-8").splitlines(keepends=True)
    if not lines:
        abort("routes_auth.py is empty. No changes applied.")
    first = lines[0].strip()
    known = (
        "raw.githubusercontent.com/faellt34/NOVORRCLUB/" in first
        and any(marker in first for marker in (
            "rrclub_finance_route_smoke.py", "rrclub_p5_overlay.py",
            "rrclub_emergent_p5_safe_overlay.py",
        ))
        and ("curl " in first or "python3 " in first)
    )
    if known:
        rest = "".join(lines[1:])
        replacement = rest if re.search(r"(?m)^import re\s*$", rest) else "import re\n" + rest
        try:
            ast.parse(replacement, filename="backend/routes_auth.py")
        except SyntaxError:
            abort("routes_auth.py has other errors. No changes applied.")
        staged["backend/routes_auth.py"] = replacement.encode("utf-8")
        print("  ✓ routes_auth.py: colagem acidental identificada; restauro preparado", flush=True)


def main():
    global BACKUP
    print("=== RRCLUB: P5 PORTUGAL + BRASIL / INTEGRAÇÃO LOCAL SEGURA ===", flush=True)
    if not all((ROOT / p).is_file() for p in (
        "backend/server.py", "backend/routes_pix.py",
        "frontend/package.json", "backend/routes_auth.py"
    )):
        abort("Pasta RRClub não identificada. Nenhum ficheiro alterado.")
    if local_flag("P5_ENABLED") == "true":
        abort("P5_ENABLED já está ativo. Desative-o manualmente antes da integração.")
    for rel, _, _ in MANIFEST:
        if (ROOT / rel).is_symlink():
            abort(f"Ficheiro simbólico inesperado: {rel}. Nada aplicado.")

    print("1/4 Preparar diferenças e verificar versões GitHub...", flush=True)
    staged = {}
    base_data = {}
    for rel, ancestor_hash, new_hash in MANIFEST:
        path = ROOT / rel
        after = fetch(TARGET, rel, new_hash)
        if path.is_file() and path.read_bytes() == after:
            continue  # Idempotente; não reescrever ficheiros já corretos.
        if ancestor_hash is None:
            if path.exists():
                abort(f"Já existe {rel} com conteúdo diferente. Nada aplicado.")
            staged[rel] = after
            continue
        if not path.is_file():
            abort(f"Ficheiro local ausente: {rel}. Nada aplicado.")
        before = fetch(BASE, rel, ancestor_hash)
        existing = path.read_bytes()
        merged = (after if existing == before else three_way(rel, existing, before, after))
        if merged != existing:
            staged[rel] = merged
    stage_auth_repair(staged)
    if not staged:
        print("P5 já sincronizado: nenhum ficheiro precisava de atualização.")
        return

    print(f"2/4 Validar sintaxe e políticas, {len(staged)} ficheiros...", flush=True)
    syntax_checks(staged)
    pix_payload = staged.get("backend/routes_pix.py") or (ROOT / "backend/routes_pix.py").read_bytes()
    if b"PIX_STRIPE_SECRET_KEY" not in pix_payload or b"'/stripe/pix/webhook'" not in pix_payload:
        abort("Proteção Pix Brasil alterada. Nada aplicado.")
    pt_payload = staged.get("backend/p5_checkout.py") or (ROOT / "backend/p5_checkout.py").read_bytes()
    if b'startswith("sk_test_")' not in pt_payload or b'P5_ENABLED' not in pt_payload:
        abort("Bloqueio de produção P5 Portugal ausente. Nada aplicado.")

    BACKUP = Path(tempfile.mkdtemp(prefix="rrclub_p5_backup_", dir="/tmp"))
    originals = {}
    for rel in staged:
        local = ROOT / rel
        originals[rel] = local.read_bytes() if local.is_file() else None
        if originals[rel] is not None:
            dst = BACKUP / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local, dst)
    print("  Backup local:", BACKUP, flush=True)
    print("3/4 Aplicar diferenças e executar testes rápidos...", flush=True)
    try:
        for rel, payload in staged.items():
            atomic_write(ROOT/rel, payload)
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT/"backend")
        test = subprocess.run(
            [sys.executable, "-m", "unittest", "discover",
             "-s", str(ROOT/"backend/tests"), "-p", "test_p5_rules.py", "-v"],
            cwd=str(ROOT), env=env, timeout=35, capture_output=True, text=True,
        )
        if test.returncode != 0:
            abort("Teste das regras P5 falhou: " + (test.stderr or test.stdout)[-750:])
        print("  ✓ Regras P5 aprovadas", flush=True)
        print("4/4 CONCLUÍDO: P5 integrado sem ativar produção.", flush=True)
        print(f"  Ficheiros atualizados: {len(staged)}")
        print("  Pix Brasil e MB WAY Portugal preservados.")
        print("  Nenhum deploy, nenhuma cobrança, nenhuma transferência.")
        print("  Próximo passo: validação da Prévia antes de publicar.", flush=True)
    except Exception:
        print("Falha durante integração; a restaurar todas as alterações...", flush=True)
        for rel, original in originals.items():
            p = ROOT / rel
            if original is None:
                if p.exists(): p.unlink()
            else:
                atomic_write(p, original)
        print("RESTAURO CONCLUÍDO: ficheiros anteriores mantidos.", flush=True)
        raise


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("NÃO APLICADO / ERRO:", str(exc), flush=True)
        sys.exit(1)
