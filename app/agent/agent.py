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
from utils.settings import Settings
from tools.manager import agent_tools

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

class AgentFactory:
    def __init__(self, llm="gemini"):
        
        # Configuração do Modelo
        if llm == "gemini":
            self.llm = ChatGoogleGenerativeAI(
                api_key=Settings.gemini["api_key"],
                model=Settings.gemini["model"],
                temperature=0.4  # Reduzi a temperatura para focar na execução de ferramentas
            )
        elif llm == "maritaca":
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
        
        # --- VINCULAÇÃO CORRETA ---
        # Apenas o bind é necessário. O modelo lerá a definição da classe Pydantic automaticamente.
        self.llm_with_tools = self.llm.bind_tools(agent_tools)
        self.tools = agent_tools

        # 1. CARREGAR E-MAILS (Com a correção de escape do JSON)
        try:
            with open("app/assets/emails.json", "r", encoding="utf-8") as f:
                emails_list = json.load(f)
                # Escapando chaves para não quebrar o PromptTemplate
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

        # 3. PROMPT LIMPO (Sem injeção de tools_message)
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
            # Verifica se o modelo decidiu chamar uma ferramenta
            if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
                return "continue"
            return "end"

        def after_tools(state: AgentState):
            messages = state["messages"]
            last_message = messages[-1]
            
            if isinstance(last_message, ToolMessage):
                tool_name = last_message.name
                
                # CodeHelper e ConsultarAgenda voltam pro agente para ele explicar o resultado
                if tool_name in ["ConsultarAgenda", "CodeHelper", "SharkHelper", "LerNoticias"]:
                    return "agent"

                # CriarEvento já gera uma resposta final bonita (no google.py), então podemos encerrar
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

    def invoke(self, input_text: str, session_messages: List[dict], uploaded_files: List[dict] = None):
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

        inputs = {"messages": history_objects + [HumanMessage(content=current_content)]}
        
        # Execução do Grafo
        try:
            result = self.graph.invoke(inputs)
            last_message = result["messages"][-1]
            content = last_message.content
        except Exception as e:
            return {"output": [{"role": "assistant", "content": f"Erro interno no Agente: {str(e)}"}]}

        # Correção de retorno vazio (caso a ferramenta tenha rodado mas o conteúdo não veio)
        if not content:
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                 # Se parou numa chamada de ferramenta sem executar o nó 'tools' (erro raro)
                 content = "Estou tentando acessar a agenda, mas houve uma interrupção técnica."
            else:
                 # Se for ToolMessage, o conteúdo é o output da ferramenta
                 if isinstance(last_message, ToolMessage):
                     content = last_message.content

        # Garantia final de string
        if isinstance(content, list):
            parts = [c.get("text", "") for c in content if isinstance(c, dict)]
            content = " ".join(parts)
            
        return {"output": [{"role": "assistant", "content": str(content)}]}