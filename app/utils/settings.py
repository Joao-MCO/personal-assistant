import json
import logging
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

def get_secret(key, default=None):
    """Busca o segredo de forma robusta e Case-Insensitive"""
    # 1. Tenta busca direta
    try:
        if key in st.secrets:
            return st.secrets[key]
    except:
        pass

    # 2. Tenta busca varrendo as chaves (para evitar problemas de maiúsculas/minúsculas)
    try:
        key_lower = key.lower()
        for k, v in st.secrets.items():
            if k.lower() == key_lower:
                return v
    except:
        pass
        
    # 3. Tenta do ambiente
    return os.getenv(key, default)

class AppSettings:
    """
    Classe dinâmica que busca as configurações sempre que são acessadas.
    Isso evita problemas de cache onde a chave aparece como None porque
    foi lida antes de estar disponível.
    """
    
    @property
    def gemini(self):
        return {
            "api_key": get_secret("GEMINI_API_KEY") or get_secret("GOOGLE_API_KEY"),
            "model": get_secret("GEMINI_MODEL", "gemini-1.5-flash"), 
            "embedding": get_secret("GEMINI_EMBEDDING_MODEL")
        }

    @property
    def maritaca(self):
        return {
            "api_key": get_secret("MARITACA_API_KEY"),
            "model": get_secret("MARITACA_MODEL")
        }

    @property
    def claude(self):
        return {
            "api_key": get_secret("CLAUDE_API_KEY"),
            "model": get_secret("CLAUDE_MODEL")
        }

    @property
    def openai(self):
        return {
            "api_key": get_secret("OPENAI_API_KEY"),
            "model": get_secret("OPENAI_MODEL")
        }

    @property
    def chroma(self):
        return {
            "api_key": get_secret("CHROMA_API_KEY"),
            "tenant": get_secret("CHROMA_TENANT"),
            "database": get_secret("CHROMA_DATABASE"),
            "host": get_secret("CHROMA_HOST")
        }

    @property
    def google(self):
        # Tenta recuperar o JSON de credenciais de várias formas
        secret_json = get_secret("GOOGLE_CLIENT_SECRET") or get_secret("client_secret") or "client_secret.json"
        return {
            "client_secret": secret_json,
            "calendar_id": "primary"
        }

    @property
    def auth(self):
        return {
            "secret": get_secret("AUTH_COOKIE_SECRET", "chave_secreta_padrao_segura"),
            "cookie_name": "google_auth_cookie",
            "expiry_days": 7,
            "redirect_uri": get_secret("AUTH_REDIRECT_URI", "https://cidinha-shark.streamlit.app"),
            "client_id": get_secret("GOOGLE_CLIENT_ID")
            # "client_secret": get_secret("GOOGLE_CLIENT_SECRET")
        }

    @property
    def working_days(self):
        return {
            "Monday": {"start": "8:00", "end": "18:00"},
            "Tuesday": {"start": "8:00", "end": "18:00"},
            "Wednesday": {"start": "8:00", "end": "18:00"},
            "Thursday": {"start": "8:00", "end": "18:00"},
            "Friday": {"start": "8:00", "end": "17:00"}
        }

    @property
    def gnews_api_key(self):
        return get_secret("GNEWS_API_KEY")

    @property
    def max_tokens(self):
        return get_secret("MAX_TOKENS")

    @property
    def temperature(self):
        return get_secret("TEMPERATURE")

    @property
    def orchestrator(self):
        return get_secret("ORCHESTRATOR_MODEL")

# Instância global que substitui a classe estática antiga
Settings = AppSettings()