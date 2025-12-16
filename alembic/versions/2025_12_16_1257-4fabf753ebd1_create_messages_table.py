"""create_messages_table

Revision ID: 4fabf753ebd1
Revises: fa4d578fc0f0
Create Date: 2025-12-16 12:57:44.666362

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4fabf753ebd1'
down_revision: Union[str, Sequence[str], None] = 'fa4d578fc0f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('messages',
        sa.Column('message_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.BigInteger(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.conversation_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('message_id')
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_messages_conversation_id', table_name='messages')
    op.drop_table('messages')
