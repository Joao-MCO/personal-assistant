"""
Configuração central do SQLAlchemy: engine, fábrica de sessões e a função
`init_db()` chamada uma vez na subida da aplicação (ver app/main.py).

Funciona com SQLite (default, zero configuração pra desenvolver — o arquivo
`cidinha.db` é criado sozinho na pasta de onde o processo roda) e com
Postgres em produção, só trocando DATABASE_URL no .env. O restante do código
(app/db/models.py, app/services/session_store.py, etc.) não faz nenhuma
suposição específica de dialeto, então migrar de um para o outro não exige
mudar mais nada além dessa variável de ambiente.
"""

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from utils.settings import WrappedSettings as Settings

logger = logging.getLogger(__name__)

Base = declarative_base()

# SQLite, por padrão, só permite uso pela thread que abriu a conexão --
# o Uvicorn atende requisições em threads diferentes, então esse
# connect_arg é necessário. Postgres/MySQL não usam (e ignoram) essa opção.
_is_sqlite = Settings.database_url.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(Settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency do FastAPI: abre uma sessão por requisição e garante o close no final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Cria as tabelas que ainda não existirem (idempotente -- não apaga nem
    recria as que já existem) e roda as seeds iniciais. Chamado uma vez no
    startup da aplicação.

    Isso cobre o "criar as tabelas" para quem está começando agora. Uma vez
    em produção com dado real, o caminho recomendado para MUDANÇAS de schema
    é Alembic (pasta migrations/ na raiz do projeto), não alterar os models
    e confiar só nesse create_all -- ver README.md.
    """
    from db import models  # noqa: F401  -- garante que todos os modelos registraram em Base.metadata

    Base.metadata.create_all(bind=engine)
    dialect = Settings.database_url.split("://")[0]
    logger.info(f"✅ Banco de dados inicializado (dialeto: {dialect})")

    from db.seed import seed_employees_from_json, seed_legacy_api_key

    db = SessionLocal()
    try:
        seed_employees_from_json(db)
        seed_legacy_api_key(db)
    finally:
        db.close()