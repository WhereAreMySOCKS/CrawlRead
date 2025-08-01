from typing import Optional, List
from fastapi import APIRouter, Path, Query, BackgroundTasks
from app.models.http_entities import WebsiteResponse
from app.models.monitor_entities import ArticleListResponse, ArticleResponse
from app.services.schedule_service import article_scheduler
from app.services.website_service import WebsiteFetchService
from app.services.article_service import ArticleParserService, ArticleExtractorService
from app.services.storage_service import ArticleStorageService

router = APIRouter()

# 服务实例
website_service = WebsiteFetchService()
article_parser_service = ArticleParserService()
article_extractor_service = ArticleExtractorService(max_concurrent=10)
storage_service = ArticleStorageService()


@router.get("/fetch/{website}/{section}", tags=["Web Operations"], response_model=WebsiteResponse)
async def fetch_website_content(
        website: str = Path(..., description="网站标识符，如 csmonitor"),
        section: str = Path(..., description="板块标识符，如 business"),
        timeout: Optional[int] = Query(None, description="请求超时时间（秒）")
) -> WebsiteResponse:
    """
    根据配置获取指定网站和板块的内容，不包含解析步骤
    """
    return await website_service.fetch_content(website, section, timeout)


@router.get("/parse/{website}/{section}", tags=["Web Operations"], response_model=ArticleListResponse)
async def parse_article_list(
        website: str = Path(..., description="网站标识符，如 csmonitor"),
        section: str = Path(..., description="板块标识符，如 business"),
        timeout: Optional[int] = Query(None, description="请求超时时间（秒）")
) -> ArticleListResponse:
    """
    获取并解析指定网站和板块的文章列表
    """
    # 先获取内容
    fetch_response = await website_service.fetch_content(website, section, timeout)
    if not fetch_response.success:
        return ArticleListResponse(
            success=False,
            website=website,
            section=section,
            error=fetch_response.error,
            articles=None
        )

    # 解析文章列表
    return await article_parser_service.parse_article_list(
        website, section, fetch_response.fetch_result
    )


@router.get("/extract-article", tags=["Web Operations"], response_model=ArticleResponse)
async def extract_single_article(
        url: str = Query(..., description="文章URL"),
        save: bool = Query(False, description="是否保存到本地")
) -> ArticleResponse:
    """
    提取单篇文章的内容
    """
    result = await article_extractor_service.extract_single_article_by_url(url)

    if save and result.get('success'):
        await storage_service.save_article(result)

    return ArticleResponse(
        success=result.get('success', False),
        url=url,
        title=result.get('title', ''),
        content=result.get('content', ''),
        error=None if result.get('success', False) else "提取文章失败"
    )


@router.get("/extract-all/{website}/{section}", tags=["Web Operations"], response_model=ArticleListResponse)
async def extract_all_articles(
        website: str = Path(..., description="网站标识符，如 csmonitor"),
        section: str = Path(..., description="板块标识符，如 business"),
        timeout: Optional[int] = Query(None, description="请求超时时间（秒）"),
        save: bool = Query(False, description="是否保存到本地")
) -> ArticleListResponse:
    """
    获取、解析指定网站板块的文章列表，并提取所有文章内容
    """
    # 获取文章列表
    article_list_response = await parse_article_list(website, section, timeout)
    if not article_list_response.success:
        return article_list_response

    # 提取所有文章内容
    results = await article_extractor_service.extract_all_articles(article_list_response.articles)

    # 保存文章（如果需要）
    if save:
        background_tasks = BackgroundTasks()
        for result in results:
            if result.get('success'):
                background_tasks.add_task(storage_service.save_article, result)

    # 更新文章列表中的内容
    for i, article in enumerate(article_list_response.articles):
        if i < len(results):
            article.content = results[i].get('content')
            article.extracted = results[i].get('success', False)

    return article_list_response


@router.post("/save-article", tags=["Storage Operations"])
async def save_article_to_storage(article: ArticleResponse) -> dict:
    """
    保存单篇文章到本地存储
    """
    result = await storage_service.save_article({
        'url': article.url,
        'title': article.title,
        'content': article.content,
        'success': article.success
    })

    return {"success": result, "message": "文章已保存" if result else "保存失败"}

# router = APIRouter(prefix="/scheduler", tags=["Scheduler"])

@router.post("/fetch-now")
async def trigger_article_fetch(background_tasks: BackgroundTasks):
    """
    手动触发文章列表获取任务
    """
    background_tasks.add_task(article_scheduler.fetch_article_list)
    return {"message": "文章获取任务已加入队列"}

@router.post("/process-next")
async def process_next_article(background_tasks: BackgroundTasks):
    """
    手动触发处理下一篇文章
    """
    background_tasks.add_task(article_scheduler.process_next_article)
    return {"message": "文章处理任务已加入队列"}

@router.get("/status")
async def get_scheduler_status():
    """
    获取调度器状态
    """
    return {
        "queue_size": len(article_scheduler._article_queue),
        "processed_count": len(article_scheduler._processed_articles),
        "current_index": article_scheduler._current_index,
        "fetching_active": article_scheduler._fetching_active,
        "scheduler_running": article_scheduler.scheduler.running
    }