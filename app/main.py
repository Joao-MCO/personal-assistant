import logging
import os
import json
import requests
import streamlit as st
import google.oauth2.credentials
from google_auth_oauthlib.flow import Flow
from ui.styles import apply_custom_styles
from ui.render import render_header, render_chat_history, render_upload_warning
from ui.state import init_session_state
from utils.settings import Settings

# Configurações para ambiente de desenvolvimento/cloud
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

# Configuração de Logger
logging.basicConfig(level=logging.INFO)
logging.getLogger('google_auth_oauthlib').setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

class MemoryGoogleAuth:
    """
    Gerencia autenticação OAuth2 usando dicionários em memória.
    """
    def __init__(self, client_config, redirect_uri):
        self.client_config = client_config
        self.redirect_uri = redirect_uri
        self.SCOPES = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid"
        ]
        
    def get_flow(self):
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri,
        )

        # DESATIVA PKCE (OBRIGATÓRIO NO STREAMLIT)
        flow._oauth2session._client.code_challenge_method = None

        return flow


    def login(self):
        flow = self.get_flow()
        auth_url, state = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )

        st.session_state["oauth_state"] = state
        st.link_button("Conectar Google Calendar", auth_url)

    def check_authentication(self):
        code = st.query_params.get("code")
        state = st.query_params.get("state")

        if not code:
            return

        if isinstance(code, list):
            code = code[0]
        if isinstance(state, list):
            state = state[0]

        if state != st.session_state.get("oauth_state"):
            st.warning("Estado OAuth inválido")
            return

        try:
            flow = self.get_flow()
            flow.fetch_token(code=code)

            creds = flow.credentials

            st.session_state["google_creds"] = {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes,
            }

            st.session_state["connected"] = True
            st.query_params.clear()
            st.rerun()

        except Exception:
            logger.exception("Erro OAuth")
            st.warning("Falha na autenticação")



    def logout(self):
        """Limpa a sessão."""
        if 'google_creds' in st.session_state:
            del st.session_state['google_creds']
        st.session_state['connected'] = False
        st.session_state['user_info'] = None

    @property
    def credentials(self):
        """Reconstrói o objeto Credentials a partir da sessão."""
        creds_data = st.session_state.get('google_creds')
        if not creds_data:
            return None
        return google.oauth2.credentials.Credentials(**creds_data)


def setup_authentication():
    """Configura a autenticação usando Settings (Env Vars) e a classe em memória."""
    client_secret_data = Settings.google.get('client_secret')
    
    if not client_secret_data:
        st.error("❌ Erro de Configuração: Variável 'client_secret' não encontrada.")
        st.stop()
        
    if isinstance(client_secret_data, str):
        try:
            client_config = json.loads(client_secret_data)
        except json.JSONDecodeError:
            st.error("❌ Erro: O conteúdo de 'client_secret' não é um JSON válido.")
            st.stop()
    else:
        client_config = client_secret_data

    # Inicializa o Autenticador
    auth = MemoryGoogleAuth(
        client_config=client_config,
        redirect_uri=Settings.auth["redirect_uri"] 
    )
    
    # Verifica callback do login
    auth.check_authentication()
    
    # Recupera credenciais para validar usuário
    creds = auth.credentials
    
    if creds and creds.valid:
        st.session_state['connected'] = True
        
        if 'user_info' not in st.session_state:
            try:
                headers = {"Authorization": f"Bearer {creds.token}"}
                res = requests.get("https://www.googleapis.com/oauth2/v1/userinfo?alt=json", headers=headers)
                
                if res.status_code == 200:
                    user_data = res.json()
                    st.session_state['user_info'] = user_data
                    st.session_state['user_email'] = user_data.get('email')
                    st.rerun()
            except Exception as e:
                logger.error(f"Erro ao buscar user info: {e}")
    
    return auth

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
                    user_creds = auth.credentials

                    if st.session_state.get('connected') and not user_creds:
                        logger.warning("UI diz conectado, mas credenciais estão vazias.")

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