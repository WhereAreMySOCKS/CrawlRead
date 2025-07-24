from typing import List, Dict, Any
from app.models.monitor_entities import MonitorArticleList, MonitorArticle
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse
from app.core.config import get_website_config


def extract_article_contents(article_list: MonitorArticleList) -> List[Dict[str, Any]]:
    """
    提取 MonitorArticle 列表中每篇文章的正文内容

    Args:
        article_list: 包含 MonitorArticle 的列表实体

    Returns:
        List[Dict]，每个元素包含：
        {
            "url": str,
            "title": str,
            "content": str 或 None,
            "error": str 或 None
        }
    """
    results = []

    for article in article_list.articles:
        result = {
            "url": article.url,
            "title": article.title,
            "content": None,
            "error": None
        }

        try:
            parsed_url = urlparse(article.url)
            domain = parsed_url.netloc

            # 简单域名映射
            if "csmonitor.com" in domain:
                website = "csmonitor"
            else:
                result["error"] = f"不支持的域名: {domain}"
                results.append(result)
                continue

            # 动态板块推断（可扩展）
            path_parts = parsed_url.path.strip("/").split("/")
            if "World" in path_parts:
                section = "world"
            elif "USA" in path_parts:
                section = "usa"
            else:
                section = "business"

            config = get_website_config(website, section)
            headers = config.get("headers", {})
            cookies = config.get("cookies", {})

            resp = requests.get(article.url, headers=headers, cookies=cookies, timeout=10)
            if resp.status_code != 200:
                result["error"] = f"HTTP {resp.status_code}"
                results.append(result)
                continue

            soup = BeautifulSoup(resp.text, 'html.parser')
            body = soup.find('div', class_='article-body') or \
                   soup.find('section', {'itemprop': 'articleBody'}) or \
                   soup.find('div', {'id': 'content'})

            if not body:
                result["error"] = "正文提取失败"
                results.append(result)
                continue

            paragraphs = [p.get_text(strip=True) for p in body.find_all('p')]
            result["content"] = "\n".join(paragraphs)

        except Exception as e:
            result["error"] = str(e)

        results.append(result)

    return results
