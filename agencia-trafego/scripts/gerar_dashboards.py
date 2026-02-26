#!/usr/bin/env python3
"""
Gerador automático de dashboards HTML quinzenais por cliente.

Uso:
  python3 gerar_dashboards.py "Nome do Cliente"   # gera para um cliente
  python3 gerar_dashboards.py --todos              # gera para todos
  python3 gerar_dashboards.py --abrir "Nome"       # gera e abre no navegador
"""

import argparse
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DASHBOARDS_DIR = BASE_DIR / "dashboards"
CLIENTES_PATH = BASE_DIR / "clientes" / "clientes.json"
TEMPLATE_PATH = DASHBOARDS_DIR / "template_dashboard.html"

try:
    from jinja2 import Environment, FileSystemLoader
    _jinja_ok = True
except ImportError:
    _jinja_ok = False


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
        if nome_lower in c["nome"].lower():
            return c
    return None


def carregar_dados(plataforma: str, slug: str, idx: int = 0) -> dict | None:
    """Carrega dados de um cliente (idx=0 mais recente, idx=1 anterior)."""
    arquivos = sorted(DATA_DIR.glob(f"{plataforma}_{slug}_*.json"), reverse=True)
    if len(arquivos) <= idx:
        return None
    with open(arquivos[idx], "r", encoding="utf-8") as f:
        return json.load(f)


def fmt_brl(valor) -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "—"
    return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_num(valor) -> str:
    if valor is None:
        return "—"
    try:
        v = float(valor)
        if v >= 1_000_000:
            return f"{v/1_000_000:.1f}M"
        if v >= 1_000:
            return f"{v/1_000:.1f}k"
        return f"{v:.0f}"
    except (TypeError, ValueError):
        return "—"


def delta_str(atual, anterior) -> tuple[str, str]:
    """Retorna (texto_delta, classe_css) comparando atual vs anterior."""
    if atual is None or anterior is None or anterior == 0:
        return "—", "delta-neu"
    diff_pct = (atual - anterior) / abs(anterior) * 100
    if diff_pct > 0:
        return f"+{diff_pct:.0f}%", "delta-pos"
    return f"{diff_pct:.0f}%", "delta-neg"


def status_cpa(cpa_real, cpa_meta) -> str:
    if not cpa_real or not cpa_meta:
        return "ok"
    ratio = cpa_real / cpa_meta
    if ratio >= 2.0:
        return "crit"
    if ratio >= 1.3:
        return "warn"
    return "ok"


def gerar_resumo_executivo(cliente: dict, dados_meta: dict | None, dados_google: dict | None) -> str:
    """
    Gera parágrafo de resumo executivo usando a API do Claude (Anthropic).
    Fallback para texto gerado localmente se API não disponível.
    """
    partes = []
    if dados_meta:
        t = dados_meta.get("totais", {})
        partes.append(f"Meta Ads: gasto R${t.get('spend', 0):.2f}, "
                      f"CPA R${t.get('cpa', 0):.2f}, "
                      f"leads {t.get('leads', 0):.0f}, compras {t.get('compras', 0):.0f}.")
    if dados_google:
        t = dados_google.get("totais", {})
        partes.append(f"Google Ads: gasto R${t.get('cost', 0):.2f}, "
                      f"CPA R${t.get('cpa', 0):.2f}, conversões {t.get('conversions', 0):.0f}.")

    dados_texto = " ".join(partes) if partes else "Nenhum dado coletado ainda."

    try:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY não definida")
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": (
                    "Você é um especialista em tráfego pago explicando resultados para um dono de negócio "
                    "que não entende de marketing digital. "
                    f"Dados do período para o cliente {cliente['nome']}: {dados_texto} "
                    "Escreva exatamente 2 frases claras resumindo se o dinheiro está bem investido e qual foi o "
                    "destaque do período. Sem jargão técnico. Seja direto e positivo quando cabível."
                )
            }]
        )
        return msg.content[0].text.strip()
    except Exception:
        pass

    # Fallback local
    objetivo = cliente.get("objetivo", "resultados")
    if dados_meta and dados_google:
        return (
            f"O investimento em anúncios neste período foi distribuído entre Meta e Google, "
            f"gerando resultados em ambas as plataformas para {cliente['nome']}. "
            f"Acompanhe os indicadores abaixo para entender os próximos passos recomendados."
        )
    plat = "Meta Ads" if dados_meta else "Google Ads"
    return (
        f"Neste período, o investimento em {plat} gerou {objetivo} para {cliente['nome']}. "
        f"Veja os indicadores detalhados abaixo e o plano de ação recomendado."
    )


def construir_contexto(cliente: dict) -> dict:
    """Monta o dicionário de contexto para renderizar o template Jinja2."""
    slug = cliente.get("slug") or slugify(cliente["nome"])

    dados_meta = carregar_dados("meta", slug, idx=0)
    dados_meta_ant = carregar_dados("meta", slug, idx=1)
    dados_google = carregar_dados("google", slug, idx=0)
    dados_google_ant = carregar_dados("google", slug, idx=1)

    agora = datetime.now()
    quinzena = 1 if agora.day <= 15 else 2
    periodo = agora.strftime("%d/%m/%Y")

    ctx = {
        "cliente_nome": cliente["nome"],
        "periodo": f"01/{agora.strftime('%m/%Y')} — {periodo}" if quinzena == 1 else f"16/{agora.strftime('%m/%Y')} — {periodo}",
        "quinzena": quinzena,
        "gerado_em": agora.strftime("%d/%m/%Y às %H:%M"),
        "tem_meta": dados_meta is not None,
        "tem_google": dados_google is not None,
    }

    # Totais combinados
    meta_spend = dados_meta["totais"]["spend"] if dados_meta else 0
    google_cost = dados_google["totais"]["cost"] if dados_google else 0
    total_spend = meta_spend + google_cost

    meta_spend_ant = dados_meta_ant["totais"]["spend"] if dados_meta_ant else None
    google_cost_ant = dados_google_ant["totais"]["cost"] if dados_google_ant else None
    total_spend_ant = (meta_spend_ant or 0) + (google_cost_ant or 0) if (meta_spend_ant or google_cost_ant) else None

    meta_conversoes = (dados_meta["totais"].get("leads", 0) + dados_meta["totais"].get("compras", 0)) if dados_meta else 0
    google_conversoes = dados_google["totais"].get("conversions", 0) if dados_google else 0
    total_conversoes = meta_conversoes + google_conversoes

    meta_conv_ant = (dados_meta_ant["totais"].get("leads", 0) + dados_meta_ant["totais"].get("compras", 0)) if dados_meta_ant else None
    google_conv_ant = dados_google_ant["totais"].get("conversions", 0) if dados_google_ant else None
    total_conv_ant = (meta_conv_ant or 0) + (google_conv_ant or 0) if (meta_conv_ant or google_conv_ant) else None

    cpa_medio = (total_spend / total_conversoes) if total_conversoes > 0 else None
    cpa_meta_val = (
        (cliente.get("meta_cpa", 0) + cliente.get("google_cpa", 0)) / 2
        if cliente.get("meta_cpa") and cliente.get("google_cpa")
        else cliente.get("meta_cpa") or cliente.get("google_cpa")
    )

    meta_impr = dados_meta["totais"].get("impressions", 0) if dados_meta else 0
    google_impr = dados_google["totais"].get("impressions", 0) if dados_google else 0
    total_impressoes = meta_impr + google_impr

    meta_cliques = dados_meta["totais"].get("clicks", 0) if dados_meta else 0
    google_cliques = dados_google["totais"].get("clicks", 0) if dados_google else 0
    total_cliques = meta_cliques + google_cliques
    ctr_medio = (total_cliques / total_impressoes * 100) if total_impressoes > 0 else 0

    delta_spend_txt, delta_spend_cls = delta_str(total_spend, total_spend_ant)
    delta_conv_txt, delta_conv_cls = delta_str(total_conversoes, total_conv_ant)

    # Status geral baseado em CPA
    st_cpa = status_cpa(cpa_medio, cpa_meta_val)
    if st_cpa == "crit":
        sg = "vermelho"
        sg_emoji = "🔴"
        sg_texto = "ATENÇÃO NECESSÁRIA"
    elif st_cpa == "warn":
        sg = "amarelo"
        sg_emoji = "🟡"
        sg_texto = "MONITORAR"
    else:
        sg = "verde"
        sg_emoji = "🟢"
        sg_texto = "DENTRO DA META"

    ctx.update({
        "total_spend": fmt_brl(total_spend),
        "status_spend": st_cpa,
        "delta_spend": delta_spend_txt,
        "delta_class_spend": delta_spend_cls,
        "cpa_medio": fmt_brl(cpa_medio) if cpa_medio else "—",
        "cpa_meta": fmt_brl(cpa_meta_val) if cpa_meta_val else "—",
        "status_cpa": st_cpa,
        "delta_class_cpa": "delta-neg" if st_cpa in ("warn", "crit") else "delta-pos",
        "total_conversoes": fmt_num(total_conversoes),
        "status_conversoes": "ok",
        "delta_conversoes": delta_conv_txt,
        "delta_class_conversoes": delta_conv_cls,
        "total_impressoes": fmt_num(total_impressoes),
        "delta_impressoes": "—",
        "total_cliques": fmt_num(total_cliques),
        "ctr_medio": f"{ctr_medio:.2f}",
        "status_geral": sg,
        "status_geral_emoji": sg_emoji,
        "status_geral_texto": sg_texto,
        "roas_real": None,
        "roas_meta": None,
    })

    # Meta Ads block
    if dados_meta:
        m = dados_meta["totais"]
        m_cpa = m.get("cpa")
        m_cpa_meta = cliente.get("meta_cpa")
        m_tipo = "Leads" if cliente.get("objetivo") in ("leads",) else "Compras"
        m_conv = m.get("leads", 0) if cliente.get("objetivo") == "leads" else m.get("compras", 0)
        m_freq = (
            sum(d.get("frequency", 0) for d in dados_meta.get("dias", []) if d.get("frequency"))
            / max(len([d for d in dados_meta.get("dias", []) if d.get("frequency")]), 1)
        )
        ctx.update({
            "meta_spend": fmt_brl(m.get("spend", 0)),
            "meta_budget_diario": fmt_brl(cliente.get("meta_budget_diario")),
            "meta_status_spend": "ok",
            "meta_cpa_real": fmt_brl(m_cpa) if m_cpa else "—",
            "meta_cpa_meta": fmt_brl(m_cpa_meta) if m_cpa_meta else "—",
            "meta_status_cpa": status_cpa(m_cpa, m_cpa_meta),
            "meta_delta_class_cpa": "delta-neg" if status_cpa(m_cpa, m_cpa_meta) != "ok" else "delta-pos",
            "meta_tipo_conversao": m_tipo,
            "meta_conversoes": fmt_num(m_conv),
            "meta_frequencia": f"{m_freq:.1f}",
            "meta_roas_real": None,
            "meta_roas_meta": None,
            "meta_status_roas": "ok",
            "meta_delta_class_roas": "delta-neu",
        })
        if cliente.get("objetivo") == "vendas" and m.get("roas"):
            ctx["meta_roas_real"] = f"{m['roas']:.2f}"
            ctx["meta_roas_meta"] = fmt_brl(cliente.get("meta_roas"))
            roas_st = "ok" if m["roas"] >= (cliente.get("meta_roas") or 0) else "crit"
            ctx["meta_status_roas"] = roas_st
            ctx["meta_delta_class_roas"] = "delta-pos" if roas_st == "ok" else "delta-neg"

    # Google Ads block
    if dados_google:
        g = dados_google["totais"]
        g_cpa = g.get("cpa")
        g_cpa_meta = cliente.get("google_cpa")
        ctx.update({
            "google_spend": fmt_brl(g.get("cost", 0)),
            "google_budget_diario": fmt_brl(cliente.get("google_budget_diario")),
            "google_status_spend": "ok",
            "google_cpa_real": fmt_brl(g_cpa) if g_cpa else "—",
            "google_cpa_meta": fmt_brl(g_cpa_meta) if g_cpa_meta else "—",
            "google_status_cpa": status_cpa(g_cpa, g_cpa_meta),
            "google_delta_class_cpa": "delta-neg" if status_cpa(g_cpa, g_cpa_meta) != "ok" else "delta-pos",
            "google_conversoes": fmt_num(g.get("conversions", 0)),
            "google_qs_medio": f"{g.get('quality_score_medio', 0):.1f}" if g.get("quality_score_medio") else "—",
            "google_ctr": f"{g.get('ctr_medio', 0):.2f}",
            "google_cpc_medio": fmt_brl(
                g.get("cost", 0) / g.get("clicks", 1) if g.get("clicks") else None
            ),
        })

    # Resumo executivo
    ctx["resumo_executivo"] = gerar_resumo_executivo(cliente, dados_meta, dados_google)

    # Problemas e oportunidades (importar do analisador)
    problemas = []
    oportunidades = []
    plano_acao = []
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from analisador import (
            analisar_meta, analisar_google,
            carregar_dados_recentes, carregar_dados_anteriores,
        )
        analises = []
        if dados_meta:
            analises.append(analisar_meta(cliente, dados_meta, dados_meta_ant))
        if dados_google:
            analises.append(analisar_google(cliente, dados_google, dados_google_ant))

        for a in analises:
            problemas.extend(a["problemas"])
            oportunidades.extend(a["oportunidades"])

        # Gerar plano de ação numerado a partir dos problemas
        for p in problemas:
            if p.startswith("→"):
                plano_acao.append(p[1:].strip())
    except Exception as e:
        print(f"  ⚠️  Aviso ao importar analisador para plano de ação: {e}")

    ctx["problemas"] = problemas
    ctx["oportunidades"] = oportunidades
    ctx["plano_acao"] = plano_acao

    return ctx


def gerar_dashboard(cliente: dict) -> Path | None:
    slug = cliente.get("slug") or slugify(cliente["nome"])

    if not _jinja_ok:
        print("❌ Jinja2 não instalado. Execute: pip install jinja2")
        return None

    if not TEMPLATE_PATH.exists():
        print(f"❌ Template não encontrado: {TEMPLATE_PATH}")
        return None

    dados_meta = carregar_dados("meta", slug, idx=0)
    dados_google = carregar_dados("google", slug, idx=0)
    if not dados_meta and not dados_google:
        print(f"⚠️  Nenhum dado para '{cliente['nome']}'. Rode os coletores primeiro.")
        return None

    print(f"🔄 Gerando dashboard: {cliente['nome']}...")
    ctx = construir_contexto(cliente)

    env = Environment(loader=FileSystemLoader(str(DASHBOARDS_DIR)))
    template = env.get_template("template_dashboard.html")
    html = template.render(**ctx)

    agora = datetime.now()
    quinzena = 1 if agora.day <= 15 else 2
    nome_arquivo = f"{slug}_Q{quinzena}_{agora.strftime('%Y-%m-%d')}.html"
    caminho = DASHBOARDS_DIR / nome_arquivo

    caminho.write_text(html, encoding="utf-8")
    print(f"✅ Dashboard salvo: {caminho.name}")
    return caminho


def main():
    parser = argparse.ArgumentParser(description="Gerador de dashboards quinzenais")
    parser.add_argument("cliente", nargs="?", help="Nome do cliente")
    parser.add_argument("--todos", action="store_true", help="Gerar para todos os clientes")
    parser.add_argument("--abrir", metavar="CLIENTE", help="Gerar e abrir no navegador")
    args = parser.parse_args()

    DASHBOARDS_DIR.mkdir(exist_ok=True)

    if args.abrir:
        cliente = encontrar_cliente(args.abrir)
        if not cliente:
            print(f"❌ Cliente '{args.abrir}' não encontrado.")
            sys.exit(1)
        caminho = gerar_dashboard(cliente)
        if caminho:
            subprocess.run(["xdg-open" if sys.platform == "linux" else "open", str(caminho)])
        return

    if args.todos:
        clientes = carregar_clientes()
        gerados = []
        for cliente in clientes:
            if not cliente.get("ativo", True):
                continue
            caminho = gerar_dashboard(cliente)
            if caminho:
                gerados.append(caminho)
        print(f"\n📊 {len(gerados)} dashboard(s) gerado(s) em: {DASHBOARDS_DIR}")
        return

    if args.cliente:
        cliente = encontrar_cliente(args.cliente)
        if not cliente:
            print(f"❌ Cliente '{args.cliente}' não encontrado em clientes.json")
            sys.exit(1)
        gerar_dashboard(cliente)
        return

    parser.print_help()
    print("\nExemplos:")
    print('  python3 gerar_dashboards.py "Clínica Sorriso"')
    print("  python3 gerar_dashboards.py --todos")
    print('  python3 gerar_dashboards.py --abrir "Pet Shop"')


if __name__ == "__main__":
    main()
