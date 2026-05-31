"""Configuração do Connector, carregada de variáveis de ambiente / .env."""
from __future__ import annotations

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

    # Supabase (Fases 3-5)
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    nexus_user_id: str = ""

    # Vault Obsidian servido na página Knowledge. Vazio = <repo>/NEXUS (ao lado de connector/).
    vault_path: str = ""

    port: int = 8000
    allowed_origins: str = "http://localhost:3000"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
