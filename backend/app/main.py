import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db, redis as redis_module, minio as minio_module
from app.health import router as health_router
from app.auth import router as auth_router
from app.users import router as users_router
from app.submissions import router as submissions_router
from app.websocket import router as websocket_router
from app.portfolio import router as portfolio_router
from app.problems import router as problems_router
from app.terminal import router as terminal_router
from app.community import router as community_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== ProofForge API starting up ===")
    await db.init_pool()
    await redis_module.init_redis()
    minio_module.init_minio()
    minio_module.ensure_buckets()
    logger.info("=== All services ready ===")
    yield
    logger.info("=== ProofForge API shutting down ===")
    await db.close_pool()
    await redis_module.close_redis()


app = FastAPI(
    title="ProofForge API",
    version="0.1.0",
    description="AI-powered developer simulation platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "ws://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router.router, prefix="/api/v1")
app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(users_router.router, prefix="/api/v1")
app.include_router(submissions_router.router, prefix="/api/v1")
app.include_router(websocket_router.router, prefix="/api/v1")
app.include_router(portfolio_router.router, prefix="/api/v1")
app.include_router(problems_router.router, prefix="/api/v1")
app.include_router(terminal_router.router, prefix="/api/v1")
app.include_router(community_router.router, prefix="/api/v1")
