"""
Skills especialistas de engenharia de código. Todas seguem o mesmo padrão:
chamam Claude diretamente (independente de qual modelo esteja orquestrando a
conversa -- o mesmo precedente que o antigo CodeHelper já estabelecia),
registram o uso em `llm_calls` (services/llm_usage.py) e retornam a resposta
já pronta (`return_direct = True` -- ver TOOLS_RETURN_DIRECT em agent/agent.py).

Claude foi escolhido para essa família por ser tipicamente mais cuidadoso em
tarefas de geração/análise de código e seguir instruções detalhadas de forma
consistente -- mas é só uma configuração (MODEL_FAMILY, no topo do arquivo),
não algo hardcoded em cada função; trocar para "gpt" ou "gemini" é uma
mudança de uma linha.
"""

import logging
import time
from typing import ClassVar, Optional, Type

from langchain_core.prompts import PromptTemplate
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from agent.llm_factory import LLMFactory
from models.tools import (
    DiagnosticoDeErroInput,
    GeradorDeDocumentacaoInput,
    GeradorDeTestesInput,
    RevisorDeCodigoInput,
    RevisorDeSegurancaInput,
)
from services.llm_usage import log_llm_call

logger = logging.getLogger(__name__)

MODEL_FAMILY = "claude"


def _run_prompt(skill_name: str, template: str, **kwargs) -> str:
    """
    Helper compartilhado pelas 5 skills desta família: monta o prompt, chama
    o LLM especialista (sem o ping de teste extra -- ver create_llm_fast) e
    registra o uso em llm_calls antes de devolver o texto da resposta.
    """
    start = time.time()
    try:
        llm = LLMFactory.create_llm_fast(MODEL_FAMILY)
        prompt = PromptTemplate.from_template(template).format(**kwargs)
        response = llm.invoke(prompt)
        log_llm_call(model_family=MODEL_FAMILY, skill_name=skill_name, llm_response=response)
        return response.content
    except (ValueError, RuntimeError) as e:
        logger.error(f"{skill_name}: erro ao usar LLM especialista ({MODEL_FAMILY}): {e}")
        return f"Não consegui usar o modelo especialista ({MODEL_FAMILY}) agora: {e}"
    except Exception as e:
        logger.exception(f"{skill_name}: erro inesperado")
        return f"Erro inesperado ao executar {skill_name}: {e}"
    finally:
        logger.info(f"{skill_name} — tempo de execução: {time.time() - start:.2f}s")


class RevisorDeCodigo(BaseTool):
    name: str = "RevisorDeCodigo"
    description: str = """
    Use para revisar um trecho de código, função ou PR colado pelo usuário.
    Analisa contra boas práticas gerais (legibilidade, tratamento de erros,
    nomes, PEP8/convenções da linguagem) e sugere melhorias concretas.
    NÃO use para gerar testes (use GeradorDeTestes) nem para revisão
    focada em segurança (use RevisorDeSeguranca).
    """
    args_schema: Type[BaseModel] = RevisorDeCodigoInput
    return_direct: bool = True

    TEMPLATE: ClassVar[str] = """Você é um Engenheiro de Software Sênior fazendo code review na SharkDev.

Analise o código abaixo e devolva:
1. **Resumo** — o que o código faz, em 1-2 frases.
2. **Pontos de atenção** — problemas reais (bugs, falta de tratamento de erro, nomes ruins, complexidade desnecessária). Seja específico, cite a linha/trecho.
3. **Sugestão de código** — se a mudança for pequena e valer a pena, mostre o trecho corrigido. Não reescreva tudo se não for necessário.

Se o código já estiver bom, diga isso diretamente em vez de forçar críticas.

Contexto adicional fornecido: {contexto}

Código para revisão:
```
{codigo}
```
"""

    def _run(self, codigo: str, contexto: Optional[str] = None) -> str:
        return _run_prompt(self.name, self.TEMPLATE, codigo=codigo, contexto=contexto or "(nenhum fornecido)")


class GeradorDeTestes(BaseTool):
    name: str = "GeradorDeTestes"
    description: str = """
    Use para gerar testes unitários a partir de uma função ou trecho de código
    fornecido pelo usuário.
    """
    args_schema: Type[BaseModel] = GeradorDeTestesInput
    return_direct: bool = True

    TEMPLATE: ClassVar[str] = """Você é um Engenheiro de Software Sênior especialista em testes automatizados.

Gere testes unitários completos para o código abaixo, cobrindo: caso feliz, pelo menos um caso de borda, e pelo menos um caso de erro/exceção esperado.

Framework solicitado: {framework}
Se nenhum framework foi especificado, infira pela linguagem do código (ex.: pytest para Python, jest para JavaScript/TypeScript).

Devolva o arquivo de teste completo, pronto para rodar — sem placeholders como "# resto dos testes aqui".

Código:
```
{codigo}
```
"""

    def _run(self, codigo: str, framework: Optional[str] = None) -> str:
        return _run_prompt(self.name, self.TEMPLATE, codigo=codigo, framework=framework or "(não especificado, infira)")


class DiagnosticoDeErro(BaseTool):
    name: str = "DiagnosticoDeErro"
    description: str = """
    Use quando o usuário colar um stack trace, mensagem de erro ou trecho de
    log e pedir ajuda para entender ou resolver.
    """
    args_schema: Type[BaseModel] = DiagnosticoDeErroInput
    return_direct: bool = True

    TEMPLATE: ClassVar[str] = """Você é um Engenheiro de Software Sênior fazendo troubleshooting.

Analise o erro/log abaixo e devolva:
1. **Causa provável** — em linguagem direta, o que está causando isso.
2. **Como resolver** — passos concretos ou o trecho de código corrigido, se o contexto permitir.
3. **Como evitar no futuro** — se fizer sentido (ex.: validação faltando, tratamento de exceção).

Se o erro for ambíguo e o contexto fornecido não for suficiente para ter certeza, diga isso explicitamente e liste as hipóteses mais prováveis em vez de inventar uma causa única.

Contexto/código relevante: {contexto}

Erro/log:
```
{erro}
```
"""

    def _run(self, erro: str, contexto: Optional[str] = None) -> str:
        return _run_prompt(self.name, self.TEMPLATE, erro=erro, contexto=contexto or "(nenhum fornecido)")


class GeradorDeDocumentacao(BaseTool):
    name: str = "GeradorDeDocumentacao"
    description: str = """
    Use para gerar documentação (docstrings inline ou um README.md completo)
    a partir de um código fornecido pelo usuário.
    """
    args_schema: Type[BaseModel] = GeradorDeDocumentacaoInput
    return_direct: bool = True

    TEMPLATE_DOCSTRING: ClassVar[str] = """Você é um Engenheiro de Software Sênior escrevendo documentação técnica.

Gere docstrings completas para o código abaixo (formato apropriado à linguagem — ex.: Google/NumPy style em Python, JSDoc em JavaScript). Documente parâmetros, retorno, exceções levantadas e adicione um exemplo de uso quando fizer sentido.

Devolva o código completo com as docstrings inseridas, não só as docstrings soltas.

Código:
```
{codigo}
```
"""

    TEMPLATE_README: ClassVar[str] = """Você é um Engenheiro de Software Sênior escrevendo documentação técnica.

Gere um README.md completo para o código abaixo: o que faz, como instalar/rodar, principais funções/classes e um exemplo de uso.

Código:
```
{codigo}
```
"""

    def _run(self, codigo: str, formato: str = "docstring") -> str:
        template = self.TEMPLATE_README if formato == "readme" else self.TEMPLATE_DOCSTRING
        return _run_prompt(self.name, template, codigo=codigo)


class RevisorDeSeguranca(BaseTool):
    name: str = "RevisorDeSeguranca"
    description: str = """
    Use para analisar um código em busca de vulnerabilidades de segurança
    conhecidas: SQL injection, XSS, segredos/chaves hardcoded, falta de
    validação de entrada, etc. Diferente do RevisorDeCodigo, que é sobre
    qualidade geral — use esta quando o pedido for especificamente sobre
    segurança.
    """
    args_schema: Type[BaseModel] = RevisorDeSegurancaInput
    return_direct: bool = True

    TEMPLATE: ClassVar[str] = """Você é um Engenheiro de Segurança revisando código em busca de vulnerabilidades.

Analise o código abaixo especificamente por:
- Injeção (SQL, comando, template)
- XSS / falta de sanitização de saída
- Segredos, chaves de API ou senhas hardcoded
- Falta de validação/sanitização de entrada do usuário
- Uso inseguro de deserialização, eval, ou similar

Para cada achado, indique a gravidade (baixa/média/alta/crítica) e a correção sugerida. Se nada relevante for encontrado, diga isso claramente em vez de forçar achados triviais.

Código:
```
{codigo}
```
"""

    def _run(self, codigo: str) -> str:
        return _run_prompt(self.name, self.TEMPLATE, codigo=codigo)