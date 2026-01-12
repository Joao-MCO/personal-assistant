import os
import streamlit as st
from utils.settings import Settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

def get_service():
    creds = None
    scopes = Settings.google["scopes"]

    # ---------------------------------------------------------
    # ESTRATÉGIA 1: Tentar carregar das Secrets/Env (Nuvem)
    # ---------------------------------------------------------
    if Settings.google["token"]:
        try:
            creds = Credentials.from_authorized_user_info(Settings.google["token"], scopes)
        except Exception as e:
            print(f"Erro ao ler token das configurações: {e}")

    # ---------------------------------------------------------
    # ESTRATÉGIA 2: Tentar carregar arquivo local (Cache Local)
    # ---------------------------------------------------------
    if not creds and os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', scopes)
        except Exception as e:
            print(f"Erro ao ler token.json: {e}")

    # ---------------------------------------------------------
    # Validação e Renovação
    # ---------------------------------------------------------
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Erro ao renovar token: {e}")
                creds = None # Força novo login se falhar renovação

        # Se ainda não temos credenciais válidas...
        if not creds:
            # Se estiver no Streamlit Cloud, não podemos abrir browser -> ERRO
            if hasattr(st, "runtime") and st.runtime.exists():
                st.error("❌ ERRO DE AUTENTICAÇÃO NO CLOUD")
                st.warning("Você precisa gerar o token localmente e colocá-lo nas Secrets como 'GOOGLE_TOKEN_JSON'.")
                return None
            
            # Se for local, abre o navegador para login
            else:
                print("Iniciando fluxo de login no navegador...")
                flow = InstalledAppFlow.from_client_config(
                    client_config=Settings.google["auth"],
                    scopes=scopes
                )
                creds = flow.run_local_server(port=0)
                
                # Salva o token para a próxima vez (Cache Local)
                print("Login realizado! Salvando 'token.json'...")
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)