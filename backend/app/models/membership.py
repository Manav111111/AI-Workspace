import enum
import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Enum, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.company import Company


class MembershipRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class Membership(BaseModel):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_user_company_membership"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MembershipRole] = mapped_column(
        Enum(MembershipRole, native_enum=False, length=50),
        default=MembershipRole.MEMBER,
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="memberships")
    company: Mapped["Company"] = relationship("Company", back_populates="memberships")
