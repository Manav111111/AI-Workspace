"""Add AI Control Plane tables: trace_summaries, audit_events, playground_sessions, playground_messages, model_pricing_versions, usage_ledger_entries, usage_budgets

Revision ID: 008_ai_control_plane
Revises: 007_voice_ai_runtime
Create Date: 2026-09-25 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '008_ai_control_plane'
down_revision = '007_voice_ai_runtime'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Trace summaries
    op.create_table(
        'trace_summaries',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('ai_employee_id', sa.Uuid(), nullable=True),
        sa.Column('conversation_id', sa.Uuid(), nullable=True),
        sa.Column('trace_id', sa.String(length=64), nullable=False),
        sa.Column('request_type', sa.String(length=50), nullable=False, server_default='CHAT'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='SUCCESS'),
        sa.Column('total_latency_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('spans_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('spans_data', sa.JSON(), nullable=False),
        sa.Column('safe_metadata', sa.JSON(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['ai_employee_id'], ['ai_employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_trace_summaries_company_id'), 'trace_summaries', ['company_id'], unique=False)
    op.create_index(op.f('ix_trace_summaries_ai_employee_id'), 'trace_summaries', ['ai_employee_id'], unique=False)
    op.create_index(op.f('ix_trace_summaries_conversation_id'), 'trace_summaries', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_trace_summaries_trace_id'), 'trace_summaries', ['trace_id'], unique=False)
    op.create_index(op.f('ix_trace_summaries_request_type'), 'trace_summaries', ['request_type'], unique=False)
    op.create_index(op.f('ix_trace_summaries_status'), 'trace_summaries', ['status'], unique=False)

    # 2. Audit events
    op.create_table(
        'audit_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('actor_id', sa.Uuid(), nullable=True),
        sa.Column('ai_employee_id', sa.Uuid(), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('trace_id', sa.String(length=64), nullable=True),
        sa.Column('safe_metadata', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['ai_employee_id'], ['ai_employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_events_company_id'), 'audit_events', ['company_id'], unique=False)
    op.create_index(op.f('ix_audit_events_actor_id'), 'audit_events', ['actor_id'], unique=False)
    op.create_index(op.f('ix_audit_events_ai_employee_id'), 'audit_events', ['ai_employee_id'], unique=False)
    op.create_index(op.f('ix_audit_events_event_type'), 'audit_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_audit_events_resource_type'), 'audit_events', ['resource_type'], unique=False)
    op.create_index(op.f('ix_audit_events_trace_id'), 'audit_events', ['trace_id'], unique=False)

    # 3. Playground sessions
    op.create_table(
        'playground_sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('ai_employee_id', sa.Uuid(), nullable=False),
        sa.Column('session_name', sa.String(length=100), nullable=False, server_default='Playground Session'),
        sa.Column('config_snapshot', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='ACTIVE'),
        sa.ForeignKeyConstraint(['ai_employee_id'], ['ai_employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_playground_sessions_company_id'), 'playground_sessions', ['company_id'], unique=False)
    op.create_index(op.f('ix_playground_sessions_user_id'), 'playground_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_playground_sessions_ai_employee_id'), 'playground_sessions', ['ai_employee_id'], unique=False)
    op.create_index(op.f('ix_playground_sessions_status'), 'playground_sessions', ['status'], unique=False)

    # 4. Playground messages
    op.create_table(
        'playground_messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('citations', sa.JSON(), nullable=False),
        sa.Column('retrieval_debug', sa.JSON(), nullable=False),
        sa.Column('prompt_debug', sa.JSON(), nullable=False),
        sa.Column('trace_id', sa.String(length=64), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['playground_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_playground_messages_session_id'), 'playground_messages', ['session_id'], unique=False)
    op.create_index(op.f('ix_playground_messages_company_id'), 'playground_messages', ['company_id'], unique=False)
    op.create_index(op.f('ix_playground_messages_trace_id'), 'playground_messages', ['trace_id'], unique=False)

    # 5. Model pricing versions
    op.create_table(
        'model_pricing_versions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('version_tag', sa.String(length=50), nullable=False, server_default='2026-09-01'),
        sa.Column('input_price_per_million', sa.Numeric(precision=12, scale=6), nullable=False, server_default='0.075000'),
        sa.Column('output_price_per_million', sa.Numeric(precision=12, scale=6), nullable=False, server_default='0.300000'),
        sa.Column('cached_input_price_per_million', sa.Numeric(precision=12, scale=6), nullable=False, server_default='0.018750'),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='USD'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_model_pricing_versions_provider'), 'model_pricing_versions', ['provider'], unique=False)
    op.create_index(op.f('ix_model_pricing_versions_model'), 'model_pricing_versions', ['model'], unique=False)
    op.create_index(op.f('ix_model_pricing_versions_is_active'), 'model_pricing_versions', ['is_active'], unique=False)

    # 6. Usage ledger entries
    op.create_table(
        'usage_ledger_entries',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('ai_employee_id', sa.Uuid(), nullable=True),
        sa.Column('conversation_id', sa.Uuid(), nullable=True),
        sa.Column('trace_id', sa.String(length=64), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('operation_type', sa.String(length=50), nullable=False, server_default='LLM_GENERATION'),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cached_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('audio_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('estimated_cost', sa.Numeric(precision=12, scale=6), nullable=False, server_default='0.000000'),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='USD'),
        sa.Column('cost_status', sa.String(length=30), nullable=False, server_default='FINAL'),
        sa.Column('usage_source', sa.String(length=40), nullable=False, server_default='PROVIDER_REPORTED'),
        sa.Column('pricing_version_id', sa.String(length=50), nullable=True),
        sa.Column('idempotency_key', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['ai_employee_id'], ['ai_employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_usage_ledger_entries_company_id'), 'usage_ledger_entries', ['company_id'], unique=False)
    op.create_index(op.f('ix_usage_ledger_entries_ai_employee_id'), 'usage_ledger_entries', ['ai_employee_id'], unique=False)
    op.create_index(op.f('ix_usage_ledger_entries_conversation_id'), 'usage_ledger_entries', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_usage_ledger_entries_trace_id'), 'usage_ledger_entries', ['trace_id'], unique=False)
    op.create_index(op.f('ix_usage_ledger_entries_idempotency_key'), 'usage_ledger_entries', ['idempotency_key'], unique=False)

    # 7. Usage budgets
    op.create_table(
        'usage_budgets',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('ai_employee_id', sa.Uuid(), nullable=True),
        sa.Column('budget_name', sa.String(length=100), nullable=False, server_default='Monthly Budget'),
        sa.Column('limit_amount', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='USD'),
        sa.Column('period_type', sa.String(length=30), nullable=False, server_default='MONTHLY'),
        sa.Column('soft_limit_percent', sa.Float(), nullable=False, server_default='80.0'),
        sa.Column('hard_limit_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['ai_employee_id'], ['ai_employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_usage_budgets_company_id'), 'usage_budgets', ['company_id'], unique=False)
    op.create_index(op.f('ix_usage_budgets_ai_employee_id'), 'usage_budgets', ['ai_employee_id'], unique=False)


def downgrade() -> None:
    op.drop_table('usage_budgets')
    op.drop_table('usage_ledger_entries')
    op.drop_table('model_pricing_versions')
    op.drop_table('playground_messages')
    op.drop_table('playground_sessions')
    op.drop_table('audit_events')
    op.drop_table('trace_summaries')
