# monitor_entities.py
from typing import List, Optional
from pydantic import BaseModel


class MonitorArticle(BaseModel):
    """单篇 Christian Science Monitor 文章"""
    url: str
    title: str
    summary: Optional[str] = None
    image_src: Optional[str] = None


class MonitorArticleList(BaseModel):
    """文章列表实体"""
    articles: Optional[List[MonitorArticle]]

class ArticleListResponse(BaseModel):
    """文章列表响应"""
    success: bool
    website: str
    section: str
    articles: Optional[List[MonitorArticle]] = None
    error: Optional[str] = None


class ArticleResponse(BaseModel):
    """单篇文章响应"""
    success: bool
    url: str
    title: Optional[str] = ""
    content: Optional[str] = ""
    error: Optional[str] = None