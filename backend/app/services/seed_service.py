import logging
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.ai_employee import AIEmployee, AIEmployeeStatus
from app.models.ai_employee_knowledge_base import AIEmployeeKnowledgeBase
from app.models.ai_employee_tool import AIEmployeeTool
from app.models.business_entities import Order, OrderStatus, Product
from app.models.company import Company
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase, KnowledgeBaseStatus
from app.models.membership import Membership, MembershipRole
from app.models.user import User

logger = logging.getLogger("app.services.seed_service")

DEMO_EMAIL = "demo@avtaar.ai"
DEMO_PASSWORD = "Demo12345!"
DEMO_FULL_NAME = "Avtaar Demo Admin"
DEMO_COMPANY_NAME = "Avtaar Technologies Inc. (Demo Workspace)"
DEMO_COMPANY_SLUG = "avtaar-demo-workspace"


class SeedService:
    """Enterprise Seeder ensuring that the default Demo Account and its rich
    knowledge bases, AI Employees, and business entities are always available
    and resilient across container restarts.
    """

    @classmethod
    async def seed_demo_account(cls, session: AsyncSession) -> bool:
        """Checks if the demo account exists. If not, creates the full demo tenant."""
        stmt = select(User).where(User.email == DEMO_EMAIL)
        existing_user = (await session.execute(stmt)).scalar_one_or_none()
        if existing_user:
            logger.info("Demo account already initialized.")
            return False

        logger.info("Seeding Avtaar Demo Account and enterprise knowledge base...")

        # 1. Create Demo Company
        company = Company(
            id=uuid.uuid4(),
            name=DEMO_COMPANY_NAME,
            slug=DEMO_COMPANY_SLUG,
            is_active=True,
        )
        session.add(company)
        await session.flush()

        # 2. Create Demo User
        user = User(
            id=uuid.uuid4(),
            email=DEMO_EMAIL,
            hashed_password=get_password_hash(DEMO_PASSWORD),
            full_name=DEMO_FULL_NAME,
            is_active=True,
            is_superuser=True,
        )
        session.add(user)
        await session.flush()

        # 3. Create Owner Membership
        membership = Membership(
            id=uuid.uuid4(),
            user_id=user.id,
            company_id=company.id,
            role=MembershipRole.OWNER,
        )
        session.add(membership)
        await session.flush()

        # 4. Create Knowledge Bases
        kb_customer = KnowledgeBase(
            id=uuid.uuid4(),
            company_id=company.id,
            name="Customer Support & Product Guide",
            description="Official product documentation, pricing tiers, SLAs, and refund policies.",
            status=KnowledgeBaseStatus.ACTIVE,
        )
        kb_hr = KnowledgeBase(
            id=uuid.uuid4(),
            company_id=company.id,
            name="HR & Employee Handbook",
            description="Internal operational guidelines, leave policies, compensation, and benefits.",
            status=KnowledgeBaseStatus.ACTIVE,
        )
        session.add_all([kb_customer, kb_hr])
        await session.flush()

        # 5. Create Documents and Chunks for Customer KB
        doc_refund = Document(
            id=uuid.uuid4(),
            company_id=company.id,
            knowledge_base_id=kb_customer.id,
            filename="Refund_and_Billing_Policy.md",
            original_filename="Refund_and_Billing_Policy.md",
            file_type="markdown",
            mime_type="text/markdown",
            file_size=2048,
            storage_path="./uploads/demo_refund_policy.md",
            status=DocumentStatus.PROCESSED,
            document_metadata={"title": "Avtaar Refund & Billing Policy 2026", "author": "Finance Dept"},
        )
        session.add(doc_refund)
        await session.flush()

        chunk_refund_1 = DocumentChunk(
            id=uuid.uuid4(),
            company_id=company.id,
            knowledge_base_id=kb_customer.id,
            document_id=doc_refund.id,
            chunk_index=0,
            content="Avtaar Refund Policy: Customers are eligible for a 100% full refund within 30 days of initial subscription purchase if service uptime falls below 99.9% or if unsatisfied with performance. Refund requests are processed within 3 business days back to the original payment method.",
            token_count=45,
            chunk_metadata={"source": "Refund_and_Billing_Policy.md", "header_path": "Refund Policy > Eligibility", "page": 1},
        )
        chunk_refund_2 = DocumentChunk(
            id=uuid.uuid4(),
            company_id=company.id,
            knowledge_base_id=kb_customer.id,
            document_id=doc_refund.id,
            chunk_index=1,
            content="Pricing Tiers & Quotas: The Professional Plan is $49/month per AI Employee, including 50,000 monthly tokens and up to 5 custom knowledge bases. The Enterprise Plan is $499/month, offering unlimited knowledge bases, dedicated Qdrant vector isolation, custom LLM fine-tuning, and 24/7 dedicated support.",
            token_count=52,
            chunk_metadata={"source": "Refund_and_Billing_Policy.md", "header_path": "Pricing > Subscription Tiers", "page": 2},
        )
        session.add_all([chunk_refund_1, chunk_refund_2])
        await session.flush()

        # 6. Create Documents and Chunks for HR KB
        doc_hr = Document(
            id=uuid.uuid4(),
            company_id=company.id,
            knowledge_base_id=kb_hr.id,
            filename="HR_Employee_Handbook_2026.md",
            original_filename="HR_Employee_Handbook_2026.md",
            file_type="markdown",
            mime_type="text/markdown",
            file_size=3072,
            storage_path="./uploads/demo_hr_handbook.md",
            status=DocumentStatus.PROCESSED,
            document_metadata={"title": "HR Employee Handbook 2026", "author": "People Ops"},
        )
        session.add(doc_hr)
        await session.flush()

        chunk_hr_1 = DocumentChunk(
            id=uuid.uuid4(),
            company_id=company.id,
            knowledge_base_id=kb_hr.id,
            document_id=doc_hr.id,
            chunk_index=0,
            content="Annual Leave Policy: Full-time employees receive 25 days of paid annual leave per calendar year, accrued monthly at 2.08 days. Employees can carry over up to 5 unused leave days into the next calendar year. Leave requests exceeding 3 consecutive business days must be submitted at least 2 weeks in advance.",
            token_count=55,
            chunk_metadata={"source": "HR_Employee_Handbook_2026.md", "header_path": "Time Off > Annual Leave", "page": 1},
        )
        chunk_hr_2 = DocumentChunk(
            id=uuid.uuid4(),
            company_id=company.id,
            knowledge_base_id=kb_hr.id,
            document_id=doc_hr.id,
            chunk_index=1,
            content="Remote Work & Wellness Stipend: Employees are supported in flexible remote work. Each employee receives an annual $1,200 wellness and home office equipment stipend, reimbursable via the internal payroll portal upon receipt submission.",
            token_count=40,
            chunk_metadata={"source": "HR_Employee_Handbook_2026.md", "header_path": "Benefits > Remote Stipend", "page": 2},
        )
        session.add_all([chunk_hr_1, chunk_hr_2])
        await session.flush()

        # 7. Index in Qdrant Vector Cloud if configured
        try:
            from app.services.embeddings import EmbeddingService
            from app.services.qdrant_service import QdrantService
            emb_service = EmbeddingService()
            qdrant_service = QdrantService()

            # Ensure collections exist
            await qdrant_service.ensure_collection(kb_customer.id)
            await qdrant_service.ensure_collection(kb_hr.id)

            # Insert Customer chunks
            vectors_cust = await emb_service.embed_chunks([chunk_refund_1.content, chunk_refund_2.content])
            await qdrant_service.upsert_chunks(
                knowledge_base_id=kb_customer.id,
                chunks=[chunk_refund_1, chunk_refund_2],
                vectors=vectors_cust,
            )

            # Insert HR chunks
            vectors_hr = await emb_service.embed_chunks([chunk_hr_1.content, chunk_hr_2.content])
            await qdrant_service.upsert_chunks(
                knowledge_base_id=kb_hr.id,
                chunks=[chunk_hr_1, chunk_hr_2],
                vectors=vectors_hr,
            )
            logger.info("Demo knowledge chunks successfully indexed into Qdrant vector cloud.")
        except Exception as qe:
            logger.warning(f"Could not index demo chunks to Qdrant during seed: {qe}")

        # 8. Create AI Employees
        emp_maya = AIEmployee(
            id=uuid.uuid4(),
            company_id=company.id,
            name="Maya",
            role="AI Customer & Technical Specialist",
            description="Assists customers with product specifications, pricing, refund inquiries, and order lookup.",
            personality="Professional, authoritative, empathetic, concise",
            system_prompt="You are Maya, an enterprise AI specialist for Avtaar. Provide clear, empathetic, and factual answers strictly grounded in company documentation. Always cite references.",
            language="en",
            status=AIEmployeeStatus.ACTIVE,
            is_published=True,
            public_id="demo-maya-public",
            allowed_domains=["*"],
            widget_config={"primary_color": "#FF9D00", "theme": "dark", "welcome_message": "Hello! I am Maya, your AI specialist. How can I help you today?"},
            avatar_config={"enabled": False, "model_preset": "executive_sarah"},
            voice_config={"enabled": False, "voice_id": "alloy"},
        )

        emp_alex = AIEmployee(
            id=uuid.uuid4(),
            company_id=company.id,
            name="Alex",
            role="HR & Internal Operations Specialist",
            description="Assists employees with company handbook policies, leave requests, wellness benefits, and payroll questions.",
            personality="Warm, supportive, clear, structured",
            system_prompt="You are Alex, an internal HR AI specialist for Avtaar. Answer employee inquiries grounded in the HR Employee Handbook with exact policy citations.",
            language="en",
            status=AIEmployeeStatus.ACTIVE,
            is_published=False,
            allowed_domains=[],
            widget_config={},
            avatar_config={"enabled": False, "model_preset": "support_alex"},
            voice_config={"enabled": False, "voice_id": "echo"},
        )
        session.add_all([emp_maya, emp_alex])
        await session.flush()

        # 9. Assign Knowledge Bases to AI Employees
        rel_maya_kb = AIEmployeeKnowledgeBase(
            company_id=company.id,
            ai_employee_id=emp_maya.id,
            knowledge_base_id=kb_customer.id,
        )
        rel_alex_kb = AIEmployeeKnowledgeBase(
            company_id=company.id,
            ai_employee_id=emp_alex.id,
            knowledge_base_id=kb_hr.id,
        )
        session.add_all([rel_maya_kb, rel_alex_kb])

        # 10. Assign Tools to Maya
        tool_prod = AIEmployeeTool(
            company_id=company.id,
            ai_employee_id=emp_maya.id,
            tool_name="product_search",
        )
        tool_order = AIEmployeeTool(
            company_id=company.id,
            ai_employee_id=emp_maya.id,
            tool_name="order_lookup",
        )
        session.add_all([tool_prod, tool_order])
        await session.flush()

        # 11. Create Demo Business Data (Orders & Products) for live tool testing
        order_1 = Order(
            id=uuid.uuid4(),
            company_id=company.id,
            order_number="ORD-9001",
            customer_identifier="john.doe@example.com",
            status=OrderStatus.DELIVERED.value,
            items=[{"name": "Avtaar Professional Subscription", "qty": 1, "price": 49.0}],
            total=49.0,
        )
        order_2 = Order(
            id=uuid.uuid4(),
            company_id=company.id,
            order_number="ORD-9002",
            customer_identifier="sarah.smith@example.com",
            status=OrderStatus.PROCESSING.value,
            items=[{"name": "Avtaar Enterprise Suite", "qty": 1, "price": 499.0}],
            total=499.0,
        )
        session.add_all([order_1, order_2])

        await session.commit()
        logger.info(f"Demo account '{DEMO_EMAIL}' successfully created with company '{company.name}', 2 AI Employees (Maya & Alex), 2 Knowledge Bases, and demo order data.")
        return True
