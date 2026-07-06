"""
Backtest empírico da estratégia do autotrader sobre o histórico REAL de candles OTC
(puxado da IQ via o connector rodando). Mede taxa de acerto de verdade — sem achismo.

Binária: vence se, na expiração (1 candle M5 = 5min), o preço fechou na direção prevista.
Breakeven com payout p: 1/(1+p). Ex.: p=0.84 -> 54.3%.
"""
import httpx

import indicators
from config import settings

BASE = f"http://localhost:{settings.port}"
H = httpx.Client(base_url=BASE, timeout=60)

M5, M15 = 300, 900
N5, N15 = 700, 240        # candles a puxar
WIN = 200                 # janela passada por analyze (igual ao robô)
PAYOUT = 0.84
BREAKEVEN = 1 / (1 + PAYOUT)


def candles(active, size, count):
    r = H.get(f"/candles?active={active}&size={size}&count={count}")
    r.raise_for_status()
    return r.json()["candles"]


def m15_dir_at(m15, j):
    """Direção do sinal M15 considerando candles até o índice j (janela trailing)."""
    lo = max(0, j - WIN + 1)
    s = indicators.analyze("x", "M15", m15[lo:j + 1])
    return s["direction"]


def outcome(c_now, c_next, direction):
    if c_next["close"] > c_now["close"]:
        return "call"
    if c_next["close"] < c_now["close"]:
        return "put"
    return "tie"


def backtest_pair(active):
    try:
        c5 = candles(active, M5, N5)
        c15 = candles(active, M15, N15)
    except Exception as e:
        return None
    if len(c5) < WIN + 10 or len(c15) < 40:
        return None

    # índice M15 cujo 'time' <= t (busca linear com ponteiro)
    res = []  # (conf, won, with_confluence_ok)
    j = 0
    for i in range(WIN, len(c5) - 1):
        t = c5[i]["time"]
        while j + 1 < len(c15) and c15[j + 1]["time"] <= t:
            j += 1
        sig = indicators.analyze(active, "M5", c5[i - WIN + 1:i + 1])
        d5 = sig["direction"]
        if d5 is None:
            continue
        conf = sig["confidence"]
        out = outcome(c5[i], c5[i + 1], d5)
        if out == "tie":
            continue
        won = out == d5
        confl_ok = (m15_dir_at(c15, j) == d5)
        res.append((conf, won, confl_ok))
    return res


def summarize(rows, label):
    n = len(rows)
    if n == 0:
        print(f"  {label}: sem amostras")
        return
    w = sum(1 for _, won, _ in rows if won)
    rate = w / n
    flag = "ACIMA do breakeven ✅" if rate > BREAKEVEN else "abaixo do breakeven ❌"
    print(f"  {label}: {w}/{n} = {rate:.1%}  ({flag})")


WATCH = H.get("/autotrader/status").json().get("assets", [])
print(f"Backtest OTC — {len(WATCH)} pares | janela {WIN} | breakeven {BREAKEVEN:.1%} (payout {PAYOUT:.0%})\n")

allrows = []
per_pair = []
for a in WATCH:
    r = backtest_pair(a)
    if r is None:
        continue
    allrows.extend(r)
    if r:
        w = sum(1 for _, won, _ in r if won)
        per_pair.append((a, w / len(r), len(r)))

print("=" * 64)
print("1) TODOS os sinais M5 (sem filtro)")
summarize([(c, won, ok) for c, won, ok in allrows], "M5 geral")

print("\n2) Por faixa de CONFIANÇA (M5)")
for lo in (0.2, 0.4, 0.6, 0.8, 1.0):
    sub = [(c, won, ok) for c, won, ok in allrows if abs(c - lo) < 1e-9]
    summarize(sub, f"conf = {lo:.1f}")
print("  --- limiares acumulados ---")
for thr in (0.4, 0.6, 0.8):
    summarize([(c, won, ok) for c, won, ok in allrows if c >= thr], f"conf >= {thr:.1f}")

print("\n3) COM CONFLUÊNCIA M5+M15 (regra atual do robô)")
summarize([(c, won, ok) for c, won, ok in allrows if ok], "confluência")
for thr in (0.4, 0.6, 0.8):
    summarize([(c, won, ok) for c, won, ok in allrows if ok and c >= thr], f"confluência + conf >= {thr:.1f}")

print("\n4) MELHORES e PIORES pares (taxa de acerto M5 geral)")
per_pair.sort(key=lambda x: x[1], reverse=True)
for a, rate, n in per_pair[:5]:
    print(f"  + {a:<14} {rate:.1%}  ({n})")
for a, rate, n in per_pair[-5:]:
    print(f"  - {a:<14} {rate:.1%}  ({n})")

# autocorrelação de retornos (mean-reversion vs momentum) num par líquido
print("\n5) NATUREZA do OTC (autocorrelação de retornos consecutivos)")
for a in WATCH[:6]:
    try:
        c5 = candles(a, M5, 400)
    except Exception:
        continue
    rets = [c5[i]["close"] - c5[i - 1]["close"] for i in range(1, len(c5))]
    pairs = [(rets[i - 1], rets[i]) for i in range(1, len(rets)) if rets[i - 1] and rets[i]]
    if len(pairs) < 30:
        continue
    mx = sum(x for x, _ in pairs) / len(pairs)
    my = sum(y for _, y in pairs) / len(pairs)
    cov = sum((x - mx) * (y - my) for x, y in pairs)
    vx = sum((x - mx) ** 2 for x, _ in pairs) ** 0.5
    vy = sum((y - my) ** 2 for _, y in pairs) ** 0.5
    ac = cov / (vx * vy) if vx and vy else 0
    nat = "MEAN-REVERSION (reversão)" if ac < -0.05 else "MOMENTUM (tendência)" if ac > 0.05 else "ruído (random walk)"
    print(f"  {a:<14} autocorr={ac:+.2f}  -> {nat}")
