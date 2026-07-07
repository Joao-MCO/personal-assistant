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