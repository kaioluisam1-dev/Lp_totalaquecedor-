#!/usr/bin/env python3
"""
Scheduler — Agendamento automático das tarefas diárias.

Executa toda manhã às 8h:
  1. coletor_meta.py
  2. coletor_google.py
  3. analisador.py (carteira completa)
  4. verificador.py (alertas)

No último dia da quinzena (15 e no último dia do mês):
  5. gerar_dashboards.py (todos os clientes)

Uso:
  python3 scripts/scheduler.py          # inicia o agendador (roda indefinidamente)
  python3 scripts/scheduler.py --agora  # executa todas as tarefas agora (teste)

Configuração cron (Mac/Linux) — rode 'crontab -e' e adicione:
  0 8 * * * cd ~/Documentos/agencia-trafego && python3 scripts/scheduler.py --agora >> logs/scheduler.log 2>&1

Configuração Windows (PowerShell como administrador):
  schtasks /create /tn "AgenciaTrafego" /tr "python3 C:\\caminho\\scripts\\scheduler.py --agora" /sc daily /st 08:00
"""

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "scheduler.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

SCRIPTS_DIR = BASE_DIR / "scripts"
ALERTAS_DIR = BASE_DIR / "alertas"
PYTHON = sys.executable


def executar(nome: str, script: Path, args: list[str] | None = None) -> bool:
    """Executa um script Python e registra início/fim no log."""
    cmd = [PYTHON, str(script)] + (args or [])
    log.info(f"▶  Iniciando: {nome}")
    inicio = datetime.now()
    try:
        result = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=False, text=True, timeout=600)
        duracao = (datetime.now() - inicio).seconds
        if result.returncode == 0:
            log.info(f"✅ Concluído: {nome} ({duracao}s)")
            return True
        else:
            log.error(f"❌ Erro em {nome} (código {result.returncode}) após {duracao}s")
            return False
    except subprocess.TimeoutExpired:
        log.error(f"⏱  Timeout em {nome} (>600s)")
        return False
    except Exception as e:
        log.error(f"❌ Exceção em {nome}: {e}")
        return False


def eh_ultimo_dia_quinzena() -> bool:
    hoje = datetime.now()
    import calendar
    ultimo_dia_mes = calendar.monthrange(hoje.year, hoje.month)[1]
    return hoje.day == 15 or hoje.day == ultimo_dia_mes


def executar_rotina_diaria() -> None:
    log.info("=" * 60)
    log.info(f"ROTINA DIÁRIA — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    log.info("=" * 60)

    tarefas = [
        ("Coletor Meta Ads",    SCRIPTS_DIR / "coletor_meta.py",    None),
        ("Coletor Google Ads",  SCRIPTS_DIR / "coletor_google.py",  None),
        ("Analisador Carteira", SCRIPTS_DIR / "analisador.py",      ["--carteira"]),
        ("Verificador Alertas", ALERTAS_DIR  / "verificador.py",    None),
    ]

    resultados = {}
    for nome, script, args in tarefas:
        if not script.exists():
            log.warning(f"⚠️  Script não encontrado: {script}. Pulando.")
            resultados[nome] = "não encontrado"
            continue
        ok = executar(nome, script, args)
        resultados[nome] = "ok" if ok else "erro"

    if eh_ultimo_dia_quinzena():
        log.info("📊 Último dia da quinzena — gerando dashboards...")
        script_dash = SCRIPTS_DIR / "gerar_dashboards.py"
        if script_dash.exists():
            ok = executar("Gerador Dashboards", script_dash, ["--todos"])
            resultados["Gerador Dashboards"] = "ok" if ok else "erro"

    log.info("=" * 60)
    log.info("RESUMO DA ROTINA:")
    for nome, status in resultados.items():
        emoji = "✅" if status == "ok" else ("⚠️" if status == "não encontrado" else "❌")
        log.info(f"  {emoji} {nome}: {status}")
    log.info("=" * 60)


def iniciar_agendador() -> None:
    """Mantém o processo rodando e dispara às 8h todo dia."""
    try:
        import schedule
        import time
    except ImportError:
        log.error("Biblioteca 'schedule' não instalada. Execute: pip install schedule")
        sys.exit(1)

    schedule.every().day.at("08:00").do(executar_rotina_diaria)
    log.info("⏰ Scheduler iniciado. Próxima execução às 08:00.")
    log.info("   Pressione Ctrl+C para parar.")

    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="Scheduler de tarefas de tráfego")
    parser.add_argument(
        "--agora",
        action="store_true",
        help="Executar todas as tarefas imediatamente (útil para teste e cron)",
    )
    args = parser.parse_args()

    if args.agora:
        executar_rotina_diaria()
    else:
        iniciar_agendador()


if __name__ == "__main__":
    main()
