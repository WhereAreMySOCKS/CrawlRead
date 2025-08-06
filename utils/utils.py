import hashlib
from datetime import datetime

def timestamp_to_datetime(timestamp):
    """Convert Unix timestamp to readable datetime format"""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def generate_article_id(filename: str) -> str:
    """根据文件名生成唯一的文章ID"""
    return hashlib.md5(filename.encode('utf-8')).hexdigest()[:12]