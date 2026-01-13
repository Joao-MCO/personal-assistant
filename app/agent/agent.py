import datetime
import json
import base64
import operator
from typing import List, TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatMaritalk
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tools.google import CheckCalendar, CreateEvent
from utils.settings import Settings
from tools.manager import agent_tools

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

class AgentFactory:
    def __init__(self, llm="gemini"):
        # 1. REMOVER as versões globais das ferramentas do Google
        # para evitar conflito entre usuários (single-session)
        global_tools = [t for t in agent_tools if t.name not in ["CriarEvento", "ConsultarAgenda"]]
        
        # 2. INSTANCIAR novas ferramentas exclusivas para este agente
        self.create_event_tool = CreateEvent()
        self.check_calendar_tool = CheckCalendar()
        
        # 3. Criar lista final de ferramentas desta sessão
        self.session_tools = global_tools + [self.create_event_tool, self.check_calendar_tool]
        
        # --- CORREÇÃO DE SEGURANÇA ---
        # Se llm for None ou vazio, força o padrão "gemini"
        if not llm:
            llm = "gemini"
            
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
            # Fallback (Else) para Gemini: 
            # Captura "gemini" OU qualquer valor desconhecido/nulo que tenha passado
            self.llm = ChatGoogleGenerativeAI(
                api_key=Settings.gemini["api_key"],
                model=Settings.gemini["model"],
                temperature=0.4 
            )

        # Agora self.llm existe garantidamente
        self.llm_with_tools = self.llm.bind_tools(self.session_tools)
        
        # O nó de ferramentas deve usar a lista da sessão
        self.tools = self.session_tools

        # 1. CARREGAR E-MAILS
        try:
            with open("app/assets/emails.json", "r", encoding="utf-8") as f:
                emails_list = json.load(f)
                emails_str = json.dumps(emails_list, ensure_ascii=False).replace("{", "{{").replace("}", "}}")
        except Exception as e:
            print(f"Aviso: Não foi possível carregar emails.json: {e}")
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
            Sua missão é facilitar a vida da equipe agendando reuniões, tirando dúvidas e lendo notícias.

            ### 📅 CONTEXTO TEMPORAL (Use para calcular datas)
            - **Hoje:** {dia_hoje_pt}, {data_hoje}.
            - **Hora:** {hora_agora}.
            - **Regra:** Se o usuário pedir "amanhã às 14h", calcule a data exata com base em hoje ({data_hoje}).
            - **Importante:** A ferramenta de calendário exige dia, mês e ano precisos.

            ### 📒 LISTA DE CONTATOS
            Quando estiver pedindo da própria agenda, assuma email = 'primary'.
            {emails_str}

            ### ⚙️ INSTRUÇÕES DE EXECUÇÃO
            1. **Prioridade:** Se o usuário pedir algo que suas ferramentas fazem (Agenda, Notícias, Código, RPG), **USE A FERRAMENTA**. Não explique, apenas faça.
            2. **Agendamento:** Se faltar o e-mail de alguém, procure na lista acima. Se não achar, tente nome.sobrenome@sharkdev.com.br.
            3. **Assertividade:** Nunca diga "não tenho acesso" se você possui a ferramenta `CriarEvento` ou `ConsultarAgenda` disponível. Tente usá-las.
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
                tool_name = last_message.name
                if tool_name in ["ConsultarAgenda", "CodeHelper", "SharkHelper", "LerNoticias"]:
                    return "agent"
                if tool_name in ["CriarEvento", "RPGQuestion"]:
                     return "end"
            return "agent"
        
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)
        
        workflow.set_entry_point("agent")
        
        workflow.add_conditional_edges(
            "agent", should_continue, {"continue": "tools", "end": END}
        )
        
        workflow.add_conditional_edges(
            "tools", after_tools, {"agent": "agent", "end": END}
        )
        
        return workflow.compile()
    
    def _reconstruct_history(self, session_messages: List[dict]) -> List[BaseMessage]:
        history = []
        for msg in session_messages:
            if not isinstance(msg, dict): continue
            
            role = msg.get("role")
            content = msg.get("content")
            if not content: continue

            if role == "user":
                history.append(HumanMessage(content=str(content)))
            elif role == "assistant":
                history.append(AIMessage(content=str(content)))
        return history

    def invoke(self, input_text: str, session_messages: List[dict], uploaded_files: List[dict] = None, user_credentials=None):
        history_objects = self._reconstruct_history(session_messages)
        
        current_content = []
        if input_text:
            current_content.append({"type": "text", "text": input_text})
            
        if uploaded_files:
            for file in uploaded_files:
                try:
                    mime = file['mime']
                    if mime.startswith('image/'):
                        encoded = base64.b64encode(file['data']).decode('utf-8')
                        current_content.append({
                            "type": "image_url", 
                            "image_url": {"url": f"data:{mime};base64,{encoded}"}
                        })
                    else:
                        text = file['data'].decode('utf-8', errors='ignore')
                        current_content.append({"type": "text", "text": f"\n[Anexo]: {text}"})
                except:
                    pass
        
        if not current_content:
            current_content.append({"type": "text", "text": "..."})
        
        # --- INJEÇÃO DE CREDENCIAIS ---
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
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                 content = "Estou processando sua solicitação..."
            else:
                 if isinstance(last_message, ToolMessage):
                     content = last_message.content

        if isinstance(content, list):
            parts = [c.get("text", "") for c in content if isinstance(c, dict)]
            content = " ".join(parts)
            
        return {"output": [{"role": "assistant", "content": str(content)}]}