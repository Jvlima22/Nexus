"""
Wrapper resiliente sobre a API não-oficial da IQ Option (iqoptionapi).

Responsabilidades (Fase 1):
  - Obter o SSID (env em dev; endpoint do Worker em prod) e conectar via WS.
  - Manter a conexão viva: heartbeat + reconexão automática (SSID expira).
  - Expor leitura de ativos (open/payout) e candles.

ATENÇÃO: a lib iqoptionapi é um fork não-oficial; nomes de métodos podem variar
entre versões. Os pontos sensíveis estão marcados com [VERIFICAR-FORK].
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

import httpx

from config import settings

logger = logging.getLogger("nexus.iq")

# A lib iqoptionapi sobe um thread interno (__get_digital_open) que lê a chave
# 'underlying' antes de a lista digital carregar → KeyError repetido e inofensivo.
# Não dá pra try/except dentro do thread dela, então engolimos só esse erro
# específico via excepthook global (à prova de versão).
_prev_excepthook = threading.excepthook


def _silence_digital_keyerror(args: threading.ExceptHookArgs) -> None:  # type: ignore[name-defined]
    # Engole qualquer erro originado no thread interno __get_digital_open da lib
    # (KeyError 'underlying' OU TypeError quando a lista digital vem None).
    tb = args.exc_traceback
    while tb is not None:
        if "get_digital_open" in tb.tb_frame.f_code.co_name:
            return
        tb = tb.tb_next
    _prev_excepthook(args)


threading.excepthook = _silence_digital_keyerror

# Mapa interval (segundos) aceito pela IQ para candles.
VALID_CANDLE_SIZES = {1, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 14400, 86400}


class IQClient:
    """Sessão única com a IQ Option, protegida por lock para uso concorrente."""

    def __init__(self) -> None:
        self._iq: Any = None
        self._lock = threading.Lock()
        self._connected = False
        self._last_ok = 0.0

    # ── SSID ──────────────────────────────────────────────────────────────────
    def _resolve_ssid(self) -> str:
        """Dev: usa IQ_SSID. Prod: busca SSID decifrado no Worker do NEXUS."""
        if settings.iq_ssid:
            return settings.iq_ssid
        if settings.ssid_endpoint:
            resp = httpx.get(
                settings.ssid_endpoint,
                headers={"Authorization": f"Bearer {settings.ssid_token}"},
                timeout=10,
            )
            resp.raise_for_status()
            ssid = resp.json().get("ssid")
            if not ssid:
                raise RuntimeError("Worker não devolveu ssid")
            return ssid
        raise RuntimeError("Sem SSID: configure IQ_SSID ou SSID_ENDPOINT")

    # ── Conexão ─────────────────────────────────────────────────────────────--
    def connect(self) -> None:
        from iqoptionapi.stable_api import IQ_Option  # import tardio (lib pesada)

        with self._lock:
            if settings.iq_email and settings.iq_password:
                # Caminho confiável: a lib faz o login e gerencia o SSID sozinha.
                iq = IQ_Option(settings.iq_email, settings.iq_password)
                ok, reason = iq.connect()
            else:
                # Fallback best-effort por SSID (o fork não tem API pública estável
                # p/ injetar SSID; pode falhar conforme a versão).
                ssid = self._resolve_ssid()
                iq = IQ_Option("", "")
                iq.set_session({"User-Agent": "Mozilla/5.0"}, {"ssid": ssid})
                ok, reason = iq.connect()

            if not ok:
                raise RuntimeError(f"connect() falhou: {reason}")

            iq.change_balance(settings.iq_balance_mode)  # PRACTICE | REAL
            # Atualiza a tabela de actives (a embutida na lib é antiga e não tem
            # vários OTC/ativos novos → "not found on consts" ao pedir candles).
            try:
                iq.update_ACTIVES_OPCODE()
            except Exception:  # noqa: BLE001
                logger.debug("update_ACTIVES_OPCODE falhou (ignorado)")
            self._iq = iq
            self._connected = True
            self._last_ok = time.time()
            logger.info("IQ conectada (modo=%s)", settings.iq_balance_mode)
            self._warmup_digital(iq)

    @staticmethod
    def _warmup_digital(iq: Any, timeout_s: float = 8.0) -> None:
        """
        Pré-carrega a lista de ativos digitais. Sem isso, o thread interno
        __get_digital_open da lib lê a chave 'underlying' antes dela existir e
        cospe KeyError repetido (barulho inofensivo). Esperar a lista chegar
        silencia o thread e deixa os ativos digitais disponíveis em get_assets().
        """
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                data = iq.get_digital_underlying_list_data()
                if isinstance(data, dict) and "underlying" in data:
                    return
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.5)
        logger.warning("warm-up digital expirou; lista digital pode vir incompleta")

    def is_healthy(self) -> bool:
        iq = self._iq
        if iq is None:
            return False
        try:
            healthy = bool(iq.check_connect())
        except Exception:  # noqa: BLE001 — qualquer erro = não saudável
            healthy = False
        self._connected = healthy
        if healthy:
            self._last_ok = time.time()
        return healthy

    def ensure_connected(self) -> None:
        if not self.is_healthy():
            logger.warning("Conexão caiu — reconectando…")
            try:
                self.connect()
            except Exception:  # noqa: BLE001
                logger.exception("Falha ao reconectar")

    # ── Watchdog (heartbeat) ────────────────────────────────────────────────--
    def start_watchdog(self, interval_s: int = 30) -> None:
        def loop() -> None:
            while True:
                self.ensure_connected()
                time.sleep(interval_s)

        threading.Thread(target=loop, daemon=True, name="iq-watchdog").start()
        logger.info("Watchdog iniciado (cada %ss)", interval_s)

    # ── Leitura de dados ──────────────────────────────────────────────────────
    # Mapa kind da IQ → type aceito pela tabela `assets` (CHECK). Kinds fora daqui
    # são ignorados para não violar a constraint.
    _TYPE_MAP = {
        "turbo": "binary",
        "binary": "binary",
        "digital": "digital",
        "forex": "forex",
        "crypto": "crypto",
        "cryptocurrency": "crypto",
        "stock": "stock",
        "stocks": "stock",
        "commodity": "commodity",
        "commodities": "commodity",
    }

    def get_assets(self) -> list[dict[str, Any]]:
        """Ativos com estado aberto/fechado e payout, normalizados p/ a tabela `assets`."""
        self.ensure_connected()
        iq = self._iq
        open_times = iq.get_all_open_time()      # {'binary': {'EURUSD': {'open': True}, ...}, ...}
        profits = iq.get_all_profit()             # {'EURUSD': {'binary': 0.85, 'turbo': 0.85}}

        out: list[dict[str, Any]] = []
        for kind, actives in open_times.items():
            mapped = self._TYPE_MAP.get(kind)
            if mapped is None:
                continue
            for symbol, info in actives.items():
                payout = profits.get(symbol, {}).get(kind)
                out.append(
                    {
                        "symbol": symbol,
                        "type": mapped,
                        "is_open": bool(info.get("open")),
                        "payout": round(payout * 100, 2) if isinstance(payout, (int, float)) else None,
                    }
                )
        return out

    def get_candles(self, active: str, size: int, count: int, end_ts: int | None = None) -> list[dict[str, Any]]:
        """Histórico de candles. size em segundos (ver VALID_CANDLE_SIZES)."""
        if size not in VALID_CANDLE_SIZES:
            raise ValueError(f"size inválido: {size}")
        self.ensure_connected()
        iq = self._iq
        end_ts = end_ts or int(time.time())
        raw = iq.get_candles(active, size, count, end_ts)  # lista de dicts da IQ (ou None)
        if not raw:
            # Ativo sem série de candles (ex.: ação OTC fora da tabela da lib).
            raise ValueError(f"sem candles para '{active}' (ativo não tem série disponível)")
        return [self._norm_candle(c) for c in raw]

    @staticmethod
    def _norm_candle(c: dict[str, Any]) -> dict[str, Any]:
        """Normaliza para o formato do lightweight-charts (time em epoch s)."""
        return {
            "time": int(c["from"]),
            "open": c["open"],
            "high": c["max"],
            "low": c["min"],
            "close": c["close"],
            "volume": c.get("volume", 0),
        }

    # ── Streaming de candles ao vivo ────────────────────────────────────────--
    def start_candle_stream(self, active: str, size: int) -> None:
        if size not in VALID_CANDLE_SIZES:
            raise ValueError(f"size inválido: {size}")
        self.ensure_connected()
        # maxdict pequeno: só precisamos do candle em formação + alguns anteriores.
        self._iq.start_candles_stream(active, size, 10)

    def stop_candle_stream(self, active: str, size: int) -> None:
        if self._iq is not None:
            try:
                self._iq.stop_candles_stream(active, size)
            except Exception:  # noqa: BLE001
                logger.debug("stop_candles_stream falhou (ignorado)")

    def latest_candle(self, active: str, size: int) -> dict[str, Any] | None:
        """Candle mais recente (em formação) do stream ao vivo, já normalizado."""
        rt = self._iq.get_realtime_candles(active, size)
        if not rt:
            return None
        last_ts = max(rt.keys())
        return self._norm_candle(rt[last_ts])

    # ── Conta / ordens ──────────────────────────────────────────────────────--
    def get_balance(self) -> float:
        self.ensure_connected()
        return float(self._iq.get_balance())

    def get_payout(self, active: str, option_type: str) -> float | None:
        """Payout % atual do ativo (best-effort)."""
        try:
            profits = self._iq.get_all_profit().get(active, {})
            kind = "digital" if option_type == "digital" else "turbo"
            p = profits.get(kind) or profits.get("binary")
            return round(p * 100, 2) if isinstance(p, (int, float)) else None
        except Exception:  # noqa: BLE001
            return None

    def buy(self, active: str, direction: str, amount: float, expiration_min: int, option_type: str) -> Any:
        """Abre uma ordem. Retorna o order_id da IQ. Levanta erro se a IQ recusar."""
        self.ensure_connected()
        iq = self._iq
        if option_type == "digital":
            ok, order_id = iq.buy_digital_spot(active, amount, direction, expiration_min)
        else:
            ok, order_id = iq.buy(amount, active, direction, expiration_min)
        if not ok:
            raise RuntimeError(f"IQ recusou a ordem: {order_id}")
        return order_id

    @staticmethod
    def _status_from_pnl(pnl: float) -> str:
        if pnl > 0:
            return "win"
        if pnl < 0:
            return "loss"
        return "tie"

    def _symbol_for(self, active_id: Any) -> str | None:
        """active_id (int) → símbolo, via tabela de constantes da lib (atualizada no connect)."""
        try:
            from iqoptionapi.constants import ACTIVES  # name → id (mutável em runtime)

            for name, aid in ACTIVES.items():
                if aid == active_id:
                    return name
        except Exception:  # noqa: BLE001
            pass
        return None

    @staticmethod
    def _extract_positions(data: Any) -> list[dict[str, Any]]:
        if isinstance(data, tuple):
            data = data[1] if len(data) > 1 else (data[0] if data else None)
        if isinstance(data, dict):
            data = data.get("positions") or data.get("data") or []
        return data if isinstance(data, list) else []

    def _norm_position(self, p: dict[str, Any], instrument_type: str) -> dict[str, Any] | None:
        """Normaliza uma posição do histórico p/ as colunas de `trades`. Defensivo."""
        if not isinstance(p, dict):
            return None
        eid = p.get("external_id") or p.get("id")
        ids = p.get("raw_event", {}).get("order_ids") if isinstance(p.get("raw_event"), dict) else None
        if not eid and ids:
            eid = ids[0]
        if not eid:
            return None
        active_id = p.get("active_id") or p.get("instrument_active_id")
        symbol = self._symbol_for(active_id) or (str(active_id) if active_id else "?")
        direction = (p.get("instrument_dir") or p.get("direction") or "").lower()
        invest = p.get("invest") or p.get("amount") or p.get("buy_amount")
        pnl = p.get("pnl") or p.get("close_profit") or p.get("pnl_realized")
        reason = (p.get("close_reason") or p.get("status") or "").lower()
        status = {"win": "win", "loose": "loss", "equal": "tie"}.get(reason)
        return {
            "external_id": str(eid),
            "asset": symbol,
            "type": "Call" if direction == "call" else "Put" if direction == "put" else None,
            "amount": invest,
            "pnl": pnl,
            "status": status or "open",
            "option_type": "digital" if "digital" in instrument_type else "binary",
        }

    def get_position_history_raw(self, instrument_type: str, limit: int = 50) -> Any:
        """Saída crua do histórico (diagnóstico — o shape varia entre versões)."""
        self.ensure_connected()
        try:
            return self._iq.get_position_history_v2(instrument_type, limit, 0, 0, 0)
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)}

    def result_from_history(self, order_id: Any, option_type: str, limit: int = 50) -> tuple[str | None, float | None]:
        """
        Resultado de uma ordem via histórico de posições (independe da sessão —
        funciona p/ ordens órfãs de processos antigos). Casa o order_id contra
        external_id/id/raw_event.order_ids da posição.
        """
        self.ensure_connected()
        target = str(order_id)
        itypes = ["digital-option"] if option_type == "digital" else ["turbo-option", "binary-option"]
        for itype in itypes:
            try:
                data = self._iq.get_position_history_v2(itype, limit, 0, 0, 0)
            except Exception:  # noqa: BLE001
                continue
            for p in self._extract_positions(data):
                if not isinstance(p, dict):
                    continue
                cand: set[str] = set()
                for k in ("external_id", "id"):
                    if p.get(k) is not None:
                        cand.add(str(p[k]))
                raw = p.get("raw_event") if isinstance(p.get("raw_event"), dict) else {}
                for oid in (raw.get("order_ids") or p.get("order_ids") or []):
                    cand.add(str(oid))
                if target not in cand:
                    continue
                pnl = p.get("pnl") or p.get("pnl_realized") or p.get("close_profit")
                reason = str(p.get("close_reason") or p.get("status") or "").lower()
                status = {"win": "win", "loose": "loss", "loss": "loss", "equal": "tie"}.get(reason)
                if status is None and isinstance(pnl, (int, float)):
                    status = self._status_from_pnl(pnl)
                if status:
                    return status, (float(pnl) if isinstance(pnl, (int, float)) else None)
        return None, None

    def get_position_history(self, instrument_type: str, limit: int = 100) -> list[dict[str, Any]]:
        """Histórico de posições de um tipo (best-effort; formato da lib varia)."""
        self.ensure_connected()
        iq = self._iq
        try:
            data = iq.get_position_history_v2(instrument_type, limit, 0, 0, 0)
        except Exception:  # noqa: BLE001
            data = iq.get_position_history(instrument_type)
        out: list[dict[str, Any]] = []
        for p in self._extract_positions(data):
            norm = self._norm_position(p, instrument_type)
            if norm:
                out.append(norm)
        return out

    def check_result(self, order_id: Any, option_type: str) -> tuple[str | None, float | None]:
        """
        NÃO-bloqueante: resultado se a ordem já fechou, senão (None, None).
        Usado na reconciliação (ordens órfãs após restart). Defensivo quanto ao
        formato retornado pela lib entre versões.
        """
        self.ensure_connected()
        iq = self._iq
        try:
            oid = int(order_id)
        except (TypeError, ValueError):
            return None, None
        try:
            if option_type == "digital":
                closed, win = iq.check_win_digital_v2(oid)
                if not closed:
                    return None, None
                return self._status_from_pnl(float(win)), float(win)
            res = iq.check_win_v4(oid)
        except Exception:  # noqa: BLE001
            return None, None
        if not isinstance(res, (tuple, list)) or len(res) < 2:
            return None, None
        a, b = res[0], res[1]
        pnl = float(b) if isinstance(b, (int, float)) else None
        if isinstance(a, str):  # 'win' | 'loose' | 'equal'
            mapped = {"win": "win", "loose": "loss", "loss": "loss", "equal": "tie"}.get(a.lower())
            return (mapped, pnl) if mapped else (None, None)
        if a is True:  # fechado (bool) → status pelo PnL
            return (self._status_from_pnl(pnl) if pnl is not None else "tie"), pnl
        return None, None  # ainda aberta

    def wait_result(self, order_id: Any, option_type: str, timeout_s: int = 900) -> tuple[str, float | None]:
        """Bloqueia até a opção fechar e devolve (status, pnl). status: win|loss|tie."""
        self.ensure_connected()
        iq = self._iq
        if option_type == "digital":
            deadline = time.time() + timeout_s
            while time.time() < deadline:
                closed, win = iq.check_win_digital_v2(order_id)
                if closed:
                    return self._status_from_pnl(win), float(win)
                time.sleep(2)
            return "open", None  # timeout — tracker desiste, trade fica 'open'
        # Binário/turbo: check_win_v3 bloqueia até fechar e retorna o lucro.
        profit = iq.check_win_v3(order_id)
        return self._status_from_pnl(profit), float(profit)


# Instância única usada pelo app.
client = IQClient()
