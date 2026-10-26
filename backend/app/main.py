
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import check_database_connection
from app.routes.tattoo_sessions import router as tattoo_sessions_router


app = FastAPI(
    title=settings.app_name,
    description=(
        "API para el seguimiento fotográfico de la cicatrización "
        "de tatuajes de Mari."
    ),
    version="0.3.0",
)

allowed_origins = [
    origin.strip()
    for origin in settings.frontend_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(tattoo_sessions_router)


@app.get("/", tags=["General"])
def root():
    return {
        "application": settings.app_name,
        "status": "running",
        "environment": settings.environment,
    }


@app.get("/health", tags=["General"])
def health():
    try:
        database_connected = check_database_connection()
    except Exception:
        database_connected = False

    if not database_connected:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "degraded",
                "database": "disconnected",
            },
        )

    return {
        "status": "ok",
        "service": "mari-tattoo-care-api",
        "database": "connected",
    }
