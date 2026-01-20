import datetime
import hashlib
import json
import operator
import logging
import streamlit as st
from typing import TypedDict, Annotated, Sequence, List, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from utils.files import get_emails
from utils.settings import WrappedSettings as Settings
from prompts.templates import AGENT_SYSTEM_PROMPT
from tools.manager import agent_tools
from tools.google_tools import CheckCalendar, CreateEvent
from tools.gmail import CheckEmail, SendEmail

# Configuração do Logger
logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

class AgentFactory:
    def __init__(self, llm="gemini"):
        logger.info(f"Inicializando AgentFactory. Modelo solicitado: {llm}")
        
        # 1. Ferramentas que precisam de credenciais do usuário (Runtime)
        self.create_event_tool = CreateEvent()
        self.check_calendar_tool = CheckCalendar()
        self.check_email_tool = CheckEmail()
        self.send_email_tool = SendEmail()
        
        # 2. Ferramentas Globais (Manager) + Ferramentas de Sessão
        global_tools = [t for t in agent_tools if t.name not in ["CriarEvento", "ConsultarAgenda", "ConsultarEmail", "EnviarEmail"]]
        
        self.tools = global_tools + [
            self.create_event_tool, 
            self.check_calendar_tool, 
            self.check_email_tool, 
            self.send_email_tool
        ]

        # 3. Seleção e Configuração do Modelo (LLM)
        self.llm = self._get_llm_instance(llm)
        
        try:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        except NotImplementedError:
            logger.warning(f"⚠️ O modelo '{llm}' não suporta bind_tools nativamente. O agente funcionará apenas como CHAT (sem ferramentas).")
            self.llm_with_tools = self.llm
        except Exception as e:
            logger.error(f"Erro ao vincular ferramentas: {e}")
            self.llm_with_tools = self.llm

        # 4. Contexto Temporal e Dinâmico
        emails_str = get_emails(True)
        agora = datetime.datetime.now()
        dias_pt = {
            "Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira",
            "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"
        }
        
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
            if model_name == "gpt":
                logger.info("Instanciando ChatOpenAI (GPT)")
                return ChatOpenAI(
                    api_key=Settings.openai["api_key"], 
                    model=Settings.openai["model"],
                    temperature=0.7
                )
            else:
                logger.info("Instanciando Google Gemini (Default)")
                if not Settings.gemini.get("api_key"):
                    msg = "Erro Crítico: API Key do Gemini não encontrada."
                    logger.critical(msg)
                    st.error(f"🚨 {msg}")
                    st.stop()
                    
                return ChatGoogleGenerativeAI(
                    api_key=Settings.gemini["api_key"], 
                    model=Settings.gemini["model"], 
                    temperature=0.4
                )
        except Exception as e:
            logger.error(f"Erro ao iniciar LLM ({model_name}): {e}", exc_info=True)
            st.error(f"Erro ao iniciar LLM ({model_name}): {e}")
            st.stop()

    def _create_graph(self):
        workflow = StateGraph(AgentState)
        
        def call_model(state: AgentState):
            messages = state["messages"]
            chain = self.prompt | self.llm_with_tools
            response = chain.invoke({"messages": messages})
            return {"messages": [response]}
        
        def router_logic(state: AgentState):
            messages = state["messages"]
            last_message = messages[-1]
            
            if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
                return "end"
            
            return "continue"

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

    def _tool_cache_key(self, tool_name: str, args: dict) -> str:
        payload = json.dumps(
            {"tool": tool_name, "args": args},
            sort_keys=True,
            default=str
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def _cached_tool_executor(self, tool):
        original_run = tool._run

        def wrapped_run(*args, **kwargs):
            key = self._tool_cache_key(tool.name, kwargs)

            with self._tool_cache_lock:
                if key in self._tool_cache:
                    logger.info(f"[CACHE HIT] Tool {tool.name}")
                    return self._tool_cache[key]

            result = original_run(*args, **kwargs)

            with self._tool_cache_lock:
                self._tool_cache[key] = result

            return result

        tool._run = wrapped_run

    # ------------------------------------------------------------------

    def invoke(
        self,
        input_text: str,
        session_messages: List[dict],
        uploaded_files: List[dict] = None,
        user_credentials=None,
        user_infos=None
    ):
        # 🔹 Limpa cache a cada execução do agente
        self._tool_cache = {}

        if user_credentials:
            for tool in [
                self.create_event_tool,
                self.check_calendar_tool,
                self.check_email_tool,
                self.send_email_tool
            ]:
                tool.set_credentials(user_credentials)
                self._cached_tool_executor(tool)

        lc_messages = self._reconstruct_history(session_messages)
        
        current_content = []
        if input_text: 
            current_content.append({"type": "text", "text": input_text})
            
        if uploaded_files:
            file_names = ", ".join([f.get("name", "arquivo") for f in uploaded_files]) if uploaded_files else "arquivos"
            current_content.append({"type": "text", "text": f"\n[SISTEMA]: O usuário anexou os seguintes arquivos: {file_names}. Se precisar analisá-los, peça detalhes."})
            
            for file in uploaded_files:
                if file.get('mime', '').startswith('image/'):
                    try:
                        import base64
                        encoded = base64.b64encode(file['data']).decode('utf-8')
                        current_content.append({"type": "image_url", "image_url": {"url": f"data:{file['mime']};base64,{encoded}"}})
                    except Exception as img_err:
                        logger.warning(f"Erro ao processar imagem anexa: {img_err}")

        if user_infos and 'email' in user_infos and 'user' in user_infos:
             current_content.append({"type": "text", "text": f"\nCONTEXTO DO USUÁRIO:\nNome: {user_infos['user']}\nE-mail: {user_infos['email']}"})

        lc_messages.append(HumanMessage(content=current_content))
        
        try:
            logger.info("Invocando LangGraph...")
            result = self.graph.invoke({"messages": lc_messages})
            
            last_message = result["messages"][-1]
            content = last_message.content
            
            # --- FIX: TRATAMENTO DE CONTEÚDO EM LISTA (Maritaca/Anthropic) ---
            if isinstance(content, list):
                # Extrai apenas o texto dos blocos
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        text_parts.append(part["text"])
                    elif hasattr(part, "text"):
                        text_parts.append(part.text)
                    elif isinstance(part, str):
                        text_parts.append(part)
                content = "\n".join(text_parts)
            # -----------------------------------------------------------------
            
            if not content:
                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                     logger.info("Resposta vazia da LLM, mas com tool_calls pendentes.")
                     content = "🤔 Processando ferramentas..."
                else:
                     logger.info("Resposta vazia da LLM e sem tool_calls.")
                     content = "✅ Feito."

            logger.info("Agent.invoke finalizado com sucesso.")
            return {"output": [{"role": "assistant", "content": str(content)}]}

        except Exception as e:
            logger.error(f"Erro na execução do agente: {str(e)}", exc_info=True)
            return {"output": [{"role": "assistant", "content": f"Desculpe, ocorreu um erro interno no agente: {str(e)}"}]}