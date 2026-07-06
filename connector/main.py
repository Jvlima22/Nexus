"""
NEXUS — connector/main.py
FastAPI bridge entre MetaTrader 5 (Python lib) e o frontend NEXUS.
Integra: pattern_engine, session_filter, trade_logger.

Endpoints REST:
  GET  /health
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
from contextlib import asynccontextmanager
from typing import Literal, Optional

import MetaTrader5 as mt5
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from pattern_engine import Candle, analyze, detect_patterns
from session_filter import check_session, next_allowed_session
from trade_logger import (
    log_signal,  # noqa: F401 — disponível para uso externo
    log_trade_close,
    log_trade_open,
    get_pattern_stats,
    get_session_summary,
)


# ---------------------------------------------------------------------------
# Configuração via .env
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    mt5_login: int = 0
    mt5_password: str = ""
    mt5_server: str = ""
    allowed_origins: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# ---------------------------------------------------------------------------
# Mapeamento de timeframes
# ---------------------------------------------------------------------------

TIMEFRAME_MAP: dict[str, int] = {
    "M1":  mt5.TIMEFRAME_M1,
    "M5":  mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1":  mt5.TIMEFRAME_H1,
    "H4":  mt5.TIMEFRAME_H4,
    "D1":  mt5.TIMEFRAME_D1,
}

# ---------------------------------------------------------------------------
# Estado global
# ---------------------------------------------------------------------------

_mt5_connected = False


# ---------------------------------------------------------------------------
# Lifespan: conectar / desconectar MT5
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _mt5_connected
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
            print(f"[MT5] Conectado — conta {info.login} | saldo ${info.balance:.2f}")
        else:
            print(f"[MT5] AVISO: não conectado — {mt5.last_error()}")
    except Exception as exc:
        print(f"[MT5] Erro na inicialização: {exc}")
        _mt5_connected = False

    yield

    mt5.shutdown()
    print("[MT5] Desconectado.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="NEXUS MT5 Connector", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers internos
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
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return {
        "ok": True,
        "mt5_connected": _mt5_connected,
        "mt5_error": str(mt5.last_error()) if not _mt5_connected else None,
    }


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
    candles = _mt5_candles(symbol, timeframe, count)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(candles),
        "candles": [
            {
                "time": c.time,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
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
    candles = _mt5_candles(symbol, timeframe, count)
    result = analyze(candles, symbol=symbol, timeframe=timeframe, atr_period=atr_period)
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
    candles = _mt5_candles(symbol, timeframe, count)
    signals = detect_patterns(candles)
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
def place_order(req: OrderRequest):
    """
    Executa ordem a mercado.
    Gate de risco: bloqueia se alavancagem implícita > 50× equity.
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

    if req.volume * contract_size * price_ask > acct.equity * 50:
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
        print(f"[trade_logger] Erro ao gravar abertura: {exc}")

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
        print(f"[trade_logger] Erro ao gravar fechamento: {exc}")

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
# WebSocket — streaming de vela ao vivo
# ---------------------------------------------------------------------------


@app.websocket("/ws/mt5/candles")
async def ws_candles(
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

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
