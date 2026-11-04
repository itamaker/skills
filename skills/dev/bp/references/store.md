# Shortcut file

Read this only when the file looks corrupted or the user asks how it works. Normal use goes through `scripts/bp.sh`.

`~/.bp/aliases.tsv` (the folder is `$BP_HOME` when set), one shortcut per line, tab-separated: `alias`, `kind`, `target`, and an optional fourth field `with`, an app to open the target in.

```
chrome	app	Google Chrome
gmail	url	https://mail.google.com	Google Chrome
work	path	/Users/me/Projects	Visual Studio Code
slack-off	quit	Slack
morning	group	chrome,gmail,work
```

| kind | macOS | Linux |
|---|---|---|
| `app` | `open -a "<target>"`; target is the app name | run command `<target>` detached, else `gtk-launch "<target>"`; target is a command name or desktop-entry ID such as `firefox` |
| `url`, `path` | `open "<target>"`, or `open -a "<with>" "<target>"` | `xdg-open "<target>"`, or the command `<with>` run detached with the target |
| `quit` | quits the app named `<target>` | `pkill -x "<target>"`; target is the process name (first 15 characters) |
| `group` | opens each listed alias in order; one failing member is reported and the rest still open | the same |

- Alias: lowercase letters, digits, `-` or `_`; not `add`, `rm`, `ls`, `find`, `scan` or `auto`.
- Values contain no tabs or newlines; a path is absolute and exists; the `with` app exists on this machine; a group lists saved aliases (not groups) separated by commas.
- A url may use `http`, `https`, `mailto`, `tel`, `sms`, `facetime`, `zoommtg`, `zoomus`, `msteams`, `slack`, `spotify` or `x-apple.systempreferences`. Links that can trigger actions inside other apps are refused. Auto-save keeps only plain `http(s)` addresses.
- An `app` or `with` value must be an installed GUI app: an `.app` bundle on macOS; on Linux a command or desktop-entry id that a launcher lists. A plain command such as `rm` or `sh` is refused, because these values are executed.
- `~/.bp/auto-off`, if present, switches auto-saving off.
- The script writes through a temporary file and renames it, so an interrupted write leaves the old file intact. Stray `aliases.tsv.tmp.*` files can be deleted.
- Linux app discovery reads `.desktop` files in `/usr/share/applications`, `/usr/local/share/applications`, `~/.local/share/applications`, the Flatpak export folders and `/var/lib/snapd/desktop/applications`. macOS discovery reads `.app` bundles in `/Applications`, its `Utilities` folder, `/System/Applications` and `~/Applications`.
