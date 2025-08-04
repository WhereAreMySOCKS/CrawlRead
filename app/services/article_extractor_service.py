import asyncio
import os
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.models.monitor_entities import MonitorArticleList, MonitorArticle
from app.services.http_client import make_request
from app.services.image_downloader import download_image
from app.services.template_service import TemplateService
from utils.logger_util import logger


class ArticleExtractor:
    """
    一个用于从 The Christian Science Monitor 网站提取和清理文章内容的类。
    支持图片下载到本地，并可控制图片质量。
    优化版本：使用模板服务分离HTML和CSS
    """

    def __init__(
            self,
            max_concurrent: int = 5,
            save_html: bool = True,
            download_images: bool = True,
            resize_images: bool = False,
            max_image_width: int = 1200,
            max_image_height: int = 1200,
            image_quality: int = 85,
            max_image_size: int = 500 * 1024
    ):
        self.max_concurrent = max_concurrent
        self.save_html = save_html
        self.download_images = download_images
        self.resize_images = resize_images
        self.max_image_width = max_image_width
        self.max_image_height = max_image_height
        self.image_quality = image_quality
        self.max_image_size = max_image_size

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36'
        }
        self.base_url = "https://www.csmonitor.com/"
        self.image_dir = os.path.join('data', 'images')
        self.image_semaphore = asyncio.Semaphore(10)
        self.processed_images = set()
        
        # 初始化模板服务
        self.template_service = TemplateService()

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """清理字符串，使其成为有效的文件名。"""
        name = re.sub(r'[\\/*?:"<>|]', '_', name)
        return name[:100]

    async def extract_body_from_html(self, html_content: str, article_url: str = None) -> str:
        """
        从给定的HTML内容中提取、清理并格式化文章正文。
        使用模板服务分离HTML和CSS
        """
        self.processed_images = set()
        soup = BeautifulSoup(html_content, 'lxml')

        # 提取文章元数据
        article_metadata = self._extract_article_metadata(soup)

        # 定位文章主容器
        article_container = self._find_article_container(soup)
        if not article_container:
            logger.warning("在HTML中未找到任何文章正文容器")
            return self.template_service.render_error_page(
                "错误：在此页面未找到指定的文章正文容器。",
                article_metadata.get('title', 'Error')
            )

        # 预处理：移除所有不需要的元素
        self._remove_unwanted_elements(article_container)

        # 提取文章主图
        main_image_html = await self._extract_main_image(soup, article_url)

        # 按顺序遍历并提取所有有效的内容元素
        content_elements = article_container.find_all(
            ['p', 'h2', 'h3', 'h4', 'figure', 'blockquote', 'ul', 'ol'],
            recursive=True
        )

        # 初始化输出列表
        output_html_parts = []

        # 添加文章头部信息
        if article_metadata:
            header_html = self.template_service.render_article_header(article_metadata)
            output_html_parts.append(header_html)

        # 添加主图
        if main_image_html:
            output_html_parts.append(main_image_html)

        # 处理内容元素
        processed_paragraphs = set()
        placeholder_map = {}
        placeholder_counter = 0

        for element in content_elements:
            if id(element) in processed_paragraphs:
                continue
            processed_paragraphs.add(id(element))

            if element.name == 'figure':
                placeholder_counter += 1
                placeholder_id = f"PLACEHOLDER_{placeholder_counter}"
                output_html_parts.append(placeholder_id)
                task = self._process_figure_element(element, article_url)
                placeholder_map[placeholder_id] = task
            else:
                processed_html = self._process_non_figure_element(element)
                if processed_html:
                    output_html_parts.append(processed_html)

        # 等待所有图片处理任务完成
        if placeholder_map:
            logger.info(f"开始并行处理 {len(placeholder_map)} 个图片元素")
            tasks = list(placeholder_map.values())
            results = await asyncio.gather(*tasks, return_exceptions=True)

            result_map = {}
            for (placeholder_id, task), result in zip(placeholder_map.items(), results):
                if isinstance(result, Exception):
                    logger.error(f"处理图片时发生异常: {result}")
                    result_map[placeholder_id] = ""
                else:
                    result_map[placeholder_id] = result or ""

            final_output_parts = []
            for part in output_html_parts:
                if part in result_map:
                    final_output_parts.append(result_map[part])
                else:
                    final_output_parts.append(part)
            output_html_parts = final_output_parts

        if not output_html_parts or (len(output_html_parts) <= 2 and main_image_html):
            logger.warning("虽然找到了容器，但未能提取任何有效的正文内容")
            return self.template_service.render_error_page(
                "错误：未能提取任何有效的文章内容。",
                article_metadata.get('title', 'Error')
            )

        # 组装成最终的HTML文档
        body_content = ''.join(output_html_parts)
        return self.template_service.render_article_template(
            body_content,
            article_metadata.get('title', 'Article')
        )

    def _find_article_container(self, soup: BeautifulSoup) -> Optional[Tag]:
        """查找文章主容器"""
        selectors = [
            'div.eza-body',
            'div.prem',
            'article',
            'div[class*="story-content"]',
            'div[class*="article-body"]'
        ]

        for selector in selectors:
            container = soup.select_one(selector)
            if container:
                if selector != 'div.eza-body':
                    logger.info(f"使用备选选择器找到文章容器: {selector}")
                return container
        return None

    def _remove_unwanted_elements(self, container: Tag) -> None:
        """移除不需要的元素"""
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
            for element in container.select(selector):
                element.decompose()

    def _extract_article_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """提取文章元数据"""
        metadata = {}

        # 提取标题
        title_tag = soup.find('h1') or soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text(strip=True)

        # 提取作者信息
        author_tag = soup.find('span', class_='author') or soup.find('a', rel='author')
        if author_tag:
            metadata['author'] = author_tag.get_text(strip=True)

        # 提取发布时间
        time_tag = soup.find('time')
        if time_tag and time_tag.get('datetime'):
            metadata['publish_time_display'] = time_tag.get('datetime')

        # 提取摘要
        summary_tag = soup.find('meta', attrs={'name': 'description'})
        if summary_tag and summary_tag.get('content'):
            metadata['summary'] = summary_tag.get('content')

        return metadata

    async def _extract_main_image(self, soup: BeautifulSoup, article_url: str) -> Optional[str]:
        """提取文章主图"""
        # 查找主图
        main_image_selectors = [
            'div.hero-image img',
            'div.featured-image img',
            'meta[property="og:image"]',
            'meta[name="twitter:image"]'
        ]

        for selector in main_image_selectors:
            if 'meta' in selector:
                meta_tag = soup.find('meta', attrs={'property': 'og:image'}) or \
                          soup.find('meta', attrs={'name': 'twitter:image'})
                if meta_tag and meta_tag.get('content'):
                    image_url = urljoin(article_url, meta_tag['content'])
                    return await self._download_and_create_image_html(image_url, "主图")
            else:
                img_tag = soup.select_one(selector)
                if img_tag and img_tag.get('src'):
                    image_url = urljoin(article_url, img_tag['src'])
                    return await self._download_and_create_image_html(image_url, "主图")

        return None

    async def _process_figure_element(self, element: Tag, article_url: str) -> str:
        """处理图片元素"""
        img_tag = element.find('img')
        if not img_tag or not img_tag.get('src'):
            return ""

        src = urljoin(article_url, img_tag['src'])
        alt = img_tag.get('alt', 'Article image')

        # 提取图片说明
        caption = ""
        figcaption = element.find('figcaption')
        if figcaption:
            caption = figcaption.get_text(strip=True)
        else:
            # 尝试从其他位置找说明
            caption_candidate = element.find_next_sibling()
            if caption_candidate and caption_candidate.name in ['p', 'div']:
                caption_text = caption_candidate.get_text(strip=True)
                if len(caption_text) < 200 and 'photo' in caption_text.lower():
                    caption = caption_text

        return await self._download_and_create_image_html(src, alt, caption)

    async def _download_and_create_image_html(self, image_url: str, alt: str, caption: str = None) -> str:
        """下载图片并创建HTML"""
        if not self.download_images:
            return self.template_service.render_figure(image_url, alt, caption)

        if image_url in self.processed_images:
            return ""
        self.processed_images.add(image_url)

        try:
            async with self.image_semaphore:
                result = await download_image(
                    image_url,
                    self.image_dir,
                    resize=self.resize_images,
                    max_width=self.max_image_width,
                    max_height=self.max_image_height,
                    quality=self.image_quality,
                    max_file_size=self.max_image_size
                )

            if result and result.success and result.local_path:
                local_image_path = result.local_path
                if os.name == 'nt':
                    local_image_path = local_image_path.replace('\\', '/')
                return self.template_service.render_figure(local_image_path, alt, caption)
            else:
                logger.warning(f"图片下载失败: {image_url}, 原因: {result}")
                return self.template_service.render_figure(image_url, alt, caption)

        except Exception as e:
            logger.error(f"图片下载过程中发生异常: {image_url}, 错误: {str(e)}")
            return self.template_service.render_figure(image_url, alt, caption)

    def _process_non_figure_element(self, element: Tag) -> str:
        """处理非图片元素"""
        if not element.get_text(strip=True):
            return ""

        # 创建元素的深拷贝以避免修改原始内容
        element_copy = element.__copy__()

        # 处理链接
        if element_copy.name == 'a':
            href = element_copy.get('href', '')
            if href.startswith('/'):
                href = urljoin(self.base_url, href)
            element_copy['href'] = href

        # 清理不必要的属性
        for attr in list(element_copy.attrs.keys()):
            if attr not in ['href', 'title', 'src', 'alt']:
                del element_copy[attr]

        return str(element_copy)

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
                    'content': self.template_service.render_error_page(
                        f"错误：无法从URL获取内容。{fetch_result.error}"
                    ),
                    'success': False
                }

            extracted_body = await self.extract_body_from_html(fetch_result.content, article.url)
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
                'content': self.template_service.render_error_page(
                    f"处理过程中发生异常: {e}"
                ),
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
                    fname = self.sanitize_filename(result['title'] or 'untitled_article') + ".html"
                    save_dir = os.path.join('data', 'html')
                    os.makedirs(save_dir, exist_ok=True)
                    save_path = os.path.join(save_dir, fname)

                    if os.path.exists(save_path):
                        logger.info(f"文件已存在，跳过保存: {save_path}")
                    else:
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
                logger.error(f"处理文章 {article.url} 时发生异常", exc_info=result)
                processed_results.append({
                    'url': article.url,
                    'title': getattr(article, 'title', ''),
                    'content': self.template_service.render_error_page(
                        f"处理过程中发生异常: {result}"
                    ),
                    'success': False
                })
            else:
                processed_results.append(result)

        logger.info("所有文章提取任务完成")
        return processed_results