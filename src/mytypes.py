import re
import enum

from pathlib import Path
from typing import TypeAlias

from src.common.config import get_config

PluginName: TypeAlias = str
PluginJar: TypeAlias = Path
PluginDir: TypeAlias = Path
PluginConfigFile: TypeAlias = Path
PluginDataFile: TypeAlias = Path

envs = {"VCS": "vcs"}

config = get_config()
for env_path in Path(config.base_path).iterdir():
    env_name = env_path.name
    if re.match(config.env_name_regex, env_name):
        envs[env_name.upper()] = env_name.lower()

# https://github.com/python/mypy/issues/5317
Environment: enum.Enum = enum.Enum("Environment", envs)  # type: ignore
