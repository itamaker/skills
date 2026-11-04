---
name: bp
description: Open local apps, sites, files and folders from saved nicknames on macOS or Linux, run tasks that span apps (browser, mail, chat), open a whole set at once, and learn new shortcuts as it goes. Use when the user types /bp, names apps or files to open or quit, or wants a shortcut saved.
---

# bp

`/bp` does everyday computer tasks across the user's local apps and remembers what it had to open, so next time `/bp gmail`, `/bp chrome` or `/bp work` just opens it. Nothing is fixed: any app, site, file or folder the user names is resolved on the spot. macOS and Linux; Windows is not supported.

## Setup

Everything goes through one script, `scripts/bp.sh` in the folder this SKILL.md was loaded from:

```bash
BP="bash <skill folder>/scripts/bp.sh"     # then: $BP list, $BP run gmail, ...
```

It keeps the shortcut file, validates input and starts things, so do not edit the file by hand or rebuild its commands. Pass each value as its own quoted argument. `$BP help` lists every command. Only the OS's own tools are used, so there is nothing to install. The file format is in [references/store.md](references/store.md), needed only when something looks corrupted.

## Reading the input

| Input | Do |
|---|---|
| `/bp` | `$BP list` |
| `/bp <alias>`, one word that `$BP show <alias>` finds | `$BP run <alias>`; a group opens all its members |
| a request to save, list or remove shortcuts, in plain words or as `/bp add <alias> <target> [with <app>]` | **Saving**; list with `$BP list`; remove with `$BP show` then a yes then `$BP rm` |
| `/bp find <name>`, `/bp scan` | **Finding apps** |
| `/bp stop <alias>` | `$BP stop <alias>`; for a group it quits every app in it |
| `/bp auto on` / `off` | `$BP auto on` / `off` |
| anything else | A task. |

## A task

Example: "/bp open Chrome, go to Gmail, send Li the report, then tell Wang in Slack I sent it." Everyday jobs of other kinds (a file, a project, a meeting link, a map, "start my work setup") are in [references/scenarios.md](references/scenarios.md): read it when the task is not just opening apps and sites.

1. **Plan what to open.** List the apps, sites, files or folders the task needs.
2. **Resolve each one, in this order.** (a) A saved alias: `$BP run`. (b) A saved shortcut whose name or target contains the word: look through `$BP list`. (c) An installed app: `$BP find`; a Chinese or otherwise localized app name is translated to the app's own name first. (d) For a site, its well-known address. If none fits, ask.
3. **Open it.** A page in a browser is one launch: `$BP launch url <url> [<browser>]` opens both browser and page, so do not start the browser separately first. When the user named no browser, leave the browser out so the system default is used, and do not save a browser. When the task names a site and something to search or write there, build a deep link ([references/deep-links.md](references/deep-links.md)).
4. **Do the work in the app** with whatever browser or computer-control tools the session has. With none, stop after opening, say which steps are left for the user, and still save the shortcuts.
5. **Save what was new** (**Auto-save**), then finish with one line, in the user's language, for example: `Saved shortcuts: chrome, gmail, slack. /bp rm <name> removes one.` After a task that used three or more apps, also offer once to save them as a group.

The task the user typed authorizes exactly the actions in it. If they gave no exact recipient or text for a message, show both and get a yes before sending. Send or post nothing the task did not ask for, and run a saved shortcut only when the user or their task calls for it. At a login, 2FA or CAPTCHA, stop and hand over.

If a command exits non-zero, report the reason it printed instead of claiming success. `xdg-open` needs a desktop session, so over SSH or in a container its failure is the real answer. A success message means the system was asked to open the thing, not that a window appeared: say "opened" only for that. On Linux an app started in the background reports success even if it dies at once; `$BP running <name>` can check, but a process often has a different name from its command (Chrome's is `chrome`), so a "not running" answer is not proof and you should say "asked to open" instead.

## Finding apps

`$BP find <text>` and `$BP scan` print `name<TAB>target`, where target is exactly what `add` takes for an app, and also what to give as `with` for a browser or editor (on Linux that is a command name such as `google-chrome-stable`, on macOS an app name such as `Google Chrome`).

- **find:** use the best match. Several plausible matches (Chrome and Chromium): show them and ask. No match: say so and offer a web address instead.
- **scan:** show the first 40 as a numbered list with the count of the rest, and save the ones the user picks by number or name. Never save the whole list unasked.
- **Alias:** `$BP alias "<app name>"` suggests one (`Google Chrome` becomes `chrome`). It cannot build one from a non-ASCII name; pick a short English alias and say which.

## Saving

Infer the kind from the target: `http(s)://` and other supported links are `url`, an absolute path is `path`, otherwise `app`; "quit" or "close" wording means `quit`; a comma-separated list of saved aliases is a `group`; `with <app>` names the app to open a url or path in. Expand `~` first.

```bash
$BP add chrome app "Google Chrome"
$BP add gmail url https://mail.google.com "Google Chrome"
$BP add morning group chrome,gmail,slack
```

Exit 3 means the alias is taken: show the old line it printed and ask before rerunning with `--replace`. Exit 4 means the app, `with` app or path is not on this machine: run `$BP find` and ask for the exact name. Values are written for this machine's OS.

### Auto-save

After a task opened something successfully, save it with `$BP add --auto <alias> <kind> <target> [with]`. The script skips it when auto-save is off, when the same shortcut exists, and for anything but a plain `http(s)` address without query, fragment or credentials (exit 6 is expected: say nothing about it). A taken alias gets a free suffix instead of being replaced. Beyond those hard rules, use judgment, because a script cannot tell what is worth keeping:

- Save the app and the stable entry point of each site, such as `https://mail.google.com`, with the browser as `with` when one was named. Saving a site's front door is fine when the task opened a page deep inside it.
- Do not save a URL that points at a single item (one email thread, one document, one video, one meeting).
- Save a folder or file only if the user named it, never a temporary or generated one.
- Save nothing for an app or site that failed to open.
- Tell the user what was saved, in one line.

## Remove all

Clear everything (`$BP clear --yes`) only when the user asks for exactly that and confirms after seeing `$BP list`.

## Limits

- `scripts/test.sh` checks the script against stand-ins for `open`, `osascript`, `xdg-open`, `gtk-launch` and `pkill`; it passes on Linux. The macOS commands follow standard `open` and `osascript` behavior but have not been run on a Mac.
- Driving Gmail, Slack or YouTube pages depends on the session's browser or computer-control tools. The skill ships no automation of its own.
- The file holds targets, not arbitrary shell commands, and the skill does not shut down, sleep or lock the computer. For anything else, run the command directly and do not save it here.
