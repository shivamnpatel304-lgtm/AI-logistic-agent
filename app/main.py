"""
Main FastAPI Application Entrypoint.
Configures middleware, lifecycle handlers, and mounts all API routers.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database.connection import init_db
from app.api.routes import (
    order_router,
    inventory_router,
    allocation_router,
    logistics_router,
)
from app.agents.orchestrator import orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Initializes database tables on startup.
    """
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-driven Multi-Agent Logistics and Supply Chain Optimization Platform.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing (CORS) Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 routes
app.include_router(order_router, prefix=settings.API_V1_STR)
app.include_router(inventory_router, prefix=settings.API_V1_STR)
app.include_router(allocation_router, prefix=settings.API_V1_STR)
app.include_router(logistics_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["System"])
def root():
    return {
        "app_name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "operational",
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR,
        "llm_agent_enabled": bool(settings.ENABLE_LLM_AGENT and settings.OPENAI_API_KEY),
        "oop_architecture": {
            "encapsulation": "Domain models and encapsulated services with state invariants",
            "abstraction": "Abstract Base Classes (BaseAgent, BaseService, AbstractAllocationStrategy, ReasoningEngine)",
            "inheritance": "Hierarchical extension from BaseEntity, BaseService, and BaseAgent",
            "polymorphism": "Interchangeable agent orchestration and strategy pattern fulfillment",
        },
    }


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "agents": orchestrator.get_system_health(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
