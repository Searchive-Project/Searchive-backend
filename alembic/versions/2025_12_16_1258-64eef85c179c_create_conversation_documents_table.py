"""create_conversation_documents_table

Revision ID: 64eef85c179c
Revises: 4fabf753ebd1
Create Date: 2025-12-16 12:58:45.229914

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '64eef85c179c'
down_revision: Union[str, Sequence[str], None] = '4fabf753ebd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('conversation_documents',
        sa.Column('conversation_id', sa.BigInteger(), nullable=False),
        sa.Column('document_id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.conversation_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.document_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('conversation_id', 'document_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('conversation_documents')
