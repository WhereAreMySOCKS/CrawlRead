from typing import Dict, Any, List, Optional
import yaml
import os
from pathlib import Path
import logging

# 设置日志
logger = logging.getLogger(__name__)

# 获取配置文件路径
CONFIG_DIR = Path(__file__).parent.parent / "config"
WEBSITE_CONFIG_PATH = CONFIG_DIR / "websites.yaml"
SCHEDULER_CONFIG_PATH = CONFIG_DIR / "scheduler.yaml"

# 确保配置目录存在
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


# 加载网站配置
def load_website_configs() -> Dict[str, Any]:
    """
    从配置文件加载网站配置

    Returns:
        包含所有网站配置的字典
    """
    try:
        if not WEBSITE_CONFIG_PATH.exists():
            logger.warning(f"配置文件不存在: {WEBSITE_CONFIG_PATH}")
            return {}

        with open(WEBSITE_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        return config_data.get('websites', {})
    except Exception as e:
        logger.error(f"加载配置文件失败: {str(e)}")
        return {}


# 加载调度器配置
def load_scheduler_config() -> Dict[str, Any]:
    """
    从配置文件加载调度器配置

    Returns:
        包含调度器配置的字典
    """
    try:
        if not SCHEDULER_CONFIG_PATH.exists():
            logger.warning(f"调度器配置文件不存在: {SCHEDULER_CONFIG_PATH}")
            return {
                "article_fetch": {"hour": 2, "minute": 0},
                "article_process": {"interval_minutes": 10},
                "concurrency": {"max_concurrent": 5}
            }

        with open(SCHEDULER_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        return config_data.get('scheduler', {})
    except Exception as e:
        logger.error(f"加载调度器配置文件失败: {str(e)}")
        return {
            "article_fetch": {"hour": 2, "minute": 0},
            "article_process": {"interval_minutes": 10},
            "concurrency": {"max_concurrent": 5}
        }


# 加载配置
WEBSITE_CONFIGS = load_website_configs()
SCHEDULER_CONFIG = load_scheduler_config()


def list_available_websites() -> List[str]:
    """
    列出所有可用的网站

    Returns:
        网站标识符列表
    """
    # 过滤掉 'defaults' 等非网站配置项
    return [site for site in WEBSITE_CONFIGS.keys() if site != 'defaults']


def list_available_sections(website: str) -> List[str]:
    """
    列出指定网站的所有可用板块

    Args:
        website: 网站标识符

    Returns:
        板块标识符列表
    """
    website_config = WEBSITE_CONFIGS.get(website.lower())
    if not website_config:
        return []

    return list(website_config.get("sections", {}).keys())


def get_website_config(website: str, section: str) -> Dict[str, Any]:
    """
    获取指定网站和板块的配置

    Args:
        website: 网站标识符（如 "csmonitor"）
        section: 板块标识符（如 "business"）

    Returns:
        包含URL、headers和cookies的配置字典
    """
    try:
        website_config = WEBSITE_CONFIGS.get(website.lower())
        if not website_config:
            raise ValueError(f"未找到网站配置: {website}")

        section_config = website_config.get("sections", {}).get(section.lower())
        if not section_config:
            raise ValueError(f"未找到板块配置: {website}/{section}")

        # 返回完整配置，包含url、headers和cookies
        return {
            "url": section_config.get("url", ""),
            "headers": section_config.get("headers", {}),
            "cookies": section_config.get("cookies", {})
        }
    except Exception as e:
        raise ValueError(f"获取配置失败: {str(e)}")


def get_all_website_sections() -> List[Dict[str, str]]:
    """
    获取所有网站和板块的配置

    Returns:
        包含网站和板块信息的列表
    """
    all_sections = []

    for website in list_available_websites():
        for section in list_available_sections(website):
            all_sections.append({
                "website": website,
                "section": section
            })

    return all_sections


def get_scheduler_config() -> Dict[str, Any]:
    """
    获取调度器配置

    Returns:
        调度器配置字典
    """
    return SCHEDULER_CONFIG


def get_max_concurrent() -> int:
    """
    获取最大并发数

    Returns:
        最大并发数
    """
    return SCHEDULER_CONFIG.get("concurrency", {}).get("max_concurrent", 5)


def get_article_fetch_schedule() -> Dict[str, int]:
    """
    获取文章获取调度时间

    Returns:
        包含hour和minute的字典
    """
    fetch_config = SCHEDULER_CONFIG.get("article_fetch", {})
    return {
        "hour": fetch_config.get("hour", 2),
        "minute": fetch_config.get("minute", 0)
    }


def get_article_process_interval() -> int:
    """
    获取文章处理间隔时间

    Returns:
        间隔分钟数
    """
    return SCHEDULER_CONFIG.get("article_process", {}).get("interval_minutes", 10)


# 配置文件变更检测
import time

_last_config_load_time = time.time()
_config_file_mtime = WEBSITE_CONFIG_PATH.stat().st_mtime if WEBSITE_CONFIG_PATH.exists() else 0


def has_config_changed() -> bool:
    """
    检查配置文件是否已更改

    Returns:
        True 如果配置文件已更改，否则 False
    """
    global _config_file_mtime

    if not WEBSITE_CONFIG_PATH.exists():
        return False

    current_mtime = WEBSITE_CONFIG_PATH.stat().st_mtime
    if current_mtime > _config_file_mtime:
        _config_file_mtime = current_mtime
        return True

    return False


def reload_configs() -> bool:
    """
    重新加载配置文件

    Returns:
        True 如果重新加载成功，否则 False
    """
    global WEBSITE_CONFIGS, _last_config_load_time

    try:
        WEBSITE_CONFIGS = load_website_configs()
        _last_config_load_time = time.time()
        return True
    except Exception as e:
        logger.error(f"重新加载配置失败: {e}")
        return False