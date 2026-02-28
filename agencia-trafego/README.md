# Sistema de Gestão de Tráfego Pago

Sistema completo para gerenciamento de campanhas Meta Ads e Google Ads com análise automática, dashboards e alertas.

## Estrutura

```
agencia-trafego/
├── clientes/
│   └── clientes.json          # Cadastro de clientes e metas
├── data/                      # Dados coletados das APIs (gerado automaticamente)
├── dashboards/
│   └── template_dashboard.html # Template HTML dos relatórios
├── logs/                      # Logs de execução (gerado automaticamente)
├── scripts/
│   ├── coletor_meta.py        # Coleta dados do Meta Ads
│   ├── coletor_google.py      # Coleta dados do Google Ads
│   ├── analisador.py          # Motor de análise e diagnóstico
│   ├── gerar_dashboards.py    # Gerador de relatórios HTML
│   └── scheduler.py           # Agendador de tarefas diárias
├── alertas/
│   └── verificador.py         # Verificador e disparador de alertas
├── .env.example               # Template de credenciais
├── .gitignore
└── requirements.txt
```

## Configuração

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar credenciais

```bash
cp .env.example .env
# Editar .env com suas credenciais reais
```

### 3. Cadastrar clientes

Edite `clientes/clientes.json` com os dados reais dos clientes (account_ids, metas de CPA, etc).

## Uso

```bash
# Coletar dados
python3 scripts/coletor_meta.py
python3 scripts/coletor_google.py

# Analisar um cliente
python3 scripts/analisador.py "Nome do Cliente"

# Analisar toda a carteira
python3 scripts/analisador.py --carteira

# Gerar dashboard de um cliente
python3 scripts/gerar_dashboards.py "Nome do Cliente"

# Gerar todos os dashboards
python3 scripts/gerar_dashboards.py --todos

# Verificar alertas agora
python3 alertas/verificador.py

# Testar integrações WhatsApp e e-mail
python3 alertas/verificador.py --teste

# Executar rotina completa agora
python3 scripts/scheduler.py --agora
```

## Agendamento Automático (cron — Mac/Linux)

```bash
crontab -e
# Adicionar:
0 8 * * * cd ~/Documentos/agencia-trafego && python3 scripts/scheduler.py --agora >> logs/scheduler.log 2>&1
```
