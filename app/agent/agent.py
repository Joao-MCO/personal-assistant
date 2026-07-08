import datetime
import hashlib
import json
import operator
import logging
from typing import TypedDict, Annotated, Sequence, List, Union, Dict, Any, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from utils.files import get_emails
from utils.settings import WrappedSettings as Settings
from utils.tool_cache import ToolResultCache
from agent.llm_factory import LLMFactory
from prompts.templates import AGENT_SYSTEM_PROMPT
from tools.manager import agent_tools
from tools.google_tools import CheckCalendar, CreateEvent
from tools.gmail import CheckEmail, SendEmail
from tools.drive import BuscarNoDrive
from services.google_auth import GoogleCredentialManager
from services.audit_callback import SQLAuditCallbackHandler
from threading import Lock
import html

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Estado do agente com histórico de mensagens"""
    messages: Annotated[Sequence[BaseMessage], operator.add]


class AgentFactory:
    """
    Factory para criar e gerenciar agente IA com LangGraph.
    
    Características:
    - Suporte a múltiplos modelos LLM
    - Cache inteligente com TTL
    - Validação de credenciais
    - Error handling robusto
    - Rate limiting (delegado a main.py)
    """
    
    def __init__(self, llm: str = "gemini", allowed_tools: Optional[set] = None):
        """
        Inicializa AgentFactory
        
        Args:
            llm: Modelo LLM a usar ('gemini', 'gpt', etc)
            allowed_tools: Conjunto de nomes de ferramentas permitidas para
                esta invocação (ver services/permissions.py). None = sem
                filtragem, todas as ferramentas disponíveis (uso interno/
                administrativo; o /chat da API sempre passa um valor
                explícito, calculado a partir do funcionário da sessão).
        
        Raises:
            ValueError: Se modelo inválido
            RuntimeError: Se erro ao inicializar LLM
        """
        logger.info(f"Inicializando AgentFactory com modelo: {llm}")
        self.llm_name = llm
        
        try:
            # 1. Inicializar LLM com validação
            self.llm = LLMFactory.create_llm(llm)
        except (ValueError, RuntimeError) as e:
            logger.error(f"Erro ao inicializar LLM: {e}")
            raise
        
        # 2. Ferramentas que precisam de credenciais do usuário (Runtime)
        self.create_event_tool = CreateEvent()
        self.check_calendar_tool = CheckCalendar()
        self.check_email_tool = CheckEmail()
        self.send_email_tool = SendEmail()
        self.buscar_drive_tool = BuscarNoDrive()
        
        # 3. Ferramentas Globais + Ferramentas de Sessão
        global_tools = [
            t for t in agent_tools
            if t.name not in [
                "CriarEvento", "ConsultarAgenda",
                "ConsultarEmail", "EnviarEmail", "BuscarNoDrive"
            ]
        ]
        
        self.tools = global_tools + [
            self.create_event_tool, 
            self.check_calendar_tool, 
            self.check_email_tool, 
            self.send_email_tool,
            self.buscar_drive_tool
        ]

        # 3b. Filtra pelas permissões do usuário, se informadas. O LLM só
        # recebe (via bind_tools, logo abaixo) as ferramentas permitidas —
        # ele literalmente não tem como chamar uma ferramenta que não foi
        # vinculada, então a restrição é aplicada aqui, não checada depois
        # dentro de cada tool.
        if allowed_tools is not None:
            antes = len(self.tools)
            self.tools = [t for t in self.tools if t.name in allowed_tools]
            logger.info(f"Permissões aplicadas: {len(self.tools)}/{antes} ferramenta(s) disponível(eis) para esta sessão.")
        
        # Vincular ferramentas ao modelo
        try:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
            logger.info(f"✅ {len(self.tools)} ferramentas vinculadas ao LLM")
        except NotImplementedError:
            logger.warning(
                f"⚠️ Modelo '{llm}' não suporta bind_tools nativamente. "
                f"Agente funcionará apenas como CHAT."
            )
            self.llm_with_tools = self.llm
        except Exception as e:
            logger.error(f"Erro ao vincular ferramentas: {e}", exc_info=True)
            self.llm_with_tools = self.llm
        
        # 4. Cache inteligente com TTL
        self.cache = ToolResultCache(default_ttl_minutes=10)
        self.cache_lock = Lock()
        
        # 5. Contexto Temporal e Dinâmico
        self._initialize_system_prompt()
        
        # 6. Criar grafo do agente
        self.graph = self._create_graph()
        
        logger.info("✅ AgentFactory inicializado com sucesso")

    def _initialize_system_prompt(self) -> None:
        """Inicializa prompt do sistema com contexto dinâmico"""
        try:
            emails_str = get_emails(True)
        except Exception as e:
            logger.warning(f"Não foi possível carregar emails: {e}")
            emails_str = ""
        
        agora = datetime.datetime.now()
        dias_pt = {
            "Monday": "Segunda-feira", "Tuesday": "Terça-feira",
            "Wednesday": "Quarta-feira", "Thursday": "Quinta-feira",
            "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"
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

    def _create_graph(self) -> Any:
        """Cria grafo de execução do agente"""
        workflow = StateGraph(AgentState)
        
        def call_model(state: AgentState):
            """Chama modelo LLM"""
            messages = state["messages"]
            chain = self.prompt | self.llm_with_tools
            response = chain.invoke({"messages": messages})
            return {"messages": [response]}
        
        def router_logic(state: AgentState) -> str:
            """Rota lógica para ferramentas ou fim"""
            messages = state["messages"]
            last_message = messages[-1]
            
            if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
                return "end"
            
            return "continue"
        
        # Ferramentas cujo resultado deve ir DIRETO para o usuário, sem passar de
        # novo pelo LLM (equivalente ao `return_direct` do LangChain, mas aplicado
        # manualmente aqui porque o ToolNode do LangGraph não o lê automaticamente).
        # Critério: ferramentas que já chamam seu próprio LLM especialista e
        # devolvem uma resposta final e formatada — reprocessá-las pelo
        # orquestrador só arriscaria reformatar/resumir algo que já está pronto.
        # MonitorDeCustosLLM, HealthCheckAgregado e as RAGs ficam de fora de
        # propósito: elas devolvem dado bruto que se beneficia de uma síntese
        # do orquestrador antes de chegar ao usuário.
        TOOLS_RETURN_DIRECT: List[str] = [
            "RevisorDeCodigo",
            "GeradorDeTestes",
            "DiagnosticoDeErro",
            "GeradorDeDocumentacao",
            "RevisorDeSeguranca",
            "GeradorDeCommitMessage",
            "AuditoriaDeDependencias",
            "GeradorDeStandup",
            "TradutorTecnico",
        ]

        def after_tools_router(state: AgentState) -> str:
            """Rota lógica após execução de ferramentas"""
            messages = state["messages"]
            last_message = messages[-1]
            
            if isinstance(last_message, ToolMessage):
                if last_message.name in TOOLS_RETURN_DIRECT:
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
        
        logger.info("✅ Grafo do agente compilado")
        return workflow.compile()

    def _reconstruct_history(self, session_messages: List[Dict[str, Any]]) -> List[BaseMessage]:
        """
        Reconstrói histórico de mensagens para LangChain
        
        Args:
            session_messages: Histórico de mensagens da sessão Streamlit
        
        Returns:
            Lista de mensagens BaseMessage
        """
        history = []
        
        for msg in session_messages:
            if not isinstance(msg, dict):
                continue
            
            role = msg.get("role", "").lower()
            content = str(msg.get("content", "")).strip()
            
            if not content:
                continue
            
            try:
                if role == "user":
                    history.append(HumanMessage(content=content))
                elif role == "assistant":
                    history.append(AIMessage(content=content))
            except Exception as e:
                logger.warning(f"Erro ao reconstruir mensagem: {e}")
                continue
        
        return history

    def _get_cached_result(self, tool_name: str, **kwargs) -> Any:
        """Obtém resultado em cache se disponível"""
        with self.cache_lock:
            return self.cache.get(tool_name, **kwargs)

    def _cache_result(self, tool_name: str, result: Any, ttl_minutes: int = None, **kwargs):
        """Armazena resultado em cache"""
        with self.cache_lock:
            self.cache.set(tool_name, result, ttl_minutes=ttl_minutes, **kwargs)

    def _add_user_context_safely(
        self,
        current_content: List[Dict[str, Any]],
        user_infos: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Adiciona contexto do usuário de forma segura (anti-injection)
        
        Args:
            current_content: Conteúdo atual da mensagem
            user_infos: Informações do usuário
        
        Returns:
            Conteúdo com contexto adicionado
        """
        try:
            user_name = str(user_infos.get('user', 'Unknown'))[:100]
            user_email = str(user_infos.get('email', ''))[:200]
            
            # Validar email básico
            if '@' not in user_email:
                user_email = ''
            
            # Usar HTML escape para prevenir injection
            user_name_safe = html.escape(user_name)
            user_email_safe = html.escape(user_email)
            
            # Adicionar contexto de forma estruturada
            current_content.append({
                "type": "text",
                "text": f"[CONTEXTO USUÁRIO: Nome={user_name_safe}, Email={user_email_safe}]"
            })
            
            return current_content
        
        except Exception as e:
            logger.warning(f"Erro ao adicionar contexto do usuário: {e}")
            return current_content

    def invoke(
        self,
        input_text: str,
        session_messages: List[Dict[str, Any]],
        uploaded_files: List[Dict[str, Any]] = None,
        user_credentials: Any = None,
        user_infos: Dict[str, Any] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invoca o agente com entrada do usuário
        
        Args:
            input_text: Texto de entrada do usuário
            session_messages: Histórico de mensagens
            uploaded_files: Arquivos anexados
            user_credentials: Credenciais OAuth do Google
            user_infos: Informações do usuário
            session_id: Id da sessão (usado só para marcar as linhas de
                auditoria em `tool_calls` -- ver services/audit_callback.py).
                Opcional: se omitido, a auditoria é gravada sem session_id.
        
        Returns:
            Dict com saída do agente
        
        Raises:
            RuntimeError: Se erro na execução
        """
        try:
            # 1. Configurar credenciais nas ferramentas
            if user_credentials:
                # Validar e refresh credenciais se necessário
                if not GoogleCredentialManager.ensure_valid_credentials(user_credentials):
                    logger.warning("Credenciais inválidas ou expiradas")
                    return {
                        "output": [{
                            "role": "assistant",
                            "content": "⚠️ Suas credenciais expiraram. Faça login novamente."
                        }]
                    }
                
                for tool in [
                    self.create_event_tool,
                    self.check_calendar_tool,
                    self.check_email_tool,
                    self.send_email_tool,
                    self.buscar_drive_tool
                ]:
                    tool.set_credentials(user_credentials)
                
                logger.debug("✅ Credenciais configuradas nas ferramentas")
            
            # 2. Reconstruir histórico
            lc_messages = self._reconstruct_history(session_messages)
            
            # 3. Preparar conteúdo da mensagem atual
            current_content: List[Dict[str, Any]] = []
            
            if input_text:
                current_content.append({
                    "type": "text",
                    "text": input_text
                })
            
            if uploaded_files:
                file_names = ", ".join(
                    [f.get("name", "arquivo") for f in uploaded_files]
                ) if uploaded_files else "arquivos"
                
                current_content.append({
                    "type": "text",
                    "text": f"\n[ARQUIVO]: Anexados: {file_names}"
                })
                
                # Processar imagens
                for file in uploaded_files:
                    if file.get('mime', '').startswith('image/'):
                        try:
                            import base64
                            encoded = base64.b64encode(file['data']).decode('utf-8')
                            current_content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{file['mime']};base64,{encoded}"
                                }
                            })
                        except Exception as e:
                            logger.warning(f"Erro ao processar imagem: {e}")
            
            # 4. Adicionar contexto do usuário (seguro)
            if user_infos and 'email' in user_infos and 'user' in user_infos:
                current_content = self._add_user_context_safely(
                    current_content,
                    user_infos
                )
            
            # 5. Adicionar mensagem ao histórico
            lc_messages.append(HumanMessage(content=current_content))
            
            # 6. Invocar agente (com callback de auditoria/analytics de tool_calls)
            logger.info("Invocando LangGraph...")
            audit_callback = SQLAuditCallbackHandler(session_id=session_id, model_family=self.llm_name)
            result = self.graph.invoke(
                {"messages": lc_messages},
                config={"callbacks": [audit_callback]}
            )
            
            # 7. Processar resposta
            last_message = result["messages"][-1]
            content = last_message.content
            
            # Tratar conteúdo em lista (alguns modelos retornam assim)
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        text_parts.append(part["text"])
                    elif hasattr(part, "text"):
                        text_parts.append(part.text)
                    elif isinstance(part, str):
                        text_parts.append(part)
                content = "\n".join(text_parts)
            
            # Validar conteúdo
            if not content:
                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    logger.debug("Resposta vazia mas com tool_calls")
                    content = "🤔 Processando ferramentas..."
                else:
                    logger.debug("Resposta vazia da LLM")
                    content = "✅ Feito."
            
            logger.info("✅ Agent.invoke finalizado com sucesso")
            return {
                "output": [{
                    "role": "assistant",
                    "content": str(content)
                }]
            }
        
        except Exception as e:
            logger.error(f"Erro na execução do agente: {str(e)}", exc_info=True)
            return {
                "output": [{
                    "role": "assistant",
                    "content": f"❌ Erro: {str(e)[:200]}"
                }]
            }