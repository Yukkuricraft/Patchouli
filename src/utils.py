import os
import yaml
import logging

logger = logging.getLogger(__name__)

from zipfile import ZipFile
from pathlib import Path

from typing import Optional, List, Dict

from src.mytypes import *
from src.exceptions import (
    InvalidPathException,
    InvalidPluginException,
)


def get_plugin_name_from_jar(jar_path: PluginJar) -> str:
    if jar_path.suffix != ".jar":
        raise InvalidPathException(
            f"Got '{jar_path}' as a jar path but path did not end in a '.jar'!"
        )

    try:
        with ZipFile(jar_path, "r").open("plugin.yml") as f:
            yaml_as_dict = yaml.safe_load(f)
            if "name" not in yaml_as_dict:
                raise KeyError(
                    f"{jar_path}'s plugin.yml did not contain a 'name' field!"
                )
            return yaml_as_dict["name"]
    except KeyError as e:
        # KeyError can be raised from both ZipFile().open() as well as the explicit raise
        raise InvalidPluginException from e


def filter_ignored_paths(path: Path) -> bool:
    return not any([path_to_ignore in str(path) for path_to_ignore in []])


def find_all_files_with_exts(
    base_path: Path,
    extensions: List[str],
    paths_to_ignore: List[Path],
    # paths_to_ignore: Dict[PluginName, List[Path]],
) -> List[str]:
    """
    Extensions should have a dot in front, eg [".yml", ".yaml"]
    paths_to_ignore should be absolute paths
    """

    logger.info(f"Args: {[base_path, extensions, paths_to_ignore]}")
    all_valid_files = []

    for root, dirs, files in os.walk(base_path):
        root = Path(root)

        if any([root.is_relative_to(ignored_path) for ignored_path in paths_to_ignore]):
            logger.info(f"Ignored path - Skipping: {file_path}")
            logger.debug(f"Root: {root}\nignored_paths: {paths_to_ignore}")
            continue

        for file_name in files:
            file_path = root / file_name
            if file_path.suffix not in extensions:
                logger.debug(f"Invalid suffix - Skipping: {file_path}")
                continue

            all_valid_files.append(file_path)

    return all_valid_files
