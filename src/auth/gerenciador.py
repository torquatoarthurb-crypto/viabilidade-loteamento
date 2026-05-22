"""
Gerenciamento de usuarios, autenticacao e persistencia de projetos por usuario.

Seguranca: SHA-256 com salt aleatorio por usuario (adequado para uso local/desktop).
Armazenamento: JSON em disco (sem banco de dados, alinhado com a filosofia do projeto).
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent.parent  # Rev_03/
DADOS_DIR = ROOT / "dados"
USUARIOS_FILE = DADOS_DIR / "usuarios.json"
SESSAO_FILE = DADOS_DIR / "sessao_ativa.json"


# =====================================================================
# UTILITARIOS INTERNOS
# =====================================================================

def _slug_email(email: str) -> str:
    """Converte email para slug seguro como nome de diretorio."""
    slug = email.lower().strip()
    slug = re.sub(r"[^a-z0-9]", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "usuario"


def _slug_nome(nome: str) -> str:
    """Converte nome de projeto para slug seguro como nome de arquivo."""
    slug = nome.lower().strip()
    slug = re.sub(r"[^a-z0-9à-ü]", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:60] or "projeto"


def _hash_senha(senha: str, salt: str) -> str:
    """SHA-256 com salt."""
    return hashlib.sha256(f"{salt}{senha}".encode("utf-8")).hexdigest()


def _carregar_usuarios() -> dict:
    if not USUARIOS_FILE.exists():
        return {}
    try:
        with USUARIOS_FILE.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _salvar_usuarios(usuarios: dict) -> None:
    DADOS_DIR.mkdir(parents=True, exist_ok=True)
    with USUARIOS_FILE.open("w", encoding="utf-8") as f:
        json.dump(usuarios, f, indent=2, ensure_ascii=False)


# =====================================================================
# AUTENTICACAO
# =====================================================================

def cadastrar(email: str, nome: str, senha: str) -> tuple[bool, str]:
    """Cadastra novo usuario. Retorna (sucesso, mensagem)."""
    email = email.strip().lower()

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False, "E-mail inválido. Verifique o formato (ex.: nome@gmail.com)."
    if len(nome.strip()) < 2:
        return False, "Nome deve ter pelo menos 2 caracteres."
    if len(senha) < 6:
        return False, "Senha deve ter no mínimo 6 caracteres."

    usuarios = _carregar_usuarios()
    if email in usuarios:
        return False, "Este e-mail já está cadastrado. Use outro ou faça login."

    salt = secrets.token_hex(16)
    usuarios[email] = {
        "email": email,
        "nome": nome.strip(),
        "salt": salt,
        "senha_hash": _hash_senha(senha, salt),
        "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    _salvar_usuarios(usuarios)

    pasta = pasta_projetos(email)
    pasta.mkdir(parents=True, exist_ok=True)
    return True, "Cadastro realizado com sucesso!"


def autenticar(email: str, senha: str) -> tuple[bool, str, Optional[dict]]:
    """Verifica credenciais. Retorna (sucesso, mensagem, dados_usuario)."""
    email = email.strip().lower()
    usuarios = _carregar_usuarios()

    if email not in usuarios:
        return False, "E-mail não encontrado. Verifique ou cadastre-se.", None

    u = usuarios[email]
    if _hash_senha(senha, u["salt"]) != u["senha_hash"]:
        return False, "Senha incorreta. Tente novamente.", None

    dados = {
        "email": u["email"],
        "nome": u["nome"],
        "email_slug": _slug_email(u["email"]),
    }
    return True, f"Bem-vindo, {u['nome']}!", dados


# =====================================================================
# PASTA DE PROJETOS DO USUARIO
# =====================================================================

def pasta_projetos(email: str) -> Path:
    """Retorna (e garante existencia de) a pasta de projetos do usuario."""
    p = DADOS_DIR / "projetos" / _slug_email(email)
    p.mkdir(parents=True, exist_ok=True)
    return p


# =====================================================================
# PERSISTENCIA DE PROJETOS
# =====================================================================

def _caminho_projeto(email: str, nome_projeto: str) -> Path:
    slug = _slug_nome(nome_projeto)
    return pasta_projetos(email) / f"{slug}.json"


def _caminho_meta(email: str, nome_projeto: str) -> Path:
    slug = _slug_nome(nome_projeto)
    return pasta_projetos(email) / f"{slug}_meta.json"


def salvar_projeto_usuario(email: str, projeto) -> Path:
    """
    Salva o projeto JSON na pasta do usuario.
    Retorna o caminho do arquivo salvo.
    """
    from ..modelos import Projeto as _Projeto  # evitar importacao circular
    caminho = _caminho_projeto(email, projeto.terreno.info.nome)
    with caminho.open("w", encoding="utf-8") as f:
        f.write(projeto.model_dump_json(indent=2))
    return caminho


def salvar_meta_projeto(email: str, nome_projeto: str, resultado) -> None:
    """Salva um cache leve de indicadores apos o calculo, para exibir na home."""
    ind = resultado.indicadores
    r = resultado.resumo
    meta = {
        "nome": nome_projeto,
        "calculado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "tir_anual": ind.get("tir_anual"),
        "vpl": ind.get("vpl"),
        "margem": r.get("margem_sobre_vgv_vendavel"),
        "lucro_liquido": r.get("lucro_liquido"),
        "exposicao_maxima": ind.get("exposicao_maxima"),
        "payback_simples_meses": ind.get("payback_simples_meses"),
    }
    caminho = _caminho_meta(email, nome_projeto)
    with caminho.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def carregar_meta_projeto(email: str, nome_projeto: str) -> Optional[dict]:
    """Carrega o cache de indicadores de um projeto, ou None se nao existir."""
    caminho = _caminho_meta(email, nome_projeto)
    if not caminho.exists():
        return None
    try:
        with caminho.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def carregar_projetos_usuario(email: str) -> list[dict]:
    """
    Lista todos os projetos do usuario com metadados para exibir na home.
    Cada item: {nome, cidade, uf, total_lotes, vgv_bruto, ultima_modificacao, meta, caminho}
    """
    pasta = pasta_projetos(email)
    projetos = []

    for arquivo in sorted(pasta.glob("*.json")):
        if arquivo.name.endswith("_meta.json"):
            continue
        try:
            import json as _json
            with arquivo.open(encoding="utf-8") as f:
                data = _json.load(f)

            info = data.get("terreno", {}).get("info", {})
            nome = info.get("nome", arquivo.stem)
            cidade = info.get("cidade", "")
            uf = info.get("uf", "")

            # Calcular VGV e lotes diretamente do JSON sem rodar a engine
            tipologias = data.get("terreno", {}).get("tipologias", [])
            total_lotes = sum(int(t.get("quantidade", 0)) for t in tipologias)
            vgv_bruto = 0.0
            for t in tipologias:
                qtd = float(t.get("quantidade", 0))
                area = float(t.get("area_lote_m2", 0))
                preco = float(t.get("valor_unitario", 0))
                modo = t.get("modo_preco", "por_m2")
                if modo == "por_m2":
                    vgv_bruto += qtd * area * preco
                else:
                    vgv_bruto += qtd * preco

            ultima_mod = datetime.fromtimestamp(arquivo.stat().st_mtime)
            ultima_mod_str = ultima_mod.strftime("%d/%m/%Y %H:%M")

            # Cache de indicadores (se existir)
            meta = carregar_meta_projeto(email, nome)

            projetos.append({
                "nome": nome,
                "cidade": cidade,
                "uf": uf,
                "total_lotes": total_lotes,
                "vgv_bruto": vgv_bruto,
                "ultima_modificacao": ultima_mod_str,
                "meta": meta,
                "caminho": str(arquivo),
            })
        except Exception:
            continue

    # Mais recentes primeiro
    projetos.sort(
        key=lambda p: p["ultima_modificacao"],
        reverse=True,
    )
    return projetos


def excluir_projeto_usuario(email: str, nome_projeto: str) -> None:
    """Remove o arquivo JSON e o cache de indicadores do projeto."""
    caminho = _caminho_projeto(email, nome_projeto)
    caminho_meta = _caminho_meta(email, nome_projeto)
    if caminho.exists():
        caminho.unlink()
    if caminho_meta.exists():
        caminho_meta.unlink()


# =====================================================================
# SESSAO PERSISTENTE ("manter conectado")
# =====================================================================

def salvar_sessao(dados_usuario: dict) -> None:
    """Persiste os dados do usuario logado em disco para auto-login."""
    DADOS_DIR.mkdir(parents=True, exist_ok=True)
    with SESSAO_FILE.open("w", encoding="utf-8") as f:
        json.dump(dados_usuario, f, ensure_ascii=False)


def carregar_sessao() -> Optional[dict]:
    """Carrega sessao salva. Retorna None se invalida ou expirada."""
    if not SESSAO_FILE.exists():
        return None
    try:
        with SESSAO_FILE.open(encoding="utf-8") as f:
            dados = json.load(f)
        # Verifica se o usuario ainda existe no sistema
        usuarios = _carregar_usuarios()
        if dados.get("email") in usuarios:
            return dados
        SESSAO_FILE.unlink(missing_ok=True)
        return None
    except Exception:
        return None


def limpar_sessao() -> None:
    """Remove a sessao salva (logout definitivo)."""
    SESSAO_FILE.unlink(missing_ok=True)


def duplicar_projeto_usuario(email: str, nome_original: str) -> Optional[str]:
    """Duplica um projeto com nome 'Copia de X'. Retorna o nome do novo projeto."""
    caminho = _caminho_projeto(email, nome_original)
    if not caminho.exists():
        return None

    try:
        import json as _json
        with caminho.open(encoding="utf-8") as f:
            data = _json.load(f)

        novo_nome = f"Cópia de {nome_original}"
        data.setdefault("terreno", {}).setdefault("info", {})["nome"] = novo_nome

        novo_caminho = _caminho_projeto(email, novo_nome)
        with novo_caminho.open("w", encoding="utf-8") as f:
            _json.dump(data, f, indent=2, ensure_ascii=False)

        return novo_nome
    except Exception:
        return None
