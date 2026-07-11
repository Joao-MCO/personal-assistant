"""
Tools do Agendador de Rotinas. A execução em si acontece em
services/scheduler.py -- estas tools só criam/listam os registros e
avisam o scheduler pra (des)agendar o job correspondente.
"""

import json
import logging
import re
import time
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, PrivateAttr

from db.base import SessionLocal
from db.models import ScheduledTask
from models.tools import CriarRotinaInput, ListarRotinasInput

logger = logging.getLogger(__name__)

MSG_SEM_LOGIN = "Pra criar rotinas eu preciso saber quem é você — acesse /auth/google/login e tente de novo."

_HORA_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_DIAS_VALIDOS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}


class CriarRotina(BaseTool):
    name: str = "CriarRotina"
    description: str = """
    Use para agendar uma rotina recorrente: enviar um relatório de
    engajamento ou de custo de LLM por e-mail, em um horário fixo.
    """
    args_schema: Type[BaseModel] = CriarRotinaInput
    return_direct: bool = False
    _employee_id: Optional[int] = PrivateAttr(default=None)

    def set_employee_id(self, employee_id: Optional[int]):
        self._employee_id = employee_id

    def _run(self, action_type: str, hora: str, dias_semana: Optional[str] = None) -> str:
        start = time.time()
        if not self._employee_id:
            return MSG_SEM_LOGIN

        if not _HORA_RE.match(hora):
            return f"Horário inválido: '{hora}'. Use o formato HH:MM (ex: '08:00')."

        if dias_semana:
            dias = [d.strip().lower() for d in dias_semana.split(",")]
            invalidos = [d for d in dias if d not in _DIAS_VALIDOS]
            if invalidos:
                return f"Dia(s) inválido(s): {invalidos}. Use: mon,tue,wed,thu,fri,sat,sun."
            dias_semana = ",".join(dias)

        db = SessionLocal()
        try:
            task = ScheduledTask(
                employee_id=self._employee_id,
                action_type=action_type,
                hora=hora,
                dias_semana=dias_semana,
                params=json.dumps({}),
                active=True,
            )
            db.add(task)
            db.commit()
            task_id = task.id
        finally:
            db.close()
            logger.info(f"CriarRotina — tempo de execução: {time.time() - start:.2f}s")

        from services.scheduler import agendar_job
        agendar_job(task_id, hora, dias_semana)

        freq = f"nos dias {dias_semana}" if dias_semana else "todo dia"
        return f"Rotina criada (id {task_id}): '{action_type}' às {hora}, {freq}."


class ListarRotinas(BaseTool):
    name: str = "ListarRotinas"
    description: str = "Use para listar as rotinas agendadas do usuário."
    args_schema: Type[BaseModel] = ListarRotinasInput
    return_direct: bool = False
    _employee_id: Optional[int] = PrivateAttr(default=None)

    def set_employee_id(self, employee_id: Optional[int]):
        self._employee_id = employee_id

    def _run(self) -> str:
        if not self._employee_id:
            return MSG_SEM_LOGIN

        db = SessionLocal()
        try:
            tasks = (
                db.query(ScheduledTask)
                .filter(ScheduledTask.employee_id == self._employee_id, ScheduledTask.active == True)  # noqa: E712
                .all()
            )
        finally:
            db.close()

        if not tasks:
            return "Você não tem nenhuma rotina agendada."

        linhas = [f"{len(tasks)} rotina(s) ativa(s):"]
        for t in tasks:
            freq = f"nos dias {t.dias_semana}" if t.dias_semana else "todo dia"
            ultima = f", última execução {t.last_run_at.strftime('%d/%m %H:%M')}" if t.last_run_at else ", nunca executada ainda"
            linhas.append(f"- [{t.id}] {t.action_type} às {t.hora}, {freq}{ultima}")
        return "\n".join(linhas)