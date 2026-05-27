"""
Exportador HTML para impressao como PDF (C11 + ROADMAP item 5).

Gera relatorio executivo de 4 secoes prontas para apresentacao a comite, banco ou socio.
Layout: Capa + KPIs | DRE + Composicao de Custos | Fluxo de Caixa (SVG) | Empreendimento + Tipologias.
Nao requer dependencias extras — usa apenas HTML + CSS + SVG inline.
"""

from __future__ import annotations

from datetime import datetime

try:
    from ..engine.financiamento_engine import simular_financiamento as _sim_fin
except Exception:
    _sim_fin = None


# =====================================================================
# Formatadores
# =====================================================================

def _fmt_brl(v: float | None) -> str:
    if v is None:
        return "—"
    neg = v < 0
    s = f"R$ {abs(v):,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"({s})" if neg else s


def _fmt_pct(v: float | None, casas: int = 1) -> str:
    if v is None:
        return "—"
    return f"{v * 100:.{casas}f}%"


def _fmt_abrev(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"{v / 1e6:.1f}M"
    if abs(v) >= 1_000:
        return f"{v / 1e3:.0f}k"
    return f"{v:.0f}"


def _cor(v: float | None, positivo_bom: bool = True) -> str:
    if v is None:
        return "#334155"
    ok = (v > 0) if positivo_bom else (v < 0)
    return "#15803d" if ok else "#b91c1c"


# =====================================================================
# Grafico SVG de fluxo de caixa
# =====================================================================

def _svg_fluxo_caixa(df, horizonte: int) -> str:
    """Gera SVG inline do grafico de fluxo de caixa mensal (entradas, saidas, saldo acumulado)."""
    rows: list[tuple[int, float, float, float]] = []
    for _, row in df.iterrows():
        m = int(row["Mes"])
        if m > horizonte:
            break
        rows.append((
            m,
            float(row.get("Total Entradas", 0) or 0),
            float(row.get("Total Saidas",   0) or 0),
            float(row.get("Saldo Acumulado", 0) or 0),
        ))

    if not rows:
        return '<p style="color:#94a3b8;font-size:9pt;">Sem dados de fluxo para exibir.</p>'

    n = len(rows)
    W, H = 700, 260
    pl, pr, pt, pb = 55, 10, 16, 36

    meses = [r[0] for r in rows]
    ent   = [r[1] for r in rows]
    sai   = [r[2] for r in rows]
    sal   = [r[3] for r in rows]

    all_vals = ent + sai + sal + [0.0]
    v_min = min(all_vals)
    v_max = max(all_vals)
    if abs(v_max - v_min) < 1:
        v_max = v_min + 1
    v_range = v_max - v_min
    pw = W - pl - pr
    ph = H - pt - pb

    def ys(v: float) -> float:
        return pt + ph * (1.0 - (v - v_min) / v_range)

    def xc(i: int) -> float:
        return pl + (i + 0.5) * pw / n

    zero_y = ys(0.0)
    bw = max(1.0, pw / n * 0.42)

    # Barras de entradas e saidas
    bars = ""
    for i, (e, s) in enumerate(zip(ent, sai)):
        x0 = pl + i * pw / n + pw / n * 0.05
        # Entrada (verde)
        ye = ys(e)
        he = abs(zero_y - ye)
        bars += (
            f'<rect x="{x0:.1f}" y="{min(ye, zero_y):.1f}"'
            f' width="{bw:.1f}" height="{max(he, 0.5):.1f}"'
            f' fill="#22c55e" opacity="0.7"/>'
        )
        # Saida (vermelho, levemente sobreposto)
        x1 = x0 + bw * 0.08
        ys_v = ys(s)
        hs = abs(zero_y - ys_v)
        bars += (
            f'<rect x="{x1:.1f}" y="{min(ys_v, zero_y):.1f}"'
            f' width="{bw:.1f}" height="{max(hs, 0.5):.1f}"'
            f' fill="#f87171" opacity="0.55"/>'
        )

    # Linha do saldo acumulado
    pts = " ".join(f"{xc(i):.1f},{ys(s):.1f}" for i, s in enumerate(sal))

    # Ponto de exposicao maxima
    idx_min = sal.index(min(sal)) if sal else 0
    dot_exp = (
        f'<circle cx="{xc(idx_min):.1f}" cy="{ys(sal[idx_min]):.1f}"'
        f' r="3.5" fill="#dc2626" stroke="white" stroke-width="1"/>'
    ) if sal else ""

    # Ponto de payback (primeiro mes em que saldo volta a >= 0 apos ser negativo)
    payback_dot = ""
    foi_neg = False
    for i, s in enumerate(sal):
        if s < 0:
            foi_neg = True
        if foi_neg and s >= 0:
            payback_dot = (
                f'<circle cx="{xc(i):.1f}" cy="{ys(0):.1f}"'
                f' r="3.5" fill="#16a34a" stroke="white" stroke-width="1"/>'
            )
            break

    # Grade e labels eixo Y
    grid = ""
    ylabels = ""
    for frac in [0.0, 0.25, 0.5, 0.75, 1.0]:
        v = v_min + frac * v_range
        y = ys(v)
        grid += (
            f'<line x1="{pl}" y1="{y:.1f}" x2="{W - pr}" y2="{y:.1f}"'
            f' stroke="#e2e8f0" stroke-width="0.5"/>'
        )
        ylabels += (
            f'<text x="{pl - 3}" y="{y + 3:.1f}" text-anchor="end"'
            f' font-size="8" fill="#64748b">{_fmt_abrev(v)}</text>'
        )

    # Labels eixo X (passo dinamico por horizonte)
    label_step = 24 if n > 120 else 12 if n > 60 else 6
    xlabels = ""
    for i, m in enumerate(meses):
        if m % label_step == 0 or i == n - 1:
            xlabels += (
                f'<text x="{xc(i):.1f}" y="{H - 8}" text-anchor="middle"'
                f' font-size="8" fill="#64748b">M{m}</text>'
            )

    # Legenda
    lx = pl
    leg = (
        f'<rect x="{lx}" y="2" width="10" height="8" fill="#22c55e" opacity="0.7"/>'
        f'<text x="{lx + 14}" y="10" font-size="8.5" fill="#333">Entradas</text>'
        f'<rect x="{lx + 80}" y="2" width="10" height="8" fill="#f87171" opacity="0.55"/>'
        f'<text x="{lx + 94}" y="10" font-size="8.5" fill="#333">Saidas</text>'
        f'<line x1="{lx + 155}" y1="6" x2="{lx + 170}" y2="6"'
        f' stroke="#1d4ed8" stroke-width="2"/>'
        f'<text x="{lx + 174}" y="10" font-size="8.5" fill="#333">Saldo Acumulado</text>'
        f'<circle cx="{lx + 290}" cy="6" r="4" fill="#dc2626"/>'
        f'<text x="{lx + 298}" y="10" font-size="8.5" fill="#333">Exposicao max.</text>'
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">'
        f'<rect width="{W}" height="{H}" fill="#f8fafc" rx="4"'
        f' stroke="#e2e8f0" stroke-width="0.5"/>'
        f'{grid}'
        f'<line x1="{pl}" y1="{zero_y:.1f}" x2="{W - pr}" y2="{zero_y:.1f}"'
        f' stroke="#94a3b8" stroke-width="1" stroke-dasharray="4,2"/>'
        f'{bars}'
        f'<polyline points="{pts}" fill="none" stroke="#1d4ed8" stroke-width="1.8"/>'
        f'{dot_exp}{payback_dot}'
        f'{ylabels}{xlabels}{leg}'
        f'</svg>'
    )


# =====================================================================
# Barras CSS de composicao de custos
# =====================================================================

def _html_barras_custos(categorias: list[tuple[str, float]], total: float) -> str:
    """Gera HTML com barras horizontais para composicao de custos, ordenadas por valor."""
    if total <= 0:
        return ""
    linhas = ""
    for nome_cat, valor in sorted(categorias, key=lambda x: x[1], reverse=True):
        if valor <= 0:
            continue
        pct = valor / total * 100
        w = min(100.0, pct)
        linhas += (
            f'<div style="margin-bottom:7px;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:8.5pt;margin-bottom:2px;">'
            f'<span>{nome_cat}</span>'
            f'<span style="color:#334155;">{_fmt_brl(valor)}'
            f' &nbsp;<b>{pct:.1f}%</b></span></div>'
            f'<div style="background:#e2e8f0;border-radius:3px;height:10px;">'
            f'<div style="background:#1d4ed8;width:{w:.1f}%;height:10px;'
            f'border-radius:3px;"></div></div></div>'
        )
    return linhas


# =====================================================================
# Funcao principal
# =====================================================================

def gerar_relatorio_html(projeto, resultado) -> str:
    """Gera o relatorio HTML executivo completo para impressao como PDF."""
    r   = resultado.resumo
    ind = resultado.indicadores
    info = projeto.terreno.info
    datas = projeto.terreno.datas

    nome     = info.nome
    cidade   = f"{info.cidade}/{info.uf}"
    data_rel = datetime.now().strftime("%d/%m/%Y")
    hora_rel = datetime.now().strftime("%H:%M")

    def fmt_data(d) -> str:
        meses_pt = [
            "jan", "fev", "mar", "abr", "mai", "jun",
            "jul", "ago", "set", "out", "nov", "dez",
        ]
        return f"{meses_pt[d.month - 1]}/{d.year}"

    # ---- valores do resumo ----
    vgv_bruto    = r.get("vgv_bruto",           0) or 0
    vgv_vendavel = r.get("vgv_vendavel",         0) or 0
    vgv_efetivo  = r.get("vgv_efetivo_vendavel", vgv_vendavel) or vgv_vendavel
    total_saidas = r.get("total_saidas",         0) or 0
    lucro        = r.get("lucro_liquido",        0) or 0
    total_lotes  = r.get("total_lotes",          0) or 0
    horizonte    = r.get("horizonte_meses",      0) or 0
    mes_termino  = r.get("mes_termino_obras",    0) or 0
    rec_fin      = r.get("receita_financeira",   0) or 0
    rec_total    = r.get("vgv_total_recebido",   0) or 0
    permuta_fis  = vgv_bruto - vgv_vendavel
    ajuste_pp    = vgv_efetivo - vgv_vendavel

    sem_exposicao = abs(ind.get("exposicao_maxima", 0)) < 1.0
    tir       = None if sem_exposicao else ind.get("tir_anual")
    vpl       = ind.get("vpl")
    payback   = None if sem_exposicao else ind.get("payback_simples_meses")
    pb_desc   = None if sem_exposicao else ind.get("payback_descontado_meses")
    exposicao = ind.get("exposicao_maxima")
    mult      = ind.get("lucro_sobre_exposicao")
    mes_exp   = ind.get("mes_exposicao_maxima", "—")
    margem_vv = r.get("margem_sobre_vgv_vendavel")
    margem_vb = r.get("margem_sobre_vgv_bruto")
    tma_aa    = projeto.parametros.tma_anual

    por_lote    = total_saidas / total_lotes if total_lotes > 0 else 0
    vgv_p_lote  = vgv_bruto / total_lotes if total_lotes > 0 else 0

    # ---- SVG fluxo de caixa ----
    svg_fluxo = _svg_fluxo_caixa(resultado.fluxo_caixa, horizonte)

    # ---- Categorias de custo ----
    cats = [
        ("Aquisicao Terreno",       r.get("custo_terreno_aquisicao",  0) or 0),
        ("Cartorio / Registro",     r.get("custo_terreno_cartorio",   0) or 0),
        ("Obras de Infraestrutura", r.get("custo_obras",              0) or 0),
        ("Projetos Tecnicos",       r.get("custo_projetos",           0) or 0),
        ("Licenciamento / Legal",   r.get("custo_licenciamento",      0) or 0),
        ("Marketing / Comercial",   r.get("custo_marketing",          0) or 0),
        ("Administracao",           r.get("custo_administracao",      0) or 0),
        ("Outros Desenvolvimento",  r.get("custo_outros",             0) or 0),
        ("Comissao de Vendas",      r.get("custo_comissao",           0) or 0),
        ("Impostos / Tributacao",   r.get("custo_impostos",           0) or 0),
        ("Permuta Financeira",      r.get("custo_permuta_financeira", 0) or 0),
    ]
    html_barras = _html_barras_custos(cats, total_saidas)

    # ---- Linhas da DRE — permuta, preco progressivo, juros ----
    perm_row = (
        f"<tr><td style='padding-left:14px'>(-) Permuta Fisica</td>"
        f"<td>({_fmt_brl(permuta_fis)})</td><td></td><td></td></tr>"
    ) if permuta_fis > 0 else ""

    pp_row = ""
    if abs(ajuste_pp) > 1:
        sinal = "+" if ajuste_pp > 0 else ""
        pp_row = (
            f"<tr><td style='padding-left:14px'>(+/-) Ajuste Preco Progressivo</td>"
            f"<td>{sinal}{_fmt_brl(ajuste_pp)}</td><td></td><td></td></tr>"
        )

    juros_row = (
        f"<tr><td style='padding-left:14px'>(+) Receita Financeira (Juros)</td>"
        f"<td>+ {_fmt_brl(rec_fin)}</td><td></td><td></td></tr>"
    ) if rec_fin > 0 else ""

    # Linhas de custo na DRE
    cat_rows_dre = ""
    for nome_cat, valor in sorted(cats, key=lambda x: x[1], reverse=True):
        if valor > 0:
            pct_s = valor / total_saidas * 100 if total_saidas > 0 else 0
            pct_v = valor / (vgv_efetivo or 1) * 100
            cat_rows_dre += (
                f"<tr><td style='padding-left:12px'>{nome_cat}</td>"
                f"<td>({_fmt_brl(valor)})</td>"
                f"<td style='text-align:center'>{pct_v:.1f}%</td>"
                f"<td style='text-align:center'>{pct_s:.1f}%</td></tr>"
            )

    # ---- Financiamento (se ativo) ou preview (se inativo com taxa configurada) ----
    fin_ativo = r.get("financiamento_ativo", False)
    fin_html = ""
    if fin_ativo:
        custo_fin  = r.get("custo_financiamento_total", 0) or 0
        saldo_max  = r.get("saldo_devedor_maximo",      0) or 0
        tir_sem_fn = r.get("tir_anual_sem_fin")
        fin_extra = (
            f"<tr><td>TIR sem financiamento</td>"
            f"<td style='text-align:right'>{_fmt_pct(tir_sem_fn)}</td></tr>"
        ) if tir_sem_fn else ""
        fin_html = (
            f'<div style="margin-top:12px;background:#fafafa;border:1px solid #e2e8f0;'
            f'border-radius:4px;padding:10px 12px;">'
            f'<div style="font-weight:700;font-size:9pt;color:#1d4ed8;margin-bottom:6px;">'
            f'Financiamento Bancario (ativo)</div>'
            f'<table style="width:100%;border-collapse:collapse;font-size:9pt;">'
            f'<tr><td>Custo total</td>'
            f'<td style="text-align:right">{_fmt_brl(custo_fin)}</td></tr>'
            f'<tr><td>Saldo devedor maximo</td>'
            f'<td style="text-align:right">{_fmt_brl(saldo_max)}</td></tr>'
            f'{fin_extra}'
            f'</table></div>'
        )
    else:
        # Preview estimado mesmo com financiamento desativado
        _taxa_am = getattr(getattr(projeto, "financiamento", None), "taxa_juros_am", 0) or 0
        if _taxa_am > 0 and _sim_fin is not None:
            try:
                import numpy as np
                _fluxo_base = resultado.fluxo_caixa["Saldo do Mes"].to_numpy()
                _cfg = projeto.financiamento
                _sim = _sim_fin(_fluxo_base, _cfg, resultado.horizonte)
                _custo_est = float(_sim["juros_banco"].sum())
                _pico_est  = float(_sim["saldo_devedor"].max())
                _taxa_aa = (1 + _taxa_am / 100) ** 12 - 1
                if _custo_est > 1 or _pico_est > 1:
                    fin_html = (
                        f'<div style="margin-top:12px;background:#eff6ff;'
                        f'border:1px solid #bfdbfe;border-radius:4px;padding:10px 12px;">'
                        f'<div style="font-weight:700;font-size:9pt;color:#1d4ed8;margin-bottom:4px;">'
                        f'Estimativa de Custo Financeiro (nao ativado)</div>'
                        f'<div style="font-size:8pt;color:#64748b;margin-bottom:6px;">'
                        f'Se usar CCB/CCE a {_taxa_am:.2f}% a.m. ({_taxa_aa * 100:.1f}% a.a.) '
                        f'sem limite de credito. Fluxo nao alterado.</div>'
                        f'<table style="width:100%;border-collapse:collapse;font-size:9pt;">'
                        f'<tr><td>Juros estimados (total)</td>'
                        f'<td style="text-align:right;color:#b91c1c">{_fmt_brl(_custo_est)}</td></tr>'
                        f'<tr><td>Pico do saldo devedor</td>'
                        f'<td style="text-align:right">{_fmt_brl(_pico_est)}</td></tr>'
                        f'</table></div>'
                    )
            except Exception:
                pass

    # ---- Reajustes (se ativo) ----
    reaj_ativo = r.get("reajustes_ativo", False)
    reaj_html = ""
    if reaj_ativo:
        var_incc   = r.get("variacao_custo_obras_incc", 0) or 0
        corr_parc  = r.get("receita_correcao_total",    0) or 0
        reaj_html = (
            f'<div style="margin-top:12px;background:#fafafa;border:1px solid #e2e8f0;'
            f'border-radius:4px;padding:10px 12px;">'
            f'<div style="font-weight:700;font-size:9pt;color:#1d4ed8;margin-bottom:6px;">'
            f'Reajustes Monetarios</div>'
            f'<table style="width:100%;border-collapse:collapse;font-size:9pt;">'
            f'<tr><td>Variacao INCC nas obras</td>'
            f'<td style="text-align:right">{_fmt_brl(var_incc)}</td></tr>'
            f'<tr><td>Correcao recebida nas parcelas</td>'
            f'<td style="text-align:right">+ {_fmt_brl(corr_parc)}</td></tr>'
            f'</table></div>'
        )

    # ---- Tipologias ----
    linhas_tipo = ""
    for tip in projeto.terreno.tipologias:
        pct_vgv = tip.vgv_total / vgv_bruto * 100 if vgv_bruto > 0 else 0
        gio_str = f" +{tip.gio_percentual:.1f}%" if tip.gio_percentual > 0 else ""
        linhas_tipo += (
            f"<tr>"
            f"<td>{tip.nome}{gio_str}</td>"
            f"<td style='text-align:center'>{tip.quantidade}</td>"
            f"<td style='text-align:right'>{tip.area_lote_m2:,.0f} m²</td>"
            f"<td style='text-align:right'>{_fmt_brl(tip.vgv_lote)}</td>"
            f"<td style='text-align:right'>{_fmt_brl(tip.vgv_total)}</td>"
            f"<td style='text-align:center'>{pct_vgv:.1f}%</td>"
            f"</tr>"
        )

    # ---- Legenda do payback no grafico ----
    payback_leg = (
        f' &nbsp;<span style="color:#16a34a">&#9679;</span> Payback (M{payback})'
        if payback else ""
    )

    # ---- Cor do resultado ----
    res_bg = "#dcfce7" if lucro >= 0 else "#fee2e2"

    # =====================================================================
    # HTML FINAL
    # =====================================================================
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatorio de Viabilidade — {nome}</title>
<style>
@page {{ margin: 14mm 17mm 17mm; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: Arial, Helvetica, sans-serif; color: #1e293b; font-size: 9.5pt;
       line-height: 1.5; background: white; }}

/* Aviso de impressao */
.print-hint {{ background: #fefce8; border: 1px solid #fde047; padding: 9px 14px;
  margin-bottom: 20px; border-radius: 6px; font-size: 9pt; }}

/* Capa */
.capa {{ border-bottom: 3px solid #1d4ed8; padding-bottom: 12px; margin-bottom: 16px;
  display: flex; justify-content: space-between; align-items: flex-end; }}
.capa-left h1 {{ color: #1A1916; font-size: 18pt; letter-spacing: -0.5px; margin-bottom: 3px; }}
.capa-left .sub  {{ color: #475569; font-size: 10pt; }}
.capa-left .meta {{ color: #94a3b8; font-size: 8pt; margin-top: 4px; }}
.capa-right {{ text-align: right; }}
.capa-right .badge {{ background: #1d4ed8; color: white; padding: 3px 11px;
  border-radius: 4px; font-size: 8.5pt; font-weight: 600; }}
.capa-right .tir-big {{ font-size: 19pt; font-weight: 700; color: {_cor(tir)}; margin-top: 3px; }}
.capa-right .tir-label {{ font-size: 7pt; color: #94a3b8; }}

/* KPI Grid */
.kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 7px; margin: 12px 0; }}
.kpi {{ border: 1px solid #e2e8f0; border-radius: 5px; padding: 8px 10px; background: #f8fafc; }}
.kpi-label {{ font-size: 7pt; color: #64748b; margin-bottom: 2px; }}
.kpi-value {{ font-size: 12pt; font-weight: 700; }}
.kpi-sub {{ font-size: 6.5pt; color: #94a3b8; margin-top: 1px; }}

/* Titulos de secao */
.sec {{ color: #1d4ed8; font-size: 10.5pt; font-weight: 700; margin: 16px 0 7px;
  border-bottom: 1px solid #dbeafe; padding-bottom: 3px; page-break-after: avoid; }}

/* Tabelas */
table.t {{ width: 100%; border-collapse: collapse; font-size: 9pt; page-break-inside: avoid; }}
table.t thead th {{ background: #1A1916; color: white; padding: 5px 8px; text-align: left; }}
table.t tbody td {{ padding: 3px 8px; border-bottom: 1px solid #f1f5f9; }}
tr.sub {{ background: #dbeafe !important; font-weight: 700; }}
tr.res {{ font-weight: 700; font-size: 10pt; background: {res_bg} !important; }}

table.ttipo {{ width: 100%; border-collapse: collapse; font-size: 8.5pt; margin-top: 6px; }}
table.ttipo thead th {{ background: #1A1916; color: white; padding: 5px 8px; }}
table.ttipo tbody td {{ padding: 4px 8px; border-bottom: 1px solid #f1f5f9; }}
tr.ttotal {{ font-weight: 700; background: #dbeafe !important; }}

/* Layout 2 colunas */
.cols2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}

/* Quebra de pagina */
.pb {{ page-break-before: always; }}

/* Footer */
.footer {{ font-size: 7.5pt; color: #94a3b8; text-align: center; margin-top: 24px;
  border-top: 1px solid #e2e8f0; padding-top: 6px; }}

@media print {{
  .print-hint {{ display: none; }}
  body {{ font-size: 9pt; }}
  table {{ page-break-inside: avoid; }}
  .kpi {{ page-break-inside: avoid; }}
  .kpi-grid {{ page-break-inside: avoid; }}
  .cols2 > div {{ page-break-inside: avoid; }}
  .sec {{ page-break-after: avoid; }}
  svg {{ page-break-inside: avoid; }}
}}
</style>
</head>
<body>

<!-- Aviso -->
<div class="print-hint">
  <strong>Para gerar PDF:</strong> pressione <strong>Ctrl+P</strong> &rarr;
  selecione <em>"Salvar como PDF"</em>. Ative <em>"Graficos de fundo"</em>
  nas opcoes de impressao para preservar as cores.
</div>

<!-- ======================== PAGINA 1: CAPA + KPIs ======================== -->
<div class="capa">
  <div class="capa-left">
    <h1>Viabilidade Economica</h1>
    <div class="sub"><strong>{nome}</strong> &mdash; {cidade}</div>
    <div class="meta">
      Gerado em {data_rel} {hora_rel} &nbsp;|&nbsp;
      Horizonte: {horizonte} meses &nbsp;|&nbsp;
      Termino obras: M{mes_termino} ({fmt_data(datas.termino_obras)}) &nbsp;|&nbsp;
      TMA: {tma_aa:.1f}% a.a.
    </div>
  </div>
  <div class="capa-right">
    <div class="badge">Relatorio de Comite</div>
    <div class="tir-big">{_fmt_pct(tir)}</div>
    <div class="tir-label">TIR Anual</div>
  </div>
</div>

<div class="kpi-grid">
  <div class="kpi">
    <div class="kpi-label">VGV Bruto (preco base)</div>
    <div class="kpi-value" style="color:#1A1916">{_fmt_brl(vgv_bruto)}</div>
    <div class="kpi-sub">{total_lotes} lotes &nbsp;|&nbsp; {_fmt_brl(vgv_p_lote)} / lote</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Lucro Liquido</div>
    <div class="kpi-value" style="color:{_cor(lucro)}">{_fmt_brl(lucro)}</div>
    <div class="kpi-sub">Margem s/ VGV vendavel: {_fmt_pct(margem_vv)}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">VPL &nbsp;<span style="font-size:6.5pt;font-weight:400">(TMA {tma_aa:.1f}% a.a.)</span></div>
    <div class="kpi-value" style="color:{_cor(vpl)}">{_fmt_brl(vpl)}</div>
    <div class="kpi-sub">Payback descontado: {str(pb_desc) + " m" if pb_desc else "—"}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">TIR Anual</div>
    <div class="kpi-value" style="color:{_cor(tir)}">{_fmt_pct(tir)}</div>
    <div class="kpi-sub">TIR mensal: {_fmt_pct(ind.get("tir_mensal"))}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Exposicao Maxima de Caixa</div>
    <div class="kpi-value" style="color:#b91c1c">{_fmt_brl(exposicao)}</div>
    <div class="kpi-sub">No mes M{mes_exp}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Payback Simples</div>
    <div class="kpi-value" style="color:#1A1916">{str(payback) + " meses" if payback else "—"}</div>
    <div class="kpi-sub">&nbsp;</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Multiplicador (Lucro / Exposicao)</div>
    <div class="kpi-value" style="color:{_cor(mult)}">{f"{mult:.2f}x" if mult else "—"}</div>
    <div class="kpi-sub">&nbsp;</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Margem s/ VGV Bruto</div>
    <div class="kpi-value" style="color:{_cor(margem_vb)}">{_fmt_pct(margem_vb)}</div>
    <div class="kpi-sub">Total saidas: {_fmt_brl(total_saidas)}</div>
  </div>
</div>

<!-- ======================== PAGINA 2: DRE + CUSTOS ======================== -->
<div class="pb"></div>

<div class="sec">Demonstrativo de Resultado (DRE)</div>
<table class="t">
<thead>
  <tr>
    <th style="width:52%">Descricao</th>
    <th>Valor</th>
    <th style="width:13%;text-align:center">% VGV Vendavel</th>
    <th style="width:11%;text-align:center">% Saidas</th>
  </tr>
</thead>
<tbody>
<tr>
  <td><b>VGV Bruto (preco base)</b></td>
  <td>{_fmt_brl(vgv_bruto)}</td>
  <td style="text-align:center">{_fmt_pct(vgv_bruto / vgv_vendavel if vgv_vendavel else None)}</td>
  <td></td>
</tr>
{perm_row}
<tr class="sub">
  <td>VGV Vendavel (base de calculo)</td>
  <td>{_fmt_brl(vgv_vendavel)}</td>
  <td style="text-align:center">100,0%</td>
  <td></td>
</tr>
{pp_row}
{juros_row}
<tr class="sub">
  <td>Receita Total Recebida</td>
  <td>{_fmt_brl(rec_total)}</td>
  <td style="text-align:center">{_fmt_pct(rec_total / vgv_vendavel if vgv_vendavel else None)}</td>
  <td></td>
</tr>
<tr><td>&nbsp;</td><td></td><td></td><td></td></tr>
{cat_rows_dre}
<tr class="sub">
  <td>(-) Total de Saidas</td>
  <td>({_fmt_brl(total_saidas)})</td>
  <td style="text-align:center">({_fmt_pct(total_saidas / vgv_vendavel if vgv_vendavel else None)})</td>
  <td style="text-align:center">100%</td>
</tr>
<tr class="res">
  <td>Resultado Liquido</td>
  <td>{_fmt_brl(lucro)}</td>
  <td style="text-align:center"><b>{_fmt_pct(margem_vv)}</b></td>
  <td></td>
</tr>
</tbody>
</table>

<div class="sec">Composicao dos Custos</div>
<div class="cols2">
  <div>
    {html_barras}
  </div>
  <div>
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:4px;padding:10px 12px;">
      <table style="width:100%;border-collapse:collapse;font-size:9pt;">
        <tr>
          <td style="padding:3px 0;border-bottom:1px solid #f1f5f9;">Custo por lote (medio)</td>
          <td style="text-align:right;font-weight:600;padding:3px 0;border-bottom:1px solid #f1f5f9;">{_fmt_brl(por_lote)}</td>
        </tr>
        <tr>
          <td style="padding:3px 0;border-bottom:1px solid #f1f5f9;">VGV por lote (medio)</td>
          <td style="text-align:right;font-weight:600;padding:3px 0;border-bottom:1px solid #f1f5f9;">{_fmt_brl(vgv_p_lote)}</td>
        </tr>
        <tr>
          <td style="padding:3px 0;">Total de saidas</td>
          <td style="text-align:right;font-weight:600;padding:3px 0;">{_fmt_brl(total_saidas)}</td>
        </tr>
      </table>
    </div>
    {fin_html}
    {reaj_html}
  </div>
</div>

<!-- ======================== PAGINA 3: FLUXO DE CAIXA ======================== -->
<div class="pb"></div>

<div class="sec">Curva de Caixa — Entradas, Saidas e Saldo Acumulado</div>
<div style="margin: 8px 0 4px;">
  {svg_fluxo}
</div>
<p style="font-size:8pt;color:#64748b;margin-top:6px;">
  <span style="display:inline-block;width:10px;height:8px;background:#22c55e;opacity:0.7;margin-right:4px;vertical-align:middle;"></span>Entradas mensais &nbsp;
  <span style="display:inline-block;width:10px;height:8px;background:#f87171;opacity:0.55;margin-right:4px;vertical-align:middle;"></span>Saidas mensais &nbsp;
  <span style="color:#1d4ed8;font-weight:700">&mdash;</span> Saldo Acumulado &nbsp;
  <span style="color:#dc2626;">&#9679;</span> Exposicao max. (M{mes_exp}){payback_leg}
</p>

<!-- ======================== PAGINA 4: EMPREENDIMENTO + TIPOLOGIAS ======================== -->
<div class="pb"></div>

<div class="sec">Dados do Empreendimento</div>
<div class="cols2">
  <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:4px;padding:10px 12px;">
    <table style="width:100%;border-collapse:collapse;font-size:9pt;">
      <tr><td style="padding:3px 0;border-bottom:1px solid #f1f5f9;">Area da Gleba</td>
          <td style="text-align:right;font-weight:600;padding:3px 0;border-bottom:1px solid #f1f5f9;">{projeto.terreno.areas.area_gleba_m2:,.0f} m²</td></tr>
      <tr><td style="padding:3px 0;border-bottom:1px solid #f1f5f9;">Area de Lotes</td>
          <td style="text-align:right;font-weight:600;padding:3px 0;border-bottom:1px solid #f1f5f9;">{projeto.terreno.areas.area_lotes_m2:,.0f} m²</td></tr>
      <tr><td style="padding:3px 0;border-bottom:1px solid #f1f5f9;">Aproveitamento (lotes/gleba)</td>
          <td style="text-align:right;font-weight:600;padding:3px 0;border-bottom:1px solid #f1f5f9;">{projeto.terreno.areas.aproveitamento * 100:.1f}%</td></tr>
      <tr><td style="padding:3px 0;">Total de Lotes</td>
          <td style="text-align:right;font-weight:600;padding:3px 0;">{total_lotes} lotes</td></tr>
    </table>
  </div>
  <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:4px;padding:10px 12px;">
    <table style="width:100%;border-collapse:collapse;font-size:9pt;">
      <tr><td style="padding:3px 0;border-bottom:1px solid #f1f5f9;">Inicio do Projeto (M0)</td>
          <td style="text-align:right;font-weight:600;padding:3px 0;border-bottom:1px solid #f1f5f9;">{fmt_data(datas.inicio_projeto)}</td></tr>
      <tr><td style="padding:3px 0;border-bottom:1px solid #f1f5f9;">Lancamento de Vendas</td>
          <td style="text-align:right;font-weight:600;padding:3px 0;border-bottom:1px solid #f1f5f9;">{fmt_data(datas.lancamento_vendas)}</td></tr>
      <tr><td style="padding:3px 0;border-bottom:1px solid #f1f5f9;">Inicio de Obras</td>
          <td style="text-align:right;font-weight:600;padding:3px 0;border-bottom:1px solid #f1f5f9;">{fmt_data(datas.inicio_obras)}</td></tr>
      <tr><td style="padding:3px 0;">Termino de Obras</td>
          <td style="text-align:right;font-weight:600;padding:3px 0;">{fmt_data(datas.termino_obras)}</td></tr>
    </table>
  </div>
</div>

<div class="sec">Quadro de Tipologias</div>
<table class="ttipo">
<thead>
  <tr>
    <th>Tipologia</th>
    <th style="text-align:center">Qtd</th>
    <th style="text-align:right">Area / Lote</th>
    <th style="text-align:right">VGV / Lote</th>
    <th style="text-align:right">VGV Total</th>
    <th style="text-align:center">% VGV</th>
  </tr>
</thead>
<tbody>
{linhas_tipo}
<tr class="ttotal">
  <td>TOTAL</td>
  <td style="text-align:center">{total_lotes}</td>
  <td></td>
  <td></td>
  <td style="text-align:right">{_fmt_brl(vgv_bruto)}</td>
  <td style="text-align:center">100,0%</td>
</tr>
</tbody>
</table>

<div class="footer">
  Relatorio de Viabilidade Economica &mdash; {nome} &mdash; {cidade}
  &nbsp;|&nbsp; Gerado em {data_rel} {hora_rel}
  &nbsp;|&nbsp; Este relatorio e gerado automaticamente e deve ser conferido antes de qualquer decisao de investimento.
</div>
</body>
</html>"""
