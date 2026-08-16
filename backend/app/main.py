import os
import logging
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.api.v1.auth import router as auth_router
from app.api.v1.citizens import router as citizens_router
from app.api.v1.officers import router as router_officers
from app.api.v1.operator import router as operator_router
from app.api.v1.admin import router as admin_router
from app.api.v1.devices import router as devices_router
from app.api.v1.health import router as health_router, evaluate_system_readiness
from app.api.v1.telemetry import router as telemetry_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.realtime import router as realtime_router

from app.core.middleware import RequestCorrelationMiddleware
from app.services.async_persistence import AsyncPersistenceManager

# Configure File & Console Logging
abs_log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", settings.LOG_FILE_PATH))
os.makedirs(os.path.dirname(abs_log_path), exist_ok=True)

log_formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
)

root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

# Avoid duplicate handlers if re-imported
if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
    file_handler = RotatingFileHandler(
        abs_log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for graceful startup and shutdown.
    Ensures async persistence queues drain cleanly before shutdown.
    """
    logger = logging.getLogger("crowdshield.startup")
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} in '{settings.ENV}' environment.")
    
    # Start persistence manager
    persistence_mgr = AsyncPersistenceManager.get_instance()
    persistence_mgr.start()
    
    yield
    
    # Graceful Shutdown
    shutdown_logger = logging.getLogger("crowdshield.shutdown")
    shutdown_logger.info("Executing graceful application shutdown sequence...")
    persistence_mgr.shutdown(timeout=5.0)
    shutdown_logger.info("Shutdown sequence complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="CrowdShield Realtime Crowd Safety & Stampede Prevention Platform Backend API",
    lifespan=lifespan
)

app.add_middleware(RequestCorrelationMiddleware)

# CORS configuration for Web (Next.js) & Mobile (Expo)
cors_origins = settings.cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API v1 Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(citizens_router, prefix="/api/v1")
app.include_router(router_officers, prefix="/api/v1")
app.include_router(operator_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(devices_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(telemetry_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(realtime_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Lightweight liveness check endpoint.
    """
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENV
    }


@app.get("/readiness", tags=["Health"])
async def readiness_check(db: Session = Depends(get_db)):
    """
    Comprehensive readiness check endpoint.
    """
    return evaluate_system_readiness(db)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
