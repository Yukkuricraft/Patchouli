#!/usr/bin/env python3
import os
import sys
import logging
import logging.config

logging.config.fileConfig("logging.conf")

from pathlib import Path

path_root = Path(__file__).parents[1]
sys.path.append(str(path_root))

from typing import Optional, Set, Dict, List

import src.utils as utils
from src.mytypes import *
from src.exceptions import (
    UnidentifiablePluginDirException,
)


PLUGIN_PATH_BASE = "/var/lib/yukkuricraft/prod/plugins"

PLUGIN_FOLDERS_TO_IGNORE = [
    "Updater",
    "archive",
    "bStats",
]

# List of directories in the plugin folder.
# Eg, for {'ChatFeelings': ['Data']} => "ChatFeelings/Data/* will be ignored.
# YAML_CONFIG_PATHS_TO_IGNORE: Dict[PluginName,List[Path]] = [
#    "InventoryRollbackPlus": ["backups"],
#    "InventoryRollback": ["saves"],
#    "Essentials": ["userdata"],
#    "ChatFeelings": ["Data"],
# ]
YAML_CONFIG_PATHS_TO_IGNORE: List[Path] = [
    "InventoryRollbackPlus/backups",
    "InventoryRollback/saves",
    "Essentials/userdata",
    "ChatFeelings/Data",
]


class Patchouli:
    logger: logging.Logger

    plugin_path_base: Path = Path(PLUGIN_PATH_BASE)

    plugin_names: Set[PluginName] = set()
    plugin_jar_mapping: Dict[PluginName, PluginJar] = {}
    plugin_dir_mapping: Dict[PluginName, PluginDir] = {}
    plugin_config_mapping: Dict[PluginName, List[PluginConfigFile]] = {}
    plugin_data_mapping: Dict[PluginName, List[PluginDataFile]] = {}

    yaml_config_paths_to_ignore: List[Path]

    discarded_files: Set[Path] = set()

    def __init__(self, logger=None):
        self.logger = logger if logger is not None else logging.getLogger(__name__)

        self.yaml_config_paths_to_ignore = [
            self.plugin_path_base / ignored_path
            for ignored_path in YAML_CONFIG_PATHS_TO_IGNORE
        ]

    def get_config_files_from_path(self, plugin_dir: PluginDir) -> List[str]:
        # TODO: Globbing with ** is slow - esp with dirs like dynmap. Write a wrapper.

        all_files = utils.find_all_files_with_exts(
            plugin_dir, [".yml", ".yaml", ".conf"], self.yaml_config_paths_to_ignore
        )
        all_files = list(plugin_dir.glob("**/*.yml"))

        # Temp
        self.discarded_files.update(
            list(filter(lambda f: not utils.filter_ignored_paths(f), all_files))
        )

        all_files = list(
            filter(
                utils.filter_ignored_paths,
                all_files,
            )
        )

        return all_files

    def populate_plugin_data(self) -> None:
        # Jars
        jar_paths = [
            x
            for x in self.plugin_path_base.iterdir()
            if x.is_file() and x.suffix == ".jar"
        ]

        for jar_path in jar_paths:
            plugin_name = utils.get_plugin_name_from_jar(jar_path)

            self.plugin_names.add(plugin_name)
            self.plugin_jar_mapping[plugin_name] = jar_path

        # Directories (if created by plugin)
        plugin_dirs = [
            x
            for x in self.plugin_path_base.iterdir()
            if x.is_dir() and x.name not in PLUGIN_FOLDERS_TO_IGNORE
        ]

        for plugin_dir in plugin_dirs:
            plugin_name = plugin_dir.name

            if plugin_name not in self.plugin_names:
                raise UnidentifiablePluginDirException(plugin_dir)

            self.plugin_dir_mapping[plugin_name] = plugin_dir

        # Config files - if a directory exists.
        for plugin_name, plugin_dir_path in self.plugin_dir_mapping.items():
            files = self.get_config_files_from_path(plugin_dir_path)
            self.plugin_config_mapping[plugin_name] = files

    def print_plugin_data(self) -> None:
        for plugin in self.plugin_names:
            self.logger.info("")
            self.logger.info(f"Plugin: {plugin}")
            self.logger.info(f"Jar: {self.plugin_jar_mapping[plugin]}")

            if plugin in self.plugin_dir_mapping:
                self.logger.info(f"Folder: {self.plugin_dir_mapping[plugin]}")
            else:
                self.logger.info("!! Folder: This plugin does not generate a folder")

            if plugin in self.plugin_config_mapping:
                for file in self.plugin_config_mapping[plugin]:
                    self.logger.info(f"- ConfigFile: {file}")

            if plugin in self.plugin_data_mapping:
                for file in self.plugin_data_mapping[plugin]:
                    self.logger.info(f"- DataFile: {file}")

    def run(self) -> None:
        self.populate_plugin_data()

        self.logger.info("")
        self.logger.info("")
        for file in self.discarded_files:
            pass  # self.logger.info(f"Discarded file: {file}")

        self.logger.info("")
        self.logger.info("")

        self.print_plugin_data()


if __name__ == "__main__":

    patchy = Patchouli()
    patchy.run()
