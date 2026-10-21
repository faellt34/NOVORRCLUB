#!/usr/bin/env python3
"""RRClub Emergent preflight: verifies local financial-audit integration safely.

READ-ONLY against application sources and databases:
- Never calls Stripe or production APIs.
- Never modifies existing Python/JS files.
- Never initiates a payment, transfer, payout, deployment or Git merge.
- Does not print .env or Stripe credentials.
- Runs a local React build only if dependencies are already installed.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path("/app") if Path("/app/backend/server.py").is_file() else Path.cwd()
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
checked, issues, warnings = [], [], []


def verify_file(relative_path: str, *must_contain: str):
    p = ROOT / relative_path
    if not p.is_file():
        issues.append(f"FICHEIRO EM FALTA: {relative_path}")
        return ""
    value = p.read_text(encoding="utf-8")
    for needle in must_contain:
        if needle not in value:
            issues.append(f"TEXTO EM FALTA em {relative_path}: {needle}")
    checked.append(relative_path)
    return value


print("=== RRCLUB PORTUGAL: VALIDACAO LOCAL DA AUDITORIA ===")
print("Diretorio:", ROOT)
server = verify_file(
    "backend/server.py",
    "routes_finance",
    "routes_finance.router",
)
finance = verify_file(
    "backend/routes_finance.py",
    "/admin/finance/reconciliation",
    'require_role("admin")',
    "transfer_evidence",
)
evidence = verify_file(
    "backend/finance_evidence.py",
    "transfer_evidence",
    "bank_payout",
    "not_verified",
)
payout = verify_file("frontend/src/pages/AdminPayouts.jsx", "FinanceReconciliationPanel")
component = verify_file(
    "frontend/src/components/FinanceReconciliationPanel.jsx",
    "export default function",
    "/admin/finance/reconciliation",
    "Verificar na Stripe",
)
verify_file("backend/routes_payments.py")
verify_file("backend/routes_pix.py")

if "/admin/finance/reconciliation" in finance and finance.count('require_role("admin")') >= 2:
    print("OK: endpoints de auditoria requerem admin.")
else:
    issues.append("Proteger GET de auditoria com autenticacao administrativa.")

if "transfer_evidence" in evidence and '"bank_payout": "not_verified"' in evidence:
    print("OK: uma transferencia Stripe nao e confundida com payout bancario.")
else:
    issues.append("Nao foi verificada a distincao entre transferencia e payout.")

if "Marcar como pago" in payout:
    warnings.append("Painel ainda contem acao manual 'Marcar como pago': nao usar em comissoes sem beneficiario.")

if "split_executado" in (ROOT / "backend/routes_payments.py").read_text(encoding="utf-8"):
    warnings.append("Fluxo legado ainda emite split_executado; evento nao comprova transferencia financeira.")

print("Ficheiros verificados:", len(checked))

with tempfile.TemporaryDirectory(prefix="rrclub-finance-preflight-") as tmp:
    files = ["backend/server.py", "backend/routes_finance.py", "backend/finance_evidence.py"]
    cmd = [sys.executable, "-m", "py_compile"] + [str(ROOT / f) for f in files if (ROOT / f).exists()]
    if len(cmd) > 3:
        env = os.environ.copy()
        env["PYTHONPYCACHEPREFIX"] = str(Path(tmp) / "pycache")
        proc = subprocess.run(cmd, cwd=str(ROOT), env=env, text=True, capture_output=True)
        if proc.returncode:
            issues.append("Falha na sintaxe Python: " + (proc.stderr or proc.stdout)[-1400:])
        else:
            print("OK: sintaxe Python.")

    module_ok = (BACKEND / "finance_evidence.py").is_file()
    if module_ok:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(BACKEND)
        environment["PYTHONPYCACHEPREFIX"] = str(Path(tmp) / "pycache")
        test = """
from finance_evidence import transfer_evidence
pi={"status":"succeeded","amount":90}
assert transfer_evidence(pi,None,None,90,"acct_example")["state"] != "transferred_to_connected_stripe_account"
assert transfer_evidence(pi,None,None,91,"acct_example")["state"] == "amount_mismatch"
assert transfer_evidence(pi,None,None,90,None)["state"] == "destination_unlinked"
print("OK: prova financeira independente.")
"""
        proc = subprocess.run([sys.executable, "-c", test], cwd=str(ROOT), env=environment, capture_output=True, text=True)
        if proc.returncode:
            issues.append("Teste de evidencia financeira falhou: " + proc.stderr[-1200:])
        else:
            print(proc.stdout.strip())

    if (FRONTEND / "node_modules" / "@craco").exists() or (FRONTEND / "node_modules" / "react-scripts").exists():
        if not (FRONTEND / "package.json").is_file():
            issues.append("Ficheiro frontend/package.json em falta.")
        else:
            env = os.environ.copy()
            env["CI"] = "false"
            try:
                output = subprocess.run(["npm", "run", "build"], cwd=str(FRONTEND), env=env,
                                        capture_output=True, text=True, timeout=180)
                if output.returncode:
                    issues.append("Build frontend falhou: " + (output.stderr + "\n" + output.stdout)[-2400:])
                else:
                    print("OK: build frontend compilou.")
            except (FileNotFoundError, subprocess.TimeoutExpired) as err:
                issues.append("Build frontend nao concluido: " + str(err))
    else:
        warnings.append("Build React NAO executado: dependencias node_modules nao instaladas localmente.")

print("\n=== RESULTADO ===")
for m in warnings:
    print("AVISO:", m)
for m in issues:
    print("ERRO:", m)
if issues:
    print("NAO PUBLICAR: corrigir os erros acima antes de publicar.")
    sys.exit(2)
print("VALIDACAO LOCAL BASICA APROVADA; nao confirma integracao real com a Stripe nem repasses.")
print("NENHUM DEPLOY OU PAGAMENTO EXECUTADO.")
