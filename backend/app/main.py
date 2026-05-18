import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.services.scheduler import scheduler, load_active_reminders
from app.routers import auth, chat, reminders, ws

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    logger.info("Starting up...")
    await init_db()
    scheduler.start()
    await load_active_reminders()
    logger.info("Scheduler started and reminders loaded")
    yield
    # 关闭
    logger.info("Shutting down...")
    scheduler.shutdown()


app = FastAPI(
    title="Life Assistant API",
    description="生活助手后端API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - 允许所有来源（生产环境应限制）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(reminders.router)
app.include_router(ws.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "life-assistant"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
