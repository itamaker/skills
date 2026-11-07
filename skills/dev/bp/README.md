# bp

A skill that does everyday computer tasks across your local apps and remembers what it had to open. The first time you say "open Chrome, go to Gmail", it finds the app and the page and saves them. After that `/bp gmail`, `/bp chrome` or `/bp work` just opens them. Nothing is preconfigured: any app, site, file or folder you name is resolved on the spot. macOS and Linux; Windows is not supported.

## What Claude can do with it

- **Open things by nickname**: apps, sites, files and folders, from a saved shortcut or straight from a plain request.
- **Run a task that spans apps**, such as "open Chrome, go to Gmail, send Li the report, then tell Wang in Slack I sent it". It opens each app, then does the work with whatever browser or computer-control tools the session has.
- **Open or quit a whole set at once**: save several shortcuts as a group, then `/bp work` opens every member in order and `/bp stop work` asks them all to quit.
- **Learn as it goes**: after a task it saves the apps and each site's front door, and tells you what was saved. Single items such as one email thread or one video are never saved.
- **Find files and apps**: the newest files in Downloads, Desktop and Documents, files by name, and installed apps by name or by kind (browser, editor, drawing, mail, chat and so on).

## Quick start

Install it, then:

```text
/bp                      list your saved shortcuts
/bp gmail                open a saved shortcut
/bp add gmail https://mail.google.com with Chrome
/bp find chrome          look up an installed app
/bp stop work            quit the apps in a group
/bp auto off             stop saving shortcuts automatically
```

Anything else you type is treated as a task, for example `/bp open the drawing board and draw a dog`.

## Commands

| You type | What happens |
|---|---|
| `/bp` | Lists the saved shortcuts |
| `/bp <alias>` | Opens that shortcut; a group opens all its members |
| `/bp add <alias> <target> [with <app>]` | Saves a shortcut. The kind is inferred: a link is a site, an absolute path is a file or folder, anything else is an app |
| `/bp find <name>`, `/bp scan` | Finds installed apps; `scan` lists the ones not saved yet and saves only those you pick |
| `/bp stop <alias>` | Quits the app, or every app in a group |
| `/bp auto on` / `off` | Switches automatic saving |
| anything else | A task: Claude plans what to open, opens it, does the work, then saves what was new |

Removing one shortcut asks first. Clearing all of them only happens when you ask for exactly that and confirm after seeing the list.

## Good to know

- **It only does what you asked.** A message is sent only to the recipient and with the text you gave; if either is missing, Claude shows both and waits for a yes. At a login, 2FA or CAPTCHA it stops and hands over to you.
- **It reports honestly.** "Asked to open" means the system was asked, not that a window appeared. A failed command is reported with its own reason.
- **Shortcuts hold targets, not shell commands.** Nothing arbitrary is run, and the skill does not shut down, sleep or lock the computer.
- **`with` takes an app, not a profile.** Several browser profiles or accounts cannot be chosen; the default profile opens.
- **On Linux**, opening needs a desktop session, so over SSH or in a container a failure is the real answer. Quitting works by process name, which can differ from the app's command.
- **Tested on Linux.** `scripts/test.sh` checks the script against stand-ins for the system's launch and quit tools. The macOS commands follow standard `open` and `osascript` behaviour but have not been run on a Mac. Driving Gmail, Slack or live drawing depends on the session's browser or computer-control tools; the skill ships no automation of its own.

## Where things live

```
<skills dir>/bp/                      the skill (wherever your install puts it)
├── SKILL.md                          instructions Claude follows
├── README.md                         this file
├── scripts/
│   ├── bp.sh                         the one script that keeps shortcuts and opens things
│   └── test.sh                       tests against stand-in launch tools
├── references/
│   ├── scenarios.md                  everyday jobs mapped to commands
│   ├── deep-links.md                 links that fill in a search, a draft or an event
│   └── store.md                      the shortcut file format
└── evals/                            example tasks used to check the skill

~/.bp/aliases.tsv                     your saved shortcuts
```

Do not edit `aliases.tsv` by hand; `bp.sh` validates what it writes.

## Install

```bash
npx skills@latest add itamaker/skills --skill=bp
```

Nothing else needs installing: the script uses only the operating system's own tools.
