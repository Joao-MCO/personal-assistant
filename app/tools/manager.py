from tools.google_tools import (
    CreateEvent,
    CheckCalendar,
    BuscarNoDrive,
    ArquivosRecentesDrive,
    ConsultarDocumentosDrive,
)
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
from tools.monitoring import (
    MonitorDeCustosLLM,
    HealthCheckAgregado,
    AniversariantesDoMes,
    RelatorioDeEngajamento,
)
from tools.knowledge_rag import RAGDaBaseDeCodigo, OnboardingGuiado
from tools.translate import TradutorTecnico
from tools.external_lookups import ConsultaCEP, ConsultaDocumento, CotacaoMoeda, Clima
from tools.notes import SalvarNota, ConsultarNotas
from tools.dev_formats import (
    ConversorDeFormato,
    Codificador,
    GeradorDeIdentificador,
    GeradorDeHash,
    GeradorDeSenha,
    GeradorDeDadosFake,
)
from tools.tasks import CriarTarefa, ConsultarTarefas, ConcluirTarefa
from tools.scheduler_tools import CriarRotina, ListarRotinas
from tools.shorturl import EncurtarURL
from tools.dashboard import DashboardPessoal
from tools.catalog import CatalogoDeSkills

# Instâncias para registro no Agente.
# Observação: ferramentas que precisam de credencial do usuário ou de
# employee_id (Calendar, Gmail, Drive, Tasks, Notas, Rotinas, Encurtador,
# Dashboard, Catálogo) são reinstanciadas dentro de AgentFactory.__init__
# (agent.py) como ferramentas "de sessão" -- as instâncias abaixo existem só
# por consistência de registro/introspecção (ex.: CatalogoDeSkills lista a
# partir desta lista), não são as que efetivamente recebem estado.
shark = SharkHelper()
create_event = CreateEvent()
check_calendar = CheckCalendar()
check_email = CheckEmail()
send_email = SendEmail()
buscar_drive = BuscarNoDrive()
arquivos_recentes_drive = ArquivosRecentesDrive()
consultar_documentos_drive = ConsultarDocumentosDrive()

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
aniversariantes_do_mes = AniversariantesDoMes()
relatorio_de_engajamento = RelatorioDeEngajamento()

rag_da_base_de_codigo = RAGDaBaseDeCodigo()
onboarding_guiado = OnboardingGuiado()

tradutor_tecnico = TradutorTecnico()

consulta_cep = ConsultaCEP()
consulta_documento = ConsultaDocumento()
cotacao_moeda = CotacaoMoeda()
clima = Clima()

salvar_nota = SalvarNota()
consultar_notas = ConsultarNotas()

conversor_de_formato = ConversorDeFormato()
codificador = Codificador()
gerador_de_identificador = GeradorDeIdentificador()
gerador_de_hash = GeradorDeHash()
gerador_de_senha = GeradorDeSenha()
gerador_de_dados_fake = GeradorDeDadosFake()

criar_tarefa = CriarTarefa()
consultar_tarefas = ConsultarTarefas()
concluir_tarefa = ConcluirTarefa()

criar_rotina = CriarRotina()
listar_rotinas = ListarRotinas()

encurtar_url = EncurtarURL()

dashboard_pessoal = DashboardPessoal()

catalogo_de_skills = CatalogoDeSkills()

agent_tools = [
    shark,
    create_event,
    check_calendar,
    check_email,
    send_email,
    buscar_drive,
    arquivos_recentes_drive,
    consultar_documentos_drive,
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
    aniversariantes_do_mes,
    relatorio_de_engajamento,
    rag_da_base_de_codigo,
    onboarding_guiado,
    tradutor_tecnico,
    consulta_cep,
    consulta_documento,
    cotacao_moeda,
    clima,
    salvar_nota,
    consultar_notas,
    conversor_de_formato,
    codificador,
    gerador_de_identificador,
    gerador_de_hash,
    gerador_de_senha,
    gerador_de_dados_fake,
    criar_tarefa,
    consultar_tarefas,
    concluir_tarefa,
    criar_rotina,
    listar_rotinas,
    encurtar_url,
    dashboard_pessoal,
    catalogo_de_skills,
]