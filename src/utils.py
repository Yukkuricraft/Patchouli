import re
import os
import sys
import pwd
import grp
import getpass
import yaml  # type: ignore
import logging

logger = logging.getLogger(__name__)

from zipfile import ZipFile
from pathlib import Path
from argparse import ArgumentParser

from typing import Optional, Tuple, List, Dict, Callable, Set


import src.constants as consts
from src.mytypes import *
from src.common.config import Config, get_config
from src.constants import CONFIG_NAME
from src.exceptions import (
    InvalidPathException,
    InvalidPluginException,
    InvalidEnvironmentException,
    MustBeRunAsRootException,
)

__CONFIG = get_config(CONFIG_NAME)
__BASE_PATH = Path(__CONFIG.base_path)


def ensure_root(func: Callable) -> Callable:
    def inner(*args, **kwargs):
        if getpass.getuser() != "root":
            raise MustBeRunAsRootException("This command must be run as root.")
        return func(*args, **kwargs)

    return inner


def __create_dir(path: Path, mode=0o755):
    try:
        original_umask = os.umask(0)
        path.mkdir(mode=mode)
    finally:
        os.umask(original_umask)


def ensure_valid_env(env: Environment, create_missing_dirs: bool = False):
    env_str = env.value
    if not re.match(__CONFIG.env_name_regex, env_str):
        raise InvalidEnvironmentException(
            f"Got '{env_str}' which was not a valid env name. Env names must satisfy the regex: {__CONFIG.env_name_regex}"
        )
    env_path = __BASE_PATH / env_str

    if not env_path.exists():
        if create_missing_dirs:
            inp = input(
                f"Folder for env '{env_str}' did not exist at {env_path}. Would you like to create it?y/N\n "
            )
            if len(inp) == 0 or inp[0].lower() != "y":
                print("User rejected creation.")
                print(
                    f"Cannot proceed without plugins folder. Please create '{env_path}' before trying again."
                )
                sys.exit(1)

            __create_dir(env_path, mode=0o755)
        else:
            raise InvalidEnvironmentException(
                f"Env '{env_str}' was a valid env name but could not find a directory for it! Please create {env_path} first."
            )

    plugins_path = env_path / "plugins"
    if not plugins_path.exists():
        if create_missing_dirs:
            inp = input(
                f"Plugins folder did not exist for env:{env_str} - Would you like to create one? y/N\n"
            )

            if len(inp) == 0 or inp[0].lower() != "y":
                print("User rejected creation.")
                print(
                    f"Cannot proceed without plugins folder. Please create '{plugins_path}' before trying again."
                )
                sys.exit(1)

            __create_dir(plugins_path, mode=0o755)
        else:
            raise InvalidEnvironmentException(
                f"Env '{env_str}' was a valid env name but could not find a plugin directory for it! Please create {plugins_path} first."
            )


def add_default_argparse_args(parser: ArgumentParser) -> ArgumentParser:
    parser.add_argument("--create-missing-dirs", default=None, action="store_true")
    parser.add_argument(
        "-w",
        "--plugins-whitelist",
        default=None,
        nargs="+",
        help="Explicit list of plugins to act on. Case sensitive. Incompatible with --plugins-blacklist",
    )
    parser.add_argument(
        "-b",
        "--plugins-blacklist",
        default=None,
        nargs="+",
        help="Plugins to ignore. Case sensitive. Incompatible with --plugins-whitelist",
    )
    return parser


def get_uid_gid(user: str, group: str) -> Tuple[int, int]:
    return pwd.getpwnam(user).pw_uid, grp.getgrnam(group).gr_gid


def get_plugin_path_base(env: Environment, create_missing_dirs: bool = False) -> Path:
    if env == consts.VCS_ENV:
        """
        The VCS "env" is a special env that refers to the VCS repo instead of an env folder under config.base_path
        """
        raise NotImplementedError("Aaaaaa")
    ensure_valid_env(
        env,
        create_missing_dirs=create_missing_dirs,
    )

    return __BASE_PATH / env.value / "plugins"


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
    return not any([path_to_ignore in str(path) for path_to_ignore in []])  # type: ignore


def __chop_prefix_from_paths(paths: List[Path], next_dirname: str) -> List[Path]:
    rtn = []

    for path in paths:
        if path.name != next_dirname:
            continue

        logger.info([path, next_dirname])
        chopped = Path(*path.parts[1:])
        if len(chopped.parts) > 0:
            rtn.append(chopped)

    return rtn


def __chop_prefix_from_suffixes_override(
    suffixes_override: Optional[Dict[str, List[Dict]]], next_dirname: str
) -> Optional[Dict[str, List[Dict]]]:
    """ """
    if suffixes_override is None:
        return None

    rtn = {}
    for op in ["add", "rem"]:
        if op not in suffixes_override:
            continue

        objs = []
        for obj in suffixes_override[op]:
            path = Path(obj["path"])
            if path.parts and path.parts[0] != next_dirname:
                logger.debug(
                    f"[__chop_pre_suf_over] Dropping path:{path} as it does not match next_dirname:{next_dirname}"
                )
                continue
            if len(path.parts) <= 1:
                logger.debug(
                    f"[__chop_pre_suf_over] Dropping path:{path} as it is <= len of 1"
                )
                continue

            # Icky hardcoded literals.
            # TODO: Eventually make dataclass defs for config shape.
            objs.append(
                {
                    "suffix": obj["suffix"],
                    "path": str(Path(*path.parts[1:])),  # :thinking:
                }
            )

        rtn[op] = objs

    return rtn


def __process_paths_and_suffixes_for_child_dir(
    extensions: Set[str],
    paths_to_ignore: List[Path],
    suffixes_override: Optional[Dict[str, List[Dict]]],
    child_dirname: str,
):
    extensions = set(extensions)

    if suffixes_override:
        if "add" in suffixes_override:
            for suffix_override in suffixes_override["add"]:
                suffix = suffix_override["suffix"]

                if suffix_override["path"] in [".", child_dirname]:
                    logger.debug(
                        f"Adding suffix:{suffix} to extensions for path:{suffix_override['path']}"
                    )
                    extensions.add(suffix)

        if "rem" in suffixes_override:
            for suffix_override in suffixes_override["rem"]:
                suffix = suffix_override["suffix"]

                if (
                    suffix_override["path"] in [".", child_dirname]
                    and suffix in extensions
                ):
                    logger.debug(
                        f"Removing suffix:{suffix} from extensions for path:{suffix_override['path']}"
                    )
                    extensions.remove(suffix)

    paths_to_ignore = __chop_prefix_from_paths(paths_to_ignore, child_dirname)

    suffixes_override = __chop_prefix_from_suffixes_override(
        suffixes_override, child_dirname
    )

    return extensions, paths_to_ignore, suffixes_override


def find_all_files_with_exts(
    base_path: Path,
    extensions: Set[str],
    paths_to_ignore: List[Path],
    suffixes_override: Optional[Dict[str, List[Dict]]],
) -> Tuple[List[Path], List[Path]]:
    """
    Extensions should have a dot in front, eg [".yml", ".yaml"]
    """
    extensions = set(extensions)

    all_valid_files = []
    all_invalid_files_and_dirs = []

    try:
        for child in base_path.iterdir():
            next_dirname = child.name
            if any(
                [next_dirname == str(ignored_path) for ignored_path in paths_to_ignore]
            ):
                logger.debug(f"Ignored path - Skipping: {child}")
                all_invalid_files_and_dirs.append(child)
                continue

            if child.is_dir():

                (
                    new_extensions,
                    new_paths_to_ignore,
                    new_suffixes_override,
                ) = __process_paths_and_suffixes_for_child_dir(
                    extensions, paths_to_ignore, suffixes_override, next_dirname
                )

                rec_valid_files, rec_invalid_files = find_all_files_with_exts(
                    base_path=child,
                    extensions=new_extensions,
                    paths_to_ignore=new_paths_to_ignore,
                    suffixes_override=new_suffixes_override,
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
