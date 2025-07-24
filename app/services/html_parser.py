from bs4 import BeautifulSoup
from typing import List
from app.models.monitor_entities import MonitorArticle, MonitorArticleList


def parse_html(html_content: str) -> MonitorArticleList:
    """
    从 The Christian Science Monitor 的 HTML 内容中解析并提取文章列表。

    返回:
        MonitorArticleList: 包含文章列表的实体。
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    base_url = "https://www.csmonitor.com"

    article_elements = soup.find_all('li', attrs={'data-type': 'csm_article'})
    articles: List[MonitorArticle] = []

    for item in article_elements:
        link_tag = item.find('a', href=True)
        if not link_tag:
            continue

        relative_url = link_tag['href']
        url = base_url + relative_url if relative_url.startswith('/') else relative_url

        title = item.find('span', attrs={'data-field': 'title'})
        title_text = title.text.strip() if title else None

        summary = item.find('div', attrs={'data-field': 'summary'})
        summary_text = ' '.join(summary.text.strip().split()) if summary else None

        image_tag = item.find('img', src=True)
        image_src = image_tag['src'] if image_tag else None

        if title_text and url:
            articles.append(
                MonitorArticle(
                    url=url,
                    title=title_text,
                    summary=summary_text,
                    image_src=image_src
                )
            )

    return MonitorArticleList(articles=articles)