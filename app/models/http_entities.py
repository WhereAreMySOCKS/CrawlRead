from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.models.monitor_entities import MonitorArticleList


class FetchResult(BaseModel):
    """HTTP请求的结果"""
    status_code: Optional[int] = None
    url: Optional[str] = None
    content: Optional[str] = None
    content_type: Optional[str] = None
    error: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    elapsed_time: Optional[float] = None


class WebsiteResponse(BaseModel):
    """网站内容获取响应"""
    success: bool
    website: str
    section: str
    error: Optional[str] = None
    fetch_result: Optional[FetchResult] = None
    parse_result: Optional[MonitorArticleList] = None

    @classmethod
    def success_response(cls, website: str, section: str, fetch_result: Optional[FetchResult] = None,
                         parse_result: Optional[MonitorArticleList] = None) -> 'WebsiteResponse':
        """创建成功响应"""
        return cls(
            success=True,
            website=website,
            section=section,
            fetch_result=fetch_result,
            parse_result=parse_result
        )

    @classmethod
    def error_response(cls, website: str, section: str, error: str,
                       fetch_result: Optional[FetchResult] = None) -> 'WebsiteResponse':
        """创建错误响应"""
        return cls(
            success=False,
            website=website,
            section=section,
            error=error,
            fetch_result=fetch_result,
            parse_result=None
        )
