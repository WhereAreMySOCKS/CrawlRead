from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os

from app.services.html_content_service import HTMLContentService

router = APIRouter(
    prefix="/articles",
    tags=["articles"],
)

# 创建服务实例
html_service = HTMLContentService()


@router.get("/", response_class=JSONResponse)
async def list_articles():
    """获取所有已保存的文章列表"""
    articles = html_service.list_articles()
    return {"articles": articles, "count": len(articles)}


@router.get("/view/{filename}", response_class=HTMLResponse)
async def view_article(filename: str):
    """直接查看HTML文章内容"""
    # 安全检查，防止目录遍历攻击
    if "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="文件名无效")

    # 确保文件名以.html结尾
    if not filename.endswith('.html'):
        filename += '.html'

    content = html_service.get_article_content(filename)
    if not content:
        raise HTTPException(status_code=404, detail="文章未找到")

    return content


@router.get("/exists/{filename}")
async def check_article_exists(filename: str):
    """检查文章是否存在"""
    # 安全检查
    if "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="文件名无效")

    # 确保文件名以.html结尾
    if not filename.endswith('.html'):
        filename += '.html'

    exists = html_service.article_exists(filename)
    return {"exists": exists, "filename": filename}