# 🦈 Cidinha - Assistente Virtual SharkDev

**Cidinha** é a assistente virtual inteligente da **SharkDev**, projetada para auxiliar na produtividade, programação e entretenimento da equipa. Ela utiliza uma arquitetura de agentes baseada em grafos (**LangGraph**) para orquestrar diferentes modelos de IA e ferramentas externas.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit)
![LangChain](https://img.shields.io/badge/Orchestrator-LangGraph-1C3C3C?style=for-the-badge&logo=langchain)
![Gemini](https://img.shields.io/badge/Brain-Gemini%201.5-4285F4?style=for-the-badge&logo=google-gemini)
![OpenAI](https://img.shields.io/badge/Built%20with-OpenAI%20GPT--4o-purple?style=flat-square&logo=openai&logoColor=white)

---

## 🚀 Funcionalidades

A Cidinha atua como uma agente autónoma que seleciona a ferramenta correta para cada solicitação:

### 🏢 Produtividade (Google Workspace)
* **📅 Agenda:** Consulta compromissos e cria novos eventos no Google Calendar.
* **📧 E-mail:** Lê a caixa de entrada, filtra mensagens por data/assunto e envia e-mails.
* **👥 Contactos:** Reconhece automaticamente os e-mails da equipa SharkDev para facilitar o envio.

### 💻 Desenvolvimento
* **🤖 Pair Programmer:** Utiliza o modelo **Claude 3** para gerar código, refatorar scripts e explicar conceitos de programação.
* **🦈 Shark Helper:** Um mentor especializado para dúvidas internas sobre a SharkDev, Blip e bots, utilizando RAG (Retrieval-Augmented Generation).

### 📰 Informação & Lazer
* **🗞️ Notícias:** Busca as últimas notícias via API GNews e utiliza a **Maritaca AI** para gerar resumos em português.
* **🐉 Mestre de RPG:** Responde a dúvidas sobre regras de D&D 5e consultando uma base de conhecimento vetorial.

### 👁️ Multimodalidade
* Suporte para upload e análise de ficheiros (imagens e texto) diretamente no chat.

---

## 🛠️ Stack Tecnológica

O projeto integra diversos LLMs para aproveitar o melhor de cada um:

* **Orquestração:** [LangGraph](https://langchain-ai.github.io/langgraph/) (StateGraph).
* **LLM Principais (Agente):** Google Gemini 3 Flash e GPT 5 Nano.
* **LLM Coding:** Anthropic Claude 4 Haiku.
* **LLM PT-BR:** Maritaca AI (Sabiazinho-4).
* **Vector DB:** ChromaDB com Google Generative AI Embeddings.
* **Interface:** Streamlit com CSS personalizado.

---

## ⚙️ Configuração

### 1. Instalação
Clone o repositório e instale as dependências:

```bash
git clone [https://github.com/seu-usuario/cidinha-sharkdev.git](https://github.com/seu-usuario/cidinha-sharkdev.git)
cd cidinha-sharkdev
pip install -r requirements.txt
```

###2. Variáveis de Ambiente
Crie um ficheiro .env na raiz ou configure os secrets do Streamlit com as seguintes chaves:

```Ini, TOML
ORCHESTRATOR_MODEL="gpt" | "gemini" | "claude" | "maritaca"

# Modelos de IA
GEMINI_API_KEY="sua_chave"
GEMINI_MODEL="gemini-3-flash-preview"
GEMINI_EMBEDDING_MODEL="models/embedding-001"

CLAUDE_API_KEY="sua_chave"
CLAUDE_MODEL="claude-haiku-4-5-20251001"

MARITACA_API_KEY="sua_chave"
MARITACA_MODEL="sabiazinho-4"

OPENAI_MODEL="gpt-5-nano"
OPENAI_API_KEY="sua_chave"

# Ferramentas Externas
GNEWS_API_KEY="sua_chave"

# Banco de Dados Vetorial (RAG)
CHROMA_API_KEY="sua_chave"
CHROMA_TENANT="default_tenant"
CHROMA_DATABASE="default_database"
CHROMA_HOST="seu_host_chroma"

# Autenticação Google
GOOGLE_CLIENT_ID="seu_client_id"
GOOGLE_CLIENT_SECRET='{"web":{...}}' # JSON string ou caminho para ficheiro
AUTH_REDIRECT_URI="http://localhost:8501"
AUTH_COOKIE_SECRET="string_aleatoria"
```

### 3. Execução
Inicie a aplicação Streamlit:

```Bash
streamlit run app/main.py
```

## 📂 Estrutura do Projeto
```Plaintext

personal-assistant/
├── app/
│   ├── agent/          # Lógica do Agente e Grafo
│   ├── assets/         # Imagens e dados estáticos
│   ├── interface/      # UI, Renderização e Estado
│   ├── models/         # Definições Pydantic (Inputs das Tools)
│   ├── services/       # Clientes de API (Google, Chroma)
│   ├── tools/          # Ferramentas (News, Code, RPG, Shark, Google)
│   ├── utils/          # Configurações e Embeddings
│   └── main.py         # Ponto de entrada
├── .devcontainer/      # Configuração Docker/Codespaces
├── requirements.txt    # Dependências
└── README.md
```

## 📄 Licença
Este projeto está licenciado sob a GNU GPLv3. Consulte o ficheiro LICENSE para mais detalhes.
