"""add employee roles and permissions

Revision ID: 3802b49550fe
Revises: badeccad6677
Create Date: 2026-07-08 01:31:53.863832

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3802b49550fe'
down_revision: Union[str, Sequence[str], None] = 'badeccad6677'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('employee_tool_grants',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('tool_name', sa.String(), nullable=False),
        sa.Column('granted', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'tool_name', name='uq_employee_tool')
    )
    op.create_index(op.f('ix_employee_tool_grants_employee_id'), 'employee_tool_grants', ['employee_id'], unique=False)

    # batch_alter_table: necessário porque o SQLite não suporta ALTER TABLE
    # ADD CONSTRAINT / ADD COLUMN NOT NULL diretamente -- o Alembic recria a
    # tabela por baixo dos panos nesse modo. No Postgres funciona igual (via
    # ALTER TABLE normal), então a migração é portável entre os dois.
    #
    # server_default='member' é essencial aqui: a coluna é NOT NULL e a
    # tabela `employees` já tem linhas (da seed inicial) -- sem um default,
    # o ALTER TABLE falharia por não saber que valor colocar nas linhas
    # existentes.
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.add_column(sa.Column('role', sa.String(), nullable=False, server_default='member'))

    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('employee_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_sessions_employee_id'), ['employee_id'], unique=False)
        batch_op.create_foreign_key('fk_sessions_employee_id', 'employees', ['employee_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_sessions_employee_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_sessions_employee_id'))
        batch_op.drop_column('employee_id')

    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.drop_column('role')

    op.drop_index(op.f('ix_employee_tool_grants_employee_id'), table_name='employee_tool_grants')
    op.drop_table('employee_tool_grants')
