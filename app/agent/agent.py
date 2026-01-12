import datetime
import json
import os
import base64
from typing import List, TypedDict, Annotated, Sequence, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatMaritalk
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from utils.settings import Settings
from tools.manager import agent_tools
import operator

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

class AgentFactory:
    def __init__(self, llm="gemini"):
        # Certifique-se de usar gemini-1.5-flash ou gemini-1.5-pro no settings
        if llm == "gemini":
            self.llm = ChatGoogleGenerativeAI(
                api_key=Settings.gemini["api_key"],
                model=Settings.gemini["model"],
                temperature=0.7
            )

        if llm == "maritaca":
            self.llm = ChatMaritalk(
                api_key=Settings.maritaca["api_key"],
                model=Settings.maritaca["model"],
                temperature=0.7
            )
        
        if llm == "claude":
            self.llm = ChatAnthropic(
                api_key=Settings.claude["api_key"],
                model=Settings.claude["model"],
                temperature=0.7
            )
        
        if llm == "gpt":
            self.llm = ChatOpenAI(
                api_key=Settings.openai["api_key"],
                model=Settings.openai["model"],
                temperature=0.7
            )
        
        self.llm_with_tools = self.llm.bind_tools(agent_tools)
        self.tools = agent_tools

        tools_message = ""
        for tool in self.tools:
            tools_message = tools_message + f"* {tool.name}: {tool.description}\n"

        # 1. CARREGAR E-MAILS (Com correção UTF-8)
        try:
            with open("app/assets/emails.json", "r", encoding="utf-8") as f:
                emails_list = json.load(f)
                # O TRUQUE ESTÁ AQUI:
                # Substituímos { por {{ e } por }} para o LangChain não confundir com variáveis
                emails_str = json.dumps(emails_list, ensure_ascii=False).replace("{", "{{").replace("}", "}}")
        except Exception as e:
            print(f"Aviso: Não foi possível carregar emails.json: {e}")
            emails_str = "[]"

        agora = datetime.datetime.now()
        data_hoje = agora.strftime("%d/%m/%Y")
        dia_semana = agora.strftime("%A") 
        hora_agora = agora.strftime("%H:%M")
        
        dias_pt = {
            "Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira",
            "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"
        }
        dia_hoje_pt = dias_pt.get(dia_semana, dia_semana)

        # 3. PROMPT ENRIQUECIDO
        template = f"""
            ### 🧠 PERFIL DO ORQUESTRADOR
            Você é a **Cidinha**, assistente virtual da SharkDev.
            
            ### 📅 CONTEXTO TEMPORAL (CRÍTICO PARA AGENDAMENTOS)
            - **Data Atual:** {dia_hoje_pt}, {data_hoje}.
            - **Hora Atual:** {hora_agora}.
            - **Regra:** Use esta data como base para calcular "hoje", "amanhã" (dia seguinte), "sexta-feira que vem", etc.
            - **Atenção:** Ao chamar ferramentas de calendário, você DEVE calcular o dia/mês/ano exatos baseados na data acima.

            ### 📒 LISTA DE CONTATOS SHARKDEV
            Use estes dados para encontrar e-mails de participantes:
            {emails_str}

            {tools_message}

            ### 📝 DIRETRIZES
            - Se o usuário disser apenas o nome (ex: "Reunião com o Márcio"), busque o e-mail correspondente na lista de contatos acima.
            - Se não encontrar o nome na lista, use o domínio @sharkdev.com.br por padrão.
            
            ### 🚀 REGRA DE OURO
            Se decidir usar 'LerNoticias', 'ConsultarAgenda' ou 'DuvidasRPG', apenas dispare a ferramenta.
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
            if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
                return "end"
            return "continue"

        def after_tools(state: AgentState):
            messages = state["messages"]
            last_message = messages[-1]
            
            if isinstance(last_message, ToolMessage):
                content = last_message.content or ""
                tool_name = last_message.name
            
                if tool_name in ["ConsultarAgenda", "CodeHelper", "SharkHelper"]:
                    return "agent"

                if tool_name == "LerNoticias":
                    if "Erro" in content or "Não foi possível" in content:
                        return "agent"
                    return "end"

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
    
    def _process_file(self, file_data: bytes, mime_type: str) -> dict:
        """Converte imagem/arquivo para o formato multimodal"""
        encoded_data = base64.b64encode(file_data).decode('utf-8')
        # Gemini aceita PDF via 'image_url' (data inline) no LangChain
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{encoded_data}"
            }
        }

    def _reconstruct_history(self, session_messages: List[dict]) -> List[BaseMessage]:
        """Converte o histórico de dicts do Streamlit para objetos LangChain"""
        history = []
        for msg in session_messages:
            if not isinstance(msg, dict):
                continue

            role = msg.get("role")
            content = msg.get("content")
            
            if not content: continue

            if role == "user":
                history.append(HumanMessage(content=content))
            elif role == "assistant":
                history.append(AIMessage(content=content))
        return history

    def invoke(self, input_text: str, session_messages: List[dict], uploaded_files: List[dict] = None):
        """Constrói a mensagem multimodal e invoca o agente com histórico"""
        
        # 1. Recupera o histórico anterior
        history_objects = self._reconstruct_history(session_messages)
        
        # 2. Constrói a mensagem ATUAL
        current_message_content = []
        
        if input_text:
            current_message_content.append({"type": "text", "text": input_text})
            
        if uploaded_files:
            for file in uploaded_files:
                mime = file['mime']
                data = file['data']
                
                if mime.startswith('image/') or mime == 'application/pdf':
                    media_block = self._process_file(data, mime)
                    current_message_content.append(media_block)
                
                elif mime.startswith('text/') or 'application/json' in mime or 'csv' in mime:
                    try:
                        text_content = data.decode('utf-8', errors='ignore')
                        current_message_content.append({
                            "type": "text", 
                            "text": f"\n\n--- Arquivo Anexo ({mime}) ---\n{text_content}\n-------------------------------"
                        })
                    except Exception:
                        pass
        
        if not current_message_content:
            current_message_content.append({"type": "text", "text": "..."})

        current_human_message = HumanMessage(content=current_message_content)
        
        # 3. Executa o grafo
        inputs = {"messages": history_objects + [current_human_message]}
        
        result = self.graph.invoke(inputs)
        
        # 4. Processa o retorno
        last_message = result["messages"][-1]
        content = last_message.content
        
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and 'text' in item:
                    text_parts.append(item['text'])
                elif isinstance(item, str):
                    text_parts.append(item)
            content = "\n".join(text_parts) if text_parts else str(content)

        return {"output": [{"role": "assistant", "content": content}]}