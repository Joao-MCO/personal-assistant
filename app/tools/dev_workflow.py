"""
Skills de fluxo de desenvolvimento: commit message, auditoria de
dependências e resumo de standup individual a partir de commits reais do
GitHub. Cada uma usa o modelo mais adequado à sua tarefa (ver MODEL_FAMILY em
cada classe) -- tarefas rápidas e de baixo risco usam Gemini Flash; nenhuma
delas precisa do raciocínio mais caro do Claude.
"""

import logging
import time
from typing import ClassVar, List, Optional, Type

from langchain_core.prompts import PromptTemplate
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from agent.llm_factory import LLMFactory
from models.tools import (
    AuditoriaDeDependenciasInput,
    GeradorDeCommitMessageInput,
    GeradorDeStandupInput,
)
from services.dependency_audit import DependencyAuditError, run_pip_audit, summarize_findings
from services.github_service import GitHubError, fetch_recent_commits
from services.llm_usage import log_llm_call

logger = logging.getLogger(__name__)


class GeradorDeCommitMessage(BaseTool):
    name: str = "GeradorDeCommitMessage"
    description: str = """
    Use para gerar uma mensagem de commit a partir de um 'git diff' (ou
    descrição de mudanças) colado pelo usuário.
    """
    args_schema: Type[BaseModel] = GeradorDeCommitMessageInput
    return_direct: bool = True

    MODEL_FAMILY: ClassVar[str] = "gemini"
    TEMPLATE: ClassVar[str] = """Gere uma mensagem de commit clara e concisa para o diff abaixo, seguindo o padrão Conventional Commits (feat/fix/docs/refactor/chore/test + escopo opcional + descrição curta no imperativo). Se o diff mudar mais de uma coisa relevante, inclua um corpo com bullet points depois da linha de título.

Devolva SOMENTE a mensagem de commit, sem explicações antes ou depois.

Diff:
```
{diff}
```
"""

    def _run(self, diff: str) -> str:
        start = time.time()
        try:
            llm = LLMFactory.create_llm_fast(self.MODEL_FAMILY)
            prompt = PromptTemplate.from_template(self.TEMPLATE).format(diff=diff)
            response = llm.invoke(prompt)
            log_llm_call(model_family=self.MODEL_FAMILY, skill_name=self.name, llm_response=response)
            return response.content
        except (ValueError, RuntimeError) as e:
            logger.error(f"{self.name}: erro ao usar LLM ({self.MODEL_FAMILY}): {e}")
            return f"Não consegui gerar a mensagem de commit agora: {e}"
        finally:
            logger.info(f"{self.name} — tempo de execução: {time.time() - start:.2f}s")


class AuditoriaDeDependencias(BaseTool):
    name: str = "AuditoriaDeDependencias"
    description: str = """
    Use para auditar um requirements.txt (conteúdo colado pelo usuário) em
    busca de vulnerabilidades conhecidas nas dependências. A detecção usa
    pip-audit de verdade (não adivinha CVEs) — o LLM só entra para resumir
    os achados.
    """
    args_schema: Type[BaseModel] = AuditoriaDeDependenciasInput
    return_direct: bool = True

    MODEL_FAMILY: ClassVar[str] = "gemini"
    TEMPLATE: ClassVar[str] = """Resuma os achados de segurança abaixo para um desenvolvedor, em português, priorizando por gravidade (assuma gravidade mais alta para vulnerabilidades sem correção disponível ainda, e para bibliotecas de rede/autenticação). Para cada uma, diga o que fazer (geralmente: atualizar para a versão corrigida).

Achados brutos do pip-audit:
{achados}
"""

    def _run(self, requirements_txt: str) -> str:
        start = time.time()
        try:
            audit_json = run_pip_audit(requirements_txt)
        except DependencyAuditError as e:
            logger.error(f"{self.name}: {e}")
            return f"Não consegui rodar a auditoria: {e}"
        finally:
            logger.info(f"{self.name} (pip-audit) — tempo de execução: {time.time() - start:.2f}s")

        achados = summarize_findings(audit_json)

        # Se não há nenhuma vulnerabilidade, a mensagem já é clara e objetiva
        # o suficiente — não vale gastar uma chamada de LLM só pra reformular
        # "nenhuma vulnerabilidade encontrada".
        deps_com_vuln = [d for d in audit_json.get("dependencies", []) if d.get("vulns")]
        if not deps_com_vuln:
            return achados

        try:
            llm = LLMFactory.create_llm_fast(self.MODEL_FAMILY)
            prompt = PromptTemplate.from_template(self.TEMPLATE).format(achados=achados)
            response = llm.invoke(prompt)
            log_llm_call(model_family=self.MODEL_FAMILY, skill_name=self.name, llm_response=response)
            return response.content
        except (ValueError, RuntimeError) as e:
            logger.warning(f"{self.name}: LLM de resumo falhou, devolvendo achados brutos: {e}")
            return f"(Resumo automático indisponível, achados brutos do pip-audit abaixo)\n\n{achados}"


class GeradorDeStandup(BaseTool):
    name: str = "GeradorDeStandup"
    description: str = """
    Use quando o usuário pedir um resumo de standup/daily individual (o que
    EU fiz, não o time todo). Busca os commits reais do usuário no GitHub
    (não peça pra ele digitar o que fez) e gera o resumo a partir deles.
    Requer o usuário informar o próprio usuário do GitHub se ainda não tiver
    sido dito na conversa.
    """
    args_schema: Type[BaseModel] = GeradorDeStandupInput
    return_direct: bool = True

    MODEL_FAMILY: ClassVar[str] = "gemini"
    TEMPLATE: ClassVar[str] = """Você vai gerar um resumo de standup individual (formato "ontem eu fiz X, Y, Z") a partir dos commits reais abaixo, de {username} nas últimas {desde_horas}h.

Regras:
- Agrupe commits relacionados (mesmo repositório/tema) numa única linha, em vez de listar cada commit separadamente.
- Escreva em primeira pessoa, tom direto de standup ("Trabalhei em...", "Corrigi...", "Subi...").
- Se não houver nenhum commit, diga isso diretamente — não invente atividade.

Commits (repositório | mensagem):
{commits_formatados}
"""

    def _run(self, github_username: str, desde_horas: int = 24, repos: Optional[List[str]] = None) -> str:
        start = time.time()
        try:
            commits = fetch_recent_commits(github_username, since_hours=desde_horas, repos=repos)
        except GitHubError as e:
            logger.error(f"{self.name}: {e}")
            return f"Não consegui buscar os commits: {e}"
        finally:
            logger.info(f"{self.name} (GitHub) — tempo de execução: {time.time() - start:.2f}s")

        if not commits:
            return f"Não encontrei commits de '{github_username}' nas últimas {desde_horas}h."

        commits_formatados = "\n".join(f"- {c['repo']} | {c['message'].splitlines()[0]}" for c in commits)

        try:
            llm = LLMFactory.create_llm_fast(self.MODEL_FAMILY)
            prompt = PromptTemplate.from_template(self.TEMPLATE).format(
                username=github_username,
                desde_horas=desde_horas,
                commits_formatados=commits_formatados,
            )
            response = llm.invoke(prompt)
            log_llm_call(model_family=self.MODEL_FAMILY, skill_name=self.name, llm_response=response)
            return response.content
        except (ValueError, RuntimeError) as e:
            logger.warning(f"{self.name}: LLM de resumo falhou, devolvendo lista bruta: {e}")
            return f"(Resumo automático indisponível, commits brutos abaixo)\n\n{commits_formatados}"