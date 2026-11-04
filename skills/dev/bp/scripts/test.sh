#!/usr/bin/env bash
# Checks bp.sh against stand-ins for open, osascript, xdg-open, gtk-launch and pkill.
# Touches nothing outside a temp directory. Run: bash scripts/test.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
BP="$HERE/bp.sh"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin" "$T/apps" "$T/home"
LOG="$T/calls.log"
TAB=$'\t'

# Stand-ins: each records its name and arguments, one call per line.
for c in open osascript xdg-open gtk-launch pkill google-chrome google-chrome-stable myeditor flatpak; do
  printf '#!/bin/sh\nprintf "%s" "%s" >>"%s"\nfor a in "$@"; do printf " [%%s]" "$a" >>"%s"; done\nprintf "\\n" >>"%s"\n' \
    '%s' "$c" "$LOG" "$LOG" "$LOG" >"$T/bin/$c"
  chmod +x "$T/bin/$c"
done
export PATH="$T/bin:$PATH" HOME="$T/home" BP_HOME="$T/home/.bp" BP_APP_DIRS="$T/apps"

# Sample installed apps, in both the macOS and the Linux layout.
mkdir -p "$T/apps/Safari.app" "$T/apps/Google Chrome.app"
printf '[Desktop Entry]\nType=Application\nName=Google Chrome\nName[zh_CN]=x\nExec=/usr/bin/google-chrome %%U\n\n[Desktop Action w]\nName=New Window\nExec=other\n' >"$T/apps/google-chrome.desktop"
printf '[Desktop Entry]\nType=Application\nName=My Editor\nExec=env FOO=1 myeditor %%F\n' >"$T/apps/myeditor.desktop"
printf '[Desktop Entry]\nType=Application\nName=Hidden\nExec=hid\nNoDisplay=true\n' >"$T/apps/hidden.desktop"
printf '[Desktop Entry]\nType=Link\nName=A Link\nURL=https://x\n' >"$T/apps/link.desktop"
printf '[Desktop Entry]\nType=Application\nName=Menu Only\nExec=not-on-path\n' >"$T/apps/menu-only.desktop"

pass=0; fail=0
ok() { pass=$((pass + 1)); }
bad() { fail=$((fail + 1)); printf 'FAIL: %s\n' "$1"; [ -n "${2:-}" ] && printf '      %s\n' "$2"; }
run_bp() { OUT="$(bash "$BP" "$@" 2>&1)"; RC=$?; }
expect_rc() { # name expected_rc args...
  name="$1"; want="$2"; shift 2; run_bp "$@"
  if [ "$RC" = "$want" ]; then ok; else bad "$name" "exit $RC, wanted $want: $OUT"; fi
}
expect_out() { case "$OUT" in *"$2"*) ok ;; *) bad "$1" "output lacks '$2': $OUT" ;; esac; }
expect_no_out() { case "$OUT" in *"$2"*) bad "$1" "output has '$2': $OUT" ;; *) ok ;; esac; }
expect_log() { if grep -qF -- "$2" "$LOG" 2>/dev/null; then ok; else bad "$1" "no call matching '$2' in: $(cat "$LOG" 2>/dev/null)"; fi; }
store_lines() { [ -f "$BP_HOME/aliases.tsv" ] && wc -l <"$BP_HOME/aliases.tsv" | tr -d ' ' || echo 0; }

: >"$LOG"
IS_MAC=0; [ "$(uname -s)" = Darwin ] && IS_MAC=1

# --- empty store
expect_rc "list with no store" 0 list
expect_out "list says empty" "no shortcuts yet"
expect_rc "run unknown alias" 1 run nope
expect_rc "rm unknown alias" 1 rm nope

# --- add and validation
if [ "$IS_MAC" = 1 ]; then APPT="Google Chrome"; else APPT="google-chrome"; fi
expect_rc "add app" 0 add chrome app "$APPT"
expect_rc "add url in browser" 0 add gmail url https://mail.google.com "$APPT"
expect_rc "add path" 0 add work path "$T"
expect_rc "add quit" 0 add chrome-off quit "$APPT"
expect_rc "list" 0 list
expect_out "list shows with" "(in $APPT)"
expect_rc "show" 0 show gmail
expect_out "show line" "https://mail.google.com"
expect_rc "alias with uppercase" 2 add Chrome2 app "$APPT"
expect_rc "alias with space" 2 add "a b" app "$APPT"
expect_rc "reserved alias" 2 add ls url https://example.com
expect_rc "shell metacharacters in alias" 2 add 'x;touch pwn' url https://example.com
expect_rc "unknown kind" 2 add k1 browser x
expect_rc "tab in target" 2 add k2 url "https://a.test/$(printf '\t')x"
expect_rc "url without scheme" 2 add k3 url example.com
expect_rc "relative path" 2 add k4 path relative/dir
expect_rc "missing path" 4 add k5 path "$T/does-not-exist"
expect_rc "missing app" 4 add k6 app "No Such App 9"
expect_rc "with on app" 2 add k7 app "$APPT" "$APPT"
[ "$(store_lines)" = 4 ] && ok || bad "invalid adds left the store unchanged" "lines: $(store_lines)"

# --- conflicts and duplicates
expect_rc "alias conflict" 3 add gmail url https://mail.google.com/other
expect_out "conflict shows old line" "https://mail.google.com"
expect_rc "replace" 0 add --replace gmail url https://mail.google.com/other "$APPT"
expect_rc "same target under another alias" 0 add mail2 url https://mail.google.com/other "$APPT"
expect_out "reports existing alias" "already saved as gmail"
[ "$(store_lines)" = 4 ] && ok || bad "duplicate add left the store unchanged" "lines: $(store_lines)"

# --- run
: >"$LOG"
if [ "$IS_MAC" = 1 ]; then
  expect_rc "run app" 0 run chrome;        expect_log "mac app uses open -a" "open [-a] [Google Chrome]"
  expect_rc "run url in browser" 0 run gmail; expect_log "mac url uses open -a with" "open [-a] [Google Chrome] [https://mail.google.com/other]"
  expect_rc "run quit" 0 run chrome-off;   expect_log "mac quit uses osascript" "osascript"
else
  expect_rc "run app" 0 run chrome;        sleep 0.3; expect_log "linux app runs the command" "google-chrome"
  : >"$LOG"
  expect_rc "run url in browser" 0 run gmail; sleep 0.3; expect_log "linux url goes to the browser" "google-chrome [https://mail.google.com/other]"
  expect_rc "run path" 0 run work;         expect_log "linux path uses xdg-open" "xdg-open [$T]"
  expect_rc "run quit" 0 run chrome-off;   expect_log "linux quit uses pkill -x" "pkill [-x] [--] [google-chrome]"
fi
# a value that looks like shell code must arrive as one literal argument
: >"$LOG"
expect_rc "literal target" 0 add --replace weird url 'https://a.test/$(touch pwned)?q=1;x'
expect_rc "launch literal target" 0 launch url 'https://a.test/$(touch pwned)?q=1;x'
[ ! -e pwned ] && [ ! -e "$T/pwned" ] && ok || bad "target was not executed as code"
expect_rc "launch bad kind" 2 launch exe foo
# a saved or launched "app" or "with" must be an installed GUI app, never any command on PATH
expect_rc "with: a plain command is refused" 4 add evil path "$T" rm
expect_rc "app: a plain command is refused" 4 add evil2 app rm
expect_rc "launch with: a plain command is refused" 4 launch path "$T" rm
expect_rc "launch app: a plain command is refused" 4 launch app ls
expect_rc "with: a path is refused" 4 add evil3 path "$T" /bin/rm
[ ! -e "$BP_HOME/aliases.tsv" ] || ! grep -q '^evil' "$BP_HOME/aliases.tsv" && ok || bad "refused adds were not saved"
expect_rc "launch refuses file: links" 2 launch url 'file:///etc/passwd'
expect_rc "launch refuses javascript: links" 2 launch url 'javascript:alert(1)'
expect_rc "launch refuses relative paths" 2 launch path relative/file.pdf
expect_rc "launch allows a mailto link" 0 launch url 'mailto:a@b.test'
expect_rc "rm literal" 0 rm weird

# --- auto-save rules
n0="$(store_lines)"
expect_rc "auto: query string" 6 add --auto q1 url 'https://www.youtube.com/results?search_query=x'
expect_rc "auto: fragment" 6 add --auto q2 url 'https://mail.google.com/mail/u/0/#inbox/abc'
expect_rc "auto: credentials" 6 add --auto q3 url 'https://user:pw@example.com'
expect_rc "auto: plain entry point" 0 add --auto youtube url https://www.youtube.com
expect_rc "auto: name taken, different target" 0 add --auto youtube url https://m.youtube.com
expect_out "auto: suffix used" "youtube-2"
expect_rc "auto: repeat is a no-op" 0 add --auto youtube url https://www.youtube.com
expect_out "auto: repeat reports" "already saved as youtube"
[ "$(store_lines)" = $((n0 + 2)) ] && ok || bad "auto-save added exactly two lines" "before $n0, now $(store_lines)"
expect_rc "auto off" 0 auto off
expect_rc "auto: off saves nothing" 0 add --auto nothere url https://off.test
expect_out "auto: off says so" "auto-save is off"
expect_rc "manual add still works when off" 0 add manual url https://manual.test
expect_rc "auto status" 0 auto status
expect_out "status is off" "off"
expect_rc "auto on" 0 auto on
expect_rc "auto: off saved nothing" 1 show nothere

# --- remove
expect_rc "rm" 0 rm manual
expect_rc "rm again" 1 rm manual
expect_rc "clear needs --yes" 1 clear
n1="$(store_lines)"; [ "$n1" -gt 0 ] && ok || bad "clear without --yes kept the store"
expect_rc "clear --yes" 0 clear --yes
expect_rc "list after clear" 0 list
expect_out "list empty again" "no shortcuts yet"

# --- find and scan (the sample apps exist in both layouts)
expect_rc "find chrome" 0 find chrome
expect_out "find shows Chrome" "Chrome"
expect_rc "find no match" 1 find zzzz-nothing
if [ "$IS_MAC" = 1 ]; then
  expect_rc "scan lists apps" 0 scan; expect_out "scan has Safari" "Safari"
else
  expect_rc "scan lists apps" 0 scan
  expect_out "scan has My Editor" "My Editor"
  expect_out "command from Exec, env prefix skipped" "myeditor"
  expect_no_out "hidden launcher skipped" "Hidden"
  expect_no_out "non-application skipped" "A Link"
  expect_out "falls back to desktop id" "menu-only"
  expect_no_out "localized name ignored" "Name[zh_CN]"
  run_bp add chrome app "$APPT"
  run_bp scan
  expect_no_out "scan hides saved apps" "Google Chrome"
fi

# --- link schemes
expect_rc "mailto allowed" 0 add mail url 'mailto:a@b.test?subject=hi'
expect_rc "zoom link allowed" 0 add standup url 'zoommtg://zoom.us/join?confno=123'
expect_rc "app-internal links refused" 2 add n1 url 'obsidian://open?vault=x'
expect_rc "editor deep links refused" 2 add n2 url 'vscode://file/etc/passwd'
expect_rc "file: refused" 2 add f1 url 'file:///etc/passwd'
expect_rc "javascript: refused" 2 add f2 url 'javascript:alert(1)'
expect_rc "auto-save refuses non-web links" 6 add --auto z1 url 'zoommtg://zoom.us/join?confno=9'
expect_rc "auto-save refuses mailto" 6 add --auto z2 url 'mailto:a@b.test'
expect_rc "with app must exist" 4 add k8 url https://x.test no-such-browser

# --- groups
expect_rc "group setup: app" 0 add chrome app "$APPT"
expect_rc "group setup: url" 0 add gmail url https://mail.google.com "$APPT"
expect_rc "group setup: path" 0 add work-dir path "$T"
expect_rc "make group" 0 add morning group chrome,gmail,work-dir
expect_rc "group with missing member" 4 add g2 group chrome,nope
expect_rc "group with empty element" 2 add g3 group chrome,,gmail
expect_rc "group inside group" 2 add g4 group morning,chrome
expect_rc "auto-save never makes groups" 6 add --auto g5 group chrome,gmail
expect_rc "list shows group" 0 list
expect_out "group members shown" "chrome,gmail,work-dir"
: >"$LOG"
expect_rc "run group" 0 run morning
expect_out "group reports each member" "asked to open work-dir"
sleep 0.5
calls_n="$(grep -c . "$LOG")"; [ "$calls_n" = 3 ] && ok || bad "group made three launches" "calls: $calls_n: $(cat "$LOG")"
# a failing member must not stop the rest, and the group must report failure
if [ "$IS_MAC" = 1 ]; then OPENER=open; else OPENER=xdg-open; fi
cp "$T/bin/$OPENER" "$T/bin/$OPENER.keep"
printf '#!/bin/sh\necho "boom" >&2\nexit 1\n' >"$T/bin/$OPENER"; chmod +x "$T/bin/$OPENER"
expect_rc "ordinary url member to fail" 0 add plain-site url https://plain.test
expect_rc "group with a failing member" 0 add mixed group plain-site,chrome
: >"$LOG"
expect_rc "run mixed group reports failure" 5 run mixed
expect_out "failure named" "FAILED plain-site"
expect_out "later member still opened" "asked to open chrome"
mv "$T/bin/$OPENER.keep" "$T/bin/$OPENER"
expect_rc "rm group member notes the group" 0 rm chrome
expect_out "note names the group" "morning"

# --- stop and running
: >"$LOG"
expect_rc "stop a group" 0 stop morning
expect_rc "stop a url shortcut" 2 stop gmail
expect_rc "stop unknown" 1 stop nope
expect_rc "running: this shell's bash" 0 running bash
expect_rc "running: not running" 1 running no-such-process-xyz
if [ "$IS_MAC" = 0 ]; then # Linux cuts process names to 15 characters
  printf '#!/bin/sh\nsleep 5\n' >"$T/bin/averyveryverylongprocessname"; chmod +x "$T/bin/averyveryverylongprocessname"
  ( "$T/bin/averyveryverylongprocessname" >/dev/null 2>&1 & )
  sleep 0.5
  expect_rc "running: a command name longer than 15 characters" 0 running averyveryverylongprocessname
  command -p pkill -f averyveryverylongprocessname 2>/dev/null
fi

# --- recent and files
mkdir -p "$T/dl" "$T/home/Projects/sub"
printf x >"$T/dl/old.pdf"; touch -t 202401010101 "$T/dl/old.pdf"
printf x >"$T/dl/mid.pdf"; touch -t 202501010101 "$T/dl/mid.pdf"
printf x >"$T/dl/new.pdf"
printf x >"$T/dl/.hidden"
export BP_RECENT_DIRS="$T/dl"
expect_rc "recent" 0 recent 2
first="$(printf '%s\n' "$OUT" | sed -n 1p)"; second="$(printf '%s\n' "$OUT" | sed -n 2p)"
case "$first" in *new.pdf) ok ;; *) bad "recent: newest first" "$OUT" ;; esac
case "$second" in *mid.pdf) ok ;; *) bad "recent: then the next newest" "$OUT" ;; esac
expect_no_out "recent: hidden files skipped" ".hidden"
expect_no_out "recent: count respected" "old.pdf"
expect_rc "recent: bad count" 2 recent abc
export BP_RECENT_DIRS="$T/empty"
expect_rc "recent: nothing there" 1 recent
unset BP_RECENT_DIRS
printf x >"$T/home/Projects/sub/Report-Final.pdf"; printf x >"$T/home/Projects/notes.txt"
expect_rc "files finds by name" 0 files report
expect_out "files path printed" "Report-Final.pdf"
expect_rc "files: case-insensitive" 0 files REPORT
expect_rc "files: no match" 1 files zzz-nothing
expect_rc "files: glob characters are literal" 1 files '[x]*'
expect_rc "files: in a folder" 0 files notes "$T/home/Projects"
expect_rc "files: missing folder" 4 files notes "$T/does-not-exist"

# --- category and outfile
mkdir -p "$T/apps/Krita.app"
printf '[Desktop Entry]\nType=Application\nName=Krita\nExec=krita %%F\n' >"$T/apps/krita.desktop"
printf '[Desktop Entry]\nType=Application\nName=Inkscape\nExec=inkscape %%F\n' >"$T/apps/inkscape.desktop"
expect_rc "category list" 0 category
expect_out "category list names drawing" "drawing"
expect_rc "category drawing" 0 category drawing
expect_out "drawing finds Krita" "Krita"
if [ "$IS_MAC" = 0 ]; then expect_out "drawing finds Inkscape" "Inkscape"; fi
expect_rc "category browser finds Chrome" 0 category browser
expect_out "browser has Chrome" "Chrome"
expect_rc "category with no match" 1 category music
expect_rc "unknown category" 1 category nonsense
export BP_OUT=""; unset BP_OUT
expect_rc "outfile picture" 0 outfile cat.svg
[ "$OUT" = "$T/home/Pictures/bp/cat.svg" ] && ok || bad "picture goes to Pictures/bp" "$OUT"
[ -d "$T/home/Pictures/bp" ] && ok || bad "outfile creates the folder"
printf x >"$T/home/Pictures/bp/cat.svg"
expect_rc "outfile does not overwrite" 0 outfile cat.svg
[ "$OUT" = "$T/home/Pictures/bp/cat-2.svg" ] && ok || bad "second file gets -2" "$OUT"
expect_rc "outfile document" 0 outfile notes.md
[ "$OUT" = "$T/home/Documents/bp/notes.md" ] && ok || bad "document goes to Documents/bp" "$OUT"
expect_rc "outfile without extension" 0 outfile README
[ "$OUT" = "$T/home/Documents/bp/README" ] && ok || bad "no extension" "$OUT"
expect_rc "outfile refuses folders" 2 outfile ../x.svg
expect_rc "outfile refuses dotfiles" 2 outfile .bashrc
expect_rc "outfile needs a name" 1 outfile
BP_OUT="$T/out" bash "$BP" outfile a.svg | grep -qx "$T/out/a.svg" && ok || bad "BP_OUT overrides the folder"

# --- review fixes: locking, wrappers, quit targets, reserved words
rm -f "$BP_HOME/aliases.tsv"
for i in 1 2 3 4 5 6 7 8; do bash "$BP" add "par$i" url "https://par$i.test" >/dev/null 2>&1 & done
wait
[ "$(store_lines)" = 8 ] && ok || bad "eight parallel adds all landed" "lines: $(store_lines)"
[ ! -e "$BP_HOME/.lock" ] && ok || bad "the lock is released"
expect_rc "clear removes everything" 0 clear --yes
[ "$(store_lines)" = 0 ] && ok || bad "clear emptied the store"
expect_rc "stop is a reserved alias" 2 add stop url https://stop.test
expect_rc "quit refuses a session process" 2 add k9 quit sshd
expect_rc "launch quit refuses a shell" 2 launch quit bash
expect_rc "launch quit refuses an option-like name" 2 launch quit -9
expect_rc "add quit refuses an option-like name" 2 add k10 quit -9
if [ "$IS_MAC" = 0 ]; then
  printf '[Desktop Entry]\nType=Application\nName=Wrapped App\nExec=/usr/bin/flatpak run --branch=stable org.example.Wrapped %%U\n' >"$T/apps/org.example.Wrapped.desktop"
  expect_rc "flatpak launcher" 0 find "Wrapped App"
  expect_out "wrapper launchers use the desktop id" "org.example.Wrapped"
  case "$OUT" in *"$TAB"flatpak*) bad "target must not be the wrapper command" "$OUT" ;; *) ok ;; esac
fi

# --- helpers
expect_rc "alias: Google Chrome" 0 alias "Google Chrome"; [ "$OUT" = chrome ] && ok || bad "alias for Google Chrome" "$OUT"
expect_rc "alias: Visual Studio Code" 0 alias "Visual Studio Code"; [ "$OUT" = visual-studio-code ] && ok || bad "alias for VS Code" "$OUT"
expect_rc "alias: reserved word" 0 alias "Add"; [ "$OUT" = add-app ] && ok || bad "alias for Add" "$OUT"
expect_rc "alias: no ASCII" 2 alias "微信"
expect_rc "urlenc" 0 urlenc "老高 a&b=c/中"; [ "$OUT" = "%E8%80%81%E9%AB%98%20a%26b%3Dc%2F%E4%B8%AD" ] && ok || bad "urlenc output" "$OUT"
expect_rc "unknown command" 1 frobnicate
expect_rc "help" 0 help

printf '%s passed, %s failed\n' "$pass" "$fail"
[ "$fail" = 0 ]
