"""Add onboarding fields to users

Revision ID: a7aec5b22bd9
Revises: b5b6539c590a
Create Date: 2026-05-10 13:40:59.062180

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7aec5b22bd9'
down_revision: Union[str, Sequence[str], None] = 'b5b6539c590a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('onboarding_step', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('temp_email', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'temp_email')
    op.drop_column('users', 'onboarding_step')
