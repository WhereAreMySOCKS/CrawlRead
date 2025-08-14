from typing import Dict, Any, List
import yaml
from pathlib import Path
import logging
import time

# 设置日志
logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_DIR = Path(__file__).parent.parent / "config"
CONFIG_PATH = CONFIG_DIR / "config-dev.yaml"

# 确保目录存在
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# 默认配置（防止缺失项导致程序崩溃）
DEFAULT_CONFIG = {
    "api": {},
    "scheduler": {
        "article_fetch": {"hour": 2, "minute": 0},
        "article_process": {"interval_minutes": 10},
        "concurrency": {"max_concurrent": 5}
    },
    "websites": {}
}

# 全局配置缓存
CONFIG: Dict[str, Any] = {}
_config_file_mtime = CONFIG_PATH.stat().st_mtime if CONFIG_PATH.exists() else 0


def load_config() -> Dict[str, Any]:
    """一次性加载总配置文件"""
    try:
        if not CONFIG_PATH.exists():
            logger.warning(f"配置文件不存在: {CONFIG_PATH}")
            return DEFAULT_CONFIG.copy()

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # 合并默认值
        merged = DEFAULT_CONFIG.copy()
        for k, v in data.items():
            merged[k] = v
        return merged
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return DEFAULT_CONFIG.copy()


# 初始化加载
CONFIG = load_config()

# ---------------- 兼容旧函数接口 ---------------- #

def list_available_websites() -> List[str]:
    """列出所有网站（过滤 defaults）"""
    return [site for site in CONFIG.get("websites", {}).keys() if site != "defaults"]

def list_available_sections(website: str) -> List[str]:
    """列出指定网站的所有可用板块"""
    website_config = CONFIG.get("websites", {}).get(website.lower(), {})
    return list(website_config.get("sections", {}).keys())

def get_website_config(website: str, section: str) -> Dict[str, Any]:
    """获取指定网站和板块的配置"""
    website_config = CONFIG.get("websites", {}).get(website.lower())
    if not website_config:
        raise ValueError(f"未找到网站配置: {website}")

    section_config = website_config.get("sections", {}).get(section.lower())
    if not section_config:
        raise ValueError(f"未找到板块配置: {website}/{section}")

    return {
        "url": section_config.get("url", ""),
        "headers": section_config.get("headers", {}),
        "cookies": section_config.get("cookies", {})
    }
def get_max_fetch_articles() -> int:
    """获取每次抓取的最大文章数"""
    return CONFIG.get("scheduler", {}).get("article_fetch", {}).get("max_articles", 100)

def get_all_website_sections() -> List[Dict[str, str]]:
    """获取所有网站和板块"""
    all_sections = []
    for website in list_available_websites():
        for section in list_available_sections(website):
            all_sections.append({"website": website, "section": section})
    return all_sections

def get_scheduler_config() -> Dict[str, Any]:
    return CONFIG.get("scheduler", {})

def get_api_config() -> Dict[str, Any]:
    return CONFIG.get("api", {})

def get_max_concurrent() -> int:
    return CONFIG.get("scheduler", {}).get("concurrency", {}).get("max_concurrent", 5)

def get_article_fetch_schedule() -> Dict[str, int]:
    fetch_config = CONFIG.get("scheduler", {}).get("article_fetch", {})
    return {
        "hour": fetch_config.get("hour", 2),
        "minute": fetch_config.get("minute", 0)
    }

def get_article_process_interval() -> int:
    return CONFIG.get("scheduler", {}).get("article_process", {}).get("interval_minutes", 10)

# ---------------- 文件变化检测 & 重载 ---------------- #

def has_config_changed() -> bool:
    """检查配置文件是否已更改"""
    global _config_file_mtime
    if not CONFIG_PATH.exists():
        return False
    current_mtime = CONFIG_PATH.stat().st_mtime
    if current_mtime > _config_file_mtime:
        _config_file_mtime = current_mtime
        return True
    return False

def reload_configs() -> bool:
    """重新加载配置"""
    global CONFIG
    try:
        CONFIG = load_config()
        return True
    except Exception as e:
        logger.error(f"重新加载配置失败: {e}")
        return False
