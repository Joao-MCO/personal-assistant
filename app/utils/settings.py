import os
import streamlit as st
from dotenv import load_dotenv

# Carrega o .env se estiver rodando localmente
load_dotenv()

def get_secret(key, default=None):
    """
    Tenta buscar a chave primeiro no Streamlit Secrets.
    Se falhar (ou não estiver no Streamlit), busca nas variáveis de ambiente (OS).
    """
    # 1. Tenta pegar do st.secrets (Nuvem)
    try:
        if key in st.secrets:
            return st.secrets[key]
    except (FileNotFoundError, AttributeError):
        pass  # Ignora se não houver arquivo de secrets ou não for app Streamlit
    
    # 2. Tenta pegar do ambiente local (.env / Docker)
    return os.getenv(key, default)

class Settings:
    # Agora usamos a função get_secret em vez de os.getenv direto
    
    gemini = {
        "api_key": get_secret("GEMINI_API_KEY"),
        "model": get_secret("GEMINI_MODEL", "gemini-1.5-flash"), # Adicionei um valor padrão por segurança
        "embedding": get_secret("GEMINI_EMBEDDING_MODEL")
    }

    maritaca = {
        "api_key": get_secret("MARITACA_API_KEY"),
        "model": get_secret("MARITACA_MODEL")
    }

    claude = {
        "api_key": get_secret("CLAUDE_API_KEY"),
        "model": get_secret("CLAUDE_MODEL")
    }

    openai = {
        "api_key": get_secret("OPENAI_API_KEY"),
        "model": get_secret("OPENAI_MODEL")
    }

    chroma = {
        "api_key": get_secret("CHROMA_API_KEY"),
        "tenant": get_secret("CHROMA_TENANT"),
        "database": get_secret("CHROMA_DATABASE"),
        "host": get_secret("CHROMA_HOST")
    }

    gnews_api_key = get_secret("GNEWS_API_KEY")
    max_tokens = get_secret("MAX_TOKENS")
    temperature = get_secret("TEMPERATURE")

    orchestrator = get_secret("ORCHESTRATOR_MODEL")