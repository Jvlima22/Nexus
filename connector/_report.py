"""
Relatório do Autotrader: (A) histórico persistente em risk_events + (B) varredura
AO VIVO de cada par da watchlist (mesma lógica M5+M15 do robô), via o connector rodando.
"""
import httpx

import supabase_sync as ss
from config import settings

BASE = f"http://localhost:{settings.port}"
H = httpx.Client(base_url=BASE, timeout=30)


def section(t):
    print("\n" + "=" * 72 + f"\n{t}\n" + "=" * 72)


# ── A) Histórico persistente (o que chegou ao Risk Judge) ───────────────────────
section("A) HISTÓRICO PERSISTENTE — risk_events (negadas x operadas)")
sb = ss.get_sb()
try:
    rows = (sb.table("risk_events").select("*").order("created_at", desc=True).limit(500).execute()).data or []
except Exception:
    rows = (sb.table("risk_events").select("*").limit(500).execute()).data or []

appr = [r for r in rows if r.get("decision") == "approved"]
rej = [r for r in rows if r.get("decision") == "rejected"]
print(f"total: {len(rows)} | operou (approved): {len(appr)} | negou (rejected): {len(rej)}")
from collections import Counter
if rej:
    print("\nnegadas por motivo:")
    for code, n in Counter(r.get("code") for r in rej).most_common():
        print(f"  {code:<18} {n}")
if appr:
    print("\nAPROVADAS (operou) — detalhe:")
    for r in appr:
        ts = (r.get("created_at") or "")[:19].replace("T", " ")
        print(f"  {ts} | {str(r.get('asset')):<14} | {r.get('direction')} | "
              f"conf {r.get('confidence')} | amt {r.get('amount')} | src {r.get('source')}")
print("\nultimas 15 decisoes do juiz:")
for r in rows[:15]:
    ts = (r.get("created_at") or "")[:19].replace("T", " ")
    print(f"  {ts} | {r.get('decision'):<8} | {str(r.get('code')):<16} | "
          f"{str(r.get('asset')):<14} | {str(r.get('direction'))}")

# ── contexto dos gates globais agora ────────────────────────────────────────────
section("CONTEXTO DOS GATES AGORA")
try:
    sent = H.get("/sentiment").json()
    print(f"macro_bias (Polymarket): {sent.get('macro_bias')}  -> veta ordens contrárias")
except Exception as e:
    print(f"sentiment: erro {e}")
try:
    cal = H.get("/calendar").json()
    print(f"blackout de notícia: {cal.get('blackout')}")
except Exception as e:
    print(f"calendar: erro {e}")

# ── B) Varredura ao vivo da watchlist ───────────────────────────────────────────
section("B) VARREDURA AO VIVO — cada par da watchlist (M5 + M15)")
st = H.get("/autotrader/status").json()
watch = st.get("assets", [])
print(f"watchlist: {st.get('watchlist_count')} ativos ({st.get('universe')}), "
      f"payout≥{st.get('min_payout')}% | mostrando {len(watch)}\n")


def sig(active, size):
    try:
        r = H.get(f"/indicators?active={active}&size={size}&count=200").json()
        return r.get("direction"), r.get("confidence"), r.get("bias")
    except Exception:
        return "ERR", None, None


rows_out = []
for a in watch:
    d5, c5, _ = sig(a, 300)
    if d5 in (None, "ERR"):
        rows_out.append((a, d5, c5, None, None, "pulou: sem consenso M5" if d5 is None else "erro M5"))
        continue
    d15, c15, _ = sig(a, 900)
    if d15 != d5:
        rows_out.append((a, d5, c5, d15, c15, f"pulou: sem confluência (M15={d15})"))
    else:
        conf = min(c5 or 0, c15 or 0)
        rows_out.append((a, d5, c5, d15, c15, f">>> OPORTUNIDADE: {d5.upper()} conf {conf:.2f} (iria ao juiz)"))

# ordena: oportunidades primeiro
rows_out.sort(key=lambda r: (not r[5].startswith(">>>"), r[0]))
print(f"{'ATIVO':<15} {'M5':<5} {'c5':<5} {'M15':<5} {'c15':<5} VEREDITO")
print("-" * 72)
opp = 0
for a, d5, c5, d15, c15, verd in rows_out:
    if verd.startswith(">>>"):
        opp += 1
    f5 = f"{c5:.2f}" if isinstance(c5, (int, float)) else "-"
    f15 = f"{c15:.2f}" if isinstance(c15, (int, float)) else "-"
    print(f"{a:<15} {str(d5):<5} {f5:<5} {str(d15):<5} {f15:<5} {verd}")

section("RESUMO")
skip5 = sum(1 for r in rows_out if "sem consenso" in r[5])
skipc = sum(1 for r in rows_out if "sem confluência" in r[5])
print(f"analisados: {len(rows_out)} | oportunidades (confluência): {opp} | "
      f"sem consenso M5: {skip5} | sem confluência: {skipc}")
print("Obs: 'oportunidade' = passaria a confluência; a execução ainda depende do Risk Judge "
      "(sessão/macro/notícia/confiança/2%/breaker/teto).")
