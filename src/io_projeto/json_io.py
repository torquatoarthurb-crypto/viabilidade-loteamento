"""Carregar e salvar projetos em formato JSON."""

from __future__ import annotations

import json
from pathlib import Path

from ..modelos import Projeto


def carregar_projeto(caminho: str | Path) -> Projeto:
    """Carrega um projeto de um arquivo JSON e devolve uma instancia validada."""
    caminho = Path(caminho)
    with caminho.open(encoding="utf-8") as f:
        data = json.load(f)
    return Projeto.model_validate(data)


def salvar_projeto(projeto: Projeto, caminho: str | Path) -> None:
    """Salva um projeto em arquivo JSON."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as f:
        f.write(projeto.model_dump_json(indent=2))
