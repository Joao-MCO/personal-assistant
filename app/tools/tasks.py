"""
Gerenciador de Tarefas via Google Tasks — mesmo padrão de credencial das
outras tools do Google (Calendar/Gmail/Drive): recebem a credencial da
sessão atual via set_credentials(), setada em agent/agent.py a cada chamada.
"""

import logging
import time
from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, PrivateAttr

from models.tools import ConcluirTarefaInput, ConsultarTarefasInput, CriarTarefaInput

logger = logging.getLogger(__name__)

MSG_LOGIN = (
    "Pra gerenciar suas tarefas eu preciso que você esteja logado no Google.\n"
    "Acesse /auth/google/login para autenticar e tente novamente."
)


class CriarTarefa(BaseTool):
    name: str = "CriarTarefa"
    description: str = "Use para criar uma nova tarefa no Google Tasks do usuário."
    args_schema: Type[BaseModel] = CriarTarefaInput
    return_direct: bool = False
    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds

    def _run(self, titulo: str, data_vencimento: Optional[str] = None, notas: Optional[str] = None) -> str:
        start = time.time()
        if not self._user_credentials:
            return MSG_LOGIN

        from services.google_services import get_service
        service = get_service(self._user_credentials, "tasks")
        if not service:
            return "Erro técnico ao autenticar no Google Tasks."

        body = {"title": titulo}
        if notas:
            body["notes"] = notas
        if data_vencimento:
            body["due"] = f"{data_vencimento}T00:00:00.000Z"

        try:
            result = service.tasks().insert(tasklist="@default", body=body).execute()
            venc = f" (vencimento: {data_vencimento})" if data_vencimento else ""
            return f"Tarefa criada: '{titulo}'{venc}."
        except Exception as e:
            logger.error(f"Erro CriarTarefa: {e}", exc_info=True)
            return f"Erro ao criar tarefa: {e}"
        finally:
            logger.info(f"CriarTarefa — tempo de execução: {time.time() - start:.2f}s")


class ConsultarTarefas(BaseTool):
    name: str = "ConsultarTarefas"
    description: str = "Use para listar as tarefas pendentes (ou também concluídas, se pedido) do Google Tasks do usuário."
    args_schema: Type[BaseModel] = ConsultarTarefasInput
    return_direct: bool = False
    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds

    def _run(self, incluir_concluidas: bool = False) -> str:
        start = time.time()
        if not self._user_credentials:
            return MSG_LOGIN

        from services.google_services import get_service
        service = get_service(self._user_credentials, "tasks")
        if not service:
            return "Erro técnico ao autenticar no Google Tasks."

        try:
            result = service.tasks().list(tasklist="@default", showCompleted=incluir_concluidas).execute()
            tarefas = result.get("items", [])

            if not tarefas:
                return "Nenhuma tarefa encontrada."

            linhas = [f"{len(tarefas)} tarefa(s):"]
            for t in tarefas:
                status = "✅" if t.get("status") == "completed" else "⬜"
                venc = f" (vence {t['due'][:10]})" if t.get("due") else ""
                linhas.append(f"{status} [{t['id']}] {t.get('title', 'sem título')}{venc}")
            return "\n".join(linhas)
        except Exception as e:
            logger.error(f"Erro ConsultarTarefas: {e}", exc_info=True)
            return f"Erro ao consultar tarefas: {e}"
        finally:
            logger.info(f"ConsultarTarefas — tempo de execução: {time.time() - start:.2f}s")


class ConcluirTarefa(BaseTool):
    name: str = "ConcluirTarefa"
    description: str = "Use para marcar uma tarefa como concluída no Google Tasks. Precisa do id da tarefa (retornado por ConsultarTarefas)."
    args_schema: Type[BaseModel] = ConcluirTarefaInput
    return_direct: bool = False
    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds

    def _run(self, tarefa_id: str) -> str:
        start = time.time()
        if not self._user_credentials:
            return MSG_LOGIN

        from services.google_services import get_service
        service = get_service(self._user_credentials, "tasks")
        if not service:
            return "Erro técnico ao autenticar no Google Tasks."

        try:
            service.tasks().patch(tasklist="@default", task=tarefa_id, body={"status": "completed"}).execute()
            return "Tarefa marcada como concluída."
        except Exception as e:
            logger.error(f"Erro ConcluirTarefa: {e}", exc_info=True)
            return f"Erro ao concluir tarefa: {e}"
        finally:
            logger.info(f"ConcluirTarefa — tempo de execução: {time.time() - start:.2f}s")