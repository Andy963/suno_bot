#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date     : 2024/3/25
# @FileName : config.py
# Created by; Andy963
from pathlib import Path

import yaml

config_dir = Path("/etc/suno")
# load yaml config
with open(config_dir / "config.yaml", "r") as f:
    config_yaml = yaml.safe_load(f)

telegram_token = config_yaml.get("telegram_token")
bot_id = config_yaml.get("bot_id")
