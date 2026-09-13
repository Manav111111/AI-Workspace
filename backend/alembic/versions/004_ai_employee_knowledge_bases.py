"""Alembic migration for AI Employee Knowledge Base Association

Revision ID: 004_ai_employee_knowledge_bases
Revises: 003_conversations_and_messages
Create Date: 2026-09-13 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004_ai_employee_knowledge_bases"
down_revision: Union[str, None] = "003_conversations_and_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_employee_knowledge_bases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("ai_employee_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_base_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ai_employee_id"], ["ai_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ai_employee_id", "knowledge_base_id", name="uq_ai_employee_knowledge_base"),
    )
    op.create_index("ix_ai_employee_knowledge_bases_company_id", "ai_employee_knowledge_bases", ["company_id"])
    op.create_index("ix_ai_employee_knowledge_bases_ai_employee_id", "ai_employee_knowledge_bases", ["ai_employee_id"])
    op.create_index("ix_ai_employee_knowledge_bases_knowledge_base_id", "ai_employee_knowledge_bases", ["knowledge_base_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_employee_knowledge_bases_knowledge_base_id", table_name="ai_employee_knowledge_bases")
    op.drop_index("ix_ai_employee_knowledge_bases_ai_employee_id", table_name="ai_employee_knowledge_bases")
    op.drop_index("ix_ai_employee_knowledge_bases_company_id", table_name="ai_employee_knowledge_bases")
    op.drop_table("ai_employee_knowledge_bases")
