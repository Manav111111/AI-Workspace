from typing import List, Optional
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent.models import ToolContext
from app.services.agent.tools.product_search import ProductSearchTool
from app.services.retrieval import RetrievalService, RetrievedChunk


class MockScopedRetrievalService(RetrievalService):
    """Mock Retrieval Service that records which knowledge base IDs were queried."""
    def __init__(self):
        self.last_queried_kb_ids = []

    async def retrieve(
        self,
        company_id: uuid.UUID,
        query: str,
        knowledge_base_ids: Optional[List[uuid.UUID]] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        self.last_queried_kb_ids = knowledge_base_ids or []
        kb_id = (knowledge_base_ids[0] if knowledge_base_ids else uuid.uuid4())
        return [
            RetrievedChunk(
                chunk_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                knowledge_base_id=kb_id,
                text="The Pro Developer Laptop features 64GB RAM and 2TB SSD.",
                score=0.92,
                source="hardware_specs.pdf",
                page_number=1,
                header_path="Hardware > Laptops",
            )
        ]


@pytest.mark.asyncio
async def test_product_search_strictly_inherits_assigned_kbs(db_session: AsyncSession):
    """Verify that ProductSearchTool queries Qdrant strictly with the assigned knowledge base IDs."""
    company_id = uuid.uuid4()
    emp_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    eng_kb_id = uuid.uuid4()
    prod_kb_id = uuid.uuid4()

    mock_retrieval = MockScopedRetrievalService()
    tool = ProductSearchTool(retrieval_service=mock_retrieval)

    # Employee assigned only Engineering & Product KBs
    context = ToolContext(
        company_id=company_id,
        ai_employee_id=emp_id,
        conversation_id=conv_id,
        assigned_kb_ids=[eng_kb_id, prod_kb_id],
    )

    res = await tool.execute(
        context=context,
        arguments={"query": "laptop"},
        session=db_session,
    )

    assert res.success is True
    assert res.data is not None
    assert len(res.data["products"]) == 1
    # Verify retrieval service was called with the exact assigned KBs
    assert set(mock_retrieval.last_queried_kb_ids) == {eng_kb_id, prod_kb_id}


@pytest.mark.asyncio
async def test_product_search_zero_assigned_kbs_returns_empty(db_session: AsyncSession):
    """Verify that if an AI Employee has 0 assigned KBs, ProductSearchTool bypasses search completely."""
    company_id = uuid.uuid4()
    mock_retrieval = MockScopedRetrievalService()
    tool = ProductSearchTool(retrieval_service=mock_retrieval)

    # 0 assigned knowledge bases
    context = ToolContext(
        company_id=company_id,
        ai_employee_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        assigned_kb_ids=[],
    )

    res = await tool.execute(
        context=context,
        arguments={"query": "laptop"},
        session=db_session,
    )

    assert res.success is True
    assert len(res.data["products"]) == 0
    # Did not invoke retrieval
    assert len(mock_retrieval.last_queried_kb_ids) == 0
