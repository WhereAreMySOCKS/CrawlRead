import asyncio
import datetime
import os
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag
from app.models.monitor_entities import MonitorArticleList, MonitorArticle
from app.services.http_client import make_request
from utils.logger_util import logger


class ArticleExtractor:
    """
    一个用于从 The Christian Science Monitor 网站提取和清理文章内容的类。
    """

    def __init__(self, max_concurrent: int = 5, save_html: bool = True):
        self.max_concurrent = max_concurrent
        self.save_html = save_html
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36'
        }
        self.base_url = "https://www.csmonitor.com/"

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """清理字符串，使其成为有效的文件名。"""
        # 移除无效字符
        name = re.sub(r'[\\/*?:"<>|]', '_', name)
        # 避免文件名过长
        return name[:100]

    async def extract_body_from_html(self, html_content: str) -> str:
        """
        从给定的HTML内容中提取、清理并格式化文章正文。
        增强版本，支持完整的文章结构和元数据提取。
        """
        soup = BeautifulSoup(html_content, 'lxml')

        # 提取文章元数据
        article_metadata = self._extract_article_metadata(soup)

        # 1. 定位文章主容器
        article_container = soup.find('div', class_='eza-body')

        # 如果找不到主容器，尝试其他选择器
        if not article_container:
            alternative_selectors = [
                'div.prem',
                'article',
                'div[class*="story-content"]',
                'div[class*="article-body"]'
            ]

            for selector in alternative_selectors:
                article_container = soup.select_one(selector)
                if article_container:
                    logger.info(f"使用备选选择器找到文章容器: {selector}")
                    break

        if not article_container:
            logger.warning("在HTML中未找到任何文章正文容器")
            return self._create_html_document(
                "错误：在此页面未找到指定的文章正文容器。",
                title=article_metadata.get('title', 'Error')
            )

        # 2. 预处理：移除所有不需要的元素
        unwanted_selectors = [
            'aside',
            '.story-half',
            '#paywall',
            '.inline-messenger',
            '.ezp-inbody-promo',
            '#inbody-related-stories',
            'script',
            'style',
            '.advertisement',
            '.ad-wrapper',
            '.share-tools',
            '.newsletter-banner'
        ]

        for selector in unwanted_selectors:
            for element in article_container.select(selector):
                element.decompose()

        # 3. 提取文章主图
        main_image_html = self._extract_main_image(soup)

        # 4. 按顺序遍历并提取所有有效的内容元素
        content_elements = article_container.find_all(['p', 'h2', 'h3', 'h4', 'figure', 'blockquote', 'ul', 'ol'],
                                                      recursive=True)
        output_html_parts = []

        # 添加文章头部信息
        if article_metadata:
            header_html = self._create_article_header(article_metadata)
            output_html_parts.append(header_html)

        # 添加主图
        if main_image_html:
            output_html_parts.append(main_image_html)

        processed_paragraphs = set()  # 避免重复处理段落

        for element in content_elements:
            # 跳过已处理的元素
            if id(element) in processed_paragraphs:
                continue

            # 处理段落
            if element.name == 'p':
                text = element.get_text(strip=True)
                # 过滤掉空的、太短的或包含无关信息的段落
                if (text and len(text) > 20 and
                        "This story was reported by" not in text and
                        "©" not in text and
                        not text.startswith("ADVERTISEMENT") and
                        not re.match(r'^[\s\W]*$', text)):
                    # 处理段落中的链接
                    processed_text = self._process_paragraph_links(element)
                    output_html_parts.append(f"<p>{processed_text}</p>")
                    processed_paragraphs.add(id(element))

            # 处理各级标题
            elif element.name in ['h2', 'h3', 'h4']:
                text = element.get_text(strip=True)
                if text and len(text) > 3:
                    output_html_parts.append(f"<{element.name}>{text}</{element.name}>")
                    processed_paragraphs.add(id(element))

            # 处理引用块
            elif element.name == 'blockquote':
                text = element.get_text(strip=True)
                if text:
                    output_html_parts.append(
                        f'<blockquote style="border-left: 4px solid #ddd; padding-left: 1em; margin: 1em 0; font-style: italic;">{text}</blockquote>')
                    processed_paragraphs.add(id(element))

            # 处理列表
            elif element.name in ['ul', 'ol']:
                list_items = element.find_all('li')
                if list_items:
                    list_html = f"<{element.name}>"
                    for li in list_items:
                        li_text = li.get_text(strip=True)
                        if li_text:
                            list_html += f"<li>{li_text}</li>"
                    list_html += f"</{element.name}>"
                    output_html_parts.append(list_html)
                    processed_paragraphs.add(id(element))

            # 处理内容中的图片
            elif element.name == 'figure':
                figure_html = self._process_figure_element(element)
                if figure_html:
                    output_html_parts.append(figure_html)
                    processed_paragraphs.add(id(element))

        if not output_html_parts or (len(output_html_parts) <= 2 and main_image_html):
            logger.warning("虽然找到了容器，但未能提取任何有效的正文内容")
            return self._create_html_document(
                "错误：未能提取任何有效的文章内容。",
                title=article_metadata.get('title', 'Error')
            )

        # 5. 组装成最终的HTML文档
        body_content = ''.join(output_html_parts)
        return self._create_html_document(
            body_content,
            title=article_metadata.get('title', 'Extracted Article')
        )

    def _extract_article_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """提取文章元数据"""
        metadata = {}

        # 提取标题
        title_element = soup.find('h1', id='headline') or soup.find('h1', class_='eza-title')
        if title_element:
            metadata['title'] = title_element.get_text().strip()
        else:
            # 从meta标签提取
            title_meta = soup.find('meta', property='og:title')
            if title_meta:
                metadata['title'] = title_meta.get('content', '').strip()

        # 提取作者
        author_element = soup.find('span', class_='staff-name')
        if author_element:
            metadata['author'] = author_element.get_text().strip()

        # 提取作者机构
        staffline_element = soup.find('span', class_='staffline')
        if staffline_element:
            metadata['staffline'] = staffline_element.get_text().strip()

        # 提取发布时间
        time_element = soup.find('time')
        if time_element:
            metadata['publish_time'] = time_element.get('datetime', '')
            metadata['publish_time_display'] = time_element.get_text().strip()

        # 提取地点
        dateline = soup.find('span', id='dateline') or soup.find('span', class_='eza-dateline')
        if dateline:
            metadata['dateline'] = dateline.get_text().strip()

        # 提取摘要
        summary_div = soup.find('div', id='summary') or soup.find('div', class_='eza-summary')
        if summary_div:
            summary_p = summary_div.find('p')
            if summary_p:
                metadata['summary'] = summary_p.get_text().strip()

        # 提取分类/标签
        kicker = soup.find('span', class_='kicker') or soup.find('span', class_='story_kicker')
        if kicker:
            metadata['category'] = kicker.get_text().strip()

        return metadata

    def _create_article_header(self, metadata: Dict[str, str]) -> str:
        """创建文章头部HTML"""
        header_parts = []

        if metadata.get('category'):
            header_parts.append(
                f'<div class="article-category" style="color: #666; font-size: 0.9em; text-transform: uppercase; margin-bottom: 0.5em;">{metadata["category"]}</div>')

        if metadata.get('title'):
            header_parts.append(
                f'<h1 style="color: #2a2a2a; margin: 0.5em 0; line-height: 1.2;">{metadata["title"]}</h1>')

        if metadata.get('summary'):
            header_parts.append(
                f'<div class="article-summary" style="font-size: 1.1em; color: #555; margin: 1em 0; line-height: 1.4; font-style: italic;">{metadata["summary"]}</div>')

        # 作者和时间信息
        byline_parts = []
        if metadata.get('author'):
            author_text = metadata['author']
            if metadata.get('staffline'):
                author_text += f" - {metadata['staffline']}"
            byline_parts.append(f'<span class="author">{author_text}</span>')

        if metadata.get('publish_time_display'):
            byline_parts.append(f'<span class="publish-time">{metadata["publish_time_display"]}</span>')

        if metadata.get('dateline'):
            byline_parts.append(f'<span class="dateline">{metadata["dateline"]}</span>')

        if byline_parts:
            byline_html = ' | '.join(byline_parts)
            header_parts.append(
                f'<div class="article-byline" style="color: #666; font-size: 0.9em; margin: 1em 0; padding: 0.5em 0; border-top: 1px solid #eee; border-bottom: 1px solid #eee;">{byline_html}</div>')

        return ''.join(header_parts)

    def _extract_main_image(self, soup: BeautifulSoup) -> Optional[str]:
        """提取文章主图"""
        main_media = soup.find('div', id='main-media')
        if main_media:
            return self._process_figure_element(main_media)
        return None

    def _process_figure_element(self, element: Tag) -> Optional[str]:
        """处理图片元素"""
        img_tag = element.find('img')
        if not img_tag:
            return None

        # 获取图片URL
        src = (img_tag.get('data-srcset') or
               img_tag.get('data-src') or
               img_tag.get('src'))

        if not src:
            return None

        # 从srcset中提取第一个URL
        if ' ' in src:
            src = src.split(' ')[0]

        # 处理URL
        if src.startswith('//'):
            src = 'https:' + src
        elif not src.startswith('http'):
            src = urljoin(self.base_url, src)

        alt = img_tag.get('alt', 'Article image')

        # 提取图片说明
        caption_text = ""
        caption_selectors = [
            'div.eza-caption',
            'figcaption',
            '.caption-bar',
            '.image-caption'
        ]

        for selector in caption_selectors:
            caption_element = element.find(selector) or element.parent.find(selector) if element.parent else None
            if caption_element:
                caption_text = caption_element.get_text(strip=True)
                break

        # 提取图片来源
        credit_text = ""
        credit_selectors = [
            'span.eza-credit',
            '.image-credit',
            '.photo-credit'
        ]

        for selector in credit_selectors:
            credit_element = element.find(selector) or element.parent.find(selector) if element.parent else None
            if credit_element:
                credit_text = credit_element.get_text(strip=True)
                break

        # 组合说明和来源
        full_caption = []
        if caption_text:
            full_caption.append(caption_text)
        if credit_text:
            full_caption.append(f"({credit_text})")

        caption_html = ' '.join(full_caption) if full_caption else ''

        # 生成图片HTML
        figure_html = (
            '<figure style="text-align: center; margin: 1.5em 0; background: #f8f9fa; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'
            f'<img src="{src}" alt="{alt}" style="max-width: 100%; height: auto; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);" />'
        )

        if caption_html:
            figure_html += f'<figcaption style="font-size: 0.9em; color: #666; margin-top: 10px; line-height: 1.4; max-width: 90%; margin-left: auto; margin-right: auto;">{caption_html}</figcaption>'

        figure_html += '</figure>'

        return figure_html

    def _process_paragraph_links(self, paragraph: Tag) -> str:
        """处理段落中的链接"""
        # 简单地返回段落的文本内容，保持链接但移除复杂的属性
        for link in paragraph.find_all('a'):
            href = link.get('href', '')
            if href:
                # 处理相对链接
                if href.startswith('/'):
                    href = urljoin(self.base_url, href)
                link['href'] = href
                # 移除不必要的属性
                for attr in list(link.attrs.keys()):
                    if attr not in ['href', 'title']:
                        del link[attr]

        return str(paragraph.decode_contents())

    def _create_html_document(self, body_content: str, title: str = "Article") -> str:
        """创建一个带有样式的完整HTML文档。"""
        style = """
        <style>
            body { 
                font-family: "Georgia", "Times New Roman", serif; 
                line-height: 1.7; 
                padding: 20px; 
                max-width: 800px; 
                margin: auto; 
                background-color: #fafafa; 
                color: #333; 
            }
            h1 { 
                color: #1a1a1a; 
                margin: 0.5em 0; 
                font-size: 2em; 
                line-height: 1.2; 
                border-bottom: 2px solid #2c5aa0; 
                padding-bottom: 10px;
            }
            h2, h3, h4 { 
                color: #2a2a2a; 
                margin-top: 1.8em; 
                margin-bottom: 0.5em;
                border-bottom: 1px solid #ddd; 
                padding-bottom: 5px;
            }
            h2 { font-size: 1.5em; }
            h3 { font-size: 1.3em; }
            h4 { font-size: 1.1em; }
            p { 
                margin: 1.2em 0; 
                text-align: justify; 
                text-indent: 1.5em;
            }
            .article-summary { text-indent: 0 !important; }
            .article-byline { text-indent: 0 !important; }
            .article-category { text-indent: 0 !important; }
            figure { 
                border: none; 
                margin: 2em 0;
            }
            img { 
                border: 1px solid #ddd; 
                border-radius: 6px; 
                padding: 4px; 
                background: white; 
            }
            blockquote {
                background: #f9f9f9;
                border-left: 4px solid #2c5aa0;
                margin: 1.5em 0;
                padding: 1em 1.5em;
                font-style: italic;
            }
            ul, ol {
                margin: 1em 0;
                padding-left: 2em;
            }
            li {
                margin: 0.5em 0;
            }
            a {
                color: #2c5aa0;
                text-decoration: none;
                border-bottom: 1px dotted #2c5aa0;
            }
            a:hover {
                color: #1a3d6b;
                border-bottom: 1px solid #1a3d6b;
            }
        </style>
        """
        return (f"<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>"
                f"<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
                f"<title>{title}</title>{style}</head><body>{body_content}</body></html>")

    async def extract_single_article(self, article: MonitorArticle, headers: Optional[Dict[str, str]] = None) -> Dict[
        str, Any]:
        """从单个文章URL中提取内容。"""
        headers = headers or self.headers
        logger.info(f"开始提取文章: {article.title} ({article.url})")

        try:
            fetch_result = await make_request(url=article.url, headers=headers, timeout=20)
            if fetch_result.error or not fetch_result.content:
                error_msg = f"请求失败: {fetch_result.error}"
                logger.error(error_msg)
                return {
                    'url': article.url,
                    'title': getattr(article, 'title', ''),
                    'content': self._create_html_document(f"错误：无法从URL获取内容。{fetch_result.error}"),
                    'success': False
                }

            extracted_body = await self.extract_body_from_html(fetch_result.content)
            logger.info(f"提取成功: {article.title}")
            return {
                'url': article.url,
                'title': getattr(article, 'title', ''),
                'content': extracted_body,
                'success': True
            }

        except Exception as e:
            error_msg = f"提取文章过程中发生未知错误: {e}"
            logger.exception(error_msg)
            return {
                'url': article.url,
                'title': getattr(article, 'title', ''),
                'content': self._create_html_document(error_msg),
                'success': False
            }

    async def extract_all(self, article_list: MonitorArticleList) -> List[Dict[str, Any]]:
        """并发提取文章列表中的所有文章。"""
        if not article_list.articles:
            logger.warning("文章列表为空，无需提取")
            return []

        logger.info(f"开始提取 {len(article_list.articles)} 篇文章，最大并发数: {self.max_concurrent}")
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def extract_with_semaphore(article):
            async with semaphore:
                result = await self.extract_single_article(article)
                if self.save_html and result.get('success'):
                    # 使用文章标题作为文件名
                    fname = self.sanitize_filename(result['title'] or 'untitled_article') + ".html"
                    # 按日期创建文件夹
                    save_dir = os.path.join('data', 'html', datetime.datetime.now().strftime("%Y-%m-%d"))
                    os.makedirs(save_dir, exist_ok=True)
                    save_path = os.path.join(save_dir, fname)

                    try:
                        with open(save_path, 'w', encoding='utf-8') as f:
                            f.write(result['content'])
                        logger.info(f"HTML 已保存至: {save_path}")
                    except Exception as e:
                        logger.warning(f"保存 HTML 文件失败: {save_path} - {e}")
                return result

        tasks = [extract_with_semaphore(article) for article in article_list.articles]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                article = article_list.articles[i]
                logger.error(f"处理文章 {article.url} 时发生致命异常", exc_info=result)
                processed_results.append({
                    'url': article.url,
                    'title': getattr(article, 'title', ''),
                    'content': self._create_html_document(f"处理过程中发生异常: {result}"),
                    'success': False
                })
            else:
                processed_results.append(result)

        logger.info("所有文章提取任务完成")
        return processed_results