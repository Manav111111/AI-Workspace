"""Alembic migration for Phase 3: AI Employee Tools, Business Entities, Pending Actions & Audit Log

Revision ID: 005_agent_tools_and_business_entities
Revises: 004_ai_employee_knowledge_bases
Create Date: 2026-09-13 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "005_agent_tools_and_business_entities"
down_revision: Union[str, None] = "004_ai_employee_knowledge_bases"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. AI Employee Tool Assignment Table
    op.create_table(
        "ai_employee_tools",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("ai_employee_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ai_employee_id"], ["ai_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ai_employee_id", "tool_name", name="uq_ai_employee_tool"),
    )
    op.create_index("ix_ai_employee_tools_id", "ai_employee_tools", ["id"])
    op.create_index("ix_ai_employee_tools_company_id", "ai_employee_tools", ["company_id"])
    op.create_index("ix_ai_employee_tools_ai_employee_id", "ai_employee_tools", ["ai_employee_id"])
    op.create_index("ix_ai_employee_tools_tool_name", "ai_employee_tools", ["tool_name"])

    # 2. Pending Tool Action Table (Server-side confirmation lifecycle)
    op.create_table(
        "pending_tool_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("ai_employee_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("validated_arguments", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ai_employee_id"], ["ai_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pending_tool_actions_id", "pending_tool_actions", ["id"])
    op.create_index("ix_pending_tool_actions_company_id", "pending_tool_actions", ["company_id"])
    op.create_index("ix_pending_tool_actions_ai_employee_id", "pending_tool_actions", ["ai_employee_id"])
    op.create_index("ix_pending_tool_actions_conversation_id", "pending_tool_actions", ["conversation_id"])
    op.create_index("ix_pending_tool_actions_user_id", "pending_tool_actions", ["user_id"])
    op.create_index("ix_pending_tool_actions_status", "pending_tool_actions", ["status"])

    # 3. Orders Table
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.String(length=50), nullable=False),
        sa.Column("customer_identifier", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("total", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "order_number", name="uq_company_order_number"),
    )
    op.create_index("ix_orders_id", "orders", ["id"])
    op.create_index("ix_orders_company_id", "orders", ["company_id"])
    op.create_index("ix_orders_order_number", "orders", ["order_number"])
    op.create_index("ix_orders_customer_identifier", "orders", ["customer_identifier"])
    op.create_index("ix_orders_status", "orders", ["status"])

    # 4. Leads Table
    op.create_table(
        "leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("interest", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leads_id", "leads", ["id"])
    op.create_index("ix_leads_company_id", "leads", ["company_id"])
    op.create_index("ix_leads_email", "leads", ["email"])

    # 5. Support Tickets Table
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_number", sa.String(length=50), nullable=False),
        sa.Column("customer_email", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "ticket_number", name="uq_company_ticket_number"),
    )
    op.create_index("ix_support_tickets_id", "support_tickets", ["id"])
    op.create_index("ix_support_tickets_company_id", "support_tickets", ["company_id"])
    op.create_index("ix_support_tickets_ticket_number", "support_tickets", ["ticket_number"])
    op.create_index("ix_support_tickets_customer_email", "support_tickets", ["customer_email"])

    # 6. Tool Executions (Audit Log with Idempotency Constraint)
    op.create_table(
        "tool_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("ai_employee_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ai_employee_id"], ["ai_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "idempotency_key", name="uq_tool_execution_idempotency"),
    )
    op.create_index("ix_tool_executions_id", "tool_executions", ["id"])
    op.create_index("ix_tool_executions_company_id", "tool_executions", ["company_id"])
    op.create_index("ix_tool_executions_ai_employee_id", "tool_executions", ["ai_employee_id"])
    op.create_index("ix_tool_executions_conversation_id", "tool_executions", ["conversation_id"])
    op.create_index("ix_tool_executions_user_id", "tool_executions", ["user_id"])
    op.create_index("ix_tool_executions_tool_name", "tool_executions", ["tool_name"])
    op.create_index("ix_tool_executions_idempotency_key", "tool_executions", ["idempotency_key"])


def downgrade() -> None:
    op.drop_table("tool_executions")
    op.drop_table("support_tickets")
    op.drop_table("leads")
    op.drop_table("orders")
    op.drop_table("pending_tool_actions")
    op.drop_table("ai_employee_tools")
