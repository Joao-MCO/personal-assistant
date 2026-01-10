import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    gemini = {
        "api_key": os.getenv("GEMINI_API_KEY"),
        "model": os.getenv("GEMINI_MODEL"),
        "embedding": os.getenv("GEMINI_EMBEDDING_MODEL")
    }

    maritaca = {
        "api_key": os.getenv("MARITACA_API_KEY"),
        "model": os.getenv("MARITACA_MODEL")
    }

    claude = {
        "api_key": os.getenv("CLAUDE_API_KEY"),
        "model": os.getenv("CLAUDE_MODEL")
    }

    chroma = {
        "api_key": os.getenv("CHROMA_API_KEY"),
        "tenant": os.getenv("CHROMA_TENANT"),
        "database": os.getenv("CHROMA_DATABASE"),
        "host": os.getenv("CHROMA_HOST")
    }

    gnews_api_key = os.getenv("GNEWS_API_KEY")
    max_tokens = os.getenv("MAX_TOKENS")
    temperature = os.getenv("TEMPERATURE")