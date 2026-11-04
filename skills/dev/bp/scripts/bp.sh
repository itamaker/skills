#!/usr/bin/env bash
# bp.sh: nickname store and launcher for local apps, sites and folders.
# Works on macOS and Linux with only OS tools. Written for bash 3.2 (macOS).
#
# Usage: bp.sh <command> [args]     (bp.sh help lists the commands)
# Exit codes: 0 ok, 1 not found or usage, 2 invalid input, 3 alias conflict,
#             4 target missing on this machine, 5 launch failed, 6 not saved by rule.
set -u

BP_HOME="${BP_HOME:-$HOME/.bp}"
STORE="$BP_HOME/aliases.tsv"
TAB=$'\t'
NL=$'\n'
OS="$(uname -s)"
RESERVED="add rm ls find scan auto stop"

die() { code=$1; shift; printf 'bp: %s\n' "$*" >&2; exit "$code"; }

# One writer at a time: parallel bp.sh calls must not overwrite each other's changes.
LOCKDIR=""
lock() {
  mkdir -p "$BP_HOME" 2>/dev/null
  l="$BP_HOME/.lock"; tries=0
  while ! mkdir "$l" 2>/dev/null; do
    tries=$((tries + 1))
    # a lock older than a minute belongs to a process that died
    if [ $((tries % 20)) = 0 ] && [ -n "$(find "$l" -maxdepth 0 -mmin +1 2>/dev/null)" ]; then rmdir "$l" 2>/dev/null; continue; fi
    [ "$tries" -le 300 ] || die 1 "the shortcut file is busy (delete $l if no bp command is running)"
    sleep 0.1
  done
  LOCKDIR="$l"
  trap 'rmdir "$LOCKDIR" 2>/dev/null' EXIT
}

# Session-critical processes are never quit, and a target is never read as an option.
refuse_quit() {
  case "$1" in
    -*) die 2 "a quit target must not start with a dash" ;;
    systemd | init | launchd | loginwindow | WindowServer | Finder | Dock | SystemUIServer | Xorg | Xwayland | \
    gnome-shell | plasmashell | kwin_x11 | kwin_wayland | sshd | dbus-daemon | dbus-broker | pipewire | \
    pulseaudio | login | sudo | bash | zsh | fish | sh | dash)
      die 2 "refusing to quit a system or shell process: $1" ;;
  esac
}

# ---------- validation ----------

clean_value() { # non-empty, no tab or newline
  case "$1" in
    '' | *"$TAB"* | *"$NL"*) return 1 ;;
  esac
  return 0
}

valid_alias() {
  case "$1" in '' | *[!abcdefghijklmnopqrstuvwxyz0123456789_-]*) return 1 ;; esac
  for w in $RESERVED; do [ "$1" = "$w" ] && return 1; done
  return 0
}

valid_kind() { case "$1" in app | url | path | quit | group) return 0 ;; esac; return 1; }

# Link schemes a url shortcut may use. Others (file:, javascript:, data: ...) are refused.
url_scheme_ok() {
  case "$1" in
    http://* | https://* | mailto:* | tel:* | sms:* | facetime:* | zoommtg://* | zoomus://* | \
    msteams:* | slack://* | spotify:* | x-apple.systempreferences:*) return 0 ;;
  esac
  return 1
}

# ---------- store ----------

get_line() { # alias -> full line, status 1 if absent
  [ -f "$STORE" ] || return 1
  line="$(A="$1" awk -F'\t' '$1 == ENVIRON["A"] { print; exit }' "$STORE")"
  [ -n "$line" ] || return 1
  printf '%s\n' "$line"
}

alias_for() { # kind target with -> alias that already holds this triple
  [ -f "$STORE" ] || return 1
  found="$(K="$1" T="$2" W="${3:-}" awk -F'\t' \
    'ENVIRON["K"] == $2 && ENVIRON["T"] == $3 && ENVIRON["W"] == $4 { print $1; exit }' "$STORE")"
  [ -n "$found" ] || return 1
  printf '%s\n' "$found"
}

write_line() { # alias kind target with: replaces any line for that alias
  mkdir -p "$BP_HOME" || die 2 "cannot create $BP_HOME"
  touch "$STORE"
  tmp="$STORE.tmp.$$"
  {
    A="$1" awk -F'\t' '$1 != ENVIRON["A"]' "$STORE"
    printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "${4:-}"
  } >"$tmp" && mv "$tmp" "$STORE"
}

# ---------- installed apps ----------

app_dirs() {
  if [ -n "${BP_APP_DIRS:-}" ]; then
    printf '%s\n' "$BP_APP_DIRS" | tr ':' '\n'
  elif [ "$OS" = Darwin ]; then
    printf '%s\n' /Applications /Applications/Utilities /System/Applications \
      /System/Applications/Utilities "$HOME/Applications"
  else
    printf '%s\n' /usr/share/applications /usr/local/share/applications \
      "$HOME/.local/share/applications" /var/lib/flatpak/exports/share/applications \
      "$HOME/.local/share/flatpak/exports/share/applications" \
      /var/lib/snapd/desktop/applications
  fi
}

linux_apps() { # name<TAB>desktop-id<TAB>command, for launchers a menu would show
  app_dirs | while IFS= read -r d; do
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
  done
}

apps_list() { # name<TAB>target-to-save, sorted
  if [ "$OS" = Darwin ]; then
    app_dirs | while IFS= read -r d; do
      for a in "$d"/*.app; do
        [ -e "$a" ] || continue
        n="$(basename "$a" .app)"
        printf '%s\t%s\n' "$n" "$n"
      done
    done | sort -u
  else
    linux_apps | while IFS="$TAB" read -r n id cmd; do
      t="$id"; b="${cmd##*/}"
      case "$b" in
        flatpak | snap | sh | bash | dash | python | python3 | java | wine | xdg-open | gtk-launch) ;; # a wrapper: use the desktop id
        *)
          if [ -n "$b" ] && command -v "$b" >/dev/null 2>&1; then t="$b"
          elif [ -n "$cmd" ] && [ -x "$cmd" ]; then t="$cmd"; fi ;;
      esac
      printf '%s\t%s\n' "$n" "$t"
    done | sort -u
  fi
}

# True only for an installed GUI app: an .app bundle on macOS; on Linux a command or id that a
# desktop launcher lists. Any other command on PATH (rm, sh, ...) is refused on purpose, since a
# saved app or "with" value is executed.
app_exists() {
  [ -n "$1" ] || return 1
  if [ "$OS" = Darwin ]; then
    case "$1" in */*) return 1 ;; esac
    app_dirs | while IFS= read -r d; do [ -e "$d/$1.app" ] && echo y; done | grep -q y
  else
    [ -n "${APPS_CACHE+x}" ] || APPS_CACHE="$(apps_list)"
    printf '%s\n' "$APPS_CACHE" | cut -f2 | grep -qxF -- "$1" && return 0
    case "$1" in */*) return 1 ;; esac
    app_dirs | while IFS= read -r d; do [ -e "$d/$1.desktop" ] && echo y; done | grep -q y
  fi
}

# ---------- opening things ----------

detach() { setsid nohup "$@" >/dev/null 2>&1 & }

launch() { # kind target [with]
  kind="$1"; target="$2"; with="${3:-}"
  case "$kind" in
    app)
      if [ "$OS" = Darwin ]; then
        open -a "$target" || die 5 "could not open the app: $target"
      elif command -v "$target" >/dev/null 2>&1; then
        detach "$target"
      elif command -v gtk-launch >/dev/null 2>&1; then
        gtk-launch "$target" || die 5 "gtk-launch could not start: $target"
      else
        die 5 "cannot launch $target: no such command and gtk-launch is missing"
      fi ;;
    url | path)
      if [ "$OS" = Darwin ]; then
        if [ -n "$with" ]; then open -a "$with" "$target"; else open "$target"; fi ||
          die 5 "could not open: $target"
      elif [ -n "$with" ] && command -v "$with" >/dev/null 2>&1; then
        detach "$with" "$target"
      elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$target" || die 5 "xdg-open could not open: $target (it needs a desktop session)"
      else
        die 5 "xdg-open is missing; cannot open $target"
      fi ;;
    quit)
      if [ "$OS" = Darwin ]; then
        osascript -e 'on run argv' -e 'tell application (item 1 of argv) to quit' -e 'end run' "$target" ||
          die 5 "could not quit: $target"
      else
        pkill -x -- "${target:0:15}" || die 5 "no running process named $target"
      fi ;;
    *) die 2 "unknown kind: $kind" ;;
  esac
}

# ---------- commands ----------

cmd_list() {
  if [ ! -s "$STORE" ]; then echo "no shortcuts yet"; return 0; fi
  awk -F'\t' '{ printf "%-14s %-5s %s%s\n", $1, $2, $3, ($4 != "" ? "  (in " $4 ")" : "") }' "$STORE"
}

cmd_show() {
  [ $# -eq 1 ] || die 1 "usage: show <alias>"
  get_line "$1" || die 1 "no such alias: $1"
}

cmd_run() {
  [ $# -eq 1 ] || die 1 "usage: run <alias>"
  line="$(get_line "$1")" || die 1 "no such alias: $1"
  IFS="$TAB" read -r _ kind target with <<EOF
$line
EOF
  if [ "$kind" = group ]; then run_group "$target"; return; fi
  launch "$kind" "$target" "${with:-}"
  echo "asked to open $1 ($kind $target${with:+ in $with})"
}

run_group() { # members: open each in order, report failures, keep going
  failed=0
  err="$BP_HOME/.err.$$"
  old_ifs="$IFS"; IFS=','; set -f; set -- $1; set +f; IFS="$old_ifs"
  for m in "$@"; do
    if ml="$(get_line "$m")"; then
      IFS="$TAB" read -r _ k t w <<EOF
$ml
EOF
      if ( launch "$k" "$t" "${w:-}" ) 2>"$err"; then
        echo "asked to open $m ($k $t${w:+ in $w})"
      else
        failed=$((failed + 1)); echo "FAILED $m: $(cat "$err" 2>/dev/null)"
      fi
      sleep 0.3
    else
      failed=$((failed + 1)); echo "FAILED $m: no such alias"
    fi
  done
  rm -f "$err"
  [ "$failed" = 0 ] || exit 5
}

cmd_stop() { # quit the app behind an alias, or every app in a group
  [ $# -eq 1 ] || die 1 "usage: stop <alias>"
  line="$(get_line "$1")" || die 1 "no such alias: $1"
  IFS="$TAB" read -r _ kind target _w <<EOF
$line
EOF
  case "$kind" in
    app | quit) ( launch quit "$target" ) && echo "asked $target to quit" ;;
    group)
      old_ifs="$IFS"; IFS=','; set -f; set -- $target; set +f; IFS="$old_ifs"
      for m in "$@"; do
        ml="$(get_line "$m")" || continue
        IFS="$TAB" read -r _ k t _w <<EOF
$ml
EOF
        case "$k" in
          app | quit)
            if ( launch quit "$t" ) 2>/dev/null; then echo "asked $t to quit"; else echo "could not quit $t (not running?)"; fi ;;
        esac
      done ;;
    *) die 2 "nothing to quit for a $kind shortcut" ;;
  esac
}

cmd_running() {
  [ $# -ge 1 ] || die 1 "usage: running <process name>"
  name="$*"
  [ "$OS" = Darwin ] || name="${name:0:15}" # Linux process names are cut to 15 characters
  if pgrep -ix -- "$name" >/dev/null 2>&1; then echo "running: $*"; else echo "not running: $*"; return 1; fi
}

cmd_recent() { # newest files in Downloads, Desktop and Documents
  n="${1:-10}"
  case "$n" in '' | *[!0-9]*) die 2 "usage: recent [count]" ;; esac
  tmp="$(mktemp "${TMPDIR:-/tmp}/bp.XXXXXX")" || die 2 "cannot create a temporary file"
  dirs="${BP_RECENT_DIRS:-$HOME/Downloads:$HOME/Desktop:$HOME/Documents}"
  printf '%s\n' "$dirs" | tr ':' '\n' | while IFS= read -r d; do
    [ -d "$d" ] || continue
    if [ "$OS" = Darwin ]; then
      find "$d" -maxdepth 2 -type f ! -name '.*' -exec stat -f '%m %N' {} + 2>/dev/null
    else
      find "$d" -maxdepth 2 -type f ! -name '.*' -exec stat -c '%Y %n' {} + 2>/dev/null
    fi
  done >"$tmp"
  if [ ! -s "$tmp" ]; then rm -f "$tmp"; echo "no recent files"; return 1; fi
  sort -rn "$tmp" | head -n "$n" | while IFS= read -r row; do
    ts="${row%% *}"; f="${row#* }"
    if [ "$OS" = Darwin ]; then when="$(date -r "$ts" '+%Y-%m-%d %H:%M')"; else when="$(date -d "@$ts" '+%Y-%m-%d %H:%M')"; fi
    printf '%s\t%s\n' "$when" "$f"
  done
  rm -f "$tmp"
}

cmd_files() { # files <text> [folder]: find files by name, default under the home folder
  [ $# -ge 1 ] || die 1 "usage: files <text> [folder]"
  text="$1"; root="${2:-$HOME}"
  [ -d "$root" ] || die 4 "folder does not exist: $root"
  out=""
  if [ "$OS" = Darwin ] && command -v mdfind >/dev/null 2>&1; then
    out="$(mdfind -onlyin "$root" -name "$text" 2>/dev/null | head -n 20)"
  fi
  if [ -z "$out" ]; then
    pat="$(printf '%s' "$text" | sed -e 's/[][*?\\]/\\&/g')"
    out="$(find "$root" -maxdepth 5 \( -name '.*' -o -name node_modules -o -name Library \) -prune \
      -o -iname "*$pat*" -print 2>/dev/null | head -n 20)"
  fi
  [ -n "$out" ] || { echo "no file matches '$text'"; return 1; }
  printf '%s\n' "$out"
}

cmd_launch() { # open without saving: launch <kind> <target> [with]
  [ $# -ge 2 ] || die 1 "usage: launch <kind> <target> [with]"
  valid_kind "$1" || die 2 "kind must be app, url, path, quit or group"
  clean_value "$2" || die 2 "invalid target"
  if [ -n "${3:-}" ]; then clean_value "$3" || die 2 "invalid 'with' value"; fi
  case "$1" in
    url) url_scheme_ok "$2" || die 2 "unsupported link scheme: $2" ;;
    path) case "$2" in /*) ;; *) die 2 "a path must be absolute (expand ~ first)" ;; esac ;;
    app) app_exists "$2" || die 4 "no installed app matches '$2' (try: find <text>)" ;;
    quit) refuse_quit "$2" ;;
  esac
  if [ -n "${3:-}" ]; then
    case "$1" in url | path) ;; *) die 2 "'with' only applies to url and path" ;; esac
    app_exists "$3" || die 4 "'with' app not found on this machine: $3 (use the name or command that 'find' prints)"
  fi
  launch "$1" "$2" "${3:-}"
  echo "asked to open $1 $2${3:+ in $3}"
}

url_ok_for_auto() { # stable entry points only: no query, fragment or credentials
  case "$1" in
    http://* | https://*) ;;
    *) return 1 ;;
  esac
  case "$1" in *\?* | *\#*) return 1 ;; esac
  rest="${1#*://}"
  hostpart="${rest%%/*}"
  case "$hostpart" in *@*) return 1 ;; esac
  return 0
}

cmd_add() {
  auto=0; replace=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --auto) auto=1; shift ;;
      --replace) replace=1; shift ;;
      *) break ;;
    esac
  done
  [ $# -ge 3 ] || die 1 "usage: add [--auto] [--replace] <alias> <kind> <target> [with]"
  al="$1"; kind="$2"; target="$3"; with="${4:-}"

  valid_alias "$al" || die 2 "invalid alias '$al' (lowercase letters, digits, - and _; not: $RESERVED)"
  valid_kind "$kind" || die 2 "kind must be app, url, path, quit or group"
  clean_value "$target" || die 2 "invalid target (empty, or contains a tab or newline)"
  if [ -n "$with" ]; then
    clean_value "$with" || die 2 "invalid 'with' value"
    case "$kind" in url | path) ;; *) die 2 "'with' only applies to url and path" ;; esac
  fi

  if [ "$auto" = 1 ] && [ -e "$BP_HOME/auto-off" ]; then
    echo "auto-save is off; nothing saved"; return 0
  fi

  if [ -n "$with" ] && ! app_exists "$with"; then
    die 4 "'with' app not found on this machine: $with (use the name or command that 'find' prints)"
  fi

  case "$kind" in
    group)
      [ "$auto" = 0 ] || die 6 "not saved: groups are never created by auto-save"
      case "$target" in *,,* | ,* | *,) die 2 "a group is a comma-separated list of aliases" ;; esac
      old_ifs="$IFS"; IFS=','; set -f; set -- $target; set +f; IFS="$old_ifs"
      for m in "$@"; do
        ml="$(get_line "$m")" || die 4 "group member is not a saved alias: $m"
        case "$ml" in *"${TAB}group${TAB}"*) die 2 "a group cannot contain another group: $m" ;; esac
      done ;;
    url)
      url_scheme_ok "$target" || die 2 "unsupported link scheme (allowed: http, https, mailto, tel, sms, facetime, zoommtg, zoomus, msteams, slack, spotify, x-apple.systempreferences)"
      if [ "$auto" = 1 ] && ! url_ok_for_auto "$target"; then
        die 6 "not saved: auto-save keeps only plain entry points (no query, fragment or credentials)"
      fi ;;
    path)
      case "$target" in /*) ;; *) die 2 "a path must be absolute (expand ~ first)" ;; esac
      [ -e "$target" ] || die 4 "path does not exist: $target" ;;
    app)
      app_exists "$target" || die 4 "no installed app matches '$target' (try: find <text>)" ;;
    quit) refuse_quit "$target" ;;
  esac

  lock
  if existing="$(alias_for "$kind" "$target" "$with")"; then
    echo "already saved as $existing"; return 0
  fi

  if old="$(get_line "$al")"; then
    if [ "$auto" = 1 ]; then # never replace in auto mode: take the next free suffix
      n=2
      while get_line "$al-$n" >/dev/null 2>&1; do n=$((n + 1)); done
      al="$al-$n"
    elif [ "$replace" = 0 ]; then
      printf 'bp: alias "%s" already exists: %s\n' "$al" "$old" >&2
      printf 'bp: rerun with --replace to overwrite it\n' >&2
      exit 3
    fi
  fi

  write_line "$al" "$kind" "$target" "$with"
  echo "saved: $al  $kind  $target${with:+  (in $with)}"
}

cmd_rm() {
  [ $# -eq 1 ] || die 1 "usage: rm <alias>"
  get_line "$1" >/dev/null || die 1 "no such alias: $1"
  refs="$(M="$1" awk -F'\t' '$2 == "group" { n = split($3, a, ","); for (i = 1; i <= n; i++) if (a[i] == ENVIRON["M"]) print $1 }' "$STORE" | tr '\n' ' ')"
  [ -z "$refs" ] || echo "note: still listed in group(s): $refs" >&2
  lock
  tmp="$STORE.tmp.$$"
  A="$1" awk -F'\t' '$1 != ENVIRON["A"]' "$STORE" >"$tmp" && mv "$tmp" "$STORE"
  echo "removed: $1"
}

cmd_clear() {
  [ "${1:-}" = "--yes" ] || die 1 "usage: clear --yes   (removes every shortcut)"
  if [ -f "$STORE" ]; then
    lock
    : >"$STORE" || die 1 "could not clear $STORE"
  fi
  echo "all shortcuts removed"
}

cmd_find() {
  [ $# -ge 1 ] || die 1 "usage: find <text>"
  out="$(apps_list | grep -iF -- "$*")" || { echo "no installed app matches '$*'"; return 1; }
  printf '%s\n' "$out"
}

category_pattern() { # extended-regex of name fragments for a kind of app
  case "$1" in
    drawing) echo 'paint|draw|sketch|krita|gimp|inkscape|pixelmator|affinity|freeform|whiteboard|procreate|illustrator|photoshop|figma|canva|excalidraw' ;;
    browser) echo 'chrome|chromium|firefox|safari|edge|brave|opera|vivaldi|arc' ;;
    editor) echo 'code|vim|emacs|sublime|textedit|text editor|gedit|kate|zed|cursor|xcode|intellij|pycharm|webstorm|notepad' ;;
    terminal) echo 'terminal|iterm|konsole|alacritty|kitty|wezterm|tilix|xterm|ghostty' ;;
    mail) echo 'mail|thunderbird|outlook|evolution|geary|spark' ;;
    chat) echo 'slack|discord|telegram|wechat|weixin|teams|zoom|signal|element|messages|whatsapp|line|feishu|lark|dingtalk|qq' ;;
    music) echo 'music|spotify|rhythmbox|clementine|netease|qqmusic|amarok' ;;
    video) echo 'vlc|mpv|quicktime|iina|totem|celluloid|bilibili' ;;
    notes) echo 'notes|obsidian|notion|joplin|bear|typora|evernote|logseq' ;;
    office) echo 'word|excel|powerpoint|pages|numbers|keynote|libreoffice|wps|onlyoffice' ;;
    spreadsheet) echo 'excel|numbers|calc|wps' ;;
    files) echo 'finder|files|nautilus|dolphin|thunar|nemo|pcmanfm' ;;
    settings) echo 'settings|preferences|control center' ;;
    *) return 1 ;;
  esac
}

CATEGORIES="drawing browser editor terminal mail chat music video notes office spreadsheet files settings"

cmd_category() { # installed apps of one kind, for requests like "open a drawing app"
  if [ $# -eq 0 ]; then echo "categories: $CATEGORIES"; return 0; fi
  pat="$(category_pattern "$1")" || die 1 "unknown category '$1' (categories: $CATEGORIES)"
  out="$(apps_list | grep -iE -- "$pat")" || { echo "no installed app in category '$1'"; return 1; }
  printf '%s\n' "$out"
}

cmd_outfile() { # a free absolute path for a file you are about to create for the user
  [ $# -eq 1 ] || die 1 "usage: outfile <filename.ext>"
  name="$1"
  case "$name" in
    */* | .* | '') die 2 "give a plain file name, no folders and no leading dot" ;;
  esac
  clean_value "$name" || die 2 "invalid file name"
  ext="$(printf '%s' "${name##*.}" | LC_ALL=C tr 'A-Z' 'a-z')"
  [ "$ext" != "$name" ] || ext=""
  case "$ext" in
    svg | png | jpg | jpeg | gif | webp | bmp) dir="${BP_OUT:-$HOME/Pictures/bp}" ;;
    *) dir="${BP_OUT:-$HOME/Documents/bp}" ;;
  esac
  mkdir -p "$dir" || die 2 "cannot create $dir"
  base="${name%.*}"; [ -n "$ext" ] || base="$name"
  cand="$dir/$name"; n=2
  while [ -e "$cand" ]; do
    if [ -n "$ext" ]; then cand="$dir/$base-$n.${name##*.}"; else cand="$dir/$base-$n"; fi
    n=$((n + 1))
  done
  printf '%s\n' "$cand"
}

cmd_scan() {
  S="$([ -f "$STORE" ] && cut -f3 "$STORE")"
  apps_list | S="$S" awk -F'\t' '
    BEGIN { n = split(ENVIRON["S"], a, "\n"); for (i = 1; i <= n; i++) if (a[i] != "") s[a[i]] = 1 }
    !($2 in s)'
}

cmd_alias() { # suggest an alias for an app name
  [ $# -ge 1 ] || die 1 "usage: alias <app name>"
  s="$(printf '%s' "$*" | LC_ALL=C tr 'A-Z' 'a-z' | LC_ALL=C tr -c 'a-z0-9' '-' |
    sed -e 's/--*/-/g' -e 's/^-//' -e 's/-$//')"
  case "$s" in
    google-* | microsoft-* | apple-* | adobe-*) rest="${s#*-}"; [ -n "$rest" ] && s="$rest" ;;
  esac
  [ -n "$s" ] || die 2 "no ASCII letters or digits to build an alias from; choose one by hand"
  valid_alias "$s" || s="$s-app"
  printf '%s\n' "$s"
}

cmd_urlenc() {
  LC_ALL=C
  s="$*"; i=0; out=""
  while [ "$i" -lt "${#s}" ]; do
    c="${s:$i:1}"
    case "$c" in
      [abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.~_-]) out="$out$c" ;;
      *) v="$(printf '%d' "'$c")"; out="$out$(printf '%%%02X' $((v & 255)))" ;;
    esac
    i=$((i + 1))
  done
  printf '%s\n' "$out"
}

cmd_auto() {
  case "${1:-status}" in
    on) rm -f "$BP_HOME/auto-off"; echo "auto-save: on" ;;
    off) mkdir -p "$BP_HOME" && : >"$BP_HOME/auto-off"; echo "auto-save: off" ;;
    status) if [ -e "$BP_HOME/auto-off" ]; then echo "auto-save: off"; else echo "auto-save: on"; fi ;;
    *) die 1 "usage: auto [on|off|status]" ;;
  esac
}

cmd_help() {
  cat <<'EOF'
bp.sh <command>
  list                          show saved shortcuts
  show <alias>                  print one line: alias kind target [with]
  run <alias>                   open a saved shortcut (a group opens its members in order)
  stop <alias>                  quit the app behind an alias, or every app in a group
  running <process name>        is a process running? (names can differ from commands)
  recent [count]                newest files in Downloads, Desktop and Documents
  files <text> [folder]         find files by name (default: under the home folder)
  launch <kind> <target> [with] open something without saving it
  add [--auto] [--replace] <alias> <kind> <target> [with]
                                kinds: app url path quit group
                                a group target is a comma-separated list of aliases
  rm <alias>                    remove one shortcut
  clear --yes                   remove all shortcuts
  find <text>                   installed apps matching text (name<TAB>target)
  scan                          installed apps not yet saved (name<TAB>target)
  category [name]               installed apps of one kind (drawing, browser, editor, ...)
  outfile <filename.ext>        a free path under ~/Pictures/bp or ~/Documents/bp for a file you create
  alias <app name>              suggest an alias
  urlenc <text>                 percent-encode text for a URL
  auto [on|off|status]          switch auto-saving
Store: $BP_HOME/aliases.tsv (default ~/.bp)
EOF
}

main() {
  [ $# -ge 1 ] || { cmd_help; exit 1; }
  c="$1"; shift
  case "$c" in
    list | ls) cmd_list "$@" ;;
    show) cmd_show "$@" ;;
    run) cmd_run "$@" ;;
    stop) cmd_stop "$@" ;;
    running) cmd_running "$@" ;;
    recent) cmd_recent "$@" ;;
    files) cmd_files "$@" ;;
    launch) cmd_launch "$@" ;;
    add) cmd_add "$@" ;;
    rm) cmd_rm "$@" ;;
    clear) cmd_clear "$@" ;;
    find) cmd_find "$@" ;;
    scan) cmd_scan "$@" ;;
    category) cmd_category "$@" ;;
    outfile) cmd_outfile "$@" ;;
    alias) cmd_alias "$@" ;;
    urlenc) cmd_urlenc "$@" ;;
    auto) cmd_auto "$@" ;;
    help | -h | --help) cmd_help ;;
    *) die 1 "unknown command: $c (try: help)" ;;
  esac
}

main "$@"
