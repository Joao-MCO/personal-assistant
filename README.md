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
* **👥 Contactos:** Reconhece automaticamente os e-mails da equipa SharkDev para facilitar o envio.

### 🦈 Conhecimento Interno
* **Shark Helper:** Um mentor especializado para dúvidas internas sobre a SharkDev, Blip e bots, utilizando RAG (Retrieval-Augmented Generation) sobre uma base vetorial (ChromaDB).

### 👁️ Multimodalidade
* Suporte para upload e análise de ficheiros (imagens e texto) diretamente na conversa.

---

## 🛠️ Stack Tecnológica

* **Orquestração:** [LangGraph](https://langchain-ai.github.io/langgraph/) (StateGraph).
* **API:** [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn.
* **LLMs suportados:** Google Gemini, OpenAI GPT e Anthropic Claude (escolha configurável, ver abaixo).
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

# Proteção da própria API (header X-API-Key). Deixe vazio em dev local se quiser.
API_KEY="uma_chave_forte_para_produção"

# Sessões de conversa em memória
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

## 🔌 Endpoints principais

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/chat` | Envia uma mensagem para a Cidinha. Aceita `multipart/form-data` com campos `message`, `session_id` (opcional), `llm` (opcional) e `files` (opcional, um ou mais anexos). |
| `GET` | `/chat/{session_id}/history` | Retorna o histórico completo de uma sessão. |
| `GET` | `/auth/google/login` | Inicia o login Google (redireciona o navegador para a tela de consentimento). Aceita `session_id` opcional na query. |
| `GET` | `/auth/google/callback` | Callback do Google — não é chamado manualmente. |
| `GET` | `/auth/google/status` | Verifica se uma sessão está autenticada no Google. |
| `POST` | `/auth/google/logout` | Remove as credenciais Google de uma sessão. |
| `GET` | `/health` | Health check. |

`/chat` e `/chat/{session_id}/history` exigem o header `X-API-Key` se `API_KEY` estiver configurada no `.env`. As rotas `/auth/google/*` são de acesso livre (fluxo de redirecionamento do navegador — ver comentário no topo de `app/api/auth.py` para o porquê).

**Fluxo típico:** chame `/auth/google/login` num navegador (ou direcione o usuário para lá) para liberar Agenda/Gmail; guarde o `session_id` retornado no callback; use esse mesmo `session_id` em todas as chamadas a `/chat` para manter o contexto da conversa e o acesso ao Google.

---

## 📂 Estrutura do Projeto
```Plaintext

personal-assistant/
├── app/
│   ├── agent/          # Lógica do Agente e Grafo (LangGraph)
│   ├── api/             # Rotas da API (chat, auth)
│   ├── assets/          # Dados estáticos (contactos internos)
│   ├── models/          # Definições Pydantic (Inputs das Tools)
│   ├── services/        # Clientes de API (Google, Chroma) e SessionStore
│   ├── tools/           # Ferramentas (Shark, Google Calendar, Gmail)
│   ├── utils/           # Configurações e Embeddings
│   └── main.py          # Ponto de entrada (app FastAPI)
├── requirements.txt      # Dependências
└── README.md
```

## 📄 Licença
Este projeto está licenciado sob a GNU GPLv3. Consulte o ficheiro LICENSE para mais detalhes.