#!/usr/bin/env python3
"""
Coletor de dados do Meta Ads.
Conecta à Meta Marketing API e baixa métricas dos últimos 14 dias
para cada cliente cadastrado em clientes/clientes.json.
"""

import json
import os
import re
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env na raiz do projeto
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

# Configuração de logging
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "coletor.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def slugify(texto: str) -> str:
    texto = texto.lower().strip()
    texto = re.sub(r"[^\w\s-]", "", texto)
    texto = re.sub(r"[\s_-]+", "-", texto)
    return texto


def carregar_clientes() -> list:
    caminho = BASE_DIR / "clientes" / "clientes.json"
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def coletar_meta_cliente(cliente: dict, dias: int = 14) -> dict | None:
    """
    Puxa métricas do Meta Ads para um cliente.
    Retorna dicionário com métricas ou None em caso de erro.
    """
    account_id = cliente.get("account_id_meta", "").strip()
    if not account_id or account_id.startswith("act_123"):
        log.warning(f"[{cliente['nome']}] account_id Meta não configurado ou é exemplo. Pulando.")
        return None

    try:
        from facebook_business.api import FacebookAdsApi
        from facebook_business.adobjects.adaccount import AdAccount
        from facebook_business.adobjects.adsinsights import AdsInsights
    except ImportError:
        log.error("Biblioteca facebook_business não encontrada. Instale: pip install facebook-business")
        return None

    app_id = os.getenv("META_APP_ID")
    app_secret = os.getenv("META_APP_SECRET")
    access_token = os.getenv("META_ACCESS_TOKEN")

    if not all([app_id, app_secret, access_token]):
        log.error("Credenciais Meta incompletas no .env (META_APP_ID, META_APP_SECRET, META_ACCESS_TOKEN).")
        return None

    FacebookAdsApi.init(app_id, app_secret, access_token)

    data_fim = datetime.now().strftime("%Y-%m-%d")
    data_inicio = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")

    account = AdAccount(account_id)

    campos = [
        AdsInsights.Field.spend,
        AdsInsights.Field.impressions,
        AdsInsights.Field.reach,
        AdsInsights.Field.clicks,
        AdsInsights.Field.ctr,
        AdsInsights.Field.actions,
        AdsInsights.Field.cost_per_action_type,
        AdsInsights.Field.frequency,
    ]

    if cliente.get("objetivo") == "vendas":
        campos.append(AdsInsights.Field.purchase_roas)

    params = {
        "time_range": {"since": data_inicio, "until": data_fim},
        "level": "account",
        "time_increment": 1,
    }

    log.info(f"[{cliente['nome']}] Coletando dados Meta de {data_inicio} até {data_fim}...")

    insights = account.get_insights(fields=campos, params=params)

    dias_data = []
    for insight in insights:
        dia = dict(insight)
        actions = dia.pop("actions", []) or []
        cost_per_action = dia.pop("cost_per_action_type", []) or []

        for a in actions:
            tipo = a.get("action_type", "")
            valor = float(a.get("value", 0))
            if tipo in ("lead", "offsite_conversion.fb_pixel_lead"):
                dia["leads"] = dia.get("leads", 0) + valor
            elif tipo in ("purchase", "offsite_conversion.fb_pixel_purchase"):
                dia["compras"] = dia.get("compras", 0) + valor

        for c in cost_per_action:
            tipo = c.get("action_type", "")
            valor = float(c.get("value", 0))
            if tipo in ("lead", "offsite_conversion.fb_pixel_lead"):
                dia["cpa_lead"] = valor
            elif tipo in ("purchase", "offsite_conversion.fb_pixel_purchase"):
                dia["cpa_compra"] = valor

        roas_lista = dia.pop("purchase_roas", []) or []
        if roas_lista:
            dia["roas"] = float(roas_lista[0].get("value", 0))

        for campo in ("spend", "impressions", "reach", "clicks", "ctr", "frequency"):
            if campo in dia:
                try:
                    dia[campo] = float(dia[campo])
                except (ValueError, TypeError):
                    pass

        dias_data.append(dia)

    resultado = {
        "cliente": cliente["nome"],
        "plataforma": "meta",
        "account_id": account_id,
        "periodo": {"inicio": data_inicio, "fim": data_fim},
        "coletado_em": datetime.now().isoformat(),
        "dias": dias_data,
        "totais": {
            "spend": sum(d.get("spend", 0) for d in dias_data),
            "impressions": sum(d.get("impressions", 0) for d in dias_data),
            "clicks": sum(d.get("clicks", 0) for d in dias_data),
            "leads": sum(d.get("leads", 0) for d in dias_data),
            "compras": sum(d.get("compras", 0) for d in dias_data),
        },
    }

    totais = resultado["totais"]
    if totais["leads"] > 0:
        totais["cpa"] = totais["spend"] / totais["leads"]
    elif totais["compras"] > 0:
        totais["cpa"] = totais["spend"] / totais["compras"]

    if totais["clicks"] > 0:
        totais["ctr_medio"] = totais["clicks"] / max(totais["impressions"], 1) * 100

    return resultado


def salvar_resultado(resultado: dict, cliente_slug: str) -> Path:
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    data_dir = BASE_DIR / "data"
    data_dir.mkdir(exist_ok=True)
    caminho = data_dir / f"meta_{cliente_slug}_{data_hoje}.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    return caminho


def main():
    log.info("=== Iniciando coleta Meta Ads ===")
    clientes = carregar_clientes()
    resumo = []

    for cliente in clientes:
        if not cliente.get("ativo", True):
            log.info(f"[{cliente['nome']}] Cliente marcado como inativo. Pulando.")
            continue

        slug = cliente.get("slug") or slugify(cliente["nome"])

        resultado = coletar_meta_cliente(cliente)
        if resultado is None:
            resumo.append({"cliente": cliente["nome"], "status": "pulado"})
            continue

        caminho = salvar_resultado(resultado, slug)
        totais = resultado["totais"]
        log.info(
            f"[{cliente['nome']}] ✅ Salvo em {caminho.name} | "
            f"Gasto: R${totais['spend']:.2f} | "
            f"Leads: {totais.get('leads', 0):.0f} | "
            f"Compras: {totais.get('compras', 0):.0f}"
        )
        resumo.append({"cliente": cliente["nome"], "status": "ok", "arquivo": str(caminho.name)})

    log.info("=== Coleta Meta Ads concluída ===")
    print("\n--- RESUMO ---")
    for r in resumo:
        status_icon = "✅" if r["status"] == "ok" else "⚠️"
        print(f"{status_icon} {r['cliente']}: {r['status']}")


if __name__ == "__main__":
    main()
