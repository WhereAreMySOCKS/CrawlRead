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
from app.core.config import (
    get_all_website_sections,
    get_article_fetch_schedule,
    get_article_process_interval,
    get_max_concurrent,
)

class ArticleSchedulerService:
    """
    定时文章获取与保存服务
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

        # 并发限制
        max_concurrent = get_max_concurrent()
        self.website_service = WebsiteFetchService()
        self.article_parser = ArticleParserService()
        self.article_extractor = ArticleExtractorService(max_concurrent=max_concurrent)
        self.storage_service = ArticleStorageService()

        # 任务队列与缓存
        self._article_queue: List[MonitorArticle] = []
        self._processed_articles: set = set()
        self._current_index: int = 0

        # 锁：保证同一时刻只有一个 fetch 任务
        self._fetch_lock = asyncio.Lock()

        # 日志
        self._setup_logging()

    # ------------------------------------------------------------------
    # 日志
    # ------------------------------------------------------------------
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.log = logging.getLogger("ArticleScheduler")

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def start(self):
        """幂等地启动调度器：先清空旧 job，再重新添加"""
        if self.scheduler.running:
            self.scheduler.remove_all_jobs()
        else:
            self.scheduler.start()

        schedule_conf = get_article_fetch_schedule()
        hour = schedule_conf.get("hour", 2)
        minute = schedule_conf.get("minute", 0)
        process_interval = get_article_process_interval()

        # 每日定时抓取
        self.scheduler.add_job(
            self.fetch_article_list,
            CronTrigger(hour=hour, minute=minute),
            id='daily_article_fetch',
            replace_existing=True
        )

        # 周期性处理文章
        self.scheduler.add_job(
            self.process_next_article,
            IntervalTrigger(minutes=process_interval),
            id='article_saving',
            replace_existing=True
        )

        # 立即执行一次
        self.scheduler.add_job(
            self.fetch_article_list,
            'date',
            run_date=datetime.now(),
            id='initial_fetch',
            replace_existing=True
        )

        self.log.info(
            f"文章调度器已启动，获取时间：{hour}:{minute}，处理间隔：{process_interval}分钟"
        )

    def shutdown(self):
        """彻底关闭调度器，移除全部 job，清空队列与缓存"""
        if self.scheduler.running:
            self.scheduler.remove_all_jobs()
            self.scheduler.shutdown()
            self.log.info("文章调度器已关闭")

        self._article_queue.clear()
        self._processed_articles.clear()
        self._current_index = 0
        self.log.info("任务队列与缓存已清空")

    # ------------------------------------------------------------------
    # 业务逻辑
    # ------------------------------------------------------------------
    async def fetch_article_list(self):
        """获取文章列表的定时任务（带锁，避免并发）"""
        async with self._fetch_lock:
            self.log.info("开始执行文章列表获取任务")

            try:
                websites = get_all_website_sections()
                if not websites:
                    self.log.error("未找到任何网站或板块配置")
                    return

                max_articles = get_article_fetch_schedule().get("max_fetch_count", 10)
                new_total = 0
                fetch_ok = 0

                for site in websites:
                    site_name, section = site["website"], site["section"]
                    fetch_resp = await self.website_service.fetch_content(site_name, section)
                    if not fetch_resp.success:
                        self.log.error(
                            f"获取 {site_name}/{section} 内容失败: {fetch_resp.error}"
                        )
                        continue

                    parse_resp = await self.article_parser.parse_article_list(
                        site_name, section, fetch_resp.fetch_result
                    )
                    if not parse_resp.success or not parse_resp.articles:
                        self.log.error(
                            f"解析 {site_name}/{section} 文章列表失败: {parse_resp.error}"
                        )
                        continue

                    fetch_ok += 1
                    random.shuffle(parse_resp.articles)
                    new_this_section = 0
                    for art in parse_resp.articles[:max_articles]:
                        if art.url not in self._processed_articles:
                            self._article_queue.append(art)
                            new_this_section += 1
                            new_total += 1
                    self.log.info(
                        f"从 {site_name}/{section} 获取 {len(parse_resp.articles)} 篇，新增 {new_this_section} 篇"
                    )

                self.log.info(
                    f"任务完成，成功获取 {fetch_ok}/{len(websites)} 个板块，共添加 {new_total} 篇新文章到队列"
                )

            except Exception as e:
                self.log.exception(f"获取文章列表时发生错误: {e}")

    async def process_next_article(self):
        """处理队列中的下一篇文章"""
        if not self._article_queue:
            self.log.info("没有待处理的文章，跳过本次处理")
            # 队列为空且未在 fetch 时，触发一次新的抓取
            if not self._fetch_lock.locked():
                asyncio.create_task(self.fetch_article_list())
            return

        if self._current_index >= len(self._article_queue):
            self._current_index = 0

        article = self._article_queue[self._current_index]
        self._current_index += 1

        if article.url in self._processed_articles:
            self.log.info(f"文章已处理过，跳过: {article.title}")
            return await self.process_next_article()

        self.log.info(f"开始处理文章: {article.title}")
        try:
            extract_result = await self.article_extractor.extract_single_article_by_url(
                article.url
            )
            if extract_result.get("success"):
                saved = await self.storage_service.save_article(extract_result)
                if saved:
                    self._processed_articles.add(article.url)
                    self.log.info(f"文章已成功保存: {article.title}")
                else:
                    self.log.warning(f"文章保存失败: {article.title}")
            else:
                self.log.warning(
                    f"文章内容提取失败: {article.title} - {extract_result.get('error', '未知错误')}"
                )
        except Exception as e:
            self.log.exception(f"处理文章时发生错误: {article.title} - {e}")


# ----------------------------------------------------------
# 全局实例
# ----------------------------------------------------------
article_scheduler = ArticleSchedulerService()