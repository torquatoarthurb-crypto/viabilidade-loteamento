"""
Aba 1 — Informacoes do Terreno e do Projeto.

Inputs: identificacao, quadro de areas, datas-chave, tipologias.
Outputs: aproveitamento, relacao lotes/viario, VGV bruto, composicao.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from ...modelos import (
    Aba1Terreno,
    Aba3Obras,
    DatasProjeto,
    InfoEmpreendimento,
    ParametrosFinanceiros,
    QuadroAreas,
    Tipologia,
)
from ..helpers import (
    aviso_validacao,
    btn_proximo_modulo,
    cabecalho_aba,
    formatar_brl,
    formatar_num,
    formatar_pct,
    get_projeto,
    invalidar_resultado,
    numero_brl,
    set_projeto,
)


def _add_meses(d: date, n: int) -> date:
    """Soma n meses a uma data, mantendo o dia 1 do mes resultante."""
    ano = d.year + (d.month - 1 + n) // 12
    mes = (d.month - 1 + n) % 12 + 1
    return date(ano, mes, 1)


def _extrair_coords_gmaps(url: str) -> tuple[float, float] | None:
    """E5: Extrai (lat, lon) de um URL do Google Maps. Retorna None se nao reconhecer."""
    import re
    m = re.search(r'@(-?\d{1,3}\.\d+),(-?\d{1,3}\.\d+)', url)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r'[?&]q=(-?\d{1,3}\.?\d*),(-?\d{1,3}\.?\d*)', url)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r'll=(-?\d{1,3}\.\d+),(-?\d{1,3}\.\d+)', url)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None


def _parsear_kmz(arquivo) -> list[list[float]] | None:
    """Parseia KMZ ou KML e retorna lista de [lat, lon] da poligonal completa."""
    import zipfile, io, xml.etree.ElementTree as ET
    try:
        conteudo = arquivo.read()
        if arquivo.name.lower().endswith(".kmz"):
            with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
                kml_nome = next((n for n in z.namelist() if n.lower().endswith(".kml")), None)
                if kml_nome is None:
                    return None
                kml_bytes = z.read(kml_nome)
        else:
            kml_bytes = conteudo
        root = ET.fromstring(kml_bytes)
        # Tenta múltiplos namespaces KML (2.2, 2.1, sem namespace)
        _NS_OPTS = [
            "http://www.opengis.net/kml/2.2",
            "http://earth.google.com/kml/2.1",
            "",
        ]
        def _tag(ns: str, name: str) -> str:
            return f"{{{ns}}}{name}" if ns else name

        def _parse_coords(text: str) -> list[list[float]]:
            pontos: list[list[float]] = []
            for part in text.strip().split():
                partes = part.split(",")
                if len(partes) >= 2:
                    try:
                        pontos.append([float(partes[1]), float(partes[0])])
                    except ValueError:
                        continue
            return pontos

        for _NS in _NS_OPTS:
            # Prefere outer boundary de Polygon para ler a poligonal completa
            for poly in root.iter(_tag(_NS, "Polygon")):
                outer = poly.find(f".//{_tag(_NS, 'outerBoundaryIs')}//{_tag(_NS, 'coordinates')}")
                if outer is None:
                    outer = poly.find(f".//{_tag(_NS, 'coordinates')}")
                if outer is not None and outer.text:
                    pontos = _parse_coords(outer.text)
                    if pontos:
                        return pontos
            # Fallback: LineString ou LinearRing genérico
            for tag in (_tag(_NS, "LinearRing"), _tag(_NS, "LineString")):
                for elem in root.iter(tag):
                    coords_el = elem.find(f".//{_tag(_NS, 'coordinates')}")
                    if coords_el is not None and coords_el.text:
                        pontos = _parse_coords(coords_el.text)
                        if pontos:
                            return pontos
        return None
    except Exception:
        return None


def _leaflet_html_poligono(coords: list[list[float]]) -> str:
    """Gera HTML com mapa Leaflet mostrando o poligono importado do KMZ."""
    import json
    lat_c = sum(p[0] for p in coords) / len(coords)
    lon_c = sum(p[1] for p in coords) / len(coords)
    coords_js = json.dumps(coords)
    return (
        '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>'
        '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>'
        '<div id="map_kmz" style="height:340px;background:#131822;border-radius:8px;"></div>'
        '<script>'
        'var m=L.map("map_kmz").setView([' + str(lat_c) + ',' + str(lon_c) + '],13);'
        'L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",'
        '{attribution:"\\u00a9 OpenStreetMap",maxZoom:19}).addTo(m);'
        'var poly=L.polygon(' + coords_js + ','
        '{color:"#34D399",weight:2,fillOpacity:0.2}).addTo(m);'
        'm.fitBounds(poly.getBounds().pad(0.12));'
        '</script>'
    )


# A8: lista de cidades brasileiras para autocomplete
_CIDADES_BR: list[str] = [
    "Anápolis", "Aparecida de Goiânia", "Aracaju", "Araguari", "Ananindeua",
    "Barbacena", "Belém", "Belo Horizonte", "Betim", "Blumenau", "Boa Vista", "Brasília",
    "Camaçari", "Campo Grande", "Campinas", "Canoas", "Cascavel", "Caruaru",
    "Caucaia", "Caxias do Sul", "Conselheiro Lafaiete", "Contagem",
    "Coronel Fabriciano", "Cuiabá", "Curitiba",
    "Diamantina", "Divinópolis", "Dourados", "Duque de Caxias",
    "Feira de Santana", "Florianópolis", "Fortaleza", "Foz do Iguaçu",
    "Goiânia", "Governador Valadares", "Guarulhos",
    "Ibirité", "Ilhéus", "Ipatinga", "Itabira", "Itaúna",
    "João Pessoa", "Joinville", "Juazeiro do Norte", "Juiz de Fora", "Jundiaí",
    "Lavras", "Londrina", "Luziânia",
    "Macaé", "Maceió", "Manaus", "Maracanaú", "Maringá", "Montes Claros",
    "Mossoró", "Muriaé",
    "Natal", "Niterói", "Nova Iguaçu", "Nova Lima",
    "Osasco", "Ouro Preto",
    "Palmas", "Passos", "Patos de Minas", "Paulista", "Pelotas",
    "Petrolina", "Petrópolis", "Poços de Caldas", "Porto Alegre",
    "Porto Seguro", "Porto Velho", "Pouso Alegre",
    "Recife", "Ribeirão das Neves", "Ribeirão Preto", "Rio Branco",
    "Rio de Janeiro", "Rondonópolis",
    "Sabará", "Salvador", "Santa Luzia", "Santo André", "Santos",
    "São Bernardo do Campo", "São Gonçalo", "São José", "São José dos Campos",
    "São Luís", "São Paulo", "Sete Lagoas", "Sorocaba",
    "Teófilo Otoni", "Teresina", "Timóteo",
    "Ubá", "Uberaba", "Uberlândia",
    "Varginha", "Várzea Grande", "Vitória", "Vitória da Conquista",
    "Volta Redonda",
]

_TIPOS_LOTEAMENTO = [
    "",
    "Loteamento fechado",
    "Loteamento aberto",
    "Condominio fechado",
    "Loteamento misto",
    "Loteamento residencial",
    "Loteamento comercial",
    "Loteamento industrial",
    "Outro",
]

_MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}
_ANOS = list(range(2015, 2046))


def _mes_ano(label: str, value: date, key: str) -> date:
    st.markdown(f"**{label}**")
    c1, c2 = st.columns([3, 2])
    with c1:
        mes = st.selectbox(
            "Mes", options=list(range(1, 13)),
            format_func=lambda m: _MESES_PT[m],
            index=value.month - 1,
            key=f"{key}_m",
            label_visibility="collapsed",
        )
    with c2:
        ano = st.selectbox(
            "Ano", options=_ANOS,
            index=_ANOS.index(value.year) if value.year in _ANOS else 0,
            key=f"{key}_a",
            label_visibility="collapsed",
        )
    return date(ano, mes, 1)


def _aviso_save(e: Exception) -> None:
    """Exibe aviso amigavel (st.warning) para erros de validacao ao salvar."""
    from pydantic import ValidationError as _VE

    _campo_pt: dict[str, str] = {
        "area_gleba_m2": "Área da gleba",
        "area_sistema_viario_m2": "Sistema viário",
        "area_verde_m2": "Área verde / lazer",
        "area_institucional_m2": "Área institucional",
        "area_app_m2": "APP",
        "area_lotes_m2": "Área de lotes",
        "inicio_projeto": "Início do projeto (M0)",
        "aprovacao": "Aprovação",
        "lancamento_vendas": "Lançamento de vendas",
        "inicio_obras": "Início de obras",
        "termino_obras": "Término de obras",
    }
    _msg_pt: dict[str, str] = {
        "greater than 0": "deve ser maior que zero",
        "greater than or equal to 0": "deve ser maior ou igual a zero",
        "Field required": "campo obrigatório",
        "less than or equal to": "valor muito alto",
    }

    if isinstance(e, _VE):
        msgs: list[str] = []
        for err in e.errors():
            loc = err.get("loc", ())
            campo = _campo_pt.get(str(loc[-1]) if loc else "", str(loc[-1]) if loc else "")
            msg = err.get("msg", "dado inválido")
            msg = msg.replace("Value error, ", "")
            for _en, _pt in _msg_pt.items():
                if _en in msg:
                    msg = _pt
                    break
            msgs.append(f"**{campo}**: {msg}" if campo else msg)
        texto = "\n\n".join(f"• {m}" for m in msgs)
        st.warning(f"Dados incompletos ou inválidos — corrija e salve novamente:\n\n{texto}")
    else:
        st.warning("Não foi possível salvar. Verifique os dados e tente novamente.")


def _calcular_duracao_obras(obras: Aba3Obras) -> int | None:
    if obras.modo == "resumido" and obras.resumido is not None:
        return int(obras.resumido.duracao_meses)
    if obras.modo == "detalhado" and obras.etapas:
        inicios = [e.mes_inicio for e in obras.etapas]
        finais = [e.mes_inicio + e.duracao_meses for e in obras.etapas]
        duracao = max(finais) - min(inicios)
        return max(duracao, 1)
    return None


def renderizar() -> None:
    """Renderiza a Aba 1 completa."""
    cabecalho_aba(
        1,
        "Informacoes do Terreno e do Projeto",
        "Quadro de areas, datas-chave, tipologias de lote e VGV bruto.",
    )

    projeto = get_projeto()
    terreno = projeto.terreno
    parametros = projeto.parametros

    # ============================================================
    # CARD 1 — IDENTIFICACAO
    # ============================================================
    with st.container(border=True):
        st.markdown("#### Identificação")

        col1, col2, col3, col4 = st.columns([3, 2, 1.2, 2])
        with col1:
            nome = st.text_input("Nome do empreendimento", value=terreno.info.nome)
        with col2:
            _cidade_atual = terreno.info.cidade
            _opcoes_cidade = sorted(
                set(_CIDADES_BR + ([_cidade_atual] if _cidade_atual and _cidade_atual not in _CIDADES_BR else [])),
                key=lambda x: x.lower(),
            ) + ["Outra cidade..."]
            _idx_cidade = (
                _opcoes_cidade.index(_cidade_atual)
                if _cidade_atual in _opcoes_cidade else 0
            )
            _cidade_sel = st.selectbox(
                "Cidade",
                options=_opcoes_cidade,
                index=_idx_cidade,
                key="aba1_cidade_sel",
                help="Digite para buscar. Nao encontrou? Selecione 'Outra cidade...'",
            )
            if _cidade_sel == "Outra cidade...":
                cidade = st.text_input(
                    "Nome da cidade",
                    value="" if _cidade_atual in _CIDADES_BR else _cidade_atual,
                    key="aba1_cidade_outro",
                    placeholder="Digite o nome da cidade",
                )
            else:
                cidade = _cidade_sel
        with col3:
            uf = st.text_input("UF", value=terreno.info.uf, max_chars=2)
        with col4:
            _tipo_atual = terreno.info.tipo_loteamento or ""
            _idx_tipo = _TIPOS_LOTEAMENTO.index(_tipo_atual) if _tipo_atual in _TIPOS_LOTEAMENTO else 0
            tipo_loteamento = st.selectbox(
                "Tipo de loteamento",
                options=_TIPOS_LOTEAMENTO,
                index=_idx_tipo,
                key="aba1_tipo_loteamento",
                format_func=lambda x: x if x else "— Selecione —",
            )

        # E5: LOCALIZACAO NO MAPA
        latitude: float | None = terreno.info.latitude
        longitude: float | None = terreno.info.longitude
        link_maps: str = terreno.info.link_maps or ""

        with st.expander("Localização no mapa (opcional)", expanded=False):
            # KMZ / KML import
            _kmz_upload = st.file_uploader(
                "Importar área delimitada (KMZ/KML)",
                type=["kmz", "kml"],
                key="aba1_kmz_upload",
                help="Exporte o polígono do Google Earth ou Google My Maps como KMZ e importe aqui.",
            )
            _kmz_coords: list[list[float]] | None = None
            if _kmz_upload is not None:
                _kmz_coords = _parsear_kmz(_kmz_upload)
                if _kmz_coords:
                    _lat_c = sum(p[0] for p in _kmz_coords) / len(_kmz_coords)
                    _lon_c = sum(p[1] for p in _kmz_coords) / len(_kmz_coords)
                    latitude = _lat_c
                    longitude = _lon_c
                    st.success(
                        f"Polígono importado: **{len(_kmz_coords)} pontos**. "
                        f"Centróide: {_lat_c:.5f}, {_lon_c:.5f}"
                    )
                else:
                    st.error("Não foi possível extrair coordenadas. Verifique se o arquivo contém um polígono.")

            st.markdown("---")
            link_maps = st.text_input(
                "Link do Google Maps (alternativo)",
                value=terreno.info.link_maps or "",
                key="aba1_link_maps",
                placeholder="https://www.google.com/maps/@-19.9191,-43.9386,15z",
                help="Cole o URL da barra de endereços do Google Maps. "
                     "As coordenadas serão extraídas automaticamente.",
            )

            coords_gmaps = _extrair_coords_gmaps(link_maps) if link_maps.strip() else None

            if coords_gmaps and _kmz_coords is None:
                latitude, longitude = coords_gmaps
                st.success(
                    f"Coordenadas extraídas do link: **{latitude:.6f}**, **{longitude:.6f}**"
                )
            elif _kmz_coords is None:
                _col_lat, _col_lon = st.columns(2)
                with _col_lat:
                    _lat_str = st.text_input(
                        "Latitude",
                        value=f"{terreno.info.latitude:.6f}" if terreno.info.latitude is not None else "",
                        key="aba1_lat_str",
                        placeholder="-19.919100",
                        help="Latitude decimal (negativo = hemisfério Sul). Ex: -19.919100 para BH.",
                    )
                with _col_lon:
                    _lon_str = st.text_input(
                        "Longitude",
                        value=f"{terreno.info.longitude:.6f}" if terreno.info.longitude is not None else "",
                        key="aba1_lon_str",
                        placeholder="-43.938600",
                        help="Longitude decimal (negativo = oeste de Greenwich). Ex: -43.938600 para BH.",
                    )
                try:
                    latitude = float(_lat_str.replace(",", ".")) if _lat_str.strip() else None
                    longitude = float(_lon_str.replace(",", ".")) if _lon_str.strip() else None
                except ValueError:
                    latitude = terreno.info.latitude
                    longitude = terreno.info.longitude

            if latitude is not None and longitude is not None:
                if _kmz_coords is not None:
                    import streamlit.components.v1 as _stc_kmz
                    _stc_kmz.html(_leaflet_html_poligono(_kmz_coords), height=360)
                    st.caption(f"Centróide: {latitude:.5f}, {longitude:.5f}")
                else:
                    _gmaps_url = f"https://www.google.com/maps?q={latitude},{longitude}"
                    _col_btn, _col_info = st.columns([1, 3])
                    with _col_btn:
                        st.markdown(
                            f'<a href="{_gmaps_url}" target="_blank" '
                            f'style="display:inline-block;padding:6px 12px;background:#4A9EFF;'
                            f'color:#fff;border-radius:4px;text-decoration:none;font-size:13px;">'
                            f'Abrir no Google Maps</a>',
                            unsafe_allow_html=True,
                        )
                    with _col_info:
                        st.caption(
                            f"{latitude:.6f}, {longitude:.6f}  \n"
                            f"[OpenStreetMap](https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude})"
                        )

                    _delta = 0.006
                    _osm_url = (
                        f"https://www.openstreetmap.org/export/embed.html?"
                        f"bbox={longitude - _delta},{latitude - _delta},"
                        f"{longitude + _delta},{latitude + _delta}"
                        f"&layer=mapnik&marker={latitude},{longitude}"
                    )
                    import streamlit.components.v1 as _stc_loc
                    _stc_loc.iframe(_osm_url, height=300, scrolling=False)
            else:
                pass

    # ============================================================
    # CARD 2 — QUADRO DE AREAS
    # ============================================================
    with st.container(border=True):
        st.markdown("#### Quadro de Áreas")

        # U1: seletor de unidade de area (m², ha, alqueire mineiro)
        _UNIDADES = {"m²": 1.0, "ha": 10_000.0, "alqueire": 48_400.0}
        _UNIDADE_LABELS = {"m²": "m²", "ha": "hectares (ha)", "alqueire": "alqueires (MG, 48.400 m²)"}
        _unidade = st.session_state.get("aba1_unidade_area", "m²")

        col_gleba, col_unidade, col_modo = st.columns([2, 1, 2])
        with col_unidade:
            _unidade = st.selectbox(
                "Unidade de área",
                options=list(_UNIDADES.keys()),
                index=list(_UNIDADES.keys()).index(_unidade) if _unidade in _UNIDADES else 0,
                key="aba1_unidade_area",
                format_func=lambda u: _UNIDADE_LABELS[u],
                help="Alqueire mineiro = 48.400 m² = 4,84 ha. "
                     "Alqueire paulista = 24.200 m² = 2,42 ha.",
            )
        _fator = _UNIDADES[_unidade]

        with col_gleba:
            _gleba_display = numero_brl(
                f"Area da gleba ({_unidade})",
                value=float(terreno.areas.area_gleba_m2) / _fator,
                key="aba1_area_gleba",
                min_value=0.0001,
            )
            area_gleba = _gleba_display * _fator
            if _unidade != "m²":
                st.caption(f"= {formatar_num(area_gleba, 0)} m²")
        with col_modo:
            usar_pct = st.toggle(
                "Inserir areas em % da gleba",
                value=st.session_state.get("aba1_usar_pct", False),
                key="aba1_usar_pct",
                help="Quando ativado, informe cada area como % da gleba. "
                     "O m² e calculado automaticamente.",
            )

        def _area_input(label: str, key_m2: str, key_pct: str, valor_m2: float) -> float:
            """Retorna area em m², seja por input direto, via % da gleba, ou na unidade selecionada."""
            if usar_pct and area_gleba > 0:
                pct_atual = valor_m2 / area_gleba * 100 if area_gleba > 0 else 0.0
                pct = numero_brl(
                    f"{label} (%)",
                    value=pct_atual,
                    key=key_pct,
                    min_value=0.0,
                    max_value=100.0,
                )
                m2 = pct / 100.0 * area_gleba
                st.caption(f"= {formatar_num(m2, 0)} m²")
                return m2
            else:
                _val_display = valor_m2 / _fator
                _resultado_display = numero_brl(
                    f"{label} ({_unidade})",
                    value=_val_display,
                    key=key_m2,
                    min_value=0.0,
                )
                m2 = _resultado_display * _fator
                if _unidade != "m²":
                    st.caption(f"= {formatar_num(m2, 0)} m²")
                return m2

        # 4 colunas iguais para as sub-areas (layout simetrico)
        col_v, col_vd, col_ins, col_app_c = st.columns(4)
        with col_v:
            area_viario = _area_input(
                "Sistema viario",
                key_m2="aba1_area_viario",
                key_pct="aba1_pct_viario",
                valor_m2=float(terreno.areas.area_sistema_viario_m2),
            )
        with col_vd:
            area_verde = _area_input(
                "Area verde / lazer",
                key_m2="aba1_area_verde",
                key_pct="aba1_pct_verde",
                valor_m2=float(terreno.areas.area_verde_m2),
            )
        with col_ins:
            area_inst = _area_input(
                "Area institucional",
                key_m2="aba1_area_inst",
                key_pct="aba1_pct_inst",
                valor_m2=float(terreno.areas.area_institucional_m2),
            )
        with col_app_c:
            area_app = _area_input(
                "APP",
                key_m2="aba1_area_app",
                key_pct="aba1_pct_app",
                valor_m2=float(terreno.areas.area_app_m2),
            )

        area_outras = area_viario + area_verde + area_inst + area_app
        area_lotes_sugerida = max(area_gleba - area_outras, 0)

        # Area de lotes — toggle a esquerda, resultado a direita
        col_chk, col_lot = st.columns([2, 3])
        with col_chk:
            usar_subtracao = st.checkbox(
                "Calcular area de lotes por subtracao", value=True, key="aba1_calc_lotes"
            )
        with col_lot:
            if usar_subtracao:
                area_lotes = area_lotes_sugerida
                st.metric("Area de lotes", formatar_num(area_lotes, 0) + " m²",
                          help="Calculada por subtração: gleba − viário − verde − institucional − APP")
            else:
                if usar_pct and area_gleba > 0:
                    pct_lotes_atual = float(terreno.areas.area_lotes_m2) / area_gleba * 100
                    pct_lotes = numero_brl(
                        "Area de lotes (%)",
                        value=pct_lotes_atual,
                        key="aba1_pct_lotes",
                        min_value=0.0,
                        max_value=100.0,
                    )
                    area_lotes = pct_lotes / 100.0 * area_gleba
                    st.caption(f"= {formatar_num(area_lotes, 0)} m²")
                else:
                    area_lotes = numero_brl(
                        "Area de lotes (m²)",
                        value=float(terreno.areas.area_lotes_m2),
                        key="aba1_area_lotes",
                        min_value=0.0,
                    )

        # Indicadores de aproveitamento — bloco destacado com 3 índices
        if area_gleba > 0:
            _aprov_pct = area_lotes / area_gleba * 100
            _viario_gleba_pct = area_viario / area_gleba * 100 if area_gleba > 0 else 0
            _viario_lotes_pct = area_viario / area_lotes * 100 if area_lotes > 0 else 0

            def _ind_html(label: str, valor: str, sub: str) -> str:
                return (
                    f'<div style="text-align:center;">'
                    f'<div style="font-size:10px;font-weight:700;color:#8A8880;'
                    f'letter-spacing:0.10em;text-transform:uppercase;margin-bottom:6px;">{label}</div>'
                    f'<div style="font-size:22px;font-weight:800;color:#1A1916;'
                    f'-webkit-text-stroke:0.3px #1A1916;line-height:1;">{valor}</div>'
                    f'<div style="font-size:11px;color:#5A5650;margin-top:4px;">{sub}</div>'
                    f'</div>'
                )

            st.markdown(
                '<div style="background:#F0EEE9;border:1px solid #D8D4C8;border-radius:8px;'
                'padding:16px 20px;margin:14px 0 4px;display:grid;'
                'grid-template-columns:1fr 1px 1fr 1px 1fr;align-items:center;gap:0;">'
                + _ind_html("Área de Lotes / Gleba", f"{_aprov_pct:.1f}%", "aproveitamento")
                + '<div style="background:#D8D4C8;height:36px;"></div>'
                + _ind_html("Viário / Gleba", f"{_viario_gleba_pct:.1f}%", "infraestrutura viária")
                + '<div style="background:#D8D4C8;height:36px;"></div>'
                + _ind_html("Viário / Lotes", f"{_viario_lotes_pct:.1f}%", "relação viário ÷ área vendável")
                + '</div>',
                unsafe_allow_html=True,
            )

    # ============================================================
    # CARD 3 — DATAS-CHAVE DO PROJETO
    # ============================================================
    with st.container(border=True):
        st.markdown("#### Datas-chave do Projeto")

        obras = projeto.obras
        duracao_calculada_meses = _calcular_duracao_obras(obras)

        col1, col2, col3 = st.columns(3)
        with col1:
            inicio_projeto = _mes_ano(
                "Inicio do projeto (M0)",
                terreno.datas.inicio_projeto,
                "aba1_dt_ini",
            )
            aprovacao = _mes_ano(
                "Aprovacao",
                terreno.datas.aprovacao,
                "aba1_dt_apr",
            )
        with col2:
            lancamento = _mes_ano(
                "Lancamento de vendas",
                terreno.datas.lancamento_vendas,
                "aba1_dt_lanc",
            )
            inicio_obras = _mes_ano(
                "Inicio de obras",
                terreno.datas.inicio_obras,
                "aba1_dt_ini_ob",
            )
        with col3:
            # Duracao inicial derivada do modelo (termino - inicio, em meses)
            _dur_modelo = max(1, (
                (terreno.datas.termino_obras.year - terreno.datas.inicio_obras.year) * 12
                + (terreno.datas.termino_obras.month - terreno.datas.inicio_obras.month)
            ))
            # Override enviado por sincronizar_aba3 quando o fluxo ultrapassa a duracao
            _override = st.session_state.pop("_aba1_duracao_obras_override", None)
            if _override is not None:
                st.session_state["aba1_duracao_obras"] = int(_override)

            st.markdown("**Duração das obras (meses)**")
            duracao_obras_meses = int(st.number_input(
                "Duração das obras (meses)",
                value=_dur_modelo,
                min_value=1,
                step=1,
                key="aba1_duracao_obras",
                help="Contado a partir do início das obras.",
                label_visibility="collapsed",
            ))
            termino_obras = _add_meses(inicio_obras, duracao_obras_meses)
            st.markdown(
                f'**Término de obras** &nbsp; '
                f'<span style="font-family:\'DM Mono\',monospace;font-size:14px;color:#1A1916;">'
                f'{termino_obras.strftime("%m/%Y")}</span>',
                unsafe_allow_html=True,
            )

            if duracao_calculada_meses is not None and duracao_calculada_meses > duracao_obras_meses:
                st.info(
                    f"As etapas de obra cobrem **{duracao_calculada_meses} meses**, "
                    f"além da duração configurada ({duracao_obras_meses} meses). "
                    "Salve a aba de obras para atualizar automaticamente."
                )

        # A4: Avisos de conflitos de datas
        _erros_datas: list[str] = []
        if aprovacao < inicio_projeto:
            _erros_datas.append("A Aprovação precisa ser igual ou posterior ao Início do Projeto (M0).")
        if lancamento < inicio_projeto:
            _erros_datas.append("O Lançamento de Vendas precisa ser igual ou posterior ao Início do Projeto (M0).")
        if inicio_obras < inicio_projeto:
            _erros_datas.append("O Início de Obras precisa ser igual ou posterior ao Início do Projeto (M0).")
        if termino_obras <= inicio_obras:
            _erros_datas.append("O Término de Obras precisa ser posterior ao Início de Obras.")
        for _msg_data in _erros_datas:
            st.warning(_msg_data)

    # Linha do tempo abaixo das datas-chave
    try:
        from ..helpers import criar_fig_linha_do_tempo as _criar_lt
        _fig_lt = _criar_lt(projeto)
        st.plotly_chart(_fig_lt, use_container_width=True, config={"displayModeBar": False})
        st.caption(
            "Os numeros 'M' sao os meses relativos ao inicio do projeto. "
            "Use eles ao preencher campos 'Mes inicio' e 'Mes fim' nas demais abas."
        )
    except Exception:
        pass

    # ============================================================
    # CARD 4 — TIPOLOGIAS DE LOTE
    # ============================================================
    _TIP_LISTA_KEY = "aba1_tip_lista"
    _TIP_HASH_KEY = "aba1_tip_proj_hash"

    def _tip_hash(tips: list) -> str:
        return str([(t.nome, t.quantidade, t.area_lote_m2, t.modo_preco, t.valor_unitario)
                    for t in tips])

    _proj_hash = _tip_hash(terreno.tipologias)
    if st.session_state.get(_TIP_HASH_KEY) != _proj_hash:
        st.session_state[_TIP_LISTA_KEY] = [
            {
                "nome": t.nome,
                "qtd": t.quantidade,
                "area_m2": t.area_lote_m2,
                "modo": t.modo_preco,
                "valor": t.valor_unitario,
                "agio_pct": 0.0,
            }
            for t in terreno.tipologias
        ]
        st.session_state[_TIP_HASH_KEY] = _proj_hash
        for _k in list(st.session_state.keys()):
            if "_tipr_" in _k:
                del st.session_state[_k]

    lista: list[dict] = st.session_state.get(_TIP_LISTA_KEY, [])

    with st.container(border=True):
        st.markdown("#### Tipologias de Lote")

        _area_por_total = st.checkbox(
            "Inserir área total da tipologia (em vez de área por lote)",
            value=st.session_state.get("aba1_area_por_total", False),
            key="aba1_area_por_total",
            help="Quando ativado, informe a área total dos lotes. A área por lote é calculada automaticamente (÷ quantidade).",
        )

        _col_w = [3, 0.8, 1.2, 1.4, 1.8, 1.4, 2.4, 0.5]
        _area_col_label = "Área total (m²)" if _area_por_total else "Área/lote (m²)"
        if lista:
            _hcols = st.columns(_col_w)
            _area_res_label = "Média/lote (m²)" if _area_por_total else "Área total"
            _hlabels = ["Nome", "Qtd", _area_col_label, "Modo", "Valor unit. (R$)", _area_res_label, "VGV", ""]
            for _hc, _hl in zip(_hcols, _hlabels):
                with _hc:
                    st.markdown(
                        f'<div style="font-size:10px;color:var(--stone-500);font-weight:600;'
                        f'letter-spacing:0.06em;text-transform:uppercase;padding-bottom:3px;">{_hl}</div>',
                        unsafe_allow_html=True,
                    )

        lista_atual: list[dict] = []
        _idx_remover: int | None = None

        for i, _item in enumerate(lista):
            _cw = st.columns(_col_w)
            with _cw[0]:
                _nome_i = st.text_input(
                    "nome", value=_item["nome"], key=f"_tipr_{i}_nome",
                    label_visibility="collapsed",
                )
            with _cw[1]:
                _qtd_i = st.number_input(
                    "qtd", value=int(_item["qtd"]), min_value=1, step=1,
                    key=f"_tipr_{i}_qtd", label_visibility="collapsed",
                )
            with _cw[2]:
                if _area_por_total:
                    _area_total_inp = numero_brl(
                        "area_total", value=float(_item["area_m2"]) * max(int(_item["qtd"]), 1),
                        key=f"_tipr_{i}_area", min_value=0.0, casas=2,
                        label_visibility="collapsed",
                    )
                    _area_i = _area_total_inp / max(int(_qtd_i), 1)
                else:
                    _area_i = numero_brl(
                        "area", value=float(_item["area_m2"]),
                        key=f"_tipr_{i}_area", min_value=0.0, casas=2,
                        label_visibility="collapsed",
                    )
            with _cw[3]:
                _modo_i = st.selectbox(
                    "modo", options=["por_m2", "por_lote"],
                    index=0 if _item["modo"] == "por_m2" else 1,
                    key=f"_tipr_{i}_modo", label_visibility="collapsed",
                )
            with _cw[4]:
                _valor_i = numero_brl(
                    "valor", value=float(_item["valor"]),
                    key=f"_tipr_{i}_valor", min_value=0.0, casas=2,
                    label_visibility="collapsed",
                )
            _area_tot_i = float(_qtd_i) * _area_i
            _preco_base_i = _area_i * _valor_i if _modo_i == "por_m2" else _valor_i
            _vgv_i = float(_qtd_i) * _preco_base_i
            _area_res_val = _area_i if _area_por_total else _area_tot_i
            _area_res_fmt = f"{_area_res_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            with _cw[5]:
                st.markdown(
                    f'<div style="padding:7px 0 0 0;font-size:12px;'
                    f'font-family:\'DM Mono\',monospace;color:var(--stone-700);">{_area_res_fmt} m²</div>',
                    unsafe_allow_html=True,
                )
            with _cw[6]:
                st.markdown(
                    f'<div style="padding:7px 0 0 0;font-size:12px;'
                    f'font-family:\'DM Mono\',monospace;color:var(--stone-700);">{formatar_brl(_vgv_i)}</div>',
                    unsafe_allow_html=True,
                )
            with _cw[7]:
                if st.button(
                    "×", key=f"_tipr_{i}_del",
                    icon=":material/delete:",
                    help="Remover tipologia",
                    width="stretch",
                ):
                    _idx_remover = i
            lista_atual.append({
                "nome": _nome_i.strip(),
                "qtd": int(_qtd_i),
                "area_m2": float(_area_i),
                "modo": str(_modo_i),
                "valor": float(_valor_i),
                "agio_pct": 0.0,
            })

        if _idx_remover is not None:
            lista_atual.pop(_idx_remover)
            for _k in list(st.session_state.keys()):
                if "_tipr_" in _k:
                    del st.session_state[_k]
            st.session_state[_TIP_LISTA_KEY] = lista_atual
            st.session_state[_TIP_HASH_KEY] = _proj_hash
            st.rerun()

        if st.button("Adicionar tipologia", icon=":material/add:", key="aba1_tip_add"):
            lista_atual.append({
                "nome": f"Tipologia {len(lista_atual) + 1}",
                "qtd": 1, "area_m2": 0.0, "modo": "por_m2",
                "valor": 0.0, "agio_pct": 0.0,
            })
            for _k in list(st.session_state.keys()):
                if "_tipr_" in _k:
                    del st.session_state[_k]
            st.session_state[_TIP_LISTA_KEY] = lista_atual
            st.session_state[_TIP_HASH_KEY] = _proj_hash
            st.rerun()

        _tip_editadas: list[Tipologia] = []
        _tip_errors: list[str] = []
        for _d in lista_atual:
            _nome_t = _d["nome"]
            if not _nome_t:
                continue
            try:
                _tip_editadas.append(Tipologia(
                    nome=_nome_t,
                    quantidade=_d["qtd"],
                    area_lote_m2=_d["area_m2"],
                    modo_preco=_d["modo"],
                    valor_unitario=_d["valor"],
                    gio_percentual=_d["agio_pct"],
                ))
            except Exception as _e:
                if hasattr(_e, "errors"):
                    try:
                        _msgs = [
                            f"{e.get('loc', ['?'])[-1]}: {e.get('msg', '')}"
                            for e in _e.errors()
                        ]
                        _tip_errors.append(f"'{_nome_t}': {'; '.join(_msgs)}")
                    except Exception:
                        _tip_errors.append(f"'{_nome_t}': dados inválidos")
                else:
                    _tip_errors.append(f"'{_nome_t}': {_e}")

        _tip_atual_hash = _tip_hash(_tip_editadas)
        _tip_dirty = bool(_tip_editadas) and _tip_atual_hash != _tip_hash(terreno.tipologias)

        for _err in _tip_errors:
            st.warning(f"Dados inválidos — {_err}")

        salvar_tips = False
        if _tip_dirty:
            st.markdown(
                '<div style="color:var(--accent-500);font-size:12px;padding-top:4px;">'
                '● Tipologias com alterações não salvas — clique em "Salvar aba" abaixo.'
                '</div>',
                unsafe_allow_html=True,
            )

        total_lotes = 0
        area_usada = 0.0
        vgv_total = 0.0
        for _d in lista_atual:
            if not _d["nome"]:
                continue
            try:
                total_lotes += _d["qtd"]
                area_usada += _d["qtd"] * _d["area_m2"]
                _pb = _d["area_m2"] * _d["valor"] if _d["modo"] == "por_m2" else _d["valor"]
                vgv_total += _d["qtd"] * _pb * (1 + _d["agio_pct"] / 100)
            except Exception:
                continue

        # Resultados destacados em bloco (mesmo padrão dos indicadores de aproveitamento)
        _area_usada_fmt = formatar_num(area_usada, 0) + " m²"
        if area_lotes > 0:
            _saldo = area_lotes - area_usada
            _area_sub = (
                f"de {formatar_num(area_lotes, 0)} m² disponíveis"
                if _saldo >= 0
                else f"<span style='color:#EF4444;'>Excedeu {formatar_num(-_saldo, 0)} m²</span>"
            )
        else:
            _area_sub = "área de lotes não configurada"

        def _res_html(label: str, valor: str, sub: str) -> str:
            return (
                f'<div style="text-align:center;">'
                f'<div style="font-size:10px;font-weight:700;color:#8A8880;'
                f'letter-spacing:0.10em;text-transform:uppercase;margin-bottom:6px;">{label}</div>'
                f'<div style="font-size:18px;font-weight:700;color:#1A1916;line-height:1;">{valor}</div>'
                f'<div style="font-size:11px;color:#5A5650;margin-top:4px;">{sub}</div>'
                f'</div>'
            )

        st.markdown(
            '<div style="background:#F0EEE9;border:1px solid #D8D4C8;border-radius:8px;'
            'padding:14px 20px;margin:10px 0 4px;display:grid;'
            'grid-template-columns:1fr 1px 1fr 1px 1fr;align-items:center;gap:0;">'
            + _res_html("VGV Total Bruto", formatar_brl(vgv_total), "&nbsp;")
            + '<div style="background:#D8D4C8;height:36px;"></div>'
            + _res_html("Total de Lotes", str(total_lotes), "unidades")
            + '<div style="background:#D8D4C8;height:36px;"></div>'
            + _res_html("Área de Lotes", _area_usada_fmt, _area_sub)
            + '</div>',
            unsafe_allow_html=True,
        )

        if area_lotes > 0 and (_saldo := area_lotes - area_usada) < 0:
            st.warning(f"Área das tipologias excede em {formatar_num(-_saldo, 0)} m² o limite de {formatar_num(area_lotes, 0)} m²")

        # A1: barra de progresso — vermelha enquanto incompleta, verde quando 100%
        if area_lotes > 0:
            _frac = area_usada / area_lotes
            _bar_w = min(_frac * 100, 100)
            _cor_bar = "#22C55E" if _frac >= 1.0 else "#EF4444"
            _label_bar = (
                f"{formatar_num(area_usada, 0)} de {formatar_num(area_lotes, 0)} m²"
                f" ({_frac * 100:.1f}%)"
            )
            st.markdown(
                f'<div style="margin:6px 0 10px 0;">'
                f'<div style="font-size:10px;color:var(--stone-500);font-weight:600;'
                f'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:5px;">Ocupação da área de lotes</div>'
                f'<div style="background:var(--stone-100);border-radius:6px;height:8px;overflow:hidden;">'
                f'<div style="background:{_cor_bar};width:{_bar_w:.1f}%;height:100%;border-radius:6px;"></div>'
                f'</div>'
                f'<div style="font-size:11px;font-family:\'DM Mono\',monospace;color:{_cor_bar};margin-top:4px;">{_label_bar}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ============================================================
    # TMA
    # ============================================================
    with st.container(border=True):
        st.markdown("#### Taxa Mínima de Atratividade (TMA)")
        _col_tma1, _col_tma2 = st.columns(2)
        with _col_tma1:
            tma_anual = numero_brl(
                "TMA (% ao ano)",
                value=float(parametros.tma_anual),
                key="aba1_tma",
                min_value=0.0,
                help="Pratica de mercado:\n"
                     "• Conservador: 8-12% a.a. (Selic ou CDI)\n"
                     "• Moderado: 12-15% a.a.\n"
                     "• Agressivo: 15-20% a.a.",
            )
        with _col_tma2:
            _tma_mensal = (1 + tma_anual / 100) ** (1 / 12) - 1
            st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
            st.markdown(
                f'<div style="font-size:11px;color:#9CA3AF;">Equivalente mensal</div>'
                f'<div style="font-size:13px;font-weight:600;">{_tma_mensal * 100:.4f} % a.m.</div>',
                unsafe_allow_html=True,
            )

    # ============================================================
    # NAVEGACAO
    # ============================================================
    btn_proximo_modulo("Terreno")

    # ============================================================
    # SAVE BUTTON (campos de identificacao, areas, datas + tipologias)
    # ============================================================
    atual = projeto.terreno

    # Dirty check rapido (sem reconstruir Pydantic)
    _dirty1 = (
        atual.info.nome != nome
        or atual.info.cidade != cidade
        or atual.info.uf != uf.upper()
        or atual.info.tipo_loteamento != tipo_loteamento
        or atual.info.latitude != latitude
        or atual.info.longitude != longitude
        or atual.info.link_maps != link_maps
        or atual.areas.area_gleba_m2 != area_gleba
        or atual.areas.area_sistema_viario_m2 != area_viario
        or atual.areas.area_verde_m2 != area_verde
        or atual.areas.area_institucional_m2 != area_inst
        or atual.areas.area_app_m2 != area_app
        or atual.areas.area_lotes_m2 != area_lotes
        or atual.datas.inicio_projeto != inicio_projeto
        or atual.datas.aprovacao != aprovacao
        or atual.datas.lancamento_vendas != lancamento
        or atual.datas.inicio_obras != inicio_obras
        or atual.datas.termino_obras != termino_obras
        or _tip_dirty
        or abs(parametros.tma_anual - tma_anual) > 0.001
    )

    # Staged: persiste valores atuais para sincronizar_aba1 usar antes do Calcular
    st.session_state["_aba1_staged"] = {
        "nome": nome, "cidade": cidade, "uf": uf,
        "tipo_loteamento": tipo_loteamento,
        "latitude": latitude, "longitude": longitude, "link_maps": link_maps,
        "area_gleba": area_gleba, "area_viario": area_viario,
        "area_verde": area_verde, "area_inst": area_inst,
        "area_app": area_app, "area_lotes": area_lotes,
        "inicio_projeto": inicio_projeto, "aprovacao": aprovacao,
        "lancamento": lancamento, "inicio_obras": inicio_obras,
        "termino_obras": termino_obras,
        "tipologias": _tip_editadas if _tip_editadas else list(atual.tipologias),
        "tma_anual": tma_anual,
    }

    st.markdown("---")
    _col_ind1, _col_btn1 = st.columns([3, 1])
    with _col_ind1:
        if _dirty1:
            st.markdown(
                '<div style="color:var(--accent-500);font-size:12px;padding-top:6px;">'
                '● Alterações não salvas</div>',
                unsafe_allow_html=True,
            )
    with _col_btn1:
        salvar_aba1 = st.button(
            "Salvar aba",
            key="aba1_salvar_aba",
            type="primary" if _dirty1 else "secondary",
            width="stretch",
            icon=":material/save:",
        )

    # Processar save — botao de aba (geral) ou botao de tipologias
    if salvar_aba1 or (salvar_tips and _tip_dirty):
        try:
            _tips_save = _tip_editadas if bool(_tip_editadas) else list(atual.tipologias)
            novo_terreno = Aba1Terreno(
                info=InfoEmpreendimento(
                    nome=nome, cidade=cidade, uf=uf.upper(),
                    tipo_loteamento=tipo_loteamento,
                    latitude=latitude, longitude=longitude, link_maps=link_maps,
                ),
                areas=QuadroAreas(
                    area_gleba_m2=area_gleba,
                    area_sistema_viario_m2=area_viario,
                    area_verde_m2=area_verde,
                    area_institucional_m2=area_inst,
                    area_app_m2=area_app,
                    area_lotes_m2=area_lotes,
                ),
                datas=DatasProjeto(
                    inicio_projeto=inicio_projeto,
                    aprovacao=aprovacao,
                    lancamento_vendas=lancamento,
                    inicio_obras=inicio_obras,
                    termino_obras=termino_obras,
                ),
                tipologias=_tips_save,
            )
            set_projeto(projeto.model_copy(update={
                "terreno": novo_terreno,
                "parametros": ParametrosFinanceiros(tma_anual=tma_anual),
            }))
            invalidar_resultado()
            if _tip_dirty:
                st.session_state[_TIP_HASH_KEY] = _tip_atual_hash
            st.rerun()
        except Exception as _e:
            _aviso_save(_e)


def sincronizar_aba1() -> None:
    """Salva o estado da Aba 1 no projeto (chamado pelo sidebar antes de Calcular)."""
    staged = st.session_state.get("_aba1_staged")
    if staged is None:
        return
    try:
        projeto = get_projeto()
        novo_terreno = Aba1Terreno(
            info=InfoEmpreendimento(
                nome=staged["nome"],
                cidade=staged["cidade"],
                uf=staged["uf"].upper(),
                tipo_loteamento=staged["tipo_loteamento"],
                latitude=staged["latitude"],
                longitude=staged["longitude"],
                link_maps=staged["link_maps"],
            ),
            areas=QuadroAreas(
                area_gleba_m2=staged["area_gleba"],
                area_sistema_viario_m2=staged["area_viario"],
                area_verde_m2=staged["area_verde"],
                area_institucional_m2=staged["area_inst"],
                area_app_m2=staged["area_app"],
                area_lotes_m2=staged["area_lotes"],
            ),
            datas=DatasProjeto(
                inicio_projeto=staged["inicio_projeto"],
                aprovacao=staged["aprovacao"],
                lancamento_vendas=staged["lancamento"],
                inicio_obras=staged["inicio_obras"],
                termino_obras=staged["termino_obras"],
            ),
            tipologias=staged["tipologias"],
        )
        tma = staged.get("tma_anual")
        terreno_mudou = projeto.terreno.model_dump_json() != novo_terreno.model_dump_json()
        tma_mudou = tma is not None and abs(projeto.parametros.tma_anual - float(tma)) > 0.001
        if terreno_mudou or tma_mudou:
            update: dict = {"terreno": novo_terreno}
            if tma is not None:
                update["parametros"] = ParametrosFinanceiros(tma_anual=float(tma))
            set_projeto(projeto.model_copy(update=update))
            invalidar_resultado()
    except Exception:
        pass
