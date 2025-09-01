import asyncio
import logging
from datetime import datetime
import random
from typing import List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.services.article.website_service import WebsiteFetchService
from app.services.article.article_service import ArticleParserService, ArticleExtractorService
from app.services.article.storage_service import ArticleStorageService
from app.models.monitor_entities import MonitorArticle
from app.core.config import get_all_website_sections, get_article_fetch_schedule, get_article_process_interval, \
    get_max_concurrent


class ArticleSchedulerService:
    """
    定时文章获取与保存服务
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

        # 从配置中读取最大并发数
        max_concurrent = get_max_concurrent()

        self.website_service = WebsiteFetchService()
        self.article_parser = ArticleParserService()
        self.article_extractor = ArticleExtractorService(max_concurrent=max_concurrent)
        self.storage_service = ArticleStorageService()

        # 存储待处理的文章队列
        self._article_queue: List[MonitorArticle] = []
        # 存储已处理的文章URL，避免重复处理
        self._processed_articles: set = set()
        # 当前正在处理的文章索引
        self._current_index: int = 0
        # 是否有活动的获取任务
        self._fetching_active: bool = False

        # 添加日志记录
        self._setup_logging()

    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.log = logging.getLogger("ArticleScheduler")

    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            # 从配置中读取调度时间
            fetch_schedule = get_article_fetch_schedule()
            hour = fetch_schedule.get("hour", 2)
            minute = fetch_schedule.get("minute", 0)

            # 添加每天文章列表获取任务
            self.scheduler.add_job(
                self.fetch_article_list,
                CronTrigger(hour=hour, minute=minute),  # 使用配置的时间
                id='daily_article_fetch',
                replace_existing=True
            )

            # 从配置中读取处理间隔
            process_interval = get_article_process_interval()

            # 添加定期文章保存任务
            self.scheduler.add_job(
                self.process_next_article,
                IntervalTrigger(minutes=process_interval),  # 使用配置的间隔
                id='article_saving',
                replace_existing=True
            )

            # 启动时立即执行一次文章获取
            self.scheduler.add_job(
                self.fetch_article_list,
                'date',
                run_date=datetime.now(),
                id='initial_fetch',
                replace_existing=True
            )

            self.scheduler.start()
            self.log.info(f"文章调度器已启动，获取时间：{hour}:{minute}，处理间隔：{process_interval}分钟")

    def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.log.info("文章调度器已关闭")
        self._article_queue.clear()
        self.log.info("任务队列已清空")

    async def fetch_article_list(self):
        """获取文章列表的定时任务"""
        if self._fetching_active:
            self.log.warning("已有活动的获取任务，跳过本次执行")
            return

        self._fetching_active = True
        self.log.info("开始执行文章列表获取任务")

        try:
            # 从配置文件中获取所有网站和板块配置
            websites_to_fetch = get_all_website_sections()

            # 如果没有找到任何配置，使用默认值或记录错误
            if not websites_to_fetch:
                self.log.error("未找到任何网站或板块配置，请检查配置文件")
                self._fetching_active = False
                return

            self.log.info(f"计划获取 {len(websites_to_fetch)} 个网站/板块的内容")
            new_articles_count = 0
            fetch_count = 0

            for site_info in websites_to_fetch:
                website = site_info["website"]
                section = site_info["section"]

                self.log.info(f"开始获取 {website}/{section} 的文章列表")

                # 获取文章列表
                fetch_response = await self.website_service.fetch_content(website, section)
                if not fetch_response.success:
                    self.log.error(f"获取 {website}/{section} 内容失败: {fetch_response.error}")
                    continue

                fetch_count += 1

                # 解析文章列表
                article_list_response = await self.article_parser.parse_article_list(
                    website, section, fetch_response.fetch_result
                )

                if not article_list_response.success or not article_list_response.articles:
                    self.log.error(f"解析 {website}/{section} 文章列表失败: {article_list_response.error}")
                    continue

                section_new_count = 0

                # 打乱取固定数量的文章
                max_articles = get_article_fetch_schedule().get("max_fetch_count", 10)
                random.shuffle(article_list_response.articles)  # 先打乱
                article_list_response.articles = article_list_response.articles[:max_articles]
                # 将新文章添加到队列中
                for article in article_list_response.articles:
                    if article.url not in self._processed_articles:
                        self._article_queue.append(article)
                        new_articles_count += 1
                        section_new_count += 1

                self.log.info(f"从 {website}/{section} 获取到 {len(article_list_response.articles)} 篇文章，"
                              f"新增 {section_new_count} 篇")

            # 汇总报告
            self.log.info(f"任务完成，成功获取 {fetch_count}/{len(websites_to_fetch)} 个板块，"
                          f"共添加 {new_articles_count} 篇新文章到队列")

        except Exception as e:
            self.log.exception(f"获取文章列表时发生错误: {e}")
        finally:
            self._fetching_active = False

    async def process_next_article(self):
        """处理队列中的下一篇文章"""
        if not self._article_queue:
            self.log.info("没有待处理的文章，跳过本次处理")
            # 如果队列为空，尝试获取新文章
            if not self._fetching_active:
                asyncio.create_task(self.fetch_article_list())
            return

        # 获取下一篇待处理的文章
        if self._current_index >= len(self._article_queue):
            self._current_index = 0  # 重置索引，从头开始处理

        article = self._article_queue[self._current_index]
        self._current_index += 1

        # 检查文章是否已处理
        if article.url in self._processed_articles:
            self.log.info(f"文章已处理过，跳过: {article.title}")
            return await self.process_next_article()  # 递归处理下一篇

        self.log.info(f"开始处理文章: {article.title}")

        try:
            # 提取文章内容
            result = await self.article_extractor.extract_single_article_by_url(article.url)

            if result.get('success'):
                # 保存文章
                save_result = await self.storage_service.save_article(result)

                if save_result:
                    self.log.info(f"文章已成功保存: {article.title}")
                    # 记录已处理的文章URL
                    self._processed_articles.add(article.url)
                else:
                    self.log.warning(f"文章保存失败: {article.title}")
            else:
                self.log.warning(f"文章内容提取失败: {article.title} - {result.get('error', '未知错误')}")

        except Exception as e:
            self.log.exception(f"处理文章时发生错误: {article.title} - {e}")


# 创建全局实例
article_scheduler = ArticleSchedulerService()