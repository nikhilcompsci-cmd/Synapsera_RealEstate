"""create failed documents and processing checkpoints tables

Revision ID: 003
Revises: 002
Create Date: 2025-12-11 12:00:00.000000

Description:
    Creates tables for failed document tracking and recovery system:
    - failed_documents: Records failed uploads with error classification
    - processing_checkpoints: Stores intermediate processing results

Security:
    - Foreign key constraints with CASCADE delete
    - Enum constraints for error_type and status fields
    - Indexes for performance on common queries

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create failed_documents and processing_checkpoints tables.
    
    Failed Documents Table:
        Tracks documents that failed during ingestion with comprehensive
        error information for retry management and recovery operations.
    
    Processing Checkpoints Table:
        Stores intermediate processing results (extracted text, chunks,
        embeddings) to enable resume capability after failures.
    """
    
    # Create enums first (using DO block to handle if they already exist)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'error_type_enum') THEN
                CREATE TYPE error_type_enum AS ENUM (
                    'transient',
                    'permanent',
                    'user_fixable',
                    'system_issue',
                    'rate_limit',
                    'timeout',
                    'unknown'
                );
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'failure_status_enum') THEN
                CREATE TYPE failure_status_enum AS ENUM (
                    'retrying',
                    'permanently_failed',
                    'resolved',
                    'ignored'
                );
            END IF;
        END $$;
    """)
    
    # Create failed_documents table (using raw SQL to avoid enum creation conflicts)
    op.execute("""
        CREATE TABLE failed_documents (
            id SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            user_id INTEGER,
            filename VARCHAR(500) NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            error_type error_type_enum NOT NULL DEFAULT 'unknown',
            error_message TEXT NOT NULL,
            error_details TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            max_retries INTEGER NOT NULL DEFAULT 3,
            last_retry_at TIMESTAMPTZ,
            next_retry_at TIMESTAMPTZ,
            status failure_status_enum NOT NULL DEFAULT 'retrying',
            failed_stage VARCHAR(100),
            processing_duration DOUBLE PRECISION,
            task_id VARCHAR(255),
            resolution_notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            resolved_at TIMESTAMPTZ
        )
    """)
    
    # Create indexes for failed_documents
    # Index for querying by project
    op.create_index('idx_failed_documents_project_id', 'failed_documents', ['project_id'])
    
    # Index for querying by status
    op.create_index('idx_failed_documents_status', 'failed_documents', ['status'])
    
    # Index for querying by error type
    op.create_index('idx_failed_documents_error_type', 'failed_documents', ['error_type'])
    
    # Index for querying by created_at (for time-based queries)
    op.create_index('idx_failed_documents_created_at', 'failed_documents', ['created_at'])
    
    # Index for querying by task_id
    op.create_index('idx_failed_documents_task_id', 'failed_documents', ['task_id'])
    
    # Index for next_retry_at (for scheduled retry queries)
    op.create_index('idx_failed_documents_next_retry_at', 'failed_documents', ['next_retry_at'])
    
    # Composite indexes for common queries
    # Query failed documents pending retry
    op.create_index(
        'idx_failed_documents_retry_schedule',
        'failed_documents',
        ['status', 'next_retry_at']
    )
    
    # Query failed documents by project and status
    op.create_index(
        'idx_failed_documents_project_status',
        'failed_documents',
        ['project_id', 'status']
    )
    
    # Query recent failures for monitoring
    op.create_index(
        'idx_failed_documents_created_status',
        'failed_documents',
        ['created_at', 'status']
    )
    
    # Query by error type for analysis
    op.create_index(
        'idx_failed_documents_error_type_created',
        'failed_documents',
        ['error_type', 'created_at']
    )
    
    # Create processing_checkpoints table
    op.create_table(
        'processing_checkpoints',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_identifier', sa.String(length=255), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('stage', sa.String(length=50), nullable=False),
        sa.Column('checkpoint_data', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_identifier')
    )
    
    # Create indexes for processing_checkpoints
    op.create_index('idx_checkpoints_document_id', 'processing_checkpoints', ['document_identifier'])
    op.create_index('idx_checkpoints_project_id', 'processing_checkpoints', ['project_id'])
    op.create_index('idx_checkpoints_expires_at', 'processing_checkpoints', ['expires_at'])


def downgrade() -> None:
    """
    Drop failed_documents and processing_checkpoints tables.
    
    Warning:
        This will permanently delete all failed document records
        and processing checkpoints. Ensure backups exist before downgrading.
    """
    # Drop processing_checkpoints table and indexes
    op.drop_index('idx_checkpoints_expires_at', table_name='processing_checkpoints')
    op.drop_index('idx_checkpoints_project_id', table_name='processing_checkpoints')
    op.drop_index('idx_checkpoints_document_id', table_name='processing_checkpoints')
    op.drop_table('processing_checkpoints')
    
    # Drop failed_documents table and indexes
    op.drop_index('idx_failed_documents_error_type_created', table_name='failed_documents')
    op.drop_index('idx_failed_documents_created_status', table_name='failed_documents')
    op.drop_index('idx_failed_documents_project_status', table_name='failed_documents')
    op.drop_index('idx_failed_documents_retry_schedule', table_name='failed_documents')
    op.drop_index('idx_failed_documents_next_retry_at', table_name='failed_documents')
    op.drop_index('idx_failed_documents_task_id', table_name='failed_documents')
    op.drop_index('idx_failed_documents_created_at', table_name='failed_documents')
    op.drop_index('idx_failed_documents_error_type', table_name='failed_documents')
    op.drop_index('idx_failed_documents_status', table_name='failed_documents')
    op.drop_index('idx_failed_documents_project_id', table_name='failed_documents')
    op.drop_table('failed_documents')
    
    # Drop enums
    op.execute('DROP TYPE failure_status_enum')
    op.execute('DROP TYPE error_type_enum')
