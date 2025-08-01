from fastapi import APIRouter, BackgroundTasks
from app.services.schedule_service import article_scheduler

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])

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