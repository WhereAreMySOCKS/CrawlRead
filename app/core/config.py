from typing import Dict, Any, List

# 网站配置
WEBSITE_CONFIGS = {
    # CSMonitor网站配置
    "csmonitor": {
        # 板块配置
        "sections": {
            "business": {
                "url": "https://www.csmonitor.com/Business",
                "headers": {
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
                },
                "cookies": {}
            },
            # 可以添加更多板块，如体育、政治等
            "world": {
                "url": "https://www.csmonitor.com/World",
                "headers": {
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
                },
                "cookies": {}
            },
            "usa": {
                "url": "https://www.csmonitor.com/USA",
                "headers": {
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
                },
                "cookies": {}
            }
        }
    },
    # 可以添加更多网站配置
}


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


def list_available_websites() -> List[str]:
    """
    列出所有可用的网站
    
    Returns:
        网站标识符列表
    """
    return list(WEBSITE_CONFIGS.keys())


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