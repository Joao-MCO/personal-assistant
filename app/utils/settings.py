import os
import logging
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Optional

logger = logging.getLogger(__name__)

load_dotenv()
class SettingsConfig(BaseSettings):
    """Configurações da aplicação com validação Pydantic"""
    
    # ===========================
    # LLM MODELS & API KEYS
    # ===========================
    
    # Google Gemini (Recomendado)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"  # ✅ Modelo correto
    GEMINI_EMBEDDING_MODEL: str = "models/embedding-001"
    
    # Maritaca
    MARITACA_API_KEY: Optional[str] = None
    MARITACA_MODEL: str = "sabiazinho-4"
    
    # Anthropic Claude
    CLAUDE_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"  # ✅ Modelo correto
    
    # OpenAI GPT
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo"  # ✅ Modelo correto (gpt-5.1 não existe)
    
    # ===========================
    # RAG & VECTOR DATABASE
    # ===========================
    
    CHROMA_API_KEY: Optional[str] = None
    CHROMA_TENANT: Optional[str] = "default_tenant"
    CHROMA_DATABASE: Optional[str] = "default_database"
    CHROMA_HOST: Optional[str] = None

    # ===========================
    # GOOGLE SERVICES
    # ===========================
    
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    AUTH_COOKIE_SECRET: str = "change_me_in_production"
    AUTH_REDIRECT_URI: str = "http://localhost:8501"
    
    # ===========================
    # NEWS API
    # ===========================
    
    GNEWS_API_KEY: Optional[str] = None
    
    # ===========================
    # SECURITY & ENCRYPTION
    # ===========================
    
    ENCRYPTION_KEY: Optional[str] = None
    
    # ===========================
    # APP CONFIGURATION
    # ===========================
    
    ORCHESTRATOR_MODEL: str = "gemini"
    MAX_TOKENS: int = 8192
    TEMPERATURE: float = 0.4
    
    # ===========================
    # LOGGING
    # ===========================
    
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    class Config:
        """Configuração Pydantic"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignora variáveis extras no .env
        case_sensitive = False  # Case insensitive para variáveis


def load_settings() -> SettingsConfig:
    """
    Carrega configurações priorizando st.secrets para compatibilidade com Streamlit Cloud
    
    Ordem de prioridade:
    1. Streamlit Secrets (st.secrets) - Streamlit Cloud
    2. Variáveis de ambiente (.env) - Desenvolvimento local
    3. Valores padrão
    
    Returns:
        SettingsConfig: Instância com configurações carregadas
    """
    # 1. Carregar do .env primeiro via Pydantic
    settings = SettingsConfig()
    logger.debug("✅ Configurações carregadas de .env")
    
    # 2. Sobrescrever com st.secrets se disponível (Streamlit Cloud)
    try:
        import streamlit as st
        
        if hasattr(st, 'secrets') and st.secrets:
            logger.debug("Sobrescrevendo com st.secrets (Streamlit Cloud)")
            
            for field in settings.model_fields:
                # Procura case insensitive nos secrets
                for secret_key, secret_val in st.secrets.items():
                    if secret_key.upper() == field.upper():
                        if secret_val:  # Só sobrescrever se não vazio
                            setattr(settings, field, secret_val)
                            logger.debug(f"✅ {field} carregado de st.secrets")
                        break
    
    except (ImportError, FileNotFoundError, Exception) as e:
        # Streamlit não disponível ou secrets.toml não existe
        logger.debug(f"st.secrets não disponível: {e}")
    
    return settings


def validate_critical_settings(settings: SettingsConfig) -> bool:
    """
    Valida que configurações críticas estão presentes
    
    Args:
        settings: Instância de SettingsConfig
    
    Returns:
        bool: True se válido, False se não
    """
    critical_keys = [
        "GEMINI_API_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "ENCRYPTION_KEY"
    ]
    
    missing = [key for key in critical_keys if not getattr(settings, key, None)]
    
    if missing:
        logger.error(f"❌ Configurações críticas ausentes: {', '.join(missing)}")
        return False
    
    logger.info("✅ Todas as configurações críticas validadas")
    return True


# ============================================================================
# INSTÂNCIA SINGLETON
# ============================================================================

Settings = load_settings()


# ============================================================================
# WRAPPER PARA COMPATIBILIDADE COM CÓDIGO ANTIGO
# ============================================================================

class AppSettingsWrapper:
    """
    Wrapper para manter compatibilidade com código que acessa as configurações
    através de propriedades (ex: Settings.gemini, Settings.openai, etc)
    
    Exemplo:
        Settings.gemini['api_key']  # Retorna GEMINI_API_KEY
        Settings.openai['model']    # Retorna OPENAI_MODEL
    """
    
    @property
    def gemini(self) -> dict:
        """Configurações do Google Gemini"""
        return {
            "api_key": Settings.GEMINI_API_KEY,
            "model": Settings.GEMINI_MODEL,
            "embedding": Settings.GEMINI_EMBEDDING_MODEL
        }
    
    @property
    def maritaca(self) -> dict:
        """Configurações do Maritaca"""
        return {
            "api_key": Settings.MARITACA_API_KEY,
            "model": Settings.MARITACA_MODEL
        }
    
    @property
    def claude(self) -> dict:
        """Configurações do Anthropic Claude"""
        return {
            "api_key": Settings.CLAUDE_API_KEY,
            "model": Settings.CLAUDE_MODEL
        }
    
    @property
    def openai(self) -> dict:
        """Configurações do OpenAI"""
        return {
            "api_key": Settings.OPENAI_API_KEY,
            "model": Settings.OPENAI_MODEL
        }
    
    @property
    def chroma(self) -> dict:
        """Configurações do Chroma (Vector Database)"""
        return {
            "api_key": Settings.CHROMA_API_KEY,
            "tenant": Settings.CHROMA_TENANT,
            "database": Settings.CHROMA_DATABASE,
            "host": Settings.CHROMA_HOST
        }
    
    @property
    def redis(self) -> dict:
        """Configurações do Redis"""
        return {
            "host": Settings.REDIS_HOST,
            "port": Settings.REDIS_PORT,
            "db": Settings.REDIS_DB,
            "password": Settings.REDIS_PASSWORD
        }
    
    @property
    def google(self) -> dict:
        """Configurações do Google OAuth"""
        return {
            "client_id": Settings.GOOGLE_CLIENT_ID,
            "client_secret": Settings.GOOGLE_CLIENT_SECRET,
            "calendar_id": "primary"
        }
    
    @property
    def auth(self) -> dict:
        """Configurações de autenticação"""
        return {
            "secret": Settings.AUTH_COOKIE_SECRET,
            "cookie_name": "google_auth",
            "expiry_days": 7,
            "redirect_uri": Settings.AUTH_REDIRECT_URI,
            "client_id": Settings.GOOGLE_CLIENT_ID
        }
    
    @property
    def encryption(self) -> dict:
        """Configurações de criptografia"""
        return {
            "key": Settings.ENCRYPTION_KEY
        }
    
    @property
    def gnews_api_key(self) -> Optional[str]:
        """API Key do Google News"""
        return Settings.GNEWS_API_KEY
    
    @property
    def orchestrator(self) -> str:
        """Modelo LLM orquestrador padrão"""
        return Settings.ORCHESTRATOR_MODEL
    
    @property
    def llm_config(self) -> dict:
        """Configurações de LLM"""
        return {
            "max_tokens": Settings.MAX_TOKENS,
            "temperature": Settings.TEMPERATURE,
            "model": Settings.ORCHESTRATOR_MODEL
        }
    
    @property
    def logging_config(self) -> dict:
        """Configurações de logging"""
        return {
            "level": Settings.LOG_LEVEL,
            "file": Settings.LOG_FILE
        }


# Substituir a instância antiga pela Wrapper
WrappedSettings = AppSettingsWrapper()


# ============================================================================
# VALIDAÇÃO E LOGGING
# ============================================================================

if __name__ == "__main__":
    # Debug: Mostrar configurações (sem expor secrets)
    print("\n" + "="*70)
    print("CONFIGURAÇÕES CARREGADAS")
    print("="*70)
    
    config_info = {
        "Gemini": "✅" if Settings.GEMINI_API_KEY else "❌",
        "OpenAI": "✅" if Settings.OPENAI_API_KEY else "❌",
        "Claude": "✅" if Settings.CLAUDE_API_KEY else "❌",
        "Google OAuth": "✅" if Settings.GOOGLE_CLIENT_ID else "❌",
        "Encryption Key": "✅" if Settings.ENCRYPTION_KEY else "❌",
        "Redis": f"✅ ({Settings.REDIS_HOST}:{Settings.REDIS_PORT})",
        "Modelo Padrão": Settings.ORCHESTRATOR_MODEL,
    }
    
    for key, value in config_info.items():
        print(f"  {key:<20} {value}")
    
    print("="*70 + "\n")