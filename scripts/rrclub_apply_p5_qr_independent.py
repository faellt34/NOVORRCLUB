#!/usr/bin/env python3
"""Apply only P5 QR approval/polling fixes. No Stripe calls or payout changes."""
from pathlib import Path
import sys
import tempfile
import shutil
import subprocess
import os

root = Path("/app")
partner = root / "frontend/src/pages/PartnerDashboard.jsx"
follower = root / "frontend/src/components/P5FollowerPanel.jsx"
test_file = root / "frontend/src/components/P5FollowerPanel.test.jsx"
for p in (partner, follower):
    if not p.is_file():
        raise SystemExit("BLOQUEADO: falta o ficheiro " + str(p))

original = {p: p.read_text(encoding="utf-8") for p in (partner, follower)}
changed = {}
p = original[partner]
old = 'disabled={submitting || (preview?.currency === "brl" && !pixAvailable)}'
new = 'disabled={submitting || (!p5Mode && preview?.currency === "brl" && !pixAvailable)}'
if old in p:
    if p.count(old) != 1:
        raise SystemExit("BLOQUEADO: botao do parceiro ambiguo")
    p = p.replace(old, new, 1)
elif new not in p:
    raise SystemExit("BLOQUEADO: botao do parceiro personalizado; nada alterado")
changed[partner] = p

s = original[follower]
old_poll1 = """    const started = Date.now();
    async function check() {"""
new_poll1 = """    const started = Date.now();
    // QR valido ate o prazo real da sessao, sem encerrar monitorizacao aos 5 min.
    const expiry = Date.parse(session.expires_at);
    const pollingDeadline = Number.isFinite(expiry) ? expiry : started + 300000;
    async function check() {"""
old_poll2 = """      if (!cancelled && Date.now() - started < 300000) {
        timer = setTimeout(check, 2500);
      }"""
new_poll2 = """      if (!cancelled && Date.now() < pollingDeadline) {
        timer = setTimeout(check, Date.now() - started < 300000 ? 2500 : 15000);
      }"""
if old_poll1 in s and old_poll2 in s:
    if s.count(old_poll1) != 1 or s.count(old_poll2) != 1:
        raise SystemExit("BLOQUEADO: monitorizacao P5 ambigua")
    s = s.replace(old_poll1, new_poll1, 1).replace(old_poll2, new_poll2, 1)
elif "const pollingDeadline =" not in s or "Date.now() < pollingDeadline" not in s:
    raise SystemExit("BLOQUEADO: monitorizacao P5 personalizada; nada alterado")
changed[follower] = s

if not all(needle in changed[partner] for needle in (
    "(!p5Mode && preview?.currency", 'data-testid="validate-coupon-button"'
)):
    raise SystemExit("BLOQUEADO: botao P5 nao validado")
if not all(needle in changed[follower] for needle in (
    "Date.now() < pollingDeadline", "session.expires_at",
    "Date.now() - started < 300000 ? 2500 : 15000"
)):
    raise SystemExit("BLOQUEADO: monitorizacao P5 nao validada")

modifications = {path: content for path, content in changed.items() if original[path] != content}
if not modifications:
    print("P5: APPROVACAO QR E MONITORIZACAO JA CORRIGIDAS, NADA DUPLICADO")
    sys.exit(0)
backup = Path(tempfile.mkdtemp(prefix="rrclub_p5_qr_backup_"))
for file in modifications:
    shutil.copy2(file, backup / file.name)
try:
    for file, contents in modifications.items():
        file.write_text(contents, encoding="utf-8")
    frontend = root / "frontend"
    npm = shutil.which("npm")
    if npm and (frontend / "node_modules/@craco/craco").exists() and test_file.is_file():
        env = dict(os.environ, CI="true")
        result = subprocess.run(
            [npm, "test", "--", "--watch=false", "--runInBand",
             "--runTestsByPath", "src/components/P5FollowerPanel.test.jsx"],
            cwd=frontend, env=env, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=120
        )
        print(result.stdout[-4500:])
        if result.returncode:
            raise RuntimeError("teste P5 frontend falhou")
        print("P5 FRONTEND: TESTES EXISTENTES PASSARAM")
    else:
        print("P5 FRONTEND: dependencias/teste indisponiveis; verificacao estatica OK.")
except Exception as exc:
    for file in modifications:
        file.write_text(original[file], encoding="utf-8")
    raise SystemExit("BLOQUEADO: rollback concluido; " + type(exc).__name__ + ": " + str(exc))
print("P5 QR: APROVACAO INDEPENDENTE DO PIX APLICADA")
print("Monitorizacao continua ate expiracao da sessao.")
print("Backup:", backup)
print("Nenhuma conta Stripe, campanha, parceiro, influencer, repasse ou deploy alterado.")
