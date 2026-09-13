import datetime
import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.membership import MembershipRole


class CompanyBase(BaseModel):
    name: str
    slug: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    is_active: Optional[bool] = None


class CompanyRead(CompanyBase):
    id: uuid.UUID
    slug: str
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class MembershipRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    company_id: uuid.UUID
    role: MembershipRole
    created_at: datetime.datetime
    company: Optional[CompanyRead] = None

    model_config = ConfigDict(from_attributes=True)


class MembershipCreate(BaseModel):
    user_email: str
    role: MembershipRole = MembershipRole.MEMBER
