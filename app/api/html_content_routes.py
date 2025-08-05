from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
import hashlib

from app.services.html_content_service import HTMLContentService

router = APIRouter(
    prefix="/articles",
    tags=["articles"],
)

html_service = HTMLContentService()


def generate_article_id(filename: str) -> str:
    """根据文件名生成唯一的文章ID"""
    return hashlib.md5(filename.encode('utf-8')).hexdigest()[:12]


@router.get("/", response_class=JSONResponse)
async def list_articles():
    """获取所有已保存的文章列表"""
    articles = html_service.list_articles()
    # 为每篇文章添加ID
    articles_with_id = []
    for article in articles:
        article_data = {
            "id": generate_article_id(article["filename"]),
            "filename": article["filename"],
            "title": article.get("title", ""),
            "formatted_date": article.get("'formatted_date'", "")
        }
        articles_with_id.append(article_data)

    return {"articles": articles_with_id, "count": len(articles_with_id)}


@router.get("/view/{article_id}", response_class=HTMLResponse)
async def view_article_by_id(article_id: str):
    """通过文章ID查看HTML文章内容"""
    # 根据ID找到对应的文件名
    articles = html_service.list_articles()
    filename = None

    for article in articles:
        if generate_article_id(article["filename"]) == article_id:
            filename = article["filename"]
            break

    if not filename:
        raise HTTPException(status_code=404, detail="文章未找到")

    content = html_service.get_article_content(filename)
    if not content:
        raise HTTPException(status_code=404, detail="文章内容读取失败")

    return content


@router.get("/exists/{article_id}")
async def check_article_exists_by_id(article_id: str):
    """通过文章ID检查文章是否存在"""
    articles = html_service.list_articles()

    for article in articles:
        if generate_article_id(article["filename"]) == article_id:
            return {"exists": True, "article_id": article_id, "filename": article["filename"]}

    return {"exists": False, "article_id": article_id}