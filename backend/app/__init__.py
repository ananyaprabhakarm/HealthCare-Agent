import logging
import os
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes.chat import router as chat_router
from .routes.doctor import router as doctor_router


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Doctor Assistant MCP Backend")

    cors_origins = os.getenv("CORS_ORIGINS", "*")
    allowed_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins or ["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Middleware to log all requests
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        
        # Log incoming request
        logger.info(f"🔵 {request.method} {request.url.path} - Started")
        
        try:
            response = await call_next(request)
            
            # Calculate request duration
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                f"✅ {request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Duration: {duration:.2f}s"
            )
            
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"❌ {request.method} {request.url.path} - "
                f"Error: {str(e)} - "
                f"Duration: {duration:.2f}s"
            )
            raise
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"💥 Unhandled error on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
    app.include_router(doctor_router, prefix="/api/doctor", tags=["doctor"])
    
    logger.info("🚀 HealthCare Agent Backend initialized")
    
    return app





