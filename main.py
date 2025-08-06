from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os

from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router as api_router
from app.api.scheduler_routes import router as scheduler_router
from app.api.html_content_routes import router as html_content_router
from app.services.schedule_service import article_scheduler
from app.services.html_content_service import HTMLContentService
from utils.utils import timestamp_to_datetime


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源（生产环境应替换为前端域名）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法（GET/POST等）
    allow_headers=["*"],  # 允许所有请求头
)

# 创建数据目录（如果不存在）
os.makedirs(os.path.join('data', 'html'), exist_ok=True)
os.makedirs(os.path.join('data', 'images'), exist_ok=True)

# 挂载静态文件服务，用于提供图片等静态资源
app.mount("/data", StaticFiles(directory="data"), name="data")

# 设置Jinja2模板
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["timestamp_to_datetime"] = timestamp_to_datetime


@app.get("/")
async def home(request: Request):
    """网站首页，显示所有可用的文章列表"""
    html_service = HTMLContentService()
    articles = html_service.list_articles()

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "articles": articles, "count": len(articles)}
    )


# Include API routes
app.include_router(api_router)
app.include_router(scheduler_router)
app.include_router(html_content_router)  # 添加HTML内容路由

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)