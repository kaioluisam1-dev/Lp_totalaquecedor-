#!/usr/bin/env python3
"""
Verificador automático de alertas.
Analisa todos os clientes, detecta anomalias críticas
e envia alertas via WhatsApp (Zapi) e e-mail (SendGrid).

Uso:
  python3 alertas/verificador.py              # verifica todos
  python3 alertas/verificador.py --teste      # envia mensagem de teste
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"alertas_{datetime.now().strftime('%Y-%m-%d')}.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

DATA_DIR = BASE_DIR / "data"
CLIENTES_PATH = BASE_DIR / "clientes" / "clientes.json"


# ── Thresholds ──────────────────────────────────────────────────────────────
THRESHOLDS = {
    "cpa_critico": 2.0,
    "roas_critico_dias": 3,
    "frequencia_critica": 3.5,
    "gasto_minimo_alerta": 100.0,
    "budget_esgotado_hora": 12,
}


def slugify(texto: str) -> str:
    texto = texto.lower().strip()
    texto = re.sub(r"[^\w\s-]", "", texto)
    texto = re.sub(r"[\s_-]+", "-", texto)
    return texto


def carregar_clientes() -> list:
    with open(CLIENTES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def carregar_dados_recentes(plataforma: str, slug: str) -> dict | None:
    arquivos = sorted(DATA_DIR.glob(f"{plataforma}_{slug}_*.json"), reverse=True)
    if not arquivos:
        return None
    with open(arquivos[0], "r", encoding="utf-8") as f:
        return json.load(f)


def verificar_cliente(cliente: dict) -> list[dict]:
    """Retorna lista de alertas para um cliente. Lista vazia = tudo ok."""
    alertas = []
    slug = cliente.get("slug") or slugify(cliente["nome"])
    nome = cliente["nome"]

    # ── Meta Ads ──────────────────────────────────────────────────────────
    dados_meta = carregar_dados_recentes("meta", slug)
    if dados_meta:
        totais = dados_meta.get("totais", {})
        spend = totais.get("spend", 0)
        cpa_real = totais.get("cpa")
        cpa_meta_val = cliente.get("meta_cpa")
        roas_real = totais.get("roas")
        roas_meta_val = cliente.get("meta_roas")

        dias = dados_meta.get("dias", [])

        # CPA crítico com gasto mínimo
        if cpa_real and cpa_meta_val and spend >= THRESHOLDS["gasto_minimo_alerta"]:
            ratio = cpa_real / cpa_meta_val
            if ratio >= THRESHOLDS["cpa_critico"]:
                alertas.append({
                    "nivel": "critico",
                    "plataforma": "Meta",
                    "cliente": nome,
                    "mensagem": (
                        f"🔴 [{nome}] CPA Meta R${cpa_real:.2f} está {ratio:.1f}x acima da meta "
                        f"(R${cpa_meta_val:.2f}). Gasto: R${spend:.2f}."
                    ),
                    "sugestao": "Sugestão: revisar criativos e pausar ad sets com pior CPA.",
                })

        # ROAS abaixo da meta por 3+ dias consecutivos
        if roas_meta_val and dias:
            dias_roas_baixo = 0
            for dia in sorted(dias, key=lambda d: d.get("date_start", ""), reverse=True):
                roas_dia = dia.get("roas")
                if roas_dia is not None:
                    if roas_dia < roas_meta_val:
                        dias_roas_baixo += 1
                    else:
                        break
                if dias_roas_baixo >= THRESHOLDS["roas_critico_dias"]:
                    alertas.append({
                        "nivel": "critico",
                        "plataforma": "Meta",
                        "cliente": nome,
                        "mensagem": (
                            f"🔴 [{nome}] ROAS Meta {roas_real:.2f}x abaixo da meta "
                            f"{roas_meta_val:.2f}x por {dias_roas_baixo} dias consecutivos."
                        ),
                        "sugestao": "Sugestão: revisar funil de vendas e landing pages.",
                    })
                    break

        # Campanha parou de veicular
        if dias:
            ultimo_dia = dias[-1]
            impr = float(ultimo_dia.get("impressions", 1))
            if impr == 0:
                alertas.append({
                    "nivel": "critico",
                    "plataforma": "Meta",
                    "cliente": nome,
                    "mensagem": f"🔴 [{nome}] Campanha Meta com 0 impressões no último dia — verificar se está ativa.",
                    "sugestao": "Sugestão: checar status das campanhas e orçamento no painel.",
                })

        # Frequência crítica
        freq_vals = [float(d.get("frequency", 0)) for d in dias if d.get("frequency")]
        if freq_vals:
            freq_media = sum(freq_vals) / len(freq_vals)
            if freq_media >= THRESHOLDS["frequencia_critica"]:
                alertas.append({
                    "nivel": "atencao",
                    "plataforma": "Meta",
                    "cliente": nome,
                    "mensagem": (
                        f"🟡 [{nome}] Frequência Meta {freq_media:.1f} (acima de {THRESHOLDS['frequencia_critica']}) "
                        f"— risco de fadiga de criativos."
                    ),
                    "sugestao": "Sugestão: inserir novos criativos e/ou ampliar o público.",
                })

        # Budget esgotado antes das 12h (verifica se spend do dia = budget diário)
        meta_budget = cliente.get("meta_budget_diario", 0)
        if dias and meta_budget > 0:
            spend_hoje = float(dias[-1].get("spend", 0))
            hora_atual = datetime.now().hour
            if spend_hoje >= meta_budget * 0.95 and hora_atual < THRESHOLDS["budget_esgotado_hora"]:
                alertas.append({
                    "nivel": "atencao",
                    "plataforma": "Meta",
                    "cliente": nome,
                    "mensagem": (
                        f"🟡 [{nome}] Budget Meta esgotado antes das {THRESHOLDS['budget_esgotado_hora']}h "
                        f"(R${spend_hoje:.2f} de R${meta_budget:.2f})."
                    ),
                    "sugestao": "Sugestão: considerar aumentar o budget diário.",
                })

    # ── Google Ads ────────────────────────────────────────────────────────
    dados_google = carregar_dados_recentes("google", slug)
    if dados_google:
        totais = dados_google.get("totais", {})
        cost = totais.get("cost", 0)
        cpa_real = totais.get("cpa")
        cpa_meta_val = cliente.get("google_cpa")
        dias = dados_google.get("dias", [])

        # CPA crítico
        if cpa_real and cpa_meta_val and cost >= THRESHOLDS["gasto_minimo_alerta"]:
            ratio = cpa_real / cpa_meta_val
            if ratio >= THRESHOLDS["cpa_critico"]:
                alertas.append({
                    "nivel": "critico",
                    "plataforma": "Google",
                    "cliente": nome,
                    "mensagem": (
                        f"🔴 [{nome}] CPA Google R${cpa_real:.2f} está {ratio:.1f}x acima da meta "
                        f"(R${cpa_meta_val:.2f}). Gasto: R${cost:.2f}."
                    ),
                    "sugestao": "Sugestão: negativar keywords com CPA alto e revisar lances.",
                })

        # Campanha parou de veicular
        if dias:
            ultimo_dia = dias[-1]
            if float(ultimo_dia.get("impressions", 1)) == 0:
                alertas.append({
                    "nivel": "critico",
                    "plataforma": "Google",
                    "cliente": nome,
                    "mensagem": f"🔴 [{nome}] Campanha Google com 0 impressões no último dia.",
                    "sugestao": "Sugestão: verificar status e orçamento no Google Ads.",
                })

    return alertas


def formatar_whatsapp(alertas: list[dict]) -> str:
    if not alertas:
        return "✅ *Verificação concluída — Nenhuma anomalia crítica encontrada.*"
    linhas = ["🚨 *ALERTAS DE PERFORMANCE* 🚨", ""]
    for a in alertas:
        linhas.append(a["mensagem"])
        linhas.append(f"   _{a['sugestao']}_")
        linhas.append("")
    linhas.append(f"_Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}_")
    return "\n".join(linhas)


def enviar_whatsapp(mensagem: str) -> bool:
    instance_id = os.getenv("ZAPI_INSTANCE_ID")
    token = os.getenv("ZAPI_TOKEN")
    grupo_id = os.getenv("WHATSAPP_GRUPO_ID")

    if not all([instance_id, token, grupo_id]):
        log.warning("Credenciais Zapi incompletas. WhatsApp não enviado.")
        return False

    url = f"https://api.z-api.io/instances/{instance_id}/token/{token}/send-text"
    payload = {"phone": grupo_id, "message": mensagem}

    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        log.info("✅ Alerta WhatsApp enviado com sucesso.")
        return True
    except requests.RequestException as e:
        log.error(f"❌ Erro ao enviar WhatsApp: {e}")
        return False


def enviar_email(alertas: list[dict]) -> bool:
    api_key = os.getenv("SENDGRID_API_KEY")
    remetente = os.getenv("EMAIL_REMETENTE")
    destinatario = os.getenv("EMAIL_DESTINO")

    if not all([api_key, remetente, destinatario]):
        log.warning("Credenciais SendGrid incompletas. E-mail não enviado.")
        return False

    n_criticos = sum(1 for a in alertas if a["nivel"] == "critico")
    assunto = f"[ALERTA] {n_criticos} problema(s) crítico(s) — {datetime.now().strftime('%d/%m/%Y')}"

    corpo_html = f"""
    <h2>🚨 Alertas de Performance — {datetime.now().strftime('%d/%m/%Y %H:%M')}</h2>
    <p>{len(alertas)} alerta(s) identificado(s): {n_criticos} crítico(s).</p>
    <hr/>
    """
    for a in alertas:
        cor = "#dc2626" if a["nivel"] == "critico" else "#d97706"
        corpo_html += f"""
        <div style="border-left: 4px solid {cor}; padding: 12px 16px; margin: 12px 0; background: #fafafa;">
          <strong>{a['mensagem']}</strong><br/>
          <em style="color: #6b7280;">{a['sugestao']}</em>
        </div>
        """

    payload = {
        "personalizations": [{"to": [{"email": destinatario}]}],
        "from": {"email": remetente},
        "subject": assunto,
        "content": [{"type": "text/html", "value": corpo_html}],
    }

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        resp = requests.post("https://api.sendgrid.com/v3/mail/send", json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        log.info(f"✅ E-mail de alerta enviado para {destinatario}.")
        return True
    except requests.RequestException as e:
        log.error(f"❌ Erro ao enviar e-mail: {e}")
        return False


def enviar_teste() -> None:
    """Envia mensagem de teste para validar as integrações."""
    msg = (
        "✅ *Teste de integração — Sistema de Alertas*\n\n"
        f"Conexão WhatsApp funcionando!\n"
        f"_{datetime.now().strftime('%d/%m/%Y às %H:%M')}_"
    )
    print("Enviando WhatsApp de teste...")
    ok = enviar_whatsapp(msg)
    print("✅ WhatsApp OK" if ok else "❌ WhatsApp falhou")

    print("Enviando e-mail de teste...")
    ok2 = enviar_email([{
        "nivel": "atencao",
        "plataforma": "Teste",
        "cliente": "Teste",
        "mensagem": "🟡 [Teste] Mensagem de teste do sistema de alertas.",
        "sugestao": "Nenhuma ação necessária — apenas teste de integração.",
    }])
    print("✅ E-mail OK" if ok2 else "❌ E-mail falhou")


def main():
    parser = argparse.ArgumentParser(description="Verificador automático de alertas")
    parser.add_argument("--teste", action="store_true", help="Enviar mensagem de teste")
    parser.add_argument("--so-imprimir", action="store_true", help="Imprimir alertas sem enviar")
    args = parser.parse_args()

    if args.teste:
        enviar_teste()
        return

    log.info("=== Iniciando verificação de alertas ===")
    clientes = carregar_clientes()
    todos_alertas = []

    for cliente in clientes:
        if not cliente.get("ativo", True):
            continue
        alertas_cliente = verificar_cliente(cliente)
        if alertas_cliente:
            log.warning(f"[{cliente['nome']}] {len(alertas_cliente)} alerta(s) encontrado(s).")
        else:
            log.info(f"[{cliente['nome']}] ✅ Nenhuma anomalia.")
        todos_alertas.extend(alertas_cliente)

    mensagem_wpp = formatar_whatsapp(todos_alertas)
    print("\n" + mensagem_wpp)

    if not args.so_imprimir and todos_alertas:
        enviar_whatsapp(mensagem_wpp)
        enviar_email(todos_alertas)
    elif not todos_alertas:
        log.info("Nenhum alerta crítico — notificações não enviadas.")

    log.info(f"=== Verificação concluída: {len(todos_alertas)} alerta(s) ===")


if __name__ == "__main__":
    main()
