# Everyday scenarios

How common computer jobs map onto `scripts/bp.sh` (`$BP` below). Read the row that matches; most tasks are one or two commands. Each `launch` opens without saving; add `--auto` saves only where the table says so.

| The user wants | Do |
|---|---|
| **Start a work setup** ("上班", "start my day") | Save once: `$BP add work group chrome,gmail,slack`. Then `/bp work` is `$BP run work`; members open in order and a failing one is reported without stopping the rest. Groups hold aliases, so save the members first. |
| **End the day / close the apps** | `$BP stop work` asks every app in the group to quit. One app: `$BP stop slack`. Warn first if an app may hold unsaved work. |
| **Open a folder** (Downloads, Desktop, a project) | `$BP launch path /absolute/path`. Expand `~`, `~/Downloads`, `~/Desktop`, `~/Documents` to the real home path first. |
| **Open a project in the editor** | `$BP launch path /abs/project "<editor>"`, with the editor name or command `find` printed. Save it if they say it is a regular one: `$BP add proj path /abs/project "<editor>"`. |
| **Open a file in a given app** | The same: `$BP launch path /abs/file.pdf "<app>"`. With no app named, the system default opens it. |
| **Find a file** ("the pdf I downloaded", "my report") | `$BP recent 10` covers Downloads, Desktop and Documents; `$BP files <text> [folder]` searches by name anywhere else. For "latest" or "recent", take the newest file of the type asked (a PDF means a `.pdf`, even if a photo is newer) and open it, naming the runner-up so the user can redirect. For a name with several different matches, show up to five with their dates and ask. |
| **Draw something** ("open the drawing board and draw a cat") | See **Make something, then open it** below. |
| **Write a note, a list, a document** | The same: write the file yourself, then open it in an editor or notes app. |
| **Make a table** | The same, as a `.csv`, opened in a spreadsheet app. |
| **Open "a" kind of app** (a drawing board, a browser, a terminal, a music player) | `$BP category <kind>`: drawing, browser, editor, terminal, mail, chat, music, video, notes, office, spreadsheet, files, settings. Several matches: pick the obvious one, or ask. None: say so and offer a web version (see [deep-links.md](deep-links.md)). |
| **Is X running? / open it only if not** | `$BP running <process name>`. The process name can differ from the app name (Chrome is `chrome`), so a "no" is a hint, not proof. |
| **Join a meeting** | `$BP launch url "<meeting link>"`: `https://` links open in the browser, `zoommtg://` and `msteams:` open the app. A meeting link names one meeting, so never auto-save it; save by hand only if the user says it recurs. |
| **Write an email** | Default mail app: `$BP launch url "mailto:<to>?subject=<s>&body=<b>"` with values from `$BP urlenc`. In Gmail instead: the draft link in [deep-links.md](deep-links.md). Sending is the user's call unless the task says send. |
| **Add a calendar event** | The Google Calendar link in [deep-links.md](deep-links.md) fills the form in; saving the event still needs the user or the session's browser tools. |
| **Look something up** (web, map, translation, wiki, video) | The matching link in [deep-links.md](deep-links.md), opened in the browser the user named, else the default. |
| **Play music or video** | A search link (YouTube, Bilibili) or `spotify:search:<q>` with `$BP launch url`. Pressing play needs the session's computer-control tools; otherwise stop at the results and say so. |
| **Open settings** | `$BP find settings`, then open the app it finds (System Settings on macOS; GNOME Settings, KDE System Settings and others on Linux). Specific panes depend on the OS version, so do not guess a pane link. |
| **Switch to a running app** | On macOS `$BP launch app "<App>"` brings it forward. On Linux there is no portable way; say so. |
| **Open several sites at once** | `$BP add` each, then one `group`; or several `$BP launch url ...` calls in the order given. |
| **App with a localized name** | Translate to the app's own name before `find`, and try both. Words for a kind of app, not one app (画板, 画图, 白板 for a drawing board), go to `$BP category drawing`. Examples: 备忘录 Notes, 日历 Calendar, 访达 Finder, 终端 Terminal, 系统设置 System Settings, 邮件 Mail, 提醒事项 Reminders, 照片 Photos, 音乐 Music, 地图 Maps, 计算器 Calculator, 微信 WeChat; on Linux 文件 Files, 设置 Settings, 文本编辑器 Text Editor. |
| **Several accounts or browser profiles** | `with` takes only an app, so profiles cannot be chosen. Say so and open the default profile. |

## Work live in an app

When the user asks for something to be drawn or typed in an app ("open the drawing board and draw a dog", "write it in Notes"), do it in the app, where they can watch. This needs the session's computer-control tools (screenshots, mouse and keyboard). Check your own tool list for them: names such as `computer_*` or `computer-use`, or a single tool that switches computer control on, which you should call. Follow any instructions that come with them before the first step.

1. **Open the app.** `$BP category drawing` lists drawing boards and whiteboards (画板, 白板, 画图); Prefer freehand apps: Freeform, Krita, Drawing, MyPaint, Pixelmator, GIMP. Vector editors such as Inkscape and LibreOffice Draw need a tool picked for every shape, so use them last. Then `$BP launch app <target>`, or `$BP run <alias>` if it is saved. A whiteboard in the browser is a good fallback: `https://excalidraw.com` (see [deep-links.md](deep-links.md)); there the key `p` selects the freehand pencil.
2. **Look first.** Take a screenshot and find the canvas. If a new-document dialog is open, accept the defaults. Choose a plain pencil or pen and a dark color. Stay in that app's window; if a dialog asks about saving, signing in, permissions or updates, stop and ask.
3. **Plan the picture in canvas coordinates** before touching the mouse. For a dog: a body ellipse, a round head, two ears, eyes, a nose, four legs, a tail. Write each stroke as a list of points, a circle or ellipse as 12 to 16 points around its edge.
4. **Draw stroke by stroke,** dragging along the points. Take a screenshot every few strokes to check position and size. Undo (Cmd or Ctrl+Z) a wrong stroke instead of erasing. About 15 to 30 strokes make a recognizable picture; stop when it is one. Draw ears, legs and other pointed parts as one closed outline (go back to the start point) so they read as shapes, and keep every part inside the canvas.
5. **Leave it open and unsaved.** Say what you drew and offer to save or export it (ask where). Never overwrite an existing file.

If the session has no computer-control tools, open the app, say plainly that drawing live needs them (and that they can be switched on for the session), and stop. Do not pretend to have drawn. Offer to generate a picture file and open it instead, as a choice for the user, never as the default.

## Make a file, then open it

When the user wants a file (a note, a table, a page, a picture to keep), or chooses the file route above:

1. **Pick the app** with `$BP category <kind>`: `editor` or `notes` for text, `spreadsheet` for tables, `drawing` for pictures (an SVG opens in Inkscape, Krita, GIMP, Affinity or any browser).
2. **Get a free path** with `F="$($BP outfile cat.svg)"`. It never overwrites an existing file and puts pictures in `~/Pictures/bp` and everything else in `~/Documents/bp`, where the user will find them. Do not use `/tmp`.
3. **Write the file** to that path: Markdown or text for a note, CSV with a header row for a table, HTML for a page, and for a picture an SVG with `viewBox="0 0 800 600"` and a few dozen lines of filled, outlined shapes layered from back to front.
4. **Open it:** `$BP launch path "$F" "<app>"`, or without an app for the system default.
5. **Tell the user** where the file is and that it was generated as a file, not made by hand in the app.

## What this skill does not do

- Run arbitrary shell commands or scripts as shortcuts (start a dev server, `docker compose up`): run those directly and do not save them here.
- Shut down, sleep, restart or lock the computer, or change system settings.
- Click, type or draw inside an app by itself. That is done with the session's browser or computer-control tools; without them, stop after opening and list the steps left.
- Windows, or a Linux session with no desktop (over SSH or in a container): `xdg-open` fails there, and the honest answer is to print the link or path instead.
