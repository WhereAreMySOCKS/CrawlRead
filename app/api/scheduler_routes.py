
from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.services.article.schedule_service import article_scheduler

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

@router.post("/start")
async def start_scheduler(background_tasks: BackgroundTasks):
    """
    手动启动调度器
    """
    try:
        background_tasks.add_task(article_scheduler.start)
        return {"message": "调度器启动命令已提交"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_scheduler(background_tasks: BackgroundTasks):
    """
    手动停止调度器
    """
    try:
        background_tasks.add_task(article_scheduler.shutdown)
        return {"message": "调度器停止命令已提交"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 可以扩展状态接口返回更详细的调度器状态
@router.get("/status")
async def get_scheduler_status():
    """
    获取调度器状态（扩展版）
    """
    return {
        "scheduler_running": article_scheduler.scheduler.running,
        "queue_size": len(article_scheduler._article_queue),
        "processed_count": len(article_scheduler._processed_articles),
        "current_index": article_scheduler._current_index,
        "next_run_time": str(article_scheduler.scheduler.get_job('daily_article_fetch').next_run_time)
            if article_scheduler.scheduler.get_job('daily_article_fetch') else None,
    }