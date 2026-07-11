"""
Catálogo de Skills: lista o que a Cidinha sabe fazer, agrupado por
categoria, filtrado pelas permissões reais de quem perguntou (reaproveita
services/permissions.py -- a mesma fonte de verdade que decide quais tools
o LLM recebe via bind_tools).
"""

import logging
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, PrivateAttr

from models.tools import CatalogoDeSkillsInput

logger = logging.getLogger(__name__)

# Categoria de exibição por nome de ferramenta. Ferramentas não listadas
# aqui caem em "Outras" -- não quebra ao esquecer de categorizar uma nova.
CATEGORIAS = {
    "AjudaShark": "Conhecimento Interno",
    "RAGDaBaseDeCodigo": "Conhecimento Interno",
    "OnboardingGuiado": "Conhecimento Interno",
    "CriarEvento": "Google Workspace",
    "ConsultarAgenda": "Google Workspace",
    "ConsultarEmail": "Google Workspace",
    "EnviarEmail": "Google Workspace",
    "BuscarNoDrive": "Google Workspace",
    "ArquivosRecentesDrive": "Google Workspace",
    "ConsultarDocumentosDrive": "Google Workspace",
    "CriarTarefa": "Google Workspace",
    "ConsultarTarefas": "Google Workspace",
    "ConcluirTarefa": "Google Workspace",
    "RevisorDeCodigo": "Engenharia de Código",
    "GeradorDeTestes": "Engenharia de Código",
    "DiagnosticoDeErro": "Engenharia de Código",
    "GeradorDeDocumentacao": "Engenharia de Código",
    "RevisorDeSeguranca": "Engenharia de Código",
    "GeradorDeCommitMessage": "Fluxo de Desenvolvimento",
    "AuditoriaDeDependencias": "Fluxo de Desenvolvimento",
    "GeradorDeStandup": "Fluxo de Desenvolvimento",
    "TradutorTecnico": "Fluxo de Desenvolvimento",
    "MonitorDeCustosLLM": "Monitoramento (admin)",
    "HealthCheckAgregado": "Monitoramento (admin)",
    "RelatorioDeEngajamento": "Monitoramento (admin)",
    "ConsultaCEP": "Consultas Externas",
    "ConsultaDocumento": "Consultas Externas",
    "CotacaoMoeda": "Consultas Externas",
    "Clima": "Consultas Externas",
    "SalvarNota": "Produtividade Pessoal",
    "ConsultarNotas": "Produtividade Pessoal",
    "CriarRotina": "Produtividade Pessoal",
    "ListarRotinas": "Produtividade Pessoal",
    "AniversariantesDoMes": "Organização Interna",
    "EncurtarURL": "Utilidades",
    "ConversorDeFormato": "Utilidades de Dev",
    "Codificador": "Utilidades de Dev",
    "GeradorDeIdentificador": "Utilidades de Dev",
    "GeradorDeHash": "Utilidades de Dev",
    "GeradorDeSenha": "Utilidades de Dev",
    "GeradorDeDadosFake": "Utilidades de Dev",
    "DashboardPessoal": "Meta",
}


class CatalogoDeSkills(BaseTool):
    name: str = "CatalogoDeSkills"
    description: str = "Use quando o usuário perguntar o que a Cidinha sabe fazer, ou pedir uma lista das funcionalidades disponíveis."
    args_schema: Type[BaseModel] = CatalogoDeSkillsInput
    return_direct: bool = False
    _employee_id: Optional[int] = PrivateAttr(default=None)

    def set_employee_id(self, employee_id: Optional[int]):
        self._employee_id = employee_id

    def _run(self) -> str:
        from services.permissions import get_allowed_tool_names
        from tools.manager import agent_tools

        permitidas = get_allowed_tool_names(self._employee_id)
        disponiveis = [t for t in agent_tools if t.name in permitidas]

        por_categoria: dict = {}
        for tool in disponiveis:
            categoria = CATEGORIAS.get(tool.name, "Outras")
            por_categoria.setdefault(categoria, []).append(tool.name)

        linhas = [f"Posso ajudar com {len(disponiveis)} coisa(s), agrupadas assim:"]
        for categoria in sorted(por_categoria):
            linhas.append(f"\n**{categoria}**")
            for nome in sorted(por_categoria[categoria]):
                linhas.append(f"- {nome}")

        return "\n".join(linhas)