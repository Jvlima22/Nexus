"""
Varredura de EXPIRAÇÃO (Robô OTC v2 — item 3). Mede o acerto da estratégia atual
(indicators.analyze, voto-maioria) em 3 expirações — 1min/5min/15min — cada uma no
seu timeframe nativo (sinal gerado e resolvido no mesmo TF, como binária opera).

Fecha a última porta do OTC antes de cravar "beco sem saída": se nenhuma expiração
cruzar o breakeven em nenhum par, a varredura de expiração também não tem edge.

Roda standalone contra o connector LIGADO (usa /candles e /autotrader/status).
Uso:  .venv/Scripts/python.exe _expiration.py
"""
import sys

import httpx

import indicators
from config import settings

sys.stdout.reconfigure(encoding="utf-8")  # console cp1252 não imprime ≥/–/etc.

BASE = f"http://localhost:{settings.port}"
H = httpx.Client(base_url=BASE, timeout=90)

# (label, size_segundos, n_candles_a_puxar)
TFS = [("1min  (M1)", 60, 700), ("5min  (M5)", 300, 700), ("15min (M15)", 900, 500)]
WIN = 200
PAYOUT = 0.84
BREAKEVEN = 1 / (1 + PAYOUT)


def candles(active, size, count):
    r = H.get(f"/candles?active={active}&size={size}&count={count}")
    r.raise_for_status()
    return r.json()["candles"]


def outcome(c_now, c_next):
    if c_next["close"] > c_now["close"]:
        return "call"
    if c_next["close"] < c_now["close"]:
        return "put"
    return None


def scan_tf(active, label, size):
    """Acerto do baseline em 1 expiração (= 1 candle do TF). Retorna (wins, n)."""
    try:
        c = candles(active, size, [n for lbl, s, n in TFS if s == size][0])
    except Exception:
        return 0, 0
    if len(c) < WIN + 10:
        return 0, 0
    w = n = 0
    for i in range(WIN, len(c) - 1):
        d = indicators.analyze(active, label, c[i - WIN + 1:i + 1])["direction"]
        if d is None:
            continue
        realized = outcome(c[i], c[i + 1])
        if realized is None:
            continue
        n += 1
        w += int(d == realized)
    return w, n


def run():
    watch = H.get("/autotrader/status").json().get("assets", [])
    print(f"Varredura de expiração — {len(watch)} pares OTC | breakeven {BREAKEVEN:.1%} "
          f"(payout {PAYOUT:.0%}) | meta 57%\n")

    agg = {label: [0, 0] for label, _, _ in TFS}
    best_per_pair = {label: (None, 0.0, 0) for label, _, _ in TFS}

    for a in watch:
        for label, size, _ in TFS:
            w, n = scan_tf(a, label, size)
            if n == 0:
                continue
            agg[label][0] += w
            agg[label][1] += n
            rate = w / n
            if n >= 200 and rate > best_per_pair[label][1]:
                best_per_pair[label] = (a, rate, n)

    print("=" * 64)
    print(f"{'EXPIRAÇÃO':<16}{'ACERTO':>9}{'AMOSTRA':>10}   veredito")
    print("-" * 64)
    for label, _, _ in TFS:
        w, n = agg[label]
        if n == 0:
            print(f"{label:<16}{'—':>9}{0:>10}")
            continue
        rate = w / n
        flag = "ACIMA breakeven" if rate > BREAKEVEN else "abaixo"
        mark = "  <<< EDGE" if rate > 0.57 else ""
        print(f"{label:<16}{rate:>8.1%}{n:>10}   {flag}{mark}")

    print("\nMELHOR par por expiração (amostra ≥ 200):")
    for label, _, _ in TFS:
        a, rate, n = best_per_pair[label]
        if a is None:
            print(f"  {label:<16} —")
            continue
        mark = "  <<< EDGE" if rate > 0.57 else (" (>breakeven)" if rate > BREAKEVEN else "")
        print(f"  {label:<16} {a:<14} {rate:.1%}  ({n}){mark}")

    print(f"\nbreakeven={BREAKEVEN:.1%}  meta=57.0%  — promover expiração só com EDGE marcado.")


if __name__ == "__main__":
    run()
