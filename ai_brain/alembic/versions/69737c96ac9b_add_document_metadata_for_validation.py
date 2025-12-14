"""add_document_metadata_for_validation

Revision ID: 69737c96ac9b
Revises: 003
Create Date: 2025-12-11 22:50:13.792547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69737c96ac9b'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add validation_metadata JSON column to documents table
    op.add_column('documents', sa.Column('validation_metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove validation_metadata column
    op.drop_column('documents', 'validation_metadata')
