import streamlit as st
from ui.styles import apply_custom_styles
from ui.render import render_header, render_chat_history, render_upload_warning
from ui.state import init_session_state

def main():
    # 1. Configuração da Página
    st.set_page_config(page_title="Cidinha - SharkDev", page_icon="🦈", layout="centered")
    
    # 2. Carrega CSS e Estado
    apply_custom_styles()
    init_session_state()
    
    # 3. Renderiza Interface Fixa
    render_header()
    render_chat_history()

    # 4. Função de bloqueio de input
    def lock_input():
        st.session_state.processing = True

    # 5. Componentes de Input (Upload + Chat)
    with st.popover("📎", help="Anexar Arquivos"):
        st.markdown("### Anexar Documentos")
        uploaded_files = st.file_uploader(
            "Upload", 
            accept_multiple_files=True,
            label_visibility="collapsed",
            key=f"uploader_{st.session_state['uploader_key']}" 
        )

    # Input de texto
    user_text = st.chat_input(
        "Como posso ajudar a SharkDev hoje?", 
        disabled=st.session_state.processing,
        on_submit=lock_input,
        key="user_input_widget"
    )

    # Aviso flutuante se houver arquivos mas ainda não enviou
    if uploaded_files and not st.session_state.processing:
        render_upload_warning(len(uploaded_files))

    # --- LÓGICA DE PROCESSAMENTO E ENVIO ---
    if st.session_state.processing:
        # Se usuário digitou algo ou apenas anexou (tratamento de input vazio pode ser adicionado se desejar)
        if user_text:
            display_text = user_text
            msg_images = []    
            files_to_send = [] 
            
            # Processamento de arquivos
            if uploaded_files:
                file_names = []
                for f in uploaded_files:
                    file_names.append(f.name)
                    bytes_data = f.getvalue()
                    
                    files_to_send.append({
                        "data": bytes_data,
                        "mime": f.type
                    })

                    if f.type.startswith("image/"):
                        msg_images.append(bytes_data)
                
                display_text += f"\n\n*(📎 Anexos: {', '.join(file_names)})*"

            # Atualiza histórico com mensagem do usuário
            st.session_state['messages'].append({
                "role": "user", 
                "content": display_text,
                "images": msg_images 
            })
            
            # Renderiza a mensagem do usuário imediatamente para feedback visual
            with st.chat_message("user", avatar="🤓"):
                st.markdown(display_text)
                if msg_images:
                    for img_data in msg_images:
                        st.image(img_data, use_container_width=True)

            # Chama o Agente
            with st.spinner("A Pamela não vai gostar nada dessa demora..."):
                try:
                    response = st.session_state.factory.invoke(
                        input_text=user_text, 
                        session_messages=st.session_state['messages'],
                        uploaded_files=files_to_send 
                    )
                    
                    outputs = response.get('output', [])
                    if isinstance(outputs, str): outputs = [{"role": "assistant", "content": outputs}]
                    
                    for resp in outputs:
                        st.session_state['messages'].append(resp)
                        with st.chat_message(resp["role"], avatar="🦈"):
                            st.markdown(resp["content"])
                            
                except Exception as e:
                    st.error(f"Erro: {e}")
            
            # Limpa o uploader incrementando a chave
            st.session_state['uploader_key'] += 1
            
            st.session_state.processing = False
            st.rerun()
        else:
            # Caso tenha entrado em processing sem texto (apenas enter vazio)
            st.session_state.processing = False
            st.rerun()

if __name__ == "__main__":
    main()