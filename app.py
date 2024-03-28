#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date     : 2024/3/25
# @FileName : app.py
# Created by; Andy963
import asyncio

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from cmd_router import cmd_router, menus
from utils.tasks import update_cookie_session_date, update_cookie_left_count

# Bot token can be obtained via https://t.me/BotFather


# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()

dp.include_router(cmd_router)


async def telegram_bot() -> None:
    bot = Bot(config.telegram_token)
    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        update_cookie_session_date,
        "cron",
        hour="3",
        misfire_grace_time=600,
        args=[
            bot,
        ],
    )
    scheduler.add_job(
        update_cookie_left_count,
        "cron",
        hour="0,12",
        misfire_grace_time=600,
        args=[
            bot,
        ],
    )
    # set bot menu
    await bot.set_my_commands(menus)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(telegram_bot())
