from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from app.services.article.html_content_service import HTMLContentService

router = APIRouter(
    prefix="/articles",
    tags=["articles"],
)

html_service = HTMLContentService()

@router.get("/", response_class=JSONResponse)
async def list_articles():
    """获取所有已保存的文章列表"""
    articles = html_service.list_articles()

    # 为每篇文章添加ID
    articles_with_id = [
        {
            "filename": article["filename"],
            "title": article.get("title", ""),
            "formatted_date": article.get("formatted_date", "")
        }
        for article in articles
    ]

    # 按日期倒序排序（最新在前）
    articles_with_id.sort(
        key=lambda x: x["formatted_date"],
        reverse=True
    )

    return {"articles": articles_with_id, "count": len(articles_with_id)}


@router.get("/view/{filename}", response_class=HTMLResponse)
async def view_article_by_name(filename: str):
    """通过文件名查看HTML文章内容"""
    try:
        # 获取所有文章
        articles = html_service.list_articles()

        # 查找匹配的文章
        found_filename = None
        for article in articles:
            if article["filename"] == filename:
                found_filename = article["filename"]
                break

        if not found_filename:
            raise HTTPException(status_code=404, detail=f"未找到文件名为 '{filename}' 的文章")

        # 获取文章内容
        content = html_service.get_article_content(found_filename)
        if not content:
            raise HTTPException(status_code=404, detail="文章内容读取失败")

        return content

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@router.get("/exists/{filename}")
async def check_article_exists_by_article_name(filename: str):
    articles = html_service.list_articles()

    for article in articles:
        if article["filename"] == filename:
            return {"exists": True, "filename": filename}

    return {"exists": False, "filename": filename}