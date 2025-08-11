import base64
import os
from datetime import datetime
from typing import Dict, Optional

from utils.logger_util import logger


class HTMLContentService:
    """
    纯Base64编码/解码的内容服务
    """

    def __init__(self, html_dir: str = os.path.join('data', 'html')):
        self.html_dir = html_dir
        os.makedirs(self.html_dir, exist_ok=True)

    @staticmethod
    def encode_title_to_filename(title: str, article_id: str = None) -> str:
        """将标题Base64编码到文件名"""
        if not title.strip():
            title = f"untitled_{int(datetime.now().timestamp())}"

        # 直接Base64编码
        encoded = base64.urlsafe_b64encode(title.encode('utf-8')).decode('ascii')

        # 构造文件名
        if article_id:
            return f"{article_id}_{encoded}.html"
        else:
            return f"{encoded}.html"

    @staticmethod
    def decode_title_from_filename(filename: str) -> str:
        """从文件名Base64解码标题"""
        try:
            # 移除.html和可能的ID前缀
            name = filename.replace('.html', '')
            parts = name.split('_', 1)

            encoded_part = parts[1] if len(parts) == 2 and parts[0].isdigit() else name

            # Base64解码
            return base64.urlsafe_b64decode(encoded_part.encode('ascii')).decode('utf-8')

        except Exception:
            # 解码失败就用文件名
            return filename.replace('.html', '').replace('_', ' ')

    def list_articles(self) -> list:
        """获取文章列表"""
        articles = []

        try:
            for filename in os.listdir(self.html_dir):
                if not filename.endswith('.html'):
                    continue

                file_path = os.path.join(self.html_dir, filename)
                stats = os.stat(file_path)

                articles.append({
                    "id": self._extract_id(filename),
                    "filename": filename,
                    "title": self.decode_title_from_filename(filename),
                    "file_size": stats.st_size,
                    "file_size_formatted": self._format_size(stats.st_size),
                    "modified_time": stats.st_mtime,
                    "formatted_date": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })

            articles.sort(key=lambda x: x["modified_time"], reverse=True)
        except Exception as e:
            logger.error(f"获取文章列表失败: {e}")

        return articles

    def get_article_data(self, article_id: str) -> Optional[Dict[str, str]]:
        """根据ID获取文章数据"""
        try:
            for filename in os.listdir(self.html_dir):
                if filename.startswith(f"{article_id}_") and filename.endswith('.html'):
                    content = self.get_article_content(filename)
                    if content:
                        return {
                            "id": article_id,
                            "title": self.decode_title_from_filename(filename),
                            "content": content,
                            "filename": filename,
                            "publishTime": datetime.fromtimestamp(
                                os.path.getmtime(os.path.join(self.html_dir, filename))
                            ).strftime("%Y-%m-%d %H:%M:%S")
                        }
        except Exception as e:
            logger.error(f"获取文章数据失败: {e}")
        return None

    def get_article_content(self, filename: str) -> Optional[str]:
        """获取文章内容"""
        try:
            file_path = os.path.join(self.html_dir, filename)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"读取文章失败: {e}")
        return None

    def _extract_id(self, filename: str) -> str:
        """提取文章ID"""
        parts = filename.split('_')
        return parts[0] if parts and parts[0].isdigit() else ""

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def article_exists(self, filename: str) -> bool:
        """检查文章是否存在"""
        return os.path.exists(os.path.join(self.html_dir, filename))

