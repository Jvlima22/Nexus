#!/usr/bin/env python3
"""
NEXUS Daily Trader Bot
Estratégia: EMA 20/50 H4 (tendência) + EMA 20 H1 (entrada) + Volume
Execução autônoma | 07:00 UTC | Risco 2% por trade
"""

import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

# ── Dependências ──────────────────────────────────────────────────────────────
for pkg in ["MetaTrader5", "python-dotenv"]:
    try:
        __import__(pkg.replace("-", "_").split(".")[0] if pkg != "python-dotenv" else "dotenv")
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--break-system-packages", "-q"])

import MetaTrader5 as mt5
from dotenv import load_dotenv
import os

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

MT5_LOGIN    = int(os.getenv("MT5_LOGIN", "108960873"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "H_3vClCm")
MT5_SERVER   = os.getenv("MT5_SERVER", "MetaQuotes-Demo")

RISK_PCT       = 0.02    # 2% por trade
MAX_POSITIONS  = 3       # máximo de posições simultâneas
MAX_DD_DAY_PCT = 0.04    # 4% drawdown máximo diário — para tudo
MIN_RR         = 1.2     # RR mínimo para abrir operação
MAGIC          = 20260701
NO_TRADE_AFTER = 20      # hora UTC — não abre ordens após 20:00 sexta

SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
    "AUDUSD", "NZDUSD", "USDCAD",
    "EURJPY", "GBPJPY", "XAUUSD",
]

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_PATH = BASE_DIR / "logs"
LOG_PATH.mkdir(exist_ok=True)
log_file = LOG_PATH / f"nexus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("NEXUS")


# ── Indicadores ───────────────────────────────────────────────────────────────

def ema(prices: list[float], period: int) -> float:
    """EMA simples — sem pandas."""
    k = 2.0 / (period + 1)
    val = sum(prices[:period]) / period  # seed com SMA
    for p in prices[period:]:
        val = p * k + val * (1 - k)
    return val


def avg_volume(volumes: list[float], lookback: int = 10) -> float:
    return sum(volumes[-lookback - 1:-1]) / lookback


# ── Análise de sinal ──────────────────────────────────────────────────────────

def analisar(symbol: str) -> dict | None:
    """
    Retorna sinal {symbol, side, entry, sl, tp, rr} ou None.
    Lógica:
      H4: EMA20 > EMA50 → tendência de alta → só BUY
           EMA20 < EMA50 → tendência de baixa → só SELL
      H1: último candle fechado > EMA20 H1 → confirma BUY
           último candle fechado < EMA20 H1 → confirma SELL
      Volume H1: último candle > média dos 10 anteriores
      SL: swing low/high dos últimos 5 candles H1
      TP: SL distance × RR mínimo
    """
    mt5.symbol_select(symbol, True)

    # H4 — 55 candles para EMA50 estável
    h4 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 56)
    if h4 is None or len(h4) < 55:
        log.warning(f"{symbol}: candles H4 insuficientes")
        return None

    closes_h4 = [c["close"] for c in h4]
    ema20_h4 = ema(closes_h4, 20)
    ema50_h4 = ema(closes_h4, 50)

    if ema20_h4 > ema50_h4:
        trend = "BUY"
    elif ema20_h4 < ema50_h4:
        trend = "SELL"
    else:
        return None  # sem tendência clara

    # H1 — 25 candles para EMA20 + volume
    h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 26)
    if h1 is None or len(h1) < 22:
        log.warning(f"{symbol}: candles H1 insuficientes")
        return None

    closes_h1 = [c["close"] for c in h1]
    volumes_h1 = [c["tick_volume"] for c in h1]
    ema20_h1 = ema(closes_h1, 20)

    last_close = closes_h1[-2]   # último candle FECHADO (index -1 ainda está formando)
    last_vol   = volumes_h1[-2]
    avg_vol    = avg_volume(volumes_h1[:-1])  # média dos 10 fechados antes do último

    # Confirmação de entrada
    if trend == "BUY"  and last_close <= ema20_h1:
        return None
    if trend == "SELL" and last_close >= ema20_h1:
        return None

    # Volume acima da média
    if last_vol < avg_vol * 0.9:  # tolerância de 10%
        return None

    # SL baseado em estrutura (swing dos últimos 5 candles H1 fechados)
    info = mt5.symbol_info(symbol)
    if not info:
        return None

    pip = info.point * 10  # 1 pip
    recent = h1[-6:-1]     # últimos 5 candles fechados

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return None

    if trend == "BUY":
        entry = tick.ask
        sl    = min(c["low"] for c in recent) - pip * 2
        dist  = entry - sl
        if dist <= 0:
            return None
        tp    = entry + dist * MIN_RR
    else:
        entry = tick.bid
        sl    = max(c["high"] for c in recent) + pip * 2
        dist  = sl - entry
        if dist <= 0:
            return None
        tp    = entry - dist * MIN_RR

    rr = abs(tp - entry) / abs(entry - sl)

    return {
        "symbol": symbol,
        "side":   trend,
        "entry":  entry,
        "sl":     round(sl, info.digits),
        "tp":     round(tp, info.digits),
        "rr":     round(rr, 2),
        "ema20_h4": round(ema20_h4, info.digits),
        "ema50_h4": round(ema50_h4, info.digits),
    }


# ── Gerenciamento de risco ────────────────────────────────────────────────────

def calcular_lots(symbol: str, entry: float, sl: float, balance: float) -> float:
    info = mt5.symbol_info(symbol)
    if not info:
        return 0.01

    sl_dist   = abs(entry - sl)
    tick_val  = info.trade_tick_value
    tick_size = info.trade_tick_size

    if tick_size == 0 or tick_val == 0:
        return 0.01

    risco_usd = balance * RISK_PCT
    risco_lot = (sl_dist / tick_size) * tick_val
    if risco_lot == 0:
        return 0.01

    lots = risco_usd / risco_lot
    step = info.volume_step
    lots = round(round(lots / step) * step, 2)
    lots = max(info.volume_min, min(info.volume_max, lots))
    return lots


def checar_drawdown_diario(balance: float, equity: float) -> bool:
    """Retorna True se drawdown excedeu o limite."""
    dd = (balance - equity) / balance
    if dd >= MAX_DD_DAY_PCT:
        log.error(f"⛔ Drawdown diário atingido: {dd*100:.1f}% ≥ {MAX_DD_DAY_PCT*100:.0f}%")
        return True
    return False


def contar_posicoes() -> int:
    pos = mt5.positions_get(magic=MAGIC)
    return len(pos) if pos else 0


def sexta_noite() -> bool:
    """True se for sexta após 20:00 UTC."""
    now = datetime.now(timezone.utc)
    return now.weekday() == 4 and now.hour >= NO_TRADE_AFTER


# ── Execução de ordens ────────────────────────────────────────────────────────

def executar(sinal: dict, balance: float) -> dict:
    symbol = sinal["symbol"]
    side   = sinal["side"]
    entry  = sinal["entry"]
    sl     = sinal["sl"]
    tp     = sinal["tp"]

    lots = calcular_lots(symbol, entry, sl, balance)
    if lots <= 0:
        return {"ok": False, "msg": "lots inválido"}

    info  = mt5.symbol_info(symbol)
    oType = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL

    req = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       symbol,
        "volume":       lots,
        "type":         oType,
        "price":        entry,
        "sl":           sl,
        "tp":           tp,
        "deviation":    20,
        "magic":        MAGIC,
        "comment":      "NEXUS-AUTO",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(req)

    # Fallback para FOK se IOC falhar
    if result.retcode not in (mt5.TRADE_RETCODE_DONE,):
        req["type_filling"] = mt5.ORDER_FILLING_FOK
        result = mt5.order_send(req)

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        return {"ok": True, "ticket": result.order, "lots": lots, "entry": entry}
    else:
        return {"ok": False, "msg": f"{result.retcode} — {result.comment}"}


# ── Breakeven ────────────────────────────────────────────────────────────────

def aplicar_breakeven():
    """Move SL para breakeven quando posição atingir 50% do TP."""
    posicoes = mt5.positions_get(magic=MAGIC)
    if not posicoes:
        return

    for p in posicoes:
        entry = p.price_open
        tp    = p.tp
        sl    = p.sl
        atual = mt5.symbol_info_tick(p.symbol)
        if not atual:
            continue

        price = atual.bid if p.type == 0 else atual.ask  # BUY usa bid para P&L

        if tp == 0 or sl == 0:
            continue

        dist_tp  = abs(tp - entry)
        dist_now = abs(price - entry)

        # 50% do caminho até o TP
        if dist_now >= dist_tp * 0.5 and abs(sl - entry) > 0.00001:
            novo_sl = round(entry, mt5.symbol_info(p.symbol).digits)
            req = {
                "action":   mt5.TRADE_ACTION_SLTP,
                "symbol":   p.symbol,
                "position": p.ticket,
                "sl":       novo_sl,
                "tp":       tp,
            }
            res = mt5.order_send(req)
            if res.retcode == mt5.TRADE_RETCODE_DONE:
                log.info(f"🔒 Breakeven: {p.symbol} #{p.ticket} → SL movido para {novo_sl}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("  NEXUS TRADER BOT — Iniciando sessão")
    log.info(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    log.info("=" * 60)

    # Conecta MT5
    if not mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        log.error(f"❌ MT5 não conectou: {mt5.last_error()}")
        return {"erro": "MT5 offline", "operacoes": []}

    acc     = mt5.account_info()
    balance = acc.balance
    equity  = acc.equity

    log.info(f"✅ MT5 | Conta: {acc.login} | Saldo: ${balance:,.2f} | Equity: ${equity:,.2f}")

    # Breakeven nas posições abertas
    aplicar_breakeven()

    resultado = {
        "data":        datetime.now(timezone.utc).isoformat(),
        "saldo":       balance,
        "equity":      equity,
        "operacoes":   [],
        "ignorados":   [],
    }

    # Verifica drawdown diário
    if checar_drawdown_diario(balance, equity):
        log.warning("🛑 Drawdown limite atingido — sem novas operações hoje.")
        mt5.shutdown()
        return resultado

    # Verifica se é sexta à noite
    if sexta_noite():
        log.info("📅 Sexta após 20:00 UTC — sem novas operações.")
        mt5.shutdown()
        return resultado

    # Verifica limite de posições
    abertas = contar_posicoes()
    slots   = MAX_POSITIONS - abertas
    log.info(f"📊 Posições abertas: {abertas}/{MAX_POSITIONS} | Slots disponíveis: {slots}")

    if slots <= 0:
        log.info("🔒 Limite de posições atingido — nenhuma nova ordem.")
        mt5.shutdown()
        return resultado

    # Analisa todos os símbolos
    sinais = []
    for symbol in SYMBOLS:
        sinal = analisar(symbol)
        if sinal:
            log.info(
                f"✅ Sinal: {sinal['side']:4} {symbol:<8} | "
                f"Entry: {sinal['entry']:.5f} | SL: {sinal['sl']:.5f} | "
                f"TP: {sinal['tp']:.5f} | RR: 1:{sinal['rr']}"
            )
            sinais.append(sinal)
        else:
            log.info(f"⏭  {symbol:<8} — sem sinal")
            resultado["ignorados"].append(symbol)

    if not sinais:
        log.info("📭 Nenhum sinal válido hoje.")
        mt5.shutdown()
        return resultado

    # Executa até preencher os slots disponíveis
    executados = 0
    for sinal in sinais:
        if executados >= slots:
            log.info(f"🔒 Slots preenchidos — {sinal['symbol']} aguarda próxima sessão.")
            break

        log.info(f"🚀 Executando {sinal['side']} {sinal['symbol']}...")
        res = executar(sinal, balance)

        if res["ok"]:
            log.info(
                f"  ✅ Aberto | Ticket #{res['ticket']} | "
                f"{res['lots']} lots @ {res['entry']:.5f}"
            )
            resultado["operacoes"].append({
                "symbol": sinal["symbol"],
                "side":   sinal["side"],
                "ticket": res["ticket"],
                "lots":   res["lots"],
                "entry":  res["entry"],
                "sl":     sinal["sl"],
                "tp":     sinal["tp"],
                "rr":     sinal["rr"],
            })
            executados += 1
        else:
            log.error(f"  ❌ Falha: {res['msg']}")

        time.sleep(0.5)

    # Resumo final
    log.info("-" * 60)
    log.info(f"  Sessão concluída | {executados} operação(ões) abertas")
    log.info(f"  Log salvo em: {log_file}")
    log.info("=" * 60)

    mt5.shutdown()
    return resultado


if __name__ == "__main__":
    resultado = main()

    # Dispara email se houver operações ou erros
    try:
        from nexus_notifier import enviar_email
        enviar_email(resultado)
    except Exception as e:
        log.warning(f"Email não enviado: {e}")
