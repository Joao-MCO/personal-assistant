import datetime
import json
import base64
import operator
import streamlit as st
from typing import List, TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatMaritalk
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tools.google_tools import CheckCalendar, CreateEvent
from utils.settings import Settings
from tools.manager import agent_tools

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

class AgentFactory:
    def __init__(self, llm="gemini"):
        # 1. REMOVER as versões globais das ferramentas do Google
        global_tools = [t for t in agent_tools if t.name not in ["CriarEvento", "ConsultarAgenda"]]
        
        # 2. INSTANCIAR novas ferramentas exclusivas
        self.create_event_tool = CreateEvent()
        self.check_calendar_tool = CheckCalendar()
        self.session_tools = global_tools + [self.create_event_tool, self.check_calendar_tool]
        
        # Fallback de segurança para llm
        if not llm: llm = "gemini"
            
        # Configuração do Modelo
        if llm == "maritaca":
            self.llm = ChatMaritalk(
                api_key=Settings.maritaca["api_key"],
                model=Settings.maritaca["model"],
                temperature=0.7
            )
        elif llm == "claude":
            self.llm = ChatAnthropic(
                api_key=Settings.claude["api_key"],
                model=Settings.claude["model"],
                temperature=0.7
            )
        elif llm == "gpt":
            self.llm = ChatOpenAI(
                api_key=Settings.openai["api_key"],
                model=Settings.openai["model"],
                temperature=0.7
            )
        else:
            # Fallback para Gemini
            api_key = Settings.gemini.get("api_key")
            
            # --- BLINDAGEM & DEBUG ---
            if not api_key:
                st.error("🚨 **Erro Crítico:** A aplicação não conseguiu ler a API Key do Gemini.")
                
                # DIAGNÓSTICO: Mostra o que o Streamlit está vendo de verdade
                try:
                    keys_visiveis = list(st.secrets.keys())
                    st.warning(f"🔍 **Raio-X dos Secrets:** O Streamlit encontrou estas chaves salvas: {keys_visiveis}")
                    st.info("Verifique se 'GEMINI_API_KEY' está nesta lista exatamente como escrito (sem aspas extras no nome).")
                except Exception as e:
                    st.error(f"Não foi possível ler os secrets para debug: {e}")
                
                st.stop()
                
            self.llm = ChatGoogleGenerativeAI(
                api_key=api_key,
                model=Settings.gemini["model"],
                temperature=0.4 
            )

        self.llm_with_tools = self.llm.bind_tools(self.session_tools)
        self.tools = self.session_tools

        # 1. CARREGAR E-MAILS
        try:
            with open("app/assets/emails.json", "r", encoding="utf-8") as f:
                emails_list = json.load(f)
                emails_str = json.dumps(emails_list, ensure_ascii=False).replace("{", "{{").replace("}", "}}")
        except:
            emails_str = "[]"

        # 2. CONTEXTO TEMPORAL
        agora = datetime.datetime.now()
        data_hoje = agora.strftime("%d/%m/%Y")
        dia_semana = agora.strftime("%A") 
        hora_agora = agora.strftime("%H:%M")
        
        dias_pt = {
            "Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira",
            "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"
        }
        dia_hoje_pt = dias_pt.get(dia_semana, dia_semana)

        # 3. PROMPT
        template = f"""
            ### 🧠 PERFIL
            Você é a **Cidinha**, assistente virtual executiva da SharkDev.
            
            ### 📅 CONTEXTO TEMPORAL
            - **Hoje:** {dia_hoje_pt}, {data_hoje} ({hora_agora}).
            
            ### 📒 CONTATOS
            {emails_str}
            
            ### 🛠️ REGRAS DE SELEÇÃO DE FERRAMENTAS
            1. **Agenda/Reuniões:** Use `ConsultarAgenda` ou `CriarEvento`.
            2. **Notícias:** Use `LerNoticias`.
            3. **RPG/D&D:** Use `DuvidasRPG`.
            4. **Códigos:** Use `AjudaProgramacao`
            5. **TUDO O MAIS (Técnico ou Geral):** Use a ferramenta `AjudaShark`.
            6. **Papo Furado:** Se o usuário disser apenas "Oi", "Bom dia" ou "Obrigado", **NÃO** chame ferramentas. Responda diretamente.

            ### ⚙️ INSTRUÇÕES GERAIS
            - Se faltar email, procure na lista ou use o padrão `@sharkdev.com.br`.
            - Seja proativa e educada.
        """

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", template),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        self.graph = self._create_graph()
    
    def _create_graph(self):
        workflow = StateGraph(AgentState)
        
        def call_model(state: AgentState):
            messages = state["messages"]
            prompt_value = self.prompt.invoke({"messages": messages})
            response = self.llm_with_tools.invoke(prompt_value)
            return {"messages": [response]}
        
        tool_node = ToolNode(self.tools)
        
        def should_continue(state: AgentState):
            messages = state["messages"]
            last_message = messages[-1]
            if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
                return "continue"
            return "end"

        def after_tools(state: AgentState):
            messages = state["messages"]
            last_message = messages[-1]
            if isinstance(last_message, ToolMessage):
                if last_message.name in ["CriarEvento","ConsultarAgenda", "LerNoticias"]:
                    return "agent"
                
                if last_message.name in [ "RPGQuestion", "AjudaShark", "CodeHelper"]:
                     return "end"
            return "agent"
        
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue, {"continue": "tools", "end": END})
        workflow.add_conditional_edges("tools", after_tools, {"agent": "agent", "end": END})
        return workflow.compile()
    
    def _reconstruct_history(self, session_messages: List[dict]) -> List[BaseMessage]:
        history = []
        for msg in session_messages:
            if not isinstance(msg, dict): continue
            role = msg.get("role")
            content = msg.get("content")
            if not content: continue
            if role == "user": history.append(HumanMessage(content=str(content)))
            elif role == "assistant": history.append(AIMessage(content=str(content)))
        return history

    def invoke(self, input_text: str, session_messages: List[dict], uploaded_files: List[dict] = None, user_credentials=None):
        history_objects = self._reconstruct_history(session_messages)
        current_content = []
        if input_text: current_content.append({"type": "text", "text": input_text})
            
        if uploaded_files:
            for file in uploaded_files:
                try:
                    mime = file['mime']
                    if mime.startswith('image/'):
                        encoded = base64.b64encode(file['data']).decode('utf-8')
                        current_content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}})
                    else:
                        text = file['data'].decode('utf-8', errors='ignore')
                        current_content.append({"type": "text", "text": f"\n[Anexo]: {text}"})
                except: pass
        
        if not current_content: current_content.append({"type": "text", "text": "..."})
        
        if user_credentials:
            self.create_event_tool.set_credentials(user_credentials)
            self.check_calendar_tool.set_credentials(user_credentials)
        
        try:
            inputs = {"messages": history_objects + [HumanMessage(content=current_content)]}
            result = self.graph.invoke(inputs)
            last_message = result["messages"][-1]
            content = last_message.content
        except Exception as e:
            return {"output": [{"role": "assistant", "content": f"Erro interno no Agente: {str(e)}"}]}

        if not content:
            if hasattr(last_message, "tool_calls") and last_message.tool_calls: content = "Estou processando..."
            elif isinstance(last_message, ToolMessage): content = last_message.content

        if isinstance(content, list):
            parts = [c.get("text", "") for c in content if isinstance(c, dict)]
            content = " ".join(parts)
            
        return {"output": [{"role": "assistant", "content": str(content)}]}