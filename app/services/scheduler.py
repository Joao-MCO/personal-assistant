"""
Agendador de Rotinas: roda dentro do próprio processo (APScheduler,
BackgroundScheduler), com os jobs persistidos em `scheduled_tasks` e
recarregados no startup (ver iniciar_scheduler(), chamado em main.py).

IMPORTANTE — só funciona corretamente com 1 worker do Uvicorn/Gunicorn. Com
mais de um worker, cada processo teria seu próprio scheduler e a mesma
rotina rodaria em duplicidade (uma vez por worker). No Render, com o plano
atual (1 worker), não é um problema; vale revisar se um dia escalar
horizontalmente -- nesse caso, o caminho é mover para uma fila externa
(ex.: Celery Beat) ou garantir que só um worker rode o scheduler.

`ACTION_HANDLERS` é um conjunto FECHADO de ações conhecidas -- nunca código
arbitrário vindo do usuário -- por segurança.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def _handler_relatorio_engajamento(employee_id: int, params: dict) -> str:
    from tools.monitoring import RelatorioDeEngajamento
    return RelatorioDeEngajamento()._run(dias=params.get("dias", 7))


def _handler_custo_llm(employee_id: int, params: dict) -> str:
    from tools.monitoring import MonitorDeCustosLLM
    return MonitorDeCustosLLM()._run(dias=params.get("dias", 7))


ACTION_HANDLERS: Dict[str, Callable[[int, dict], str]] = {
    "relatorio_engajamento": _handler_relatorio_engajamento,
    "custo_llm": _handler_custo_llm,
}

ACTION_TITULOS = {
    "relatorio_engajamento": "Relatório de Engajamento (Cidinha)",
    "custo_llm": "Custo de LLM (Cidinha)",
}


def _executar_rotina(task_id: int) -> None:
    """Executa uma rotina: roda o handler, grava o resultado, e-maila se houver credencial disponível."""
    from db.base import SessionLocal
    from db.models import ScheduledTask

    db = SessionLocal()
    try:
        task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id, ScheduledTask.active == True).first()  # noqa: E712
        if task is None:
            logger.warning(f"Rotina {task_id} não encontrada ou inativa — pulando execução.")
            return

        handler = ACTION_HANDLERS.get(task.action_type)
        if handler is None:
            logger.error(f"Rotina {task_id}: action_type '{task.action_type}' desconhecido.")
            return

        params = json.loads(task.params) if task.params else {}
        try:
            resultado = handler(task.employee_id, params)
        except Exception as e:
            resultado = f"Erro ao executar a rotina: {e}"
            logger.exception(f"Rotina {task_id} ({task.action_type}) falhou")

        task.last_run_at = datetime.now(timezone.utc)
        task.last_result = resultado
        db.commit()

        _notificar_por_email(task.employee_id, task.action_type, resultado)
    finally:
        db.close()


def _notificar_por_email(employee_id: int, action_type: str, resultado: str) -> None:
    """Envia o resultado por e-mail se o funcionário tiver uma credencial Google válida em alguma sessão. Silencioso se não tiver."""
    try:
        from services.session_store import session_store
        from tools.gmail import SendEmail
        import google.oauth2.credentials

        creds_dict = session_store.get_latest_google_credentials_for_employee(employee_id)
        if not creds_dict:
            logger.info(f"Rotina ({action_type}) executada, mas funcionário {employee_id} não tem credencial Google disponível para notificar por e-mail.")
            return

        from db.base import SessionLocal
        from db.models import Employee
        db = SessionLocal()
        try:
            employee = db.query(Employee).filter(Employee.id == employee_id).first()
            destinatario = employee.email if employee else None
        finally:
            db.close()

        if not destinatario:
            return

        creds = google.oauth2.credentials.Credentials(**creds_dict)
        tool = SendEmail()
        tool.set_credentials(creds)
        tool._run(
            to=destinatario,
            subject=ACTION_TITULOS.get(action_type, "Rotina agendada (Cidinha)"),
            body=resultado,
        )
    except Exception:
        logger.exception(f"Falha ao notificar por e-mail a rotina ({action_type}) do funcionário {employee_id} — resultado já foi salvo em last_result")


def _cron_trigger(hora: str, dias_semana: Optional[str]) -> CronTrigger:
    h, m = hora.split(":")
    if dias_semana:
        return CronTrigger(hour=int(h), minute=int(m), day_of_week=dias_semana)
    return CronTrigger(hour=int(h), minute=int(m))


def agendar_job(task_id: int, hora: str, dias_semana: Optional[str]) -> None:
    if _scheduler is None:
        return
    _scheduler.add_job(
        _executar_rotina,
        trigger=_cron_trigger(hora, dias_semana),
        args=[task_id],
        id=f"scheduled_task_{task_id}",
        replace_existing=True,
    )


def remover_job(task_id: int) -> None:
    if _scheduler is None:
        return
    try:
        _scheduler.remove_job(f"scheduled_task_{task_id}")
    except Exception:
        pass  # job pode já não existir -- não é um erro relevante


def iniciar_scheduler() -> None:
    """Chamado uma vez no startup da aplicação (main.py): sobe o scheduler e recarrega as rotinas ativas do banco."""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
    _scheduler.start()

    from db.base import SessionLocal
    from db.models import ScheduledTask

    db = SessionLocal()
    try:
        ativas = db.query(ScheduledTask).filter(ScheduledTask.active == True).all()  # noqa: E712
        for task in ativas:
            agendar_job(task.id, task.hora, task.dias_semana)
        logger.info(f"Scheduler iniciado com {len(ativas)} rotina(s) ativa(s) recarregada(s) do banco.")
    finally:
        db.close()