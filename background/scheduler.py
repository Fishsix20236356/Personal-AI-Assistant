"""Scheduler — APScheduler 定时任务。"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.background.wechat_sync import run_wechat_sync
from app.reports.daily_report import DailyReportService
from app.wechat.search_store import WeChatSearchStore
from config.settings import settings


def create_scheduler(
    wechat_search: WeChatSearchStore,
    report_service: DailyReportService,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.DEFAULT_TIMEZONE)

    # 日报生成
    def parse_cron(cron_str: str):
        parts = cron_str.split()
        return {
            "minute": parts[0] if len(parts) > 0 else "0",
            "hour": parts[1] if len(parts) > 1 else "8",
            "day": parts[2] if len(parts) > 2 else "*",
            "month": parts[3] if len(parts) > 3 else "*",
            "day_of_week": parts[4] if len(parts) > 4 else "*",
        }

    cron_kwargs = parse_cron(settings.DAILY_REPORT_CRON)

    async def daily_report_job():
        from datetime import date
        today = date.today().isoformat()
        await report_service.generate(today)

    scheduler.add_job(daily_report_job, "cron", **cron_kwargs, id="daily_report")

    # 微信增量同步（每小时）
    async def wechat_sync_job():
        await run_wechat_sync(wechat_search)

    scheduler.add_job(wechat_sync_job, "interval", hours=1, id="wechat_sync")

    return scheduler
