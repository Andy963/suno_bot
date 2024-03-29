#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date     : 2024/3/25
# @FileName : cmd_router.py
# Created by; Andy963
import time
from pathlib import Path

from aiogram import types, Router, enums
from aiogram.filters import Command
from aiogram.types import (
    BotCommand,
    FSInputFile,
)
from requests import get

from db import db
from utils.logger import FileSplitLogger
from utils.suno import SongsGen

cmd_router = Router()
bot_logger = FileSplitLogger("./logs/bot.log").logger
menu_list = [
    ("/start", "Start"),
    ("/sing", "sing a song"),
    ("/cookie", "add Cookie"),
    ("/count", "get left count"),
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
        db.update_cookie(ck.id, left_count=0, is_working=False)
        await message.answer(
            f"Cookie {ck.id} is is running out of usage."
            f"and disabled, please try again."
        )
        return
    try:
        db.update_cookie(ck.id, left_count - 1, is_working=True)
        song_info = sg.get_songs_info(prompt=prompt)
        song_name = song_info["song_name"]
        lyric = song_info["lyric"]
        song_ids = song_info["song_ids"]
        audio_urls = [f"https://cdn1.suno.ai/{i}.mp3" for i in song_ids]
        video_urls = [f"https://cdn1.suno.ai/{i}.mp4" for i in song_ids]
        db.create_song(
            name=song_name,
            lyric=lyric,
            audio_url=audio_urls,
            video_url=video_urls,
        )
        output_dir = "./output"
        max_retries = 5  # retry to download from suno
        sleep_time = 60  # sleep time at first time
        if not Path(output_dir).exists():
            Path(output_dir).mkdir()
        time.sleep(sleep_time)
        for index, url in enumerate(audio_urls, 1):
            retry_count = 0
            while retry_count < max_retries:
                response = get(url, allow_redirects=False, stream=True)
                if response.status_code == 200:
                    song_file = (
                        Path(output_dir) / f"{song_name.replace(' ', '_')}_{index}.mp3"
                    )
                    with open(song_file, "wb") as output_file:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                output_file.write(chunk)
                    # check file size
                    if song_file.stat().st_size < 1024 or (not song_file.exists()):
                        bot_logger.warning(
                            f"Downloaded song {song_name} failed, file size is too small"
                        )
                        song_file.unlink()
                        retry_count += 1
                        bot_logger.warning(
                            f"Retrying download for song {song_file.name}, attempt {retry_count}"
                        )
                        time.sleep(sleep_time)
                        sleep_time = max(sleep_time - 10, 10)
                    else:
                        af = FSInputFile(song_file, filename=song_file.name)
                        await message.bot.send_chat_action(
                            message.chat.id, enums.ChatAction.UPLOAD_VOICE
                        )
                        await message.bot.send_audio(
                            message.chat.id, audio=af, caption=lyric
                        )
                        song_file.unlink()
                        break
                else:
                    retry_count += 1
                    bot_logger.warning(
                        f"Could not download song, retry attempt {retry_count}"
                    )
                    time.sleep(sleep_time)
                    sleep_time = max(sleep_time - 10, 10)
    except Exception as e:
        bot_logger.error(f"get songs failed with: {e}")
        await message.answer("get songs failed please check the log")
    finally:
        db.update_cookie(ck.id, left_count - 1, is_working=False)
