import os
from typing import Dict, Any, Optional
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


class TemplateService:
    """
    模板服务类，用于管理和渲染HTML模板
    将HTML和CSS从Python代码中分离出来
    """

    def __init__(self, template_dir: str = "app/templates/html"):
        """
        初始化模板服务

        Args:
            template_dir: 模板目录路径
        """
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        渲染指定模板

        Args:
            template_name: 模板文件名
            context: 渲染上下文数据

        Returns:
            渲染后的HTML字符串
        """
        template = self.env.get_template(template_name)
        return template.render(**context)

    def render_article_template(self, body_content: str, title: str = "Article") -> str:
        """
        渲染文章页面模板

        Args:
            body_content: 文章正文内容
            title: 文章标题

        Returns:
            完整的HTML页面字符串
        """
        return self.render_template('article.html', {
            'body_content': body_content,
            'title': title
        })

    def render_article_header(self, metadata: Dict[str, str]) -> str:
        """
        渲染文章头部信息

        Args:
            metadata: 文章元数据

        Returns:
            文章头部的HTML字符串
        """
        return self.render_template('article_header.html', metadata)

    def render_figure(self, image_path: str, alt: str = "Article image",
                      caption: Optional[str] = None) -> str:
        """
        渲染图片元素

        Args:
            image_path: 图片路径
            alt: 图片alt文本
            caption: 图片说明文字

        Returns:
            图片的HTML字符串
        """
        return self.render_template('figure.html', {
            'image_path': image_path,
            'alt': alt,
            'caption': caption
        })

    def render_image_placeholder(self, alt: str, caption: Optional[str] = None) -> str:
        """
        渲染图片占位符

        Args:
            alt: 图片alt文本/描述
            caption: 图片说明文字

        Returns:
            图片占位符的HTML字符串
        """
        return self.render_template('image_placeholder.html', {
            'alt': alt,
            'caption': caption
        })

    def render_error_page(self, error_message: str, title: str = "Error") -> str:
        """
        渲染错误页面

        Args:
            error_message: 错误信息
            title: 页面标题

        Returns:
            错误页面的HTML字符串
        """
        return self.render_article_template(
            f"<div class='error-message'>{error_message}</div>",
            title
        )

    def render_figure_fallback(self, image_path: str, alt: str = "Article image",
                               caption: Optional[str] = None) -> str:
        """
        渲染图片元素（内联样式版本，用于模板文件不可用时的备选方案）

        Args:
            image_path: 图片路径
            alt: 图片alt文本
            caption: 图片说明文字

        Returns:
            图片的HTML字符串
        """
        caption_html = ""
        if caption:
            caption_html = f'''
            <figcaption style="font-style: italic; color: #666; text-align: center; margin-top: 10px; font-size: 0.9em;">
                {caption}
            </figcaption>'''

        return f'''
        <figure style="text-align: center; margin: 1.5em 0; background: #f8f9fa; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <img src="{image_path}" alt="{alt}" style="max-width: 100%; height: auto; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);"/>
            {caption_html}
        </figure>
        '''

    def render_image_placeholder_fallback(self, alt: str, caption: Optional[str] = None) -> str:
        """
        渲染图片占位符（内联样式版本，用于模板文件不可用时的备选方案）

        Args:
            alt: 图片alt文本/描述
            caption: 图片说明文字

        Returns:
            图片占位符的HTML字符串
        """
        caption_html = ""
        if caption:
            caption_html = f'''
            <figcaption style="font-style: italic; color: #666; text-align: center; margin-top: 10px; font-size: 0.9em;">
                {caption}
            </figcaption>'''

        return f'''
        <figure style="text-align: center; margin: 1.5em 0; background: #f8f9fa; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="background: #e9ecef; padding: 40px; border-radius: 4px; color: #6c757d; font-family: Arial, sans-serif;">
                📷 图片暂无法显示<br>
                <small style="font-size: 0.8em; margin-top: 5px; display: block;">{alt}</small>
            </div>
            {caption_html}
        </figure>
        '''

    def _template_exists(self, template_name: str) -> bool:
        """
        检查模板文件是否存在

        Args:
            template_name: 模板文件名

        Returns:
            模板文件是否存在
        """
        template_path = Path(self.template_dir) / template_name
        return template_path.exists()

    def safe_render_figure(self, image_path: str, alt: str = "Article image",
                           caption: Optional[str] = None) -> str:
        """
        安全渲染图片元素（如果模板不存在则使用fallback）

        Args:
            image_path: 图片路径
            alt: 图片alt文本
            caption: 图片说明文字

        Returns:
            图片的HTML字符串
        """
        try:
            if self._template_exists('figure.html'):
                return self.render_figure(image_path, alt, caption)
            else:
                return self.render_figure_fallback(image_path, alt, caption)
        except Exception:
            return self.render_figure_fallback(image_path, alt, caption)

    def safe_render_image_placeholder(self, alt: str, caption: Optional[str] = None) -> str:
        """
        安全渲染图片占位符（如果模板不存在则使用fallback）

        Args:
            alt: 图片alt文本/描述
            caption: 图片说明文字

        Returns:
            图片占位符的HTML字符串
        """
        try:
            if self._template_exists('image_placeholder.html'):
                return self.render_image_placeholder(alt, caption)
            else:
                return self.render_image_placeholder_fallback(alt, caption)
        except Exception:
            return self.render_image_placeholder_fallback(alt, caption)