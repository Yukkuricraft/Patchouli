#!/usr/bin/env python3
import sys
from pathlib import Path

path_root = Path(__file__).parents[1]
sys.path.append(str(path_root))

import os
import yaml
from zipfile import ZipFile

from typing import Set, Dict, List

from src.exceptions import (
    InvalidPathException,
    InvalidPluginException,
    UnidentifiablePluginFolderException,
)


PLUGIN_PATH_BASE = "/var/lib/yukkuricraft/prod/plugins"

PLUGIN_FOLDERS_TO_IGNORE = [
    "Updater",
    "archive",
    "bStats",
]


class Patchouli:
    plugin_path_base: Path = Path(PLUGIN_PATH_BASE)

    plugin_names: Set = set()
    plugin_jar_mapping: Dict = {}
    plugin_dir_mapping: Dict = {}
    plugin_config_mapping: Dict = {}
    plugin_data_mapping: Dict = {}

    @staticmethod
    def get_plugin_name_from_jar(path: Path) -> str:
        if path.suffix != ".jar":
            raise InvalidPathException

        with ZipFile(path, "r").open("plugin.yml") as f:
            yaml_as_dict = yaml.safe_load(f)
            if "name" not in yaml_as_dict:
                raise InvalidPluginException
            return yaml_as_dict["name"]

    yaml_paths_to_ignore = [
        "InventoryRollbackPlus/backups",
        "InventoryRollback/saves",
        "Essentials/userdata",
        "ChatFeelings/Data",
    ]

    def get_config_files_from_path(self, path: Path) -> List[str]:
        all_files = list(path.glob("**/*.yml"))
        all_files = list(
            filter(
                lambda fname: not any(
                    [
                        path_to_ignore in str(fname)
                        for path_to_ignore in self.yaml_paths_to_ignore
                    ]
                ),
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
            plugin_name = self.__class__.get_plugin_name_from_jar(jar_path)

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
                raise UnidentifiablePluginFolderException(plugin_dir)

            self.plugin_dir_mapping[plugin_name] = plugin_dir

        # Config files - if a directory exists.
        for plugin_name, plugin_folder_path in self.plugin_dir_mapping.items():
            files = self.get_config_files_from_path(plugin_folder_path)
            self.plugin_config_mapping[plugin_name] = files

    def print_plugin_data(self) -> None:
        for plugin in self.plugin_names:
            print()
            print(f"Plugin: {plugin}")
            print(f"Jar: {self.plugin_jar_mapping[plugin]}")

            if plugin in self.plugin_dir_mapping:
                print(f"Folder: {self.plugin_dir_mapping[plugin]}")
            else:
                print("!! Folder: This plugin does not generate a folder")

            if plugin in self.plugin_config_mapping:
                for file in self.plugin_config_mapping[plugin]:
                    print(f"- ConfigFile: {file}")

            if plugin in self.plugin_data_mapping:
                for file in self.plugin_data_mapping[plugin]:
                    print(f"- DataFile: {file}")

    def run(self) -> None:
        self.populate_plugin_data()

        self.print_plugin_data()


if __name__ == "__main__":
    patchy = Patchouli()
    patchy.run()
