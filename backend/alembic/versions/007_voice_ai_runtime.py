"""Add voice_sessions table and voice telemetry

Revision ID: 007_voice_ai_runtime
Revises: 006_public_ai_employee_runtime
Create Date: 2026-09-15 23:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '007_voice_ai_runtime'
down_revision = '006_public_ai_employee_runtime'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'voice_sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('ai_employee_id', sa.Uuid(), nullable=False),
        sa.Column('conversation_id', sa.Uuid(), nullable=False),
        sa.Column('public_session_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('input_audio_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('output_audio_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('stt_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tts_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('llm_input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('llm_output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('time_to_first_transcript_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('time_to_first_audio_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_latency_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('interruptions_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['ai_employee_id'], ['ai_employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['public_session_id'], ['public_chat_sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_voice_sessions_company_id'), 'voice_sessions', ['company_id'], unique=False)
    op.create_index(op.f('ix_voice_sessions_ai_employee_id'), 'voice_sessions', ['ai_employee_id'], unique=False)
    op.create_index(op.f('ix_voice_sessions_conversation_id'), 'voice_sessions', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_voice_sessions_public_session_id'), 'voice_sessions', ['public_session_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_voice_sessions_public_session_id'), table_name='voice_sessions')
    op.drop_index(op.f('ix_voice_sessions_conversation_id'), table_name='voice_sessions')
    op.drop_index(op.f('ix_voice_sessions_ai_employee_id'), table_name='voice_sessions')
    op.drop_index(op.f('ix_voice_sessions_company_id'), table_name='voice_sessions')
    op.drop_table('voice_sessions')
