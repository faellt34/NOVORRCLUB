#!/usr/bin/env python3
"""RRClub: ativa P5 QR Portugal/Brasil sem apagar personalizações do Emergent.

Faz backup, merge seletivo, validação sintática, testes financeiros locais e
marca P5_ENABLED/EUR/BRL=true em backend/.env. NÃO faz deploy, não acede à
Stripe, não cria pagamentos/transfers/Connect, não faz Git checkout/reset.
PT_SPLIT_AUTO_TRANSFER não é ativado.
"""
from __future__ import annotations
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

ROOT = Path("/app") if (Path("/app/backend/server.py").is_file()) else Path.cwd()
BASE = "e92a45597d978a6a8518f8efdff2c565b410ea23"
TARGET = "b6a73ed1223548b982b30f98cd120dba806571e7"
REPO = "faellt34/NOVORRCLUB"
MANIFEST = json.loads(r'''[["backend/p5_checkout.py","a7a71629306d6dfb5ea2c59eb4ba2f4ac9958532","d967a54165bb5476df6da01e37e585a662d4214d"],["backend/p5_rules.py","6ac3bff3db6a1c3fcc4a340462d81643f1c729da","123899834f279d90ea1fa20cafe063b6ffb106e3"],["backend/tests/test_p5_rules.py","3037fcf439720814c0c952a7a94260d35e408fd9","7ab15f14e9d03c4e2d25d2fef2fcfb6878caac63"],["frontend/src/components/P5FollowerPanel.jsx","311abf3ec32b00ea2289124c85050b27cdc60a25","69351af99ad6ba8ba7d4574af3220b51e9b12abf"],["frontend/src/components/P5FollowerPanel.test.jsx","16a7eba19ff505c470e2c670dbeb4da2845e22c7","33c2549e8f2f68af6c7d835fb416efe20eda210f"],["frontend/src/pages/PublicCoupon.jsx","eabcd93b3d2a37f1a0a2f3b2025239cc836e0db4","154a1f0bf4a9c42f8528ebf267fb4429a4563261"],["frontend/src/pages/PartnerDashboard.jsx","cdd5f3362d31fb504b0ec00b58bd3a64bad76df6","8d015e3ff19c0c62896d017426f4d082dccdb43c"],["backend/pt_split.py",null,"dc88657f8fa96206f6ea1e540de3a68812685f6a"],["backend/tests/test_p5_activation_policy.py",null,"40a8f25ea6294b77832579602788d678dd611647"],["backend/tests/test_p5_legacy_campaigns.py",null,"5a08a9c1d71e917c44d2fd651aa993aa0b74dde0"]]''')


def stop(message):
    raise RuntimeError(message)


def sha_git(payload):
    return hashlib.sha1(
        b"blob " + str(len(payload)).encode() + b"\0" + payload
    ).hexdigest()


def remote(commit, relative, expected):
    url = f"https://raw.githubusercontent.com/{REPO}/{commit}/{relative}"
    with urlopen(Request(url, headers={"User-Agent": "rrclub-safe-p5-release"}), timeout=25) as response:
        data = response.read(400_000)
    if sha_git(data) != expected:
        stop("Fonte GitHub inesperada: " + relative)
    return data


def merge(relative, ours, ancestor, theirs):
    with tempfile.TemporaryDirectory(prefix="p5_merge_") as tmp:
        d = Path(tmp)
        for name, data in (("ours", ours), ("base", ancestor), ("theirs", theirs)):
            (d / name).write_bytes(data)
        p = subprocess.run(["git", "merge-file", "--diff3", "-p",
                            str(d/"ours"), str(d/"base"), str(d/"theirs")],
                           capture_output=True, timeout=15)
        if p.returncode == 0:
            return p.stdout
        return ui_semantic_merge(relative, ours)


def ui_semantic_merge(relative, ours):
    """Narrow fallback for two JSX views; other conflicts MUST stop."""
    s = ours.decode("utf-8")
    if relative == "frontend/src/pages/PartnerDashboard.jsx":
        anchor = '  const p5Mode = Boolean(p5Currencies[String(preview?.currency || data?.partner?.currency || "eur").toLowerCase()]);'
        if "p5EligibleCampaign" not in s and s.count(anchor) == 1:
            s = s.replace(anchor,
                '  const p5EligibleCampaign = preview && Number(preview.desconto) === 5 && Number(preview.comissao) === 5 && Boolean(preview.influencer_id);\n'
                '  const p5Mode = Boolean(p5EligibleCampaign && p5Currencies[String(preview.currency || data?.partner?.currency || "eur").toLowerCase()]);', 1)
        if "p5EligibleCampaign" in s:
            return s.encode("utf-8")
    if relative == "frontend/src/pages/PublicCoupon.jsx":
        a = '  const [p5Enabled, setP5Enabled] = useState(false);'
        if "p5CheckoutEnabled" not in s and s.count(a) == 1:
            s = s.replace(a, a+'\n  const [p5CheckoutEnabled, setP5CheckoutEnabled] = useState(false);', 1)
        start = s.find('    setP5Enabled(false);\n    if (!c || c.status !== "Ativa")')
        finish = s.find('    return () => { cancelled = true; };', start) if start >= 0 else -1
        if start >= 0 and finish >= 0:
            s = s[:start] + (
                '    setP5Enabled(false);\n'
                '    setP5CheckoutEnabled(false);\n'
                '    if (!c || c.status !== "Ativa") return () => { cancelled = true; };\n'
                '    api.get("/public/p5/config").then(({ data }) => {\n'
                '      if (cancelled) return;\n'
                '      const selected = (c.currency || "eur").toLowerCase();\n'
                '      setP5Enabled(Boolean(c.p5_eligible && data?.currencies?.[selected]));\n'
                '      setP5CheckoutEnabled(Boolean(data?.checkout_currencies?.[selected]));\n'
                '    }).catch(() => {\n'
                '      if (!cancelled) { setP5Enabled(false); setP5CheckoutEnabled(false); }\n'
                '    });\n'
            ) + s[finish:]
        s = s.replace(
            '<P5FollowerPanel code={code} currency={currency} />',
            '<P5FollowerPanel code={code} currency={currency} checkoutEnabled={p5CheckoutEnabled} />'
        )
        if "c.p5_eligible" in s and "checkoutEnabled={p5CheckoutEnabled}" in s:
            return s.encode("utf-8")
    stop("Conflito de modificações locais em " + relative + "; nada aplicado.")


def patch_server(ours):
    s = ours.decode("utf-8")
    if "import p5_checkout" not in s or "p5_checkout.router" not in s:
        stop("O backend local ainda não tem P5 V3 integrado. Parar para não substituir server.py.")
    if "import pt_split" not in s:
        s = s.replace("import p5_checkout\n", "import p5_checkout\nimport pt_split\n", 1)
    if "pt_split.router" not in s:
        if s.count("p5_checkout.router,") != 1:
            stop("Registo de routers personalizado: requer inspeção.")
        s = s.replace("p5_checkout.router,", "p5_checkout.router, pt_split.router,", 1)
    return s.encode("utf-8")


def patch_data(ours):
    s = ours.decode("utf-8")
    if '"p5_eligible": p5_eligible' in s:
        return ours
    a = '    return {"cupom": c["cupom"], "campanha": c["nome"], "desconto": c["desconto"], "validade": c["validade"], "status": c["status"],'
    if s.count(a) != 1:
        stop("Resposta do cupão personalizado; nada aplicado.")
    before = ('    p5_eligible = bool(c.get("influencer_id")) and float(c.get("desconto", -1)) == 5 and float(c.get("comissao", -1)) == 5\n')
    s = s.replace(a, before + a.replace('"cupom":', '"p5_eligible": p5_eligible, "cupom":'), 1)
    return s.encode("utf-8")


def patch_payments(ours):
    s = ours.decode("utf-8")
    guard = '    if currency_enabled("eur"):\n'
    new_guard = ('    if currency_enabled("eur") and float(c.get("desconto", -1)) == 5 '
                 'and float(c.get("comissao", -1)) == 5 and c.get("influencer_id"):\n')
    if guard in s:
        if s.count(guard) != 1:
            stop("Guard checkout Portugal ambíguo.")
        s = s.replace(guard, new_guard, 1)
    elif new_guard not in s:
        stop("Proteção de checkout EUR P5 não encontrada.")
    if "await settle_webhook_safely(obj[" not in s:
        pos = s.find("async def stripe_webhook")
        if pos < 0:
            stop("Webhook EUR inexistente.")
        m = re.search(r'(?m)^(?P<indent>[ ]+)await fulfil\(obj\["id"\], .*?\)[ \t]*$', s[pos:])
        if not m:
            stop("Webhook EUR alterado, não foi possível inserir a reconciliação P5 com segurança.")
        offset = pos + m.end()
        indent = m.group("indent")
        s = s[:offset] + "\n" + indent + "from pt_split import settle_webhook_safely\n" + indent + 'await settle_webhook_safely(obj["id"])' + "\n" + s[offset:]
    return s.encode("utf-8")


def activate_env(original):
    s = original.decode("utf-8")
    # Read but NEVER print secrets. Prevent accidentally enabling PT live auto transfers.
    flags = {}
    for line in s.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        if k in flags:
            stop("Configuração duplicada no .env: " + k)
        flags[k] = v.strip().strip("'").strip('"').lower()
    auto = lambda k: (os.environ.get(k, flags.get(k, "false")).lower() == "true")
    if auto("PT_SPLIT_ENABLED") and auto("PT_SPLIT_LIVE_ENABLED") and auto("PT_SPLIT_AUTO_TRANSFER"):
        stop("Split PT live automático já ativo; avaliar antes de alterar P5 no workspace.")
    for k in ("P5_ENABLED", "P5_EUR_ENABLED", "P5_BRL_ENABLED"):
        lines = s.splitlines(keepends=True)
        matches = [i for i, line in enumerate(lines) if re.match(r"^\s*"+re.escape(k)+r"\s*=", line)]
        if len(matches) > 1:
            stop("Variável P5 repetida em .env: " + k)
        if matches:
            end = "\n" if lines[matches[0]].endswith("\n") else ""
            lines[matches[0]] = k + "=true" + end
            s = "".join(lines)
        else:
            s = s.rstrip("\n") + "\n" + k + "=true\n"
    return s.encode("utf-8")


def validate(staged):
    auth = (ROOT / "backend/routes_auth.py").read_text()
    ast.parse(auth, filename="backend/routes_auth.py")
    for path, data in staged.items():
        if path.endswith(".py"):
            ast.parse(data.decode("utf-8"), filename=path)
    pix = (ROOT / "backend/routes_pix.py").read_text()
    if "PIX_STRIPE_SECRET_KEY" not in pix or "currency_enabled('brl')" not in pix:
        stop("Código Pix não preservado ou P5 BR não integrado. Nada aplicado.")
    php = staged.get("backend/p5_checkout.py") or (ROOT / "backend/p5_checkout.py").read_bytes()
    if b"checkout_globally_enabled" not in php or b"await wait_for_connect" not in php:
        stop("Política de espera financeira P5 não está presente.")
    partner = staged.get("frontend/src/pages/PartnerDashboard.jsx") or (ROOT / "frontend/src/pages/PartnerDashboard.jsx").read_bytes()
    public = staged.get("frontend/src/pages/PublicCoupon.jsx") or (ROOT / "frontend/src/pages/PublicCoupon.jsx").read_bytes()
    if b"p5EligibleCampaign" not in partner or b"c.p5_eligible" not in public:
        stop("Compatibilidade de campanhas antigas não confirmada.")
    jsx = [(p, d) for p, d in staged.items() if p.endswith(".jsx")]
    if jsx:
        with tempfile.TemporaryDirectory(prefix="p5_jsx_") as temp:
            paths = []
            for i, (_, data) in enumerate(jsx):
                p = Path(temp) / f"component_{i}.jsx"
                p.write_bytes(data)
                paths.append(str(p))
            program = ("const fs=require('fs');const parser=require('@babel/parser');"
                       "for(const p of process.argv.slice(1)) parser.parse(fs.readFileSync(p,'utf8'),"
                       "{sourceType:'module',plugins:['jsx']});")
            p = subprocess.run(["node", "-e", program, *paths],
                               cwd=str(ROOT/"frontend"), capture_output=True, text=True, timeout=35)
            if p.returncode != 0:
                stop("Sintaxe JSX: " + (p.stderr or "")[-330:])
    print("✓ Sintaxe Python, frontend e proteção Pix/legado verificadas.", flush=True)


def atomic_write(path, payload, old=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".p5-stage")
    try:
        tmp.write_bytes(payload)
        if old is not None and path.exists():
            tmp.chmod(path.stat().st_mode & 0o777)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def run():
    if not (ROOT/"backend/server.py").is_file() or not (ROOT/"frontend/package.json").is_file():
        stop("Workspace RRClub não identificado em /app.")
    envfile = ROOT/"backend/.env"
    if not envfile.is_file():
        stop("backend/.env não encontrado: ativação P5 requer ambiente existente.")
    print("RRCLUB P5 — INTEGRAÇÃO + ATIVAÇÃO QR SEGURO PT/BR", flush=True)
    staged = {}
    for rel, ancestor_hash, desired_hash in MANIFEST:
        p = ROOT/rel
        if p.is_symlink():
            stop("Não substituirei ligação simbólica: "+rel)
        desired = remote(TARGET, rel, desired_hash)
        if p.is_file() and p.read_bytes() == desired:
            continue
        if ancestor_hash is None:
            if p.exists():
                stop("Ficheiro financeiro já existente e diferente: " + rel)
            staged[rel] = desired
            continue
        if not p.is_file():
            stop("Ficheiro base local não encontrado: " + rel)
        ancestor = remote(BASE, rel, ancestor_hash)
        ours = p.read_bytes()
        merged = desired if ours == ancestor else merge(rel, ours, ancestor, desired)
        if merged != ours:
            staged[rel] = merged

    for rel, patcher in (
        ("backend/server.py", patch_server),
        ("backend/routes_data.py", patch_data),
        ("backend/routes_payments.py", patch_payments),
    ):
        p = ROOT / rel
        if not p.is_file():
            stop("Falta ficheiro local " + rel)
        ours = p.read_bytes()
        new = patcher(ours)
        if new != ours:
            staged[rel] = new
    oldenv = envfile.read_bytes()
    newenv = activate_env(oldenv)
    if newenv != oldenv:
        staged["backend/.env"] = newenv
    print("1/3 Ficheiros para integrar:", len(staged), flush=True)
    validate(staged)
    backup = Path(tempfile.mkdtemp(prefix="rrclub_p5_release_", dir="/tmp"))
    originals = {}
    for rel in staged:
        p = ROOT / rel
        orig = p.read_bytes() if p.is_file() else None
        originals[rel] = orig
        if orig is not None:
            dest = backup / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
    print("2/3 Backup protegido:", backup, flush=True)
    try:
        for rel, data in staged.items():
            atomic_write(ROOT/rel, data, originals[rel])
        for test in ("test_p5_rules.py", "test_p5_activation_policy.py", "test_p5_legacy_campaigns.py"):
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT/"backend")
            p = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s",
                 str(ROOT/"backend/tests"), "-p", test, "-v"],
                cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=35
            )
            if p.returncode:
                stop("Falha de teste " + test + ": " + (p.stderr or p.stdout)[-400:])
        print("3/3 APROVADO — código P5 PT/BR atualizado, flags de QR true, testes OK.")
        print("Legado preservado; Pix e credenciais originais intactos.")
        print("Split Portugal NÃO foi ativado; destinatários sem KYC aguardam Stripe.")
        print("SEM deploy, cobrança, repasse ou transferência neste comando.")
        print("Podes atualizar a PRÉVIA e, depois de confirmar o caminho P5, usar DEPLOY do Emergent.")
    except Exception:
        for rel, data in originals.items():
            p = ROOT / rel
            if data is None:
                if p.exists(): p.unlink()
            else:
                atomic_write(p, data, data)
        print("Restauro efetuado; alterações anteriores preservadas.", flush=True)
        raise


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print("PARADO EM SEGURANÇA:", str(exc), flush=True)
        sys.exit(1)
