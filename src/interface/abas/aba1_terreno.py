"""
Aba 1 — Informacoes do Terreno e do Projeto.

Inputs: identificacao, quadro de areas, datas-chave, tipologias.
Outputs: aproveitamento, relacao lotes/viario, VGV bruto, composicao.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from ...modelos import (
    Aba1Terreno,
    Aba3Obras,
    DatasProjeto,
    InfoEmpreendimento,
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
    """Parseia KMZ ou KML e retorna lista de [lat, lon] do primeiro poligono/linha encontrado."""
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
        _NS = "http://www.opengis.net/kml/2.2"
        for tag in (f"{{{_NS}}}Polygon", f"{{{_NS}}}LinearRing", f"{{{_NS}}}LineString"):
            for elem in root.iter(tag):
                coords_el = elem.find(f".//{{{_NS}}}coordinates")
                if coords_el is not None and coords_el.text:
                    pontos: list[list[float]] = []
                    for part in coords_el.text.strip().split():
                        partes = part.split(",")
                        if len(partes) >= 2:
                            try:
                                pontos.append([float(partes[1]), float(partes[0])])
                            except ValueError:
                                continue
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

    # ============================================================
    # CARD 1 — IDENTIFICACAO
    # ============================================================
    with st.container(border=True):
        st.markdown("#### 🏢 Identificacao")

        col1, col2, col3, col4 = st.columns([3, 2, 1, 2])
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

        with st.expander("📍 Localização no mapa (opcional)", expanded=False):
            st.caption(
                "Importe um KMZ/KML com o polígono da área, cole o link do Google Maps, "
                "ou informe as coordenadas manualmente."
            )

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
                        f"✅ Polígono importado: **{len(_kmz_coords)} pontos**. "
                        f"Centróide: {_lat_c:.5f}, {_lon_c:.5f}"
                    )
                else:
                    st.error("❌ Não foi possível extrair coordenadas. Verifique se o arquivo contém um polígono.")

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
                    f"✅ Coordenadas extraídas do link: **{latitude:.6f}**, **{longitude:.6f}**"
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
                    st.caption(f"📍 Centróide: {latitude:.5f}, {longitude:.5f}")
                else:
                    _gmaps_url = f"https://www.google.com/maps?q={latitude},{longitude}"
                    _col_btn, _col_info = st.columns([1, 3])
                    with _col_btn:
                        st.markdown(
                            f'<a href="{_gmaps_url}" target="_blank" '
                            f'style="display:inline-block;padding:6px 12px;background:#4A9EFF;'
                            f'color:#fff;border-radius:4px;text-decoration:none;font-size:13px;">'
                            f'🗺️ Abrir no Google Maps</a>',
                            unsafe_allow_html=True,
                        )
                    with _col_info:
                        st.caption(
                            f"📍 {latitude:.6f}, {longitude:.6f}  \n"
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
                st.info(
                    "💡 Importe um KMZ, cole um link do Google Maps ou informe as coordenadas "
                    "para ver o mapa de localização."
                )

    # ============================================================
    # CARD 2 — QUADRO DE AREAS
    # ============================================================
    with st.container(border=True):
        st.markdown("#### 📐 Quadro de Areas")

        col_gleba, col_modo = st.columns([3, 2])
        with col_gleba:
            area_gleba = numero_brl(
                "Area da gleba (m²)",
                value=float(terreno.areas.area_gleba_m2),
                key="aba1_area_gleba",
                min_value=1.0,
            )
        with col_modo:
            usar_pct = st.toggle(
                "Inserir areas em % da gleba",
                value=st.session_state.get("aba1_usar_pct", False),
                key="aba1_usar_pct",
                help="Quando ativado, informe cada area como % da gleba. "
                     "O m² e calculado automaticamente.",
            )

        def _area_input(label: str, key_m2: str, key_pct: str, valor_m2: float) -> float:
            """Retorna area em m², seja por input direto ou via % da gleba."""
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
                return numero_brl(
                    f"{label} (m²)",
                    value=valor_m2,
                    key=key_m2,
                    min_value=0.0,
                )

        col1, col2, col3 = st.columns(3)
        with col1:
            area_viario = _area_input(
                "Sistema viario",
                key_m2="aba1_area_viario",
                key_pct="aba1_pct_viario",
                valor_m2=float(terreno.areas.area_sistema_viario_m2),
            )
        with col2:
            area_verde = _area_input(
                "Area verde / lazer",
                key_m2="aba1_area_verde",
                key_pct="aba1_pct_verde",
                valor_m2=float(terreno.areas.area_verde_m2),
            )
            area_inst = _area_input(
                "Area institucional",
                key_m2="aba1_area_inst",
                key_pct="aba1_pct_inst",
                valor_m2=float(terreno.areas.area_institucional_m2),
            )
        with col3:
            area_app = _area_input(
                "APP",
                key_m2="aba1_area_app",
                key_pct="aba1_pct_app",
                valor_m2=float(terreno.areas.area_app_m2),
            )

        area_outras = area_viario + area_verde + area_inst + area_app
        area_lotes_sugerida = max(area_gleba - area_outras, 0)
        with col1:
            usar_subtracao = st.checkbox(
                "Calcular area de lotes por subtracao", value=True, key="aba1_calc_lotes"
            )
            if usar_subtracao:
                area_lotes = area_lotes_sugerida
                st.metric("Area de lotes (calculada)", formatar_num(area_lotes, 0) + " m²")
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

        # Metricas de aproveitamento
        if area_gleba > 0:
            _aprov = area_lotes / area_gleba * 100
            _infra = area_outras / area_gleba * 100
            _col_m1, _col_m2, _col_m3 = st.columns(3)
            with _col_m1:
                st.metric("Aproveitamento", f"{_aprov:.1f}%",
                          help="% da gleba destinada a lotes (area vendavel)")
            with _col_m2:
                st.metric("Infraestrutura", f"{_infra:.1f}%",
                          help="Sistema viario + areas verdes + institucional + APP")
            with _col_m3:
                _rel = area_lotes / area_viario if area_viario > 0 else 0
                st.metric("Lotes / Viario", f"{_rel:.2f}x",
                          help="Eficiencia: quanto de area vendavel por m² de viario")

    # ============================================================
    # CARD 3 — DATAS-CHAVE DO PROJETO
    # ============================================================
    with st.container(border=True):
        st.markdown("#### 📅 Datas-chave do Projeto")
        st.caption(
            "Termino do projeto e calculado automaticamente: maior valor entre o termino "
            "de obras e (data da ultima parcela + 2 meses)."
        )

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
            termino_obras_auto = st.checkbox(
                "Calcular termino pelas obras (Aba 3)",
                value=True,
                key="aba1_termino_auto",
                help="Usa: inicio_obras + duracao maxima das etapas da Aba 3. "
                     "Desmarque para definir manualmente.",
            )

            if termino_obras_auto and duracao_calculada_meses is not None:
                termino_obras_calculado = _add_meses(inicio_obras, duracao_calculada_meses)
                st.info(
                    f"**Termino de obras (calculado):**  \n"
                    f"{termino_obras_calculado.strftime('%m/%Y')}  \n"
                    f"({duracao_calculada_meses} meses de obra)"
                )
                termino_obras = termino_obras_calculado
            elif termino_obras_auto and duracao_calculada_meses is None:
                st.warning("Nao ha obras cadastradas na Aba 3. Usando o valor manual.")
                termino_obras = _mes_ano(
                    "Termino de obras (manual)",
                    terreno.datas.termino_obras,
                    "aba1_dt_fim_ob",
                )
            else:
                termino_obras = _mes_ano(
                    "Termino de obras (manual)",
                    terreno.datas.termino_obras,
                    "aba1_dt_fim_ob",
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
            st.warning(f"⚠️ {_msg_data}")

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
    with st.container(border=True):
        st.markdown("#### 🏘️ Tipologias de Lote")
        st.caption("Adicione, edite ou remova tipologias na tabela abaixo.")

        # Cache estavel: evita que o data_editor perca edicoes ao reconstruir o df do projeto
        _TIP_DF_KEY = "aba1_tip_df_cache"
        _TIP_HASH_KEY = "aba1_tip_proj_hash"

        def _tip_hash(tips: list) -> str:
            return str([(t.nome, t.quantidade, t.area_lote_m2, t.modo_preco, t.valor_unitario)
                        for t in tips])

        def _df_vazio() -> pd.DataFrame:
            return pd.DataFrame({
                "Nome": pd.Series(dtype="str"),
                "Quantidade": pd.Series(dtype="int"),
                "Area do lote (m²)": pd.Series(dtype="float"),
                "Modo de preco": pd.Series(dtype="str"),
                "Valor unitario (R$)": pd.Series(dtype="float"),
            })

        _proj_hash = _tip_hash(terreno.tipologias)
        if st.session_state.get(_TIP_HASH_KEY) != _proj_hash:
            # Projeto mudou externamente (novo projeto aberto, duplicar, etc.) — recarrega
            if terreno.tipologias:
                st.session_state[_TIP_DF_KEY] = pd.DataFrame([
                    {
                        "Nome": t.nome,
                        "Quantidade": t.quantidade,
                        "Area do lote (m²)": t.area_lote_m2,
                        "Modo de preco": t.modo_preco,
                        "Valor unitario (R$)": t.valor_unitario,
                    }
                    for t in terreno.tipologias
                ])
            else:
                st.session_state[_TIP_DF_KEY] = _df_vazio()
            st.session_state[_TIP_HASH_KEY] = _proj_hash
            # Limpa delta obsoleto do data_editor para evitar conflito de indices
            st.session_state.pop("aba1_tipologias", None)

        _df_base = st.session_state.get(_TIP_DF_KEY, _df_vazio())

        df_tipologias = st.data_editor(
            _df_base,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Nome": st.column_config.TextColumn(required=True),
                "Quantidade": st.column_config.NumberColumn(min_value=1, step=1, required=True),
                "Area do lote (m²)": st.column_config.NumberColumn(min_value=0.01, format="%.2f"),
                "Modo de preco": st.column_config.SelectboxColumn(
                    options=["por_m2", "por_lote"], required=True
                ),
                "Valor unitario (R$)": st.column_config.NumberColumn(min_value=0.01, format="%.2f"),
            },
            key="aba1_tipologias",
        )

        # Persiste o estado atual do data_editor no cache proprio
        st.session_state[_TIP_DF_KEY] = df_tipologias

        # Item 7: duplicar tipologia existente
        _nomes_tip = [
            str(row.get("Nome", "")).strip()
            for _, row in df_tipologias.iterrows()
            if str(row.get("Nome", "")).strip()
        ]
        if _nomes_tip:
            _c_dup_sel, _c_dup_btn = st.columns([3, 1])
            with _c_dup_sel:
                _nome_dup = st.selectbox(
                    "Duplicar tipologia",
                    options=_nomes_tip,
                    key="aba1_dup_sel",
                )
            with _c_dup_btn:
                st.write("")
                if st.button("Duplicar ↓", key="aba1_btn_dup", use_container_width=True,
                             help="Cria uma cópia da tipologia selecionada com os mesmos valores"):
                    _fonte = next(
                        (row for _, row in df_tipologias.iterrows()
                         if str(row.get("Nome", "")).strip() == _nome_dup),
                        None,
                    )
                    if _fonte is not None:
                        _novos = []
                        for _, _row in df_tipologias.iterrows():
                            _n = str(_row.get("Nome", "")).strip()
                            if not _n:
                                continue
                            try:
                                _novos.append(Tipologia(
                                    nome=_n,
                                    quantidade=int(_row["Quantidade"]),
                                    area_lote_m2=float(_row["Area do lote (m²)"]),
                                    modo_preco=str(_row["Modo de preco"]),
                                    valor_unitario=float(_row["Valor unitario (R$)"]),
                                ))
                            except Exception:
                                pass
                        _novos.append(Tipologia(
                            nome=f"{_nome_dup} (copia)",
                            quantidade=int(_fonte.get("Quantidade", 1) or 1),
                            area_lote_m2=float(_fonte.get("Area do lote (m²)", 0.0) or 0.0),
                            modo_preco=str(_fonte.get("Modo de preco", "por_lote")),
                            valor_unitario=float(_fonte.get("Valor unitario (R$)", 0.0) or 0.0),
                        ))
                        _novo_terreno = projeto.terreno.model_copy(update={"tipologias": _novos})
                        set_projeto(projeto.model_copy(update={"terreno": _novo_terreno}))
                        invalidar_resultado()
                        st.rerun()

        total_lotes = 0
        area_usada = 0.0
        vgv_total = 0.0
        for _, row in df_tipologias.iterrows():
            if not str(row.get("Nome", "")).strip():
                continue
            try:
                qtd = float(row.get("Quantidade", 0) or 0)
                area_t = float(row.get("Area do lote (m²)", 0) or 0)
                modo_t = str(row.get("Modo de preco", "por_lote"))
                valor_t = float(row.get("Valor unitario (R$)", 0) or 0)
                total_lotes += int(qtd)
                area_usada += qtd * area_t
                vgv_total += qtd * area_t * valor_t if modo_t == "por_m2" else qtd * valor_t
            except Exception:
                continue

        col_v, col_l, col_a = st.columns(3)
        with col_v:
            st.metric("VGV Total Bruto", formatar_brl(vgv_total))
        with col_l:
            st.metric("Total de Lotes", str(total_lotes))
        with col_a:
            if area_lotes > 0:
                saldo = area_lotes - area_usada
                ok = saldo >= 0
                icone = "✅" if ok else "❌"
                st.metric(
                    f"{icone} Area de lotes",
                    f"{formatar_num(area_usada, 0)} m²",
                )
                if ok:
                    st.caption(
                        f"Disponivel: {formatar_num(saldo, 0)} m² "
                        f"de {formatar_num(area_lotes, 0)} m²"
                    )
                    # B6: aviso de sub-utilizacao
                    if saldo > area_lotes * 0.02:
                        st.info(
                            f"💡 {formatar_num(saldo, 0)} m² sem tipologia ({saldo / area_lotes * 100:.1f}%). "
                            "Verifique se todas as tipologias foram cadastradas."
                        )
                else:
                    st.warning(
                        f"⚠️ Excedeu em {formatar_num(-saldo, 0)} m² "
                        f"o limite de {formatar_num(area_lotes, 0)} m²"
                    )
            else:
                st.metric("Area usada pelas tipologias", f"{formatar_num(area_usada, 0)} m²")

        # A1: barra de progresso do fechamento de area
        if area_lotes > 0:
            _frac = area_usada / area_lotes
            _bar_w = min(_frac * 100, 100)
            _cor_bar = "#22C55E" if _frac <= 1.0 else "#EF4444"
            _label_bar = (
                f"{formatar_num(area_usada, 0)} de {formatar_num(area_lotes, 0)} m²"
                f" ({_frac * 100:.1f}%)"
            )
            st.markdown(
                f'<div style="margin:4px 0 10px 0;">'
                f'<div style="font-size:11px;color:#9CA3AF;margin-bottom:4px;">Ocupacao da area de lotes</div>'
                f'<div style="background:#1F2937;border-radius:6px;height:12px;overflow:hidden;">'
                f'<div style="background:{_cor_bar};width:{_bar_w:.1f}%;height:100%;border-radius:6px;"></div>'
                f'</div>'
                f'<div style="font-size:11px;color:{_cor_bar};margin-top:3px;">{_label_bar}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ============================================================
    # NAVEGACAO
    # ============================================================
    btn_proximo_modulo("Terreno")

    # ============================================================
    # AUTO-SAVE
    # ============================================================
    try:
        tipologias = []
        for _, row in df_tipologias.iterrows():
            nome_t = str(row.get("Nome", "")).strip()
            if not nome_t:
                continue
            try:
                tipologias.append(
                    Tipologia(
                        nome=nome_t,
                        quantidade=int(row["Quantidade"]),
                        area_lote_m2=float(row["Area do lote (m²)"]),
                        modo_preco=str(row["Modo de preco"]),
                        valor_unitario=float(row["Valor unitario (R$)"]),
                    )
                )
            except Exception:
                continue

        if tipologias:
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
                tipologias=tipologias,
            )

            atual = projeto.terreno
            mudou = (
                atual.info.nome != novo_terreno.info.nome
                or atual.info.cidade != novo_terreno.info.cidade
                or atual.info.uf != novo_terreno.info.uf
                or atual.info.tipo_loteamento != novo_terreno.info.tipo_loteamento
                or atual.info.latitude != novo_terreno.info.latitude
                or atual.info.longitude != novo_terreno.info.longitude
                or atual.info.link_maps != novo_terreno.info.link_maps
                or atual.areas.area_gleba_m2 != novo_terreno.areas.area_gleba_m2
                or atual.areas.area_sistema_viario_m2 != novo_terreno.areas.area_sistema_viario_m2
                or atual.areas.area_verde_m2 != novo_terreno.areas.area_verde_m2
                or atual.areas.area_institucional_m2 != novo_terreno.areas.area_institucional_m2
                or atual.areas.area_app_m2 != novo_terreno.areas.area_app_m2
                or atual.areas.area_lotes_m2 != novo_terreno.areas.area_lotes_m2
                or atual.datas.inicio_projeto != novo_terreno.datas.inicio_projeto
                or atual.datas.aprovacao != novo_terreno.datas.aprovacao
                or atual.datas.lancamento_vendas != novo_terreno.datas.lancamento_vendas
                or atual.datas.inicio_obras != novo_terreno.datas.inicio_obras
                or atual.datas.termino_obras != novo_terreno.datas.termino_obras
                or len(atual.tipologias) != len(novo_terreno.tipologias)
                or any(
                    a.nome != b.nome or a.quantidade != b.quantidade
                    or a.area_lote_m2 != b.area_lote_m2 or a.modo_preco != b.modo_preco
                    or a.valor_unitario != b.valor_unitario
                    for a, b in zip(atual.tipologias, novo_terreno.tipologias)
                )
            )
            if mudou:
                projeto_atualizado = projeto.model_copy(update={"terreno": novo_terreno})
                set_projeto(projeto_atualizado)
                invalidar_resultado()
                # Atualiza hash para nao re-sincronizar o cache na proxima render
                st.session_state["aba1_tip_proj_hash"] = str(
                    [(t.nome, t.quantidade, t.area_lote_m2, t.modo_preco, t.valor_unitario)
                     for t in tipologias]
                )
    except Exception:
        pass  # erros de validacao serao mostrados pelo painel de pendencias
