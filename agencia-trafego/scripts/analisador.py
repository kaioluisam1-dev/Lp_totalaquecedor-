#!/usr/bin/env python3
"""
Motor de análise e otimização de campanhas.

Uso:
  python3 analisador.py "Nome do Cliente"   # analisa um cliente específico
  python3 analisador.py --carteira           # analisa todos os clientes
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CLIENTES_PATH = BASE_DIR / "clientes" / "clientes.json"


# ── Thresholds de alerta ────────────────────────────────────────────────────
THRESHOLDS = {
    "cpa_atencao": 1.3,       # CPA > 1.3x meta  → ATENÇÃO
    "cpa_critico": 2.0,       # CPA > 2.0x meta   → CRÍTICO
    "roas_critico": 1.0,      # ROAS < 1.0x meta  → CRÍTICO
    "frequencia_atencao": 3.0,# Freq Meta > 3     → ATENÇÃO
    "frequencia_critica": 3.5,# Freq Meta > 3.5   → CRÍTICO
    "quality_score_atencao": 6,# QS < 6           → ATENÇÃO
    "ctr_queda_atencao": 0.30, # CTR caiu 30%     → ATENÇÃO
}

STATUS_EMOJI = {"verde": "🟢", "amarelo": "🟡", "vermelho": "🔴"}


def slugify(texto: str) -> str:
    texto = texto.lower().strip()
    texto = re.sub(r"[^\w\s-]", "", texto)
    texto = re.sub(r"[\s_-]+", "-", texto)
    return texto


def carregar_clientes() -> list:
    with open(CLIENTES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def encontrar_cliente(nome: str) -> dict | None:
    clientes = carregar_clientes()
    nome_lower = nome.lower()
    for c in clientes:
        if nome_lower in c["nome"].lower() or nome_lower == c.get("slug", ""):
            return c
    return None


def carregar_dados_recentes(plataforma: str, slug: str) -> dict | None:
    """Carrega o arquivo JSON mais recente para a plataforma e cliente."""
    arquivos = sorted(DATA_DIR.glob(f"{plataforma}_{slug}_*.json"), reverse=True)
    if not arquivos:
        return None
    with open(arquivos[0], "r", encoding="utf-8") as f:
        return json.load(f)


def carregar_dados_anteriores(plataforma: str, slug: str) -> dict | None:
    """Carrega o segundo arquivo mais recente (para comparação de período anterior)."""
    arquivos = sorted(DATA_DIR.glob(f"{plataforma}_{slug}_*.json"), reverse=True)
    if len(arquivos) < 2:
        return None
    with open(arquivos[1], "r", encoding="utf-8") as f:
        return json.load(f)


def analisar_meta(cliente: dict, dados: dict, dados_ant: dict | None) -> dict:
    """Gera diagnóstico detalhado do Meta Ads para um cliente."""
    problemas = []
    oportunidades = []
    status = "verde"

    totais = dados.get("totais", {})
    spend = totais.get("spend", 0)
    leads = totais.get("leads", 0)
    compras = totais.get("compras", 0)
    cpa_real = totais.get("cpa")
    cpa_meta = cliente.get("meta_cpa")
    roas_real = totais.get("roas")
    roas_meta = cliente.get("meta_roas")

    # Frequência média
    dias = dados.get("dias", [])
    freq_vals = [d.get("frequency", 0) for d in dias if d.get("frequency")]
    freq_media = sum(freq_vals) / len(freq_vals) if freq_vals else 0

    # CPA análise
    if cpa_real and cpa_meta:
        ratio = cpa_real / cpa_meta
        if ratio >= THRESHOLDS["cpa_critico"]:
            status = "vermelho"
            problemas.append(
                f"CPA Meta R${cpa_real:.2f} está {ratio:.1f}x acima da meta (R${cpa_meta:.2f}) [CRÍTICO]"
            )
            problemas.append("→ Pausar ad sets com CPA mais alto; revisar criativos e segmentações")
        elif ratio >= THRESHOLDS["cpa_atencao"]:
            if status == "verde":
                status = "amarelo"
            problemas.append(
                f"CPA Meta R${cpa_real:.2f} está {ratio:.1f}x acima da meta (R${cpa_meta:.2f}) [ATENÇÃO]"
            )
            problemas.append("→ Testar novos criativos e revisar público do ad set com pior CPA")
        else:
            oportunidades.append(
                f"CPA Meta R${cpa_real:.2f} dentro da meta (R${cpa_meta:.2f}) — avaliar escala gradual"
            )

    # ROAS análise (ecommerce)
    if roas_real is not None and roas_meta:
        if roas_real < roas_meta * THRESHOLDS["roas_critico"]:
            status = "vermelho"
            problemas.append(
                f"ROAS Meta {roas_real:.2f}x abaixo da meta {roas_meta:.2f}x [CRÍTICO]"
            )
            problemas.append("→ Revisar funil de vendas, LPs e conjunto de produtos com pior ROAS")

    # Frequência
    if freq_media >= THRESHOLDS["frequencia_critica"]:
        if status == "verde":
            status = "amarelo"
        problemas.append(f"Frequência média {freq_media:.1f} — fadiga de criativos [ATENÇÃO]")
        problemas.append("→ Inserir novos criativos imediatamente e considerar ampliar público")
    elif freq_media >= THRESHOLDS["frequencia_atencao"]:
        if status == "verde":
            status = "amarelo"
        problemas.append(f"Frequência média {freq_media:.1f} — atenção à fadiga de criativos")

    # CTR queda vs período anterior
    if dados_ant:
        ctr_atual = totais.get("ctr_medio", 0)
        ctr_ant = dados_ant.get("totais", {}).get("ctr_medio", 0)
        if ctr_ant > 0 and ctr_atual > 0:
            queda = (ctr_ant - ctr_atual) / ctr_ant
            if queda >= THRESHOLDS["ctr_queda_atencao"]:
                if status == "verde":
                    status = "amarelo"
                problemas.append(
                    f"CTR caiu {queda*100:.0f}% vs período anterior ({ctr_ant:.2f}% → {ctr_atual:.2f}%) [ATENÇÃO]"
                )
                problemas.append("→ Renovar criativos; testar novos ângulos de comunicação")

    # Oportunidade de escala
    if not problemas and spend > 0 and cpa_meta and cpa_real:
        if cpa_real < cpa_meta * 0.85:
            oportunidades.append(
                f"CPA 15%+ abaixo da meta — considerar aumentar budget em 20-30%"
            )

    return {
        "plataforma": "meta",
        "status": status,
        "spend": spend,
        "cpa_real": cpa_real,
        "cpa_meta": cpa_meta,
        "roas_real": roas_real,
        "roas_meta": roas_meta,
        "frequencia_media": freq_media,
        "leads": leads,
        "compras": compras,
        "problemas": problemas,
        "oportunidades": oportunidades,
    }


def analisar_google(cliente: dict, dados: dict, dados_ant: dict | None) -> dict:
    """Gera diagnóstico detalhado do Google Ads para um cliente."""
    problemas = []
    oportunidades = []
    status = "verde"

    totais = dados.get("totais", {})
    cost = totais.get("cost", 0)
    conversions = totais.get("conversions", 0)
    cpa_real = totais.get("cpa")
    cpa_meta = cliente.get("google_cpa")
    qs_medio = totais.get("quality_score_medio")
    keywords_baixo_qs = dados.get("keywords_baixo_qs", [])

    # CPA
    if cpa_real and cpa_meta:
        ratio = cpa_real / cpa_meta
        if ratio >= THRESHOLDS["cpa_critico"]:
            status = "vermelho"
            problemas.append(
                f"CPA Google R${cpa_real:.2f} está {ratio:.1f}x acima da meta (R${cpa_meta:.2f}) [CRÍTICO]"
            )
            problemas.append("→ Negativar keywords com CPA alto; revisar lances e correspondências")
        elif ratio >= THRESHOLDS["cpa_atencao"]:
            if status == "verde":
                status = "amarelo"
            problemas.append(
                f"CPA Google R${cpa_real:.2f} está {ratio:.1f}x acima da meta (R${cpa_meta:.2f}) [ATENÇÃO]"
            )
            problemas.append("→ Revisar keywords de menor desempenho e ajustar lances")
        else:
            oportunidades.append(
                f"CPA Google R${cpa_real:.2f} dentro da meta — avaliar aumento de budget"
            )

    # Quality Score
    if qs_medio and qs_medio < THRESHOLDS["quality_score_atencao"]:
        if status == "verde":
            status = "amarelo"
        problemas.append(
            f"Quality Score médio {qs_medio:.1f} abaixo de 6 [ATENÇÃO]"
        )
        problemas.append("→ Melhorar relevância de anúncios e landing pages para as keywords principais")

    if keywords_baixo_qs:
        kws = ", ".join([k["keyword"] for k in keywords_baixo_qs[:3]])
        problemas.append(f"Keywords com QS baixo: {kws}")

    # CTR queda
    if dados_ant:
        ctr_atual = totais.get("ctr_medio", 0)
        ctr_ant = dados_ant.get("totais", {}).get("ctr_medio", 0)
        if ctr_ant > 0 and ctr_atual > 0:
            queda = (ctr_ant - ctr_atual) / ctr_ant
            if queda >= THRESHOLDS["ctr_queda_atencao"]:
                if status == "verde":
                    status = "amarelo"
                problemas.append(
                    f"CTR Google caiu {queda*100:.0f}% vs período anterior [ATENÇÃO]"
                )
                problemas.append("→ Revisar copies dos anúncios e testar novas chamadas para ação")

    return {
        "plataforma": "google",
        "status": status,
        "cost": cost,
        "cpa_real": cpa_real,
        "cpa_meta": cpa_meta,
        "conversions": conversions,
        "quality_score_medio": qs_medio,
        "problemas": problemas,
        "oportunidades": oportunidades,
    }


def status_geral(analises: list) -> str:
    if any(a["status"] == "vermelho" for a in analises):
        return "vermelho"
    if any(a["status"] == "amarelo" for a in analises):
        return "amarelo"
    return "verde"


def gerar_relatorio_texto(cliente: dict, analises: list) -> str:
    sg = status_geral(analises)
    linhas = [
        f"{'='*60}",
        f"RELATÓRIO DE PERFORMANCE — {cliente['nome'].upper()}",
        f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"Status Geral: {STATUS_EMOJI[sg]} {sg.upper()}",
        f"{'='*60}",
        "",
    ]

    for analise in analises:
        plat = analise["plataforma"].upper()
        st = analise["status"]
        linhas.append(f"--- {plat} [{STATUS_EMOJI[st]} {st.upper()}] ---")

        if analise["plataforma"] == "meta":
            linhas.append(f"  Gasto: R${analise.get('spend', 0):.2f}")
            if analise.get("cpa_real"):
                linhas.append(f"  CPA Real: R${analise['cpa_real']:.2f} | Meta: R${analise.get('cpa_meta', 0):.2f}")
            if analise.get("leads"):
                linhas.append(f"  Leads: {analise['leads']:.0f}")
            if analise.get("compras"):
                linhas.append(f"  Compras: {analise['compras']:.0f}")
            if analise.get("frequencia_media"):
                linhas.append(f"  Frequência Média: {analise['frequencia_media']:.1f}")
        else:
            linhas.append(f"  Gasto: R${analise.get('cost', 0):.2f}")
            if analise.get("cpa_real"):
                linhas.append(f"  CPA Real: R${analise['cpa_real']:.2f} | Meta: R${analise.get('cpa_meta', 0):.2f}")
            if analise.get("conversions"):
                linhas.append(f"  Conversões: {analise['conversions']:.0f}")
            if analise.get("quality_score_medio"):
                linhas.append(f"  Quality Score médio: {analise['quality_score_medio']:.1f}")

        if analise["problemas"]:
            linhas.append("")
            linhas.append("  ⚠️  PROBLEMAS IDENTIFICADOS:")
            for p in analise["problemas"]:
                linhas.append(f"     {p}")

        if analise["oportunidades"]:
            linhas.append("")
            linhas.append("  🚀  OPORTUNIDADES:")
            for o in analise["oportunidades"]:
                linhas.append(f"     {o}")

        linhas.append("")

    linhas.append(f"{'='*60}")
    return "\n".join(linhas)


def analisar_cliente(nome_cliente: str, imprimir: bool = True) -> dict | None:
    cliente = encontrar_cliente(nome_cliente)
    if not cliente:
        print(f"❌ Cliente '{nome_cliente}' não encontrado em clientes.json")
        return None

    slug = cliente.get("slug") or slugify(cliente["nome"])
    analises = []

    dados_meta = carregar_dados_recentes("meta", slug)
    dados_meta_ant = carregar_dados_anteriores("meta", slug)
    if dados_meta:
        analises.append(analisar_meta(cliente, dados_meta, dados_meta_ant))

    dados_google = carregar_dados_recentes("google", slug)
    dados_google_ant = carregar_dados_anteriores("google", slug)
    if dados_google:
        analises.append(analisar_google(cliente, dados_google, dados_google_ant))

    if not analises:
        print(f"⚠️  Nenhum dado coletado ainda para '{cliente['nome']}'. Rode os coletores primeiro.")
        return None

    relatorio = gerar_relatorio_texto(cliente, analises)

    if imprimir:
        print(relatorio)

    # Salvar relatório em arquivo
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    caminho = DATA_DIR / f"analise_{slug}_{data_hoje}.txt"
    caminho.write_text(relatorio, encoding="utf-8")

    sg = status_geral(analises)
    return {
        "cliente": cliente["nome"],
        "slug": slug,
        "status": sg,
        "analises": analises,
        "relatorio_path": str(caminho),
    }


def analisar_carteira(imprimir_detalhes: bool = False) -> list:
    """Analisa todos os clientes ativos e retorna ranking por status de risco."""
    clientes = carregar_clientes()
    resultados = []

    for cliente in clientes:
        if not cliente.get("ativo", True):
            continue
        resultado = analisar_cliente(cliente["nome"], imprimir=imprimir_detalhes)
        if resultado:
            resultados.append(resultado)

    # Ordenar: vermelho primeiro, depois amarelo, depois verde
    ordem = {"vermelho": 0, "amarelo": 1, "verde": 2}
    resultados.sort(key=lambda x: ordem.get(x["status"], 3))

    # Imprimir resumo com semáforo
    print("\n" + "="*60)
    print("RANKING DA CARTEIRA — STATUS ATUAL")
    print("="*60)
    for r in resultados:
        emoji = STATUS_EMOJI[r["status"]]
        n_problemas = sum(len(a["problemas"]) for a in r["analises"])
        print(f"{emoji} {r['cliente']:<35} | {r['status'].upper():<10} | {n_problemas} problema(s)")
    print("="*60)

    # Salvar ranking
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    caminho = DATA_DIR / f"carteira_{data_hoje}.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(
            [{"cliente": r["cliente"], "status": r["status"], "n_problemas": sum(len(a["problemas"]) for a in r["analises"])} for r in resultados],
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\nRanking salvo em: {caminho.name}")
    return resultados


def main():
    parser = argparse.ArgumentParser(description="Motor de análise de campanhas")
    parser.add_argument("cliente", nargs="?", help="Nome do cliente para analisar")
    parser.add_argument("--carteira", action="store_true", help="Analisar todos os clientes")
    parser.add_argument("--detalhes", action="store_true", help="Exibir detalhes de cada cliente ao analisar carteira")
    args = parser.parse_args()

    DATA_DIR.mkdir(exist_ok=True)

    if args.carteira:
        analisar_carteira(imprimir_detalhes=args.detalhes)
    elif args.cliente:
        analisar_cliente(args.cliente)
    else:
        parser.print_help()
        print("\nExemplos:")
        print('  python3 analisador.py "Clínica Sorriso"')
        print("  python3 analisador.py --carteira")
        print("  python3 analisador.py --carteira --detalhes")


if __name__ == "__main__":
    main()
