import os
import asyncio
from typing import Dict, Any
from utils.logger_util import logger
import re


class ArticleStorageService:
    """
    负责将文章内容保存到本地的服务
    """

    def __init__(self, base_dir: str = "data/html"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """清理字符串，使其成为有效的文件名。"""
        import re
        # 移除无效字符
        name = re.sub(r'[\\/*?:"<>|]', '_', name)
        # 避免文件名过长
        return name[:100]

    async def save_article(self, article_data: Dict[str, Any]) -> bool:
        """
        保存文章到本地文件系统

        Args:
            article_data: 包含文章信息的字典

        Returns:
            bool: 保存是否成功
        """
        try:
            title = article_data.get('title', 'untitled_article')
            content = article_data.get('content', '')

            try:
                title = article_data.get('title', '')
                content = article_data.get('content', '')

                if not title and content:
                    html_title_match = re.search(r'<title>(.*?)</title>', content)

                    if html_title_match:
                        # Extract and set the title from the HTML content
                        title = html_title_match.group(1)
                    else:
                        # Use URL slug as fallback
                        url = article_data.get('url', '')
                        if url:
                            slug = url.split('/')[-1]
                            title = slug.replace('-', ' ').title()
                        else:
                            # 无法获取title时用时间戳命名文章
                            title = f"article_{int(asyncio.get_event_loop().time())}"
                logger.info(f"处理文章: {title}")

            except Exception as e:
                logger.warning(f"文章内容为空，跳过保存: {title}")
                return False

            # 使用文章标题作为文件名
            fname = self.sanitize_filename(title) + ".html"
            save_path = os.path.join(self.base_dir, fname)

            # 检查文件是否已存在，如果存在则跳过而不覆盖
            if os.path.exists(save_path):
                logger.info(f"文件已存在，跳过保存: {save_path}")
                return True

            # 使用异步文件操作
            async def write_file():
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self._write_to_file(save_path, content)
                )

            await write_file()
            logger.info(f"HTML 已保存至: {save_path}")
            return True

        except Exception as e:
            logger.error(f"保存文章失败: {str(e)}")
            return False

    def _write_to_file(self, path: str, content: str):
        """同步写入文件内容"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)