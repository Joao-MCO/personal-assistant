"""
Rastreamento de uso/custo de LLM: toda skill especialista que chama um modelo
diretamente (RevisorDeCodigo, GeradorDeTestes, etc.) usa `log_llm_call()`
depois de receber a resposta, para alimentar a tabela `llm_calls` que o
MonitorDeCustosLLM consulta. As chamadas do próprio orquestrador são
registradas à parte, pelo `SQLAuditCallbackHandler` (services/audit_callback.py).

IMPORTANTE sobre os preços abaixo: são valores aproximados, para dar uma
ORDEM DE GRANDEZA de custo -- não uma fatura exata. Preços de LLM mudam com
frequência; ajuste `PRECOS_POR_1M_TOKENS` conforme a tabela vigente dos
provedores sempre que for relevante. O objetivo aqui é comparar o uso
relativo entre modelos/skills, não reconciliar com a fatura real.
"""

import logging
from typing import Any, Optional

from db.base import SessionLocal
from db.models import LLMCall

logger = logging.getLogger(__name__)

# Preço aproximado em USD por 1 milhão de tokens (entrada, saída).
# Ajuste conforme a tabela de preços vigente de cada provedor.
PRECOS_POR_1M_TOKENS = {
    "gemini": {"input": 0.10, "output": 0.40},
    "gpt": {"input": 0.15, "output": 0.60},
    "claude": {"input": 1.00, "output": 5.00},
}


def estimate_cost(model_family: str, tokens_in: int, tokens_out: int) -> Optional[float]:
    precos = PRECOS_POR_1M_TOKENS.get(model_family)
    if precos is None or tokens_in is None or tokens_out is None:
        return None
    return round((tokens_in / 1_000_000) * precos["input"] + (tokens_out / 1_000_000) * precos["output"], 6)


def extract_token_usage(llm_response: Any) -> tuple[Optional[int], Optional[int]]:
    """
    Extrai (tokens_in, tokens_out) de uma resposta do LangChain, cobrindo os
    dois formatos mais comuns entre os providers usados no projeto:
    `response.usage_metadata` (Gemini/Anthropic via LangChain) e
    `response.response_metadata['token_usage']` (OpenAI).
    """
    usage = getattr(llm_response, "usage_metadata", None)
    if usage:
        return usage.get("input_tokens"), usage.get("output_tokens")

    meta = getattr(llm_response, "response_metadata", None) or {}
    token_usage = meta.get("token_usage") or meta.get("usage")
    if token_usage:
        return (
            token_usage.get("prompt_tokens") or token_usage.get("input_tokens"),
            token_usage.get("completion_tokens") or token_usage.get("output_tokens"),
        )
    return None, None


def log_llm_call(
    model_family: str,
    skill_name: str,
    llm_response: Any = None,
    session_id: Optional[str] = None,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
) -> None:
    """
    Grava uma chamada de LLM em `llm_calls`. Pode receber a resposta bruta do
    LangChain (`llm_response`, e os tokens são extraídos dela automaticamente)
    ou os tokens já contados manualmente (`tokens_in`/`tokens_out`).

    Uma falha aqui nunca deve interromper a resposta ao usuário -- por isso
    o try/except só loga o erro.
    """
    try:
        if llm_response is not None and (tokens_in is None or tokens_out is None):
            tokens_in, tokens_out = extract_token_usage(llm_response)

        cost = estimate_cost(model_family, tokens_in, tokens_out) if (tokens_in and tokens_out) else None

        db = SessionLocal()
        try:
            db.add(LLMCall(
                session_id=session_id,
                model=model_family,
                skill_name=skill_name,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                estimated_cost_usd=cost,
            ))
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception(f"Falha ao registrar uso de LLM ({skill_name}/{model_family}) — resposta ao usuário não é afetada")