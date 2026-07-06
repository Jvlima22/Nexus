"""
Helper p/ descobrir slugs válidos da Polymarket (Gamma API) para POLYMARKET_SLUGS.

Uso:
  python find_slugs.py                 # top mercados por volume (slug -> pergunta)
  python find_slugs.py <slug>          # valida um slug específico
  python find_slugs.py -q recession    # busca por palavra na pergunta
"""
from __future__ import annotations

import sys

import httpx

import doh

GAMMA_HOST = "gamma-api.polymarket.com"
GAMMA = f"https://{GAMMA_HOST}/markets"

# Mesmo contorno de DNS do connector (provedor BR forja NXDOMAIN p/ polymarket).
doh.enable_for(GAMMA_HOST)


def _rows(params: dict) -> list[dict]:
    r = httpx.get(GAMMA, params=params, timeout=20)
    r.raise_for_status()
    d = r.json()
    return d if isinstance(d, list) else d.get("data", [])


def top() -> None:
    rows = _rows({"active": "true", "closed": "false", "order": "volumeNum",
                  "ascending": "false", "limit": 15})
    print(f"{len(rows)} mercados ativos (maior volume):\n")
    for m in rows:
        vol = m.get("volumeNum") or m.get("volume") or 0
        print(f"  {m.get('slug')}")
        print(f"      {m.get('question')}  (vol ~${float(vol):,.0f})")


def search(term: str, page: int = 500, max_offset: int = 10000) -> None:
    """Pagina a Gamma (mercados de maior volume não trazem os econômicos no topo).

    A Gamma recusa offset > ~10000 (422); paramos antes e toleramos falha de página,
    imprimindo o que já foi encontrado.
    """
    term_l = term.lower()
    hits: list[dict] = []
    seen: set[str] = set()
    offset = 0
    while offset <= max_offset:
        try:
            rows = _rows({"active": "true", "closed": "false", "order": "volumeNum",
                          "ascending": "false", "limit": page, "offset": offset})
        except Exception as exc:  # noqa: BLE001 — limite/instabilidade: para e mostra o parcial
            print(f"(parou em offset {offset}: {exc})")
            break
        if not rows:
            break
        for m in rows:
            slug = m.get("slug")
            if slug in seen:
                continue
            seen.add(slug)
            if term_l in (m.get("question") or "").lower() or term_l in (slug or "").lower():
                hits.append(m)
        offset += page
    hits.sort(key=lambda m: float(m.get("volumeNum") or m.get("volume") or 0), reverse=True)
    print(f"\n{len(hits)} mercado(s) com '{term}' (varridos {len(seen)} mercados):\n")
    for m in hits:
        vol = m.get("volumeNum") or m.get("volume") or 0
        print(f"  {m.get('slug')}  ->  {m.get('question')}  (vol ~${float(vol):,.0f})")


def validate(slug: str) -> None:
    rows = _rows({"slug": slug})
    if not rows:
        print(f"VAZIO — '{slug}' nao e um market slug valido (talvez seja event slug).")
        return
    m = rows[0]
    print("OK — slug valido!")
    print("  pergunta:", m.get("question"))
    print("  outcomes:", m.get("outcomes"))
    print("  precos  :", m.get("outcomePrices"))


if __name__ == "__main__":
    try:
        if len(sys.argv) == 1:
            top()
        elif sys.argv[1] in ("-q", "--search") and len(sys.argv) > 2:
            search(sys.argv[2])
        else:
            validate(sys.argv[1])
    except Exception as e:  # noqa: BLE001
        print("ERRO ao consultar a Gamma API:", e)
        sys.exit(1)
