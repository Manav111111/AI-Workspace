from typing import List
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import TenantContext, get_tenant_context
from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.models.ai_employee import AIEmployee
from app.models.ai_employee_tool import AIEmployeeTool
from app.schemas.tool import AssignEmployeeToolsRequest, ToolSummaryResponse
from app.services.agent.tool_registry import tool_registry

router = APIRouter(prefix="/tools", tags=["AI Employee Tools"])


@router.get("", response_model=List[ToolSummaryResponse], status_code=status.HTTP_200_OK)
async def list_available_tools(
    tenant: TenantContext = Depends(get_tenant_context),
) -> List[ToolSummaryResponse]:
    """Lists all available business tools registered in the platform catalog."""
    tools = tool_registry.list_available_tools()
    return [
        ToolSummaryResponse(
            name=t.name,
            description=t.description,
            permission=t.permission.value,
            input_schema=t.input_schema,
        )
        for t in tools
    ]


@router.get("/employees/{employee_id}", response_model=List[str], status_code=status.HTTP_200_OK)
async def get_employee_tools(
    employee_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    """Lists the names of tools assigned to a specific AI Employee."""
    # Verify employee belongs to tenant
    emp_stmt = select(AIEmployee).where(
        AIEmployee.id == employee_id,
        AIEmployee.company_id == tenant.company_id,
    )
    emp_res = await session.execute(emp_stmt)
    if not emp_res.scalar_one_or_none():
        raise NotFoundException("AI Employee not found")

    stmt = select(AIEmployeeTool.tool_name).where(
        AIEmployeeTool.ai_employee_id == employee_id,
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


@router.put("/employees/{employee_id}", response_model=List[str], status_code=status.HTTP_200_OK)
async def assign_employee_tools(
    employee_id: uuid.UUID,
    payload: AssignEmployeeToolsRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[str]:
    """Assigns or updates tools for an AI Employee, enforcing that only registered tools can be assigned."""
    emp_stmt = select(AIEmployee).where(
        AIEmployee.id == employee_id,
        AIEmployee.company_id == tenant.company_id,
    )
    emp_res = await session.execute(emp_stmt)
    if not emp_res.scalar_one_or_none():
        raise NotFoundException("AI Employee not found")

    # Validate tool names exist in registry
    registered_names = {t.name for t in tool_registry.list_available_tools()}
    valid_names = [name for name in set(payload.tool_names) if name in registered_names]

    # Atomically replace tool assignments
    await session.execute(
        delete(AIEmployeeTool).where(AIEmployeeTool.ai_employee_id == employee_id)
    )

    for name in valid_names:
        session.add(
            AIEmployeeTool(
                company_id=tenant.company_id,
                ai_employee_id=employee_id,
                tool_name=name,
            )
        )

    await session.commit()
    return valid_names
