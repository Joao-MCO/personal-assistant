"""
Cofre de Notas: salvar e consultar notas de texto livre, sempre escopadas ao
funcionário da sessão atual (via employee_id) -- ninguém vê nota de outra
pessoa. Sem employee_id (guest/sem login), a skill não funciona -- não tem
"dono" pra associar a nota.
"""

import logging
import time
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, PrivateAttr

from db.base import SessionLocal
from db.models import Note
from models.tools import ConsultarNotasInput, SalvarNotaInput

logger = logging.getLogger(__name__)

MSG_SEM_LOGIN = "Pra salvar notas eu preciso saber quem é você — acesse /auth/google/login e tente de novo."


class SalvarNota(BaseTool):
    name: str = "SalvarNota"
    description: str = "Use quando o usuário pedir para lembrar/salvar/anotar alguma informação (texto, JSON, um lembrete)."
    args_schema: Type[BaseModel] = SalvarNotaInput
    return_direct: bool = False
    _employee_id: Optional[int] = PrivateAttr(default=None)

    def set_employee_id(self, employee_id: Optional[int]):
        self._employee_id = employee_id

    def _run(self, conteudo: str) -> str:
        if not self._employee_id:
            return MSG_SEM_LOGIN

        db = SessionLocal()
        try:
            db.add(Note(employee_id=self._employee_id, content=conteudo))
            db.commit()
        finally:
            db.close()
        return "Nota salva."


class ConsultarNotas(BaseTool):
    name: str = "ConsultarNotas"
    description: str = "Use quando o usuário pedir para ver/buscar as notas que salvou anteriormente."
    args_schema: Type[BaseModel] = ConsultarNotasInput
    return_direct: bool = False
    _employee_id: Optional[int] = PrivateAttr(default=None)

    def set_employee_id(self, employee_id: Optional[int]):
        self._employee_id = employee_id

    def _run(self, busca: Optional[str] = None) -> str:
        if not self._employee_id:
            return MSG_SEM_LOGIN

        db = SessionLocal()
        try:
            query = db.query(Note).filter(Note.employee_id == self._employee_id)
            if busca:
                query = query.filter(Note.content.ilike(f"%{busca}%"))
            notas = query.order_by(Note.created_at.desc()).limit(20).all()
        finally:
            db.close()

        if not notas:
            return "Nenhuma nota encontrada." if busca else "Você ainda não salvou nenhuma nota."

        linhas = [f"- [{n.created_at.strftime('%d/%m %H:%M')}] {n.content}" for n in notas]
        return "\n".join(linhas)