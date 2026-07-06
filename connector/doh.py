"""
DNS-over-HTTPS (Cloudflare) para hosts bloqueados pelo DNS do provedor.

Alguns provedores no Brasil forjam NXDOMAIN para polymarket.com. Em vez de exigir
troca de DNS no SO, resolvemos o host via DoH em `https://1.1.1.1/dns-query` (IP
direto — não precisa de DNS) e instalamos um patch ESCOPADO em socket.getaddrinfo:
só os hosts registrados via enable_for() passam pelo DoH; todo o resto cai no
resolver normal. A conexão final é feita pelo IP, mas TLS/SNI continuam usando o
hostname original → a validação de certificado permanece intacta.
"""
from __future__ import annotations

import logging
import socket
import threading
import time

import httpx

logger = logging.getLogger("nexus.doh")

# Resolvedores DoH por IP (sem dependência de DNS). Tentados em ordem.
_DOH_HOSTS = ["1.1.1.1", "1.0.0.1"]
_TTL = 300.0  # segundos de cache por host

_overrides: set[str] = set()
_cache: dict[str, tuple[float, list[str]]] = {}
_lock = threading.Lock()
_orig_getaddrinfo = socket.getaddrinfo
_installed = False


def _doh_resolve(host: str) -> list[str]:
    last_exc: Exception | None = None
    for doh in _DOH_HOSTS:
        try:
            r = httpx.get(
                f"https://{doh}/dns-query",
                params={"name": host, "type": "A"},
                headers={"accept": "application/dns-json"},
                timeout=10.0,
            )
            r.raise_for_status()
            answers = r.json().get("Answer", [])
            ips = [a["data"] for a in answers if a.get("type") == 1]  # type 1 = A
            if ips:
                return ips
        except Exception as exc:  # noqa: BLE001 — tenta o próximo resolvedor
            last_exc = exc
    raise RuntimeError(f"DoH não resolveu {host}") from last_exc


def _resolve_cached(host: str) -> list[str]:
    now = time.time()
    with _lock:
        hit = _cache.get(host)
        if hit and now - hit[0] < _TTL:
            return hit[1]
    ips = _doh_resolve(host)
    with _lock:
        _cache[host] = (now, ips)
    logger.info("DoH resolveu %s -> %s", host, ips)
    return ips


def _patched_getaddrinfo(host, *args, **kwargs):  # noqa: ANN001
    if host in _overrides:
        try:
            ip = _resolve_cached(host)[0]
            return _orig_getaddrinfo(ip, *args, **kwargs)
        except Exception:  # noqa: BLE001 — fallback p/ o resolver do SO
            logger.exception("DoH falhou para %s; usando o resolver do SO", host)
    return _orig_getaddrinfo(host, *args, **kwargs)


def enable_for(host: str) -> None:
    """Registra um host p/ resolução via DoH e instala o patch (idempotente)."""
    global _installed
    _overrides.add(host)
    if not _installed:
        socket.getaddrinfo = _patched_getaddrinfo
        _installed = True
        logger.info("DoH (Cloudflare) ativado para %s", sorted(_overrides))
