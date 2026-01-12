import json
import logging
import os
import streamlit as st
from dotenv import load_dotenv

# Carrega o .env se estiver rodando localmente
load_dotenv()

logger = logging.getLogger(__name__)

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
        pass
    
    # 2. Tenta pegar do ambiente local (.env / Docker)
    return os.getenv(key, default)

def get_json_secret(key, default=None):
    """
    Carrega segredos JSON de forma robusta, aceitando String ou Dict.
    """
    data = get_secret(key)
    
    # 1. Se não encontrou nada
    if data is None:
        return default

    # 2. Se já for um dicionário (O Streamlit parseou o TOML automaticamente)
    if isinstance(data, dict):
        return data

    # 3. Se for string, tenta fazer o parse do JSON
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            print(f"Erro: A chave {key} tem uma string que não é um JSON válido.")
            return default
            
    return default

# --- NOVA FUNÇÃO PARA LER CREDENCIAIS ---
def get_google_credentials():
    """
    Busca credenciais OAuth no .env ou no arquivo credentials.json local.
    """
    # 1. Tenta pegar da variável de ambiente (Deploy/Cloud)
    json_str = get_secret("GOOGLE_API_JSON")
    if json_str:
        try:
            return json.loads(json_str)
        except Exception as e:
            print(f"Erro ao ler GOOGLE_API_JSON do env: {e}")
    
    # 2. Se não achou ou falhou, tenta ler o arquivo local (Desenvolvimento)
    if os.path.exists("credentials.json"):
        try:
            with open("credentials.json", "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao ler credentials.json: {e}")
            
    return {} # Retorna vazio se falhar tudo

class Settings:
    
    gemini = {
        "api_key": get_secret("GEMINI_API_KEY"),
        "model": get_secret("GEMINI_MODEL", "gemini-1.5-flash"), 
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

    # --- GOOGLE CONFIG ATUALIZADA ---
    google = {
        # Usa a nova função que lê o arquivo credentials.json automaticamente
        "auth": get_google_credentials(),
        
        "token": get_json_secret("GOOGLE_TOKEN_JSON", None),
        
        "calendar_id": get_secret("CALENDAR_ID", "primary"),
        "scopes": ["https://www.googleapis.com/auth/calendar"]
    }

    working_days = {
        "Monday": {"start": "8:00", "end": "18:00"},
        "Tuesday": {"start": "8:00", "end": "18:00"},
        "Wednesday": {"start": "8:00", "end": "18:00"},
        "Thursday": {"start": "8:00", "end": "18:00"},
        "Friday": {"start": "8:00", "end": "17:00"}
    }

    gnews_api_key = get_secret("GNEWS_API_KEY")
    max_tokens = get_secret("MAX_TOKENS")
    temperature = get_secret("TEMPERATURE")
    orchestrator = get_secret("ORCHESTRATOR_MODEL")