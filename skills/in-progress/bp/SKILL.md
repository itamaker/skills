---
name: bp
description: Open local macOS apps, folders and URLs from short saved aliases with the bp (Betaphor) CLI, and add, list or remove those aliases. Use when the user types /bp, or asks to open, launch or quit a Mac app or site by nickname.
---

# bp

[bp](https://github.com/itamaker/bp) keeps a table of `alias -> command` in SQLite (`~/.betaphor`) and runs the command when you call `bp <alias>`. This skill is the agent front end: `/bp` finds, opens and saves shortcuts without the user touching the CLI. macOS only.

## Arguments

| Input | Do |
|---|---|
| `/bp` | List aliases (see **List**). |
| `/bp <alias>` | Run it. |
| `/bp add <alias> <target>` | Save it. `<target>` may be an app name, URL or path; build the command from the table below. |
| `/bp rm <alias>` | Remove it, after confirming. |
| `/bp <anything else>` | Not an alias: treat as an app name, URL or path, open it, then offer to save it. |

Plain requests ("open Safari", "quit Slack") follow the same flow.

## Setup check

Run `command -v bp`. If it is missing, say so and give the install route from the bp README (needs Go; builds from source with `./install.sh`). Do not install it unasked. Meanwhile still do the job without saving: `open -a "<App>"`, `open <url>` or `open <path>`.

## List

`bp ls` panics when stdin is not a terminal (its width probe reads `stty size`), which is the case in an agent shell. Read the table directly instead:

```bash
sqlite3 -separator ' -> ' ~/.betaphor 'SELECT alias, command FROM aliases ORDER BY alias'
```

No file or no table means no aliases yet.

## Run

1. Look the alias up with the query above. Never call `bp <alias>` for an unknown name: it panics.
2. Run `bp <alias>`.
3. Tell the user the command that ran. `bp` discards the command's stderr and exit status, so a missing app fails silently. For an app launch, confirm with `osascript -e 'application "<App>" is running'` once after a second; if `false`, say it did not start.

Aliases run on the user's behalf only when they ask for that alias. Do not run saved commands you were not asked to.

## Add

Build the command in one of these forms. `bp` splits it into words itself and executes it directly with no shell, so `~`, `|`, `&&`, `$VAR` and redirects do not work.

| Target | Command |
|---|---|
| App by name | `open -a "Visual Studio Code"` |
| Folder or file | `open /Users/me/Projects` (absolute path) |
| URL | `open https://example.com` |
| Quit an app | `osascript -e 'quit app "Slack"'` |
| Open with an app | `open -a "Visual Studio Code" /Users/me/Projects/app` |

Do not use a bare `/Applications/X.app` path: that is a directory and cannot be executed.

Before saving:

1. For an app, check the name resolves: `osascript -e 'id of app "<App>"'`. On error, ask for the exact name.
2. Look the alias up. `INSERT OR REPLACE` overwrites without asking, so if it exists show the old command and ask before replacing.
3. Save by piping the two prompts (alias, then command) to stdin:

```bash
printf '%s\n%s\n' 'code' 'open -a "Visual Studio Code"' | bp add
```

Pick a short lowercase alias that is not `add`, `ls`, `rm`, `rmAll` or `help`; those are subcommands and shadow the alias.

## Remove

Confirm the alias and its command with the user first, then pipe the prompt's answer:

```bash
printf 'y\n' | bp rm <alias>
```

Never run `bp rmAll` unless the user asked to clear everything and confirmed after you showed the list.

## Limits

- Not tested on macOS by the author of this skill: the `open`, `osascript` and `sqlite3` lines follow standard macOS behavior and the `bp` source, and `add`, `rm` and alias execution were run against a Linux build.
- `bp` reads the database from the account's home directory, not `$HOME`.
- Output of `bp <alias>` is stdout only. A command that prints to stderr or exits non-zero looks successful.
- No Linux or Windows support; `open` and `osascript` do not exist there.
