"""transactions portfolio_id

Revision ID: 7f3a1c9e5d21
Revises: 9e0b7604ee6d
Create Date: 2026-08-23 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f3a1c9e5d21'
down_revision: Union[str, None] = '9e0b7604ee6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite can't add a populated table's column as NOT NULL in one step:
    # add nullable, backfill, then tighten (same pattern as 9e0b7604ee6d).
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('portfolio_id', sa.Integer(), nullable=True))

    # Best-effort backfill: if every existing position for a transaction's
    # asset belongs to a single portfolio, attribute the transaction there.
    op.execute(
        "UPDATE transactions SET portfolio_id = ("
        "  SELECT p.portfolio_id FROM positions p"
        "  WHERE p.asset_id = transactions.asset_id"
        "  GROUP BY p.asset_id"
        "  HAVING COUNT(DISTINCT p.portfolio_id) = 1"
        ")"
    )
    # Anything left ambiguous (asset held in >1 portfolio) or without a
    # matching position falls back to the oldest portfolio.
    op.execute(
        "UPDATE transactions SET portfolio_id = (SELECT MIN(id) FROM portfolios) "
        "WHERE portfolio_id IS NULL"
    )

    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.alter_column('portfolio_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_index(batch_op.f('ix_transactions_portfolio_id'), ['portfolio_id'], unique=False)
        batch_op.create_foreign_key('fk_transactions_portfolio_id_portfolios', 'portfolios', ['portfolio_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_transactions_portfolio_id_portfolios', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_transactions_portfolio_id'))
        batch_op.drop_column('portfolio_id')
