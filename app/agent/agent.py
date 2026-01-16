import datetime
import operator
import streamlit as st
from typing import TypedDict, Annotated, Sequence, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatMaritalk
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from utils.files import get_emails
from utils.settings import WrappedSettings as Settings
from prompts.templates import AGENT_SYSTEM_PROMPT
from tools.manager import agent_tools
from tools.google_tools import CheckCalendar, CheckEmail, CreateEvent, SendEmail

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

class AgentFactory:
    def __init__(self, llm="gemini"):
        # 1. Ferramentas que precisam de credenciais do usuário (Runtime)
        # Estas são instanciadas aqui para receberem as credenciais da sessão atual
        self.create_event_tool = CreateEvent()
        self.check_calendar_tool = CheckCalendar()
        self.check_email_tool = CheckEmail()
        self.send_email_tool = SendEmail()
        
        # 2. Ferramentas Globais (Manager) + Ferramentas de Sessão
        # Filtramos do manager as tools que estamos criando manualmente acima para evitar duplicidade
        global_tools = [t for t in agent_tools if t.name not in ["CriarEvento", "ConsultarAgenda", "ConsultarEmail", "EnviarEmail"]]
        
        self.tools = global_tools + [
            self.create_event_tool, 
            self.check_calendar_tool, 
            self.check_email_tool, 
            self.send_email_tool
        ]

        # 3. Seleção e Configuração do Modelo (LLM)
        self.llm = self._get_llm_instance(llm)
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # 4. Contexto Temporal e Dinâmico
        emails_str = get_emails(True)
        agora = datetime.datetime.now()
        dias_pt = {
            "Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira",
            "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"
        }
        
        # Formatação do System Prompt com dados atuais
        formatted_system_prompt = AGENT_SYSTEM_PROMPT.format(
            dia_hoje_pt=dias_pt.get(agora.strftime("%A"), ""),
            data_hoje=agora.strftime("%d/%m/%Y"),
            hora_agora=agora.strftime("%H:%M"),
            emails_str=emails_str
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", formatted_system_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        # 5. Criação do Grafo (LangGraph)
        self.graph = self._create_graph()

    def _get_llm_instance(self, model_name):
        """Centraliza a lógica de instanciação da LLM com tratamento de erros."""
        try:
            if model_name == "maritaca":
                return ChatMaritalk(
                    api_key=Settings.maritaca["api_key"], 
                    model=Settings.maritaca["model"],
                    temperature=0.7
                )
            elif model_name == "claude":
                return ChatAnthropic(
                    api_key=Settings.claude["api_key"], 
                    model=Settings.claude["model"],
                    temperature=0.7
                )
            elif model_name == "gpt":
                return ChatOpenAI(
                    api_key=Settings.openai["api_key"], 
                    model=Settings.openai["model"],
                    temperature=0.7
                )
            else:
                # Fallback padrão: Google Gemini
                if not Settings.gemini.get("api_key"):
                    st.error("🚨 Erro Crítico: API Key do Gemini não encontrada.")
                    st.stop()
                    
                return ChatGoogleGenerativeAI(
                    api_key=Settings.gemini["api_key"], 
                    model=Settings.gemini["model"], 
                    temperature=0.4
                )
        except Exception as e:
            st.error(f"Erro ao iniciar LLM ({model_name}): {e}")
            st.stop()

    def _create_graph(self):
        workflow = StateGraph(AgentState)
        
        # Nó do Agente (LLM)
        def call_model(state: AgentState):
            messages = state["messages"]
            chain = self.prompt | self.llm_with_tools
            response = chain.invoke({"messages": messages})
            return {"messages": [response]}
        
        # Lógica de Decisão (Router)
        def router_logic(state: AgentState):
            messages = state["messages"]
            last_message = messages[-1]
            
            # Se a LLM não chamou nenhuma ferramenta, encerra o ciclo
            if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
                return "end"
            
            # Se chamou ferramenta, continua para o nó de tools
            return "continue"

        # Lógica Pós-Ferramenta
        def after_tools_router(state: AgentState):
            messages = state["messages"]
            last_message = messages[-1]
            
            if isinstance(last_message, ToolMessage):
                if last_message.name in ["AjudaProgramacao", "DuvidasRPG"]:
                    return "end"
                
                return "agent"
            
            return "agent"
        
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(self.tools))
        
        workflow.set_entry_point("agent")
        
        workflow.add_conditional_edges("agent", router_logic, {
            "continue": "tools", 
            "end": END
        })
        
        workflow.add_conditional_edges("tools", after_tools_router, {
            "agent": "agent", 
            "end": END
        })
        
        return workflow.compile()

    def _reconstruct_history(self, session_messages: List[dict]) -> List[BaseMessage]:
        """Converte o histórico de dicionários do Streamlit para objetos LangChain"""
        history = []
        for msg in session_messages:
            if not isinstance(msg, dict): continue
            
            role = msg.get("role")
            content = str(msg.get("content", ""))
            
            if not content: continue
            
            if role == "user": 
                history.append(HumanMessage(content=content))
            elif role == "assistant": 
                history.append(AIMessage(content=content))
        return history

    def invoke(self, input_text: str, session_messages: List[dict], uploaded_files: List[dict] = None, user_credentials=None, user_infos=None):
        # 1. Configura Credenciais para Ferramentas do Google (Runtime)
        if user_credentials:
            self.create_event_tool.set_credentials(user_credentials)
            self.check_calendar_tool.set_credentials(user_credentials)
            self.check_email_tool.set_credentials(user_credentials)
            self.send_email_tool.set_credentials(user_credentials)

        # 2. Reconstrói Histórico
        lc_messages = self._reconstruct_history(session_messages)
        
        # 3. Prepara Conteúdo Atual (Multimodal)
        current_content = []
        if input_text: 
            current_content.append({"type": "text", "text": input_text})
            
        if uploaded_files:
            # Aviso para o agente sobre arquivos (não joga todo o binário no prompt para economizar tokens)
            file_names = ", ".join([f.get("name", "arquivo") for f in uploaded_files]) if uploaded_files else "arquivos"
            current_content.append({"type": "text", "text": f"\n[SISTEMA]: O usuário anexou os seguintes arquivos: {file_names}. Se precisar analisá-los, peça detalhes."})
            
            # Se tiver imagens, adiciona para visão
            for file in uploaded_files:
                if file.get('mime', '').startswith('image/'):
                    try:
                        import base64
                        encoded = base64.b64encode(file['data']).decode('utf-8')
                        current_content.append({"type": "image_url", "image_url": {"url": f"data:{file['mime']};base64,{encoded}"}})
                    except: pass

        # Informações de Contexto do Usuário
        if user_infos and 'email' in user_infos and 'user' in user_infos:
             current_content.append({"type": "text", "text": f"\nCONTEXTO DO USUÁRIO:\nNome: {user_infos['user']}\nE-mail: {user_infos['email']}"})

        # Adiciona a mensagem atual ao histórico
        lc_messages.append(HumanMessage(content=current_content))
        
        try:
            # Executa o Grafo
            result = self.graph.invoke({"messages": lc_messages})
            last_message = result["messages"][-1]
            content = last_message.content
            
            # Tratamento de resposta vazia ou Tool Calls pendentes
            if not content:
                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                     content = "🤔 Processando ferramentas..."
                else:
                     content = "✅ Feito."

            return {"output": [{"role": "assistant", "content": str(content)}]}

        except Exception as e:
            return {"output": [{"role": "assistant", "content": f"Desculpe, ocorreu um erro interno no agente: {str(e)}"}]}