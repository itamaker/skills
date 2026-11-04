# Everyday scenarios

How common computer jobs map onto `scripts/bp.sh` (`$BP` below). Read the row that matches; most tasks are one or two commands. Each `launch` opens without saving; add `--auto` saves only where the table says so.

| The user wants | Do |
|---|---|
| **Start a work setup** ("上班", "start my day") | Save once: `$BP add work group chrome,gmail,slack`. Then `/bp work` is `$BP run work`; members open in order and a failing one is reported without stopping the rest. Groups hold aliases, so save the members first. |
| **End the day / close the apps** | `$BP stop work` asks every app in the group to quit. One app: `$BP stop slack`. Warn first if an app may hold unsaved work. |
| **Open a folder** (Downloads, Desktop, a project) | `$BP launch path /absolute/path`. Expand `~`, `~/Downloads`, `~/Desktop`, `~/Documents` to the real home path first. |
| **Open a project in the editor** | `$BP launch path /abs/project "<editor>"`, with the editor name or command `find` printed. Save it if they say it is a regular one: `$BP add proj path /abs/project "<editor>"`. |
| **Open a file in a given app** | The same: `$BP launch path /abs/file.pdf "<app>"`. With no app named, the system default opens it. |
| **Find a file** ("the pdf I downloaded", "my report") | The newest files: `$BP recent 10`. By name: `$BP files <text> [folder]`. One clear match: open it. Several: show up to five with their dates and ask. |
| **Is X running? / open it only if not** | `$BP running <process name>`. The process name can differ from the app name (Chrome is `chrome`), so a "no" is a hint, not proof. |
| **Join a meeting** | `$BP launch url "<meeting link>"`: `https://` links open in the browser, `zoommtg://` and `msteams:` open the app. A meeting link names one meeting, so never auto-save it; save by hand only if the user says it recurs. |
| **Write an email** | Default mail app: `$BP launch url "mailto:<to>?subject=<s>&body=<b>"` with values from `$BP urlenc`. In Gmail instead: the draft link in [deep-links.md](deep-links.md). Sending is the user's call unless the task says send. |
| **Add a calendar event** | The Google Calendar link in [deep-links.md](deep-links.md) fills the form in; saving the event still needs the user or the session's browser tools. |
| **Look something up** (web, map, translation, wiki, video) | The matching link in [deep-links.md](deep-links.md), opened in the browser the user named, else the default. |
| **Play music or video** | A search link (YouTube, Bilibili) or `spotify:search:<q>` with `$BP launch url`. Pressing play needs the session's computer-control tools; otherwise stop at the results and say so. |
| **Open settings** | `$BP find settings`, then open the app it finds (System Settings on macOS; GNOME Settings, KDE System Settings and others on Linux). Specific panes depend on the OS version, so do not guess a pane link. |
| **Switch to a running app** | On macOS `$BP launch app "<App>"` brings it forward. On Linux there is no portable way; say so. |
| **Open several sites at once** | `$BP add` each, then one `group`; or several `$BP launch url ...` calls in the order given. |
| **App with a localized name** | Translate to the app's own name before `find`, and try both: 备忘录 Notes, 日历 Calendar, 访达 Finder, 终端 Terminal, 系统设置 System Settings, 邮件 Mail, 提醒事项 Reminders, 照片 Photos, 音乐 Music, 地图 Maps, 计算器 Calculator, 微信 WeChat; on Linux 文件 Files, 设置 Settings, 文本编辑器 Text Editor. |
| **Several accounts or browser profiles** | `with` takes only an app, so profiles cannot be chosen. Say so and open the default profile. |

## What this skill does not do

- Run arbitrary shell commands or scripts as shortcuts (start a dev server, `docker compose up`): run those directly and do not save them here.
- Shut down, sleep, restart or lock the computer, or change system settings.
- Click or type inside an app. That needs the session's browser or computer-control tools; without them, stop after opening and list the steps left.
- Windows, or a Linux session with no desktop (over SSH or in a container): `xdg-open` fails there, and the honest answer is to print the link or path instead.
