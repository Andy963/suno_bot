#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date     : 2024/3/25
# @FileName : cmd_router.py
# Created by; Andy963
from aiogram import types, Router, enums
from aiogram.filters import Command
from aiogram.types import BotCommand, FSInputFile

from db import db
from utils.suno import SongsGen

cmd_router = Router()

menu_list = [
    ("/start", "Start"),
    ("/sing", "sing a song"),
    ("cookie", "add Cookie"),
]
menus = [BotCommand(command=cmd, description=dsp) for cmd, dsp in menu_list]


@cmd_router.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Hello, this a  suno bot.")


@cmd_router.message(Command("count"))
async def count(message: types.Message):
    ct = db.get_left_count()
    await message.answer(
        f'Currently you can create at most {ct} song{"s" if ct > 1 else ""}.'
    )


@cmd_router.message(Command("cookie"))
async def new_cookie(message: types.Message):
    text = message.text
    cookie = text.split("/cookie")[-1]
    cookie = cookie.strip()
    if not cookie or len(cookie) < 10:
        await message.answer("Cookie is invalid")
        return
    if db.get_cookie_by_content(cookie):
        await message.answer("Cookie already exists")
        return
    db.create_cookie(content=cookie)
    await message.answer("Cookie saved")


@cmd_router.message(Command("sing"))
async def new_song(message: types.Message):
    text = message.text
    prompt = text.split("/sing")[-1]
    prompt = prompt.strip()
    if not prompt or len(prompt) < 2:
        await message.answer("Prompt is invalid")
        return
    await message.answer("Singing...")
    ck = db.get_alive_cookie()
    if not ck:
        await message.answer("Idle cookie is not available")
        return
    sg = SongsGen(ck.content)
    left_count = sg.get_limit_left()
    if left_count <= 0:
        await message.answer("Cookie is is running out of usage.")
        return
    try:
        db.update_cookie(ck.id, left_count - 1, is_working=True)
        song_file, lyric, song_name, song_urls = sg.save_songs(prompt=prompt)
        await message.bot.send_chat_action(
            message.chat.id, enums.ChatAction.UPLOAD_VOICE
        )
        af = FSInputFile(song_file, filename=song_file.name)
        await message.bot.send_audio(message.chat.id, audio=af, caption=lyric)
        song_file.unlink()
        db.create_song(
            name=song_name,
            lyric=lyric,
            audio_url=song_urls,
        )
    except Exception as e:
        print(e)
        await message.answer("Error occurred")
    finally:
        db.update_cookie(ck.id, left_count - 1,is_working=False)
