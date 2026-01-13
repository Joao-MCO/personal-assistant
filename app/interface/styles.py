import streamlit as st

def apply_custom_styles():
    st.markdown("""
        <style>
        /* 1. Fundo Preto Absoluto */
        .stApp {
            background-color: #000000;
            color: #ffffff;
        }

        /* 2. Barra Lateral */
        [data-testid="stSidebar"] {
            background-color: #050505;
            border-right: 1px solid #1f1f1f;
        }
        
        .block-container {
            padding-top: 2rem;
            padding-bottom: 150px; 
        }

        /* 3. Títulos e Imagens */
        .cidinha-title {
            color: #F551B1 !important;
            font-family: 'Helvetica Neue', sans-serif;
            font-weight: 800;
            font-size: 3rem;
            margin-bottom: 0px;
            line-height: 1.0;
        }
        .cidinha-subtitle {
            color: #eeeeee;
            font-weight: 400;
            font-size: 1.1rem;
            margin-top: 5px;
        }
        div[data-testid="column"]:nth-of-type(1) img {
            border-radius: 50%;
            border: 3px solid #F551B1;
            object-fit: cover;
        }

       /* --- 4. CONFIGURAÇÃO DOS BALÕES (FORMATO PÍLULA) --- */
        
        /* Geral (Assistente e Usuário) */
        .stChatMessage {
            background-color: #111111;
            border: 2px solid #F551B1;
            border-radius: 50px; 
            padding: 1rem 1.5rem;
        }

        /* Específico do Usuário */
        div[data-testid="stChatMessageUser"] {
            background-color: #1a1a1a !important;
            border: 2px solid #F551B1 !important;
            box-shadow: 0px 0px 15px rgba(245, 81, 177, 0.2); 
        }

        /* --- 5. CORREÇÃO DO POPOVER (CLIPE) --- */
        div[data-testid="stPopover"] {
            position: fixed;
            bottom: 3.5rem; 
            z-index: 10000;
            left: 50%;
            transform: translateX(-370px);
            width: 40px !important; 
            height: 40px !important;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        div[data-testid="stPopover"] > button {
            background-color: transparent !important;
            color: #F551B1 !important;
            border: none !important;
            font-size: 1.5rem !important; 
            padding: 0px !important;
            margin: 0px !important;
            width: 100% !important;
            height: 100% !important;
            box-shadow: none !important;
            border-radius: 50% !important;
        }
        
        div[data-testid="stPopover"] button:hover {
            color: #ff8ecf !important;
        }

        /* --- 6. AJUSTE DO INPUT DE TEXTO --- */
        .stChatInput textarea {
            padding-left: 3.5rem !important; 
            color: white;
            background-color: #1a1a1a;
            border: 1px solid #333;
            border-radius: 50px; 
        }
        
        #MainMenu, footer, header {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)