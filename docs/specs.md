# Specification
Or rather whatever shortlist of desired functionality.

## Base Workflow
Create git repository per server being managed. The state of the repo and the state of the filesystem are not synced automatically but rather through `git patchy` subcommands. If there is ever a difference, by default patchy creates a "merge commit". You may override to copy and overwrite. These sync commands have different commands for both directions (server state -> git repo state vs vice versa).

## "Features"
### Show all plugins and its data
- Should show all plugins with name, jar path, folder path, config file paths
- Already implemented
- `git patchy show`

### Copy current repo state of configs to an environment
- How to specify env? Default to dev1 and otherwise override or require explicit env?
- How to handle updates to the environments that aren't reflected within stuff?
    - Could make tmp branches and use `git` to figure it out for us via fake/temp merges.


### Copy environment files to current repo state
- Vice versa

### Copy files from one env to another

