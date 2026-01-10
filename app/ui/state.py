import streamlit as st
from agent.agent import AgentFactory

def init_session_state():
    """Inicializa as variáveis de estado da sessão"""
    if 'factory' not in st.session_state:
        # Assumindo que AgentFactory usa 'gemini' por padrão conforme seu código original
        st.session_state.factory = AgentFactory(llm="gemini")
        
    if 'messages' not in st.session_state:
        st.session_state['messages'] = []
        
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    
    if 'uploader_key' not in st.session_state:
        st.session_state['uploader_key'] = 0