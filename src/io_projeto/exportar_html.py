"""
Exportador HTML para impressao como PDF (C11).

Gera relatorio formatado para impressao/PDF diretamente do navegador.
Nao requer dependencias extras — usa apenas HTML + CSS inline.
"""

from __future__ import annotations

from datetime import datetime


def gerar_relatorio_html(projeto, resultado) -> str:
    """Gera o relatorio HTML completo para impressao como PDF."""
    r = resultado.resumo
    ind = resultado.indicadores
    info = projeto.terreno.info

    nome = info.nome
    cidade = f"{info.cidade}/{info.uf}"
    data_rel = datetime.now().strftime("%d/%m/%Y %H:%M")

    vgv_bruto = r.get("vgv_bruto", 0) or 0
    vgv_vendavel = r.get("vgv_vendavel", 0) or 0
    total_saidas = r.get("total_saidas", 0) or 0
    lucro = r.get("lucro_liquido", 0) or 0
    total_lotes = r.get("total_lotes", 0) or 0

    tir = ind.get("tir_anual")
    vpl = ind.get("vpl")
    payback = ind.get("payback_simples_meses")
    exposicao = ind.get("exposicao_maxima")
    multiplicador = ind.get("lucro_sobre_exposicao")
    margem_vv = r.get("margem_sobre_vgv_vendavel")
    margem_vb = r.get("margem_sobre_vgv_bruto")
    tma = projeto.parametros.tma_anual

    def fmt_brl(v: float | None) -> str:
        if v is None:
            return "—"
        if v < 0:
            return f"(R$ {abs(v):,.0f})".replace(",", ".")
        return f"R$ {v:,.0f}".replace(",", ".")

    def fmt_pct(v: float | None) -> str:
        if v is None:
            return "—"
        return f"{v * 100:.1f}%"

    def cor_lucro(v: float | None) -> str:
        return "#1a7a3c" if (v or 0) > 0 else "#c0392b"

    permuta_fisica = vgv_bruto - vgv_vendavel
    rec_financeira = r.get("receita_financeira", 0) or 0
    receita_total = r.get("vgv_total_recebido", 0) or 0

    permuta_row = (
        f"<tr><td>&nbsp;&nbsp;&nbsp;(-) Permuta Fisica</td>"
        f"<td>({fmt_brl(permuta_fisica)})</td><td></td></tr>"
        if permuta_fisica > 0 else ""
    )
    juros_row = (
        f"<tr><td>&nbsp;&nbsp;&nbsp;(+) Receita Financeira (Juros Price)</td>"
        f"<td>+ {fmt_brl(rec_financeira)}</td><td></td></tr>"
        if rec_financeira > 0 else ""
    )

    categorias = [
        ("Aquisicao do Terreno", r.get("custo_terreno_aquisicao", 0) or 0),
        ("Cartorio / Registro", r.get("custo_terreno_cartorio", 0) or 0),
        ("Obras de Infraestrutura", r.get("custo_obras", 0) or 0),
        ("Projetos Tecnicos", r.get("custo_projetos", 0) or 0),
        ("Licenciamento / Legal", r.get("custo_licenciamento", 0) or 0),
        ("Marketing / Comercial", r.get("custo_marketing", 0) or 0),
        ("Outros / Administracao", (r.get("custo_outros", 0) or 0) + (r.get("custo_administracao", 0) or 0)),
        ("Comissao de Vendas", r.get("custo_comissao", 0) or 0),
        ("Impostos / Tributacao", r.get("custo_impostos", 0) or 0),
        ("Permuta Financeira", r.get("custo_permuta_financeira", 0) or 0),
    ]
    cat_rows = ""
    for nome_cat, valor in categorias:
        if valor and valor > 0:
            pct_s = valor / total_saidas * 100 if total_saidas > 0 else 0
            pct_v = valor / vgv_vendavel * 100 if vgv_vendavel > 0 else 0
            por_lote = valor / total_lotes if total_lotes > 0 else 0
            cat_rows += (
                f"<tr><td>{nome_cat}</td>"
                f"<td>{fmt_brl(valor)}</td>"
                f"<td>{pct_s:.1f}%</td>"
                f"<td>{pct_v:.1f}%</td>"
                f"<td>{fmt_brl(por_lote)}</td></tr>"
            )

    horizonte = r.get("horizonte_meses", "—")
    mes_termino = r.get("mes_termino_obras", "—")

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatorio de Viabilidade — {nome}</title>
<style>
@page {{ margin: 18mm 20mm; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: Arial, Helvetica, sans-serif; color: #222; font-size: 10pt; line-height: 1.45; }}
.aviso-print {{ background:#fffbe6; border:1px solid #f0c040; padding:10px 16px;
    margin-bottom:20px; border-radius:6px; font-size:10pt; }}
.capa {{ border-bottom: 3px solid #2E75B6; padding-bottom: 14px; margin-bottom: 20px; }}
.capa h1 {{ color:#1F3864; font-size:20pt; margin-bottom:4px; }}
.capa .sub {{ color:#555; font-size:11pt; }}
.capa .data {{ color:#888; font-size:9pt; margin-top:6px; }}
h2 {{ color:#2E75B6; font-size:12pt; margin:22px 0 8px; border-bottom:1px solid #D6E4F0;
     padding-bottom:4px; page-break-after:avoid; }}
.kpi-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin:12px 0; }}
.kpi {{ border:1px solid #D6E4F0; border-radius:5px; padding:10px 12px; background:#F7FAFF; }}
.kpi-label {{ font-size:8pt; color:#666; margin-bottom:3px; }}
.kpi-value {{ font-size:13pt; font-weight:700; }}
.verde {{ color:#1a7a3c; }}
.vermelho {{ color:#c0392b; }}
.neutro {{ color:#1F3864; }}
table {{ width:100%; border-collapse:collapse; margin:10px 0; font-size:9.5pt; page-break-inside:avoid; }}
thead th {{ background:#1F3864; color:#fff; padding:7px 10px; text-align:left; font-weight:600; }}
tbody td {{ padding:5px 10px; border-bottom:1px solid #e5e5e5; }}
tbody tr:nth-child(even) td {{ background:#F7FAFF; }}
tr.subtotal td {{ font-weight:700; background:#D6E4F0 !important; }}
tr.resultado td {{ font-weight:700; font-size:10.5pt;
    background:{('#C6EFCE' if lucro >= 0 else '#FFC7CE')} !important; }}
.footer {{ font-size:8.5pt; color:#888; text-align:center; margin-top:36px;
    border-top:1px solid #ccc; padding-top:8px; }}
@media print {{
    .aviso-print {{ display:none; }}
    body {{ font-size:9.5pt; }}
    h2 {{ font-size:11pt; }}
}}
</style>
</head>
<body>
<div class="aviso-print">
  <strong>Para salvar como PDF:</strong> pressione <strong>Ctrl+P</strong> (ou Cmd+P no Mac) &rarr; selecione
  <em>"Salvar como PDF"</em> (Chrome/Edge) ou <em>"Gerar PDF"</em> (Firefox). Ative "Graficos de fundo" nas
  opcoes de impressao para manter as cores.
</div>

<div class="capa">
  <h1>Relatorio de Viabilidade Economica</h1>
  <div class="sub"><strong>{nome}</strong> &mdash; {cidade}</div>
  <div class="data">Gerado em: {data_rel} &nbsp;|&nbsp; Horizonte: {horizonte} meses &nbsp;|&nbsp; Termino obras: M{mes_termino}</div>
</div>

<h2>1. Indicadores Principais</h2>
<div class="kpi-grid">
  <div class="kpi">
    <div class="kpi-label">VGV Bruto</div>
    <div class="kpi-value neutro">{fmt_brl(vgv_bruto)}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Lucro Liquido</div>
    <div class="kpi-value" style="color:{cor_lucro(lucro)}">{fmt_brl(lucro)}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Margem s/ VGV Vendavel</div>
    <div class="kpi-value" style="color:{cor_lucro(margem_vv)}">{fmt_pct(margem_vv)}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">TIR Anual</div>
    <div class="kpi-value" style="color:{cor_lucro(tir)}">{fmt_pct(tir)}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">VPL (TMA {tma:.1f}% a.a.)</div>
    <div class="kpi-value" style="color:{cor_lucro(vpl)}">{fmt_brl(vpl)}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Payback Simples</div>
    <div class="kpi-value neutro">{str(payback) + " meses" if payback else "—"}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Exposicao Maxima de Caixa</div>
    <div class="kpi-value neutro">{fmt_brl(exposicao)}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Multiplicador (Lucro / Exposicao)</div>
    <div class="kpi-value {'verde' if (multiplicador or 0) > 1 else 'neutro'}">{f"{multiplicador:.2f}x" if multiplicador else "—"}</div>
  </div>
</div>

<h2>2. DRE — Demonstrativo de Resultado</h2>
<table>
<thead><tr><th style="width:45%">Descricao</th><th>Valor</th><th>% VGV Vendavel</th></tr></thead>
<tbody>
<tr><td><b>VGV Bruto</b></td><td>{fmt_brl(vgv_bruto)}</td>
    <td>{fmt_pct(vgv_bruto / vgv_vendavel if vgv_vendavel else None)}</td></tr>
{permuta_row}
<tr class="subtotal"><td>VGV Vendavel (base de calculo)</td>
    <td>{fmt_brl(vgv_vendavel)}</td><td>100,0%</td></tr>
{juros_row}
<tr class="subtotal"><td>Receita Total</td><td>{fmt_brl(receita_total)}</td>
    <td>{fmt_pct(receita_total / vgv_vendavel if vgv_vendavel else None)}</td></tr>
<tr><td>&nbsp;</td><td></td><td></td></tr>
<tr><td>(-) Total de Saidas</td>
    <td>({fmt_brl(total_saidas)})</td>
    <td>({fmt_pct(total_saidas / vgv_vendavel if vgv_vendavel else None)})</td></tr>
<tr class="resultado">
  <td>Resultado Bruto (Lucro Liquido)</td>
  <td>{fmt_brl(lucro)}</td>
  <td>{fmt_pct(margem_vv)}</td>
</tr>
</tbody>
</table>
<p style="font-size:9pt;color:#666;margin-top:4px;">
  Margem sobre VGV Bruto: {fmt_pct(margem_vb)} &nbsp;|&nbsp; Total de lotes: {total_lotes}
</p>

<h2>3. Composicao dos Custos</h2>
<table>
<thead><tr>
  <th style="width:35%">Categoria</th>
  <th>Valor Total</th><th>% das Saidas</th><th>% VGV Vendavel</th><th>R$ / Lote</th>
</tr></thead>
<tbody>
{cat_rows}
<tr class="subtotal">
  <td>Total de Saidas</td>
  <td>{fmt_brl(total_saidas)}</td>
  <td>100,0%</td>
  <td>{fmt_pct(total_saidas / vgv_vendavel if vgv_vendavel else None)}</td>
  <td>{fmt_brl(total_saidas / total_lotes if total_lotes else None)}</td>
</tr>
</tbody>
</table>

<h2>4. Dados do Empreendimento</h2>
<table>
<thead><tr><th>Item</th><th>Valor</th></tr></thead>
<tbody>
<tr><td>Area da Gleba</td><td>{projeto.terreno.areas.area_gleba_m2:,.0f} m&sup2;</td></tr>
<tr><td>Area de Lotes</td><td>{projeto.terreno.areas.area_lotes_m2:,.0f} m&sup2;</td></tr>
<tr><td>Aproveitamento (lotes/gleba)</td>
    <td>{projeto.terreno.areas.aproveitamento * 100:.1f}%</td></tr>
<tr><td>Total de Lotes</td><td>{total_lotes} lotes</td></tr>
<tr><td>VGV medio por Lote</td>
    <td>{fmt_brl(vgv_bruto / total_lotes if total_lotes else None)}</td></tr>
<tr><td>Inicio do Projeto (M0)</td>
    <td>{projeto.terreno.datas.inicio_projeto.strftime("%B/%Y")}</td></tr>
<tr><td>Lancamento de Vendas</td>
    <td>{projeto.terreno.datas.lancamento_vendas.strftime("%B/%Y")}</td></tr>
<tr><td>Inicio de Obras</td>
    <td>{projeto.terreno.datas.inicio_obras.strftime("%B/%Y")}</td></tr>
<tr><td>Termino de Obras</td>
    <td>{projeto.terreno.datas.termino_obras.strftime("%B/%Y")}</td></tr>
</tbody>
</table>

<div class="footer">
  Sistema de Viabilidade Economica de Loteamento &mdash; {data_rel}
  &nbsp;|&nbsp; Este relatorio e gerado automaticamente e deve ser conferido antes de qualquer decisao de investimento.
</div>
</body>
</html>"""

    return html
