#!/usr/bin/env python

import yaml
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

    def listnodes(self) -> List[str]:
        return self.data.keys()

    def items(
        self,
    ) -> List[Tuple[str,]]:
        return self.data.items()

    def __init__(self, data: Dict):
        self.data = {}

        for k, v in data.items():
            if type(v) in [int, float, str, bool, list]:
                self.data[k] = v
            else:
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
