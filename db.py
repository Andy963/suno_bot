#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date     : 2024/3/25
# @FileName : db.py
# Created by; Andy963
from datetime import datetime, timedelta
from functools import partial

import pytz
from sqlalchemy import Column, Integer, String, JSON, Boolean, func
from sqlalchemy import create_engine, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

TIMEZONE = "Asia/Shanghai"


def get_cur_time(tz=TIMEZONE, delta_days=0):
    current_time = datetime.now(pytz.timezone(tz))
    if delta_days != 0:
        current_time += timedelta(days=delta_days)
    return current_time


class Cookie(Base):
    __tablename__ = "cookie"
    id = Column(Integer, primary_key=True)
    content = Column(String)
    left_counts = Column(Integer, default=0)
    is_working = Column(Boolean, default=False)
    session_expired = Column(DateTime, default=partial(get_cur_time, delta_days=7))
    remark = Column(String, default="")
    created = Column(DateTime, default=get_cur_time)
    updated = Column(DateTime, default=get_cur_time, onupdate=get_cur_time)


class Song(Base):
    __tablename__ = "song"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    lyric = Column(String)
    audio_url = Column(JSON, default=[])
    video_url = Column(JSON, default=[])
    created = Column(DateTime, default=get_cur_time)
    updated = Column(DateTime, default=get_cur_time, onupdate=get_cur_time)


class DB:
    def __init__(self, url="sqlite:///db.sqlite"):
        self.engine = create_engine(url=url, connect_args={"check_same_thread": False})
        self.Session = sessionmaker(bind=self.engine)

    def get_all_cookie(self):
        with self.Session() as session:
            cookies = session.query(Cookie).all()
            return cookies

    def update_cookie_session_expired(self, cookie, dt):
        with self.Session() as session:
            cookie.session_expired = dt
            session.commit()
            return cookie

    def get_alive_cookie(self):
        """get a list of alive and idle cookie can be used to draw"""
        with self.Session() as session:
            cur_time = datetime.now(pytz.timezone(TIMEZONE))
            cookies = (
                session.query(Cookie)
                .filter(
                    Cookie.left_counts > 0,
                    Cookie.is_working == False,  # noqa: E712
                )
                .first()
            )
            return cookies

    def create_cookie(self, content: str, left_counts: int = 5):
        with self.Session() as session:
            cookie = Cookie(
                content=content,
                is_working=False,
                left_counts=left_counts,
                is_expired=False,
            )
            session.add(cookie)
            session.commit()
            return cookie

    def get_cookie_by_content(self, content: str):
        with self.Session() as session:
            cookie = session.query(Cookie).filter(Cookie.content == content).first()
            return cookie

    def update_cookie(
        self,
        cookie_id: int,
        left_counts: int,
        session_expired: datetime = None,
        is_working: bool = False,
    ):
        with self.Session() as session:
            cookie = session.query(Cookie).filter(Cookie.id == cookie_id).first()
            cookie.left_counts = left_counts
            if session_expired:
                cookie.session_expired = session_expired
            cookie.is_working = is_working
            session.commit()
            return cookie

    def get_left_count(self):
        with self.Session() as session:
            cur_time = datetime.now(pytz.timezone(TIMEZONE))
            total_left_counts = (
                session.query(func.sum(Cookie.left_counts))
                .filter(
                    Cookie.left_counts > 0,
                    Cookie.is_working == False,  # noqa: E712
                )
                .scalar()
            )
            return total_left_counts if total_left_counts else 0

    def create_song(
        self, name: str, lyric: str, audio_url: list, video_url: list = None
    ):
        with self.Session() as session:
            song = Song(
                name=name, lyric=lyric, audio_url=audio_url, video_url=video_url
            )
            session.add(song)
            session.commit()
            return song


db = DB()
__all__ = [
    "db",
    "Base",
]
