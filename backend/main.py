"""
GenAI Platform — FastAPI Application Factory.
Initializes the app, registers all routers, and sets up DB on startup.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.init_db import init_db
from backend.api.routes import health, projects, agent_config, chat, documents, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # --- Startup ---
    print("=" * 50)
    print("  GenAI Platform — Starting Up")
    print("=" * 50)
    await init_db()
    print("[App] All systems ready.")
    yield
    # --- Shutdown ---
    print("[App] Shutting down.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="GenAI Platform",
        description="A modular, config-driven, multi-project GenAI platform.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS configuration
    origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers under /api/v1 prefix
    api_prefix = "/api/v1"
    app.include_router(health.router, prefix=api_prefix)
    app.include_router(projects.router, prefix=api_prefix)
    app.include_router(agent_config.router, prefix=api_prefix)
    app.include_router(chat.router, prefix=api_prefix)
    app.include_router(documents.router, prefix=api_prefix)
    app.include_router(transactions.router, prefix=api_prefix)

    return app


# Create the app instance (used by uvicorn)
app = create_app()
