import streamlit as st
from agent.agent import AgentFactory
from utils.settings import Settings

def init_session_state():
    """Inicializa as variáveis de estado da sessão"""
    if 'factory' not in st.session_state:
        # CORREÇÃO: Usa "gemini" se Settings.orchestrator for None ou vazio
        model_to_use = Settings.orchestrator or "gemini"
        st.session_state.factory = AgentFactory(llm=model_to_use)
        
    if 'messages' not in st.session_state:
        st.session_state['messages'] = []
        
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    
    if 'uploader_key' not in st.session_state:
        st.session_state['uploader_key'] = 0

    if 'user' not in st.session_state:
        st.session_state['user'] = "Usuário"