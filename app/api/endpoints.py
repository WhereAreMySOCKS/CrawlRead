from fastapi import APIRouter ,Path
from typing import Dict, Any, Optional, Coroutine

from app.models.http_entities import WebsiteResponse
from app.services.website_service import fetch_and_parse_website


router = APIRouter()

# Mock database
items_db = []


@router.get("/health", summary="服务健康检查", tags=["Utility"])
async def health_check() -> Dict[str, str]:
    return {"status": "ok"}

@router.get("/fetch-and-parse/{website}/{section}", tags=["Web Operations"])
async def fetch_and_parse_website_content(
    website: str = Path(..., description="网站标识符，如 csmonitor"),
    section: str = Path(..., description="板块标识符，如 business"),
    timeout: Optional[int] = None
) -> WebsiteResponse:
    """
    根据配置获取并解析指定网站和板块的内容
    """
    result = await fetch_and_parse_website(website, section, timeout)
    return result