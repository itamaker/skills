# Deep links

When a task names a site and something to look for or do there, open the page that already shows it instead of the front page plus clicks. This also works when the session has no browser tools.

Build the URL, then open it without saving (it holds a query): `$BP launch url "<url>" ["<browser>"]`, with the browser the user named, or none for the system default. One launch opens browser and page together.

| Goal | URL |
|---|---|
| Search YouTube | `https://www.youtube.com/results?search_query=<q>` |
| Find a YouTube channel | the same URL plus `&sp=EgIQAg%253D%253D` (copy this value exactly; the `%25` is intended) |
| Search Bilibili | `https://search.bilibili.com/all?keyword=<q>` |
| Search Google | `https://www.google.com/search?q=<q>` |
| Search Baidu | `https://www.baidu.com/s?wd=<q>` |
| Search GitHub | `https://github.com/search?q=<q>` |
| Wikipedia (Chinese / English) | `https://zh.wikipedia.org/w/index.php?search=<q>` / `https://en.wikipedia.org/w/index.php?search=<q>` |
| Map search | `https://www.google.com/maps/search/?api=1&query=<q>` |
| Directions to a place | `https://www.google.com/maps/dir/?api=1&destination=<q>` |
| Translate | `https://translate.google.com/?sl=auto&tl=<lang code>&text=<q>&op=translate` |
| Start a Gmail draft | `https://mail.google.com/mail/?view=cm&fs=1&to=<to>&su=<subject>&body=<body>` |
| New calendar event | `https://calendar.google.com/calendar/render?action=TEMPLATE&text=<title>&dates=<start>/<end>&details=<notes>` with times as `YYYYMMDDTHHMMSS` (local) |
| New Google Doc / Sheet | `https://docs.google.com/document/create` / `https://docs.google.com/spreadsheets/create` |
| Mail app draft | `mailto:<to>?subject=<s>&body=<b>` (opens the system mail app, not a browser) |
| Spotify search | `spotify:search:<q>` (opens the Spotify app) |

Percent-encode every `<...>` value with `$BP urlenc "<text>"`, including non-ASCII text (`老高` becomes `%E8%80%81%E9%AB%98`). Only the links the script allows can be launched or saved: web addresses, `mailto:`, `tel:`, `sms:`, `facetime:`, `zoommtg://`, `zoomus://`, `msteams:`, `slack://`, `spotify:`, `vscode://`, `obsidian://`, `notion://`, `discord://`, `tg://` and `x-apple.systempreferences:`.

For a site not in the table, use its own search box with the session's browser tools, or open its front page and say what is left.

## Going on into a result

With browser tools, continue from the opened page. For a channel or profile, take the top result whose name contains the words the user gave and open it (for "watch their videos", its `/videos` page). Tell the user the name and address you actually reached and the next two matches, since names are often shared. Moving between pages is not consequential, so pick and say so rather than asking.

Without browser tools you have not seen the page: do not say which result comes first or what it contains. Stop at the results page and say which click is left.

A Gmail or calendar link only fills the form in. Sending or saving still needs the task to ask for it, and the recipient, text or time shown to the user first if they were not given exactly.
