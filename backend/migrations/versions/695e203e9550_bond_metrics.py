"""bond metrics

Revision ID: 695e203e9550
Revises: 7f3a1c9e5d21
Create Date: 2026-08-28 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '695e203e9550'
down_revision: Union[str, None] = '7f3a1c9e5d21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # All nullable -- same "legitimately absent for some assets" pattern as
    # the equity fundamentals columns (a stock has no TIR, a bond has no P/E).
    with op.batch_alter_table('fundamentals', schema=None) as batch_op:
        batch_op.add_column(sa.Column('bond_tir', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('bond_tem', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('bond_tna', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('bond_modified_duration', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('bond_parity', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('bond_days_to_coupon', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('fundamentals', schema=None) as batch_op:
        batch_op.drop_column('bond_days_to_coupon')
        batch_op.drop_column('bond_parity')
        batch_op.drop_column('bond_modified_duration')
        batch_op.drop_column('bond_tna')
        batch_op.drop_column('bond_tem')
        batch_op.drop_column('bond_tir')
