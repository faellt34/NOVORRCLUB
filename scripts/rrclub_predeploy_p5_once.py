#!/usr/bin/env python3
"""Read-only RRClub P5 deploy gate. Never moves money, alters flags or deploys."""
import ast
from pathlib import Path
import os
import subprocess
import sys
from urllib.request import urlopen

ROOT=Path("/app") if Path("/app/backend/server.py").is_file() else Path.cwd()
BACKEND=ROOT/"backend"
issues=[]

def check(name,good,detail=""):
    print(("OK" if good else "FALHA")+": "+name+(" — "+detail if detail else ""))
    if not good: issues.append(name)

print("=== RRCLUB PRE-DEPLOY P5 ===")
required=("server.py","routes_auth.py","p5_checkout.py","p5_rules.py",
          "pt_split.py","routes_pix.py","routes_payments.py")
for name in required:
    f=BACKEND/name
    try:
        ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        check("Python "+name,True)
    except Exception as ex:
        check("Python "+name,False,type(ex).__name__+" "+str(ex)[:120])
checkout=(BACKEND/"p5_checkout.py").read_text()
server=(BACKEND/"server.py").read_text()
pt=(BACKEND/"pt_split.py").read_text()
check("P5 router", "p5_checkout.router" in server)
check("P5 cobrança PT com MB WAY", 'payment_method_types=["card", "mb_way"]' in checkout)
check("Sem downgrade oculto para cartão", 'idempotency_key="p5-" + rec["id"] + "-card"' not in checkout)
check("Validação destinatários PT", "recipients_ready" in checkout and "recipients_ready" in pt)
check("QR e checkout BRL/EUR separados", "currency_enabled" in checkout and "brl" in checkout and "eur" in checkout)
env={}
f=BACKEND/".env"
if f.is_file():
    for line in f.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k,v=line.split("=",1)
            env[k.strip()]=v.strip().strip("'").strip('"')
for k in ("P5_ENABLED","P5_BRL_ENABLED","P5_EUR_ENABLED","PIX_ENABLED",
          "PT_SPLIT_ENABLED","PT_SPLIT_LIVE_ENABLED","PT_SPLIT_AUTO_TRANSFER"):
    val=os.environ.get(k,env.get(k,"not_set")).lower()
    print("CONFIG "+k+"="+val+" (configuração, não prova de pagamento)")
frontend=ROOT/"frontend"
if frontend.is_dir():
    run=subprocess.run(["npm","run","build"],cwd=frontend,timeout=180)
    check("Frontend produção",run.returncode==0)
else: check("Frontend presente",False)
try:
    with urlopen("https://rrclub.online/api/",timeout=12) as response:
        check("API pública online (não é teste financeiro)",response.status==200)
except Exception as ex:
    print("AVISO: API pública não respondeu:",type(ex).__name__)
print("NENHUM pagamento, transferência, Mongo, .env ou deploy alterado.")
if issues:
    print("BLOQUEADO: corrigir falhas acima antes do deploy:",", ".join(issues))
    sys.exit(1)
print("RRCLUB P5: APTO PARA DEPLOY DE CÓDIGO; split LIVE depende de verificação por campanha.")
