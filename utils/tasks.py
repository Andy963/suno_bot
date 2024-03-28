#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date     : 2024/3/28
# @FileName : tasks.py # noqa
# Created by; Andy963
from aiogram import Bot

import config
from db import db
from utils.suno import SongsGen


async def update_cookie_session_date(bot: Bot):
    cks = db.get_all_cookie()
    for ck in cks:
        sg = SongsGen(ck.content)
        rs = sg.get_session_expire_date()
        if rs:
            db.update_cookie_session_expired(ck, rs)
            await bot.send_message(
                config.bot_id,
                f"{ck.id} session updated and will expired at {rs}",
                disable_notification=True,
            )


async def update_cookie_left_count(bot: Bot):
    cks = db.get_all_cookie()
    for ck in cks:
        sg = SongsGen(ck.content)
        rs = sg.get_limit_left()
        db.update_cookie(ck.id, left_counts=rs)

        await bot.send_message(
            config.bot_id,
            f"{ck.id} left count updated to {rs}",
            disable_notification=True,
        )
