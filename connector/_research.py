"""
Pesquisa de sinal (Robô OTC v2 — item 2 "motor mais forte"). MEDE candidatos de
estratégia contra o histórico REAL antes de promover qualquer um ao código de
produção — honra a regra de ouro: nada entra sem re-backtest acima do breakeven.

Roda standalone contra o connector LIGADO (usa /candles e /autotrader/status, não
abre 2ª conexão IQ). Para cada par OTC da watchlist, puxa M5/M15/H1 uma vez e tabela
a taxa de acerto (expiração = 1 candle M5) de várias variantes de sinal.

Uso:  .venv/Scripts/python.exe _research.py
"""
import httpx

import indicators
from config import settings

BASE = f"http://localhost:{settings.port}"
H = httpx.Client(base_url=BASE, timeout=90)

M5, M15, H1 = 300, 900, 3600
N5, N15, NH1 = 700, 240, 200
WIN = 200                 # janela passada por analyze (igual ao robô)
PAYOUT = 0.84
BREAKEVEN = 1 / (1 + PAYOUT)


def candles(active, size, count):
    r = H.get(f"/candles?active={active}&size={size}&count={count}")
    r.raise_for_status()
    return r.json()["candles"]


def trail_dir(series, j, tf, win=WIN):
    """direction do analyze() sobre a janela trailing até o índice j."""
    lo = max(0, j - win + 1)
    return indicators.analyze("x", tf, series[lo:j + 1])["direction"]


def trail_trend(series, j, tf, lookback=20):
    lo = max(0, j - lookback + 1)
    return indicators.trend_structure(series[lo:j + 1], lookback)


def hour_of(ts):
    import datetime
    return datetime.datetime.utcfromtimestamp(ts).hour


# ── variantes: cada uma devolve 'call'/'put'/None p/ o sinal no índice i de c5 ──
def v_baseline(win5):
    return indicators.analyze("x", "M5", win5)["direction"]


def v_strong(win5):
    """Só consenso forte: |bull-bear| >= 3 de 5 indicadores (confiança >= 0.6)."""
    s = indicators.analyze("x", "M5", win5)
    return s["direction"] if s["confidence"] >= 0.6 else None


def v_momentum(win5):
    a, b = win5[-2]["close"], win5[-1]["close"]
    return "call" if b > a else "put" if b < a else None


def v_reversion(win5):
    a, b = win5[-2]["close"], win5[-1]["close"]
    return "put" if b > a else "call" if b < a else None


def v_rsi_extreme(win5):
    closes = [c["close"] for c in win5]
    r = indicators.rsi(closes)
    if r is None:
        return None
    if r < 30:
        return "call"
    if r > 70:
        return "put"
    return None


def v_ema_only(win5):
    return {"bullish": "call", "bearish": "put", "neutral": None}[
        indicators._vote_ema([c["close"] for c in win5])  # noqa: SLF001
    ]


VARIANTS = {
    "baseline (voto maioria)": v_baseline,
    "consenso forte (conf>=0.6)": v_strong,
    "momentum (segue ult. candle)": v_momentum,
    "reversao (contra ult. candle)": v_reversion,
    "RSI extremo (<30/>70)": v_rsi_extreme,
    "EMA cross puro": v_ema_only,
}


def outcome(c_now, c_next):
    if c_next["close"] > c_now["close"]:
        return "call"
    if c_next["close"] < c_now["close"]:
        return "put"
    return None


def run():
    watch = H.get("/autotrader/status").json().get("assets", [])
    print(f"Pesquisa de sinal — {len(watch)} pares OTC | breakeven {BREAKEVEN:.1%} "
          f"(payout {PAYOUT:.0%}) | exp 1 candle M5\n")

    # tally por variante: [wins, n]; e variantes com filtro H1 (sufixo +H1)
    tally = {k: [0, 0] for k in VARIANTS}
    tally.update({f"{k} +H1": [0, 0] for k in VARIANTS})
    by_hour = {h: [0, 0] for h in range(24)}  # baseline por hora UTC

    for a in watch:
        try:
            c5 = candles(a, M5, N5)
            ch1 = candles(a, H1, NH1)
        except Exception:
            continue
        if len(c5) < WIN + 10 or len(ch1) < 30:
            continue

        jh = 0
        for i in range(WIN, len(c5) - 1):
            t = c5[i]["time"]
            while jh + 1 < len(ch1) and ch1[jh + 1]["time"] <= t:
                jh += 1
            win5 = c5[i - WIN + 1:i + 1]
            realized = outcome(c5[i], c5[i + 1])
            if realized is None:
                continue
            h1_trend = trail_trend(ch1, jh, "H1")  # bullish/bearish/neutral

            for name, fn in VARIANTS.items():
                d = fn(win5)
                if d is None:
                    continue
                won = int(d == realized)
                tally[name][0] += won
                tally[name][1] += 1
                # filtro H1: só conta se o H1 concorda com a direção
                agree = (h1_trend == "bullish" and d == "call") or \
                        (h1_trend == "bearish" and d == "put")
                if agree:
                    tally[f"{name} +H1"][0] += won
                    tally[f"{name} +H1"][1] += 1
                if name.startswith("baseline"):
                    by_hour[hour_of(t)][0] += won
                    by_hour[hour_of(t)][1] += 1

    print("=" * 70)
    print(f"{'VARIANTE':<34}{'ACERTO':>10}{'AMOSTRA':>10}   veredito")
    print("-" * 70)
    for name, (w, n) in sorted(tally.items(), key=lambda kv: (kv[1][0] / kv[1][1]) if kv[1][1] else 0, reverse=True):
        if n == 0:
            print(f"{name:<34}{'—':>10}{0:>10}")
            continue
        rate = w / n
        flag = "ACIMA breakeven" if rate > BREAKEVEN else ("> margem 57%!" if rate > 0.57 else "abaixo")
        mark = "  <<< EDGE" if rate > 0.57 and n >= 300 else ""
        print(f"{name:<34}{rate:>9.1%}{n:>10}   {flag}{mark}")

    print("\nBaseline por HORA UTC (procura janela com edge):")
    for h in range(24):
        w, n = by_hour[h]
        if n < 50:
            continue
        rate = w / n
        bar = "#" * int((rate - 0.45) * 200) if rate > 0.45 else ""
        flag = " *>57%" if rate > 0.57 else ""
        print(f"  {h:02d}h  {rate:>6.1%}  ({n:>4}) {bar}{flag}")

    print(f"\nbreakeven={BREAKEVEN:.1%}  margem-alvo=57.0%  — só promove variante com EDGE marcado.")


if __name__ == "__main__":
    run()
