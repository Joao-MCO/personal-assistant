import logging
import os

# Precisa ser setado antes de qualquer troca de 'code' por token OAuth: o
# Google às vezes devolve os escopos em formato/ordem levemente diferente do
# solicitado, e o oauthlib recusa a troca se não relaxarmos essa checagem.
# (Mesma linha que já existia no main.py antigo do Streamlit.)
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import admin, auth, chat
from db.base import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("google_auth_oauthlib").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cidinha - API SharkDev",
    description="API da assistente virtual executiva da SharkDev.",
    version="2.0.0",
)

# Em produção, troque "*" pelo(s) domínio(s) real(is) do seu frontend/cliente.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(admin.router)


@app.on_event("startup")
async def on_startup():
    """Cria as tabelas que não existirem e roda as seeds iniciais (idempotente)."""
    init_db()


@app.get("/health", tags=["health"])
async def health_check():
    """Checagem simples de disponibilidade (útil para load balancer / orquestrador)."""
    return {"status": "ok"}


if __name__ == "__main__":
    # Atalho para `python main.py` em desenvolvimento. Em produção, prefira
    # rodar via `uvicorn main:app` com um process manager (ver README.md).
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)