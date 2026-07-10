#!/usr/bin/env python3
"""
NEXUS Trader Bot 24h
Loop continuo — verifica a cada 5 min, opera quando vela H1 fecha
Auto-start com Windows | 10 posicoes maximas | Risco 2% por trade
"""

import sys, time, logging, os
from datetime import datetime, timezone, date
from pathlib import Path
from collections import defaultdict

def _probe(pkg: str) -> None:
    if pkg == "python-dotenv":
        __import__("dotenv")
    elif pkg == "supabase":
        # "import supabase" sozinho é enganado pela pasta supabase/ (migrations
        # SQL) na raiz do projeto, que o Python trata como namespace package —
        # precisa checar o símbolo real que usamos.
        from supabase import create_client  # noqa: F401
    else:
        __import__(pkg)


for pkg in ["MetaTrader5", "python-dotenv", "supabase"]:
    try:
        _probe(pkg)
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

import MetaTrader5 as mt5
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")
# connector/.env tem SUPABASE_SERVICE_ROLE_KEY + NEXUS_USER_ID + os tunings do Risk
# Judge (RISK_PCT, MIN_CONFIDENCE, ...). Carrega ANTES de importar risk (que lê
# connector.config.settings no import) — assim funciona com qualquer cwd de onde
# este script for lançado. override=False: se a raiz já definiu a mesma chave, ela vence.
load_dotenv(BASE_DIR / "connector" / ".env", override=False)

# connector/ tem o Risk Judge (risk.py) — mesmo juiz que audita o lado IQ Option,
# agora agnóstico de corretora (ver connector/risk.py).
sys.path.insert(0, str(BASE_DIR / "connector"))
import risk  # noqa: E402 — precisa do sys.path e do load_dotenv acima

MT5_LOGIN     = int(os.getenv("MT5_LOGIN", "108960873"))
MT5_PASSWORD  = os.getenv("MT5_PASSWORD", "H_3vClCm")
MT5_SERVER    = os.getenv("MT5_SERVER", "MetaQuotes-Demo")
NEXUS_USER_ID = os.getenv("NEXUS_USER_ID", "")

RISK_PCT        = 0.02
MAX_POSITIONS   = 10
MAX_DD_DAY_PCT  = 0.06    # 6% drawdown max diario (mais agressivo com 10 pos)
MIN_RR          = 1.2
MAGIC           = 20260701
CHECK_INTERVAL  = 300     # 5 minutos entre verificacoes
DAILY_EMAIL_UTC = 22      # hora UTC do email diario de resumo

SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
    "AUDUSD", "NZDUSD", "USDCAD",
    "EURJPY", "GBPJPY", "XAUUSD",
]

# ── Logging rotativo ──────────────────────────────────────────────────────────
LOG_PATH = BASE_DIR / "logs"
LOG_PATH.mkdir(exist_ok=True)

def criar_logger():
    nome = f"nexus_24h_{datetime.now().strftime('%Y%m%d')}.log"
    logger = logging.getLogger("NEXUS24H")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh = logging.FileHandler(LOG_PATH / nome, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger

log = criar_logger()

# ── Supabase ──────────────────────────────────────────────────────────────────

def _supabase():
    """Retorna cliente Supabase ou None se credenciais ausentes."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    from supabase import create_client
    return create_client(url, key)


def _detect_session(utc_hour: int) -> str:
    if 22 <= utc_hour or utc_hour < 7:  return "asian"
    if 7  <= utc_hour < 12:             return "london"
    if 12 <= utc_hour < 16:             return "overlap"
    if 16 <= utc_hour < 21:             return "new_york"
    return "off"


def sb_log_open(sinal: dict, ticket: int, lots: float) -> None:
    """Insere trade aberto no Supabase."""
    try:
        sb = _supabase()
        if not sb:
            return
        now = datetime.now(timezone.utc).isoformat()
        sb.table("trades").insert({
            "user_id":      NEXUS_USER_ID,
            "created_at":   now,
            "time":         now,
            "source":       "nexus_mt5",
            "position_id":  str(ticket),
            "symbol":       sinal["symbol"],
            "asset":        sinal["symbol"],
            "direction":    sinal["side"],
            "type":         sinal["side"],          # compatibilidade frontend
            "volume":       lots,
            "entry_price":  sinal["entry"],
            "stop_loss":    sinal["sl"],
            "take_profit":  sinal["tp"],
            "status":       "open",
            "timeframe":    "H1",
            "pattern":      "EMA20/50",
            "session":      _detect_session(datetime.now(timezone.utc).hour),
            "magic":        MAGIC,
        }).execute()
    except Exception as e:
        log.warning(f"Supabase open log falhou: {e}")


def sb_log_account_snapshot(acc) -> None:
    """Snapshot de conta (balance/equity/margin_level) em bankroll_history — alimenta
    o card de conta MT5 e o gráfico de evolução na Visão Geral (source='nexus_mt5')."""
    try:
        sb = _supabase()
        if not sb:
            return
        sb.table("bankroll_history").insert({
            "user_id":      NEXUS_USER_ID,
            "balance":      acc.balance,
            "equity":       acc.equity,
            "margin_level": acc.margin_level,
            "currency":     "USD",
            "account_type": "real",
            "source":       "nexus_mt5",
            "timestamp":    datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        log.warning(f"Supabase account snapshot falhou: {e}")


def sb_log_close(position_id: int, close_price: float, pnl: float, reason: str) -> None:
    """Atualiza trade fechado no Supabase."""
    try:
        sb = _supabase()
        if not sb:
            return
        now    = datetime.now(timezone.utc).isoformat()
        result = "win" if pnl > 0 else "loss"
        sb.table("trades").update({
            "status":       "closed",
            "result":       pnl,
            "close_price":  close_price,
            "pnl":          pnl,
            "close_reason": reason,
            "closed_at":    now,
        }).eq("user_id", NEXUS_USER_ID).eq("position_id", str(position_id)).execute()
    except Exception as e:
        log.warning(f"Supabase close log falhou: {e}")


# ── Estado global ─────────────────────────────────────────────────────────────
ultimo_candle: dict[str, datetime] = {}   # ultima vela H1 processada por simbolo
email_enviado_hoje: set[date]      = set()
saldo_abertura_dia: float          = 0.0
dia_atual: date                    = date.today()
posicoes_abertas: dict[int, dict]  = {}   # ticket → dados da posição para detectar fechamentos

# ── Indicadores ───────────────────────────────────────────────────────────────

def ema(prices: list, period: int) -> float:
    if len(prices) < period:
        return prices[-1]
    k   = 2.0 / (period + 1)
    val = sum(prices[:period]) / period
    for p in prices[period:]:
        val = p * k + val * (1 - k)
    return val

def avg_volume(volumes: list, lookback: int = 10) -> float:
    subset = volumes[-lookback - 1:-1]
    return sum(subset) / len(subset) if subset else 0

# ── Conexao MT5 ───────────────────────────────────────────────────────────────

def conectar() -> bool:
    if mt5.terminal_info() is not None:
        return True
    ok = mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
    if ok:
        acc = mt5.account_info()
        log.info(f"MT5 conectado | Conta: {acc.login} | Saldo: ${acc.balance:,.2f}")
    else:
        log.error(f"MT5 falhou: {mt5.last_error()}")
    return ok

# ── Mercado fechado ───────────────────────────────────────────────────────────

def mercado_fechado() -> bool:
    """Forex fecha sexta 22:00 UTC e abre domingo 22:00 UTC."""
    now = datetime.now(timezone.utc)
    wd  = now.weekday()
    # Sabado inteiro + Domingo antes das 22:00 + Sexta apos 21:59
    if wd == 5:
        return True
    if wd == 6 and now.hour < 22:
        return True
    if wd == 4 and now.hour >= 22:
        return True
    return False

# ── Nova vela H1 ──────────────────────────────────────────────────────────────

def nova_vela_h1(symbol: str) -> bool:
    """True se fechou uma vela H1 que ainda nao processamos."""
    candles = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 1, 1)
    if candles is None or len(candles) == 0:
        return False
    ts = datetime.fromtimestamp(candles[0]["time"], tz=timezone.utc)
    if ultimo_candle.get(symbol) != ts:
        ultimo_candle[symbol] = ts
        return True
    return False

# ── Analise de sinal ──────────────────────────────────────────────────────────

def analisar(symbol: str) -> dict | None:
    mt5.symbol_select(symbol, True)

    h4 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 56)
    if h4 is None or len(h4) < 55:
        return None

    closes_h4 = [c["close"] for c in h4]
    ema20_h4  = ema(closes_h4, 20)
    ema50_h4  = ema(closes_h4, 50)

    if   ema20_h4 > ema50_h4: trend = "BUY"
    elif ema20_h4 < ema50_h4: trend = "SELL"
    else: return None

    h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 26)
    if h1 is None or len(h1) < 22:
        return None

    closes_h1 = [c["close"] for c in h1]
    volumes   = [c["tick_volume"] for c in h1]
    ema20_h1  = ema(closes_h1, 20)

    last_close = closes_h1[-2]
    last_vol   = volumes[-2]
    avg_vol    = avg_volume(volumes)

    if trend == "BUY"  and last_close <= ema20_h1: return None
    if trend == "SELL" and last_close >= ema20_h1: return None
    if avg_vol > 0 and last_vol < avg_vol * 0.85:  return None

    info = mt5.symbol_info(symbol)
    if not info: return None

    pip     = info.point * 10
    recent  = h1[-6:-1]
    tick    = mt5.symbol_info_tick(symbol)
    if not tick: return None

    if trend == "BUY":
        entry = tick.ask
        sl    = min(c["low"] for c in recent) - pip * 2
        dist  = entry - sl
        if dist <= 0: return None
        tp    = entry + dist * MIN_RR
    else:
        entry = tick.bid
        sl    = max(c["high"] for c in recent) + pip * 2
        dist  = sl - entry
        if dist <= 0: return None
        tp    = entry - dist * MIN_RR

    return {
        "symbol": symbol, "side": trend,
        "entry": entry,
        "sl": round(sl, info.digits),
        "tp": round(tp, info.digits),
        "rr": round(abs(tp - entry) / dist, 2),
    }

# ── Gerenciamento de risco ────────────────────────────────────────────────────

def calcular_lots(symbol: str, entry: float, sl: float, balance: float) -> float:
    info = mt5.symbol_info(symbol)
    if not info: return 0.01
    sl_dist  = abs(entry - sl)
    tick_val = info.trade_tick_value
    tick_sz  = info.trade_tick_size
    if tick_sz == 0 or tick_val == 0: return 0.01
    risco_lot = (sl_dist / tick_sz) * tick_val
    if risco_lot == 0: return 0.01
    lots = (balance * RISK_PCT) / risco_lot
    step = info.volume_step
    lots = round(round(lots / step) * step, 2)
    return max(info.volume_min, min(info.volume_max, lots))

def risco_monetario(symbol: str, entry: float, sl: float, lots: float) -> float:
    """Risco em $ da posição (distância ao SL × valor do tick × lotes) — o `amount`
    que o Risk Judge audita contra o teto de 2% da banca."""
    info = mt5.symbol_info(symbol)
    if not info or not info.trade_tick_size or not info.trade_tick_value:
        return 0.0
    dist = abs(entry - sl)
    return (dist / info.trade_tick_size) * info.trade_tick_value * lots


def ja_tem_posicao(symbol: str) -> bool:
    pos = mt5.positions_get(symbol=symbol)
    if not pos: return False
    return any(p.magic == MAGIC for p in pos)

def contar_posicoes() -> int:
    pos = mt5.positions_get(magic=MAGIC)
    return len(pos) if pos else 0

def checar_drawdown(balance: float, equity: float) -> bool:
    if balance == 0: return False
    dd = (balance - equity) / balance
    if dd >= MAX_DD_DAY_PCT:
        log.error(f"DRAWDOWN LIMITE: {dd*100:.1f}% >= {MAX_DD_DAY_PCT*100:.0f}% — pausando operacoes")
        return True
    return False

# ── Execucao ──────────────────────────────────────────────────────────────────

def executar(sinal: dict, balance: float) -> dict:
    symbol = sinal["symbol"]
    lots   = calcular_lots(symbol, sinal["entry"], sinal["sl"], balance)
    oType  = mt5.ORDER_TYPE_BUY if sinal["side"] == "BUY" else mt5.ORDER_TYPE_SELL

    for filling in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK):
        req = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       symbol,
            "volume":       lots,
            "type":         oType,
            "price":        sinal["entry"],
            "sl":           sinal["sl"],
            "tp":           sinal["tp"],
            "deviation":    20,
            "magic":        MAGIC,
            "comment":      "NEXUS-24H",
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": filling,
        }
        res = mt5.order_send(req)
        if res.retcode == mt5.TRADE_RETCODE_DONE:
            return {"ok": True, "ticket": res.order, "lots": lots}

    return {"ok": False, "msg": f"{res.retcode} — {res.comment}"}

# ── Deteccao de fechamentos ───────────────────────────────────────────────────

def _detectar_fechamentos() -> None:
    """
    Compara posicoes abertas agora com o snapshot anterior.
    Qualquer ticket que sumiu foi fechado — busca no historico de deals para pegar
    close_price, pnl e motivo, depois loga no Supabase.
    """
    global posicoes_abertas

    atuais_raw = mt5.positions_get(magic=MAGIC) or []
    atuais     = {p.ticket: p for p in atuais_raw}

    # Tickets que existiam antes mas nao existem mais = fechados
    fechados = set(posicoes_abertas.keys()) - set(atuais.keys())

    for ticket in fechados:
        # Busca o deal de saida nos ultimos 30 dias
        from datetime import timedelta
        deals = mt5.history_deals_get(
            datetime.now(timezone.utc) - timedelta(days=30),
            datetime.now(timezone.utc),
            position=ticket,
        )
        pnl         = 0.0
        close_price = 0.0
        reason      = "manual"

        if deals:
            # O deal de saida e o ultimo com entry_type=1 (DEAL_ENTRY_OUT)
            saidas = [d for d in deals if d.entry == mt5.DEAL_ENTRY_OUT]
            if saidas:
                d           = saidas[-1]
                pnl         = d.profit
                close_price = d.price
                # Detecta motivo pelo comment do deal
                comment     = (d.comment or "").lower()
                if "tp" in comment or "take profit" in comment:
                    reason = "tp"
                elif "sl" in comment or "stop loss" in comment:
                    reason = "sl"

        log.info(f"FECHADO #{ticket} | PnL: ${pnl:.2f} | Motivo: {reason}")
        sb_log_close(ticket, close_price, pnl, reason)

    # Atualiza snapshot
    posicoes_abertas = {p.ticket: {"symbol": p.symbol, "entry": p.price_open} for p in atuais_raw}


# ── Breakeven ─────────────────────────────────────────────────────────────────

def aplicar_breakeven():
    pos = mt5.positions_get(magic=MAGIC)
    if not pos: return
    for p in pos:
        if p.tp == 0 or p.sl == 0: continue
        tick = mt5.symbol_info_tick(p.symbol)
        if not tick: continue
        price    = tick.bid if p.type == 0 else tick.ask
        dist_tp  = abs(p.tp - p.price_open)
        dist_now = abs(price - p.price_open)
        if dist_now >= dist_tp * 0.5:
            novo_sl = round(p.price_open, mt5.symbol_info(p.symbol).digits)
            if (p.type == 0 and novo_sl > p.sl) or (p.type == 1 and novo_sl < p.sl):
                req = {
                    "action":   mt5.TRADE_ACTION_SLTP,
                    "symbol":   p.symbol,
                    "position": p.ticket,
                    "sl":       novo_sl,
                    "tp":       p.tp,
                }
                res = mt5.order_send(req)
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    log.info(f"BREAKEVEN {p.symbol} #{p.ticket} SL->{novo_sl}")

# ── Trailing Stop (bonus) ─────────────────────────────────────────────────────

def aplicar_trailing(pip_trail: float = 15):
    """Trail de 15 pips quando posicao esta no lucro."""
    pos = mt5.positions_get(magic=MAGIC)
    if not pos: return
    for p in pos:
        info = mt5.symbol_info(p.symbol)
        if not info: continue
        pip   = info.point * 10
        trail = pip * pip_trail
        tick  = mt5.symbol_info_tick(p.symbol)
        if not tick: continue

        if p.type == 0:  # BUY
            novo_sl = round(tick.bid - trail, info.digits)
            if novo_sl > p.sl and novo_sl > p.price_open:
                mt5.order_send({
                    "action": mt5.TRADE_ACTION_SLTP, "symbol": p.symbol,
                    "position": p.ticket, "sl": novo_sl, "tp": p.tp,
                })
        else:  # SELL
            novo_sl = round(tick.ask + trail, info.digits)
            if novo_sl < p.sl and novo_sl < p.price_open:
                mt5.order_send({
                    "action": mt5.TRADE_ACTION_SLTP, "symbol": p.symbol,
                    "position": p.ticket, "sl": novo_sl, "tp": p.tp,
                })

# ── Email diario ──────────────────────────────────────────────────────────────

def enviar_email_diario(acc):
    global email_enviado_hoje
    hoje = date.today()
    if hoje in email_enviado_hoje:
        return
    now_utc = datetime.now(timezone.utc)
    if now_utc.hour < DAILY_EMAIL_UTC:
        return

    try:
        from nexus_notifier import enviar_email
        pos = mt5.positions_get(magic=MAGIC) or []
        ops = [
            {
                "symbol": p.symbol,
                "side":   "BUY" if p.type == 0 else "SELL",
                "lots":   p.volume,
                "entry":  p.price_open,
                "sl":     p.sl,
                "tp":     p.tp,
                "rr":     0,
                "ticket": p.ticket,
            }
            for p in pos
        ]
        resultado = {
            "data":      now_utc.isoformat(),
            "saldo":     acc.balance,
            "equity":    acc.equity,
            "operacoes": ops,
            "ignorados": [],
        }
        enviar_email(resultado)
        email_enviado_hoje.add(hoje)
        log.info("Email diario enviado")
    except Exception as e:
        log.warning(f"Email falhou: {e}")

# ── Ciclo principal ───────────────────────────────────────────────────────────

def ciclo():
    global saldo_abertura_dia, dia_atual, log

    if not conectar():
        return

    acc    = mt5.account_info()
    hoje   = date.today()

    sb_log_account_snapshot(acc)

    # Reseta saldo de abertura no novo dia
    if hoje != dia_atual:
        dia_atual          = hoje
        saldo_abertura_dia = acc.balance
        log = criar_logger()   # novo arquivo de log
        log.info(f"Novo dia: {hoje} | Saldo abertura: ${saldo_abertura_dia:,.2f}")

    if saldo_abertura_dia == 0:
        saldo_abertura_dia = acc.balance

    # Detecta posicoes fechadas desde o ultimo ciclo e loga no Supabase
    _detectar_fechamentos()

    # Gestao das posicoes abertas
    aplicar_breakeven()
    aplicar_trailing()

    # Email diario
    enviar_email_diario(acc)

    # Sem trading no fim de semana
    if mercado_fechado():
        log.info("Mercado fechado (fim de semana) — aguardando...")
        return

    # Drawdown diario
    if checar_drawdown(saldo_abertura_dia, acc.equity):
        return

    # Slots disponiveis
    abertas = contar_posicoes()
    slots   = MAX_POSITIONS - abertas
    if slots <= 0:
        return

    # Analisa apenas simbolos com nova vela H1
    novos_sinais = []
    for symbol in SYMBOLS:
        if not nova_vela_h1(symbol):
            continue
        if ja_tem_posicao(symbol):
            log.info(f"{symbol}: ja tem posicao aberta")
            continue
        sinal = analisar(symbol)
        if sinal:
            log.info(
                f"SINAL {sinal['side']} {symbol} | "
                f"Entry:{sinal['entry']:.5f} SL:{sinal['sl']:.5f} "
                f"TP:{sinal['tp']:.5f} RR:1:{sinal['rr']}"
            )
            novos_sinais.append(sinal)

    # Executa ate preencher slots
    executados = 0
    for sinal in novos_sinais:
        if executados >= slots:
            break

        # ── Risk Judge (unificado com o lado IQ Option): circuit breaker, teto
        # diario, gate de margem, blackout de noticia e bias macro (Polymarket).
        # Sessao (Londres/NY) fica desligada aqui: o bot MT5 opera 24h por decisao.
        lots_estimados = calcular_lots(sinal["symbol"], sinal["entry"], sinal["sl"], acc.balance)
        risco = risco_monetario(sinal["symbol"], sinal["entry"], sinal["sl"], lots_estimados)
        bias = "call" if sinal["side"] == "BUY" else "put"
        try:
            risk.evaluate(
                sinal["symbol"], bias, risco, None,
                balance=acc.balance, source="nexus_mt5",
                margin_level=acc.margin_level, enforce_session=False,
            )
        except risk.RiskError as exc:
            log.warning(f"VETADO {sinal['symbol']}: {exc.code} — {exc}")
            continue
        except Exception as exc:
            # Falha inesperada no Risk Judge (ex: Supabase indisponível) — trata
            # como veto por seguranca: melhor pular um sinal do que operar sem
            # o juiz ter confirmado circuit breaker/teto diario/margem.
            log.error(f"Risk Judge falhou p/ {sinal['symbol']} (tratando como veto): {exc}")
            continue

        res = executar(sinal, acc.balance)
        if res["ok"]:
            log.info(f"ABERTO #{res['ticket']} {sinal['side']} {sinal['symbol']} {res['lots']} lots")
            sb_log_open(sinal, res["ticket"], res["lots"])
            executados += 1
        else:
            log.error(f"FALHA {sinal['symbol']}: {res['msg']}")
        time.sleep(0.3)

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("  NEXUS TRADER BOT 24H — Iniciado")
    log.info(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    log.info(f"  Max posicoes: {MAX_POSITIONS} | Risco: {RISK_PCT*100:.0f}% | DD max: {MAX_DD_DAY_PCT*100:.0f}%")
    log.info("=" * 60)

    falhas_consecutivas = 0

    while True:
        try:
            ciclo()
            falhas_consecutivas = 0
        except Exception as e:
            falhas_consecutivas += 1
            log.error(f"Erro no ciclo ({falhas_consecutivas}x): {e}", exc_info=True)
            if falhas_consecutivas >= 5:
                log.error("5 falhas consecutivas — reiniciando MT5...")
                try:
                    mt5.shutdown()
                except Exception:
                    pass
                falhas_consecutivas = 0
                time.sleep(60)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
