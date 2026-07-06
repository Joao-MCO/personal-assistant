"""
Callback do LangChain/LangGraph que intercepta cada execução de ferramenta
durante o grafo (Calendar, Gmail, Shark Helper...) e grava uma linha em
`tool_calls`: nome da ferramenta, parâmetros, resultado, sucesso/erro e
duração. Cobre ao mesmo tempo auditoria ("o que a Cidinha fez, em nome de
quem, com quais dados") e analytics ("qual ferramenta é mais usada, com que
duração média, com que taxa de erro").

Falhas ao gravar a auditoria NUNCA devem interromper a resposta ao usuário
-- por isso todo acesso ao banco aqui está protegido por try/except que só
loga o erro.
"""

import logging
import time
from typing import Any, Dict, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

from db.base import SessionLocal
from db.models import ToolCall

logger = logging.getLogger(__name__)


class SQLAuditCallbackHandler(BaseCallbackHandler):
    def __init__(self, session_id: Optional[str] = None):
        super().__init__()
        self.session_id = session_id
        self._started_at: Dict[UUID, float] = {}
        self._tool_name: Dict[UUID, str] = {}
        self._params: Dict[UUID, str] = {}

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._started_at[run_id] = time.monotonic()
        self._tool_name[run_id] = (serialized or {}).get("name", "desconhecida")
        self._params[run_id] = input_str

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        # LangGraph passa um objeto ToolMessage (não a string pura) para
        # on_tool_end -- extraímos .content pra gravar o texto limpo em vez
        # do repr do objeto Python inteiro.
        result_text = getattr(output, "content", None)
        if result_text is None:
            result_text = str(output)
        self._persist(run_id, result=str(result_text), success=True, error=None)

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self._persist(run_id, result=None, success=False, error=str(error))

    def _persist(self, run_id: UUID, result: Optional[str], success: bool, error: Optional[str]) -> None:
        started = self._started_at.pop(run_id, None)
        tool_name = self._tool_name.pop(run_id, "desconhecida")
        params = self._params.pop(run_id, None)
        duration_ms = int((time.monotonic() - started) * 1000) if started is not None else None

        try:
            db = SessionLocal()
            try:
                db.add(ToolCall(
                    session_id=self.session_id,
                    tool_name=tool_name,
                    params=(params[:2000] if params else None),
                    result=(result[:4000] if result else None),  # evita linhas gigantes na tabela
                    success=success,
                    error_message=(error[:2000] if error else None),
                    duration_ms=duration_ms,
                ))
                db.commit()
            finally:
                db.close()
        except Exception:
            logger.exception("Falha ao gravar auditoria de tool_call (a resposta ao usuário segue normalmente)")