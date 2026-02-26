#!/usr/bin/env python3
"""
Coletor de dados do Google Ads.
Conecta à Google Ads API via GAQL e baixa métricas dos últimos 14 dias
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

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

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


def _build_google_client():
    """Constrói e retorna o cliente da Google Ads API."""
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError:
        log.error("Biblioteca google-ads não encontrada. Instale: pip install google-ads")
        return None

    credentials = {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        "use_proto_plus": True,
    }

    missing = [k for k, v in credentials.items() if not v]
    if missing:
        log.error(f"Credenciais Google Ads incompletas no .env: {missing}")
        return None

    return GoogleAdsClient.load_from_dict(credentials)


def coletar_google_cliente(cliente: dict, dias: int = 14) -> dict | None:
    """
    Puxa métricas do Google Ads para um cliente via GAQL.
    Retorna dicionário com métricas ou None em caso de erro.
    """
    customer_id_raw = cliente.get("customer_id_google", "").strip()
    if not customer_id_raw or customer_id_raw.startswith("123-456"):
        log.warning(f"[{cliente['nome']}] customer_id Google não configurado ou é exemplo. Pulando.")
        return None

    customer_id = customer_id_raw.replace("-", "")

    google_client = _build_google_client()
    if google_client is None:
        return None

    data_fim = datetime.now().strftime("%Y-%m-%d")
    data_inicio = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")

    log.info(f"[{cliente['nome']}] Coletando dados Google Ads de {data_inicio} até {data_fim}...")

    ga_service = google_client.get_service("GoogleAdsService")

    # Query GAQL — métricas diárias da conta
    query_conta = f"""
        SELECT
            segments.date,
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.ctr,
            metrics.conversions,
            metrics.cost_per_conversion,
            metrics.average_cpc
        FROM customer
        WHERE segments.date BETWEEN '{data_inicio}' AND '{data_fim}'
        ORDER BY segments.date ASC
    """

    # Query GAQL — quality score por keyword
    query_keywords = f"""
        SELECT
            ad_group_criterion.keyword.text,
            ad_group_criterion.quality_info.quality_score,
            metrics.cost_micros,
            metrics.clicks,
            metrics.conversions
        FROM keyword_view
        WHERE segments.date BETWEEN '{data_inicio}' AND '{data_fim}'
          AND ad_group_criterion.status != 'REMOVED'
        ORDER BY metrics.cost_micros DESC
        LIMIT 50
    """

    dias_data = []
    try:
        response = ga_service.search(customer_id=customer_id, query=query_conta)
        for row in response:
            dia = {
                "date": str(row.segments.date),
                "cost": row.metrics.cost_micros / 1_000_000,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "ctr": row.metrics.ctr * 100,
                "conversions": row.metrics.conversions,
                "cost_per_conversion": row.metrics.cost_per_conversion / 1_000_000 if row.metrics.conversions > 0 else 0,
                "average_cpc": row.metrics.average_cpc / 1_000_000,
            }
            dias_data.append(dia)
    except Exception as e:
        log.error(f"[{cliente['nome']}] Erro ao consultar métricas da conta: {e}")
        return None

    keywords_data = []
    try:
        response_kw = ga_service.search(customer_id=customer_id, query=query_keywords)
        for row in response_kw:
            kw = {
                "keyword": row.ad_group_criterion.keyword.text,
                "quality_score": row.ad_group_criterion.quality_info.quality_score,
                "cost": row.metrics.cost_micros / 1_000_000,
                "clicks": row.metrics.clicks,
                "conversions": row.metrics.conversions,
            }
            keywords_data.append(kw)
    except Exception as e:
        log.warning(f"[{cliente['nome']}] Aviso ao buscar keywords: {e}")

    totais = {
        "cost": sum(d.get("cost", 0) for d in dias_data),
        "impressions": sum(d.get("impressions", 0) for d in dias_data),
        "clicks": sum(d.get("clicks", 0) for d in dias_data),
        "conversions": sum(d.get("conversions", 0) for d in dias_data),
    }

    if totais["conversions"] > 0:
        totais["cpa"] = totais["cost"] / totais["conversions"]
    if totais["impressions"] > 0:
        totais["ctr_medio"] = totais["clicks"] / totais["impressions"] * 100

    qs_valores = [kw["quality_score"] for kw in keywords_data if kw.get("quality_score")]
    if qs_valores:
        totais["quality_score_medio"] = sum(qs_valores) / len(qs_valores)
    keywords_baixo_qs = [kw for kw in keywords_data if kw.get("quality_score", 10) < 6]

    resultado = {
        "cliente": cliente["nome"],
        "plataforma": "google",
        "customer_id": customer_id,
        "periodo": {"inicio": data_inicio, "fim": data_fim},
        "coletado_em": datetime.now().isoformat(),
        "dias": dias_data,
        "keywords": keywords_data,
        "keywords_baixo_qs": keywords_baixo_qs,
        "totais": totais,
    }

    return resultado


def salvar_resultado(resultado: dict, cliente_slug: str) -> Path:
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    data_dir = BASE_DIR / "data"
    data_dir.mkdir(exist_ok=True)
    caminho = data_dir / f"google_{cliente_slug}_{data_hoje}.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    return caminho


def main():
    log.info("=== Iniciando coleta Google Ads ===")
    clientes = carregar_clientes()
    resumo = []

    for cliente in clientes:
        if not cliente.get("ativo", True):
            log.info(f"[{cliente['nome']}] Cliente marcado como inativo. Pulando.")
            continue

        slug = cliente.get("slug") or slugify(cliente["nome"])
        resultado = coletar_google_cliente(cliente)

        if resultado is None:
            resumo.append({"cliente": cliente["nome"], "status": "pulado"})
            continue

        caminho = salvar_resultado(resultado, slug)
        totais = resultado["totais"]
        log.info(
            f"[{cliente['nome']}] ✅ Salvo em {caminho.name} | "
            f"Gasto: R${totais['cost']:.2f} | "
            f"Conversões: {totais.get('conversions', 0):.0f} | "
            f"QS médio: {totais.get('quality_score_medio', 'N/A')}"
        )
        resumo.append({"cliente": cliente["nome"], "status": "ok", "arquivo": str(caminho.name)})

    log.info("=== Coleta Google Ads concluída ===")
    print("\n--- RESUMO ---")
    for r in resumo:
        status_icon = "✅" if r["status"] == "ok" else "⚠️"
        print(f"{status_icon} {r['cliente']}: {r['status']}")


if __name__ == "__main__":
    main()
