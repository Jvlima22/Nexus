"""Configuração do Connector, carregada de variáveis de ambiente / .env."""
from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Login: email+senha é o caminho confiável no fork iqoptionapi (ele gerencia o
    # SSID internamente). SSID é fallback best-effort.
    iq_email: str = ""
    iq_password: str = ""
    iq_ssid: str = ""
    ssid_endpoint: str = ""
    ssid_token: str = ""

    iq_balance_mode: str = "PRACTICE"  # PRACTICE | REAL

    # ── MetaTrader 5 — terminal local (mesma máquina do connector) ──
    mt5_login: int = 0
    mt5_password: str = ""
    mt5_server: str = ""

    # ── Risk Judge (Fase 3): o juiz inegociável por onde todo sinal passa ──
    risk_pct: float = 0.02                # alocação máx. por operação (% da banca)
    min_confidence: float = 0.70          # confiança mínima do sinal p/ executar
    neutral_low: float = 0.40             # zona de incerteza: bloqueia o trade
    neutral_high: float = 0.60
    max_consecutive_losses: int = 3       # circuit breaker: stops seguidos
    daily_loss_cap_pct: float = 0.06      # teto de prejuízo no dia (% da banca)
    # Gate de margem (broker com margem, ex. MT5): veta novas entradas se o
    # margin_level cair abaixo disso. Só roda quando o chamador informa margin_level.
    min_margin_level_pct: float = 150.0

    # ── Polymarket (Fase 4): sentimento macro = filtro primário de direção ──
    # CSV de slugs de mercados da Gamma a monitorar. Vazio = camada desligada.
    polymarket_slugs: str = ""
    polymarket_poll_s: int = 120          # intervalo do loop de sentimento (s)
    polymarket_bull_threshold: float = 0.65  # prob YES ≥ → bullish
    polymarket_bear_threshold: float = 0.35  # prob YES ≤ → bearish
    # Veta ordens que contrariam o bias macro? (regra 0 do Risk Judge)
    polymarket_gate_enabled: bool = True

    # ── Sessões de mercado (Fase 5): só opera nas janelas de maior liquidez ──
    # Veta ordens fora das sessões de Londres/NY (horários em UTC). false = 24h.
    session_gate_enabled: bool = True
    session_london_start: int = 8   # UTC (Londres ~08:00–17:00)
    session_london_end: int = 17
    session_ny_start: int = 13      # UTC (Nova York ~13:00–22:00)
    session_ny_end: int = 22

    # ── Calendário ForexFactory (Fase 6): blackout em notícias de alto impacto ──
    calendar_gate_enabled: bool = True
    calendar_poll_s: int = 1800            # recarrega o feed a cada 30 min
    calendar_blackout_before_min: int = 15  # janela antes do evento
    calendar_blackout_after_min: int = 15   # janela depois do evento
    # Níveis de impacto que disparam blackout (CSV). Ex: "High" ou "High,Medium".
    calendar_impacts: str = "High"

    # ── Autotrader (Fase 7): robô determinístico que substitui o laço OpenClaw+IA ──
    # Liga o laço autônomo. DESLIGADO por padrão — kill switch. Opera no modo da
    # conta (IQ_BALANCE_MODE); deixe em PRACTICE até validar.
    autotrader_enabled: bool = False
    # Descoberta dinâmica: varre os ativos ABERTOS (lidos do Supabase, alimentado pelo
    # asset-sync) em vez da lista fixa. False = usa AUTOTRADER_ASSETS.
    autotrader_scan_open: bool = True
    autotrader_universe: str = "currencies"  # currencies (só pares de moeda) | all
    # OTC provado random walk (07/06, 3 frentes) → fora da watchlist por padrão. O robô
    # mira forex REAL em pregão; em fim de semana (só OTC aberto) a watchlist fica vazia.
    autotrader_exclude_otc: bool = True
    autotrader_min_payout: float = 70.0    # ignora ativos com payout abaixo disso (%)
    autotrader_max_assets: int = 30        # teto de ativos avaliados por ciclo (perf)
    autotrader_assets_refresh_s: int = 300  # TTL do cache da watchlist (s)
    autotrader_max_open: int = 3           # máx. posições abertas ao mesmo tempo (trava de risco)
    autotrader_assets: str = "EURUSD"     # watchlist fixa (fallback quando scan_open=false)
    autotrader_timeframe: int = 300        # timeframe primário do sinal (s) — M5
    autotrader_confirm_tf: int = 900       # timeframe de confirmação (s) — M15
    autotrader_require_confluence: bool = True  # só opera se os 2 TFs concordam
    # Gate de regime (prompt #4): pula ambientes que não favorecem o seguidor de
    # tendência (chop lateral de baixa vol). Lê regime.suitable_for_trend do sinal.
    autotrader_regime_gate_enabled: bool = True
    autotrader_poll_s: int = 60            # intervalo do laço de decisão (s)
    autotrader_candles: int = 200          # nº de candles puxados por análise
    autotrader_expiration_min: int = 5     # expiração das ordens (min)
    autotrader_option_type: str = "binary"  # binary | digital
    autotrader_cooldown_s: int = 300       # espera no ativo após executar/vetar

    # ── Gate de evidência (Robô OTC v2): só opera par com edge MEDIDO > breakeven ──
    # Pré-filtro do autotrader (não é regra do Risk Judge — ver decisão da Fase 8).
    # O loop de edge backtesta cada par da watchlist e persiste em `asset_edge`;
    # o robô só avalia pares cujo acerto medido supere o limite com amostra mínima.
    autotrader_edge_gate_enabled: bool = True
    autotrader_edge_min_hit: float = 0.57   # acerto mínimo p/ habilitar o par (breakeven+margem)
    autotrader_edge_min_sample: int = 250   # amostra mínima de sinais p/ confiar na taxa
    autotrader_edge_use_confluence: bool = True  # medir o recorte com confluência (o que o robô opera)
    autotrader_edge_refresh_s: int = 21600  # recalcula o edge a cada 6h (backtest é pesado)

    # Supabase (Fases 3-5)
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    nexus_user_id: str = ""

    # Vault Obsidian servido na página Knowledge. Vazio = <repo>/NEXUS (ao lado de connector/).
    vault_path: str = ""

    # 8000 é usado pelo terminal MT5 nesta máquina — connector sobe em outra porta.
    port: int = 8010
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def polymarket_slugs_list(self) -> list[str]:
        return [s.strip() for s in self.polymarket_slugs.split(",") if s.strip()]

    @property
    def calendar_impacts_list(self) -> list[str]:
        return [s.strip().capitalize() for s in self.calendar_impacts.split(",") if s.strip()]

    @property
    def autotrader_assets_list(self) -> list[str]:
        return [s.strip() for s in self.autotrader_assets.split(",") if s.strip()]

    # Painéis (ex.: Render) às vezes deixam passar espaço/quebra-linha ao colar um
    # secret. Um espaço no NEXUS_USER_ID quebra o filtro UUID do Supabase (22P02).
    @field_validator(
        "nexus_user_id", "supabase_url", "supabase_service_role_key",
        "iq_email", "iq_ssid", mode="after",
    )
    @classmethod
    def _strip_env(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


settings = Settings()
