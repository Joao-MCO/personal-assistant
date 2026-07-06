import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Caminho absoluto da pasta "app/assets", calculado a partir deste arquivo
# (utils/ -> app/ -> assets/). Independe de onde o processo é iniciado.
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def get_employees_from_json() -> list:
    """
    Lê a lista de funcionários direto de emails.json. Usada SÓ pela seed
    inicial do banco (db/seed.py), na primeira vez que a tabela `employees`
    sobe vazia -- depois disso, a tabela é a fonte da verdade e este JSON
    não é mais consultado em tempo de execução.
    """
    try:
        with open(ASSETS_DIR / "emails.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar emails.json (utils/files.py): {e}")
        return []


def get_emails(agent: bool = False):
    """
    Lista de funcionários da SharkDev, agora lida da tabela `employees`
    (antes: direto de emails.json). Import feito dentro da função para
    evitar import circular com db/base.py -> db/models.py -> ... -> utils.

    Mesma assinatura/retorno de antes: quem já chamava get_emails() em
    agent.py ou api/auth.py não precisa mudar nada.
    """
    from db.base import SessionLocal
    from db.models import Employee

    emails_list = []
    db = SessionLocal()
    try:
        rows = db.query(Employee).filter(Employee.ativo == True).all()  # noqa: E712
        emails_list = [{"nome": r.nome, "email": r.email} for r in rows]
    except Exception as e:
        logger.error(f"Erro ao carregar employees do banco (utils/files.py): {e}")
    finally:
        db.close()

    if agent:
        return json.dumps(emails_list, ensure_ascii=False).replace("{", "{{").replace("}", "}}")
    return emails_list