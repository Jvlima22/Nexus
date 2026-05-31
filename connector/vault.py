"""Leitura (somente) do vault Obsidian para a página Knowledge do NEXUS."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from config import settings


def vault_root() -> Path:
    if settings.vault_path:
        return Path(settings.vault_path).resolve()
    # default: <repo>/NEXUS, ao lado de connector/
    return (Path(__file__).resolve().parent.parent / "NEXUS").resolve()


def list_tree() -> list[dict[str, Any]]:
    """Todos os .md do vault, com pasta e data de modificação."""
    root = vault_root()
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for p in root.rglob("*.md"):
        rel = p.relative_to(root)
        folder = rel.parent.as_posix()
        out.append(
            {
                "path": rel.as_posix(),
                "name": p.stem,
                "folder": "" if folder == "." else folder,
                "modified": p.stat().st_mtime,
                "size": p.stat().st_size,
            }
        )
    out.sort(key=lambda x: (x["folder"], x["name"].lower()))
    return out


def read_file(rel_path: str) -> str:
    """Markdown cru de um .md dentro do vault. Sandbox contra path-traversal."""
    root = vault_root()
    target = (root / rel_path).resolve()
    if root not in target.parents:
        raise ValueError("caminho fora do vault")
    if target.suffix != ".md" or not target.is_file():
        raise FileNotFoundError(rel_path)
    return target.read_text(encoding="utf-8")


# Subpastas onde o agente (OpenClaw) pode ESCREVER. Mantém a IA fora de áreas
# sensíveis do vault (Decisões, Templates, etc.) — escrita só em análises/registros.
WRITABLE_PREFIXES = ("30_Trading/", "40_Registros/")


def write_note(rel_path: str, content: str) -> dict[str, Any]:
    """Cria/sobrescreve um .md dentro do vault. Sandbox + allowlist de subpasta."""
    root = vault_root()
    target = (root / rel_path).resolve()
    if root not in target.parents:
        raise ValueError("caminho fora do vault")
    if target.suffix != ".md":
        raise ValueError("apenas arquivos .md")
    rel = target.relative_to(root).as_posix()
    if not rel.startswith(WRITABLE_PREFIXES):
        raise ValueError(f"escrita permitida só em {', '.join(WRITABLE_PREFIXES)}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": rel, "size": target.stat().st_size}
