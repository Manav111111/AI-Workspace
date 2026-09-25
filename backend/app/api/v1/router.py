from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.companies import router as companies_router
from app.api.v1.ai_employees import router as ai_employees_router
from app.api.v1.knowledge_bases import router as knowledge_bases_router
from app.api.v1.documents import router as documents_router
from app.api.v1.conversations import router as conversations_router

from app.api.v1.tools import router as tools_router
from app.api.v1.business_data import router as business_data_router
from app.api.v1.public import router as public_router
from app.api.v1.voice import router as voice_router
from app.api.v1.evaluations import router as evaluations_router
from app.api.v1.observability import router as observability_router
from app.api.v1.playground import router as playground_router
from app.api.v1.usage import router as usage_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(companies_router)
api_router.include_router(ai_employees_router)
api_router.include_router(knowledge_bases_router)
api_router.include_router(documents_router)
api_router.include_router(conversations_router)
api_router.include_router(tools_router)
api_router.include_router(business_data_router)
api_router.include_router(public_router)
api_router.include_router(voice_router)
api_router.include_router(evaluations_router)
api_router.include_router(observability_router)
api_router.include_router(playground_router)
api_router.include_router(usage_router)


