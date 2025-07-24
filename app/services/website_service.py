from typing import Optional
from app.core.config import get_website_config
from app.models.http_entities import WebsiteResponse, HttpFetchResult, HtmlParseResult
from app.models.monitor_entities import MonitorArticleList
from app.services.article_extractor_service import extract_article_contents
from app.services.http_client import make_request
from app.services.html_parser import parse_html


async def fetch_website_content(
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
            fetch_result=fetch_result,  # 这里应该传递fetch_result而不是parse_result
            parse_result=MonitorArticleList(articles=None)  # 原始获取阶段还没有解析结果
        )

    except Exception as e:
        return WebsiteResponse.error_response(
            website=website,
            section=section,
            error=f"获取网站内容失败: {str(e)}"
        )


async def fetch_and_parse_website(
        website: str,
        section: str,
        timeout: Optional[int] = None
) -> WebsiteResponse:
    """
    获取并解析指定网站和板块的内容

    Args:
        website: 网站标识符（如 "csmonitor"）
        section: 板块标识符（如 "business"）
        timeout: 请求超时时间（秒），可选

    Returns:
        WebsiteResponse: 标准化的响应实体
    """
    response = await fetch_website_content(website, section, timeout)

    if not response.success:
        return response

    fetch_result = response.fetch_result
    if not fetch_result:
        return WebsiteResponse.error_response(
            website=website,
            section=section,
            error="获取结果为空",
            fetch_result=None
        )


    # 检查内容类型
    if not fetch_result.content_type or "text/html" not in fetch_result.content_type.lower():
        return WebsiteResponse.error_response(
            website=website,
            section=section,
            error=f"不支持的内容类型: {fetch_result.content_type}",
            fetch_result=fetch_result
        )

    # 检查内容
    if not isinstance(fetch_result.content, str):
        return WebsiteResponse.error_response(
            website=website,
            section=section,
            error="无法解析非文本内容",
            fetch_result=fetch_result
        )

    # 解析HTML内容
    try:
        parsed_data = parse_html(fetch_result.content)
        results = extract_article_contents(parsed_data)

        return WebsiteResponse.success_response(
            website=website,
            section=section,
            fetch_result=None,
            parse_result=parsed_data # 解析成功则不返回原始数据
        )
    except Exception as e:
        return WebsiteResponse.error_response(
            website=website,
            section=section,
            error=f"解析HTML内容失败: {str(e)}",
            fetch_result=fetch_result
        )