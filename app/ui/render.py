import streamlit as st
import os

def render_header():
    """Renderiza o logo e o título da Cidinha"""
    # Define caminhos baseados na localização atual
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Sobe um nível para 'app'
    assets_dir = os.path.join(base_dir, "assets")
    img_cidinha = os.path.join(assets_dir, "cidinha.png")
    img_logo = os.path.join(assets_dir, "logo_shark.png")

    with st.container():
        if os.path.exists(img_logo):
            st.image(img_logo, use_container_width=True)
            st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.markdown("<h1 style='text-align:center; color: #F551B1; border: 2px solid #F551B1;'>LOGO SHARKDEV</h1>", unsafe_allow_html=True)

        col1, col2 = st.columns([1.2, 5])
        with col1:
            if os.path.exists(img_cidinha):
                st.image(img_cidinha, use_container_width=True)
            else:
                st.markdown("🦈") 
        with col2:
            st.markdown('<div class="cidinha-title">Cidinha</div>', unsafe_allow_html=True)
            st.markdown('<div class="cidinha-subtitle">A Secretária da SharkDev</div>', unsafe_allow_html=True)
            
    st.markdown("""<hr style="height:2px;border:none;color:#F551B1;background-color:#F551B1;margin-bottom:20px;" /> """, unsafe_allow_html=True)

def render_chat_history():
    """Renderiza mensagens e imagens do histórico"""
    if 'messages' not in st.session_state:
        return

    for message in st.session_state['messages']:
        role = message.get("role", "assistant")
        content = message.get("content", "")
        images = message.get("images", []) 
        
        avatar = "🦈" if role == "assistant" else "🤓"
        
        with st.chat_message(role, avatar=avatar):
            st.markdown(content)
            
            if images:
                for img_data in images:
                    st.image(img_data, use_container_width=True)

def render_upload_warning(file_count):
    """Mostra o aviso flutuante de arquivos anexados"""
    st.markdown(
        f"""<div style="position:fixed; bottom: 90px; left:50%; transform:translateX(-360px); 
        color:#F551B1; font-size:0.7em; background:#000; padding:2px 5px; border-radius:5px; border:1px solid #333;">
        📎 {file_count} anexo(s)
        </div>""", 
        unsafe_allow_html=True
    )