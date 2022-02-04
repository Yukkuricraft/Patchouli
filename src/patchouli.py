#!/usr/bin/env python3
import os
import sys
import shutil

import logging
import logging.config

from pathlib import Path

configpath = Path(__file__).parent / "logging.conf"
logging.config.fileConfig(configpath)

path_root = Path(__file__).parents[1]
sys.path.append(str(path_root))

from typing import Optional, Set, Dict, List, Tuple

import src.utils as utils
from src.config import Config
from src.mytypes import *
from src.exceptions import (
    UnidentifiablePluginDirException,
    InvalidEnvironmentException,
)


class Patchouli:
    config: Config
    logger: logging.Logger

    target_env: str
    base_path: Path

    plugin_names: Set[PluginName] = set()
    plugin_jar_mapping: Dict[PluginName, PluginJar] = {}
    plugin_dir_mapping: Dict[PluginName, PluginDir] = {}
    plugin_config_mapping: Dict[PluginName, List[PluginConfigFile]] = {}
    plugin_data_mapping: Dict[PluginName, List[PluginDataFile]] = {}

    discarded_files: Set[Path] = set()

    def __init__(
        self,
        config: Config,
        logger: Optional[logging.Logger] = None,
        target_env: Optional[str] = None,
    ):
        self.config = config
        self.logger = logger if logger is not None else logging.getLogger(__name__)

        self.target_env = (
            target_env if target_env is not None else self.config.default_env
        )
        self.base_path = Path(self.config.base_path)

        plugincfg = self.config.plugins
        self.config_suffixes = plugincfg.config.suffixes
        self.config_paths_to_ignore = {
            plugin_name: [Path(path) for path in paths]
            for plugin_name, paths in plugincfg.config.paths_to_ignore.items()
        }

        self.populate_plugin_data(target_env=self.target_env)

    def get_config_files_from_plugin_dir(
        self, plugin_name: PluginName, plugin_dir: PluginDir
    ) -> Tuple[List[Path], List[Path]]:

        paths_to_ignore = (
            []
            if plugin_name not in self.config_paths_to_ignore
            else self.config_paths_to_ignore[plugin_name]
        )

        (
            all_valid_config_files,
            all_ignored_paths_and_dirs,
        ) = utils.find_all_files_with_exts(
            base_path=plugin_dir,
            extensions=self.config_suffixes,
            paths_to_ignore=paths_to_ignore,
        )

        return all_valid_config_files, all_ignored_paths_and_dirs

    def populate_plugin_data(self, target_env: str) -> None:
        # Jars
        jar_paths = [
            x
            for x in utils.get_plugin_path_base(target_env).iterdir()
            if x.is_file() and x.suffix == ".jar"
        ]

        for jar_path in jar_paths:
            plugin_name = utils.get_plugin_name_from_jar(jar_path)

            self.plugin_names.add(plugin_name)
            self.plugin_jar_mapping[plugin_name] = jar_path

        # Directories (if created by plugin)
        plugin_dirs = [
            x
            for x in utils.get_plugin_path_base(target_env).iterdir()
            if x.is_dir() and x.name not in self.config.plugins.folders_to_ignore
        ]

        for plugin_dir in plugin_dirs:
            plugin_name = plugin_dir.name

            if plugin_name not in self.plugin_names:
                raise UnidentifiablePluginDirException(plugin_dir)

            self.plugin_dir_mapping[plugin_name] = plugin_dir

        # Config files - if a directory exists.
        for plugin_name, plugin_dir_path in self.plugin_dir_mapping.items():
            files, ignored_files_and_dirs = self.get_config_files_from_plugin_dir(
                plugin_name, plugin_dir_path
            )
            self.plugin_config_mapping[plugin_name] = files
            self.discarded_files.update(ignored_files_and_dirs)

    def print_plugin_data(self) -> None:
        self.logger.info(f"Printing plugin data for environment: '{self.target_env}'")

        self.logger.debug("")
        self.logger.debug("")
        for file in self.discarded_files:
            self.logger.debug(f"Discarded file: {file}")

        self.logger.info("")
        self.logger.info("")

        for plugin in sorted(list(self.plugin_names)):
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

    @utils.ensure_root
    def copy_plugin_data(self, dest_env: Optional[str]):
        """
        The src_env is understood to be the target_env the class was initialized with.
        """
        utils.ensure_valid_env(dest_env)

        dest_env = dest_env if dest_env is not None else self.config.default_copy_to_env
        dest_path_base = utils.get_plugin_path_base(dest_env)

        self.logger.info(f"Starting copy from {self.target_env} => {dest_env}")

        for plugin_name in self.plugin_config_mapping:
            for file_path in self.plugin_config_mapping[plugin_name]:
                dest_path = dest_path_base / plugin_name
                rel_path = Path(*file_path.parts[len(dest_path.parts) :])
                dest_path = dest_path / rel_path

                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy(file_path, dest_path)

                self.logger.debug(f"{file_path} => {dest_path}")

        user, group = self.config.mc_data_user, self.config.mc_data_group
        uid, gid = utils.get_uid_gid(user, group)

        self.logger.info(
            f"Recursive chowning dest_env:{dest_env} files to {user}:{group}"
        )
        for dirpath, dirnames, filenames in os.walk(dest_path_base):
            shutil.chown(dirpath, uid, gid)
            for filename in filenames:
                self.logger.info(f"{Path(dirpath) / filename} - {uid}:{gid}")
                shutil.chown(Path(dirpath) / filename, uid, gid)

        self.logger.info("Copy complete.")
