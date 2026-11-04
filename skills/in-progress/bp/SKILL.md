---
name: bp
description: Open local apps, sites and folders from saved nicknames on macOS or Linux, and learn new ones as you work. Use when the user types /bp, asks for a task that spans apps (browser, mail, chat), or asks to save, list or remove a shortcut.
---

# bp

`/bp` does a task across the user's local apps and remembers every app and site it had to open, so next time `/bp gmail` or `/bp chrome` just opens it. Shortcuts live in one text file; the skill needs only tools the OS ships (`open`/`osascript` on macOS, `xdg-open`/`gtk-launch`/`pkill` on Linux, `awk` on both). Windows is not supported.

## Reading the input

| Input | Do |
|---|---|
| `/bp` | List shortcuts. |
| `/bp <alias>` (one word that is a saved alias) | Run it. |
| `/bp find <name>` | Search the installed apps on this machine and offer to save matches. |
| `/bp scan` | List the installed apps not yet saved and save the ones the user picks. |
| `/bp add <alias> <target> [with <app>]` | Save by hand. |
| `/bp rm <alias>` | Remove, after confirming. |
| `/bp auto off` / `/bp auto on` | Stop or resume auto-saving. |
| anything else | A task. See below. |

## A task

Example: "/bp open Chrome, go to Gmail, send Li the report, then tell Wang in Slack I sent it."

1. **Plan the apps.** List what the task needs to open: here Chrome, Gmail, Slack. Nothing is fixed; any app, site or folder the task names is handled the same way.
2. **Open each one, resolving in this order.** (a) A saved alias. (b) A saved shortcut whose name or target contains the word, ignoring case. (c) An installed app on this machine (see **Find**). (d) For a site, its well-known address. If none fits, ask. Open it and note it as new unless it came from (a) or (b).
3. **Do the work in the app.** Go straight to the right page with a deep link (see **Deep links**), then continue with whatever browser or computer-control tools this session offers. If it has none, stop after opening, say which steps are left for the user, and still save the shortcuts.
4. **Save what was new** (see **Auto-save**) and finish with one line, for example: `Saved shortcuts: chrome, gmail, slack. /bp rm <name> removes one.`

The task the user typed authorizes exactly the actions in it. If they gave no exact recipient or text for a message, show both and get a yes before sending. Send or post nothing the task did not ask for. At a login, 2FA or CAPTCHA, stop and hand over.

## Store

`~/.bp/aliases.tsv`, one shortcut per line, tab-separated: `alias`, `kind`, `target`, and an optional fourth field `with`, an app to open the target in.

```
chrome	app	Google Chrome
gmail	url	https://mail.google.com	Google Chrome
slack	app	Slack
work	path	/Users/me/Projects
slack-off	quit	Slack
```

| kind | macOS | Linux |
|---|---|---|
| `app` | `open -a "<target>"`; target is the app name | run command `<target>` detached, else `gtk-launch "<target>"`; target is a command name or desktop-entry ID such as `firefox` |
| `url`, `path` | `open "<target>"`, or `open -a "<with>" "<target>"` | `xdg-open "<target>"`, or the command `<with>` run detached with the target |
| `quit` | quits the app named `<target>` | `pkill -x "<target>"`; target is the process name |

Paths are absolute: expand `~` before saving. The file belongs to one machine, so an `app`, `with` or `quit` value is written for that machine's OS (Chrome is `Google Chrome` on a Mac and `google-chrome` on many Linux systems). Alias: lowercase letters, digits, `-` or `_`, and not a word from the table above. Values contain no tabs or newlines. A missing file means no shortcuts yet.

## List

```bash
awk -F'\t' '{printf "%-12s %-5s %s %s\n", $1, $2, $3, ($4 ? "(in " $4 ")" : "")}' ~/.bp/aliases.tsv
```

Say so plainly if the file is missing or empty.

## Run

Run an alias only when the user or their task calls for it. Put values in single quotes, as below, so nothing in them reaches the shell.

```bash
ALIAS='gmail'
IFS=$'\t' read -r kind target with < <(awk -F'\t' -v a="$ALIAS" '$1==a {print $2 "\t" $3 "\t" $4; exit}' ~/.bp/aliases.tsv)
if [ "$(uname -s)" = Darwin ]; then OPEN=open; else OPEN=xdg-open; fi
case "$kind" in
  app)
    if [ "$OPEN" = open ]; then open -a "$target"
    elif command -v "$target" >/dev/null 2>&1; then setsid nohup "$target" >/dev/null 2>&1 &
    elif command -v gtk-launch >/dev/null 2>&1; then gtk-launch "$target"
    else echo "cannot launch: $target" >&2; false; fi ;;
  url|path)
    if [ -z "$with" ]; then "$OPEN" "$target"
    elif [ "$OPEN" = open ]; then open -a "$with" "$target"
    elif command -v "$with" >/dev/null 2>&1; then setsid nohup "$with" "$target" >/dev/null 2>&1 &
    else xdg-open "$target"; fi ;;
  quit)
    if [ "$OPEN" = open ]; then osascript -e 'on run argv' -e 'tell application (item 1 of argv) to quit' -e 'end run' "$target"
    else pkill -x "$target"; fi ;;
  *) echo "no such alias: $ALIAS" >&2; false ;;
esac
```

Report a non-zero exit and the printed reason instead of claiming success. On Linux a detached launch always exits 0, so check it started (`pgrep -x "$target"`) before saying it did. `xdg-open` needs a desktop session; over SSH or in a container it fails, and that is the answer to give. `pkill -x` matches the process name (first 15 characters) and exits 1 when nothing matched.

## Deep links

When a task names a site and something to look for or do there, open the page that already shows it instead of the front page plus clicks. This works even when the session has no browser tools. Build the URL, then open it with the **Run** `url` branch (set `kind=url`, `target`, and `with` to the browser the user named, or empty). Do not save it: it holds a query.

| Goal | URL |
|---|---|
| Search YouTube | `https://www.youtube.com/results?search_query=<q>` |
| Find a YouTube channel | the same URL plus `&sp=EgIQAg%253D%253D` |
| Search Google | `https://www.google.com/search?q=<q>` |
| Search GitHub | `https://github.com/search?q=<q>` |
| Start a Gmail draft | `https://mail.google.com/mail/?view=cm&fs=1&to=<to>&su=<subject>&body=<body>` |

Percent-encode every `<...>` value, including non-ASCII text:

```bash
urlenc() { local LC_ALL=C s="$1" i c; for ((i=0;i<${#s};i++)); do c=${s:i:1}; case $c in [a-zA-Z0-9.~_-]) printf '%s' "$c";; *) printf '%%%02X' "'$c";; esac; done; }
```

For a site not in the table, use its own search box with the session's browser tools, or open its front page and say what is left.

**Going on into a result.** With browser tools, continue from the opened page: for a channel, take the top result whose name contains the words the user gave, open it (for "watch their videos", its `/videos` page), and tell the user the name and address reached and the next two matches, since names are often shared. Moving between pages is not consequential, so pick and say so rather than asking. Without browser tools, stop at the results page and say which click is left. A draft is only filled in; sending still needs the task to ask for it.

## Find

List the apps installed on this machine. Reading these folders changes nothing.

macOS prints one app name per line:

```bash
for d in /Applications /Applications/Utilities /System/Applications /System/Applications/Utilities ~/Applications; do
  for a in "$d"/*.app; do [ -e "$a" ] && basename "$a" .app; done
done | sort -u
```

Linux prints `name<TAB>desktop-id<TAB>command` for each launcher a menu would show:

```bash
for d in /usr/share/applications /usr/local/share/applications ~/.local/share/applications \
         /var/lib/flatpak/exports/share/applications ~/.local/share/flatpak/exports/share/applications \
         /var/lib/snapd/desktop/applications; do
  for f in "$d"/*.desktop; do
    [ -e "$f" ] || continue
    awk -F= -v id="$(basename "$f" .desktop)" '
      /^\[/ { sec = ($0 == "[Desktop Entry]"); next }
      sec && $1 == "Name" && !name { name = substr($0, 6) }
      sec && $1 == "Exec" && !cmd  { n = split(substr($0, 6), w, " "); i = 1
                                     while (i < n && (w[i] == "env" || w[i] ~ /^[A-Za-z_][A-Za-z0-9_]*=/)) i++
                                     cmd = w[i] }
      sec && $1 == "Type"          { type = $2 }
      sec && $1 == "NoDisplay" && $2 == "true" { hide = 1 }
      END { if (type == "Application" && !hide && name) print name "\t" id "\t" cmd }' "$f"
  done
done | sort -u
```

- **`/bp find <name>`:** filter the list case-insensitively (`grep -i`) and use the best match. Several plausible matches (Chrome and Chromium): show them and ask. No match: say so and offer a web address instead.
- **`/bp scan`:** drop names already saved as a target, and show the rest as a short numbered list (the first 40, with the count of the others). Save the ones the user picks, by number or name, or all of them if they say so. Never save the whole list unasked.
- **Target to save:** on macOS the app name. On Linux the command from the third field if `command -v` finds it, otherwise the desktop id (launched with `gtk-launch`).
- **Alias:** the name in lowercase, spaces and punctuation as `-`, a leading vendor word (`google`, `microsoft`, `apple`, `adobe`) dropped when something remains, so `Google Chrome` becomes `chrome`. A clash with a different target gets a suffix.

## Add

Check the target before saving: an app comes from **Find** (a name typed by hand must match an entry there; if not, ask for the exact name), a `path` must exist after `~` is expanded. If the alias is already taken by a different target, show the old line and ask before replacing it. Then write, replacing any old line for that alias:

```bash
mkdir -p ~/.bp && touch ~/.bp/aliases.tsv
ALIAS='gmail'; KIND='url'; TARGET='https://mail.google.com'; WITH='Google Chrome'
{ awk -F'\t' -v a="$ALIAS" '$1!=a' ~/.bp/aliases.tsv; printf '%s\t%s\t%s\t%s\n' "$ALIAS" "$KIND" "$TARGET" "$WITH"; } > ~/.bp/aliases.tmp && mv ~/.bp/aliases.tmp ~/.bp/aliases.tsv
```

Leave `WITH` empty when there is none. If a value contains a single quote, write it as `'\''`. For a manual save, infer the kind: `http(s)://` is `url`, a path is `path`, otherwise `app`; "quit" or "close" wording means `quit`; `with <app>` fills the fourth field. Confirm with the saved line.

## Auto-save

After a task opened something successfully, save it unless `~/.bp/auto-off` exists (`/bp auto off` creates it, `/bp auto on` deletes it) or a shortcut with the same kind, target and `with` is already there.

- Save the app (`app`) and the stable entry point of each site (`url`, with the browser as `with` when one was named), such as `https://mail.google.com`. Keep only scheme, host and a fixed path.
- Never save a URL with a query string, fragment, credentials or a token, or one that points at a single item (one email thread, one document, one message). Save the site's front door instead, or nothing.
- Save a folder or file only if the user named it, never a temporary or generated one.
- Alias: as in **Find** (`chrome`, `gmail`, `slack`). If it is taken by a different target, add a suffix (`slack-web`) rather than replace it.
- Save nothing for an app or site that failed to open.
- Tell the user what was saved, in one line.

## Remove

Show the line, get a yes, then:

```bash
ALIAS='gmail'
awk -F'\t' -v a="$ALIAS" '$1!=a' ~/.bp/aliases.tsv > ~/.bp/aliases.tmp && mv ~/.bp/aliases.tmp ~/.bp/aliases.tsv
```

Clear everything only when the user asks for exactly that and confirms after seeing the list.

## Limits

- The file handling, the Linux launch and quit paths and the Linux app scan (run against real and sample `.desktop` files) were checked on Linux with real `awk`, `pkill` and detached launches, and stand-ins for `open`, `osascript` and `xdg-open`. The macOS app scan was checked on a sample folder only, and the macOS commands follow standard `open` and `osascript` behavior but were not run on a Mac.
- Linux launchers with a quoted or unusual `Exec` line may yield a command that `command -v` does not find; the desktop id with `gtk-launch` is the fallback, and it needs `gtk-launch` installed.
- The YouTube channel-search link and the `urlenc` helper were checked from this Linux session (the link listed the expected channels in headless Chromium). The other deep links follow those sites' public URL formats and were not opened.
- Driving Gmail or Slack depends on the browser or computer-control tools of the session. The skill does not ship its own automation, and the full flow has not been run end to end.
- The file holds targets, not arbitrary shell commands, on purpose. For anything else, run the command directly and do not save it here.
