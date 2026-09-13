import datetime
from typing import Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class AIEmployeeTool(Base):
    """Many-to-many relationship assigning specific capabilities/tools to an AI Employee.
    Enforces that an AI Employee can ONLY invoke tools explicitly assigned to it.
    """
    __tablename__ = "ai_employee_tools"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    ai_employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    # Relationships
    ai_employee = relationship("AIEmployee", back_populates="assigned_tools")

    __table_args__ = (
        UniqueConstraint(
            "ai_employee_id",
            "tool_name",
            name="uq_ai_employee_tool",
        ),
    )
