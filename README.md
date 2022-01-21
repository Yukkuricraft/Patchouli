# Patchouli - A Plugin VCS Management Tool

## Description
Patchouli is a tool that attempts to allow splitting of git-appropriate files away from non-git-appropriate files which allows server admins to add plugin configurations to VCS while backing up plugin data files and jars elsewhere.

A Minecraft server can be broken down into three major components: Plugins, World Data, and Server Level Configs. This tool addresses the plugins. A Minecraft plugin folder can be similarly broken down into three 'types' of data: Jars, Configs, and Plugin Data.

We make the following observations about the three types of data associated with plugins
#### Jars
- *All* plugins have jars (duh)
- Jars are not git-appropriate.
- Jars should be saved using a standard backup program.

#### Configs
- *Most, but not all* plugins have config files
- Config files are git appropriate as they are text-based and human modified.

#### Plugin Data
- Most plugins do not generate data stored on disk, but *a few* do.
- Plugin data, while usually in plaintext, is not git appropriate as humans do not read or write these files.
- These should be saved using a standard backup system.

## Installation
Patchouli is to be used as a `git` subcommand. To do this, we will add this folder to our `PATH` env var.

```
# Run from root of repo
export $PATH=$PWD:$PATH
```

To save this across sessions, add it to your `.bash_profile` or analogous config for your shell of choice.


## Usage

|Command|Description|
|-------|-----------|
|`git patchy help`||
|`git patchy show`|List all plugins and their various info. Lists jar path, plugin folder if present, and config files if present.|


## TODO: Write Me
