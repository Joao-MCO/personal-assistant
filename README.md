# 🦈 Cidinha - Secretária Virtual da SharkDev

Bem-vindo ao repositório da **Cidinha**, a assistente virtual inteligente da **SharkDev**. Desenvolvida com as tecnologias mais modernas de IA Generativa, a Cidinha não é apenas um chatbot, mas um agente capaz de processar documentos, analisar imagens, codificar e até tirar dúvidas sobre RPG!

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-121011?style=for-the-badge&logo=chainlink&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google%20Gemini-4285F4?style=for-the-badge&logo=google-gemini&logoColor=white)
![Anthropic Claude](https://img.shields.io/badge/Claude%203-750139?style=for-the-badge&logo=anthropic&logoColor=white)

---

## 🚀 Funcionalidades

A Cidinha utiliza uma arquitetura de **Agente (LangGraph)** que decide qual ferramenta usar com base na sua necessidade:

*   **💻 Ajuda em Programação:** Especialista em Python e arquitetura, utilizando o modelo **Claude 3** para fornecer códigos limpos e debugging.
*   **📰 Resumo de Notícias:** Busca as últimas notícias via GNews API e utiliza a **Maritaca AI** para criar mini-artigos consolidados.
*   **🎲 Mestre de RPG:** Um especialista em D&D 5e que utiliza RAG (Busca em documentos) para tirar dúvidas de regras e mecânicas.
*   **🦈 Shark Helper:** Onboarding e suporte para desenvolvedores da SharkDev, focado em Blip e fluxos conversacionais.
*   **👁️ Visão Multimodal:** Capaz de ler e analisar arquivos anexados (Imagens, PDFs, TXT, JSON, CSV).
*   **🧠 Assuntos Gerais:** Conhecimento enciclopédico via Google Gemini.

---

## 🛠️ Stack Tecnológica

*   **Interface:** [Streamlit](https://streamlit.io/) com CSS personalizado (Dark Mode & Pink accents).
*   **Orquestração de IA:** [LangChain](https://www.langchain.com/) & [LangGraph](https://blog.langchain.dev/langgraph/).
*   **Modelos de Linguagem (LLMs):**
    *   Google Gemini 1.5 Flash/Pro (Cérebro principal e Visão).
    *   Anthropic Claude 3 (Codificação).
    *   Maritalk (Processamento de linguagem natural em PT-BR).
*   **Banco de Dados Vetorial:** [ChromaDB](https://www.trychroma.com/) para busca semântica (RAG).
*   **Embeddings:** Google Generative AI Embeddings.

---

## 📋 Pré-requisitos

Antes de começar, você precisará de chaves de API para os seguintes serviços:
*   Google AI Studio (Gemini)
*   Anthropic (Claude)
*   Maritaca AI
*   GNews API
*   ChromaDB (Cloud ou Local)

---

## ⚙️ Configuração

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/seu-usuario/cidinha-sharkdev.git
    cd cidinha-sharkdev
    ```

2.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Variáveis de Ambiente:**
    Crie um arquivo `.env` na raiz do projeto (ou configure no Streamlit Secrets):
    ```env
    GEMINI_API_KEY=sua_chave_aqui
    GEMINI_MODEL=gemini-1.5-flash
    GEMINI_EMBEDDING_MODEL=models/embedding-001

    MARITACA_API_KEY=sua_chave_aqui
    MARITACA_MODEL=sabia-2-medium

    CLAUDE_API_KEY=sua_chave_aqui
    CLAUDE_MODEL=claude-3-5-sonnet-20240620

    GNEWS_API_KEY=sua_chave_aqui

    CHROMA_API_KEY=sua_chave_aqui
    CHROMA_TENANT=seu_tenant
    CHROMA_DATABASE=seu_db
    ```

---

## 🏃‍♂️ Como Executar

Para iniciar a Cidinha, basta rodar o comando:

```bash
streamlit run main.py
```

---

## 📂 Estrutura do Projeto

```text
.
├── main.py           # Ponto de entrada da aplicação Streamlit
├── agent.py          # Orquestração do Agente e lógica do Grafo
├── tools.py          # Definição e schemas das ferramentas de IA
├── settings.py       # Gerenciamento de chaves de API e configurações
├── chroma.py         # Integração com o banco de dados vetorial
├── embedding.py      # Lógica de processamento e vetorização
├── encode_image.py   # Helper para processamento de imagens
├── render.py         # Componentes visuais e interface
├── state.py          # Gerenciamento de estado da sessão
├── styles.py         # Definições de CSS (SharkDev Theme)
│
├── codes.py          # Lógica: Ajuda em Programação
├── general.py        # Lógica: Assuntos Gerais
├── news.py           # Lógica: Notícias (GNews + Maritaca)
├── shark.py          # Lógica: Suporte SharkDev / Blip
└── manager.py        # Gerenciador de roteamento de ferramentas
=======
📂 Estrutura do Projeto (Arquivos Principais)
├── main.py           # Ponto de entrada da aplicação Streamlit
├── agent.py          # Orquestração do Agente e lógica do Grafo (LangGraph)
├── tools.py          # Definição e schemas das ferramentas de IA
├── settings.py       # Gerenciamento de chaves de API e configurações
├── chroma.py         # Integração com o banco de dados vetorial ChromaDB
├── embedding.py      # Lógica de processamento e vetorização de documentos
├── encode_image.py   # Helper para processamento e codificação de imagens
├── render.py         # Componentes visuais e renderização da interface
├── state.py          # Gerenciamento de estado da sessão do Streamlit
├── styles.py         # Definições de CSS e estilo visual (SharkDev Theme)
│
└── 🛠️ Ferramentas (Tools):
    ├── codes.py      # Lógica da ferramenta de Ajuda em Programação
    ├── general.py    # Lógica para Assuntos Gerais
    ├── news.py       # Integração com GNews e resumos de notícias
    ├── shark.py      # Lógica de suporte e onboarding SharkDev
    └── manager.py    # Gerenciador de chamadas e roteamento de ferramentas
