from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# =========================================
# 1. Ferramentas de Informação (Shark)
# =========================================

class SharkHelperInput(BaseModel):
    pergunta: str = Field(
        ..., 
        description="A dúvida do usuário relacionada à SharkDev, processos internos ou plataforma Blip."
    )
    temas: List[str] = Field(
        default=[], 
        description="Lista de palavras-chave (tags) para auxiliar a busca no banco vetorial."
    )

# =========================================
# 2. Ferramentas de Produtividade (Google)
# =========================================

class CheckCalendarInput(BaseModel):
    start_date: dict = Field(
        ..., 
        description="Objeto representando a data de início da busca (chaves: year, month, day, hours, minutes)."
    )
    end_date: dict = Field(
        ..., 
        description="Objeto representando a data de fim da busca (chaves: year, month, day, hours, minutes)."
    )
    email: str = Field(
        default="primary", 
        description="ID do calendário a ser verificado (geralmente o email). Use 'primary' para o padrão."
    )

class CheckEmailInput(BaseModel):
    max_results: int = Field(
        default=5, 
        description="Número máximo de e-mails recentes a serem recuperados."
    )
    query: Optional[str] = Field(
        default=None, 
        description="Termo de busca para filtrar e-mails (ex: 'assunto:Reunião', 'from:chefe@empresa.com'). Se vazio, traz os mais recentes."
    )
    data_inicio: Optional[str] = Field(
        default=None, 
        description="Data inicial opcional para filtro (formato YYYY/MM/DD)."
    )
    data_fim: Optional[str] = Field(
        default=None, 
        description="Data final opcional para filtro (formato YYYY/MM/DD)."
    )

class SendEmailInput(BaseModel):
    to: str = Field(
        ..., 
        description="Endereço de e-mail do destinatário."
    )
    subject: str = Field(
        ..., 
        description="Assunto do e-mail."
    )
    body: str = Field(
        ..., 
        description="Conteúdo da mensagem."
    )
    body_type: Literal['plain', 'html'] = Field(
        default='plain', 
        description="Formato do corpo do e-mail: use 'plain' para texto simples ou 'html' para formatação rica."
    )

class CreateEventInput(BaseModel):
    meeting_date: dict = Field(
        ..., 
        description="Objeto com a data/hora de início da reunião (year, month, day, hours, minutes)."
    )
    description: str = Field(
        ..., 
        description="Título e descrição do evento (ex: 'Daily | Ana <> Pedro')."
    )
    attendees: Optional[List[str]] = Field(
        default=None, 
        description="Lista de e-mails dos convidados."
    )
    meet_length: int = Field(
        default=30, 
        description="Duração da reunião em minutos."
    )
    timezone: str = Field(
        default="America/Sao_Paulo", 
        description="Fuso horário do evento."
    )

# =========================================
# 3. Ferramentas de Engenharia (Código) — especialistas em Claude
# =========================================

class RevisorDeCodigoInput(BaseModel):
    codigo: str = Field(..., description="O código a ser revisado (trecho, função ou PR colado como texto).")
    contexto: Optional[str] = Field(default=None, description="Contexto adicional: linguagem, o que o código deveria fazer, convenções a seguir.")

class GeradorDeTestesInput(BaseModel):
    codigo: str = Field(..., description="A função/código para o qual gerar testes unitários.")
    framework: Optional[str] = Field(default=None, description="Framework de teste desejado (ex: pytest, jest, unittest). Se omitido, infira pela linguagem do código.")

class DiagnosticoDeErroInput(BaseModel):
    erro: str = Field(..., description="O stack trace, mensagem de erro ou trecho de log a ser diagnosticado.")
    contexto: Optional[str] = Field(default=None, description="Código relevante ao redor do erro, se disponível.")

class GeradorDeDocumentacaoInput(BaseModel):
    codigo: str = Field(..., description="O código para o qual gerar documentação.")
    formato: Literal["docstring", "readme"] = Field(default="docstring", description="'docstring' para comentários inline, 'readme' para um README.md completo.")

class RevisorDeSegurancaInput(BaseModel):
    codigo: str = Field(..., description="O código a ser analisado em busca de vulnerabilidades de segurança (SQLi, XSS, segredos hardcoded, etc.).")

# =========================================
# 4. Ferramentas de Fluxo de Desenvolvimento
# =========================================

class GeradorDeCommitMessageInput(BaseModel):
    diff: str = Field(..., description="A saída de 'git diff' (ou equivalente) com as mudanças a serem descritas.")

class AuditoriaDeDependenciasInput(BaseModel):
    requirements_txt: str = Field(..., description="O conteúdo de um requirements.txt a ser auditado em busca de vulnerabilidades conhecidas nas dependências.")

class GeradorDeStandupInput(BaseModel):
    github_username: str = Field(..., description="Usuário (login) do GitHub cujos commits serão resumidos.")
    desde_horas: int = Field(default=24, description="Quantas horas atrás buscar os commits (padrão: últimas 24h).")
    repos: Optional[List[str]] = Field(
        default=None,
        description="Lista opcional de repositórios no formato 'org/repo' para restringir a busca. Se omitido, busca em toda a organização configurada."
    )

# =========================================
# 5. Ferramentas de Monitoramento (sem LLM)
# =========================================

class MonitorDeCustosLLMInput(BaseModel):
    dias: int = Field(default=7, description="Janela de tempo em dias para agregar os custos e o uso de tokens.")

class HealthCheckAgregadoInput(BaseModel):
    pass

# =========================================
# 6. Ferramentas de Conhecimento (RAG)
# =========================================

class RAGCodebaseInput(BaseModel):
    pergunta: str = Field(..., description="A dúvida técnica sobre a base de código, arquitetura ou documentação interna dos repositórios da SharkDev.")

class OnboardingInput(BaseModel):
    pergunta: str = Field(..., description="A dúvida de alguém em onboarding sobre setup de ambiente, ferramentas ou processos iniciais na SharkDev.")

# =========================================
# 7. Outras Ferramentas
# =========================================

class TradutorTecnicoInput(BaseModel):
    texto: str = Field(..., description="O texto técnico a ser traduzido.")
    destino: Literal["en", "pt"] = Field(..., description="Idioma de destino: 'en' para inglês, 'pt' para português.")

class BuscarNoDriveInput(BaseModel):
    query: str = Field(..., description="Termo de busca: nome do arquivo, assunto da reunião, palavras-chave do conteúdo.")
    max_resultados: int = Field(default=5, description="Número máximo de arquivos a retornar.")

# =========================================
# 8. Consultas Externas (sem LLM)
# =========================================

class ConsultaCEPInput(BaseModel):
    cep: str = Field(..., description="CEP a consultar, com ou sem hífen (ex: '01310-100' ou '01310100').")

class ConsultaDocumentoInput(BaseModel):
    documento: str = Field(..., description="CPF (11 dígitos) ou CNPJ (14 dígitos), com ou sem pontuação.")

class CotacaoMoedaInput(BaseModel):
    moeda: str = Field(default="USD", description="Moeda a cotar contra o Real: dólar, euro, bitcoin ou libra (aceita código: USD, EUR, BTC, GBP).")

class ClimaInput(BaseModel):
    cidade: str = Field(..., description="Nome da cidade (Brasil) para consultar o clima atual.")

# =========================================
# 9. Cofre de Notas
# =========================================

class SalvarNotaInput(BaseModel):
    conteudo: str = Field(..., description="O conteúdo da nota a ser salva (texto livre, pode ser um JSON, um lembrete, o que for).")

class ConsultarNotasInput(BaseModel):
    busca: Optional[str] = Field(default=None, description="Termo para filtrar as notas por conteúdo. Se omitido, lista as mais recentes.")

# =========================================
# 10. Google Drive (complementos ao BuscarNoDrive)
# =========================================

class ArquivosRecentesDriveInput(BaseModel):
    max_resultados: int = Field(default=10, description="Número máximo de arquivos a retornar.")

class ConsultarDocumentosDriveInput(BaseModel):
    tipo: Optional[str] = Field(default=None, description="Filtra por tipo: 'documento', 'planilha', 'apresentacao', 'pdf'. Omita para todos os tipos.")
    pasta: Optional[str] = Field(default=None, description="Nome de uma pasta do Drive para restringir a busca. Omita para o Drive inteiro.")
    max_resultados: int = Field(default=10, description="Número máximo de arquivos a retornar.")

# =========================================
# 11. Utilitários de Dev (sem LLM)
# =========================================

class ConversorDeFormatoInput(BaseModel):
    conteudo: str = Field(..., description="O conteúdo a converter (texto bruto no formato de origem).")
    origem: Literal["json", "yaml", "csv"] = Field(..., description="Formato de origem do conteúdo.")
    destino: Literal["json", "yaml", "csv"] = Field(..., description="Formato de destino desejado.")

class CodificadorInput(BaseModel):
    texto: str = Field(..., description="O texto a codificar/decodificar.")
    operacao: Literal["base64_encode", "base64_decode", "url_encode", "url_decode", "hex_encode", "hex_decode"] = Field(
        ..., description="Qual operação de codificação/decodificação aplicar."
    )

class GeradorDeIdentificadorInput(BaseModel):
    tipo: Literal["uuid4", "ulid", "nanoid"] = Field(default="uuid4", description="Tipo de identificador único a gerar.")
    quantidade: int = Field(default=1, description="Quantos identificadores gerar de uma vez (máx. 50).")

class GeradorDeHashInput(BaseModel):
    texto: str = Field(..., description="O texto para calcular o hash.")
    algoritmo: Literal["md5", "sha1", "sha256", "sha512"] = Field(default="sha256", description="Algoritmo de hash a usar.")

class GeradorDeSenhaInput(BaseModel):
    tamanho: int = Field(default=16, description="Tamanho da senha/token (ignorado no modo 'memoravel').")
    modo: Literal["forte", "numerica", "memoravel"] = Field(
        default="forte", description="'forte' (letras/números/símbolos), 'numerica' (só dígitos, tipo PIN), 'memoravel' (palavras combinadas)."
    )

class GeradorDeDadosFakeInput(BaseModel):
    tipo: Literal["nome", "telefone", "email", "empresa", "endereco", "cpf", "texto"] = Field(
        ..., description="Tipo de dado fictício a gerar. 'texto' gera um parágrafo de lorem ipsum em português."
    )
    quantidade: int = Field(default=1, description="Quantos itens gerar de uma vez (máx. 20).")

# =========================================
# 12. Google Tasks
# =========================================

class CriarTarefaInput(BaseModel):
    titulo: str = Field(..., description="Título da tarefa.")
    data_vencimento: Optional[str] = Field(default=None, description="Data de vencimento no formato AAAA-MM-DD. Opcional.")
    notas: Optional[str] = Field(default=None, description="Notas/descrição adicional da tarefa. Opcional.")

class ConsultarTarefasInput(BaseModel):
    incluir_concluidas: bool = Field(default=False, description="Se True, inclui tarefas já marcadas como concluídas.")

class ConcluirTarefaInput(BaseModel):
    tarefa_id: str = Field(..., description="O id da tarefa a marcar como concluída (retornado por ConsultarTarefas).")

# =========================================
# 13. Agendador de Rotinas
# =========================================

class CriarRotinaInput(BaseModel):
    action_type: Literal["relatorio_engajamento", "custo_llm"] = Field(
        ..., description="Qual ação executar: 'relatorio_engajamento' ou 'custo_llm' (envia um resumo por e-mail, se houver login Google ativo)."
    )
    hora: str = Field(..., description="Horário de execução, formato HH:MM (24h).")
    dias_semana: Optional[str] = Field(
        default=None, description="Dias da semana separados por vírgula (mon,tue,wed,thu,fri,sat,sun). Omita para rodar todo dia."
    )

class ListarRotinasInput(BaseModel):
    pass

# =========================================
# 14. Encurtador de URL
# =========================================

class EncurtarURLInput(BaseModel):
    url: str = Field(..., description="A URL completa a ser encurtada.")
    slug_personalizado: Optional[str] = Field(default=None, description="Slug customizado desejado (ex: 'reuniao-abc'). Se omitido, um aleatório é gerado.")

# =========================================
# 15. Organização & Analytics
# =========================================

class AniversariantesDoMesInput(BaseModel):
    mes: Optional[int] = Field(default=None, description="Mês (1-12) para consultar aniversariantes. Se omitido, usa o mês atual.")

class RelatorioDeEngajamentoInput(BaseModel):
    dias: int = Field(default=30, description="Janela de tempo em dias para o relatório.")

# =========================================
# 16. Meta
# =========================================

class DashboardPessoalInput(BaseModel):
    pass

class CatalogoDeSkillsInput(BaseModel):
    pass