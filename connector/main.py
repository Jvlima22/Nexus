"""
NEXUS Connector — serviço HTTP/WS que faz a ponte com a IQ Option.

Fase 1 (atual): GET /health, GET /assets, GET /candles + watchdog de conexão.
Fase 2+: WS de candles ao vivo; loops de sync para Supabase (assets/trades/saldo).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import asyncio

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import orders
import sync
import vault
from config import settings
from iq_client import client
from sync import start_asset_sync, start_balance_sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("nexus.connector")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    try:
        client.connect()
    except Exception:  # noqa: BLE001 — não derruba o boot; watchdog tenta de novo
        logger.exception("Conexão inicial falhou; watchdog vai reconectar")
    client.start_watchdog(interval_s=30)
    start_asset_sync(interval_s=30)
    start_balance_sync(interval_s=15)
    sync.start_reconcile_on_boot()  # fecha ordens órfãs de restarts anteriores
    yield


app = FastAPI(title="NEXUS Connector", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class OrderIn(BaseModel):
    active: str
    direction: str  # call | put
    amount: float
    expiration: int = 1  # minutos
    option_type: str = "binary"  # binary | digital


@app.get("/health")
def health() -> dict[str, object]:
    """Endpoint do keep-alive (cron externo bate aqui a cada ~10 min no Render Free)."""
    return {"ok": True, "iq_connected": client.is_healthy()}


@app.get("/assets")
def assets() -> dict[str, object]:
    try:
        data = client.get_assets()
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
        data = client.get_candles(active, size, count)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"IQ indisponível: {exc}") from exc
    return {"active": active, "size": size, "candles": data}


@app.post("/order")
def place_order(order: OrderIn) -> dict[str, object]:
    """Executa uma ordem da NEXUS com gate de risco 2% e grava em `trades`."""
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


class NoteIn(BaseModel):
    path: str   # relativo ao vault; só 30_Trading/** ou 40_Registros/**
    content: str


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
    raw = client.get_position_history_raw(instrument_type, limit)
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
async def ws_candles(ws: WebSocket, active: str, size: int = 60) -> None:
    """
    Stream do candle em formação. O front carrega o histórico via GET /candles e
    depois assina aqui para atualizar o último candle ao vivo.

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
        logger.exception("Erro no stream de candles")
    finally:
        client.stop_candle_stream(active, size)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=False)
