#!/usr/bin/env python3
"""
NEXUS Trader — Executor de Ordens MT5
Análise H1 | 30/Jun/2026
Risco: 2% por operação (padrão NEXUS)
"""

import sys
import time
from datetime import datetime

# ── Instala MetaTrader5 se não tiver ────────────────────────────────────────
try:
    import MetaTrader5 as mt5
except ImportError:
    print("Instalando MetaTrader5...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "MetaTrader5"])
    import MetaTrader5 as mt5

# ── CONFIG ───────────────────────────────────────────────────────────────────
LOGIN    = 108960873
PASSWORD = "H_3vClCm"
SERVER   = "MetaQuotes-Demo"
RISK_PCT = 0.02   # 2% por trade
MIN_LOTS = 0.01
MAX_LOTS = 10.0
MAGIC    = 20260630

# ── ORDENS (análise H1 30/Jun/2026) ──────────────────────────────────────────
ORDERS = [
    # Análise H1 atualizada — 30/Jun/2026 ~17:30 UTC
    # Breakout das 17:00 UTC confirmado; consolidação em andamento
    {"symbol": "EURUSD", "side": "BUY",  "sl": 1.1393, "tp": 1.1458},  # suporte 1.1415, TP acima da máxima de 17:00
    {"symbol": "GBPUSD", "side": "BUY",  "sl": 1.3222, "tp": 1.3298},  # pullback para 1.3250, estrutura bullish mantida
    {"symbol": "USDJPY", "side": "BUY",  "sl": 162.20, "tp": 163.10},  # SL ajustado — exaustão leve no topo
    {"symbol": "USDCHF", "side": "SELL", "sl": 0.8095, "tp": 0.8050},  # bounce de 0.8063 mas ainda abaixo do pré-spike
    {"symbol": "AUDUSD", "side": "BUY",  "sl": 0.6895, "tp": 0.6960},  # recuperando de 0.6909, breakout 17:00 válido
    {"symbol": "NZDUSD", "side": "BUY",  "sl": 0.5655, "tp": 0.5715},  # consolidando 0.5673-0.5680 pós-spike
    {"symbol": "USDCAD", "side": "SELL", "sl": 1.4235, "tp": 1.4140},  # lower high em 1.4226, bearish de curto prazo
    {"symbol": "EURJPY", "side": "BUY",  "sl": 185.15, "tp": 186.50},  # spike 64 pips às 17:00, consolidando 185.65-185.79
    {"symbol": "GBPJPY", "side": "BUY",  "sl": 215.00, "tp": 216.60},  # uptrend mais forte da sessão (+220 pips)
    {"symbol": "XAUUSD", "side": "BUY",  "sl": 3978.00, "tp": 4065.00}, # SL acima de 3975 (low 08:00), TP abaixo do spike de 17:00
]

# ─────────────────────────────────────────────────────────────────────────────

def conectar():
    if not mt5.initialize(login=LOGIN, password=PASSWORD, server=SERVER):
        print(f"❌ Falha na conexão: {mt5.last_error()}")
        return False
    acc = mt5.account_info()
    print(f"✅ Conectado | Conta: {acc.login} | Saldo: ${acc.balance:,.2f} | Leverage: 1:{acc.leverage}")
    return True


def calcular_lots(symbol, price, sl_price):
    """Volume baseado em 2% de risco da conta."""
    info = mt5.symbol_info(symbol)
    if not info:
        return MIN_LOTS

    tick_value = info.trade_tick_value  # USD por tick, por lote
    tick_size  = info.trade_tick_size

    if tick_size == 0 or tick_value == 0:
        return MIN_LOTS

    sl_dist   = abs(price - sl_price)
    ticks_sl  = sl_dist / tick_size
    risco_lot = ticks_sl * tick_value

    if risco_lot == 0:
        return MIN_LOTS

    acc       = mt5.account_info()
    risco_usd = acc.balance * RISK_PCT
    lots      = risco_usd / risco_lot
    step      = info.volume_step
    lots      = round(round(lots / step) * step, 2)
    lots      = max(MIN_LOTS, min(MAX_LOTS, lots))
    return lots


def preview_ordens():
    """Mostra tabela com parâmetros antes de executar."""
    print(f"\n{'─'*72}")
    print(f"  {'#':<3} {'Par':<8} {'Side':<5} {'Price':<10} {'SL':<10} {'TP':<10} {'Lots':<6} {'RR'}")
    print(f"{'─'*72}")

    dados = []
    for i, o in enumerate(ORDERS, 1):
        sym  = o["symbol"]
        side = o["side"]
        sl   = o["sl"]
        tp   = o["tp"]

        mt5.symbol_select(sym, True)
        tick  = mt5.symbol_info_tick(sym)
        if not tick:
            print(f"  {i:<3} {sym:<8} SEM COTAÇÃO")
            dados.append(None)
            continue

        price = tick.ask if side == "BUY" else tick.bid
        lots  = calcular_lots(sym, price, sl)
        rr    = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0

        print(f"  {i:<3} {sym:<8} {side:<5} {price:<10.5f} {sl:<10.5f} {tp:<10.5f} {lots:<6} 1:{rr:.1f}")
        dados.append({"price": price, "lots": lots, **o})

    print(f"{'─'*72}")
    return dados


def executar_ordem(dados):
    sym  = dados["symbol"]
    side = dados["side"]

    order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL

    req = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       sym,
        "volume":       dados["lots"],
        "type":         order_type,
        "price":        dados["price"],
        "sl":           dados["sl"],
        "tp":           dados["tp"],
        "deviation":    20,
        "magic":        MAGIC,
        "comment":      "NEXUS-H1",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(req)

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"  ✅ {side} {sym} | {dados['lots']} lots @ {dados['price']:.5f} | ticket #{result.order}")
        return True
    else:
        # Tenta FOK se IOC falhou
        req["type_filling"] = mt5.ORDER_FILLING_FOK
        result2 = mt5.order_send(req)
        if result2.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"  ✅ {side} {sym} | {dados['lots']} lots @ {dados['price']:.5f} | ticket #{result2.order}")
            return True
        print(f"  ❌ {sym}: {result.retcode} — {result.comment}")
        return False


def resumo_posicoes():
    posicoes = mt5.positions_get(magic=MAGIC)
    if not posicoes:
        print("\n  Nenhuma posição aberta com MAGIC NEXUS.")
        return
    print(f"\n📊 Posições abertas ({len(posicoes)}):")
    print(f"  {'Par':<8} {'Side':<5} {'Lots':<6} {'Preço Abertura':<16} {'P&L'}")
    print(f"  {'─'*55}")
    total_pl = 0
    for p in posicoes:
        side = "BUY" if p.type == 0 else "SELL"
        print(f"  {p.symbol:<8} {side:<5} {p.volume:<6} {p.price_open:<16.5f} ${p.profit:+.2f}")
        total_pl += p.profit
    print(f"  {'─'*55}")
    print(f"  {'P&L Total:':<40} ${total_pl:+.2f}")


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print(f"  NEXUS TRADER — Execução de Ordens H1")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Risco: {RISK_PCT*100:.0f}% por trade")
    print("=" * 72)

    if not conectar():
        input("\nPressione Enter para sair...")
        return

    # Preview
    print(f"\n⚠️  PREVIEW — {len(ORDERS)} ordens a executar:")
    dados_ordens = preview_ordens()

    if any(d is None for d in dados_ordens):
        print("\n⚠️  Alguns símbolos sem cotação. Verifique se o MT5 está com mercado aberto.")

    # Confirmação
    print(f"\n❓ Confirma execução das {len([d for d in dados_ordens if d])} ordens acima? (s/N): ", end="")
    resp = input().strip().lower()

    if resp != "s":
        print("Execução cancelada.")
        mt5.shutdown()
        return

    # Executa
    print(f"\n🚀 Executando ordens...\n")
    ok = erro = 0
    for i, dados in enumerate(dados_ordens, 1):
        if dados is None:
            erro += 1
            continue
        print(f"[{i:02d}/{len(ORDERS)}] ", end="")
        if executar_ordem(dados):
            ok += 1
        else:
            erro += 1
        time.sleep(0.3)

    print(f"\n{'='*72}")
    print(f"  Resultado: {ok} executadas | {erro} erros")
    print("=" * 72)

    resumo_posicoes()
    mt5.shutdown()

    input("\nPressione Enter para fechar...")


if __name__ == "__main__":
    main()
