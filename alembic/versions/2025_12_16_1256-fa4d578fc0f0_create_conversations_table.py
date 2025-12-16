"""create_conversations_table

Revision ID: fa4d578fc0f0
Revises: 04008203f30b
Create Date: 2025-12-16 12:56:28.164723

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa4d578fc0f0'
down_revision: Union[str, Sequence[str], None] = '04008203f30b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('conversations',
        sa.Column('conversation_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('conversation_id')
    )
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_conversations_user_id', table_name='conversations')
    op.drop_table('conversations')
