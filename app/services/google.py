import streamlit as st
from utils.settings import Settings, logger
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import logging

def get_service():
    creds = None
    scopes = ["https://www.googleapis.com/auth/calendar"]

    # 1. Tenta carregar o token DOS SECRETS (Prioridade na Nuvem)
    # O Settings.google["token"] já deve estar pegando o JSON do secret GOOGLE_TOKEN_JSON
    token_json = Settings.google.get("token")
    
    if token_json:
        try:
            creds = Credentials.from_authorized_user_info(token_json, scopes)
            logger.info("Credenciais carregadas dos Secrets.")
        except Exception as e:
            logger.error(f"Erro ao carregar token dos Secrets: {e}")

    # 2. Validação e Renovação Automática (O Segredo do sucesso)
    # Se carregou as credenciais, mas elas expiraram...
    if creds and creds.expired and creds.refresh_token:
        try:
            logger.info("Token expirado. Tentando renovar via Refresh Token...")
            # Isso renova o token NA MEMÓRIA usando o refresh_token que está salvo
            creds.refresh(Request())
            logger.info("Token renovado com sucesso!")
        except Exception as e:
            logger.error(f"Falha ao renovar token: {e}")
            # Se falhar a renovação, anulamos para não tentar usar token podre
            creds = None

    # 3. Retorno
    if not creds or not creds.valid:
        logger.error("Não foi possível obter credenciais válidas.")
        return None

    return build("calendar", "v3", credentials=creds)