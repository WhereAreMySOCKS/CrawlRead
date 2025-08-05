import os
import re
from datetime import datetime
from typing import Dict, Any

from app.services.html_content_service import HTMLContentService
from utils.logger_util import logger


# 存储服务也简化
class ArticleStorageService:
    def __init__(self, base_dir: str = "data/html"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    async def save_article(self, article_data: Dict[str, Any]) -> bool:
        """保存文章"""
        try:
            content = article_data.get('content', '')
            if not content.strip():
                return False

            title = article_data.get('title', '').strip()
            if not title:
                title = self._extract_title_from_content(content)

            # 生成文件名
            filename = HTMLContentService.encode_title_to_filename(
                title,
                article_data.get('id', '')
            )

            file_path = os.path.join(self.base_dir, filename)

            if os.path.exists(file_path):
                logger.info(f"文件已存在: {filename}")
                return True

            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"文章已保存: {filename}")
            logger.info(f"标题: {title}")

            return True

        except Exception as e:
            logger.error(f"保存文章失败: {e}")
            return False

    def _extract_title_from_content(self, content: str) -> str:
        """简单提取标题"""

        # 只检查前1KB
        search_content = content[:1024]

        match = re.search(r'<title[^>]*>(.*?)</title>', search_content, re.IGNORECASE | re.DOTALL)
        if match:
            title = re.sub(r'<[^>]+>', '', match.group(1)).strip()
            if title:
                return title

        return f"article_{int(datetime.now().timestamp())}"