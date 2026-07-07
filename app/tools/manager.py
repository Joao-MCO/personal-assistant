from tools.google_tools import CreateEvent, CheckCalendar, BuscarNoDrive
from tools.gmail import CheckEmail, SendEmail
from tools.shark import SharkHelper
from tools.code_assist import (
    RevisorDeCodigo,
    GeradorDeTestes,
    DiagnosticoDeErro,
    GeradorDeDocumentacao,
    RevisorDeSeguranca,
)
from tools.dev_workflow import GeradorDeCommitMessage, AuditoriaDeDependencias, GeradorDeStandup
from tools.monitoring import MonitorDeCustosLLM, HealthCheckAgregado
from tools.knowledge_rag import RAGDaBaseDeCodigo, OnboardingGuiado
from tools.translate import TradutorTecnico

# Instâncias para registro no Agente.
# Observação: create_event, check_calendar, check_email, send_email e
# buscar_drive são reinstanciadas dentro de AgentFactory.__init__ (agent.py)
# como ferramentas "de sessão" (recebem credenciais do usuário em tempo de
# execução) — as instâncias abaixo continuam existindo só por consistência
# de registro, mas não são as que efetivamente recebem credenciais.
shark = SharkHelper()
create_event = CreateEvent()
check_calendar = CheckCalendar()
check_email = CheckEmail()
send_email = SendEmail()
buscar_drive = BuscarNoDrive()

revisor_de_codigo = RevisorDeCodigo()
gerador_de_testes = GeradorDeTestes()
diagnostico_de_erro = DiagnosticoDeErro()
gerador_de_documentacao = GeradorDeDocumentacao()
revisor_de_seguranca = RevisorDeSeguranca()

gerador_de_commit_message = GeradorDeCommitMessage()
auditoria_de_dependencias = AuditoriaDeDependencias()
gerador_de_standup = GeradorDeStandup()

monitor_de_custos_llm = MonitorDeCustosLLM()
health_check_agregado = HealthCheckAgregado()

rag_da_base_de_codigo = RAGDaBaseDeCodigo()
onboarding_guiado = OnboardingGuiado()

tradutor_tecnico = TradutorTecnico()

agent_tools = [
    shark,
    create_event,
    check_calendar,
    check_email,
    send_email,
    buscar_drive,
    revisor_de_codigo,
    gerador_de_testes,
    diagnostico_de_erro,
    gerador_de_documentacao,
    revisor_de_seguranca,
    gerador_de_commit_message,
    auditoria_de_dependencias,
    gerador_de_standup,
    monitor_de_custos_llm,
    health_check_agregado,
    rag_da_base_de_codigo,
    onboarding_guiado,
    tradutor_tecnico,
]