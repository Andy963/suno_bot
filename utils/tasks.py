#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date     : 2024/3/28
# @FileName : tasks.py # noqa
# Created by; Andy963
from datetime import date

from aiogram import Bot

import config
from db import db
from utils.logger import FileSplitLogger
from utils.suno import SongsGen

task_logger = FileSplitLogger("./logs/tasks.log").logger


async def update_session_date(bot: Bot):
    task_logger.info("update cookie session start:")
    cks = db.get_all_cookie()
    msg = []
    for ck in cks:
        sg = SongsGen(ck.content)
        rs = sg.get_session_expire_date()
        msg_ = (
            f"Cookie: {ck.id} session updated and will expired at "
            f"{rs.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        task_logger.info(msg_)
        msg.append(msg_)
        if rs:
            db.update_session_expired(ck.id, rs)
    await bot.send_message(
        config.bot_id,
        "\n".join(msg),
        disable_notification=True,
    )


async def update_cookie_left_count(bot: Bot):
    task_logger.info("update cookie left count start:")
    cks = db.get_all_cookie()
    msg = []
    for ck in cks:
        sg = SongsGen(ck.content)
        rs = sg.get_limit_left()
        db.update_cookie(ck.id, left_counts=rs)
        msg_ = f"Cookie: {ck.id} left count updated to {rs}"
        task_logger.info(msg_)
        msg.append(msg_)
    await bot.send_message(
        config.bot_id,
        "\n".join(msg),
        disable_notification=True,
    )


async def notify_session_expire(bot: Bot):
    task_logger.info("notify session expire start:")
    cks = db.get_all_cookie()
    msg = []
    today = date.today()
    for ck in cks:
        sg = SongsGen(ck.content)
        rs = sg.get_session_expire_date()
        if rs:
            if rs.date() == today:
                msg_ = f"Cookie: {ck.id} will expire today"
                msg.append(msg_)
    await bot.send_message(
        config.bot_id,
        "\n".join(msg),
        disable_notification=True,
    )
