#!/usr/bin/env python3
import os
import sys
import shutil

import logging

from pathlib import Path
from typing import Optional, Set, Dict, List, Tuple

import src.utils as utils
from src.config import Config
from src.mytypes import *
from src.exceptions import (
    UnidentifiablePluginDirException,
    InvalidEnvironmentException,
    InvalidConfigurationException,
)


class Patchouli:
    config: Config
    logger: logging.Logger

    plugins_whitelist: Optional[List[PluginName]]
    plugins_blacklist: Optional[List[PluginName]]

    target_env: Environment
    base_path: Path

    config_suffixes: Set
    config_paths_to_ignore: Dict[PluginName, List[Path]]

    plugin_names: Set[PluginName] = set()
    plugin_jar_mapping: Dict[PluginName, PluginJar] = {}
    plugin_dir_mapping: Dict[PluginName, PluginDir] = {}
    plugin_config_mapping: Dict[PluginName, List[PluginConfigFile]] = {}
    plugin_data_mapping: Dict[PluginName, List[PluginDataFile]] = {}

    create_missing_dirs: bool

    discarded_files: Set[Path] = set()

    def __init__(
        self,
        config: Config,
        logger: Optional[logging.Logger] = None,
        target_env: Optional[Environment] = None,
        create_missing_dirs: Optional[bool] = None,
        plugins_whitelist: Optional[List[PluginName]] = None,
        plugins_blacklist: Optional[List[PluginName]] = None,
    ):
        self.config = config
        self.logger = logger if logger is not None else logging.getLogger(__name__)

        if plugins_whitelist is not None and plugins_blacklist is not None:
            raise InvalidConfigurationException(
                "Cannot provide both a whitelist and blacklist"
            )
        self.plugins_whitelist = plugins_whitelist
        self.plugins_blacklist = plugins_blacklist

        self.target_env = (
            target_env
            if target_env is not None
            else Environment(self.config.default_env)
        )
        self.base_path = Path(self.config.base_path)

        pluginscfg = self.config.plugins
        self.config_suffixes = set(pluginscfg.configs.suffixes)
        self.config_paths_to_ignore = {
            plugin_name: [Path(path) for path in paths]
            for plugin_name, paths in pluginscfg.configs.paths_to_ignore.items()
        }

        self.create_missing_dirs = (
            create_missing_dirs
            if create_missing_dirs is not None
            else self.config.default_create_missing_dirs
        )

        self.populate_plugin_data(target_env=self.target_env)

    def get_config_files_from_plugin_dir(
        self, plugin_name: PluginName, plugin_dir: PluginDir
    ) -> Tuple[List[Path], List[Path]]:

        paths_to_ignore = (
            []
            if plugin_name not in self.config_paths_to_ignore
            else self.config_paths_to_ignore[plugin_name]
        )

        suffixes_to_search = self.config_suffixes
        suffixes_override = (
            self.config.plugins.configs.suffixes_override.get_or_default(plugin_name)
        )

        (
            all_valid_config_files,
            all_ignored_paths_and_dirs,
        ) = utils.find_all_files_with_exts(
            base_path=plugin_dir,
            extensions=suffixes_to_search,
            paths_to_ignore=paths_to_ignore,
            suffixes_override=suffixes_override,
        )

        return all_valid_config_files, all_ignored_paths_and_dirs

    def populate_plugin_data(self, target_env: Environment) -> None:
        self.logger.debug("Populating plugin data with:")
        self.logger.debug(f" - Whitelist: {self.plugins_whitelist}")
        self.logger.debug(f" - Blacklist: {self.plugins_blacklist}")
        # Jars
        jar_paths = [
            x
            for x in utils.get_plugin_path_base(
                target_env, create_missing_dirs=self.create_missing_dirs
            ).iterdir()
            if x.is_file() and x.suffix == ".jar"
        ]

        for jar_path in jar_paths:
            plugin_name = utils.get_plugin_name_from_jar(jar_path)

            if self.plugins_whitelist and plugin_name not in self.plugins_whitelist:
                continue
            elif self.plugins_blacklist and plugin_name in self.plugins_blacklist:
                continue

            self.plugin_names.add(plugin_name)
            self.plugin_jar_mapping[plugin_name] = jar_path

        # Directories (if created by plugin)
        plugin_dirs = [
            x
            for x in utils.get_plugin_path_base(
                target_env, create_missing_dirs=self.create_missing_dirs
            ).iterdir()
            if x.is_dir() and x.name not in self.config.plugins.folders_to_ignore
        ]

        for plugin_dir in plugin_dirs:
            plugin_name = plugin_dir.name

            if self.plugins_whitelist and plugin_name not in self.plugins_whitelist:
                continue
            elif self.plugins_blacklist and plugin_name in self.plugins_blacklist:
                continue

            if plugin_name not in self.plugin_names:
                raise UnidentifiablePluginDirException(
                    f"Could not find a plugin to associate with the directory '{plugin_dir}'. Does the .jar file for this plugin exist?"
                )

            self.plugin_dir_mapping[plugin_name] = plugin_dir

        # Config files - if a directory exists.
        for plugin_name, plugin_dir_path in self.plugin_dir_mapping.items():
            files, ignored_files_and_dirs = self.get_config_files_from_plugin_dir(
                plugin_name, plugin_dir_path
            )
            self.plugin_config_mapping[plugin_name] = files
            self.discarded_files.update(ignored_files_and_dirs)

    def print_plugin_data(self) -> None:
        self.logger.info(
            f"Printing plugin data for environment: '{self.target_env.value}'"
        )

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

    def sync_vcs_with_env(
        self, src_env: Optional[Environment], dest_env: Optional[Environment]
    ):
        """
        Direction can go either way, vcs -> env or env -> vcs.
        Direction is defined by src_env and dest_env inputs. Direction should be handled by git-patchy

        One of the src_env or dest_env must be mytypes.Environments.VCS
        """

    @utils.ensure_root
    def copy_plugin_data(self, dest_env: Optional[Environment]):
        """
        The src_env is understood to be the target_env the class was initialized with.
        """
        dest_env = dest_env if dest_env is not None else self.config.default_copy_to_env
        utils.ensure_valid_env(
            dest_env,
            create_missing_dirs=True,
        )

        dest_path_base = utils.get_plugin_path_base(
            dest_env, create_missing_dirs=self.create_missing_dirs
        )

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
                self.logger.debug(f"{Path(dirpath) / filename} - {uid}:{gid}")
                shutil.chown(Path(dirpath) / filename, uid, gid)

        self.logger.info("Copy complete.")
