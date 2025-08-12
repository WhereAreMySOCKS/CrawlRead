from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.api_models import TranslationRequest, AnalyzeIn, AnalyzeOut
from app.services.llm.llm_service import LLMTextAnalysisService
from app.services.translation.translation_service import TranslationService

router = APIRouter(prefix="/external", tags=["external"])

@router.post("/trans")
async def translate(req: TranslationRequest):
    """
    检查请求中q的长短，如果单个单词，则调用开源词典；否则使用百度翻译
    """
    service = TranslationService()
    return await service.translate(req)

@router.post("/analyze", response_model=AnalyzeOut)
async def process_next_article(payload: AnalyzeIn):
    """
    根据输入文本长度自动选用 words/paragraph/fulltext 模板并调用大模型
    """
    svc = LLMTextAnalysisService()
    type, resp = await svc.analyze(payload.text)
    if resp.error:
        raise HTTPException(status_code=400, detail=resp.error)

    return AnalyzeOut(
        type = type,
        content=resp.content,
        prompt_tokens=resp.prompt_tokens,
        completion_tokens=resp.completion_tokens,
    )