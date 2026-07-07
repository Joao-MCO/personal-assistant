# 🦈 Cidinha - Assistente Virtual SharkDev

**Cidinha** é a assistente virtual inteligente da **SharkDev**, projetada para auxiliar na produtividade e no acesso a conhecimento interno da equipa. Ela utiliza uma arquitetura de agentes baseada em grafos (**LangGraph**) para orquestrar diferentes modelos de IA e ferramentas externas, exposta através de uma **API REST (FastAPI)**.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)

![Gemini](https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=google%20gemini&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![Claude](https://img.shields.io/badge/Anthropic%20Claude-D97757?style=for-the-badge&logo=anthropic&logoColor=white)

</div>

---

## 🚀 Funcionalidades

A Cidinha atua como uma agente autónoma que seleciona a ferramenta correta para cada solicitação:

### 🏢 Produtividade (Google Workspace)
* **📅 Agenda:** Consulta compromissos e cria novos eventos no Google Calendar.
* **📧 E-mail:** Lê a caixa de entrada, filtra mensagens por data/assunto e envia e-mails.
* **📁 Google Drive:** Busca atas de reunião e documentos já existentes no Drive (`BuscarNoDrive`).
* **👥 Contactos:** Reconhece automaticamente os e-mails da equipa SharkDev para facilitar o envio.

### 🦈 Conhecimento Interno
* **Shark Helper:** Um mentor especializado para dúvidas internas sobre a SharkDev, Blip e bots, utilizando RAG (Retrieval-Augmented Generation) sobre uma base vetorial (ChromaDB).
* **RAG da Base de Código:** RAG sobre a documentação técnica/arquitetura dos repositórios (`RAGDaBaseDeCodigo`).
* **Onboarding Guiado:** RAG sobre documentação de onboarding para quem está entrando na empresa (`OnboardingGuiado`).

### 🧑‍💻 Engenharia de Código (especialistas em Claude)
* **Revisor de Código:** Revisão de qualidade geral de um trecho/PR colado (`RevisorDeCodigo`).
* **Gerador de Testes:** Gera testes unitários a partir de uma função (`GeradorDeTestes`).
* **Diagnóstico de Erro:** Analisa um stack trace/log colado e sugere a causa e o fix (`DiagnosticoDeErro`).
* **Gerador de Documentação:** Gera docstrings ou um README a partir do código (`GeradorDeDocumentacao`).
* **Revisor de Segurança:** Aponta vulnerabilidades conhecidas (SQLi, XSS, segredos hardcoded) (`RevisorDeSeguranca`).

### 🔁 Fluxo de Desenvolvimento
* **Gerador de Commit Message:** Gera uma mensagem de commit (Conventional Commits) a partir de um diff (`GeradorDeCommitMessage`).
* **Auditoria de Dependências:** Roda `pip-audit` de verdade contra um requirements.txt e resume os achados (`AuditoriaDeDependencias`).
* **Gerador de Standup:** Resumo de standup **individual**, a partir dos commits reais do usuário no GitHub — não pede pra digitar o que fez (`GeradorDeStandup`).
* **Tradutor Técnico:** Traduz texto técnico entre português e inglês (`TradutorTecnico`).

### 📊 Monitoramento (sem LLM)
* **Monitor de Custos LLM:** Agrega gasto/uso de tokens por modelo e por skill (`MonitorDeCustosLLM`).
* **Health Check Agregado:** Verifica a saúde do banco, do Chroma e de quais credenciais de LLM estão configuradas (`HealthCheckAgregado`).

### 👁️ Multimodalidade
* Suporte para upload e análise de ficheiros (imagens e texto) diretamente na conversa.

---

## 🛠️ Stack Tecnológica

* **Orquestração:** [LangGraph](https://langchain-ai.github.io/langgraph/) (StateGraph).
* **API:** [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn.
* **Banco de dados:** SQLAlchemy + Alembic (SQLite em desenvolvimento, Postgres em produção — troca só via `DATABASE_URL`).
* **LLMs suportados:** Google Gemini, OpenAI GPT e Anthropic Claude. Estratégia de orquestração: o `ORCHESTRATOR_MODEL` (rápido/barato, hoje Gemini) decide qual ferramenta chamar; cada skill especialista (`RevisorDeCodigo`, `GeradorDeTestes`...) usa internamente o modelo mais adequado à própria tarefa (`MODEL_FAMILY` no topo de cada arquivo em `tools/`), independente do orquestrador — trocar um não afeta o outro.
* **Vector DB:** ChromaDB com Google Generative AI Embeddings.
* **Autenticação Google:** OAuth 2.0 (Calendar + Gmail), fluxo completo no backend.

> ℹ️ As variáveis `MARITACA_API_KEY`/`MARITACA_MODEL` continuam presentes em `utils/settings.py` mas **não estão** ligadas a nenhum modelo em `agent/llm_factory.py` — nunca chegaram a ser integradas. Fica registado aqui para não gerar confusão; se quiser usar a Maritaca como um dos LLMs disponíveis, é só adicionar uma entrada em `MODEL_CONFIG`, seguindo o mesmo padrão do Gemini/GPT/Claude.

---

## ⚙️ Configuração

### 1. Instalação
Clone o repositório e instale as dependências:

```bash
git clone [https://github.com/seu-usuario/cidinha-sharkdev.git](https://github.com/seu-usuario/cidinha-sharkdev.git)
cd cidinha-sharkdev
pip install -r requirements.txt
```

### 2. Variáveis de Ambiente
Crie um ficheiro `.env` na raiz do projeto com as seguintes chaves:

```Ini, TOML
ORCHESTRATOR_MODEL="gemini"  # "gemini" | "gpt" | "claude" — modelo padrão do agente

# Banco de dados — SQLite por padrão (zero configuração pra desenvolver).
# Em produção, aponte para o Postgres do Render (ou outro provedor):
# "postgresql://usuario:senha@host:5432/banco"
DATABASE_URL="sqlite:///./cidinha.db"

# Modelos de IA
GEMINI_API_KEY="sua_chave"
GEMINI_MODEL="gemini-3-flash-preview"
GEMINI_EMBEDDING_MODEL="models/embedding-001"

CLAUDE_API_KEY="sua_chave"
CLAUDE_MODEL="claude-haiku-4-5-20251001"

OPENAI_MODEL="gpt-5-nano"
OPENAI_API_KEY="sua_chave"

# Banco de Dados Vetorial (RAG)
CHROMA_API_KEY="sua_chave"
CHROMA_TENANT="default_tenant"
CHROMA_DATABASE="default_database"
CHROMA_HOST="seu_host_chroma"

# Autenticação Google (fluxo OAuth completo, ver seção "Endpoints" abaixo)
GOOGLE_CLIENT_ID="seu_client_id"
GOOGLE_CLIENT_SECRET='{"web":{...}}' # JSON string ou caminho para ficheiro
AUTH_REDIRECT_URI="http://localhost:8000/auth/google/callback"
AUTH_COOKIE_SECRET="string_aleatoria"

# GitHub (GeradorDeStandup) — Personal Access Token com escopo de leitura
GITHUB_TOKEN="ghp_seu_token_aqui"
GITHUB_ORG="sharkdev"  # opcional se você sempre informar repositórios específicos

# Proteção de /chat (header X-API-Key). Se não houver nenhum cliente
# cadastrado (ver seção "Banco de Dados" abaixo) e esta variável ficar vazia,
# a verificação é desabilitada — conveniente em dev, defina em produção.
API_KEY="uma_chave_forte_para_produção"

# Protege os endpoints administrativos /admin/* (header X-Admin-Token).
# Sem isso configurado, /admin/* fica desativado por completo (503).
ADMIN_TOKEN="outra_chave_forte_só_para_administração"

# Sessões de conversa — agora persistidas no banco (ver DATABASE_URL acima)
SESSION_TTL_MINUTES="120"

# Configurações do agente
MAX_TOKENS="4000"
TEMPERATURE="0.4"
```

### 3. Execução

A aplicação roda a partir de **dentro** da pasta `app/` (os imports internos do projeto são relativos a ela, o mesmo motivo pelo qual antes se rodava `streamlit run app/main.py`):

```bash
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Com o servidor no ar, a documentação interativa (Swagger) fica disponível em **http://localhost:8000/docs** — é a forma mais rápida de testar os endpoints manualmente, sem precisar de um frontend (cobre o que antes era feito testando direto na interface do Streamlit).

Em produção, prefira rodar por trás de um process manager (ex.: `uvicorn main:app --workers 4` supervisionado por systemd/Docker, ou `gunicorn -k uvicorn.workers.UvicornWorker`).

---

## 🗄️ Banco de Dados

Na primeira subida, a aplicação cria automaticamente todas as tabelas (via `Base.metadata.create_all`, chamado no evento de `startup` do FastAPI) e roda duas seeds, ambas idempotentes:
- **`employees`** é populada a partir de `app/assets/emails.json` — só na primeira vez; depois disso a tabela é a fonte da verdade e o JSON não é mais consultado em tempo de execução.
- **`api_clients`** recebe um cliente `"legacy"` se você já tiver `API_KEY` configurada no `.env` — assim ninguém perde acesso ao migrar de uma chave única para o sistema multi-cliente.

| Tabela | Para quê |
|---|---|
| `sessions` / `messages` | Histórico de conversa por `session_id` (antes: em memória, zerava a cada restart). |
| `google_credentials` | Token OAuth do Google por sessão (antes: também em memória). |
| `employees` | Contatos internos da SharkDev (antes: `emails.json` estático). |
| `api_clients` | Clientes autorizados a chamar `/chat`, cada um com sua própria chave, revogável individualmente (antes: uma única `API_KEY`). |
| `tool_calls` | Auditoria + analytics de cada chamada de ferramenta (Calendar, Gmail, Shark Helper...): parâmetros, resultado, sucesso/erro, duração. |
| `knowledge_documents` | Controle de quais arquivos já foram indexados no Chroma pelo Shark Helper (`app/utils/embedding.py`) — os vetores continuam só no Chroma, isso é só o registro de auditoria de cima. |

### Gerenciando funcionários e chaves de API

Os endpoints `/admin/*` (protegidos por `ADMIN_TOKEN`, header `X-Admin-Token`) cobrem o que antes exigia editar `emails.json` ou o `.env` e fazer um novo deploy:

```bash
# Adicionar um funcionário
curl -X POST http://localhost:8000/admin/employees \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nome": "Nome Sobrenome", "email": "nome@sharkdev.com.br"}'

# Emitir uma nova chave de API para um cliente/time específico
curl -X POST http://localhost:8000/admin/api-clients \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Bot do Slack"}'
# -> retorna {"id":.., "name":.., "api_key": "..."} — a chave só aparece aqui, guarde-a

# Revogar uma chave (sem afetar outros clientes)
curl -X DELETE http://localhost:8000/admin/api-clients/1 -H "X-Admin-Token: $ADMIN_TOKEN"
```

### Alterando o schema (Alembic)

Depois da primeira subida (que já cria as tabelas), **mudanças de schema devem passar por migração**, não por editar `app/db/models.py` e confiar no `create_all` de novo — em especial com dado real em produção, `create_all` não sabe fazer `ALTER TABLE`. O fluxo:

```bash
# 1. Edite app/db/models.py (adicione uma coluna, uma tabela, etc.)
# 2. Gere a migração automaticamente, a partir da raiz do projeto:
alembic revision --autogenerate -m "descreva a mudança"
# 3. Revise o arquivo gerado em migrations/versions/
# 4. Aplique:
alembic upgrade head
```

`migrations/env.py` já lê a mesma `DATABASE_URL` que a aplicação usa, então isso funciona igual em SQLite local e no Postgres de produção.

---

## 🔌 Endpoints principais

> ⚠️ **Se você já tinha usuários logados antes desta versão:** o escopo do Google Drive (`drive.readonly`) foi adicionado ao OAuth. Sessões que já fizeram login antes não têm esse escopo — `BuscarNoDrive` vai falhar para elas até a pessoa refazer `/auth/google/login`.

### Populando as novas bases de conhecimento (RAG)

`RAGDaBaseDeCodigo` e `OnboardingGuiado` consultam coleções do Chroma que começam vazias. Para popular (mesmo padrão do Shark Helper, mas para arquivos `.md`/`.txt` em vez de PDF):

```python
from services.text_ingestion import create_text_embedding

create_text_embedding("codebase_docs", "dados_codigo")      # READMEs, ADRs dos repositórios
create_text_embedding("onboarding_docs", "dados_onboarding") # docs de onboarding
```

Reindexação é incremental: um arquivo só é reprocessado se o conteúdo mudou desde a última vez (controlado por `knowledge_documents`, a mesma tabela que já rastreia a indexação do Shark Helper).


| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/chat` | Envia uma mensagem para a Cidinha. Aceita `multipart/form-data` com campos `message`, `session_id` (opcional), `llm` (opcional) e `files` (opcional, um ou mais anexos). |
| `GET` | `/chat/{session_id}/history` | Retorna o histórico completo de uma sessão. |
| `GET` | `/auth/google/login` | Inicia o login Google (redireciona o navegador para a tela de consentimento). Aceita `session_id` opcional na query. |
| `GET` | `/auth/google/callback` | Callback do Google — não é chamado manualmente. |
| `GET` | `/auth/google/status` | Verifica se uma sessão está autenticada no Google. |
| `POST` | `/auth/google/logout` | Remove as credenciais Google de uma sessão. |
| `GET` `POST` `DELETE` | `/admin/employees[/{id}]` | Lista, cria e desativa funcionários. Requer `X-Admin-Token`. |
| `GET` `POST` `DELETE` | `/admin/api-clients[/{id}]` | Lista, cria e revoga chaves de API. Requer `X-Admin-Token`. |
| `GET` | `/health` | Health check. |

`/chat` e `/chat/{session_id}/history` exigem o header `X-API-Key` se houver algum cliente cadastrado em `api_clients` (ver seção "Banco de Dados"). As rotas `/auth/google/*` são de acesso livre (fluxo de redirecionamento do navegador — ver comentário no topo de `app/api/auth.py` para o porquê). As rotas `/admin/*` exigem `X-Admin-Token` e ficam desativadas (503) se `ADMIN_TOKEN` não estiver configurado.

**Fluxo típico:** chame `/auth/google/login` num navegador (ou direcione o usuário para lá) para liberar Agenda/Gmail; guarde o `session_id` retornado no callback; use esse mesmo `session_id` em todas as chamadas a `/chat` para manter o contexto da conversa e o acesso ao Google.

---

## 📂 Estrutura do Projeto
```Plaintext

personal-assistant/
├── app/
│   ├── agent/          # Lógica do Agente e Grafo (LangGraph)
│   ├── api/             # Rotas da API (chat, auth, admin)
│   ├── assets/          # Dados estáticos (fonte da seed inicial de employees)
│   ├── db/              # Modelos SQLAlchemy, engine/sessão, seeds (base.py, models.py, seed.py)
│   ├── models/          # Definições Pydantic (Inputs das Tools)
│   ├── services/        # Google, Chroma, SessionStore, GitHub, auditoria/custo de LLM, ingestão de texto
│   ├── tools/           # As ~19 ferramentas: Shark, Google, código, dev workflow, monitoramento, RAG...
│   ├── utils/           # Configurações e Embeddings (PDF)
│   └── main.py          # Ponto de entrada (app FastAPI)
├── migrations/           # Migrações Alembic (schema do banco)
├── alembic.ini
├── requirements.txt      # Dependências
└── README.md
```

## 📄 Licença
Este projeto está licenciado sob a GNU GPLv3. Consulte o ficheiro LICENSE para mais detalhes.