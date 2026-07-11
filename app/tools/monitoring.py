"""
Skills de monitoramento -- nenhuma das duas chama um LLM. MonitorDeCustosLLM
é pura agregação SQL sobre o que já é gravado em `llm_calls`
(services/llm_usage.py); HealthCheckAgregado é uma checagem direta de cada
dependência externa (banco, Chroma, credenciais de LLM configuradas).
"""

import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel
from sqlalchemy import extract, func, text

from db.base import SessionLocal
from db.models import Employee, LLMCall, Message, SessionModel
from models.tools import AniversariantesDoMesInput, HealthCheckAgregadoInput, MonitorDeCustosLLMInput, RelatorioDeEngajamentoInput

logger = logging.getLogger(__name__)


class MonitorDeCustosLLM(BaseTool):
    name: str = "MonitorDeCustosLLM"
    description: str = """
    Use quando o usuário perguntar sobre gasto/custo/uso de tokens dos
    modelos de IA (Gemini, Claude, GPT), por modelo, por skill ou por pessoa.
    """
    args_schema: Type[BaseModel] = MonitorDeCustosLLMInput
    return_direct: bool = False  # é dado bruto agregado; deixa o orquestrador apresentar em prosa

    def _run(self, dias: int = 7) -> str:
        start = time.time()
        desde = datetime.now(timezone.utc) - timedelta(days=dias)
        db = SessionLocal()
        try:
            por_modelo = (
                db.query(
                    LLMCall.model,
                    func.count(LLMCall.id).label("chamadas"),
                    func.sum(LLMCall.tokens_in).label("tokens_in"),
                    func.sum(LLMCall.tokens_out).label("tokens_out"),
                    func.sum(LLMCall.estimated_cost_usd).label("custo"),
                )
                .filter(LLMCall.created_at >= desde)
                .group_by(LLMCall.model)
                .all()
            )
            por_skill = (
                db.query(
                    LLMCall.skill_name,
                    func.count(LLMCall.id).label("chamadas"),
                    func.sum(LLMCall.estimated_cost_usd).label("custo"),
                )
                .filter(LLMCall.created_at >= desde)
                .group_by(LLMCall.skill_name)
                .order_by(func.sum(LLMCall.estimated_cost_usd).desc())
                .all()
            )
            # Custo por pessoa: só cobre chamadas do orquestrador, que carregam
            # session_id -- chamadas de skills especialistas fora do /chat
            # (ex.: rodadas via services diretamente) não têm sessão associada.
            por_pessoa = (
                db.query(
                    Employee.nome,
                    func.count(LLMCall.id).label("chamadas"),
                    func.sum(LLMCall.estimated_cost_usd).label("custo"),
                )
                .select_from(LLMCall)
                .join(SessionModel, LLMCall.session_id == SessionModel.id)
                .join(Employee, SessionModel.employee_id == Employee.id)
                .filter(LLMCall.created_at >= desde)
                .group_by(Employee.nome)
                .order_by(func.sum(LLMCall.estimated_cost_usd).desc())
                .all()
            )
        finally:
            db.close()
            logger.info(f"{self.name} — tempo de execução: {time.time() - start:.2f}s")

        if not por_modelo:
            return f"Nenhuma chamada de LLM registrada nos últimos {dias} dia(s)."

        linhas = [f"Uso de LLM nos últimos {dias} dia(s):", "", "Por modelo:"]
        custo_total = 0.0
        for row in por_modelo:
            custo = row.custo or 0.0
            custo_total += custo
            linhas.append(
                f"- {row.model}: {row.chamadas} chamada(s), "
                f"{(row.tokens_in or 0):,} tokens de entrada, {(row.tokens_out or 0):,} de saída, "
                f"~US$ {custo:.4f}"
            )

        linhas.append("")
        linhas.append("Por skill (top custos):")
        for row in por_skill:
            linhas.append(f"- {row.skill_name}: {row.chamadas} chamada(s), ~US$ {(row.custo or 0.0):.4f}")

        if por_pessoa:
            linhas.append("")
            linhas.append("Por pessoa (ranking de uso, só chamadas via chat):")
            for row in por_pessoa:
                linhas.append(f"- {row.nome}: {row.chamadas} chamada(s), ~US$ {(row.custo or 0.0):.4f}")

        linhas.append("")
        linhas.append(f"Custo total estimado: ~US$ {custo_total:.4f} (valores aproximados, ver services/llm_usage.py)")
        return "\n".join(linhas)


class HealthCheckAgregado(BaseTool):
    name: str = "HealthCheckAgregado"
    description: str = """
    Use quando o usuário perguntar se os serviços/dependências estão
    funcionando (banco de dados, base de conhecimento, modelos de IA
    configurados).
    """
    args_schema: Type[BaseModel] = HealthCheckAgregadoInput
    return_direct: bool = False

    def _run(self) -> str:
        checks = []

        # Banco de dados
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            checks.append(("Banco de dados", True, ""))
        except Exception as e:
            checks.append(("Banco de dados", False, str(e)[:150]))

        # ChromaDB
        try:
            from services.chroma import get_client
            get_client().heartbeat()
            checks.append(("ChromaDB", True, ""))
        except Exception as e:
            checks.append(("ChromaDB", False, str(e)[:150]))

        # Credenciais de LLM configuradas (checagem de configuração, não uma chamada real de teste)
        from agent.llm_factory import LLMFactory
        for model_name in LLMFactory.get_available_models():
            valid, msg = LLMFactory.validate_model(model_name)
            checks.append((f"Credencial LLM: {model_name}", valid, "" if valid else "API key não configurada"))

        linhas = []
        for nome, ok, detalhe in checks:
            status = "✅ OK" if ok else f"❌ Falhou{f' — {detalhe}' if detalhe else ''}"
            linhas.append(f"- {nome}: {status}")

        todos_ok = all(ok for _, ok, _ in checks)
        cabecalho = "Todos os serviços estão saudáveis." if todos_ok else "Alguns serviços apresentam problemas:"
        return cabecalho + "\n\n" + "\n".join(linhas)


class AniversariantesDoMes(BaseTool):
    name: str = "AniversariantesDoMes"
    description: str = "Use quando o usuário perguntar quem faz aniversário este mês (ou em outro mês específico)."
    args_schema: Type[BaseModel] = AniversariantesDoMesInput
    return_direct: bool = False

    MESES: dict = {
        1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio", 6: "junho",
        7: "julho", 8: "agosto", 9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
    }

    def _run(self, mes: Optional[int] = None) -> str:
        mes = mes or date.today().month
        if not (1 <= mes <= 12):
            return f"Mês inválido: {mes}. Use um número de 1 a 12."

        db = SessionLocal()
        try:
            pessoas = (
                db.query(Employee)
                .filter(
                    Employee.ativo == True,  # noqa: E712
                    Employee.data_nascimento.isnot(None),
                    extract("month", Employee.data_nascimento) == mes,
                )
                .order_by(extract("day", Employee.data_nascimento))
                .all()
            )
        finally:
            db.close()

        if not pessoas:
            return f"Nenhum aniversariante cadastrado em {self.MESES[mes]}."

        linhas = [f"Aniversariantes de {self.MESES[mes]}:"]
        for p in pessoas:
            linhas.append(f"- {p.nome}, dia {p.data_nascimento.day:02d}")
        return "\n".join(linhas)


class RelatorioDeEngajamento(BaseTool):
    name: str = "RelatorioDeEngajamento"
    description: str = "Use quando o usuário perguntar sobre uso/engajamento da Cidinha: quantas sessões, mensagens, quantas pessoas usaram, em um período."
    args_schema: Type[BaseModel] = RelatorioDeEngajamentoInput
    return_direct: bool = False

    def _run(self, dias: int = 30) -> str:
        desde = datetime.now(timezone.utc) - timedelta(days=dias)
        db = SessionLocal()
        try:
            total_sessoes = db.query(SessionModel).filter(SessionModel.created_at >= desde).count()
            total_mensagens = db.query(Message).filter(Message.created_at >= desde).count()
            funcionarios_unicos = (
                db.query(SessionModel.employee_id)
                .filter(SessionModel.created_at >= desde, SessionModel.employee_id.isnot(None))
                .distinct()
                .count()
            )
            top_usuarios = (
                db.query(Employee.nome, func.count(SessionModel.id).label("sessoes"))
                .join(SessionModel, SessionModel.employee_id == Employee.id)
                .filter(SessionModel.created_at >= desde)
                .group_by(Employee.nome)
                .order_by(func.count(SessionModel.id).desc())
                .limit(5)
                .all()
            )
        finally:
            db.close()

        linhas = [
            f"Engajamento nos últimos {dias} dia(s):",
            f"- {total_sessoes} sessão(ões) iniciada(s)",
            f"- {total_mensagens} mensagem(ns) trocada(s)",
            f"- {funcionarios_unicos} funcionário(s) único(s) ativo(s)",
        ]
        if top_usuarios:
            linhas.append("")
            linhas.append("Top 5 mais ativos:")
            for nome, sessoes in top_usuarios:
                linhas.append(f"- {nome}: {sessoes} sessão(ões)")
        return "\n".join(linhas)