import pytest
import uuid
from qdrant_client import QdrantClient
from app.core.exceptions import ValidationException
from app.models.ai_employee import AIEmployeeStatus
from app.models.company import Company
from app.models.knowledge_base import KnowledgeBase, KnowledgeBaseStatus
from app.schemas.ai_employee import AIEmployeeCreate, AIEmployeeUpdate
from app.services.ai_employee import AIEmployeeService
from app.services.conversation import ConversationService
from app.services.conversation_engine import ConversationEngine
from app.services.llm.mock_provider import MockLLMProvider
from app.services.qdrant_service import QdrantService
from app.services.retrieval import RetrievalService


async def create_test_company(db_session, name="Acme Corp") -> Company:
    company = Company(name=name, slug=f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)
    return company


@pytest.mark.asyncio
async def test_assign_knowledge_bases_to_ai_employee(db_session):
    """Verify that an AI Employee can be created and assigned multiple knowledge bases."""
    company = await create_test_company(db_session, "Nexus Tech")
    company_id = company.id

    # 1. Create two Knowledge Bases
    kb1 = KnowledgeBase(
        company_id=company_id,
        name="Company General",
        description="General guidelines",
        status=KnowledgeBaseStatus.ACTIVE,
    )
    kb2 = KnowledgeBase(
        company_id=company_id,
        name="Engineering Docs",
        description="Technical specifications",
        status=KnowledgeBaseStatus.ACTIVE,
    )
    db_session.add_all([kb1, kb2])
    await db_session.commit()
    await db_session.refresh(kb1)
    await db_session.refresh(kb2)

    # 2. Create AI Employee assigned to both KBs
    service = AIEmployeeService(db_session)
    create_dto = AIEmployeeCreate(
        name="Alex - AI Engineer",
        role="AI Engineer",
        description="Assists with engineering questions",
        personality="Analytical and concise",
        language="en",
        status=AIEmployeeStatus.ACTIVE,
        knowledge_base_ids=[kb1.id, kb2.id],
    )
    employee = await service.create_employee(company_id=company_id, data=create_dto)

    assert employee.id is not None
    assert len(employee.knowledge_bases) == 2
    assigned_ids = {kb.id for kb in employee.knowledge_bases}
    assert kb1.id in assigned_ids
    assert kb2.id in assigned_ids

    # 3. Update employee: remove kb2, keep only kb1
    update_dto = AIEmployeeUpdate(knowledge_base_ids=[kb1.id])
    updated = await service.update_employee(
        company_id=company_id, employee_id=employee.id, data=update_dto
    )
    assert len(updated.knowledge_bases) == 1
    assert updated.knowledge_bases[0].id == kb1.id


@pytest.mark.asyncio
async def test_cross_tenant_knowledge_base_assignment_rejected(db_session):
    """Verify that a company CANNOT assign another company's knowledge base to its AI Employee."""
    company1 = await create_test_company(db_session, "Company One")
    company2 = await create_test_company(db_session, "Company Two")

    # KB belonging strictly to company 2
    kb_company_2 = KnowledgeBase(
        company_id=company2.id,
        name="Company 2 Secret KB",
        status=KnowledgeBaseStatus.ACTIVE,
    )
    db_session.add(kb_company_2)
    await db_session.commit()
    await db_session.refresh(kb_company_2)

    service = AIEmployeeService(db_session)
    create_dto = AIEmployeeCreate(
        name="Intruder Bot",
        role="Spy",
        knowledge_base_ids=[kb_company_2.id],
    )

    # Attempt to assign company 2's KB to company 1's AI Employee must fail
    with pytest.raises(ValidationException):
        await service.create_employee(company_id=company1.id, data=create_dto)


@pytest.mark.asyncio
async def test_scoped_retrieval_by_assigned_knowledge_bases(db_session):
    """Verify that ConversationEngine strictly scopes vector retrieval to the AI Employee's assigned KBs."""
    company = await create_test_company(db_session, "Enterprise Corp")
    company_id = company.id
    qdrant = QdrantService(client=QdrantClient(":memory:"))

    # 1. Create KB A (HR) and KB B (Tech)
    kb_hr = KnowledgeBase(company_id=company_id, name="HR Policies", status=KnowledgeBaseStatus.ACTIVE)
    kb_tech = KnowledgeBase(company_id=company_id, name="Tech Guide", status=KnowledgeBaseStatus.ACTIVE)
    db_session.add_all([kb_hr, kb_tech])
    await db_session.commit()
    await db_session.refresh(kb_hr)
    await db_session.refresh(kb_tech)

    # 2. Ingest mock vectors into Qdrant for both KBs
    doc_hr_id = uuid.uuid4()
    doc_tech_id = uuid.uuid4()
    chunk_hr_id = uuid.uuid4()
    chunk_tech_id = uuid.uuid4()

    qdrant.upsert_chunks(
        company_id=company_id,
        knowledge_base_id=kb_hr.id,
        document_id=doc_hr_id,
        chunk_records=[
            {
                "id": chunk_hr_id,
                "chunk_index": 0,
                "content": "HR Policy: Annual vacation allowance is 25 paid leave days.",
                "token_count": 12,
                "chunk_metadata": {"source": "HR_Handbook.pdf", "page_number": 1},
            }
        ],
        embeddings=[[0.05] * 384],
    )

    qdrant.upsert_chunks(
        company_id=company_id,
        knowledge_base_id=kb_tech.id,
        document_id=doc_tech_id,
        chunk_records=[
            {
                "id": chunk_tech_id,
                "chunk_index": 0,
                "content": "Tech Architecture: Backend is powered by FastAPI and Qdrant vector database.",
                "token_count": 14,
                "chunk_metadata": {"source": "Architecture.md", "page_number": 1},
            }
        ],
        embeddings=[[0.05] * 384],
    )

    # 3. Create an AI Employee assigned ONLY to KB HR
    service = AIEmployeeService(db_session)
    employee_hr = await service.create_employee(
        company_id=company_id,
        data=AIEmployeeCreate(
            name="Sarah HR",
            role="HR Representative",
            knowledge_base_ids=[kb_hr.id],  # ONLY HR!
        ),
    )

    # 4. Create conversation and send query asking about both HR and Tech
    conv_service = ConversationService(db_session)
    conversation = await conv_service.create_conversation(
        company_id=company_id,
        ai_employee_id=employee_hr.id,
        title="Leave and Architecture Policy",
    )

    engine = ConversationEngine(
        session=db_session,
        llm_provider=MockLLMProvider(),
        retrieval_service=RetrievalService(qdrant_service=qdrant),
    )

    response = await engine.respond(
        company_id=company_id,
        conversation_id=conversation.id,
        user_query="Tell me about our annual leave days and backend architecture.",
    )

    # Verify retrieval metadata: ONLY KB HR was searched!
    retrieval_meta = response.retrieval_metadata
    assert retrieval_meta["assigned_kbs_count"] == 1
    assert str(kb_hr.id) in retrieval_meta["assigned_kb_ids"]
    assert str(kb_tech.id) not in retrieval_meta["assigned_kb_ids"]

    # Verify returned citations strictly belong to KB HR, NEVER to KB Tech
    for cit in response.citations:
        assert cit["knowledge_base_id"] == str(kb_hr.id)
        assert cit["knowledge_base_id"] != str(kb_tech.id)


@pytest.mark.asyncio
async def test_zero_knowledge_ai_employee_skips_retrieval(db_session):
    """Verify that an AI Employee with 0 assigned KBs cleanly skips retrieval and does not leak data."""
    company = await create_test_company(db_session, "Solo Corp")
    company_id = company.id

    service = AIEmployeeService(db_session)
    employee_persona = await service.create_employee(
        company_id=company_id,
        data=AIEmployeeCreate(
            name="General Bot",
            role="General Greeter",
            system_prompt="You greet users politely.",
            knowledge_base_ids=[],  # Zero KBs!
        ),
    )

    conv_service = ConversationService(db_session)
    conversation = await conv_service.create_conversation(
        company_id=company_id,
        ai_employee_id=employee_persona.id,
        title="Greeting",
    )

    engine = ConversationEngine(
        session=db_session,
        llm_provider=MockLLMProvider(),
    )

    response = await engine.respond(
        company_id=company_id,
        conversation_id=conversation.id,
        user_query="What confidential data do you have?",
    )

    assert response.retrieval_metadata["retrieval_skipped"] is True
    assert response.retrieval_metadata["assigned_kbs_count"] == 0
    assert len(response.citations) == 0
