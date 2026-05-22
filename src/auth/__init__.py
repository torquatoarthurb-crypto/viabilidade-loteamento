"""Modulo de autenticacao de usuarios."""

from .gerenciador import (
    autenticar,
    cadastrar,
    pasta_projetos,
    salvar_projeto_usuario,
    carregar_projetos_usuario,
    salvar_meta_projeto,
    carregar_meta_projeto,
    excluir_projeto_usuario,
    duplicar_projeto_usuario,
    salvar_sessao,
    carregar_sessao,
    limpar_sessao,
)

__all__ = [
    "autenticar",
    "cadastrar",
    "pasta_projetos",
    "salvar_projeto_usuario",
    "carregar_projetos_usuario",
    "salvar_meta_projeto",
    "carregar_meta_projeto",
    "excluir_projeto_usuario",
    "duplicar_projeto_usuario",
    "salvar_sessao",
    "carregar_sessao",
    "limpar_sessao",
]
