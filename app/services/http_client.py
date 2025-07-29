import httpx
from typing import Dict, Any, Optional

from app.models.http_entities import HttpFetchResult


async def make_request(
        url: str,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
) -> HttpFetchResult:
    """
    发送HTTP GET请求并返回响应内容

    Args:
        url: 请求的URL
        headers: 请求头
        cookies: Cookie信息
        timeout: 请求超时时间（秒），默认为30秒

    Returns:
        HttpFetchResult: 包含响应信息的实体
    """
    try:
        # 设置默认超时时间为30秒
        timeout_value = timeout or 30

        async with httpx.AsyncClient(timeout=timeout_value) as client:
            response = await client.get(
                url,
                headers=headers,
                cookies=cookies,
                follow_redirects=True
            )

            # 确保响应成功
            response.raise_for_status()

            # 尝试解析为JSON，如果失败则返回文本内容
            try:
                content = response.json()
            except:
                content = response.text

            return HttpFetchResult(
                status_code=response.status_code,
                content_type=response.headers.get("content-type", ""),
                url=url,
                headers=dict(response.headers),
                content=content,
                elapsed_time=response.elapsed.total_seconds() if response.elapsed else None
            )

    except httpx.HTTPStatusError as e:
        return HttpFetchResult(
            status_code=e.response.status_code,
            content_type=e.response.headers.get("content-type", ""),
            url=url,
            headers=dict(e.response.headers),
            content=e.response.text,
            error=f"HTTP错误: {e.response.status_code}"
        )

    except httpx.RequestError as e:
        return HttpFetchResult(
            status_code=400,
            content_type="",
            url=url,
            error=f"请求错误: {str(e)}"
        )

    except Exception as e:
        return HttpFetchResult(
            status_code=400,
            content_type="",
            url=url,
            error=f"未知错误: {str(e)}"
        )