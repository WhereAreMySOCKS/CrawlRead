import os
from typing import List, Dict, Optional
import glob
from datetime import datetime


class HTMLContentService:
    """
    服务保存的HTML内容的服务类。
    提供API接口，让用户可以访问保存在本地的HTML页面。
    """

    def __init__(self, html_dir: str = os.path.join('data', 'html'),
                 images_dir: str = os.path.join('data', 'images')):
        self.html_dir = html_dir
        self.images_dir = images_dir

        # 确保目录存在
        os.makedirs(self.html_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)

    def list_articles(self) -> List[Dict[str, str]]:
        """获取所有已保存的文章列表"""
        articles = []
        html_files = glob.glob(os.path.join(self.html_dir, "*.html"))

        for file_path in html_files:
            filename = os.path.basename(file_path)
            # 获取文件大小和最后修改时间
            stats = os.stat(file_path)
            file_size = stats.st_size
            modified_time = stats.st_mtime

            # 从文件名中提取标题（去掉.html后缀）
            title = os.path.splitext(filename)[0]

            articles.append({
                "filename": filename,
                "title": title,
                "file_size": file_size,
                "modified_time": modified_time,
                "formatted_date": datetime.fromtimestamp(modified_time).strftime("%Y-%m-%d %H:%M:%S")
            })

        # 按修改时间排序，最新的排在前面
        articles.sort(key=lambda x: x["modified_time"], reverse=True)
        return articles

    def get_article_content(self, filename: str) -> Optional[str]:
        """根据文件名获取文章HTML内容"""
        file_path = os.path.join(self.html_dir, filename)

        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def article_exists(self, filename: str) -> bool:
        """检查文章是否存在"""
        file_path = os.path.join(self.html_dir, filename)
        return os.path.exists(file_path)