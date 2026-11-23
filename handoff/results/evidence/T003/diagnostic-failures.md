# Version 12 and 13 browser diagnostics

These are failures observed during the normal owner-browser acceptance path, before the final version 14 capture.

- Version 12, source `0ce0d8ca68b949932426da9ec6595a564392611f`: Overview displayed sample KPI cards but no “Live scheduler feed” card or “Open live view” button. The shipped `liveCard()` function returned an empty string before its rendering code. Local build, validation and 9/9 Worker/SQLite tests had passed; they did not cover this browser behavior.
- Version 13, source `e2c96472995c59a9c024db4c0ba1b95d6fc87ee3`: The live card and button appeared. Clicking “Open live view” changed the route to `#live` and showed the Live feed heading, while the old data pane remained invisible. Browser inspection found `#livepane.hidden == false` but computed `display: none`, caused by `footer,#livepane{display:none!important}` in the stylesheet.
- Version 14, source `22622e0fd9a424dce9e1b46e119ad57b45590185`: The card and data pane both appeared through the normal owner-browser path. `live-feed.jpg` and `live-feed.txt` are the final acceptance evidence.

The version 12 and 13 source commits and deployment IDs are recorded in `T003.result.md`. This file is a diagnostic record, not a substituted acceptance capture.