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


def __chop_prefix_from_paths(paths: List[Path]) -> List[Path]:
    rtn = []

    for path in paths:
        chopped = Path(*path.parts[1:])
        if len(chopped.parts) > 0:
            rtn.append(chopped)

    return rtn


def find_all_files_with_exts(
    base_path: Path,
    extensions: List[str],
    paths_to_ignore: List[Path],
) -> List[str]:
    """
    Extensions should have a dot in front, eg [".yml", ".yaml"]
    """

    logger.debug(f"Args: {[base_path, extensions, paths_to_ignore]}")
    all_valid_files = []
    all_invalid_files_and_dirs = []

    try:
        for child in base_path.iterdir():
            if any(
                [child.name == str(ignored_path) for ignored_path in paths_to_ignore]
            ):
                logger.info(f"Ignored path - Skipping: {child}")
                all_invalid_files_and_dirs.append(child)
                continue

            if child.is_dir():
                rec_valid_files, rec_invalid_files = find_all_files_with_exts(
                    base_path=child,
                    extensions=extensions,
                    paths_to_ignore=__chop_prefix_from_paths(paths_to_ignore),
                )
                all_valid_files.extend(rec_valid_files)
                all_invalid_files_and_dirs.extend(rec_invalid_files)
            else:
                if child.suffix not in extensions:
                    logger.debug(f"Invalid suffix - Skipping: {child}")
                    all_invalid_files_and_dirs.append(child)
                    continue

                all_valid_files.append(child)

        return all_valid_files, all_invalid_files_and_dirs
    except PermissionError as e:
        logger.warning(f"Skipping {base_path} due to a permission error!!")
        return [], [base_path]
