import os
import streamlit as st
from pydantic_settings import BaseSettings
from typing import Optional

class SettingsConfig(BaseSettings):
    # Modelos e Keys
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3-flash-preview"
    GEMINI_EMBEDDING_MODEL: str = "models/embedding-001"
    
    MARITACA_API_KEY: Optional[str] = None
    MARITACA_MODEL: str = "sabiazinho-4"
    
    CLAUDE_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-4-5-haiku-20251001"
    
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-5.1"
    
    # RAG
    CHROMA_API_KEY: Optional[str] = None
    CHROMA_TENANT: Optional[str] = "default_tenant"
    CHROMA_DATABASE: Optional[str] = "default_database"
    CHROMA_HOST: Optional[str] = None

    # Google Auth & Tools
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    AUTH_COOKIE_SECRET: str = "change_me_in_production"
    AUTH_REDIRECT_URI: str = "http://localhost:8501"
    
    GNEWS_API_KEY: Optional[str] = None
    
    # App Config
    ORCHESTRATOR_MODEL: str = "gemini"
    MAX_TOKENS: int = 4000
    TEMPERATURE: float = 0.4

    class Config:
        env_file = ".env"
        extra = "ignore" # Ignora variaveis extras no .env

def load_settings():
    """Carrega configurações priorizando st.secrets para compatibilidade com Cloud"""
    # Tenta carregar do .env primeiro via Pydantic
    settings = SettingsConfig()
    
    # Sobrescreve com st.secrets se disponível (Streamlit Cloud)
    # Isso garante que funcione tanto local (.env) quanto cloud (Secrets)
    try:
        if st.secrets:
            for field in settings.model_fields:
                # Procura Case Insensitive nos secrets
                for secret_key, secret_val in st.secrets.items():
                    if secret_key.upper() == field.upper():
                        setattr(settings, field, secret_val)
    except FileNotFoundError:
        pass # Sem secrets.toml
        
    return settings

# Instância Singleton
Settings = load_settings()

# Propriedades de conveniência para manter compatibilidade com código antigo
class AppSettingsWrapper:
    @property
    def gemini(self): return {"api_key": Settings.GEMINI_API_KEY, "model": Settings.GEMINI_MODEL, "embedding": Settings.GEMINI_EMBEDDING_MODEL}
    @property
    def maritaca(self): return {"api_key": Settings.MARITACA_API_KEY, "model": Settings.MARITACA_MODEL}
    @property
    def claude(self): return {"api_key": Settings.CLAUDE_API_KEY, "model": Settings.CLAUDE_MODEL}
    @property
    def openai(self): return {"api_key": Settings.OPENAI_API_KEY, "model": Settings.OPENAI_MODEL}
    @property
    def chroma(self): return {"api_key": Settings.CHROMA_API_KEY, "tenant": Settings.CHROMA_TENANT, "database": Settings.CHROMA_DATABASE, "host": Settings.CHROMA_HOST}
    @property
    def google(self): return {"client_secret": Settings.GOOGLE_CLIENT_SECRET, "calendar_id": "primary"}
    @property
    def auth(self): return {"secret": Settings.AUTH_COOKIE_SECRET, "cookie_name": "google_auth", "expiry_days": 7, "redirect_uri": Settings.AUTH_REDIRECT_URI, "client_id": Settings.GOOGLE_CLIENT_ID}
    @property
    def gnews_api_key(self): return Settings.GNEWS_API_KEY
    @property
    def orchestrator(self): return Settings.ORCHESTRATOR_MODEL

# Substitui a instância antiga pela Wrapper
WrappedSettings = AppSettingsWrapper()