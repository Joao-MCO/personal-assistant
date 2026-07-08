"""
Permissões por usuário: cargo (Employee.role) dá o padrão; exceções
individuais (EmployeeToolGrant) sobrescrevem o padrão pra um funcionário
específico. Quem não está vinculado a nenhum Employee (não logou no Google,
ou logou com um e-mail que não bate com nenhum cadastro) cai em "guest".

ALL_TOOL_NAMES é calculado a partir de tools.manager.agent_tools, não
hardcoded aqui -- assim uma ferramenta nova já aparece automaticamente no
sistema de permissões (por padrão, elegível para "member") sem precisar
lembrar de atualizar uma segunda lista em outro arquivo.
"""

import logging
from typing import Dict, Optional, Set

from db.base import SessionLocal
from db.models import Employee, EmployeeToolGrant

logger = logging.getLogger(__name__)

# Ferramentas mais sensíveis/operacionais -- fora do padrão de "member" por
# escolha deliberada, não por limitação técnica. Ajuste esta lista conforme
# a política real da SharkDev; para uma pessoa específica ter acesso mesmo
# assim, use uma exceção via EmployeeToolGrant (ver api/admin.py) em vez de
# tirar a ferramenta desta lista para todo mundo.
ADMIN_ONLY_TOOLS: Set[str] = {
    "MonitorDeCustosLLM",
    "HealthCheckAgregado",
    "AuditoriaDeDependencias",
    "RevisorDeSeguranca",
}

# Acesso de quem não está vinculado a nenhum Employee (não logou no Google,
# ou logou com e-mail fora do cadastro). De propósito o conjunto mais restrito:
# só conhecimento geral, nada de ações (Calendar/Email/Drive já exigem
# credencial própria e ficam de fora daqui por segurança, não só por acaso).
GUEST_TOOLS: Set[str] = {"AjudaShark", "RAGDaBaseDeCodigo", "OnboardingGuiado", "TradutorTecnico"}

VALID_ROLES = {"admin", "member", "guest"}


def _all_tool_names() -> Set[str]:
    from tools.manager import agent_tools
    return {t.name for t in agent_tools}


def _role_default_tools(role: str) -> Set[str]:
    all_tools = _all_tool_names()
    if role == "admin":
        return set(all_tools)
    if role == "guest":
        return set(GUEST_TOOLS)
    return all_tools - ADMIN_ONLY_TOOLS  # "member" (também o fallback para cargos desconhecidos)


def get_employee_role(employee_id: Optional[int]) -> str:
    if employee_id is None:
        return "guest"
    db = SessionLocal()
    try:
        emp = db.query(Employee).filter(Employee.id == employee_id, Employee.ativo == True).first()  # noqa: E712
        return emp.role if emp else "guest"
    finally:
        db.close()


def get_allowed_tool_names(employee_id: Optional[int]) -> Set[str]:
    """O conjunto de nomes de ferramentas que este funcionário (ou guest, se None) pode usar agora."""
    role = get_employee_role(employee_id)
    allowed = _role_default_tools(role)

    if employee_id is not None:
        db = SessionLocal()
        try:
            grants = db.query(EmployeeToolGrant).filter(EmployeeToolGrant.employee_id == employee_id).all()
            for g in grants:
                if g.granted:
                    allowed.add(g.tool_name)
                else:
                    allowed.discard(g.tool_name)
        finally:
            db.close()

    return allowed


def get_effective_tool_access(employee_id: int) -> Dict[str, Dict[str, object]]:
    """
    Visão completa e transparente do acesso de um funcionário: para cada
    ferramenta, se está liberada e se isso vem do cargo ou de uma exceção
    individual. Usado pelo endpoint GET /admin/employees/{id}/tool-access.
    """
    role = get_employee_role(employee_id)
    default_tools = _role_default_tools(role)

    db = SessionLocal()
    try:
        grants = {
            g.tool_name: g.granted
            for g in db.query(EmployeeToolGrant).filter(EmployeeToolGrant.employee_id == employee_id).all()
        }
    finally:
        db.close()

    result = {}
    for tool_name in sorted(_all_tool_names()):
        if tool_name in grants:
            result[tool_name] = {"allowed": grants[tool_name], "source": "exceção individual"}
        else:
            result[tool_name] = {"allowed": tool_name in default_tools, "source": f"padrão do cargo '{role}'"}
    return result


def set_tool_grant(employee_id: int, tool_name: str, granted: bool) -> None:
    db = SessionLocal()
    try:
        existing = (
            db.query(EmployeeToolGrant)
            .filter(EmployeeToolGrant.employee_id == employee_id, EmployeeToolGrant.tool_name == tool_name)
            .first()
        )
        if existing:
            existing.granted = granted
        else:
            db.add(EmployeeToolGrant(employee_id=employee_id, tool_name=tool_name, granted=granted))
        db.commit()
    finally:
        db.close()


def clear_tool_grant(employee_id: int, tool_name: str) -> bool:
    """Remove a exceção (volta a valer o padrão do cargo). Retorna True se havia algo para remover."""
    db = SessionLocal()
    try:
        existing = (
            db.query(EmployeeToolGrant)
            .filter(EmployeeToolGrant.employee_id == employee_id, EmployeeToolGrant.tool_name == tool_name)
            .first()
        )
        if existing:
            db.delete(existing)
            db.commit()
            return True
        return False
    finally:
        db.close()