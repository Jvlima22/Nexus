"""
NEXUS — connector/main.py
FastAPI bridge unificado: IQ Option (binário/digital) + MetaTrader 5 (forex real).

Um único processo, uma única porta (settings.port, default 8010 — a 8000 é do
próprio terminal MT5 nesta máquina) — os dois lados compartilham módulos
(risk.py, supabase_sync.py) mas operam de forma independente.

Endpoints REST (IQ Option):
  GET  /health
  GET  /assets
  GET  /candles?active=&size=&count=
  GET  /indicators?active=&size=&count=
  GET  /sentiment
  POST /order
  GET  /autotrader/status
  POST /autotrader/toggle
  GET  /vault/tree
  GET  /vault/file?path=
  POST /vault/note
  GET  /debug/positions?type=&limit=
  POST /reconcile
  POST /backfill
  WS   /ws/candles?active=&size=

Endpoints REST (MetaTrader 5):
  GET  /mt5/session
  GET  /mt5/account
  GET  /mt5/price?symbol=
  GET  /mt5/candles?symbol=&timeframe=&count=
  GET  /mt5/positions?symbol=
  GET  /mt5/analyze?symbol=&timeframe=&count=&atr_period=
  GET  /mt5/signal?symbol=&timeframe=&count=
  POST /mt5/order
  POST /mt5/close
  GET  /mt5/stats?symbol=&min_samples=
  GET  /mt5/summary?date=YYYY-MM-DD
  WS   /ws/mt5/candles?symbol=&timeframe=&interval=
"""

from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from contextlib import asynccontextmanager
from typing import Literal, Optional

import MetaTrader5 as mt5
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import autotrader
import indicators as indicators_mod
import orders
import risk
import supabase_sync
import sync
import vault
from config import settings
from iq_client import client
from pattern_engine import Candle, analyze, detect_patterns
from session_filter import check_session, next_allowed_session
from sync import start_asset_sync, start_balance_sync
from trade_logger import (
    log_signal,  # noqa: F401 — disponível para uso externo
    log_trade_close,
    log_trade_open,
    get_pattern_stats,
    get_session_summary,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("nexus.connector")

# ---------------------------------------------------------------------------
# Mapeamento de timeframes
# ---------------------------------------------------------------------------

# MT5: label (M1..D1) → constante da lib.
TIMEFRAME_MAP: dict[str, int] = {
    "M1":  mt5.TIMEFRAME_M1,
    "M5":  mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1":  mt5.TIMEFRAME_H1,
    "H4":  mt5.TIMEFRAME_H4,
    "D1":  mt5.TIMEFRAME_D1,
}

# IQ Option: segundos → label (o que indicators.analyze espera em `timeframe`).
_IQ_TF_LABEL: dict[int, str] = {60: "M1", 300: "M5", 900: "M15", 3600: "H1", 14400: "H4", 86400: "D1"}

# ---------------------------------------------------------------------------
# Guarda de timeout pra chamadas à IQ Option
# ---------------------------------------------------------------------------
# A lib iqoptionapi não tem timeout embutido: se a IQ não estiver conectada, uma
# chamada como client.get_assets() pode travar o processo inteiro por minutos.
# Roda em thread própria com prazo — se estourar, devolve 503 em vez de pendurar
# a requisição (a thread travada morre sozinha quando o processo reiniciar).
_iq_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="iq-call")


def _iq_call(fn, *args, timeout: float = 8.0, **kwargs) -> object:
    future = _iq_pool.submit(fn, *args, **kwargs)
    try:
        return future.result(timeout=timeout)
    except FutureTimeoutError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"IQ Option não respondeu em {timeout:.0f}s — provável desconexão.",
        ) from exc

# ---------------------------------------------------------------------------
# Estado global (MT5 — a IQ mantém o próprio estado em iq_client.client)
# ---------------------------------------------------------------------------

_mt5_connected = False


# ---------------------------------------------------------------------------
# Lifespan: conecta as duas corretoras + os loops de sync/autotrader
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _mt5_connected

    # ── IQ Option ──
    # connect() é síncrono e SEM timeout (a lib pode travar minutos se a rede/DNS
    # até a IQ estiver bloqueada) — roda em thread p/ nunca travar o boot do app
    # (MT5 e as demais rotas não podem ficar reféns da IQ). O watchdog reconecta.
    def _iq_connect_bg() -> None:
        try:
            client.connect()
        except Exception:  # noqa: BLE001 — não derruba o boot; watchdog tenta de novo
            logger.exception("IQ: conexão inicial falhou; watchdog vai reconectar")

    threading.Thread(target=_iq_connect_bg, daemon=True, name="iq-connect-boot").start()
    client.start_watchdog(interval_s=30)
    start_asset_sync(interval_s=30)
    start_balance_sync(interval_s=15)
    sync.start_reconcile_on_boot()  # fecha ordens órfãs de restarts anteriores
    autotrader.engine.start()

    # ── MetaTrader 5 ──
    try:
        if settings.mt5_login and settings.mt5_password and settings.mt5_server:
            ok = mt5.initialize(
                login=settings.mt5_login,
                password=settings.mt5_password,
                server=settings.mt5_server,
            )
        else:
            ok = mt5.initialize()

        _mt5_connected = ok
        if ok:
            info = mt5.account_info()
            logger.info("MT5 conectado — conta %s | saldo $%.2f", info.login, info.balance)
        else:
            logger.warning("MT5 não conectado — %s", mt5.last_error())
    except Exception:  # noqa: BLE001
        logger.exception("MT5: erro na inicialização")
        _mt5_connected = False

    yield

    mt5.shutdown()
    logger.info("MT5 desconectado.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="NEXUS Connector", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers internos (MT5)
# ---------------------------------------------------------------------------


def _require_mt5() -> None:
    if not _mt5_connected:
        raise HTTPException(status_code=503, detail="Terminal MT5 não conectado.")


def _mt5_candles(symbol: str, timeframe: str, count: int = 200) -> list[Candle]:
    _require_mt5()
    tf = TIMEFRAME_MAP.get(timeframe.upper())
    if tf is None:
        raise HTTPException(status_code=400, detail=f"Timeframe inválido: {timeframe}")

    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rates is None or len(rates) == 0:
        raise HTTPException(status_code=404, detail=f"Sem dados para {symbol} {timeframe}")

    return [
        Candle(
            time=int(r["time"]),
            open=float(r["open"]),
            high=float(r["high"]),
            low=float(r["low"]),
            close=float(r["close"]),
            volume=float(r["tick_volume"]),
        )
        for r in rates
    ]


# ---------------------------------------------------------------------------
# Modelos Pydantic
# ---------------------------------------------------------------------------


class OrderIn(BaseModel):
    active: str
    direction: str  # call | put
    amount: float
    expiration: int = 1  # minutos
    option_type: str = "binary"  # binary | digital


class NoteIn(BaseModel):
    path: str   # relativo ao vault; só 30_Trading/** ou 40_Registros/**
    content: str


class ToggleIn(BaseModel):
    enabled: bool


class OrderRequest(BaseModel):
    symbol: str = Field(..., example="EURUSD")
    direction: Literal["BUY", "SELL"]
    volume: float = Field(0.01, gt=0)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: str = "NEXUS"
    pattern: str = ""
    timeframe: str = "M5"
    ai_reasoning: str = ""
    signal_id: Optional[str] = None


class CloseRequest(BaseModel):
    position_id: int
    close_reason: Literal["tp", "sl", "manual"] = "manual"


# ---------------------------------------------------------------------------
# /health — estado das duas corretoras
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return {
        "ok": True,
        "iq_connected": client.is_healthy(),
        "mt5_connected": _mt5_connected,
        "mt5_error": str(mt5.last_error()) if not _mt5_connected else None,
    }


# ---------------------------------------------------------------------------
# IQ Option — ativos, candles, indicadores, sentimento, ordens, autotrader
# ---------------------------------------------------------------------------


@app.get("/assets")
def assets() -> dict[str, object]:
    try:
        data = _iq_call(client.get_assets)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"IQ indisponível: {exc}") from exc
    return {"count": len(data), "assets": data}


@app.get("/candles")
def candles(
    active: str = Query(..., description="Símbolo, ex: EURUSD"),
    size: int = Query(60, description="Timeframe em segundos"),
    count: int = Query(100, ge=1, le=1000),
) -> dict[str, object]:
    try:
        data = _iq_call(client.get_candles, active, size, count)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"IQ indisponível: {exc}") from exc
    return {"active": active, "size": size, "candles": data}


@app.get("/indicators")
def get_indicators(
    active: str = Query(..., description="Símbolo, ex: EURUSD"),
    size: int = Query(300, description="Timeframe em segundos"),
    count: int = Query(200, ge=1, le=1000),
) -> dict[str, object]:
    """Sinal determinístico (RSI/EMA/MACD/Bollinger/estrutura) — mesmo motor
    usado pelo autotrader (indicators.analyze), agora exposto pro dashboard."""
    try:
        candles_data = _iq_call(client.get_candles, active, size, count)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"IQ indisponível: {exc}") from exc
    tf_label = _IQ_TF_LABEL.get(size, f"{size}s")
    return indicators_mod.analyze(active, tf_label, candles_data)


@app.get("/sentiment")
def get_sentiment() -> dict[str, object]:
    """Sentimento macro agregado (Polymarket) — mesma leitura usada pelo Risk Judge."""
    try:
        markets = supabase_sync.get_sentiment()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Supabase: {exc}") from exc
    bulls = sum(1 for m in markets if m.get("bias") == "bullish")
    bears = sum(1 for m in markets if m.get("bias") == "bearish")
    macro_bias = "bullish" if bulls > bears else "bearish" if bears > bulls else "neutral"
    return {"count": len(markets), "macro_bias": macro_bias, "markets": markets}


@app.post("/order")
def place_order(order: OrderIn) -> dict[str, object]:
    """Executa uma ordem da NEXUS com gate de risco (Risk Judge) e grava em `trades`."""
    try:
        return orders.place_order(
            order.active, order.direction, order.amount, order.expiration, order.option_type
        )
    except orders.RiskError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha ao executar ordem")  # traceback completo no terminal
        raise HTTPException(status_code=502, detail=f"Falha ao executar ordem: {exc}") from exc


@app.get("/autotrader/status")
def autotrader_status() -> dict[str, object]:
    return autotrader.engine.status()


@app.post("/autotrader/toggle")
def autotrader_toggle(body: ToggleIn) -> dict[str, object]:
    return {"enabled": autotrader.engine.set_enabled(body.enabled)}


@app.get("/vault/tree")
def vault_tree() -> dict[str, object]:
    """Lista todos os .md do vault Obsidian (caminho, pasta, data)."""
    files = vault.list_tree()
    return {"count": len(files), "files": files}


@app.get("/vault/file")
def vault_file(path: str = Query(..., description="Caminho relativo do .md no vault")) -> dict[str, object]:
    try:
        return {"path": path, "content": vault.read_file(path)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Não encontrado: {path}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/vault/note")
def vault_note(note: NoteIn) -> dict[str, object]:
    """Escreve um .md no vault (usado pelo agente OpenClaw para gravar análises).
    Sandbox + allowlist de subpasta em vault.write_note."""
    try:
        return {"ok": True, **vault.write_note(note.path, note.content)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/debug/positions")
def debug_positions(
    instrument_type: str = Query("binary-option", alias="type", description="turbo-option|binary-option|digital-option"),
    limit: int = Query(5, ge=1, le=50),
) -> dict[str, object]:
    """Diagnóstico: shape cru do histórico de posições da lib."""
    raw = _iq_call(client.get_position_history_raw, instrument_type, limit)
    positions = client._extract_positions(raw)  # noqa: SLF001
    return {
        "type": instrument_type,
        "count": len(positions),
        "sample": positions[:2],
        "raw_type": raw.__class__.__name__,
        "raw_keys": list(raw.keys()) if isinstance(raw, dict) else None,
    }


@app.post("/reconcile")
def reconcile() -> dict[str, object]:
    """Fecha ordens 'open' órfãs consultando o resultado na IQ. Retorna os valores."""
    try:
        return {"ok": True, **sync.reconcile_open_trades()}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha na reconciliação")
        raise HTTPException(status_code=502, detail=f"Falha na reconciliação: {exc}") from exc


@app.post("/backfill")
def backfill() -> dict[str, object]:
    """Importa operações passadas da IQ → trades (source='manual'). Rodar uma vez."""
    try:
        n = sync.backfill_history()
        return {"ok": True, "imported": n}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha no backfill")
        raise HTTPException(status_code=502, detail=f"Falha no backfill: {exc}") from exc


@app.websocket("/ws/candles")
async def ws_candles_iq(ws: WebSocket, active: str, size: int = 60) -> None:
    """
    Stream do candle em formação (IQ Option). O front carrega o histórico via
    GET /candles e depois assina aqui para atualizar o último candle ao vivo.

    Nota: o stream é por (active,size) e compartilhado — com 1 usuário tudo bem;
    multi-cliente no mesmo par exigiria refcount (Fase futura).
    """
    await ws.accept()
    try:
        client.start_candle_stream(active, size)
    except Exception as exc:  # noqa: BLE001
        await ws.send_json({"error": f"stream falhou: {exc}"})
        await ws.close()
        return

    try:
        while True:
            candle = client.latest_candle(active, size)
            if candle:
                await ws.send_json(candle)
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("Erro no stream de candles (IQ)")
    finally:
        client.stop_candle_stream(active, size)


# ---------------------------------------------------------------------------
# MetaTrader 5 — sessão, conta, candles, sinais, ordens
# ---------------------------------------------------------------------------


@app.get("/mt5/session")
def session_status():
    status = check_session()
    return {
        "allowed": status.allowed,
        "session": status.session,
        "utc_hour": status.utc_hour,
        "reason": status.reason,
        "best_pairs": status.best_pairs,
        "next_session": next_allowed_session() if not status.allowed else None,
    }


@app.get("/mt5/account")
def account_info():
    _require_mt5()
    info = mt5.account_info()
    if info is None:
        raise HTTPException(status_code=502, detail="Falha ao obter dados da conta.")
    return {
        "login": info.login,
        "name": info.name,
        "server": info.server,
        "balance": info.balance,
        "equity": info.equity,
        "margin": info.margin,
        "free_margin": info.margin_free,
        "margin_level": info.margin_level,
        "profit": info.profit,
        "leverage": info.leverage,
        "currency": info.currency,
    }


@app.get("/mt5/price")
def symbol_price(symbol: str = "EURUSD"):
    _require_mt5()
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise HTTPException(status_code=404, detail=f"Símbolo não encontrado: {symbol}")
    return {
        "symbol": symbol,
        "bid": tick.bid,
        "ask": tick.ask,
        "spread_pips": round((tick.ask - tick.bid) * 10000, 2),
        "time": tick.time,
    }


@app.get("/mt5/candles")
def get_candles(symbol: str = "EURUSD", timeframe: str = "M5", count: int = 200):
    candles_data = _mt5_candles(symbol, timeframe, count)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(candles_data),
        "candles": [
            {
                "time": c.time,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles_data
        ],
    }


@app.get("/mt5/positions")
def get_positions(symbol: Optional[str] = None):
    _require_mt5()
    positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
    if positions is None:
        return {"positions": []}
    return {
        "positions": [
            {
                "ticket": p.ticket,
                "symbol": p.symbol,
                "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                "volume": p.volume,
                "open_price": p.price_open,
                "current_price": p.price_current,
                "sl": p.sl,
                "tp": p.tp,
                "profit": p.profit,
                "comment": p.comment,
                "time": p.time,
            }
            for p in positions
        ]
    }


@app.get("/mt5/analyze")
def analyze_market(
    symbol: str = "EURUSD",
    timeframe: str = "M5",
    count: int = 200,
    atr_period: int = 14,
):
    candles_data = _mt5_candles(symbol, timeframe, count)
    result = analyze(candles_data, symbol=symbol, timeframe=timeframe, atr_period=atr_period)
    session = check_session()
    result["session"] = {
        "allowed": session.allowed,
        "name": session.session,
        "reason": session.reason,
    }
    return result


@app.get("/mt5/signal")
def best_signal(
    symbol: str = "EURUSD",
    timeframe: str = "M5",
    count: int = 200,
):
    candles_data = _mt5_candles(symbol, timeframe, count)
    signals = detect_patterns(candles_data)
    session = check_session()

    if not signals:
        return {
            "signal": None,
            "session": session.session,
            "session_allowed": session.allowed,
            "message": "Nenhum padrão detectado.",
        }

    best = max(signals, key=lambda s: s.strength)
    return {
        "signal": {
            "pattern": best.pattern,
            "direction": best.direction,
            "strength": best.strength,
            "entry": best.entry,
            "stop_loss": best.stop_loss,
            "take_profit": best.take_profit,
            "rr_ratio": best.rr_ratio,
            "description": best.description,
            "tags": best.tags,
        },
        "session": session.session,
        "session_allowed": session.allowed,
        "session_reason": session.reason,
        "total_signals": len(signals),
    }


@app.post("/mt5/order")
def place_mt5_order(req: OrderRequest):
    """
    Executa ordem a mercado.
    Gate de risco: Risk Judge unificado (connector/risk.py) quando há stop_loss
    (risco monetário = distância ao SL, igual ao usado pelo MT5 real). Sem
    stop_loss, cai no gate antigo de alavancagem (máx 50× equity).
    Grava entrada no Supabase via trade_logger.
    """
    _require_mt5()

    acct = mt5.account_info()
    tick = mt5.symbol_info_tick(req.symbol)
    if tick is None:
        raise HTTPException(status_code=404, detail=f"Símbolo não encontrado: {req.symbol}")

    sym_info = mt5.symbol_info(req.symbol)
    contract_size = getattr(sym_info, "trade_contract_size", 100_000) if sym_info else 100_000
    price_ask = tick.ask
    bias_direction = "call" if req.direction == "BUY" else "put"

    if req.stop_loss and sym_info and sym_info.trade_tick_size:
        sl_dist = abs(price_ask - req.stop_loss)
        monetary_risk = (sl_dist / sym_info.trade_tick_size) * sym_info.trade_tick_value * req.volume
        try:
            risk.evaluate(
                req.symbol, bias_direction, monetary_risk, None,
                balance=acct.balance, source="nexus_mt5",
                margin_level=acct.margin_level, enforce_session=False,
            )
        except risk.RiskError as exc:
            raise HTTPException(status_code=400, detail=f"{exc.code}: {exc}")
    elif req.volume * contract_size * price_ask > acct.equity * 50:
        raise HTTPException(
            status_code=400,
            detail=f"Volume {req.volume} excede gate de risco (máx 50× equity).",
        )

    order_type = mt5.ORDER_TYPE_BUY if req.direction == "BUY" else mt5.ORDER_TYPE_SELL
    price = tick.ask if req.direction == "BUY" else tick.bid

    req_dict: dict = {
        "action":      mt5.TRADE_ACTION_DEAL,
        "symbol":      req.symbol,
        "volume":      req.volume,
        "type":        order_type,
        "price":       price,
        "deviation":   20,
        "magic":       202600,
        "comment":     req.comment,
        "type_time":   mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    if req.stop_loss:
        req_dict["sl"] = req.stop_loss
    if req.take_profit:
        req_dict["tp"] = req.take_profit

    result = mt5.order_send(req_dict)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        retcode = result.retcode if result else -1
        msg = result.comment if result else str(mt5.last_error())
        raise HTTPException(status_code=502, detail=f"Ordem rejeitada [{retcode}]: {msg}")

    session = check_session()
    trade_id: Optional[str] = None
    try:
        trade_id = log_trade_open(
            signal_id=req.signal_id,
            position_id=result.order,
            symbol=req.symbol,
            direction=req.direction,
            volume=req.volume,
            entry_price=result.price,
            stop_loss=req.stop_loss or 0.0,
            take_profit=req.take_profit or 0.0,
            timeframe=req.timeframe,
            pattern=req.pattern,
            session=session.session,  # type: ignore[arg-type]
            ai_reasoning=req.ai_reasoning,
        )
    except Exception as exc:
        logger.warning("trade_logger: erro ao gravar abertura: %s", exc)

    return {
        "ok": True,
        "position_id": result.order,
        "symbol": req.symbol,
        "direction": req.direction,
        "volume": req.volume,
        "price": result.price,
        "trade_id": trade_id,
    }


@app.post("/mt5/close")
def close_position(req: CloseRequest):
    _require_mt5()

    positions = mt5.positions_get(ticket=req.position_id)
    if not positions:
        raise HTTPException(status_code=404, detail=f"Posição {req.position_id} não encontrada.")

    pos = positions[0]
    close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    tick = mt5.symbol_info_tick(pos.symbol)
    price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask

    result = mt5.order_send({
        "action":      mt5.TRADE_ACTION_DEAL,
        "symbol":      pos.symbol,
        "volume":      pos.volume,
        "type":        close_type,
        "position":    pos.ticket,
        "price":       price,
        "deviation":   20,
        "magic":       202600,
        "comment":     f"NEXUS_CLOSE_{req.close_reason}",
        "type_time":   mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    })

    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        retcode = result.retcode if result else -1
        msg = result.comment if result else str(mt5.last_error())
        raise HTTPException(status_code=502, detail=f"Falha ao fechar [{retcode}]: {msg}")

    pnl = pos.profit
    try:
        log_trade_close(
            position_id=req.position_id,
            close_price=result.price,
            pnl=pnl,
            close_reason=req.close_reason,
        )
    except Exception as exc:
        logger.warning("trade_logger: erro ao gravar fechamento: %s", exc)

    return {
        "ok": True,
        "position_id": req.position_id,
        "close_price": result.price,
        "pnl": pnl,
        "close_reason": req.close_reason,
    }


@app.get("/mt5/stats")
def pattern_stats(symbol: str = "EURUSD", min_samples: int = 3):
    try:
        stats = get_pattern_stats(symbol=symbol, min_samples=min_samples)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Supabase: {exc}")
    return {"symbol": symbol, "stats": stats}


@app.get("/mt5/summary")
def session_summary(date: str):
    try:
        summary = get_session_summary(date_str=date)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Supabase: {exc}")
    return summary


# ---------------------------------------------------------------------------
# WebSocket — streaming de vela ao vivo (MT5)
# ---------------------------------------------------------------------------


@app.websocket("/ws/mt5/candles")
async def ws_candles_mt5(
    websocket: WebSocket,
    symbol: str = "EURUSD",
    timeframe: str = "M1",
    interval: float = 1.0,
):
    await websocket.accept()

    if not _mt5_connected:
        await websocket.send_json({"error": "MT5 não conectado"})
        await websocket.close()
        return

    tf = TIMEFRAME_MAP.get(timeframe.upper())
    if tf is None:
        await websocket.send_json({"error": f"Timeframe inválido: {timeframe}"})
        await websocket.close()
        return

    try:
        while True:
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, 1)
            if rates is not None and len(rates) > 0:
                r = rates[0]
                await websocket.send_json({
                    "symbol":    symbol,
                    "timeframe": timeframe,
                    "time":      int(r["time"]),
                    "open":      float(r["open"]),
                    "high":      float(r["high"]),
                    "low":       float(r["low"]),
                    "close":     float(r["close"]),
                    "volume":    float(r["tick_volume"]),
                })
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"error": str(exc)})
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Entrypoint local
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=False)
