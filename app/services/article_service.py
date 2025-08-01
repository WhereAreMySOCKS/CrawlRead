from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlparse
from app.models.http_entities import FetchResult
from app.models.monitor_entities import MonitorArticleList, MonitorArticle, ArticleListResponse
from app.services.article_extractor_service import ArticleExtractor
from app.services.html_parser import parse_html


class ArticleParserService:
    """
    负责解析HTML内容，提取文章列表
    """

    def _normalize_url(self, base_url: str, relative_url: str) -> str:
        """
        将相对URL转换为绝对URL

        Args:
            base_url: 基础URL（板块URL）
            relative_url: 相对URL或绝对URL

        Returns:
            标准化的绝对URL
        """
        # 处理相对URL
        if not relative_url.startswith(('http://', 'https://')):
            return urljoin(base_url, relative_url)
        return relative_url

    async def parse_article_list(
            self,
            website: str,
            section: str,
            fetch_result: Optional[FetchResult] = None
    ) -> ArticleListResponse:
        """
        解析HTML内容，提取文章列表

        Args:
            website: 网站标识符
            section: 板块标识符
            fetch_result: 获取的网站内容结果

        Returns:
            ArticleListResponse: 包含文章列表的响应

        """
        if not fetch_result:
            return ArticleListResponse(
                success=False,
                website=website,
                section=section,
                error="获取结果为空",
                articles=None
            )

        # 检查内容类型
        if not fetch_result.content_type or "text/html" not in fetch_result.content_type.lower():
            return ArticleListResponse(
                success=False,
                website=website,
                section=section,
                error=f"不支持的内容类型: {fetch_result.content_type}",
                articles=None
            )

        # 检查内容
        if not isinstance(fetch_result.content, str):
            return ArticleListResponse(
                success=False,
                website=website,
                section=section,
                error="无法解析非文本内容",
                articles=None
            )

        # 解析HTML内容
        try:
            article_list = parse_html(fetch_result.content, -1)

            # 对所有文章URL进行标准化处理
            for article in article_list.articles:
                if article.url:
                    article.url = self._normalize_url(fetch_result.url, article.url)

            return ArticleListResponse(
                success=True,
                website=website,
                section=section,
                articles=article_list.articles
            )
        except Exception as e:
            return ArticleListResponse(
                success=False,
                website=website,
                section=section,
                error=f"解析HTML内容失败: {str(e)}",
                articles=None
            )


class ArticleExtractorService:
    """
    负责提取文章内容的服务
    """

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.extractor = ArticleExtractor(max_concurrent=max_concurrent)

    async def extract_single_article_by_url(self, url: str) -> Dict[str, Any]:
        """
        从URL提取单篇文章内容

        Args:
            url: 文章URL

        Returns:
            Dict: 包含提取结果的字典
        """
        dummy_article = MonitorArticle(url=url, title="")
        return await self.extractor.extract_single_article(dummy_article)

    async def extract_all_articles(self, articles: List[MonitorArticle]) -> List[Dict[str, Any]]:
        """
        批量提取文章内容

        Args:
            articles: 文章对象列表

        Returns:
            List[Dict]: 提取结果列表
        """
        if not articles:
            return []

        article_list = MonitorArticleList(articles=articles)
        return await self.extractor.extract_all(article_list)