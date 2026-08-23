"""portfolios

Revision ID: 9e0b7604ee6d
Revises: 9d17b4f6a8c2
Create Date: 2026-08-23 13:32:01.398305

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e0b7604ee6d'
down_revision: Union[str, None] = '9d17b4f6a8c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('portfolios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )

    # Every position that already exists (from before portfolios existed)
    # belongs to a single default portfolio -- this row IS the "rename the
    # existing one to TestPortfolio" ask, since there was no name before.
    # No explicit id: on Postgres that would insert without advancing the
    # identity sequence, so the next POST /api/portfolios would collide on
    # id=1. Resolve the id by name instead, after the insert.
    portfolios = sa.table('portfolios', sa.column('name', sa.String))
    op.bulk_insert(portfolios, [{'name': 'TestPortfolio'}])

    # SQLite can't add a populated table's column as NOT NULL in one step:
    # add nullable, backfill, then tighten.
    with op.batch_alter_table('positions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('portfolio_id', sa.Integer(), nullable=True))

    op.execute(
        "UPDATE positions SET portfolio_id = "
        "(SELECT id FROM portfolios WHERE name = 'TestPortfolio')"
    )

    with op.batch_alter_table('positions', schema=None) as batch_op:
        batch_op.alter_column('portfolio_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_index(batch_op.f('ix_positions_portfolio_id'), ['portfolio_id'], unique=False)
        batch_op.create_foreign_key('fk_positions_portfolio_id_portfolios', 'portfolios', ['portfolio_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('positions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_positions_portfolio_id_portfolios', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_positions_portfolio_id'))
        batch_op.drop_column('portfolio_id')

    op.drop_table('portfolios')
