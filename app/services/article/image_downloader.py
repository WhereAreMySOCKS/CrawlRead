import aiohttp
import asyncio
import os
import re
import hashlib
from typing import Optional, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass
from utils.logger_util import logger
from PIL import Image
import io


@dataclass
class DownloadResult:
    """图片下载结果"""
    success: bool
    local_path: Optional[str] = None
    error_message: Optional[str] = None
    file_size: Optional[int] = None
    original_size: Optional[int] = None


async def download_image(
        url: str,
        save_dir: str,
        timeout: int = 25,
        resize: bool = False,  # 统一参数名
        max_width: int = 1200,
        max_height: int = 1200,
        quality: int = 85,
        max_file_size: int = 500 * 1024
) -> DownloadResult:
    """
    下载图片并保存到本地目录，压缩图片质量但保持原始尺寸

    Args:
        url: 图片URL
        save_dir: 保存目录
        timeout: 请求超时时间(秒)
        resize: 是否调整图片尺寸
        max_width: 图片最大宽度(仅当resize=True时使用)
        max_height: 图片最大高度(仅当resize=True时使用)
        quality: JPEG压缩质量(1-100)
        max_file_size: 最大文件大小(字节)

    Returns:
        DownloadResult: 下载结果对象
    """
    if not url or not url.strip():
        return DownloadResult(success=False, error_message="Empty URL")

    # 创建保存目录
    os.makedirs(save_dir, exist_ok=True)

    # 从URL生成文件名
    url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
    parsed_url = urlparse(url)
    path = parsed_url.path

    # 获取扩展名
    ext = os.path.splitext(path)[1].lower()
    if not ext or len(ext) > 5 or ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        ext = '.jpg'  # 默认扩展名

    # 构建文件名和路径
    filename = f"{url_hash}{ext}"
    filepath = os.path.join(save_dir, filename)

    # 如果文件已存在，直接返回路径
    if os.path.exists(filepath):
        file_size = os.path.getsize(filepath)
        return DownloadResult(success=True, local_path=filepath, file_size=file_size)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    return DownloadResult(success=False, error_message=f"HTTP error: {response.status}")

                # 获取图片数据
                image_data = await response.read()
                if not image_data:
                    return DownloadResult(success=False, error_message="Empty response")

                original_size = len(image_data)

                # 处理图片质量
                try:
                    # 使用PIL处理图片
                    img = Image.open(io.BytesIO(image_data))

                    # 只有在resize=True时才调整尺寸
                    if resize:
                        width, height = img.size
                        if width > max_width or height > max_height:
                            # 计算调整比例
                            ratio = min(max_width / width, max_height / height)
                            new_size = (int(width * ratio), int(height * ratio))
                            img = img.resize(new_size, Image.LANCZOS)
                            logger.info(f"调整图片尺寸: {width}x{height} -> {new_size[0]}x{new_size[1]}")

                    # 保存为指定格式
                    output = io.BytesIO()

                    # 转换为RGB模式（如果是RGBA，去除透明通道）
                    if img.mode == 'RGBA' and ext not in ['.png', '.webp']:
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3])  # 3 是alpha通道
                        img = background

                    # 根据扩展名保存为对应格式
                    save_format = 'JPEG' if ext in ['.jpg', '.jpeg'] else ext[1:].upper()
                    if save_format == 'JPG':
                        save_format = 'JPEG'

                    # 保存图片，对JPEG应用质量压缩
                    if save_format == 'JPEG':
                        img.save(output, format=save_format, quality=quality, optimize=True)
                    elif save_format == 'PNG':
                        img.save(output, format=save_format, optimize=True, compress_level=9)
                    else:
                        img.save(output, format=save_format, optimize=True)

                    processed_data = output.getvalue()

                    # 检查处理后的文件大小
                    if len(processed_data) > max_file_size and save_format == 'JPEG':
                        current_quality = quality
                        while len(processed_data) > max_file_size and current_quality > 40:
                            current_quality -= 10
                            output = io.BytesIO()
                            img.save(output, format='JPEG', quality=current_quality, optimize=True)
                            processed_data = output.getvalue()
                            logger.info(f"降低图片质量至 {current_quality}% 以减小文件大小")

                            if current_quality <= 40:
                                break

                    final_size = len(processed_data)

                    # 保存处理后的图片
                    with open(filepath, 'wb') as f:
                        f.write(processed_data)

                    compression_ratio = (1 - final_size / original_size) * 100
                    logger.info(
                        f"图片已处理并保存: {filepath}, "
                        f"原始大小: {original_size / 1024:.1f}KB, "
                        f"处理后: {final_size / 1024:.1f}KB, "
                        f"压缩率: {compression_ratio:.1f}%"
                    )

                    return DownloadResult(
                        success=True,
                        local_path=filepath,
                        file_size=final_size,
                        original_size=original_size
                    )

                except Exception as e:
                    logger.warning(f"图片处理失败，使用原始图片: {str(e)}")
                    # 如果处理失败，保存原始图片
                    with open(filepath, 'wb') as f:
                        f.write(image_data)
                    return DownloadResult(
                        success=True,
                        local_path=filepath,
                        file_size=len(image_data),
                        original_size=len(image_data)
                    )

    except asyncio.TimeoutError:
        return DownloadResult(success=False, error_message=f"超时 {timeout}秒")
    except Exception as e:
        return DownloadResult(success=False, error_message=f"下载图片错误: {str(e)}")