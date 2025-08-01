import aiohttp
import asyncio
import os
import re
import hashlib
from typing import Optional, Tuple
from urllib.parse import urlparse
from utils.logger_util import logger
from PIL import Image
import io


async def download_image(
        url: str,
        save_dir: str,
        timeout: int = 15,
        resize_image: bool = False,  # 控制是否调整图片尺寸
        max_width: int = 1200,  # 仅当resize_image=True时使用
        max_height: int = 1200,  # 仅当resize_image=True时使用
        quality: int = 85,  # JPEG压缩质量(1-100)
        max_file_size: int = 500 * 1024  # 最大文件大小限制(500KB)
) -> Tuple[bool, str]:
    """
    下载图片并保存到本地目录，压缩图片质量但保持原始尺寸

    Args:
        url: 图片URL
        save_dir: 保存目录
        timeout: 请求超时时间(秒)
        resize_image: 是否调整图片尺寸
        max_width: 图片最大宽度(仅当resize_image=True时使用)
        max_height: 图片最大高度(仅当resize_image=True时使用)
        quality: JPEG压缩质量(1-100)
        max_file_size: 最大文件大小(字节)

    Returns:
        Tuple[bool, str]: (是否成功, 本地文件路径或错误信息)
    """
    if not url or not url.strip():
        return False, "Empty URL"

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
        return True, filepath

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    return False, f"HTTP error: {response.status}"

                # 获取图片数据
                image_data = await response.read()
                if not image_data:
                    return False, "Empty response"

                original_size = len(image_data) / 1024  # KB

                # 处理图片质量
                try:
                    # 使用PIL处理图片
                    img = Image.open(io.BytesIO(image_data))

                    # 只有在resize_image=True时才调整尺寸
                    if resize_image:
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
                    processed_size = len(processed_data) / 1024  # KB

                    # 检查处理后的文件大小
                    if len(processed_data) > max_file_size and save_format == 'JPEG':
                        # 如果仍然超过大小限制，继续降低质量（仅对JPEG有效）
                        current_quality = quality
                        while len(processed_data) > max_file_size and current_quality > 40:
                            current_quality -= 10
                            output = io.BytesIO()
                            img.save(output, format='JPEG', quality=current_quality, optimize=True)
                            processed_data = output.getvalue()
                            logger.info(f"降低图片质量至 {current_quality}% 以减小文件大小")

                            # 如果质量已经很低但仍然大于最大大小限制，就不再继续降低
                            if current_quality <= 40:
                                break

                    final_size = len(processed_data) / 1024  # KB

                    # 保存处理后的图片
                    with open(filepath, 'wb') as f:
                        f.write(processed_data)

                    logger.info(
                        f"图片已处理并保存: {filepath}, 原始大小: {original_size:.1f}KB, 处理后: {final_size:.1f}KB, 压缩率: {(1 - final_size / original_size) * 100:.1f}%")
                    return True, filepath

                except Exception as e:
                    logger.warning(f"图片处理失败，使用原始图片: {str(e)}")
                    # 如果处理失败，保存原始图片
                    with open(filepath, 'wb') as f:
                        f.write(image_data)
                    return True, filepath

    except asyncio.TimeoutError:
        return False, f"超时 {timeout}秒"
    except Exception as e:
        return False, f"下载图片错误: {str(e)}"