import os
import base64
from typing import List, TypedDict, Annotated, Sequence, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatMaritalk
from langchain_anthropic import ChatAnthropic
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
        
        self.llm_with_tools = self.llm.bind_tools(agent_tools)
        self.tools = agent_tools

        tools_message = ""
        for tool in self.tools:
            tools_message = tools_message + f"* {tool.name}: {tool.description}\n"

        template = f"""
            Você é a Cidinha, a secretária virtual da SharkDev, uma empresa de tecnologia.
            
            SUAS CAPACIDADES:
            1. Você É CAPAZ de analisar imagens, ler documentos (PDFs, TXT) e processar arquivos enviados.
            2. Se receber um arquivo (imagem ou PDF), analise seu conteúdo visual ou textual detalhadamente.
            3. Seja sempre simpática, proativa e use emojis.
            
            Ferramentas disponíveis:
            {tools_message}
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
        
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)
        
        workflow.set_entry_point("agent")
        
        workflow.add_conditional_edges(
            "agent", should_continue, {"continue": "tools", "end": END}
        )
        workflow.add_edge("tools", "agent")
        
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
            role = msg.get("role")
            content = msg.get("content")
            
            # Pula mensagens de erro ou vazias se houver
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
                
                # Suporte para Imagens E PDFs (Application/PDF)
                if mime.startswith('image/') or mime == 'application/pdf':
                    media_block = self._process_file(data, mime)
                    current_message_content.append(media_block)
                
                # Suporte para Textos/Códigos/JSON
                elif mime.startswith('text/') or 'application/json' in mime or 'csv' in mime:
                    text_content = data.decode('utf-8', errors='ignore')
                    current_message_content.append({
                        "type": "text", 
                        "text": f"\n\n--- Arquivo Anexo ({mime}) ---\n{text_content}\n-------------------------------"
                    })
        
        # Se não houver conteúdo (ex: envio vazio), evita erro
        if not current_message_content:
            current_message_content.append({"type": "text", "text": "..."})

        # Cria a mensagem humana atual
        current_human_message = HumanMessage(content=current_message_content)
        
        # 3. Executa o grafo com HISTÓRICO + MENSAGEM ATUAL
        # O LangGraph vai concatenar isso ao estado
        inputs = {"messages": history_objects + [current_human_message]}
        
        result = self.graph.invoke(inputs)
        
        # 4. Processa o retorno (pega apenas a última mensagem da IA)
        last_message = result["messages"][-1]
        content = last_message.content
        
        # Normalização de resposta
        if isinstance(content, list):
            text_parts = [item['text'] for item in content if isinstance(item, dict) and 'text' in item]
            content = "\n".join(text_parts) if text_parts else str(content)

        return {"output": [{"role": "assistant", "content": content}]}