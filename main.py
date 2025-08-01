from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from app.api.endpoints import router as api_router
from app.services.schedule_service import article_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行 - 这里放置之前在 on_event("startup") 中的代码
    article_scheduler.start()

    yield  # 应用运行期间

    # 关闭时执行 - 这里放置之前在 on_event("shutdown") 中的代码
    article_scheduler.shutdown()


app = FastAPI(
    title="CrawlRead API",
    description="API for CrawlRead application",
    version="0.1.0",
    lifespan=lifespan  # 使用新的生命周期管理器
)


@app.get("/")
async def read_root():
    return {"message": "Hello World"}


# Include API routes
app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)