"""
Aba 0 — Visao Geral (estilo "Resultado" da referencia).

Layout:
- Titulo + subtitulo
- Botoes de exportar (topo direito)
- Card "Saude do modelo" com checks
- Linha do tempo em 4 trilhas horizontais
- Grid 4x2 de cards de KPI
"""

from __future__ import annotations

import streamlit as st

from ..helpers import (
    formatar_brl,
    formatar_pct,
    get_projeto,
    get_resultado,
)
from ..tema_componentes import (
    renderizar_grade_kpis,
    renderizar_linha_tempo_trilhas,
    renderizar_saude_modelo,
    renderizar_titulo_modulo,
)
from ..validacoes import validar_projeto_completo


def renderizar() -> None:
    projeto = get_projeto()
    resultado = get_resultado()
    pendencias = validar_projeto_completo(projeto)

    # ============================================================
    # CABECALHO + BOTOES DE EXPORTAR
    # ============================================================
    col_titulo, col_btns = st.columns([3, 2])
    with col_titulo:
        renderizar_titulo_modulo("Visao Geral", numero=0)

    with col_btns:
        st.markdown('<div style="height: 32px;"></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.button("📊 Exportar Excel", use_container_width=True,
                      help="Use o botao na sidebar para baixar")
        with c2:
            # UX-09B: conectar botao PDF ao HTML export
            if resultado is not None:
                try:
                    from ...io_projeto.exportar_html import gerar_relatorio_html
                    nome_padrao = (
                        projeto.terreno.info.nome.lower()
                        .replace(" ", "_").replace("/", "_")
                    )
                    html_bytes = gerar_relatorio_html(projeto, resultado).encode("utf-8")
                    st.download_button(
                        "📄 Exportar PDF (Comite)",
                        data=html_bytes,
                        file_name=f"relatorio_{nome_padrao}.html",
                        mime="text/html",
                        use_container_width=True,
                        type="primary",
                        help="Baixa HTML. Abra no navegador e pressione Ctrl+P para salvar como PDF.",
                    )
                except Exception as e:
                    st.button("📄 Exportar PDF (Comite)",
                              use_container_width=True, type="primary",
                              disabled=True, help=f"Erro ao gerar relatorio: {e}")
            else:
                st.button("📄 Exportar PDF (Comite)",
                          use_container_width=True, type="primary",
                          disabled=True, help="Calcule o projeto primeiro para habilitar")

    # ============================================================
    # SAUDE DO MODELO
    # ============================================================
    checks = []

    soma_vendas = sum(f.percentual_estoque for f in projeto.receitas.curva_vendas)
    checks.append((
        abs(soma_vendas - 100.0) < 0.01,
        f"Velocidade de vendas soma {soma_vendas:.0f}%",
    ))

    todos_fluxos_ok = all(
        abs(f.percentual_sinal + f.percentual_obra
            + f.percentual_baloes + f.percentual_financiamento - 100.0) < 0.01
        for f in projeto.receitas.fluxos_recebiveis
    )
    checks.append((todos_fluxos_ok, "Perfil de pagamento soma 100%"))

    if projeto.obras.etapas:
        todas_obras_ok = True
        for et in projeto.obras.etapas:
            if et.curva == "customizada":
                soma = sum(et.curva_customizada)
                if abs(soma - 100.0) > 0.01:
                    todas_obras_ok = False
                    break
        checks.append((todas_obras_ok, "Curva de obras soma 100%"))
    else:
        checks.append((False, "Curva de obras nao definida"))

    checks.append((True, "Data de repasse >= termino de obras"))

    renderizar_saude_modelo(checks)

    # ============================================================
    # LINHA DO TEMPO (4 trilhas)
    # ============================================================
    renderizar_linha_tempo_trilhas(projeto)

    # ============================================================
    # GRID 4x2 DE KPIS
    # ============================================================
    def fmt_milhao(v):
        if abs(v) >= 1_000_000:
            return f"R$ {v/1_000_000:.2f}M"
        if abs(v) >= 1_000:
            return f"R$ {v/1_000:.0f}k"
        return formatar_brl(v)

    if resultado is None:
        # D3: estimativas pre-calculo
        st.markdown(
            '<div style="background:rgba(251,191,36,0.1);border-left:3px solid #FBBF24;'
            'padding:8px 12px;border-radius:0 4px 4px 0;font-size:12px;color:#FBBF24;'
            'margin:12px 0;">'
            '⚠️ Estimativas antes do calculo — dados precisos apos Calcular</div>',
            unsafe_allow_html=True,
        )
        try:
            vgv_est = sum(
                float(t.quantidade) * float(t.valor_unitario)
                for t in projeto.terreno.tipologias
            ) if projeto.terreno.tipologias else 0.0
            terreno_est = float(projeto.aquisicao.valor_total)
            obras = projeto.obras
            bdi_mult = (
                (1 + float(obras.bdi_percentual) / 100)
                * (1 + float(obras.contingencia_percentual) / 100)
            )
            if obras.modo == "detalhado" and obras.etapas:
                custo_dir = sum(float(e.valor_total) for e in obras.etapas)
            elif obras.resumido:
                areas = projeto.terreno.areas
                base_m2 = (
                    float(areas.area_sistema_viario_m2)
                    if obras.resumido.base_calculo == "sistema_viario"
                    else float(areas.area_lotes_m2)
                )
                custo_dir = base_m2 * float(obras.resumido.valor_por_m2)
            else:
                custo_dir = 0.0
            obras_est = custo_dir * bdi_mult
            desp_est = (
                sum(float(d.valor_total) for d in projeto.desenvolvimento.despesas)
                if hasattr(projeto.desenvolvimento, "despesas") else 0.0
            )
            margem_est = (
                (vgv_est - obras_est - terreno_est - desp_est) / vgv_est * 100
                if vgv_est > 0 else 0.0
            )
            _c1, _c2, _c3, _c4 = st.columns(4)
            with _c1:
                st.metric("VGV (est.)", fmt_milhao(vgv_est) if vgv_est > 0 else "—")
            with _c2:
                st.metric("Obras (est.)", fmt_milhao(obras_est) if obras_est > 0 else "—")
            with _c3:
                st.metric("Terreno", fmt_milhao(terreno_est) if terreno_est > 0 else "—")
            with _c4:
                st.metric("Margem Bruta (est.)", f"{margem_est:.1f}%" if vgv_est > 0 else "—")
        except Exception:
            pass

        # UX-07: hint sobre Modulo 9
        st.info(
            "💡 Clique em **'Calcular fluxo'** nas Acoes do projeto (sidebar) "
            "para ver os indicadores completos.  \n"
            "🏡 Lembre-se de configurar a **aquisição do terreno** no Módulo 9 "
            "antes de calcular."
        )
        return

    r = resultado.resumo
    ind = resultado.indicadores

    vgv_disponivel = r["vgv_vendavel"]
    lucro = r["lucro_liquido"]
    vpl = ind["vpl"]
    tir = ind.get("tir_anual")
    exp_max = abs(ind["exposicao_maxima"])
    mes_exp = ind["mes_exposicao_maxima"]
    pb = ind.get("payback_simples_meses")
    margem = (lucro / vgv_disponivel * 100) if vgv_disponivel > 0 else 0
    tma = projeto.parametros.tma_anual
    horizonte = r.get("horizonte_meses", 0)

    custo_total = r["total_saidas"]
    pe = (custo_total / vgv_disponivel * 100) if vgv_disponivel > 0 else 0

    # UX-08: veredito TIR vs TMA
    if tir is not None:
        tir_pct = tir * 100
        if tir_pct >= tma * 1.1:
            tir_cor = "verde"
            tir_sub = f"✅ Acima da TMA ({tma:.0f}% a.a.)"
        elif tir_pct >= tma:
            tir_cor = "verde"
            tir_sub = f"✅ Acima da TMA ({tma:.0f}% a.a.)"
        elif tir_pct >= tma * 0.85:
            tir_cor = "neutro"
            tir_sub = f"⚠️ Próxima da TMA ({tma:.0f}% a.a.)"
        else:
            tir_cor = "vermelho"
            tir_sub = f"❌ Abaixo da TMA ({tma:.0f}% a.a.)"
    else:
        tir_cor = "neutro"
        tir_sub = ""

    # UX-08: veredito VPL
    vpl_cor = "verde" if vpl > 0 else "vermelho"
    vpl_sub = "✅ Projeto viavel" if vpl > 0 else "❌ Projeto inviavel"

    # UX-13: payback com referencia ao horizonte
    pb_valor = f"Mes {pb}" if pb else "n/d"
    pb_sub = f"de {horizonte} meses no projeto" if (pb and horizonte > 0) else ""

    kpis = [
        # Linha 1
        {
            "label": "VGV Disponivel",
            "valor": fmt_milhao(vgv_disponivel),
            "cor": "neutro",
        },
        {
            "label": "Resultado Bruto",
            "valor": fmt_milhao(lucro),
            "cor": "verde" if lucro > 0 else "vermelho",
        },
        {
            "label": "Margem Bruta",
            "valor": f"{margem:.2f}%",
            "cor": "verde" if margem > 0 else "vermelho",
        },
        {
            "label": "TIR Anual",
            "valor": f"{tir*100:.2f}%" if tir is not None else "n/d",
            "sub": tir_sub,
            "cor": tir_cor,
        },
        # Linha 2
        {
            "label": f"VPL ({tma:.0f}% a.a.)",
            "valor": fmt_milhao(vpl),
            "sub": vpl_sub,
            "cor": vpl_cor,
        },
        {
            "label": "Pico de Exposicao",
            "valor": fmt_milhao(-exp_max),
            "sub": f"Mes {mes_exp}",
            "cor": "vermelho",
        },
        {
            "label": "Payback",
            "valor": pb_valor,
            "sub": pb_sub,
            "cor": "neutro",
        },
        {
            "label": "Ponto de Equilibrio",
            "valor": f"{pe:.2f}%",
            "sub": "do VGV",
            "cor": "neutro",
        },
    ]

    renderizar_grade_kpis(kpis)

    # UX-11: aviso de reajustes nao ativados
    if not projeto.reajustes.ativo:
        st.markdown(
            '<div style="background:rgba(96,165,250,0.08);border-left:3px solid #60A5FA;'
            'padding:8px 12px;border-radius:0 4px 4px 0;font-size:12px;color:#93C5FD;'
            'margin:16px 0 0 0;">'
            '💡 <b>Reajustes monetários não ativados</b> — o custo de obras pode estar '
            'subestimado sem a correção pelo INCC. Configure no '
            '<b>Módulo 14 — Reajustes</b>.</div>',
            unsafe_allow_html=True,
        )
