import logging
import os
import requests
import streamlit as st

# Configurações para evitar erro de escopo e transporte local
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' 

from streamlit_google_auth import Authenticate
from ui.styles import apply_custom_styles
from ui.render import render_header, render_chat_history, render_upload_warning
from ui.state import init_session_state
from utils.settings import Settings

# Configuração de Logger - Limpa ruídos do terminal
logging.basicConfig(level=logging.INFO)
logging.getLogger('google_auth_oauthlib').setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

def setup_authentication():
    """
    Configura o fluxo de login OAuth e gerencia a persistência do estado de forma segura.
    """
    credentials_path = "client_secret.json"
    secret_value = Settings.google.get('client_secret')

    # 1. Garante que o arquivo client_secret.json existe
    if secret_value and isinstance(secret_value, str) and secret_value.strip().startswith("{"):
        try:
            with open(credentials_path, "w") as f:
                f.write(secret_value)
        except Exception as e:
            st.error(f"Erro ao criar credenciais temporárias: {e}")
            st.stop()
    elif not os.path.exists(credentials_path):
        st.error("❌ Arquivo 'client_secret.json' não encontrado!")
        st.stop()

    # 2. Inicializa o Authenticator
    authenticator = Authenticate(
        secret_credentials_path=credentials_path,
        cookie_name=Settings.auth['cookie_name'],
        cookie_key=Settings.auth['secret'],
        redirect_uri="https://cidinha-shark.streamlit.app", 
    )
    
    # 3. Verifica o callback do Google e Cookies
    authenticator.check_authentification()
    
    # 4. Sincronização Segura de Estado
    creds = getattr(authenticator, 'credentials', None)
    
    if creds and creds.valid:
        st.session_state['connected'] = True
        st.session_state['auth'] = authenticator
        
        # Se não tiver dados do usuário, busca agora
        if 'user_info' not in st.session_state:
            try:
                token = creds.token
                headers = {"Authorization": f"Bearer {token}"}
                res = requests.get("https://www.googleapis.com/oauth2/v1/userinfo?alt=json", headers=headers)
                
                if res.status_code == 200:
                    user_data = res.json()
                    st.session_state['user_info'] = user_data
                    st.session_state['user_email'] = user_data.get('email')
                    st.rerun()
            except Exception as e:
                logger.error(f"Erro ao buscar dados do usuário: {e}")
    else:
        # CORREÇÃO CRÍTICA: Se não tem credenciais válidas, força estado desconectado.
        # Isso evita que o app tente acessar a agenda com credenciais nulas.
        if st.session_state.get('connected'):
            st.session_state['connected'] = False
            st.session_state['user_info'] = None
            st.rerun()
    
    st.session_state['auth'] = authenticator
    return authenticator

def main():
    st.set_page_config(page_title="Cidinha - SharkDev", page_icon="🦈", layout="centered")
    apply_custom_styles()
    init_session_state()

    auth = setup_authentication()
    
    with st.sidebar:
        try:
            st.image("app/assets/logo_shark.png", width=150)
        except:
            st.markdown("### 🦈 SharkDev")
            
        st.markdown("### Acesso")
        
        if not st.session_state.get('connected', False):
            auth.login() 
            st.warning("Faça login para usar a Agenda.")
        else:
            user_info = st.session_state.get('user_info', {})
            user_name = user_info.get('name', 'Usuário')
            
            st.success(f"Olá, **{user_name}**!")
            
            if st.button("Sair"):
                auth.logout()
                st.session_state['connected'] = False
                st.session_state['user_info'] = None
                st.rerun()

    render_header()
    render_chat_history()

    def lock_input():
        st.session_state.processing = True

    with st.popover("📎"):
        st.markdown("### Anexar Documentos")
        uploaded_files = st.file_uploader(
            "Upload", 
            accept_multiple_files=True,
            label_visibility="collapsed",
            key=f"uploader_{st.session_state['uploader_key']}" 
        )

    user_text = st.chat_input(
        "Como posso ajudar a SharkDev hoje?", 
        disabled=st.session_state.processing,
        on_submit=lock_input,
        key="user_input_widget"
    )
    
    if uploaded_files and not st.session_state.processing:
        render_upload_warning(len(uploaded_files))

    if st.session_state.processing:
        if user_text or uploaded_files: 
            display_text = user_text if user_text else ""
            msg_images = []    
            files_to_send = [] 
            
            if uploaded_files:
                file_names = [f.name for f in uploaded_files]
                for f in uploaded_files:
                    files_to_send.append({"data": f.getvalue(), "mime": f.type})
                    if f.type.startswith("image/"):
                        msg_images.append(f.getvalue())
                
                anexo_str = f"\n\n*(📎 Anexos: {', '.join(file_names)})*"
                display_text += anexo_str

            st.session_state['messages'].append({
                "role": "user", 
                "content": display_text,
                "images": msg_images 
            })
            
            with st.chat_message("user", avatar="🤓"):
                st.markdown(display_text)
                if msg_images:
                    for img in msg_images: st.image(img, width='stretch')

            with st.spinner("A Pamela não vai gostar nada disso..."):
                try:
                    # 1. Recupera credenciais da sessão
                    user_creds = None
                    if st.session_state.get('connected'):
                        auth_obj = st.session_state.get('auth')
                        user_creds = getattr(auth_obj, 'credentials', None)

                    # 2. Passa para o agente via 'user_credentials'
                    response = st.session_state.factory.invoke(
                        input_text=user_text or "Processar anexos", 
                        session_messages=st.session_state['messages'],
                        uploaded_files=files_to_send,
                        user_credentials=user_creds 
                    )
                    
                    outputs = response.get('output', [])
                    
                    if isinstance(outputs, str): outputs = [{"role": "assistant", "content": outputs}]
                    
                    for resp in outputs:
                        st.session_state['messages'].append(resp)
                        with st.chat_message(resp["role"], avatar="🦈"):
                            st.markdown(resp["content"])
                            
                except Exception as e:
                    st.error(f"Erro: {e}")
            
            st.session_state['uploader_key'] += 1
            st.session_state.processing = False
            st.rerun()
        else:
            st.session_state.processing = False
            st.rerun()

if __name__ == "__main__":
    main()