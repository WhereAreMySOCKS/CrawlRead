from fastapi import APIRouter, BackgroundTasks, Query

from app.models.api_models import TranslationRequest
from app.services.translation_service import TranslationService

router = APIRouter(prefix="/external", tags=["external"])

@router.post("/trans")
async def translate(req: TranslationRequest):
    """
    检查请求中q的长短，如果单个单词，则调用开源词典；否则使用百度翻译
    """
    service = TranslationService()
    return await service.translate(req)

@router.post("/analyze")
async def process_next_article(background_tasks: BackgroundTasks):
    """
    调用大模型接口
    """
    return

