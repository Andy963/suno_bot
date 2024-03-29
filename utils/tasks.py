#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date     : 2024/3/28
# @FileName : tasks.py # noqa
# Created by; Andy963
from aiogram import Bot

import config
from db import db
from utils.logger import FileSplitLogger
from utils.suno import SongsGen

task_logger = FileSplitLogger("./logs/tasks.log").logger


async def update_cookie_session_date(bot: Bot):
    task_logger.info("update cookie session start:")
    cks = db.get_all_cookie()
    for ck in cks:
        sg = SongsGen(ck.content)
        rs = sg.get_session_expire_date()
        task_logger.info(f"{ck.id} session updated and will expired at {rs}")
        if rs:
            db.update_cookie_session_expired(ck, rs)
            await bot.send_message(
                config.bot_id,
                f"{ck.id} session updated and will expired at {rs}",
                disable_notification=True,
            )


async def update_cookie_left_count(bot: Bot):
    task_logger.info("update cookie left count start:")
    cks = db.get_all_cookie()
    for ck in cks:
        sg = SongsGen(ck.content)
        rs = sg.get_limit_left()
        db.update_cookie(ck.id, left_counts=rs)
        task_logger.info(f"ck id: {ck.id} left count updated to {rs}")
        await bot.send_message(
            config.bot_id,
            f"{ck.id} left count updated to {rs}",
            disable_notification=True,
        )
