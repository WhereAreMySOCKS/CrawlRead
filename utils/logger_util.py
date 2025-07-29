import logging

# 创建通用 logger 实例
logger = logging.getLogger("article_extractor")

# 避免重复添加 handler（只初始化一次）
if not logger.handlers:
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 可选：写入文件
    # file_handler = logging.FileHandler('logs/article.log', encoding='utf-8')
    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)
