from typing import Optional
from app.core.config import get_website_config
from app.models.http_entities import WebsiteResponse
from app.models.monitor_entities import MonitorArticleList
from app.services.http_client import make_request


class WebsiteFetchService:
    """
    负责从网站获取原始内容的服务
    """

    async def fetch_content(
            self,
            website: str,
            section: str,
            timeout: Optional[int] = None
    ) -> WebsiteResponse:
        """
        根据配置获取指定网站和板块的内容

        Args:
            website: 网站标识符（如 "csmonitor"）
            section: 板块标识符（如 "business"）
            timeout: 请求超时时间（秒），可选

        Returns:
            WebsiteResponse: 标准化的响应实体
        """
        try:
            config = get_website_config(website, section)
            if not config:
                return WebsiteResponse.error_response(
                    website=website,
                    section=section,
                    error=f"未找到 {website}/{section} 的配置"
                )

            fetch_result = await make_request(
                url=config["url"],
                headers=config.get("headers"),
                cookies=config.get("cookies"),
                timeout=timeout or config.get("timeout")
            )

            # 检查是否有错误
            if fetch_result.error:
                return WebsiteResponse.error_response(
                    website=website,
                    section=section,
                    error=fetch_result.error,
                    fetch_result=fetch_result
                )

            return WebsiteResponse.success_response(
                website=website,
                section=section,
                fetch_result=fetch_result,
                parse_result=MonitorArticleList(articles=None)  # 原始获取阶段还没有解析结果
            )

        except Exception as e:
            return WebsiteResponse.error_response(
                website=website,
                section=section,
                error=f"获取网站内容失败: {str(e)}"
            )