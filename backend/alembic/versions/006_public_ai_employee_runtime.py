"""Alembic migration for Phase 4: Public AI Employee Runtime, Sessions & Usage Events

Revision ID: 006_public_ai_employee_runtime
Revises: 005_agent_tools_and_business_entities
Create Date: 2026-09-13 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "006_public_ai_employee_runtime"
down_revision: Union[str, None] = "005_agent_tools_and_business_entities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add Phase 4 columns to ai_employees
    op.add_column("ai_employees", sa.Column("public_id", sa.String(length=64), nullable=True))
    op.add_column("ai_employees", sa.Column("is_published", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("ai_employees", sa.Column("allowed_domains", sa.JSON(), server_default="[]", nullable=False))
    op.add_column("ai_employees", sa.Column("widget_config", sa.JSON(), server_default="{}", nullable=False))

    op.create_index("ix_ai_employees_public_id", "ai_employees", ["public_id"], unique=True)
    op.create_index("ix_ai_employees_is_published", "ai_employees", ["is_published"])

    # 2. Create public_chat_sessions table
    op.create_table(
        "public_chat_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("ai_employee_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("visitor_id", sa.String(length=100), nullable=True),
        sa.Column("origin_domain", sa.String(length=255), nullable=True),
        sa.Column("message_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ai_employee_id"], ["ai_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_public_chat_sessions_token_hash"),
    )
    op.create_index("ix_public_chat_sessions_id", "public_chat_sessions", ["id"])
    op.create_index("ix_public_chat_sessions_company_id", "public_chat_sessions", ["company_id"])
    op.create_index("ix_public_chat_sessions_ai_employee_id", "public_chat_sessions", ["ai_employee_id"])
    op.create_index("ix_public_chat_sessions_conversation_id", "public_chat_sessions", ["conversation_id"])
    op.create_index("ix_public_chat_sessions_token_hash", "public_chat_sessions", ["token_hash"])
    op.create_index("ix_public_chat_sessions_visitor_id", "public_chat_sessions", ["visitor_id"])

    # 3. Create public_usage_events table
    op.create_table(
        "public_usage_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("ai_employee_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("message_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("tool_call_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ai_employee_id"], ["ai_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["public_chat_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_public_usage_events_id", "public_usage_events", ["id"])
    op.create_index("ix_public_usage_events_company_id", "public_usage_events", ["company_id"])
    op.create_index("ix_public_usage_events_ai_employee_id", "public_usage_events", ["ai_employee_id"])
    op.create_index("ix_public_usage_events_session_id", "public_usage_events", ["session_id"])
    op.create_index("ix_public_usage_events_event_type", "public_usage_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("public_usage_events")
    op.drop_table("public_chat_sessions")
    op.drop_index("ix_ai_employees_is_published", table_name="ai_employees")
    op.drop_index("ix_ai_employees_public_id", table_name="ai_employees")
    op.drop_column("ai_employees", "widget_config")
    op.drop_column("ai_employees", "allowed_domains")
    op.drop_column("ai_employees", "is_published")
    op.drop_column("ai_employees", "public_id")
