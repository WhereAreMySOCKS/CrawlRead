from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.models.monitor_entities import MonitorArticleList


class HttpFetchResult(BaseModel):
    """HTTP请求结果实体"""
    status_code: int
    content_type: str
    url: str
    headers: Optional[Dict[str, str]] = None
    content: Optional[Any] = None
    elapsed_time: Optional[float] = None
    error: Optional[str] = None


class HtmlParseResult(BaseModel):
    """HTML解析结果实体"""
    title: Optional[str] = None
    meta: Optional[Dict[str, str]] = None
    links: Optional[List[str]] = None
    structured_data: Optional[Dict[str, Any]] = None
    plain_text: Optional[str] = None


class WebsiteResponse(BaseModel):
    """网站内容响应实体"""
    success: bool
    website: str
    section: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    fetch_result: Optional[HttpFetchResult] = None
    parse_result: Optional[MonitorArticleList] = None

    @classmethod
    def success_response(
        cls,
        website: str,
        section: str,
        *,
        fetch_result: Optional[HttpFetchResult] = None,
        parse_result: MonitorArticleList
    ) -> "WebsiteResponse":
        return cls(
            success=True,
            website=website,
            section=section,
            fetch_result=fetch_result,   # None 时不返回
            parse_result=parse_result
        )

    @classmethod
    def error_response(cls, website: str, section: str, error: str,
                      fetch_result: Optional[HttpFetchResult] = None):
        return cls(
            success=False,
            website=website,
            section=section,
            fetch_result=fetch_result,
            error=error,
        )

