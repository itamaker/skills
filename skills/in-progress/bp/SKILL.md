---
name: bp
description: Open apps, folders and URLs on macOS or Linux from short saved nicknames, and add, list or remove them. Use when the user types /bp, or asks to open, launch or quit an app, folder or site by nickname, or to save a shortcut for one.
---

# bp

Short nicknames for things the user opens often. `/bp code` opens whatever they saved as `code`. Everything lives in one text file and the skill uses only tools the OS ships: `open` and `osascript` on macOS; `xdg-open`, `gtk-launch` and `pkill` on Linux; `awk` on both. Windows is not supported.

## Store

`~/.bp/aliases.tsv`, one shortcut per line, three tab-separated fields:

```
code	app	Visual Studio Code
docs	url	https://example.com/docs
work	path	/Users/me/Projects
slack-off	quit	Slack
```

| kind | macOS | Linux |
|---|---|---|
| `app` | `open -a "<target>"`; target is the app name | run the command `<target>` detached, else `gtk-launch "<target>"`; target is a command name or desktop-entry ID such as `firefox` or `org.gnome.Nautilus` |
| `url` | `open "<target>"` | `xdg-open "<target>"` |
| `path` | `open "<target>"` | `xdg-open "<target>"` |
| `quit` | quits the app named `<target>` | `pkill -x "<target>"`; target is the process name |

Paths must be absolute: expand `~` before saving. The file belongs to one machine, so an `app` or `quit` target is written for that machine's OS. Alias: lowercase letters, digits, `-` or `_`, and not `add`, `ls` or `rm`. Targets must not contain tabs or newlines. A missing file means no shortcuts yet.

## Arguments

| Input | Do |
|---|---|
| `/bp` | List. |
| `/bp <alias>` | Run. |
| `/bp add <alias> <target>` | Add. Infer the kind: `http(s)://` is `url`, a path is `path`, otherwise `app`. "quit" or "close" wording means `quit`. |
| `/bp rm <alias>` | Remove, after confirming. |
| `/bp <anything else>` | Not a saved alias: treat it as an app name, URL or path, open it, then offer to save it. |

Plain requests ("open Safari", "save my projects folder as work") follow the same flow.

## List

```bash
awk -F'\t' '{printf "%-12s %-5s %s\n", $1, $2, $3}' ~/.bp/aliases.tsv
```

Say so plainly if the file is missing or empty.

## Run

Run only an alias the user asked for. Put the alias in single quotes, as below, so nothing in it reaches the shell.

```bash
ALIAS='code'
IFS=$'\t' read -r kind target < <(awk -F'\t' -v a="$ALIAS" '$1==a {print $2 "\t" $3; exit}' ~/.bp/aliases.tsv)
if [ "$(uname -s)" = Darwin ]; then OPEN=open; else OPEN=xdg-open; fi
case "$kind" in
  app)
    if [ "$OPEN" = open ]; then open -a "$target"
    elif command -v "$target" >/dev/null 2>&1; then setsid nohup "$target" >/dev/null 2>&1 &
    elif command -v gtk-launch >/dev/null 2>&1; then gtk-launch "$target"
    else echo "cannot launch: $target" >&2; false; fi ;;
  url|path) "$OPEN" "$target" ;;
  quit)
    if [ "$OPEN" = open ]; then osascript -e 'on run argv' -e 'tell application (item 1 of argv) to quit' -e 'end run' "$target"
    else pkill -x "$target"; fi ;;
  *) echo "no such alias: $ALIAS" >&2; false ;;
esac
```

Report a non-zero exit and the printed reason instead of claiming success. On Linux a detached app launch always exits 0, so check it started (`pgrep -x "$target"`) before saying it did. `xdg-open` needs a desktop session; over SSH or in a container it fails, and that is the answer to give. `pkill -x` matches the process name (first 15 characters), and exits 1 when nothing matched.

## Add

1. Check the alias is valid, then the target:
   - macOS `app`: `ls -d /Applications/"<App>".app /System/Applications/"<App>".app /Applications/Utilities/"<App>".app ~/Applications/"<App>".app 2>/dev/null`
   - Linux `app`: `command -v "<target>"`, or a file `<target>.desktop` in `/usr/share/applications` or `~/.local/share/applications`
   - `path`: expand `~` and check it exists.

   If it is not found, ask for the exact name or command.
2. If the alias is already in the file, show the old line and ask before replacing it.
3. Write it, replacing any old line for that alias:

```bash
mkdir -p ~/.bp && touch ~/.bp/aliases.tsv
ALIAS='code'; KIND='app'; TARGET='Visual Studio Code'
{ awk -F'\t' -v a="$ALIAS" '$1!=a' ~/.bp/aliases.tsv; printf '%s\t%s\t%s\n' "$ALIAS" "$KIND" "$TARGET"; } > ~/.bp/aliases.tmp && mv ~/.bp/aliases.tmp ~/.bp/aliases.tsv
```

If a value contains a single quote, write it as `'\''`. Confirm with the saved line.

## Remove

Show the line, get a yes, then:

```bash
ALIAS='code'
awk -F'\t' -v a="$ALIAS" '$1!=a' ~/.bp/aliases.tsv > ~/.bp/aliases.tmp && mv ~/.bp/aliases.tmp ~/.bp/aliases.tsv
```

Clear everything only when the user asks for exactly that and confirms after seeing the list.

## Limits

- Checked on Linux with real `awk`, `pkill` and detached launches, and stand-ins for `open`, `osascript` and `xdg-open`. The macOS commands follow standard `open` and `osascript` behavior but were not run on a Mac.
- The file holds targets, not arbitrary shell commands, on purpose. For anything else, run the command directly and do not save it here.
