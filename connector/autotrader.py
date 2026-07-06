"""
Autotrader determinístico da NEXUS (Fase 7) — o robô que ocupa o lugar do par
OpenClaw+IA no laço de decisão, sem custo de token e 100% reproduzível.

Para cada ativo da watchlist, periodicamente:
  1. COLETA   — lê candles do timeframe primário (e do de confirmação).
  2. INTERPRETA — roda indicators.analyze() → sinal determinístico (direction,
                  confidence) a partir de RSI/EMA/MACD/Bollinger/estrutura.
  3. CONFLUÊNCIA — se ligada, só segue se primário e confirmação apontam a
                   mesma direção (usa a MENOR confiança das duas — conservador).
  4. DECIDE   — dimensiona o stake (% da banca) e manda pra orders.place_order().

O laço NÃO duplica nenhuma regra de risco: quem aprova/veta é o Risk Judge
(risk.evaluate, chamado dentro de orders.place_order). Confiança baixa/neutra,
fora de sessão, blackout de notícia, bias macro contrário, alocação, circuit
breaker e teto diário vetam sozinhos — cada veto já é auditado em `risk_events`.

Segurança: DESLIGADO por padrão (AUTOTRADER_ENABLED=false). Liga via env ou
POST /autotrader/toggle. Opera no modo da conta (PRACTICE até validar).
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone

import backtest
import indicators
import orders
import supabase_sync
from config import settings
from iq_client import client
from risk import RiskError

logger = logging.getLogger("nexus.autotrader")

_TF_LABEL = {60: "M1", 300: "M5", 900: "M15", 3600: "H1", 14400: "H4", 86400: "D1"}

# Códigos ISO 4217 de moeda (o que a IQ oferece em forex). Usado para separar PAR DE MOEDA
# (EURUSD, NZDCAD-OTC…) de cripto/ação/índice (LTCUSD, NVDA, US30…) na varredura.
_ISO_CCY = {
    "USD", "EUR", "JPY", "GBP", "AUD", "NZD", "CAD", "CHF", "CNY", "CNH", "HKD", "SGD",
    "SEK", "NOK", "DKK", "PLN", "HUF", "CZK", "RUB", "TRY", "ZAR", "MXN", "BRL", "INR",
    "IDR", "PHP", "THB", "VND", "MYR", "KRW", "TWD", "ILS", "AED", "SAR", "QAR", "CLP",
    "COP", "PEN", "RON", "ISK", "NGN", "KES", "EGP", "PKR", "BDT", "UAH", "KZT",
}


def _tf(size: int) -> str:
    return _TF_LABEL.get(size, f"{size}s")


def _is_currency_pair(symbol: str) -> bool:
    """True se o símbolo é um par de DUAS moedas ISO (aceita sufixo -OTC). Exclui
    cripto (LTCUSD), ação (NVDA), índice (US30) e compostos com '/'."""
    base = symbol.upper().split("-")[0]
    if len(base) != 6 or not base.isalpha():
        return False
    return base[:3] in _ISO_CCY and base[3:] in _ISO_CCY


def _is_otc(symbol: str) -> bool:
    """True se é um par OTC (preço sintético da corretora, provado random walk em 07/06)."""
    return symbol.upper().endswith("-OTC")


class _Autotrader:
    """Estado e laço do robô. Instância única (`engine`)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._enabled = settings.autotrader_enabled
        self._started = False
        # ativo → epoch até quando pular (posição aberta OU cooldown pós-decisão)
        self._hold_until: dict[str, float] = {}
        # ring buffer das últimas decisões (p/ o /autotrader/status e debug)
        self._log: deque[dict] = deque(maxlen=50)
        self._ticks = 0
        # cache da watchlist dinâmica (evita reconstruir/ler o Supabase a cada ciclo)
        self._watch_cache: list[str] = []
        self._watch_ts = 0.0
        # edge medido por símbolo (gate de evidência): symbol → linha do asset_edge.
        # Reatribuído inteiro a cada refresh (assignment atômico → leitura sem lock).
        self._edge: dict[str, dict] = {}

    # ── controle ────────────────────────────────────────────────────────────--
    def set_enabled(self, value: bool) -> bool:
        with self._lock:
            self._enabled = value
        logger.info("Autotrader %s", "LIGADO" if value else "DESLIGADO")
        return value

    @property
    def enabled(self) -> bool:
        return self._enabled

    def start(self) -> None:
        """Sobe o thread do laço. O laço respeita o flag `enabled` (default off)."""
        if self._started:
            return
        self._started = True
        # Carrega o último edge persistido → o gate já vale logo após um restart,
        # sem esperar o primeiro backtest (que só roda após o warmup).
        if settings.autotrader_edge_gate_enabled and supabase_sync.configured():
            try:
                self._edge = supabase_sync.get_asset_edge()
                logger.info("autotrader edge: %d pares carregados do Supabase", len(self._edge))
            except Exception:  # noqa: BLE001
                logger.exception("Falha ao carregar asset_edge no boot")
        threading.Thread(target=self._loop, daemon=True, name="autotrader").start()
        if settings.autotrader_edge_gate_enabled:
            threading.Thread(target=self._edge_loop, daemon=True, name="autotrader-edge").start()
        scope = (f"scan {settings.autotrader_universe} (payout≥{settings.autotrader_min_payout}, "
                 f"máx {settings.autotrader_max_assets})" if settings.autotrader_scan_open
                 else f"fixo {settings.autotrader_assets_list}")
        gate = (f"edge>{settings.autotrader_edge_min_hit:.0%}/{settings.autotrader_edge_min_sample}"
                if settings.autotrader_edge_gate_enabled else "OFF")
        logger.info(
            "Autotrader iniciado (enabled=%s, %s, %s/%s, confluência=%s, gate=%s, máx_aberto=%d, poll=%ss)",
            self._enabled, scope, _tf(settings.autotrader_timeframe),
            _tf(settings.autotrader_confirm_tf), settings.autotrader_require_confluence,
            gate, settings.autotrader_max_open, settings.autotrader_poll_s,
        )

    def status(self) -> dict:
        now = time.time()
        scan = settings.autotrader_scan_open
        watch = self._watch_cache if scan else settings.autotrader_assets_list
        edge = self._edge
        return {
            "enabled": self._enabled,
            "balance_mode": settings.iq_balance_mode,
            "scan_open": scan,
            "universe": settings.autotrader_universe if scan else "fixed",
            "exclude_otc": settings.autotrader_exclude_otc,
            "watchlist_count": len(watch),
            "assets": watch[:50],  # amostra (pode ser grande no modo dinâmico)
            "min_payout": settings.autotrader_min_payout,
            "max_open": settings.autotrader_max_open,
            "timeframe": _tf(settings.autotrader_timeframe),
            "confirm_timeframe": _tf(settings.autotrader_confirm_tf),
            "confluence": settings.autotrader_require_confluence,
            "poll_s": settings.autotrader_poll_s,
            "stake_pct": settings.risk_pct,
            "ticks": self._ticks,
            "edge_gate": settings.autotrader_edge_gate_enabled,
            "edge_min_hit": settings.autotrader_edge_min_hit,
            "edge_min_sample": settings.autotrader_edge_min_sample,
            "edge_measured_count": len(edge),
            "edge_enabled_count": sum(1 for e in edge.values() if e.get("passes_gate")),
            "edge": {s: self._edge_view(edge[s]) for s in watch[:50] if s in edge},
            "holding": {a: _iso(t) for a, t in self._hold_until.items() if t > now},
            "recent": list(self._log)[-15:],
        }

    @staticmethod
    def _edge_view(e: dict) -> dict:
        """Recorte do edge p/ o painel: a taxa/amostra que o gate de fato usa + veredito."""
        hit, sample = backtest.gate_metric(e)
        return {"hit_rate": hit, "sample": sample, "passes_gate": bool(e.get("passes_gate"))}

    # ── laço ────────────────────────────────────────────────────────────────--
    def _loop(self) -> None:
        while True:
            try:
                if self._enabled:
                    self._tick()
            except Exception:  # noqa: BLE001 — um erro no tick nunca derruba o laço
                logger.exception("Erro no tick do autotrader")
            time.sleep(settings.autotrader_poll_s)

    def _tick(self) -> None:
        if not supabase_sync.configured():
            self._record("error", None, detail="Supabase não configurado — laço inerte")
            return
        self._ticks += 1
        now = time.time()

        # Trava de risco: nº de posições abertas agora (verdade no Supabase).
        open_count = len(supabase_sync.get_open_nexus_trades())
        if open_count >= settings.autotrader_max_open:
            self._record("skip", None, detail=f"máx. {settings.autotrader_max_open} posições "
                                              f"abertas atingido ({open_count}) — aguardando fechar")
            return

        for asset in self._watchlist():
            if open_count >= settings.autotrader_max_open:
                break
            if self._hold_until.get(asset, 0) > now:
                continue  # posição aberta ou cooldown
            try:
                if self._evaluate(asset):  # True = abriu posição
                    open_count += 1
            except Exception:  # noqa: BLE001
                logger.exception("Falha ao avaliar %s", asset)
                self._record("error", asset, detail="exceção na avaliação")

    def _watchlist(self) -> list[str]:
        """Lista de ativos a varrer. Estática (AUTOTRADER_ASSETS) ou dinâmica: ativos
        abertos do Supabase, filtrados por tipo/payout/universo, ordenados por payout."""
        if not settings.autotrader_scan_open:
            return settings.autotrader_assets_list
        now = time.time()
        if self._watch_cache and now - self._watch_ts < settings.autotrader_assets_refresh_s:
            return self._watch_cache
        want = "digital" if settings.autotrader_option_type == "digital" else "binary"
        pool = [
            r for r in supabase_sync.get_open_assets()
            if r.get("type") == want and (r.get("payout") or 0) >= settings.autotrader_min_payout
        ]
        if settings.autotrader_universe == "currencies":
            pool = [r for r in pool if _is_currency_pair(r["symbol"])]
        if settings.autotrader_exclude_otc:
            pool = [r for r in pool if not _is_otc(r["symbol"])]
        pool.sort(key=lambda r: r.get("payout") or 0, reverse=True)
        syms = [r["symbol"] for r in pool[: settings.autotrader_max_assets]]
        self._watch_cache, self._watch_ts = syms, now
        logger.info("autotrader watchlist: %d ativos (universo=%s, payout≥%s)",
                    len(syms), settings.autotrader_universe, settings.autotrader_min_payout)
        return syms

    # ── gate de evidência (edge) ──────────────────────────────────────────────
    def _edge_loop(self) -> None:
        """Thread independente: backtesta a watchlist e mede o edge de cada par.
        Roda mesmo com o robô desligado — medir é read-only e deixa o gate pronto."""
        time.sleep(30)  # warmup: deixa a conexão IQ assentar antes do 1º backtest
        while True:
            try:
                if settings.autotrader_edge_gate_enabled and supabase_sync.configured():
                    self._refresh_edge()
            except Exception:  # noqa: BLE001 — erro de edge nunca derruba o thread
                logger.exception("Erro no loop de edge do autotrader")
            time.sleep(settings.autotrader_edge_refresh_s)

    def _refresh_edge(self) -> None:
        """Mede o edge de cada par da watchlist (backtest), persiste e atualiza o cache."""
        watch = self._watchlist()
        if not watch:
            return
        measured: dict[str, dict] = {}
        for sym in watch:
            try:
                edge = backtest.backtest_pair(sym)
            except Exception:  # noqa: BLE001
                logger.exception("Falha ao backtestar %s", sym)
                continue
            if not edge:
                continue
            edge["passes_gate"] = backtest.passes_gate(edge)
            measured[sym] = edge
        if not measured:
            return
        self._edge = {**self._edge, **measured}  # merge atômico (mantém pares ausentes)
        try:
            supabase_sync.upsert_asset_edge(list(measured.values()))
        except Exception:  # noqa: BLE001
            logger.exception("Falha ao persistir asset_edge")
        n_ok = sum(1 for e in measured.values() if e["passes_gate"])
        logger.info("autotrader edge: %d pares medidos, %d habilitados (acerto>%.0f%%, amostra≥%d)",
                    len(measured), n_ok, settings.autotrader_edge_min_hit * 100,
                    settings.autotrader_edge_min_sample)

    def _evaluate(self, asset: str) -> bool:
        """Avalia um ativo. Retorna True só quando ABRE uma posição (p/ a trava de máx.)."""
        # 0) gate de evidência: só opera par com edge MEDIDO acima do breakeven.
        #    Pré-filtro do autotrader (o Risk Judge segue só com regras universais).
        if settings.autotrader_edge_gate_enabled and not backtest.passes_gate(self._edge.get(asset)):
            self._record("skip", asset, detail=self._edge_skip_reason(asset))
            return False

        # 1+2) sinal do timeframe primário
        sig = self._signal(asset, settings.autotrader_timeframe)
        if sig["direction"] is None:
            self._record("skip", asset, detail=f"sem consenso em {sig['timeframe']}")
            return False

        # 2b) gate de regime: o robô é seguidor de tendência por confluência;
        #     chop lateral de baixa volatilidade é onde ele sangra → pula.
        if settings.autotrader_regime_gate_enabled:
            reg = sig.get("regime") or {}
            if not reg.get("suitable_for_trend", True):
                self._record(
                    "skip", asset, direction=sig["direction"],
                    detail=f"regime desfavorável ({reg.get('trend')}/vol {reg.get('volatility')}): "
                           f"{reg.get('recommend')}",
                )
                return False

        confidence = sig["confidence"]

        # 3) confluência: o timeframe de confirmação precisa concordar
        if settings.autotrader_require_confluence:
            conf = self._signal(asset, settings.autotrader_confirm_tf)
            if conf["direction"] != sig["direction"]:
                self._record(
                    "skip", asset, direction=sig["direction"],
                    detail=f"sem confluência ({sig['timeframe']}={sig['direction']} / "
                           f"{conf['timeframe']}={conf['direction']})",
                )
                return False
            confidence = min(confidence, conf["confidence"])  # conservador

        # 4) stake = % fixo da banca (espelha o teto do Risk Judge → não estoura)
        balance = client.get_balance()
        stake = round(balance * settings.risk_pct, 2)
        if stake <= 0:
            self._record("skip", asset, detail=f"banca insuficiente ({balance:.2f})")
            return False

        direction = sig["direction"]
        try:
            res = orders.place_order(
                asset, direction, stake, settings.autotrader_expiration_min,
                settings.autotrader_option_type, confidence,
            )
        except RiskError as exc:
            # Já auditado em risk_events pelo Risk Judge; cooldown evita re-vetar todo tick.
            self._hold(asset, settings.autotrader_cooldown_s)
            self._record("vetoed", asset, direction=direction, confidence=confidence,
                         detail=f"{exc.code}: {exc}")
            return False
        except (ValueError, RuntimeError) as exc:
            self._record("error", asset, direction=direction, detail=str(exc))
            return False

        # executou: segura o ativo até a ordem expirar + cooldown
        hold_s = settings.autotrader_expiration_min * 60 + settings.autotrader_cooldown_s
        self._hold(asset, hold_s)
        self._record("executed", asset, direction=direction, confidence=confidence,
                     detail=f"order={res['order_id']} stake={stake:.2f} payout={res.get('payout')}")
        logger.info("Autotrader executou %s %s %.2f (conf=%.2f)", asset, direction, stake, confidence)
        return True

    # ── helpers ───────────────────────────────────────────────────────────────
    def _signal(self, asset: str, size: int) -> dict:
        candles = client.get_candles(asset, size, settings.autotrader_candles)
        return indicators.analyze(asset, _tf(size), candles)

    def _hold(self, asset: str, seconds: float) -> None:
        self._hold_until[asset] = time.time() + seconds

    def _edge_skip_reason(self, asset: str) -> str:
        """Texto auditável do porquê o gate de evidência barrou o par."""
        e = self._edge.get(asset)
        if not e:
            return "sem edge medido ainda (aguardando 1º backtest)"
        hit, sample = backtest.gate_metric(e)
        if hit is None or sample < settings.autotrader_edge_min_sample:
            return f"amostra insuficiente ({sample} < {settings.autotrader_edge_min_sample})"
        return (f"edge {hit:.1%} ≤ mínimo {settings.autotrader_edge_min_hit:.0%} "
                f"({sample} sinais) — sem vantagem comprovada")

    def _record(self, action: str, asset: str | None, *, direction: str | None = None,
                confidence: float | None = None, detail: str = "") -> None:
        entry = {
            "time": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "asset": asset,
            "direction": direction,
            "confidence": confidence,
            "detail": detail,
        }
        self._log.append(entry)
        if action in ("executed", "vetoed", "error"):
            logger.info("autotrader[%s] %s: %s", action, asset, detail)


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


engine = _Autotrader()
