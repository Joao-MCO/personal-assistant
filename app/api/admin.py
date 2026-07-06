"""
Endpoints administrativos: gestão de funcionários (contatos internos, antes
em app/assets/emails.json) e de clientes da API (chaves individuais e
revogáveis, no lugar de uma única API_KEY fixa).

Protegidos por um segredo separado (ADMIN_TOKEN, header X-Admin-Token) --
diferente do X-API-Key usado em /chat. A ideia é que só quem administra a
Cidinha (não qualquer cliente autorizado a conversar com ela) consiga criar
funcionários ou emitir/revogar chaves de API.

Sem ADMIN_TOKEN configurado no .env, estas rotas ficam DESATIVADAS por
completo (503) -- diferente do X-API-Key, que fica desabilitado (permissivo)
quando não configurado. Aqui o padrão seguro é "fechado por default", porque
o dano potencial de deixar isso aberto é maior (criar/revogar acesso à API).
"""

import hashlib
import logging
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session as DBSession

from api.schemas import (
    ApiClientCreate,
    ApiClientCreated,
    ApiClientOut,
    EmployeeCreate,
    EmployeeOut,
)
from db.base import get_db
from db.models import ApiClient, Employee
from utils.settings import WrappedSettings as Settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_HEADER = "X-Admin-Token"


async def verify_admin(x_admin_token: str = Header(default=None, alias=ADMIN_HEADER)):
    expected = Settings.admin_token
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="ADMIN_TOKEN não configurado no servidor — endpoints administrativos desativados.",
        )
    if x_admin_token != expected:
        raise HTTPException(status_code=401, detail="X-Admin-Token inválido ou ausente.")


# ---------------------------------------------------------------------------
# Funcionários (antes: app/assets/emails.json)
# ---------------------------------------------------------------------------

@router.get("/employees", response_model=list[EmployeeOut], dependencies=[Depends(verify_admin)])
async def list_employees(db: DBSession = Depends(get_db)):
    rows = db.query(Employee).order_by(Employee.nome).all()
    return [EmployeeOut(id=r.id, nome=r.nome, email=r.email, ativo=r.ativo) for r in rows]


@router.post("/employees", response_model=EmployeeOut, dependencies=[Depends(verify_admin)])
async def create_employee(payload: EmployeeCreate, db: DBSession = Depends(get_db)):
    if db.query(Employee).filter(Employee.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Já existe um funcionário com esse email.")
    row = Employee(nome=payload.nome, email=payload.email, ativo=True)
    db.add(row)
    db.commit()
    return EmployeeOut(id=row.id, nome=row.nome, email=row.email, ativo=row.ativo)


@router.delete("/employees/{employee_id}", response_model=EmployeeOut, dependencies=[Depends(verify_admin)])
async def deactivate_employee(employee_id: int, db: DBSession = Depends(get_db)):
    """Soft delete -- marca como inativo, mas mantém o histórico (mensagens antigas, por exemplo, referenciam o nome)."""
    row = db.query(Employee).filter(Employee.id == employee_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado.")
    row.ativo = False
    db.commit()
    return EmployeeOut(id=row.id, nome=row.nome, email=row.email, ativo=row.ativo)


# ---------------------------------------------------------------------------
# Clientes da API (antes: API_KEY única no .env)
# ---------------------------------------------------------------------------

@router.get("/api-clients", response_model=list[ApiClientOut], dependencies=[Depends(verify_admin)])
async def list_api_clients(db: DBSession = Depends(get_db)):
    rows = db.query(ApiClient).order_by(ApiClient.created_at.desc()).all()
    return [ApiClientOut(id=r.id, name=r.name, active=r.active) for r in rows]


@router.post("/api-clients", response_model=ApiClientCreated, dependencies=[Depends(verify_admin)])
async def create_api_client(payload: ApiClientCreate, db: DBSession = Depends(get_db)):
    """Gera uma nova chave. O valor em texto puro só aparece nesta resposta -- não fica recuperável depois."""
    plaintext_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(plaintext_key.encode()).hexdigest()
    row = ApiClient(name=payload.name, key_hash=key_hash, active=True)
    db.add(row)
    db.commit()
    return ApiClientCreated(id=row.id, name=row.name, api_key=plaintext_key)


@router.delete("/api-clients/{client_id}", response_model=ApiClientOut, dependencies=[Depends(verify_admin)])
async def revoke_api_client(client_id: int, db: DBSession = Depends(get_db)):
    row = db.query(ApiClient).filter(ApiClient.id == client_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    row.active = False
    db.commit()
    return ApiClientOut(id=row.id, name=row.name, active=row.active)