#!/usr/bin/env python

import yaml  # type: ignore
from pprint import pprint
from pathlib import Path

from typing import Optional, Dict, List, Tuple


class ConfigNode:
    data: Dict

    def __getattr__(self, name):
        rtn = self.data[name]
        return rtn

    def __getitem__(self, name):
        return self.data[name]

    def __contains__(self, item):
        return item in self.data

    def __str__(self):
        rtn = "{"
        for k, v in self.data.items():
            rtn += f"{k}: {v}, "
        rtn += "}"

        return rtn

    def listnodes(self) -> List[str]:
        return list(self.data.keys())

    def get_or_default(self, name, default=None):
        if name not in self.data:
            return default
        return self.__getitem__(name)

    def items(
        self,
    ) -> List[Tuple[str,]]:
        return list(self.data.items())  # type: ignore

    def __init__(self, data: Dict):
        self.data = {}

        for k, v in data.items():
            if type(v) in [int, float, str, bool, list]:
                self.data[k] = v
            elif v is not None:
                self.data[k] = ConfigNode(dict(v))


class Config(ConfigNode):
    data: Dict
    config_path: Path

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = (
            config_path if config_path is not None else Path("config.yml")
        )

        with open(self.config_path, "r") as f:
            self.data = yaml.safe_load(f)

        super().__init__(self.data)

    def printconfig(self):
        pprint(self.data)


__CONFIG = None


def get_config() -> Config:
    global __CONFIG

    if __CONFIG is None:
        __CONFIG = Config()

    return __CONFIG
