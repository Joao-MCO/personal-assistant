import time
import logging
from typing import Type
from pydantic import BaseModel
from langchain_core.tools import BaseTool
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from models.tools import CodeHelperInput
from utils.settings import WrappedSettings as Settings
from prompts.templates import CODE_HELPER_PROMPT

logger = logging.getLogger(__name__)

class CodeHelper(BaseTool):
    name: str = "AjudaProgramacao"
    description: str = "Use para gerar código, debug, explicar sintaxe ou refatoração."
    args_schema: Type[BaseModel] = CodeHelperInput
    return_direct: bool = True
    
    _chain: object = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Singleton da LLM e Chain
        llm = ChatAnthropic(
            model=Settings.claude["model"],
            api_key=Settings.claude["api_key"],
            temperature=0.2,
            max_tokens=4000
        )
        prompt = PromptTemplate(template=CODE_HELPER_PROMPT, input_variables=["query"])
        self._chain = prompt | llm | StrOutputParser()

    def _run(self, pergunta: str) -> str:
        logger.info(f"Tool CodeHelper iniciada. Params: pergunta='{pergunta}'")
        start = time.time()
        try:
            resposta = self._chain.invoke({"query": pergunta})
            logger.info(f"CodeHelper finalizado. Tempo: {time.time()-start:.2f}s")
            return resposta
        except Exception as e:
            logger.error(f"Erro CodeHelper: {str(e)}")
            return f"Erro ao processar código: {str(e)}"