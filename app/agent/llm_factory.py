import os
import logging
from typing import Dict, Type, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)


# Configuração centralizada de modelos LLM
MODEL_CONFIG: Dict[str, Dict[str, Any]] = {
    "gemini": {
        "class": ChatGoogleGenerativeAI,
        "model": "gemini-2.0-flash",
        "env_key": "GEMINI_API_KEY",
        "temperature": 0.4,
        "description": "Google Gemini 2.0 Flash (recomendado)"
    },
    "gpt": {
        "class": ChatOpenAI,
        "model": "gpt-4-turbo",
        "env_key": "OPENAI_API_KEY",
        "temperature": 0.7,
        "description": "OpenAI GPT-4 Turbo"
    },
}

# Adicionar Claude se disponível
try:
    from langchain_anthropic import ChatAnthropic
    MODEL_CONFIG["claude"] = {
        "class": ChatAnthropic,
        "model": "claude-3-5-sonnet-20241022",
        "env_key": "CLAUDE_API_KEY",
        "temperature": 0.4,
        "description": "Anthropic Claude 3.5 Sonnet"
    }
except ImportError:
    logger.debug("Claude não disponível (langchain_anthropic não instalado)")


class LLMFactory:
    """
    Factory para criar instâncias de LLM com validação completa
    
    Características:
    - Validação de API keys
    - Teste de conectividade
    - Mensagens de erro claras
    - Suporte a múltiplos modelos
    """
    
    @staticmethod
    def get_available_models() -> list:
        """
        Retorna lista de modelos disponíveis
        
        Returns:
            List[str]: Nomes dos modelos disponíveis
        """
        return list(MODEL_CONFIG.keys())
    
    @staticmethod
    def get_model_description(model_name: str) -> str:
        """
        Retorna descrição do modelo
        
        Args:
            model_name: Nome do modelo
        
        Returns:
            str: Descrição do modelo
        """
        if model_name in MODEL_CONFIG:
            return MODEL_CONFIG[model_name].get("description", "")
        return ""
    
    @staticmethod
    def validate_model(model_name: str) -> tuple[bool, str]:
        """
        Valida se modelo está disponível e configurado
        
        Args:
            model_name: Nome do modelo a validar
        
        Returns:
            Tuple[bool, str]: (válido, mensagem de erro)
        
        Exemplo:
            >>> valid, msg = LLMFactory.validate_model("gemini")
            >>> if not valid:
            ...     print(f"Erro: {msg}")
        """
        # Verificar se modelo existe
        if model_name not in MODEL_CONFIG:
            available = ", ".join(LLMFactory.get_available_models())
            return False, (
                f"❌ Modelo desconhecido: '{model_name}'\n"
                f"Modelos disponíveis: {available}"
            )
        
        # Verificar se API key está configurada
        config = MODEL_CONFIG[model_name]
        api_key = os.environ.get(config["env_key"])
        
        if not api_key:
            return False, (
                f"❌ API key não configurada para {model_name}\n"
                f"Defina a variável de ambiente: {config['env_key']}"
            )
        
        return True, ""
    
    @staticmethod
    def create_llm(model_name: str = "gemini") -> Any:
        """
        Cria instância de LLM com validação completa
        
        Args:
            model_name: Nome do modelo ('gemini', 'gpt', 'claude')
        
        Returns:
            Instância de LLM (ChatGoogleGenerativeAI, ChatOpenAI, etc)
        
        Raises:
            ValueError: Se modelo inválido ou API key ausente
            RuntimeError: Se erro ao conectar com serviço
        
        Exemplo:
            >>> try:
            ...     llm = LLMFactory.create_llm("gemini")
            ...     response = llm.invoke("Hello")
            ... except ValueError as e:
            ...     print(f"Config error: {e}")
            ... except RuntimeError as e:
            ...     print(f"Runtime error: {e}")
        """
        logger.info(f"Criando instância LLM: {model_name}")
        
        # 1. Validar modelo
        valid, error_msg = LLMFactory.validate_model(model_name)
        if not valid:
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        config = MODEL_CONFIG[model_name]
        api_key = os.environ[config["env_key"]]
        
        try:
            # 2. Criar instância
            logger.info(f"Instanciando {config['class'].__name__}...")
            
            llm = config["class"](
                api_key=api_key,
                model=config["model"],
                temperature=config["temperature"]
            )
            
            # 3. Testar conexão com LLM
            logger.info(f"Testando conectividade com {model_name}...")
            test_response = llm.invoke("test")
            
            if not test_response:
                raise RuntimeError(
                    f"LLM {model_name} retornou resposta vazia"
                )
            
            logger.info(f"✅ LLM {model_name} ({config['model']}) inicializado com sucesso")
            return llm
        
        except ValueError as e:
            logger.error(f"Erro de validação: {e}")
            raise ValueError(f"Erro ao validar configuração de {model_name}: {e}")
        
        except RuntimeError as e:
            logger.error(f"Erro de runtime: {e}", exc_info=True)
            raise RuntimeError(
                f"❌ Erro ao conectar com {model_name}. "
                f"Verifique sua API key e conectividade.\n"
                f"Detalhes: {str(e)[:200]}"
            )
        
        except Exception as e:
            logger.error(f"Erro inesperado: {e}", exc_info=True)
            raise RuntimeError(
                f"❌ Erro inesperado ao inicializar {model_name}: {str(e)[:200]}"
            )
    
    @staticmethod
    def create_llm_with_fallback(
        primary_model: str = "gemini",
        fallback_model: str = "gpt"
    ) -> tuple[Any, str]:
        """
        Cria instância de LLM com fallback se modelo principal falhar
        
        Args:
            primary_model: Modelo preferido
            fallback_model: Modelo de fallback
        
        Returns:
            Tuple[LLM, str]: (instância LLM, nome do modelo usado)
        
        Raises:
            RuntimeError: Se todos os modelos falharem
        
        Exemplo:
            >>> llm, model_used = LLMFactory.create_llm_with_fallback()
            >>> print(f"Usando modelo: {model_used}")
        """
        logger.info(
            f"Tentando criar LLM com fallback: "
            f"principal={primary_model}, fallback={fallback_model}"
        )
        
        # Tentar modelo principal
        try:
            llm = LLMFactory.create_llm(primary_model)
            logger.info(f"✅ Usando modelo principal: {primary_model}")
            return llm, primary_model
        except Exception as e:
            logger.warning(
                f"Falha ao usar {primary_model}: {e}. "
                f"Tentando fallback: {fallback_model}"
            )
        
        # Tentar fallback
        try:
            llm = LLMFactory.create_llm(fallback_model)
            logger.warning(f"⚠️ Usando modelo fallback: {fallback_model}")
            return llm, fallback_model
        except Exception as e:
            logger.error(f"Falha ao usar fallback {fallback_model}: {e}")
        
        # Nenhum modelo disponível
        available = ", ".join(LLMFactory.get_available_models())
        raise RuntimeError(
            f"❌ Nenhum modelo LLM disponível. "
            f"Modelos testados: {primary_model}, {fallback_model}. "
            f"Modelos disponíveis: {available}"
        )
    
    @staticmethod
    def get_model_info(model_name: str = None) -> Dict[str, Any]:
        """
        Retorna informações sobre um modelo ou todos
        
        Args:
            model_name: Nome do modelo (None = todas)
        
        Returns:
            Dict com informações do modelo(s)
        
        Exemplo:
            >>> info = LLMFactory.get_model_info("gemini")
            >>> print(f"Modelo: {info['model']}")
            >>> print(f"Temperatura: {info['temperature']}")
        """
        if model_name:
            if model_name in MODEL_CONFIG:
                return MODEL_CONFIG[model_name]
            return {}
        
        # Retornar todos
        info = {}
        for name, config in MODEL_CONFIG.items():
            info[name] = {
                "model": config["model"],
                "temperature": config["temperature"],
                "description": config.get("description", ""),
                "configured": bool(os.environ.get(config["env_key"]))
            }
        
        return info
    
    @staticmethod
    def print_available_models():
        """Imprime informações sobre modelos disponíveis"""
        info = LLMFactory.get_model_info()
        
        print("\n" + "="*60)
        print("MODELOS LLM DISPONÍVEIS")
        print("="*60)
        
        for model_name, config in info.items():
            status = "✅ Configurado" if config["configured"] else "❌ Não configurado"
            print(f"\n{model_name.upper()}")
            print(f"  Modelo: {config['model']}")
            print(f"  Temperatura: {config['temperature']}")
            print(f"  Status: {status}")
            print(f"  Descrição: {config['description']}")
        
        print("\n" + "="*60 + "\n")


# Função helper para uso simples
def get_llm(model_name: str = "gemini") -> Any:
    """
    Helper simples para obter LLM
    
    Args:
        model_name: Nome do modelo
    
    Returns:
        Instância de LLM
    
    Raises:
        ValueError, RuntimeError: Se erro
    """
    return LLMFactory.create_llm(model_name)


if __name__ == "__main__":
    # Script de teste
    LLMFactory.print_available_models()
    
    try:
        llm = LLMFactory.create_llm("gemini")
        print("✅ LLM criado com sucesso")
    except Exception as e:
        print(f"❌ Erro: {e}")