from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.auth import router as auth_router
from app.api.v1.citizens import router as citizens_router
from app.api.v1.officers import router as officers_router
from app.api.v1.operator import router as operator_router
from app.api.v1.admin import router as admin_router
from app.api.v1.devices import router as devices_router
from app.api.v1.health import router as health_router
from app.api.v1.telemetry import router as telemetry_router
from app.api.v1.analytics import router as analytics_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="CrowdShield Realtime Crowd Safety & Stampede Prevention Platform Backend API"
)

# CORS configuration for Web (Next.js) & Mobile (Expo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to explicit origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(citizens_router, prefix="/api/v1")
app.include_router(officers_router, prefix="/api/v1")
app.include_router(operator_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(devices_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(telemetry_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")



@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for Railway/Render native buildpack zero-downtime probes.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENV
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
